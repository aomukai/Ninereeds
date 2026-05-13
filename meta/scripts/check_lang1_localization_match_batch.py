#!/usr/bin/env python3
"""Check whether repaired lang_1 localizations still match the English line."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
NONSENSE_FILE = REPO_ROOT / "training_data" / "lang" / "nonsense.md"
PROGRESS_LEDGER = REPO_ROOT / "tmp" / "lang_1_batches" / "localization_match_progress.txt"
FINDINGS_LOG = REPO_ROOT / "tmp" / "lang_1_batches" / "localization_match_findings.tsv"
TMP_DIR = REPO_ROOT / "tmp" / "lang_1_batches" / "localization_match"
AUTH_FILE = Path.home() / ".local" / "share" / "opencode" / "auth.json"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-v4-flash"


def ensure_paths() -> None:
    PROGRESS_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    if not FINDINGS_LOG.exists():
        FINDINGS_LOG.write_text("", encoding="utf-8")


def load_targets() -> list[dict]:
    rows: list[dict] = []
    for line in NONSENSE_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("| training_data/lang/lang_1/"):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 2:
            continue
        rel_path = parts[0]
        path = REPO_ROOT / rel_path
        rows.append({"word": path.stem.replace("_", " "), "filename": path.name, "path": path, "rel_path": rel_path})
    return rows


def load_completed() -> list[str]:
    if not PROGRESS_LEDGER.exists():
        return []
    return [line.strip() for line in PROGRESS_LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]


def get_api_key() -> str:
    env_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if env_key:
        return env_key
    if AUTH_FILE.exists():
        data = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
        key = data.get("openrouter", {}).get("key", "")
        if key:
            return key
    raise RuntimeError("OpenRouter API key not found in env or ~/.local/share/opencode/auth.json")


def json_schema_hint() -> str:
    return """{
  "results": [
    {
      "word": "dog",
      "filename": "dog.md",
      "status": "ok",
      "problem": ""
    }
  ],
  "batch_problem": ""
}"""


def build_prompt(targets: list[dict]) -> str:
    blocks = []
    for item in targets:
        content = item["path"].read_text(encoding="utf-8").rstrip()
        blocks.append(f"FILE: {item['rel_path']}\nWORD: {item['word']}\nCONTENT:\n{content}")
    joined = "\n\n".join(blocks)
    return f"""Review whether the German, Japanese, and Chinese lines still match the English line in these repaired lang_1 files.

Task:
- Focus on localization alignment only.
- Line 1 is English ground truth for this check.
- Decide whether lines 2, 3, and 4 still express the same core concept as line 1.
- Ignore minor phrasing differences.
- Flag only clear mismatches such as different category, different concept, wrong part of speech, or numbered/placeholder mismatch.
- Do not suggest fixes.
- Do not rewrite anything.
- Return JSON only.

Files in this batch:
{joined}

Return exactly one JSON object in this schema:
{json_schema_hint()}

Rules for the JSON:
- results must contain exactly {len(targets)} items
- keep each word unchanged
- keep each filename unchanged
- status must be either "ok" or "problem"
- problem must be empty when status is "ok"
- batch_problem must be empty unless the batch itself could not be evaluated
- do not include any text before or after the JSON object
"""


def strip_wrappers(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end >= start:
        return text[start:end + 1]
    return text


def call_api(prompt: str, timeout: int, max_tokens: int) -> tuple[str, dict]:
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {get_api_key()}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API {exc.code}: {body[:600]}") from exc
    text = (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
    if not text:
        raise RuntimeError("empty API response content")
    return text, data


def parse_response(raw_text: str) -> dict:
    return json.loads(strip_wrappers(raw_text))


def verify_batch(targets: list[dict], payload: dict) -> list[dict]:
    if not isinstance(payload, dict):
        raise RuntimeError("response is not a JSON object")
    results = payload.get("results")
    batch_problem = payload.get("batch_problem", "")
    if not isinstance(results, list):
        raise RuntimeError("response missing results array")
    if batch_problem not in ("", None):
        raise RuntimeError(f"model reported batch problem: {batch_problem}")

    expected = {item["word"]: item["filename"] for item in targets}
    seen: set[str] = set()
    normalized: list[dict] = []
    for item in results:
        if not isinstance(item, dict):
            raise RuntimeError("results item is not an object")
        word = item.get("word")
        filename = item.get("filename")
        status = item.get("status")
        problem = item.get("problem")
        if word not in expected:
            raise RuntimeError(f"unexpected word in output: {word}")
        if word in seen:
            raise RuntimeError(f"duplicate word in output: {word}")
        if filename != expected[word]:
            raise RuntimeError(f"wrong filename for {word}: {filename}")
        if status not in {"ok", "problem"}:
            raise RuntimeError(f"invalid status for {word}: {status}")
        if not isinstance(problem, str):
            raise RuntimeError(f"non-string problem for {word}")
        if status == "ok" and problem.strip():
            raise RuntimeError(f"ok result for {word} has non-empty problem")
        if status == "problem" and not problem.strip():
            raise RuntimeError(f"problem result for {word} has empty problem")
        seen.add(word)
        normalized.append({"word": word, "filename": filename, "status": status, "problem": problem.strip()})
    missing = [item["word"] for item in targets if item["word"] not in seen]
    if missing:
        raise RuntimeError(f"missing words in output: {missing}")
    return normalized


def append_findings(results: list[dict]) -> int:
    flagged = [row for row in results if row["status"] == "problem"]
    if not flagged:
        return 0
    with FINDINGS_LOG.open("a", encoding="utf-8") as handle:
        for row in flagged:
            path = f"training_data/lang/lang_1/{row['filename']}"
            problem = row["problem"].replace("\t", " ").replace("\n", " ").strip()
            handle.write(f"{path}\t{problem}\n")
    return len(flagged)


def append_ledger(words: list[str]) -> None:
    with PROGRESS_LEDGER.open("a", encoding="utf-8") as handle:
        for word in words:
            handle.write(f"{word}\n")


def save_debug(batch_id: int, prompt: str, raw_text: str, raw_json: dict, suffix: str) -> None:
    (TMP_DIR / f"batch_{batch_id:04d}.{suffix}.prompt.txt").write_text(prompt, encoding="utf-8")
    (TMP_DIR / f"batch_{batch_id:04d}.{suffix}.response.txt").write_text(raw_text, encoding="utf-8")
    (TMP_DIR / f"batch_{batch_id:04d}.{suffix}.response.json").write_text(
        json.dumps(raw_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether repaired lang_1 localizations still match English.")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--max-tokens", type=int, default=16000)
    parser.add_argument("--retry-max-tokens", type=int, default=32000)
    parser.add_argument("--retries", type=int, default=2)
    args = parser.parse_args()

    ensure_paths()
    all_targets = load_targets()
    completed = set(load_completed())
    pending = [item for item in all_targets if item["word"] not in completed]
    batch = pending[: args.batch_size]

    if not batch:
        print("number of files checked: 0")
        print("findings appended: 0")
        print("findings log: tmp/lang_1_batches/localization_match_findings.tsv")
        return 0

    batch_id = len(completed) // max(args.batch_size, 1) + 1
    prompt = build_prompt(batch)
    attempts = [args.max_tokens]
    if args.retry_max_tokens not in attempts:
        attempts.append(args.retry_max_tokens)
    while len(attempts) < args.retries:
        attempts.append(args.retry_max_tokens)

    last_error: Exception | None = None
    for idx, max_tokens in enumerate(attempts, start=1):
        try:
            raw_text, raw_json = call_api(prompt, args.timeout, max_tokens)
            save_debug(batch_id, prompt, raw_text, raw_json, f"attempt{idx}")
            results = verify_batch(batch, parse_response(raw_text))
            findings = append_findings(results)
            append_ledger([item["word"] for item in batch])
            print(f"number of files checked: {len(batch)}")
            print(f"findings appended: {findings}")
            print("findings log: tmp/lang_1_batches/localization_match_findings.tsv")
            return 0
        except Exception as exc:
            last_error = exc
            time.sleep(3)

    print(f"FAILED batch {batch_id}: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

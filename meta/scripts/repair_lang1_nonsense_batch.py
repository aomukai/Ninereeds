#!/usr/bin/env python3
"""Repair flagged lang_1 files in small DeepSeek batches."""

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
OUT_DIR = REPO_ROOT / "training_data" / "lang" / "lang_1"
LEDGER = REPO_ROOT / "tmp" / "lang_1_batches" / "nonsense_repair_progress.txt"
TMP_DIR = REPO_ROOT / "tmp" / "lang_1_batches" / "nonsense_repair"
AUTH_FILE = Path.home() / ".local" / "share" / "opencode" / "auth.json"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-v4-flash"


def ensure_paths() -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)


def parse_targets() -> list[dict]:
    rows: list[dict] = []
    for line in NONSENSE_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("| training_data/lang/lang_1/"):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 2:
            continue
        rel_path, problem = parts[0], parts[1]
        path = REPO_ROOT / rel_path
        rows.append(
            {
                "path": path,
                "rel_path": rel_path,
                "filename": path.name,
                "word": path.stem.replace("_", " "),
                "problem": problem,
            }
        )
    return rows


def load_completed() -> list[str]:
    if not LEDGER.exists():
        return []
    return [line.strip() for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]


def valid_output_file(path: Path) -> bool:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return False
    return len(lines) == 4 and all(line.strip() for line in lines)


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
  "files": [
    {
      "word": "dog",
      "filename": "dog.md",
      "lines": [
        "A dog is an animal.",
        "Ein Hund ist ein Tier.",
        "犬は動物だ。",
        "狗是动物。"
      ]
    }
  ],
  "batch_problem": ""
}"""


def build_prompt(targets: list[dict]) -> str:
    blocks: list[str] = []
    for item in targets:
        current = item["path"].read_text(encoding="utf-8").rstrip()
        blocks.append(
            f"TARGET FILE: {item['rel_path']}\n"
            f"TARGET WORD: {item['word']}\n"
            f"REPORTED PROBLEM: {item['problem']}\n"
            f"CURRENT CONTENT:\n{current}"
        )
    joined = "\n\n".join(blocks)
    return f"""Repair these flagged lang_1 files.

Task:
- Rewrite only the files listed in this batch.
- Fix the reported semantic problem with the smallest clean change that makes the entry sensible.
- Preserve the overall lang_1 format: exactly 4 lines per file.
- Keep each target word tied to the same filename.
- Keep the sentences simple and natural.
- Avoid circular definitions.
- For adjective targets, define the adjective naturally through a concrete noun phrase without turning the noun into the concept.
- For verb targets, use a gerund or natural action-concept phrasing.
- For malformed or unusual targets with numeric suffixes or typo-like forms, make the entry as sensible and neutral as possible without renaming the target.
- Return JSON only.

Do not:
- add explanations
- add markdown fences
- skip any listed file
- rename files

Batch files:
{joined}

Return exactly one JSON object in this schema:
{json_schema_hint()}

Rules for the JSON:
- files must contain exactly {len(targets)} items
- each word must match the target word exactly
- each filename must match the target filename exactly
- each lines array must contain exactly 4 non-empty strings
- batch_problem must be an empty string unless the full batch cannot be repaired
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
        headers={
            "Authorization": f"Bearer {get_api_key()}",
            "Content-Type": "application/json",
        },
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
    files = payload.get("files")
    batch_problem = payload.get("batch_problem", "")
    if not isinstance(files, list):
        raise RuntimeError("response missing files array")
    if batch_problem not in ("", None):
        raise RuntimeError(f"model reported batch problem: {batch_problem}")

    expected = {item["word"]: item for item in targets}
    seen: set[str] = set()
    normalized: list[dict] = []

    for item in files:
        if not isinstance(item, dict):
            raise RuntimeError("files item is not an object")
        word = item.get("word")
        filename = item.get("filename")
        lines = item.get("lines")
        if word not in expected:
            raise RuntimeError(f"unexpected word in output: {word}")
        if word in seen:
            raise RuntimeError(f"duplicate word in output: {word}")
        if filename != expected[word]["filename"]:
            raise RuntimeError(f"wrong filename for {word}: {filename}")
        if not isinstance(lines, list) or len(lines) != 4:
            raise RuntimeError(f"{word} does not have exactly 4 lines")
        if any(not isinstance(line, str) or not line.strip() for line in lines):
            raise RuntimeError(f"{word} contains blank or non-string lines")
        seen.add(word)
        normalized.append({"word": word, "filename": filename, "lines": [line.strip() for line in lines]})

    missing = [item["word"] for item in targets if item["word"] not in seen]
    if missing:
        raise RuntimeError(f"missing words in output: {missing}")
    return normalized


def write_files(entries: list[dict]) -> None:
    for entry in entries:
        path = OUT_DIR / entry["filename"]
        path.write_text("\n".join(entry["lines"]) + "\n", encoding="utf-8")
        if not valid_output_file(path):
            raise RuntimeError(f"invalid file after write: {path.name}")


def append_ledger(words: list[str]) -> None:
    with LEDGER.open("a", encoding="utf-8") as handle:
        for word in words:
            handle.write(f"{word}\n")


def save_debug(batch_id: int, prompt: str, raw_text: str, raw_json: dict, suffix: str) -> None:
    (TMP_DIR / f"batch_{batch_id:04d}.{suffix}.prompt.txt").write_text(prompt, encoding="utf-8")
    (TMP_DIR / f"batch_{batch_id:04d}.{suffix}.response.txt").write_text(raw_text, encoding="utf-8")
    (TMP_DIR / f"batch_{batch_id:04d}.{suffix}.response.json").write_text(
        json.dumps(raw_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair flagged lang_1 files in small batches.")
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--max-tokens", type=int, default=16000)
    parser.add_argument("--retry-max-tokens", type=int, default=32000)
    parser.add_argument("--retries", type=int, default=2)
    args = parser.parse_args()

    ensure_paths()
    all_targets = parse_targets()
    completed = set(load_completed())
    pending = [item for item in all_targets if item["word"] not in completed]
    batch = pending[: args.batch_size]

    if not batch:
        print("number of files repaired: 0")
        print("output directory: training_data/lang/lang_1/")
        print("skipped/problematic words with short reason: none")
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
            entries = verify_batch(batch, parse_response(raw_text))
            write_files(entries)
            append_ledger([item["word"] for item in batch])
            print(f"number of files repaired: {len(batch)}")
            print("output directory: training_data/lang/lang_1/")
            print("skipped/problematic words with short reason: none")
            return 0
        except Exception as exc:
            last_error = exc
            time.sleep(3)

    print(f"FAILED batch {batch_id}: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

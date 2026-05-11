#!/usr/bin/env python3
"""Run one DeepSeek batch for training_data/lang/lang_1 via direct OpenRouter API."""

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
ALLOWLIST = REPO_ROOT / "training_data" / "allowlist.txt"
OUT_DIR = REPO_ROOT / "training_data" / "lang" / "lang_1"
LEDGER = REPO_ROOT / "meta" / "ledgers" / "lang_1_progress.txt"
TMP_DIR = REPO_ROOT / "tmp" / "lang_1_batches"
AUTH_FILE = Path.home() / ".local" / "share" / "opencode" / "auth.json"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-v4-flash"


def slugify(word: str) -> str:
    return word.strip().lower().replace(" ", "_")


def relaxed_slugify(word: str) -> str:
    return slugify(word).replace("-", "_")


def ensure_paths() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)


def load_allowlist() -> list[str]:
    return [line.strip() for line in ALLOWLIST.read_text(encoding="utf-8").splitlines() if line.strip()]


def valid_output_file(path: Path) -> bool:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return False
    return len(lines) == 4 and all(line.strip() for line in lines)


def bootstrap_ledger(words: list[str]) -> list[str]:
    existing = sorted(OUT_DIR.glob("*.md"))
    seen: list[str] = []
    known = set(words)
    for path in existing:
        word = path.stem.replace("_", " ")
        if word in known and valid_output_file(path):
            seen.append(word)

    if LEDGER.exists():
        recorded = [line.strip() for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]
        merged: list[str] = []
        merged_set: set[str] = set()
        for word in recorded + seen:
            if word not in merged_set:
                merged.append(word)
                merged_set.add(word)
        LEDGER.write_text("".join(f"{word}\n" for word in merged), encoding="utf-8")
        return merged

    LEDGER.write_text("".join(f"{word}\n" for word in seen), encoding="utf-8")
    return seen


def pending_words(all_words: list[str], completed: set[str]) -> list[str]:
    return [word for word in all_words if word not in completed]


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
  "problems": []
}"""


def build_prompt(targets: list[str]) -> str:
    bullets = "\n".join(f"- {word}" for word in targets)
    return f"""TASK:
Read training_data/allowlist.txt.

Create simple multilingual grounding files for exactly this batch of words:
{bullets}

Output directory:
training_data/lang/lang_1/

Create one file for every content word in this batch.

Each word must appear exactly once as the primary concept X of its own file.

Output format:
training_data/lang/lang_1/X.md

where X is the English concept word.

File format:
Line 1: English sentence
Line 2: natural/localized German
Line 3: natural/localized Japanese
Line 4: natural/localized Chinese

The lines are localisations, not literal translations.
Preserve meaning naturally in each language.
Use natural native phrasing.
Do not force English sentence structure onto other languages.

Use the following templates based on part of speech.

--------------------------------
NOUN TEMPLATE
--------------------------------

Example:
A dog is an animal.
Ein Hund ist ein Tier.
犬は動物だ。
狗是动物。

Rules:
- X is a noun.
- Use simple category/classification relationships.
- Y should be a broader category of X.
- Prefer concrete concepts.

--------------------------------
VERB TEMPLATE
--------------------------------

Example:
Running is movement.
Laufen ist Bewegung.
走ることは移動だ。
跑步是移动。

Rules:
- X is a verb.
- English must use the gerund form.
- German should use the infinitive nominally.
- Japanese and Chinese should use natural action-concept phrasing.
- Y should describe the action category or function.

--------------------------------
ADJECTIVE TEMPLATE
--------------------------------

Example:
A red apple is a fruit.
Ein roter Apfel ist eine Frucht.
赤いりんごは果物だ。
红苹果是水果。

Rules:
- X is an adjective.
- Use X naturally as an attribute of a concrete noun.
- Use a simple concrete noun.
- Keep the sentence short and easy.
- Avoid metaphorical or abstract usage.

--------------------------------
GLOBAL RULES
--------------------------------

- Use only content words from training_data/allowlist.txt.
- Grammar/function words are allowed even if not present in allowlist.txt.
- Every target word in this batch must appear once as concept X.
- Do not skip any target word in this batch.
- English and German must use correct articles where required.
- Use natural everyday language.
- Each file must contain exactly 4 lines.
- Use lowercase filenames.
- Replace spaces in filenames with underscores.
- Keep hyphens in filenames when the word already contains hyphens.
- Avoid duplicate files.
- Do not include markdown fences.
- Return JSON only.

Return exactly one JSON object in this schema:
{json_schema_hint()}

Rules for the JSON:
- "files" must contain exactly {len(targets)} items, one per target word.
- Each item must use the target word unchanged in "word".
- Each filename must be the lowercase filename for that word.
- Spaces become underscores.
- Existing hyphens stay hyphens.
- Each "lines" array must contain exactly 4 non-empty strings.
- "problems" must be an empty array unless a target is truly impossible.
- Do not include any text before or after the JSON object.
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
        "temperature": 0.2,
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
    cleaned = strip_wrappers(raw_text)
    return json.loads(cleaned)


def verify_batch(targets: list[str], payload: dict) -> list[dict]:
    if not isinstance(payload, dict):
        raise RuntimeError("response is not a JSON object")
    files = payload.get("files")
    problems = payload.get("problems")
    if not isinstance(files, list):
        raise RuntimeError("response missing files array")
    if problems not in ([], None):
        raise RuntimeError(f"model reported problems: {problems}")

    expected = {word: f"{slugify(word)}.md" for word in targets}
    relaxed_expected = {word: f"{relaxed_slugify(word)}.md" for word in targets}
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
        if filename not in {expected[word], relaxed_expected[word]}:
            raise RuntimeError(f"wrong filename for {word}: {filename}")
        if not isinstance(lines, list) or len(lines) != 4:
            raise RuntimeError(f"{word} does not have exactly 4 lines")
        if any(not isinstance(line, str) or not line.strip() for line in lines):
            raise RuntimeError(f"{word} contains blank or non-string lines")
        seen.add(word)
        normalized.append({"word": word, "filename": expected[word], "lines": [line.strip() for line in lines]})

    missing = [word for word in targets if word not in seen]
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
    parser = argparse.ArgumentParser(description="Run one DeepSeek batch for lang_1 generation.")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=1800, help="HTTP timeout in seconds")
    parser.add_argument("--max-tokens", type=int, default=16000)
    parser.add_argument("--retry-max-tokens", type=int, default=32000)
    parser.add_argument("--retries", type=int, default=2)
    args = parser.parse_args()

    ensure_paths()
    all_words = load_allowlist()
    completed = bootstrap_ledger(all_words)
    done = set(completed)
    targets = pending_words(all_words, done)[: args.batch_size]

    if not targets:
        print("number of files created: 0")
        print("output directory: training_data/lang/lang_1/")
        print("skipped/problematic words with short reason: none")
        return 0

    batch_id = len(completed) // max(args.batch_size, 1) + 1
    prompt = build_prompt(targets)
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
            entries = verify_batch(targets, parse_response(raw_text))
            write_files(entries)
            append_ledger(targets)
            print(f"number of files created: {len(targets)}")
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

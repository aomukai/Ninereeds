"""
Pilot story generator. Reads a schema record from tmp/schema_pilot_output.jsonl
(or any schema JSONL), appends it to the prompt template, and calls DeepSeek.

Usage:
  # Generate story for one specific label:
  python3 meta/scripts/story_gen_pilot.py --label worry

  # Generate stories for first N labels in the schema file:
  python3 meta/scripts/story_gen_pilot.py --count 5

  # Specify a different schema source:
  python3 meta/scripts/story_gen_pilot.py --label worry --schema tmp/phase_vocab.jsonl

Output files: tmp/stories/<label>.md
Reads OPENROUTER_API_KEY from environment or .env at repo root.
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-chat-v3-0324"
TEMPLATE = REPO / "tmp/story_gen_prompt_template.txt"
DEFAULT_SCHEMA = REPO / "tmp/schema_pilot_output.jsonl"
OUT_DIR = REPO / "tmp/stories"


def load_env():
    env_file = REPO / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def call_api(prompt: str, api_key: str) -> str:
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 2048,
    }).encode()

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]


def load_schema(path: Path) -> dict:
    return {json.loads(l)["label"]: json.loads(l)
            for l in path.read_text().splitlines() if l.strip()}


def generate(label: str, schema: dict, template: str, api_key: str) -> str:
    if label not in schema:
        sys.exit(f"Label '{label}' not found in schema file.")
    record = schema[label]
    prompt = template + json.dumps(record, ensure_ascii=False, indent=2)
    print(f"  Generating '{label}' (entry_tier={record.get('entry_tier','?')}) ...")
    return call_api(prompt, api_key)


def save(label: str, content: str) -> Path:
    OUT_DIR.mkdir(exist_ok=True)
    safe = label.replace(" ", "_").replace("/", "_")
    path = OUT_DIR / f"{safe}.md"
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label",  help="Single concept label to generate")
    ap.add_argument("--count",  type=int, help="Generate first N labels from schema")
    ap.add_argument("--schema", default=str(DEFAULT_SCHEMA),
                    help="Schema JSONL file to read from")
    args = ap.parse_args()

    load_env()
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("Set OPENROUTER_API_KEY before running.")

    template = TEMPLATE.read_text()
    schema = load_schema(Path(args.schema))

    if args.label:
        labels = [args.label]
    elif args.count:
        labels = list(schema.keys())[:args.count]
    else:
        ap.print_help()
        sys.exit(1)

    for label in labels:
        raw = generate(label, schema, template, api_key)
        path = save(label, raw)
        print(f"  Saved → {path}")
        print()
        print(raw[:600])
        print("  ..." if len(raw) > 600 else "")
        print()


if __name__ == "__main__":
    main()

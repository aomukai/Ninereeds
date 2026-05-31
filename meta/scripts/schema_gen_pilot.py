"""
Pilot: send schema_gen_prompt.txt to DeepSeek, parse the JSON array response,
and merge the new fields (pos, manifestations, anchors, entry_tier) into
tmp/phase_vocab.jsonl.

Usage:
  python3 meta/scripts/schema_gen_pilot.py \
    --prompt tmp/schema_gen_prompt.txt \
    --output tmp/schema_pilot_output.jsonl

Reads OPENROUTER_API_KEY from environment.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-chat-v3-0324"


def call_api(prompt: str, api_key: str) -> str:
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 4096,
    }).encode()

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]


def parse_response(text: str) -> list[dict]:
    # Strip any accidental markdown fences
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            l for l in lines
            if not l.startswith("```")
        ).strip()
    return json.loads(text)


def merge_into_vocab(records: list[dict], vocab_path: Path) -> dict:
    vocab = {r["label"]: r for r in (json.loads(l) for l in open(vocab_path))}
    updated = 0
    for rec in records:
        label = rec["label"]
        if label not in vocab:
            print(f"  WARN: '{label}' not in vocab list — skipping")
            continue
        vocab[label].update({
            "pos":            rec.get("pos", []),
            "manifestations": rec.get("manifestations", []),
            "anchors":        rec.get("anchors", []),
            "entry_tier":     rec.get("entry_tier", 2),
        })
        updated += 1
    return vocab, updated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt",  default="tmp/schema_gen_prompt.txt")
    ap.add_argument("--output",  default="tmp/schema_pilot_output.jsonl")
    ap.add_argument("--merge",   action="store_true",
                    help="Also merge results back into tmp/phase_vocab.jsonl")
    args = ap.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("Set OPENROUTER_API_KEY before running.")

    prompt_path = REPO / args.prompt
    prompt = prompt_path.read_text()

    print(f"Sending prompt ({len(prompt)} chars) to {MODEL} ...")
    raw = call_api(prompt, api_key)

    print("Parsing response ...")
    try:
        records = parse_response(raw)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print("--- raw response ---")
        print(raw[:2000])
        sys.exit(1)

    out_path = REPO / args.output
    with open(out_path, "w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} schema records → {out_path}")

    # Print a quick sample for review
    print("\n--- Sample output (first 5) ---")
    for r in records[:5]:
        print(json.dumps(r, indent=2, ensure_ascii=False))

    if args.merge:
        vocab_path = REPO / "tmp/phase_vocab.jsonl"
        vocab, updated = merge_into_vocab(records, vocab_path)
        with open(vocab_path, "w") as f:
            for r in sorted(vocab.values(), key=lambda r: (r["tier"], r["label"])):
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\nMerged {updated} records into {vocab_path}")


if __name__ == "__main__":
    main()

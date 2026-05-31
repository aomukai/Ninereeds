"""
Batch story generator. Generates 4-language teaching stories for all Tier-1
concepts in tmp/phase_vocab.jsonl that have a schema (manifestations field).

Usage:
  python3 meta/scripts/story_gen_batch.py [--workers 6] [--output training_data/teaching_stories]

  --workers   parallel API calls (default 6)
  --output    output directory   (default training_data/teaching_stories)
  --label     generate one specific label only
  --force     regenerate even if story file already exists

Progress: tmp/story_gen_done.txt     (one label per line = completed)
Failed:   tmp/story_gen_failed.txt   (labels that failed after retries)
Output:   <output>/<label_safe>.md   (4-language story file per concept)

Validation: each output file must contain exactly 4 [user] tags and
4 [Ninereeds] tags. Files that fail validation are retried once, then
written to failed log.
"""

import argparse
import json
import os
import re
import sys
import threading
import time
import urllib.request
from pathlib import Path

REPO        = Path(__file__).resolve().parents[2]
VOCAB_FILE  = REPO / "tmp/phase_vocab.jsonl"
TEMPLATE    = REPO / "tmp/story_gen_prompt_template.txt"
DONE_FILE   = REPO / "tmp/story_gen_done.txt"
FAILED_FILE = REPO / "tmp/story_gen_failed.txt"
API_URL     = "https://openrouter.ai/api/v1/chat/completions"
MODEL       = "deepseek/deepseek-chat-v3-0324"


def load_env():
    env = REPO / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def safe_filename(label: str) -> str:
    return re.sub(r"[^\w\-]", "_", label).strip("_") + ".md"


def validate(text: str) -> bool:
    """Check output has exactly 4 [user] and 4 [Ninereeds] blocks."""
    users     = len(re.findall(r"^\[user\]", text, re.MULTILINE))
    ninereeds = len(re.findall(r"^\[Ninereeds\]", text, re.MULTILINE))
    return users == 4 and ninereeds == 4


def call_api(prompt: str, api_key: str) -> str:
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 2048,
    }).encode()
    req = urllib.request.Request(
        API_URL, data=payload,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]


def generate_story(record: dict, template: str, api_key: str,
                   retries: int = 1) -> str | None:
    prompt = template + json.dumps(record, ensure_ascii=False, indent=2)
    for attempt in range(retries + 1):
        try:
            raw = call_api(prompt, api_key)
            text = raw.strip()
            # Strip accidental markdown fences
            if text.startswith("```"):
                text = "\n".join(l for l in text.splitlines()
                                 if not l.startswith("```")).strip()
            if validate(text):
                return text
            # Validation failed — retry
            if attempt < retries:
                time.sleep(3)
        except Exception as e:
            if attempt < retries:
                time.sleep(5)
            else:
                raise
    return None


def worker(queue: list, api_key: str, template: str, out_dir: Path,
           lock: threading.Lock, counters: dict, total: int):
    while True:
        with lock:
            if not queue:
                return
            record = queue.pop(0)

        label = record["label"]
        fname = safe_filename(label)
        out_path = out_dir / fname

        try:
            text = generate_story(record, template, api_key)
        except Exception as e:
            with lock:
                counters["failed"] += 1
                with open(FAILED_FILE, "a") as f:
                    f.write(label + "\n")
            print(f"  FAILED '{label}': {e}")
            continue

        if text is None:
            with lock:
                counters["failed"] += 1
                with open(FAILED_FILE, "a") as f:
                    f.write(label + "\n")
            print(f"  INVALID (bad block count) '{label}'")
            continue

        out_path.write_text(text + "\n", encoding="utf-8")

        with lock:
            counters["done"] += 1
            with open(DONE_FILE, "a") as f:
                f.write(label + "\n")
            pct = 100 * (counters["done"] + counters["failed"]) / total
            print(f"  [{counters['done'] + counters['failed']}/{total}  {pct:.1f}%] "
                  f"✓ {label}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--output",  default="training_data/teaching_stories")
    ap.add_argument("--label",   help="Generate one specific concept only")
    ap.add_argument("--force",   action="store_true",
                    help="Regenerate even if story file exists")
    args = ap.parse_args()

    load_env()
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("Set OPENROUTER_API_KEY before running.")

    if not TEMPLATE.exists():
        sys.exit(f"Template not found: {TEMPLATE}")
    template = TEMPLATE.read_text()

    out_dir = REPO / args.output
    out_dir.mkdir(parents=True, exist_ok=True)

    vocab = [json.loads(l) for l in VOCAB_FILE.read_text().splitlines() if l.strip()]

    done: set[str] = set()
    if DONE_FILE.exists() and not args.force:
        done = set(DONE_FILE.read_text().splitlines())

    if args.label:
        queue = [r for r in vocab if r["label"] == args.label and "manifestations" in r]
        if not queue:
            sys.exit(f"'{args.label}' not found or has no schema.")
    else:
        queue = [
            r for r in vocab
            if r["tier"] == 1
            and "manifestations" in r
            and r["label"] not in done
            and (args.force or not (out_dir / safe_filename(r["label"])).exists())
        ]

    if not queue:
        print("Nothing to generate — all concepts already have story files.")
        print("Use --force to regenerate.")
        return

    total = len(queue)
    print(f"Stories to generate: {total}  ({args.workers} workers)")
    print(f"Output: {out_dir}")

    if args.force:
        DONE_FILE.write_text("")
        FAILED_FILE.write_text("")

    lock     = threading.Lock()
    counters = {"done": 0, "failed": 0}

    threads = [
        threading.Thread(
            target=worker,
            args=(queue, api_key, template, out_dir, lock, counters, total),
            daemon=True,
        )
        for _ in range(min(args.workers, total))
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"\nDone.  ✓ {counters['done']}  ✗ {counters['failed']}")
    if counters["failed"]:
        print(f"Failed labels: {FAILED_FILE}")
        print("Re-run to retry failed items (they are not marked as done).")


if __name__ == "__main__":
    main()

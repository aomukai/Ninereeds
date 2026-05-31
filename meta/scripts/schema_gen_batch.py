"""
Batch schema generator. Generates pos/manifestations/anchors/entry_tier
for all Tier-1 concepts in tmp/phase_vocab.jsonl that don't have them yet.

Usage:
  python3 meta/scripts/schema_gen_batch.py [--batch 20] [--workers 4] [--force]

  --batch   concepts per API call (default 20)
  --workers parallel API calls   (default 4)
  --force   regenerate even if schema already present

Progress: tmp/schema_gen_done.txt  (one label per line = completed)
Output:   tmp/phase_vocab.jsonl    (updated in place)
"""

import argparse
import json
import os
import sys
import threading
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VOCAB_FILE  = REPO / "tmp/phase_vocab.jsonl"
DONE_FILE   = REPO / "tmp/schema_gen_done.txt"
API_URL     = "https://openrouter.ai/api/v1/chat/completions"
MODEL       = "deepseek/deepseek-chat-v3-0324"

PROMPT_BASE = """\
You are building curriculum schema records for a small language model that learns vocabulary through short stories.

The stories use an omniscient third-person narrator. They are set in a small village with: a garden, a pond, a bench, a path, a door, a window, a well, a field, a hedge, a market, and a tree.

Characters that may appear: a child, a boy, a girl, an old lady, a man, a dog, a cat, a bird.

Objects that may appear: a basket, bread, a bowl, a stone, a leaf, a flower, a chair, a pot, fire, rain, wind, shadow.

---

For each concept, generate four fields:

**pos**
List of grammatical roles this word can take.
Choose from: noun, verb, adjective, adverb.

**manifestations**
3 to 6 short phrases (3–6 words each) describing what this concept looks like in the physical world.
These are things a narrator can see or hear — not internal states.
Good: "hands grip the edge", "eyes follow the path", "steps slow down"
Bad: "feels nervous", "experiences concern", "has an emotion"
For abstract concepts: describe the situation or event that enacts the concept.
Good (for "chance"): "one seed grows, the other does not", "stone skips twice then sinks", "same throw gives a different result"

**anchors**
2 to 4 concrete nouns from the village world listed above that can naturally carry this concept in a story.

**entry_tier**
The minimum story complexity tier at which this concept can first be taught:
  1 — directly visible, no inference needed ("the stone is cold")
  2 — simple causality needed: because / when / so ("she waited because the dog was gone")
  3 — temporal context or multi-sentence reasoning needed ("earlier that morning... by afternoon...")
  4 — dialogue or perspective-taking required to make the concept clear

---

EXAMPLES

Input:
{"label": "anger", "domains": ["emotions_feelings"]}

Output:
{"label": "anger", "pos": ["noun", "verb"], "manifestations": ["face goes red", "hands close into fists", "voice gets loud", "turns away from the other person", "jaw is tight"], "anchors": ["child", "old lady", "door", "stone"], "entry_tier": 2}

Input:
{"label": "jump", "domains": ["movement_physical_actions"]}

Output:
{"label": "jump", "pos": ["verb", "noun"], "manifestations": ["feet leave the ground", "body rises then falls", "lands with both feet", "pushes off hard"], "anchors": ["child", "dog", "puddle", "stone"], "entry_tier": 1}

Input:
{"label": "chance", "domains": ["time_quantity"]}

Output:
{"label": "chance", "pos": ["noun"], "manifestations": ["one seed grows, the other does not", "same throw gives a different result", "outcome could not be known before it happened", "two children try the same thing, only one succeeds"], "anchors": ["seed", "stone", "rain", "game"], "entry_tier": 3}

---

Now generate schema records for the following concepts.
Return a JSON array only. No explanation. No markdown fences. No extra text.
"""


def load_env():
    env = REPO / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def api_call(batch: list[dict], api_key: str, retries: int = 2) -> list[dict]:
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content":
            PROMPT_BASE + json.dumps(batch, ensure_ascii=False, indent=2)}],
        "temperature": 0.3,
        "max_tokens": 4096,
    }).encode()
    req = urllib.request.Request(
        API_URL, data=payload,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                content = json.loads(resp.read())["choices"][0]["message"]["content"]
            text = content.strip()
            if text.startswith("```"):
                text = "\n".join(l for l in text.splitlines()
                                 if not l.startswith("```")).strip()
            return json.loads(text)
        except Exception as e:
            if attempt < retries:
                time.sleep(5 * (attempt + 1))
            else:
                raise
    return []


def worker(batches: list, api_key: str, vocab: dict, vocab_lock: threading.Lock,
           done_lock: threading.Lock, counters: dict, total: int):
    while True:
        with done_lock:
            if not batches:
                return
            batch_items = batches.pop(0)

        labels = [r["label"] for r in batch_items]
        try:
            results = api_call(batch_items, api_key)
        except Exception as e:
            print(f"  ERROR batch {labels[:3]}...: {e}")
            continue

        merged = 0
        for rec in results:
            label = rec.get("label")
            if not label:
                continue
            with vocab_lock:
                if label in vocab:
                    vocab[label].update({
                        "pos":            rec.get("pos", []),
                        "manifestations": rec.get("manifestations", []),
                        "anchors":        rec.get("anchors", []),
                        "entry_tier":     rec.get("entry_tier", 2),
                    })
                    merged += 1

        with done_lock:
            counters["done"] += len(batch_items)
            # Flush progress to disk
            with open(DONE_FILE, "a") as f:
                for lbl in labels:
                    f.write(lbl + "\n")
            pct = 100 * counters["done"] / total
            print(f"  [{counters['done']}/{total}  {pct:.1f}%] "
                  f"batch done: {labels[0]}… ({merged} merged)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch",   type=int, default=20)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--force",   action="store_true",
                    help="Regenerate even if schema already present")
    args = ap.parse_args()

    load_env()
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("Set OPENROUTER_API_KEY before running.")

    # Load vocab
    vocab = {r["label"]: r for r in
             (json.loads(l) for l in VOCAB_FILE.read_text().splitlines() if l.strip())}

    # Load already-done labels
    done: set[str] = set()
    if DONE_FILE.exists() and not args.force:
        done = set(DONE_FILE.read_text().splitlines())

    # Queue: tier=1, no schema yet (unless --force)
    pending = [
        {"label": r["label"], "domains": r["domains"][:1]}
        for r in vocab.values()
        if r["tier"] == 1
        and r["label"] not in done
        and (args.force or "manifestations" not in r)
    ]

    if not pending:
        print("Nothing to do — all Tier 1 concepts already have schemas.")
        print("Use --force to regenerate.")
        return

    # Split into batches
    batches = [pending[i:i+args.batch]
               for i in range(0, len(pending), args.batch)]

    total = len(pending)
    print(f"Concepts to process: {total} in {len(batches)} batches "
          f"({args.batch}/batch, {args.workers} workers)")

    vocab_lock  = threading.Lock()
    done_lock   = threading.Lock()
    counters    = {"done": 0}

    # Clear done file if --force
    if args.force:
        DONE_FILE.write_text("")

    threads = [
        threading.Thread(
            target=worker,
            args=(batches, api_key, vocab, vocab_lock, done_lock, counters, total),
            daemon=True,
        )
        for _ in range(args.workers)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Write updated vocab
    sorted_records = sorted(vocab.values(), key=lambda r: (r["tier"], r["label"]))
    with open(VOCAB_FILE, "w") as f:
        for r in sorted_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with_schema = sum(1 for r in vocab.values()
                      if r["tier"] == 1 and "manifestations" in r)
    print(f"\nDone. Tier-1 concepts with schema: {with_schema}/{total}")
    print(f"Updated: {VOCAB_FILE}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
classify_unsorted.py — Classify unsorted concept files into proper buckets using DeepSeek.

Usage:
  python3 meta/scripts/classify_unsorted.py classify --workers 4 --batch 50
  python3 meta/scripts/classify_unsorted.py report
  python3 meta/scripts/classify_unsorted.py apply   # move files after reviewing results

Auth: DEEPSEEK_API_KEY or OPENROUTER_API_KEY env var
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI

REPO_ROOT   = Path(__file__).resolve().parent.parent.parent
WORDS_DIR   = REPO_ROOT / "training_data" / "redesign" / "words"
UNSORTED    = WORDS_DIR / "unsorted"
RESULTS_FILE = REPO_ROOT / "tmp" / "classify_unsorted_results.jsonl"
DONE_FILE   = REPO_ROOT / "tmp" / "classify_unsorted_done.txt"

_lock = threading.Lock()

# ── Bucket definitions ────────────────────────────────────────────────────────

BUCKETS = {
    # Existing buckets
    "actions":       "Physical or intentional acts: build, take, hold, eat, throw, open, close, push, pull",
    "animals":       "Living creatures: dog, cat, bird, fish, insect, elephant, snake",
    "body":          "Parts or processes of the body: hand, eye, heart, vein, skin, heartbeat, fingerprint",
    "clothing":      "Things worn on the body: shirt, sock, mitten, coat, shoe, hat",
    "cognition":     "Mental processes and concepts: memory, attention, inference, belief, knowledge, identity",
    "colors":        "Colors and shades: red, blue, green, yellow, black, violet",
    "communication": "Acts and products of communication: instruction, message, slogan, agreement, signal, letter",
    "emotions":      "Feelings and emotional states: happiness, fear, sadness, anger, bravery, regret, jealousy",
    "food":          "Things people eat or drink: bread, apple, milk, rice, soup, almond, juice",
    "household":     "Objects found in homes: chair, table, cup, door, window, bed, vase, toilet",
    "language":      "Grammar, words, and linguistic concepts: verb, noun, paragraph, definition, conjunction, singular",
    "materials":     "Substances things are made of: wood, metal, paper, foam, glass, silver, plastic",
    "movement":      "Motion and ways of moving: spinning, gallop, departing, sliding, drifting, falling",
    "nature":        "Natural phenomena and features: river, mountain, rain, snow, fire, sky, lake, forest",
    "people":        "Human roles, types, and groups: brother, baby, gardener, actor, president, attendant",
    "places":        "Locations and spaces: subway, tunnel, orchard, forest, kitchen, hospital, city",
    "properties":    "Qualities and attributes: big, new, old, narrow, soft, bright, rough, smooth, illogical",
    "quantities":    "Measures and amounts: meter, mile, second, triple, dozen, percent",
    "shapes":        "Geometric and physical forms: circle, rectangle, layer, edge, curve, sharp",
    "social":        "Social dynamics and relationships: leadership, peace, disagreement, rudeness, assistance, offer",
    "space":         "Spatial concepts and positions: forward, edge, aisle, above, beside, center",
    "states":        "Conditions something or someone can be in: cozy, sick, poor, absent, awake, broken",
    "time":          "Time concepts and durations: recent, generation, mealtime, moment, era, deadline",
    "tools":         "Instruments, devices, vehicles: truck, television, rowboat, hammer, ladder, engine",
    # New buckets
    "sounds":        "Audible phenomena: rustle, hiss, creak, bang, whistle, thud, clatter, hum",
    "events":        "Occurrences and happenings: accident, celebration, ceremony, graduation, disaster, meeting",
    "processes":     "Multi-step operations or transformations: rendering, normalization, digestion, fermentation, compilation",
    "technology":    "Digital or technical concepts: server, password, username, virtual, software, network, algorithm",
    # Special
    "drop":          "Not a real English concept, a generation artifact, or a duplicate with no distinct meaning",
}

BUCKET_LIST = "\n".join(f"  {name}: {desc}" for name, desc in BUCKETS.items())

PROMPT_TEMPLATE = """\
You are classifying English concept words for a training corpus. Each concept has a name and a one-line description. Your task: assign each concept to exactly one bucket from the list below.

BUCKETS:
{bucket_list}

RULES:
- Choose the single best bucket. If genuinely ambiguous, pick the more specific one.
- Use "drop" only if the concept is not a real English word, is a generation artifact (e.g. "attentioning", "everydaying"), or is a meaningless duplicate.
- Do NOT use "drop" just because a word is rare or abstract.
- Output ONLY a JSON object mapping concept name → bucket name. No explanation.

CONCEPTS TO CLASSIFY:
{concepts_block}

Output format (JSON only, no markdown):
{{"concept_name": "bucket", "concept_name2": "bucket2", ...}}
"""


def load_done() -> set[str]:
    if DONE_FILE.exists():
        return set(DONE_FILE.read_text(encoding="utf-8").splitlines())
    return set()


_ANGLE_SUFFIXES = re.compile(
    r"_(what_is|meaning|example|examples|opposite|tell_me_about|boundary_\w+|"
    r"what_can\w*|what_happens\w*|what_is_ing\w*|summary|gerund|result|"
    r"who_can|behavior|capable|whatcan|whatis|can_be|can_do|"
    r"carry_\w*|close_\w*|fall_\w*|build_\w*|open_\w*)"
    r"(_rephrase)?$"
)

def _extract_concept(filename: str) -> str | None:
    """Strip angle suffix from a filename stem to get the concept name."""
    m = _ANGLE_SUFFIXES.search(filename)
    if m:
        return filename[: m.start()]
    return None


def _read_description(concept: str) -> str:
    """Read the first available angle file for a concept and return its Ninereeds answer line."""
    for f in sorted(UNSORTED.glob(f"{concept}_*.md")):
        if "_rephrase" in f.name:
            continue
        try:
            lines = f.read_text(encoding="utf-8").strip().split("\n")
            for line in lines:
                if line.startswith("[Ninereeds]"):
                    return line.replace("[Ninereeds]", "").strip()
        except Exception:
            pass
    return ""


def collect_concepts() -> list[tuple[str, str]]:
    """Return (concept_name, description) for all unclassified concepts in unsorted.

    First tries *_what_is.md; falls back to any available angle file.
    """
    done = load_done()
    seen: set[str] = set()
    concepts = []

    for f in sorted(UNSORTED.glob("*.md")):
        stem = f.stem
        concept = _extract_concept(stem)
        if concept is None:
            continue
        if concept in done or concept in seen:
            continue
        seen.add(concept)

        # Prefer what_is file for the description
        what_is = UNSORTED / f"{concept}_what_is.md"
        if what_is.exists():
            try:
                lines = what_is.read_text(encoding="utf-8").strip().split("\n")
                ans = lines[1].replace("[Ninereeds]", "").strip() if len(lines) > 1 else ""
            except Exception:
                ans = _read_description(concept)
        else:
            ans = _read_description(concept)

        concepts.append((concept, ans))
    return concepts


def classify_batch(client: OpenAI, batch: list[tuple[str, str]]) -> dict[str, str]:
    concepts_block = "\n".join(f'  "{name}": "{ans}"' for name, ans in batch)
    prompt = PROMPT_TEMPLATE.format(
        bucket_list=BUCKET_LIST,
        concepts_block=concepts_block,
    )
    resp = client.chat.completions.create(
        model=client.model,  # type: ignore[attr-defined]
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.choices[0].message.content or ""
    # Strip markdown fences if present
    raw = re.sub(r"^```json\s*|^```\s*|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    result = json.loads(raw)
    # Validate all returned buckets are known
    valid = set(BUCKETS.keys())
    cleaned = {}
    for name, bucket in result.items():
        if bucket in valid:
            cleaned[name] = bucket
        else:
            cleaned[name] = "drop"  # unknown bucket → safer to flag
    return cleaned


def cmd_classify(args: argparse.Namespace) -> None:
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY or OPENROUTER_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    use_openrouter = not os.environ.get("DEEPSEEK_API_KEY")
    base_url = "https://openrouter.ai/api/v1" if use_openrouter else "https://api.deepseek.com/v1"
    model = "deepseek/deepseek-chat-v3-0324" if use_openrouter else "deepseek-chat"

    client = OpenAI(api_key=api_key, base_url=base_url)
    client.model = model  # type: ignore[attr-defined]

    concepts = collect_concepts()
    if not concepts:
        print("Nothing to classify.")
        return

    print(f"Classifying {len(concepts)} concepts in batches of {args.batch} with {args.workers} workers...")

    batches = [concepts[i:i+args.batch] for i in range(0, len(concepts), args.batch)]

    def process_batch(batch: list[tuple[str, str]]) -> dict[str, str]:
        return classify_batch(client, batch)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(process_batch, b): b for b in batches}
        completed = 0
        for fut in as_completed(futures):
            batch = futures[fut]
            try:
                result = fut.result()
                with _lock:
                    with RESULTS_FILE.open("a", encoding="utf-8") as f:
                        for name, bucket in result.items():
                            f.write(json.dumps({"concept": name, "bucket": bucket}) + "\n")
                    with DONE_FILE.open("a", encoding="utf-8") as f:
                        for name, _ in batch:
                            f.write(name + "\n")
                completed += len(batch)
                print(f"  {completed}/{len(concepts)} done")
            except Exception as e:
                print(f"  FAIL batch starting '{batch[0][0]}': {e}", file=sys.stderr)


def cmd_report(_args: argparse.Namespace) -> None:
    if not RESULTS_FILE.exists():
        print("No results yet. Run classify first.")
        return

    from collections import Counter
    results = [json.loads(l) for l in RESULTS_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    by_bucket: Counter = Counter()
    drops = []
    for r in results:
        by_bucket[r["bucket"]] += 1
        if r["bucket"] == "drop":
            drops.append(r["concept"])

    print(f"Total classified: {len(results)}")
    print()
    for bucket, count in sorted(by_bucket.items(), key=lambda x: -x[1]):
        print(f"  {bucket:20s}  {count}")

    if drops:
        print(f"\nMarked for drop ({len(drops)}):")
        for d in sorted(drops):
            print(f"  {d}")


def cmd_apply(_args: argparse.Namespace) -> None:
    """Move files from unsorted into their assigned buckets."""
    if not RESULTS_FILE.exists():
        print("No results. Run classify first.")
        return

    results = {}
    for line in RESULTS_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            results[r["concept"]] = r["bucket"]

    moved = 0
    dropped = 0
    skipped = 0

    for concept, bucket in results.items():
        src_files = list(UNSORTED.glob(f"{concept}_*.md"))
        if not src_files:
            skipped += 1
            continue

        if bucket == "drop":
            for f in src_files:
                f.unlink()
            dropped += len(src_files)
            continue

        dest_dir = WORDS_DIR / bucket
        dest_dir.mkdir(exist_ok=True)
        for f in src_files:
            dest = dest_dir / f.name
            if dest.exists():
                # Don't overwrite existing files in target bucket
                skipped += 1
                continue
            shutil.move(str(f), str(dest))
            moved += 1

    print(f"Moved:   {moved} files")
    print(f"Dropped: {dropped} files")
    print(f"Skipped: {skipped} (already existed in target or no files found)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify unsorted concept files into buckets")
    sub = parser.add_subparsers(dest="cmd")

    c = sub.add_parser("classify")
    c.add_argument("--workers", type=int, default=4)
    c.add_argument("--batch",   type=int, default=50)

    sub.add_parser("report")
    sub.add_parser("apply")

    args = parser.parse_args()
    if args.cmd == "classify":
        cmd_classify(args)
    elif args.cmd == "report":
        cmd_report(args)
    elif args.cmd == "apply":
        cmd_apply(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

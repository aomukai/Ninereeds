#!/usr/bin/env python3
"""
story_gen_boolean.py — Boolean-teaching story generator.

Produces stories that teach yes/no discrimination through observable-state
elimination: "Is she happy? No — happy looks like X. Is she sad? Yes — sad
looks like Y." Anchors are drawn from observable domains with manifestations.

Commands:
  plan   — build job queue (800 jobs, 200 per tier)
  run    — generate stories from job queue
  status — show queue progress

Output: training_data/teaching_stories/ (same dir as story_gen_v2.py)
Tracker: tmp/story_gen_tracker.jsonl  (appended, boolean=True flag)
Jobs:    tmp/story_gen_boolean_jobs.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

_env = ROOT / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if _line.strip() and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
REMOTE_MODEL = "deepseek/deepseek-v4-flash"
MAX_TOKENS   = 32768
TEMPERATURE  = 0.85

VOCAB_FILE   = ROOT / "tmp" / "phase_vocab.jsonl"
TRACKER_FILE = ROOT / "tmp" / "story_gen_tracker.jsonl"
JOBS_FILE    = ROOT / "tmp" / "story_gen_boolean_jobs.jsonl"
OUT_DIR      = ROOT / "training_data" / "teaching_stories"
LOCK_FILE    = ROOT / "tmp" / "story_gen.lock"

STORIES_PER_TIER = 200   # 4 tiers × 200 = 800 total

# Only domains where manifestations are reliably observable in a village scene
BOOLEAN_DOMAINS = {
    "emotions_feelings",
    "movement_physical_actions",
    "sound_voice",
    "progressive_actions",
    "abstract_states",
}

TIER_DESCRIPTIONS: dict[int, str] = {
    1: ("Tier 1 — Picture-book grammar. Very short sentences (5–8 words). "
        "One idea per sentence. Simple present or simple past. No subordinate clauses."),
    2: ("Tier 2 — Picture-book grammar, slightly expanded. Short sentences. "
        "May join two clauses with 'and' or 'but'. Simple past or present."),
    3: ("Tier 3 — Early elementary grammar (1st grade). May use 'because', 'when', "
        "'then', 'so'. Cause and effect is fine."),
    4: ("Tier 4 — Elementary grammar (2nd grade). Two dialogue turns per language. "
        "May use 'although', 'until', 'after'. Still clear and direct."),
}

_write_lock   = threading.Lock()
_tracker_lock = threading.Lock()

# ---------------------------------------------------------------------------
# wordfreq
# ---------------------------------------------------------------------------
try:
    from wordfreq import zipf_frequency as _zipf_fn
    _HAS_WORDFREQ = True
except ImportError:
    _HAS_WORDFREQ = False


def zipf_score(label: str) -> float:
    if _HAS_WORDFREQ:
        try:
            return _zipf_fn(label, "en")
        except Exception:
            pass
    return 3.0


def underrep_score(label: str, n_times_used: int) -> float:
    return zipf_score(label) - math.log2(n_times_used + 1)


# ---------------------------------------------------------------------------
# Vocab
# ---------------------------------------------------------------------------

def load_vocab() -> dict[str, dict]:
    vocab: dict[str, dict] = {}
    for line in VOCAB_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        vocab[rec["label"]] = rec
    return vocab


# ---------------------------------------------------------------------------
# Candidate selection
# ---------------------------------------------------------------------------

def eligible_candidates(vocab: dict) -> list[dict]:
    """Words in boolean domains that have at least one manifestation."""
    out = []
    for r in vocab.values():
        if not r.get("manifestations"):
            continue
        domains = set(r.get("domains", []))
        if not (domains & BOOLEAN_DOMAINS):
            continue
        out.append(r)
    return out


def find_wrong_answers(anchor: dict, pool: list[dict], n: int = 2) -> list[dict]:
    """
    Find wrong-answer candidates from the same domain as anchor.
    Prefer underrepresented words so the elimination chain covers more vocab.
    """
    anchor_domains = set(anchor.get("domains", []))
    scored = []
    for r in pool:
        if r["label"] == anchor["label"]:
            continue
        if not r.get("manifestations"):
            continue
        shared = anchor_domains & set(r.get("domains", []))
        if not shared:
            continue
        score = underrep_score(r["label"], r.get("n_times_used", 0))
        scored.append((score, r["label"], r))
    scored.sort(reverse=True)
    # Pick from top candidates with some randomness so wrong answers vary
    top = scored[:max(n * 4, 10)]
    random.shuffle(top)
    return [r for _, _, r in top[:n]]


# ---------------------------------------------------------------------------
# Job queue
# ---------------------------------------------------------------------------

def build_jobs(vocab: dict) -> list[dict]:
    """
    Build 800 jobs: 200 per tier.
    Top candidates (by underrep score) get all 4 tiers.
    Lower candidates get fewer tiers.
    """
    pool = eligible_candidates(vocab)
    pool.sort(key=lambda r: underrep_score(r["label"], r.get("n_times_used", 0)),
              reverse=True)

    jobs: list[dict] = []
    job_id = 0

    for tier in range(1, 5):
        tier_candidates = pool[:STORIES_PER_TIER]
        # Shuffle slightly so tier ordering doesn't always follow the same sequence
        shuffled = tier_candidates[:]
        random.shuffle(shuffled)

        for anchor in shuffled:
            wrong = find_wrong_answers(anchor, pool)
            if not wrong:
                continue
            jobs.append({
                "id":           job_id,
                "tier":         tier,
                "anchor":       anchor["label"],
                "anchor_manifestations": anchor.get("manifestations", []),
                "wrong_words":  [w["label"] for w in wrong],
                "wrong_manifestations": [w.get("manifestations", []) for w in wrong],
                "done":         False,
            })
            job_id += 1

    return jobs


def load_jobs() -> list[dict]:
    return [json.loads(l) for l in JOBS_FILE.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def save_jobs(jobs: list[dict]):
    tmp = JOBS_FILE.with_suffix(".jsonl.tmp")
    tmp.write_text("\n".join(json.dumps(j, ensure_ascii=False) for j in jobs) + "\n",
                   encoding="utf-8")
    tmp.replace(JOBS_FILE)


def mark_done(jobs: list[dict], job_id: int):
    for j in jobs:
        if j["id"] == job_id:
            j["done"] = True
            return


# ---------------------------------------------------------------------------
# Path helpers (shared with story_gen_v2)
# ---------------------------------------------------------------------------

def safe_stem(label: str) -> str:
    return re.sub(r"[^\w\-]", "_", label).strip("_")


def unique_path(label: str) -> Path:
    stem = safe_stem(label)
    p = OUT_DIR / f"bool_{stem}.md"
    if not p.exists():
        return p
    i = 2
    while True:
        p = OUT_DIR / f"bool_{stem}_{i}.md"
        if not p.exists():
            return p
        i += 1


# ---------------------------------------------------------------------------
# Tracker append
# ---------------------------------------------------------------------------

def append_tracker(
    fname:           str,
    anchor:          str,
    words:           set[str],
    tier:            int,
    wrong_words:     list[str],
    sha256:          str,
):
    record = {
        "created_at":      datetime.now(timezone.utc).isoformat(),
        "file":            fname,
        "anchor":          anchor,
        "is_first_anchor": False,
        "tier":            tier,
        "words_present":   sorted(words),
        "support_offered": wrong_words,
        "support_found":   [w for w in wrong_words if w in words],
        "sha256":          sha256,
        "boolean":         True,
    }
    with _tracker_lock:
        with open(TRACKER_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Word scanning (EN blocks only)
# ---------------------------------------------------------------------------

_LANG_MARKERS = frozenset({"[EN]", "[DE]", "[JP]", "[ZH]"})

TIER4_EN_POSITIONS = {0, 1}


def _split_into_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.strip() in _LANG_MARKERS:
            continue
        if line.startswith("[user]") and current:
            blocks.append(current)
            current = []
        current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _block_to_text(block: list[str]) -> str:
    out = []
    for line in block:
        if line.startswith("[user]"):
            out.append(line[6:])
        elif line.startswith("[Ninereeds]"):
            out.append(line[11:])
        else:
            out.append(line)
    return " ".join(out)


def label_variants(label: str) -> list[str]:
    variants = [label.lower()]
    for art in ("a ", "an ", "the "):
        if label.lower().startswith(art):
            variants.append(label.lower()[len(art):])
    return variants


def scan_words(text: str, labels: set[str], tier: int) -> set[str]:
    blocks = _split_into_blocks(text)
    positions = TIER4_EN_POSITIONS if tier == 4 else {0}
    parts = [_block_to_text(blocks[i]) for i in positions if i < len(blocks)]
    en = " ".join(parts).lower()

    found: set[str] = set()
    for label in labels:
        for variant in label_variants(label):
            if " " in variant:
                if variant in en:
                    found.add(label)
                    break
            else:
                if re.search(r"\b" + re.escape(variant) + r"\b", en):
                    found.add(label)
                    break
    return found


# ---------------------------------------------------------------------------
# Story validation
# ---------------------------------------------------------------------------

def validate_story(text: str, tier: int) -> bool:
    expected  = 8 if tier == 4 else 4
    users     = len(re.findall(r"^\[user\]",     text, re.MULTILINE))
    ninereeds = len(re.findall(r"^\[Ninereeds\]", text, re.MULTILINE))
    return users == expected and ninereeds == expected


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def format_manifestations(mfs: list[str]) -> str:
    return "\n".join(f"  — {m}" for m in mfs) if mfs else "  — (general appearance)"


def build_prompt(job: dict) -> str:
    anchor      = job["anchor"]
    tier        = job["tier"]
    wrong_words = job["wrong_words"]
    wrong_word  = wrong_words[0]          # primary wrong answer
    anchor_mfs  = job["anchor_manifestations"]
    wrong_mfs   = job["wrong_manifestations"][0] if job["wrong_manifestations"] else []
    tier_desc   = TIER_DESCRIPTIONS[tier]

    if tier == 4:
        structure = f"""\
FORMAT — Tier 4: write exactly 8 blocks (2 turns per language), language order EN → DE → JP → ZH.
Each language block contains BOTH turns for that language before moving to the next language:
  [user] (turn 1 — wrong guess, in that language)
  [Ninereeds] (turn 1 response — starts with the word for "No")
  [user] (turn 2 — correct guess, in that language)
  [Ninereeds] (turn 2 response — starts with the word for "Yes")

Turn 1 asks whether the subject is "{wrong_word}".
[Ninereeds] answers No, explains what {wrong_word} looks like, notes the mismatch.

Turn 2 asks whether the subject is "{anchor}".
[Ninereeds] answers Yes, confirms with a manifestation, states a one-line principle."""
    else:
        structure = f"""\
FORMAT — Tiers 1–3: write exactly 4 blocks, language order EN → DE → JP → ZH.
Each block is a single [user]/[Ninereeds] pair.

The [user] asks whether the subject is "{wrong_word}" (the wrong answer).
[Ninereeds] responds:
  1. Starts with the word for "No" in that language.
  2. Explains what {wrong_word} looks like (wrong manifestation).
  3. Notes the mismatch with what is shown.
  4. Names "{anchor}" as the correct concept.
  5. Ends with one brief principle connecting the evidence to the concept."""

    return f"""\
You are writing a boolean teaching story for Ninereeds, a language-learning AI.
The story teaches yes/no discrimination through observable evidence.

TARGET CONCEPT (the correct answer): "{anchor}"
WRONG CONCEPT (to eliminate first): "{wrong_word}"

WHAT "{anchor}" LOOKS LIKE (observable manifestations):
{format_manifestations(anchor_mfs)}

WHAT "{wrong_word}" LOOKS LIKE (for contrast):
{format_manifestations(wrong_mfs)}

SCENE RULES:
- Open with 1–2 sentences placing a character in the village world showing clear evidence of "{anchor}"
- Village world: path, field, market, hedge, millpond, barn, oak tree, well, garden, doorstep
- Omniscient narrator — NO named characters. Use: "a child", "a boy", "a girl",
  "an old woman", "a man", "a dog", "a cat", "the farmer", etc.
- The scene must make "{anchor}" visually obvious and "{wrong_word}" visually impossible

COMPLEXITY: {tier_desc}

LANGUAGE RULES:
- Write EN first, then localise the SAME story into DE, JP, ZH
- Localise naturally — a native speaker must not notice it came from another language
- Localise the [user] question into each language (same question, natural phrasing)
- Yes/No localise as: EN yes/no · DE Ja/Nein · JP そうだ/そうではない · ZH 是的/不是
- JP: plain form only (行く, 見た) — never desu/masu
- ZH: Traditional Chinese characters only — never Simplified

{structure}

Each block starts with [user] on its own line, then [Ninereeds] on the next line.
Separate blocks with a single blank line. Do NOT add [EN], [DE], [JP], [ZH] label lines.

Write the story now.
"""


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------

def call_api(prompt: str, api_key: str) -> str:
    from openai import OpenAI
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    resp = client.chat.completions.create(
        model=REMOTE_MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        messages=[{"role": "user", "content": prompt}],
    )
    content = resp.choices[0].message.content
    if not content:
        raise RuntimeError("Model returned empty content")
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    if content.startswith("```"):
        content = "\n".join(l for l in content.splitlines()
                            if not l.startswith("```")).strip()
    return content


# ---------------------------------------------------------------------------
# Generate one story
# ---------------------------------------------------------------------------

def generate_one(job: dict, api_key: str, all_labels: set[str]) -> bool:
    prompt = build_prompt(job)
    tier   = job["tier"]

    for attempt in range(2):
        try:
            raw  = call_api(prompt, api_key).strip()
            text = "\n".join(line.rstrip() for line in raw.splitlines())
            if not validate_story(text, tier):
                if attempt == 0:
                    continue
                expected = 8 if tier == 4 else 4
                users = len(re.findall(r"^\[user\]", text, re.MULTILINE))
                print(f"  INVALID '{job['anchor']}' t{tier} "
                      f"(got {users} [user] blocks, expected {expected})")
                return False
            break
        except Exception as e:
            if attempt == 0:
                continue
            print(f"  FAILED '{job['anchor']}' t{tier}: {e}")
            return False

    sha   = hashlib.sha256(text.encode()).hexdigest()[:16]
    words = scan_words(text, all_labels, tier)

    with _write_lock:
        fpath = unique_path(job["anchor"])
        fpath.write_text(text + "\n", encoding="utf-8")
        fname = str(fpath.relative_to(ROOT))

    append_tracker(
        fname, job["anchor"], words, tier,
        job["wrong_words"], sha,
    )
    return True


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def acquire_lock():
    if LOCK_FILE.exists():
        pid = LOCK_FILE.read_text().strip()
        sys.exit(f"Another run is active (PID {pid}). Remove {LOCK_FILE} if stale.")
    LOCK_FILE.write_text(str(os.getpid()))


def release_lock():
    if LOCK_FILE.exists() and LOCK_FILE.read_text().strip() == str(os.getpid()):
        LOCK_FILE.unlink()


def cmd_plan(args):
    if not VOCAB_FILE.exists():
        sys.exit(f"Vocab file not found: {VOCAB_FILE}")
    vocab = load_vocab()
    jobs  = build_jobs(vocab)
    save_jobs(jobs)

    by_tier = {}
    for j in jobs:
        by_tier.setdefault(j["tier"], 0)
        by_tier[j["tier"]] += 1

    print(f"Job queue written: {JOBS_FILE}")
    print(f"Total jobs: {len(jobs)}")
    for t in sorted(by_tier):
        print(f"  Tier {t}: {by_tier[t]} stories")


def cmd_status(args):
    if not JOBS_FILE.exists():
        sys.exit("No job queue found. Run: plan")
    jobs = load_jobs()
    done  = sum(1 for j in jobs if j["done"])
    total = len(jobs)
    by_tier = {}
    for j in jobs:
        t = j["tier"]
        by_tier.setdefault(t, {"done": 0, "total": 0})
        by_tier[t]["total"] += 1
        if j["done"]:
            by_tier[t]["done"] += 1

    print(f"Progress: {done}/{total} stories done")
    for t in sorted(by_tier):
        s = by_tier[t]
        print(f"  Tier {t}: {s['done']}/{s['total']}")


def cmd_run(args):
    if not JOBS_FILE.exists():
        sys.exit("No job queue found. Run: plan first.")
    if not VOCAB_FILE.exists():
        sys.exit(f"Vocab file not found: {VOCAB_FILE}")

    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("Set OPENROUTER_API_KEY before running.")

    vocab      = load_vocab()
    all_labels = set(vocab.keys())
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    acquire_lock()
    try:
        jobs    = load_jobs()
        pending = [j for j in jobs if not j["done"]]
        print(f"Pending: {len(pending)}/{len(jobs)} jobs  |  workers: {args.workers}")

        done_count = [0]
        lock       = threading.Lock()

        def worker(job: dict):
            ok = generate_one(job, api_key, all_labels)
            if ok:
                with lock:
                    mark_done(jobs, job["id"])
                    done_count[0] += 1
                    remaining = len([j for j in jobs if not j["done"]])
                    print(f"  [{done_count[0]}/{len(pending)}] ok  "
                          f"'{job['anchor']}' t{job['tier']}  "
                          f"({remaining} remaining)")
                    # Persist every 10 completions
                    if done_count[0] % 10 == 0:
                        save_jobs(jobs)
            else:
                print(f"  SKIP '{job['anchor']}' t{job['tier']}")

        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            list(ex.map(worker, pending))

        save_jobs(jobs)
        final_done = sum(1 for j in jobs if j["done"])
        print(f"\nDone. {final_done}/{len(jobs)} stories generated.")

    finally:
        release_lock()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    ap  = argparse.ArgumentParser(description="Boolean teaching story generator.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("plan", help="Build job queue (800 jobs, 200 per tier)") \
       .set_defaults(func=cmd_plan)

    sub.add_parser("status", help="Show queue progress") \
       .set_defaults(func=cmd_status)

    p = sub.add_parser("run", help="Generate stories from job queue")
    p.add_argument("--workers", type=int, default=4)
    p.set_defaults(func=cmd_run)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

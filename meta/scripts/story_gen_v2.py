#!/usr/bin/env python3
"""
story_gen_v2.py — Teaching story generator with living list tracking.

Commands:
  run     — main loop: anchor → organic → alarm → mop-up (loops until done)
  status  — show current mode, deficits, stall counts
  tally   — recompute n_times_used from tracker; save vocab
  audit   — integrity check: orphaned files, duplicate anchors, n_times_used drift

Model: deepseek/deepseek-v4-flash (thinking model, max_tokens=32768)
Tracker: tmp/story_gen_tracker.jsonl  (append-only, one record per story)
State:   tmp/story_gen_state.json     (mode, pass_id, stall counts)
Vocab:   tmp/phase_vocab.jsonl        (n_times_used, anchor_written — derived from tracker)
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
import time
from collections import defaultdict
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
REMOTE_MODEL  = "deepseek/deepseek-v4-flash"
MAX_TOKENS    = 32768
TEMPERATURE   = 0.85

VOCAB_FILE    = ROOT / "tmp" / "phase_vocab.jsonl"
TRACKER_FILE  = ROOT / "tmp" / "story_gen_tracker.jsonl"
STATE_FILE    = ROOT / "tmp" / "story_gen_state.json"
RECEIPTS_FILE = ROOT / "tmp" / "story_gen_receipts.jsonl"
OUT_DIR       = ROOT / "training_data" / "teaching_stories"

FLOOR_TARGET    = 3
STANDARD_TARGET = 5

FLOOR_STALL_ABS    = 20
FLOOR_STALL_PCT    = 0.02
STANDARD_STALL_ABS = 50
STANDARD_STALL_PCT = 0.015
STALL_PASSES       = 2

SUPPORT_WORDS_PER_STORY = 7
CHUNK_SIZE              = 50   # tally + recompute support pool every N stories

LOCK_FILE = ROOT / "tmp" / "story_gen.lock"

_write_lock   = threading.Lock()
_tracker_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Question pools by domain type
# ---------------------------------------------------------------------------
QUESTION_POOLS: dict[str, list[str]] = {
    "physical": [
        "What does {label} look like?",
        "Where do you see {label}?",
        "Can you show me {label}?",
        "What happens with {label}?",
        "Tell me about {label}.",
    ],
    "action": [
        "What does it mean to {label}?",
        "When do people {label}?",
        "Why do people {label}?",
        "What happens when someone {label}?",
        "Who {label}?",
    ],
    "causal": [
        "Why does {label} happen?",
        "What happens when {label}?",
        "When does {label} happen?",
        "What does {label} lead to?",
        "What causes {label}?",
    ],
    "abstract": [
        "What is {label}?",
        "Can you explain {label}?",
        "What does {label} mean?",
        "How do you know when {label}?",
        "Why does {label} matter?",
    ],
    "general": [
        "Tell me about {label}.",
        "Can you tell me about {label}?",
        "What can you say about {label}?",
        "I want to learn about {label}.",
        "What is {label}?",
    ],
}

DOMAIN_POOL_MAP: dict[str, str] = {
    "movement_physical_actions": "action",
    "objects_things":            "physical",
    "animals":                   "physical",
    "nature_environment":        "physical",
    "social_interaction":        "causal",
    "emotions_feelings":         "causal",
    "cognitive_verbs":           "abstract",
    "abstract_properties":       "abstract",
    "communication_reasoning":   "abstract",
    "mathematics":               "abstract",
    "time_sequence":             "causal",
}

TIER_DESCRIPTIONS: dict[int, str] = {
    1: "Tier 1 — Simple and concrete. Short scene. One or two characters. Clear, direct language.",
    2: "Tier 2 — Moderate complexity. Two characters interact. One causal or relational element.",
    3: "Tier 3 — Richer scene. Multiple characters. Indirect or contextual usage. Some abstraction.",
    4: "Tier 4 — Full complexity. 2 turns per language (8 blocks total). Abstract or nuanced usage.",
}

# Tier-4 block layout (0-indexed): EN→DE→JP→ZH→EN→DE→JP→ZH
# English turns are at positions 0 and 4.
TIER4_EN_POSITIONS = {0, 4}

# ---------------------------------------------------------------------------
# wordfreq (lazy import with fallback)
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
# Vocab I/O  (atomic save to avoid torn writes)
# ---------------------------------------------------------------------------

def load_vocab() -> dict[str, dict]:
    vocab: dict[str, dict] = {}
    for line in VOCAB_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        rec.setdefault("n_times_used", 0)
        # tier-2 words (A/C) treated as pre-anchored
        rec.setdefault("anchor_written", rec.get("tier", 1) == 2)
        vocab[rec["label"]] = rec
    return vocab


def save_vocab(vocab: dict[str, dict]):
    tmp = VOCAB_FILE.with_suffix(".jsonl.tmp")
    lines = [json.dumps(r, ensure_ascii=False) for r in vocab.values()]
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(VOCAB_FILE)


# ---------------------------------------------------------------------------
# State I/O
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "mode":                  "anchor",
        "pass_id":               0,
        "current_tier":          1,
        "prev_floor_deficit":    None,
        "prev_standard_deficit": None,
        "floor_stall_count":     0,
        "standard_stall_count":  0,
    }


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Deficit computation
# ---------------------------------------------------------------------------

def compute_deficits(vocab: dict) -> dict:
    floor_deficit = standard_deficit = under_floor = under_standard = 0
    for r in vocab.values():
        n  = r.get("n_times_used", 0)
        fd = max(0, FLOOR_TARGET - n)
        sd = max(0, STANDARD_TARGET - n)
        floor_deficit    += fd
        standard_deficit += sd
        if fd > 0: under_floor    += 1
        if sd > 0: under_standard += 1
    return {
        "floor_deficit":    floor_deficit,
        "standard_deficit": standard_deficit,
        "under_floor":      under_floor,
        "under_standard":   under_standard,
    }


# ---------------------------------------------------------------------------
# Tally  (single source of truth: tracker → vocab)
# ---------------------------------------------------------------------------

def tally_tracker(vocab: dict) -> dict[str, int]:
    """
    Fully reconstructive tally from the tracker.
    Resets n_times_used=0 and anchor_written to the tier-based default first,
    then rebuilds both from tracker records. Tracker is the sole source of truth.
    """
    # Reset all derived fields so stale values cannot survive
    for r in vocab.values():
        r["n_times_used"] = 0
        r["anchor_written"] = (r.get("tier", 1) == 2)

    counts: dict[str, int] = defaultdict(int)
    if not TRACKER_FILE.exists():
        return dict(counts)

    for line in TRACKER_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        anchor        = rec["anchor"]
        is_first      = rec.get("is_first_anchor", False)
        counts_anchor = rec.get("counts_anchor_as_usage", False)

        # Reconstruct anchor_written from tracker records
        if is_first and anchor in vocab:
            vocab[anchor]["anchor_written"] = True

        words = set(rec.get("words_present", []))

        for word in words:
            # Skip anchor self-credit in its first dedicated story
            # (unless it's a reanchor marked to count)
            if word == anchor and is_first and not counts_anchor:
                continue
            if word in vocab:
                counts[word] += 1

    for label in vocab:
        vocab[label]["n_times_used"] = counts.get(label, 0)

    return dict(counts)


# ---------------------------------------------------------------------------
# Tracker append
# ---------------------------------------------------------------------------

def append_tracker(
    fname:             str,
    anchor:            str,
    is_first_anchor:   bool,
    words:             set[str],
    tier:              int,
    support_offered:   list[str],
    support_found:     list[str],
    sha256:            str,
    reanchor:          bool         = False,
    reanchor_reason:   str | None   = None,
    preanchor_leaks:   list[str]    | None = None,
):
    record: dict = {
        "created_at":        datetime.now(timezone.utc).isoformat(),
        "file":              fname,
        "anchor":            anchor,
        "is_first_anchor":   is_first_anchor,
        "tier":              tier,
        "words_present":     sorted(words),
        "support_offered":   support_offered,
        "support_found":     support_found,
        "sha256":            sha256,
    }
    if reanchor:
        record["reanchor"]               = True
        record["reanchor_reason"]        = reanchor_reason
        record["counts_anchor_as_usage"] = True
    if preanchor_leaks:
        record["preanchor_leaks"] = sorted(preanchor_leaks)
    with _tracker_lock:
        with open(TRACKER_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Pass receipt
# ---------------------------------------------------------------------------

def append_receipt(
    state:           dict,
    def_before:      dict,
    def_after:       dict,
    batch_size:      int,
    triggered_alarm: bool | None,
):
    receipt = {
        "pass_id":                 state["pass_id"],
        "mode":                    state["mode"],
        "batch_size":              batch_size,
        "floor_deficit_before":    def_before["floor_deficit"],
        "floor_deficit_after":     def_after["floor_deficit"],
        "floor_burn":              def_before["floor_deficit"] - def_after["floor_deficit"],
        "floor_stall_count":       state["floor_stall_count"],
        "standard_deficit_before": def_before["standard_deficit"],
        "standard_deficit_after":  def_after["standard_deficit"],
        "standard_burn":           def_before["standard_deficit"] - def_after["standard_deficit"],
        "standard_stall_count":    state["standard_stall_count"],
        "under_floor_after":       def_after["under_floor"],
        "under_standard_after":    def_after["under_standard"],
        "triggered_alarm":         triggered_alarm,
    }
    with open(RECEIPTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(receipt, ensure_ascii=False) + "\n")

    print(f"\n--- Pass {state['pass_id']} receipt ({state['mode']}) ---")
    print(f"  floor deficit:    {def_before['floor_deficit']} → {def_after['floor_deficit']}"
          f"  (burn={receipt['floor_burn']}, stall={state['floor_stall_count']})")
    print(f"  standard deficit: {def_before['standard_deficit']} → {def_after['standard_deficit']}"
          f"  (burn={receipt['standard_burn']}, stall={state['standard_stall_count']})")
    print(f"  under floor: {def_after['under_floor']}   under standard: {def_after['under_standard']}")
    if triggered_alarm:
        print("  *** ALARM: mode switch triggered ***")


# ---------------------------------------------------------------------------
# Alarm check
# ---------------------------------------------------------------------------

def check_alarm(state: dict, def_before: dict, def_after: dict) -> str | None:
    if def_after["floor_deficit"] > 0:
        burn      = def_before["floor_deficit"] - def_after["floor_deficit"]
        threshold = max(FLOOR_STALL_ABS, def_before["floor_deficit"] * FLOOR_STALL_PCT)
        if burn < threshold:
            state["floor_stall_count"] += 1
        else:
            state["floor_stall_count"] = 0
        if state["floor_stall_count"] >= STALL_PASSES:
            state["floor_stall_count"] = 0
            return "floor_mop_up"

    elif def_after["standard_deficit"] > 0:
        burn      = def_before["standard_deficit"] - def_after["standard_deficit"]
        threshold = max(STANDARD_STALL_ABS, def_before["standard_deficit"] * STANDARD_STALL_PCT)
        if burn < threshold:
            state["standard_stall_count"] += 1
        else:
            state["standard_stall_count"] = 0
        if state["standard_stall_count"] >= STALL_PASSES:
            state["standard_stall_count"] = 0
            return "standard_soft_mop_up"

    return None


# ---------------------------------------------------------------------------
# Batch size
# ---------------------------------------------------------------------------

def batch_size_for(defs: dict, mode: str) -> int:
    if mode == "anchor":
        return 400
    if defs["floor_deficit"] > 0:
        return min(400, max(50, defs["floor_deficit"] // 2))
    return min(400, max(50, defs["standard_deficit"] // 2))


# ---------------------------------------------------------------------------
# Candidate selection
# ---------------------------------------------------------------------------

def anchors_needing_first_story(vocab: dict) -> list[dict]:
    return [r for r in vocab.values()
            if r.get("tier") == 1 and not r.get("anchor_written", False)]


def select_by_underrep(
    vocab:              dict,
    n:                  int,
    exclude:            str | None = None,
    max_n_used:         int | None = None,
    anchor_written_only: bool      = False,
) -> list[dict]:
    scored = []
    for r in vocab.values():
        if r["label"] == exclude:
            continue
        n_used = r.get("n_times_used", 0)
        if max_n_used is not None and n_used >= max_n_used:
            continue
        if anchor_written_only and not r.get("anchor_written", False):
            continue
        scored.append((underrep_score(r["label"], n_used), r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:n]]


# ---------------------------------------------------------------------------
# Tier cycling
# ---------------------------------------------------------------------------

def tier_for(position: int, start_tier: int, entry_tier: int) -> int:
    """Cycle 1→2→3→4→1 from start_tier, floored at entry_tier."""
    t = (start_tier - 1 + position) % 4 + 1
    return max(t, entry_tier)


# ---------------------------------------------------------------------------
# Word scanning  (EN blocks only, tags stripped)
# ---------------------------------------------------------------------------

def label_variants(label: str) -> list[str]:
    variants = [label.lower()]
    for art in ("a ", "an ", "the "):
        if label.lower().startswith(art):
            variants.append(label.lower()[len(art):])
    return variants


_LANG_MARKERS = frozenset({"[EN]", "[DE]", "[JP]", "[ZH]"})


def _split_into_blocks(story_text: str) -> list[list[str]]:
    """Split story into [user]/[Ninereeds] blocks. Each block is a list of lines.
    Language marker lines ([EN], [DE], [JP], [ZH]) are skipped — some models add them.
    """
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in story_text.splitlines():
        if line.strip() in _LANG_MARKERS:
            continue                        # ignore language marker lines
        if line.startswith("[user]") and current:
            blocks.append(current)
            current = []
        current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _block_to_text(block: list[str]) -> str:
    """Return block content with [user] and [Ninereeds] tags stripped."""
    out = []
    for line in block:
        if line.startswith("[user]"):
            out.append(line[6:])
        elif line.startswith("[Ninereeds]"):
            out.append(line[11:])
        else:
            out.append(line)
    return " ".join(out)


def extract_en_text(story_text: str, story_tier: int) -> str:
    """Return EN block(s) lowercased, tags stripped.

    Tiers 1–3: block 0 only.
    Tier 4: blocks 0 and 4 (both English rounds in interleaved layout
            EN→DE→JP→ZH→EN→DE→JP→ZH).
    """
    blocks = _split_into_blocks(story_text)
    positions = TIER4_EN_POSITIONS if story_tier == 4 else {0}
    parts = [_block_to_text(blocks[i]) for i in positions if i < len(blocks)]
    return " ".join(parts).lower()


def scan_words(story_text: str, labels: set[str], story_tier: int) -> set[str]:
    en = extract_en_text(story_text, story_tier)
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
# Story validation  (exact block count per tier)
# ---------------------------------------------------------------------------

def validate_story(text: str, story_tier: int) -> bool:
    expected  = 8 if story_tier == 4 else 4
    users     = len(re.findall(r"^\[user\]",     text, re.MULTILINE))
    ninereeds = len(re.findall(r"^\[Ninereeds\]", text, re.MULTILINE))
    return users == expected and ninereeds == expected


# ---------------------------------------------------------------------------
# Unique output path
# ---------------------------------------------------------------------------

def safe_stem(label: str) -> str:
    return re.sub(r"[^\w\-]", "_", label).strip("_")


def unique_path(label: str) -> Path:
    stem = safe_stem(label)
    p = OUT_DIR / f"{stem}.md"
    if not p.exists():
        return p
    i = 2
    while True:
        p = OUT_DIR / f"{stem}_{i}.md"
        if not p.exists():
            return p
        i += 1


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def pick_question(record: dict) -> str:
    domains  = record.get("domains", [])
    pool_key = "general"
    for d in domains:
        if d in DOMAIN_POOL_MAP:
            pool_key = DOMAIN_POOL_MAP[d]
            break
    return random.choice(QUESTION_POOLS[pool_key]).format(label=record["label"])


def build_prompt(anchor: dict, story_tier: int, support: list[dict]) -> str:
    label    = anchor["label"]
    question = pick_question(anchor)

    concept_lines: list[str] = []
    if "manifestations" in anchor:
        concept_lines.append("Observable behaviors/examples:")
        for m in anchor["manifestations"]:
            concept_lines.append(f"  — {m}")
    if "anchors" in anchor:
        concept_lines.append("Concrete grounding words: " + ", ".join(anchor["anchors"]))
    concept_block = "\n".join(concept_lines) or "(no schema — use natural context)"

    support_list = ", ".join(r["label"] for r in support) if support else "none"
    tier_desc    = TIER_DESCRIPTIONS.get(story_tier, TIER_DESCRIPTIONS[1])
    turns        = 2 if story_tier == 4 else 1
    total_blocks = turns * 4
    tier4_note   = (
        "\nFor the second turn in each language: go deeper — show a consequence, "
        "a contrast, or a character reflecting on the concept."
        if story_tier == 4 else ""
    )

    return f"""\
You are writing a multilingual teaching story for Ninereeds, a small language-learning AI.
The story teaches the concept: "{label}"

COMPLEXITY: {tier_desc}

CONCEPT DETAILS:
{concept_block}

SUPPORT WORDS (weave these in naturally where they fit — don't force all of them):
{support_list}

OPENING QUESTION (English): "{question}"

STORY RULES:
- Open each [user] line with the question translated naturally into that language
- Do NOT start [Ninereeds] with a definition ("X is a...") — start with a scene or action
- Show observable behavior; avoid direct emotion statements ("felt happy" → show the behavior)
- Characters: Emma (curious girl), Taro (calm boy), Gran (old woman), Biscuit (cat), Bello (dog)
- Village setting: path, field, market, hedge, millpond, barn, oak tree
- Ninereeds speaks in a calm, clear, narrative voice
- JP: plain form only (行く, 見た, ではない) — never desu/masu (です/ます/でした/ました)
- ZH: Traditional Chinese characters (繁體字/台灣繁體) — never Simplified{tier4_note}

FORMAT — write exactly {total_blocks} blocks in this order: EN → DE → JP → ZH{"  (2 turns each, interleaved: EN1, DE1, JP1, ZH1, EN2, DE2, JP2, ZH2)" if story_tier == 4 else ""}
Each block starts with [user] on its own line, then [Ninereeds] (no blank line between tag and content).
Separate blocks with a single blank line. Do NOT add [EN], [DE], [JP], [ZH] language label lines.

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

def generate_one(
    anchor:          dict,
    story_tier:      int,
    api_key:         str,
    support:         list[dict],
    is_first_anchor: bool,
    all_labels:      set[str],
    reanchor:        bool            = False,
    reanchor_reason: str | None      = None,
    vocab:           dict | None     = None,
) -> bool:
    prompt = build_prompt(anchor, story_tier, support)
    support_offered = [r["label"] for r in support]

    for attempt in range(2):
        try:
            text = call_api(prompt, api_key).strip()
            if not validate_story(text, story_tier):
                expected = 8 if story_tier == 4 else 4
                users = len(re.findall(r"^\[user\]", text, re.MULTILINE))
                if attempt == 0:
                    time.sleep(3)
                    continue
                print(f"  INVALID '{anchor['label']}' (got {users} [user] blocks, expected {expected})")
                return False
            break
        except Exception as e:
            if attempt == 0:
                time.sleep(5)
                continue
            print(f"  FAILED '{anchor['label']}': {e}")
            return False

    sha = hashlib.sha256(text.encode()).hexdigest()[:16]
    words = scan_words(text, all_labels, story_tier)

    # Reanchor stories guarantee anchor credit regardless of scanner result
    if reanchor:
        words.add(anchor["label"])

    support_found = [w for w in support_offered if w in words]

    # Detect pre-anchor leakage: unintroduced tier-1 words appearing in anchor stories
    preanchor_leaks: list[str] = []
    if is_first_anchor and not reanchor and vocab is not None:
        for word in words:
            if (word != anchor["label"]
                    and vocab.get(word, {}).get("tier") == 1
                    and not vocab.get(word, {}).get("anchor_written", False)):
                preanchor_leaks.append(word)

    with _write_lock:
        fpath = unique_path(anchor["label"])
        fpath.write_text(text + "\n", encoding="utf-8")
        fname = str(fpath.relative_to(ROOT))

    append_tracker(
        fname, anchor["label"], is_first_anchor, words,
        story_tier, support_offered, support_found, sha,
        reanchor, reanchor_reason,
        preanchor_leaks if preanchor_leaks else None,
    )
    return True


# ---------------------------------------------------------------------------
# Run one chunk in parallel  (no per-worker vocab save)
# ---------------------------------------------------------------------------

def run_chunk(
    chunk:           list[dict],
    tiers:           list[int],
    api_key:         str,
    vocab:           dict,
    all_labels:      set[str],
    support_pool:    list[dict],
    is_first_fn,                       # callable(record) -> bool
    reanchor:        bool,
    reanchor_reason: str | None,
    workers:         int,
) -> int:
    """Execute chunk in parallel. Returns number of successful stories.
    Applies vocab field updates (anchor_written) after all workers finish.
    n_times_used is NOT updated here — caller must call tally_tracker afterward.
    """
    done   = [0]
    lock   = threading.Lock()
    n      = len(chunk)
    # Collect which labels to mark anchor_written after the chunk
    newly_anchored: set[str] = set()

    def worker(args: tuple):
        record, tier = args
        sup = [r for r in support_pool if r["label"] != record["label"]]
        random.shuffle(sup)
        sup      = sup[:SUPPORT_WORDS_PER_STORY]
        is_first = is_first_fn(record)
        ok       = generate_one(record, tier, api_key, sup, is_first,
                                all_labels, reanchor, reanchor_reason, vocab)
        if ok:
            with lock:
                if is_first:
                    newly_anchored.add(record["label"])
                done[0] += 1
                print(f"  [{done[0]}/{n}] ✓ {record['label']} (tier {tier})")

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(worker, zip(chunk, tiers)))

    # Apply anchor_written updates (single-threaded, all workers done)
    for label in newly_anchored:
        vocab[label]["anchor_written"] = True

    return done[0]


# ---------------------------------------------------------------------------
# Process a full batch in chunks, tallying between chunks
# ---------------------------------------------------------------------------

def run_batch_chunked(
    batch:           list[dict],
    start_tier:      int,
    api_key:         str,
    vocab:           dict,
    all_labels:      set[str],
    mode:            str,
    is_first_fn,
    reanchor:        bool,
    reanchor_reason: str | None,
    workers:         int,
) -> tuple[int, int]:
    """
    Process batch in CHUNK_SIZE slices, tallying between each chunk.
    Returns (total_successes, final_current_tier).
    Aborts early if any chunk returns zero successes.
    """
    total_ok = 0
    current_tier = start_tier

    for i in range(0, len(batch), CHUNK_SIZE):
        chunk = batch[i : i + CHUNK_SIZE]
        tiers = [tier_for(i + j, start_tier, chunk[j].get("entry_tier", 1))
                 for j in range(len(chunk))]

        # Support pool: anchor_written_only during anchor pass
        support_pool = select_by_underrep(
            vocab, 50,
            max_n_used=STANDARD_TARGET,
            anchor_written_only=(mode == "anchor"),
        )

        ok = run_chunk(chunk, tiers, api_key, vocab, all_labels, support_pool,
                       is_first_fn, reanchor, reanchor_reason, workers)
        total_ok += ok

        # Tally and save after each chunk
        tally_tracker(vocab)
        save_vocab(vocab)

        # Advance tier counter past this chunk
        current_tier = (start_tier - 1 + i + len(chunk)) % 4 + 1

        if ok == 0 and len(chunk) > 0:
            print(f"  Chunk {i // CHUNK_SIZE + 1}: zero successes. API may be down. Aborting pass.")
            break

    return total_ok, current_tier


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


def cmd_tally(args):
    vocab  = load_vocab()
    counts = tally_tracker(vocab)
    save_vocab(vocab)
    defs = compute_deficits(vocab)
    print(f"Tallied {len(counts)} tracked words.")
    print(f"Floor deficit:    {defs['floor_deficit']}  ({defs['under_floor']} words below {FLOOR_TARGET})")
    print(f"Standard deficit: {defs['standard_deficit']}  ({defs['under_standard']} words below {STANDARD_TARGET})")


def cmd_status(args):
    if not VOCAB_FILE.exists():
        sys.exit("No vocab file found.")
    vocab   = load_vocab()
    state   = load_state()
    defs    = compute_deficits(vocab)
    stories = list(OUT_DIR.glob("*.md")) if OUT_DIR.exists() else []
    n_t1    = sum(1 for r in vocab.values() if r.get("tier") == 1)
    n_anch  = sum(1 for r in vocab.values()
                  if r.get("tier") == 1 and r.get("anchor_written", False))
    print(f"Mode:              {state['mode']}")
    print(f"Pass:              {state['pass_id']}")
    print(f"Current tier:      {state['current_tier']}")
    print(f"Floor deficit:     {defs['floor_deficit']}  ({defs['under_floor']} below {FLOOR_TARGET})")
    print(f"Standard deficit:  {defs['standard_deficit']}  ({defs['under_standard']} below {STANDARD_TARGET})")
    print(f"Floor stall:       {state['floor_stall_count']}/{STALL_PASSES}")
    print(f"Standard stall:    {state['standard_stall_count']}/{STALL_PASSES}")
    print(f"Tier-1 anchored:   {n_anch}/{n_t1}")
    print(f"Stories on disk:   {len(stories)}")
    if not _HAS_WORDFREQ:
        print("WARNING: wordfreq not installed — Zipf fallback active (pip install wordfreq)")


def cmd_audit(args):
    if not VOCAB_FILE.exists():
        sys.exit("No vocab file found.")

    # Snapshot stored values BEFORE any tally (audit must not blind itself)
    stored_vocab   = load_vocab()
    stored_counts  = {label: r.get("n_times_used", 0) for label, r in stored_vocab.items()}
    stored_anchored = {label: r.get("anchor_written", False) for label, r in stored_vocab.items()}

    # Recompute into a separate fresh copy so comparison is valid
    fresh_vocab = load_vocab()
    tally_tracker(fresh_vocab)
    defs = compute_deficits(fresh_vocab)

    # --- load tracker ---
    tracker_records: list[dict] = []
    tracker_files: set[str]     = set()
    first_anchor_map: dict[str, list[str]] = {}

    if TRACKER_FILE.exists():
        for line in TRACKER_FILE.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            tracker_records.append(rec)
            tracker_files.add(rec["file"])
            if rec.get("is_first_anchor"):
                first_anchor_map.setdefault(rec["anchor"], []).append(rec["file"])

    # --- story files on disk ---
    story_files: set[str] = set()
    if OUT_DIR.exists():
        for f in OUT_DIR.glob("*.md"):
            story_files.add(str(f.relative_to(ROOT)))

    # --- checks ---
    no_tracker   = sorted(story_files - tracker_files)
    missing_file = sorted(tracker_files - story_files)
    dup_first    = {anchor: files for anchor, files in first_anchor_map.items()
                    if len(files) > 1}
    missing_anchor = [label for label, r in fresh_vocab.items()
                      if r.get("tier") == 1 and not r.get("anchor_written", False)]

    # n_times_used drift: stored vs freshly recomputed
    mismatches = [
        (label, stored_counts[label], fresh_vocab[label].get("n_times_used", 0))
        for label in stored_vocab
        if stored_counts[label] != fresh_vocab[label].get("n_times_used", 0)
    ]

    # sha256 verification: compare stored hash against actual file content
    sha_mismatches: list[tuple[str, str, str]] = []
    for rec in tracker_records:
        stored_sha = rec.get("sha256")
        if not stored_sha:
            continue
        fpath = ROOT / rec["file"]
        if fpath.exists():
            actual_sha = hashlib.sha256(
                fpath.read_text(encoding="utf-8").rstrip("\n").encode()
            ).hexdigest()[:16]
            if actual_sha != stored_sha:
                sha_mismatches.append((rec["anchor"], rec["file"], stored_sha, actual_sha))

    # pre-anchor leakage summary
    all_leaks: list[str] = []
    for rec in tracker_records:
        all_leaks.extend(rec.get("preanchor_leaks", []))

    # top overrepresented
    overrep = sorted(
        [(label, r.get("n_times_used", 0)) for label, r in fresh_vocab.items()
         if r.get("n_times_used", 0) > STANDARD_TARGET],
        key=lambda x: x[1], reverse=True,
    )

    print("=== Audit Report ===")
    print(f"Stories on disk:          {len(story_files)}")
    print(f"Tracker entries:          {len(tracker_files)}")
    print(f"Stories without tracker:  {len(no_tracker)}")
    print(f"Tracker with missing file:{len(missing_file)}")
    print(f"Duplicate first-anchors:  {len(dup_first)}")
    print(f"Tier-1 missing anchor:    {len(missing_anchor)}")
    print(f"n_times_used drift:       {len(mismatches)}")
    print(f"sha256 mismatches:        {len(sha_mismatches)}")
    print(f"Pre-anchor leak events:   {len(all_leaks)}  (distinct: {len(set(all_leaks))})")
    print(f"Words above standard:     {len(overrep)}")
    print(f"Floor deficit (fresh):    {defs['floor_deficit']}  ({defs['under_floor']} words)")
    print(f"Standard deficit (fresh): {defs['standard_deficit']}  ({defs['under_standard']} words)")

    if no_tracker:
        print(f"\nStories without tracker entry ({len(no_tracker)}):")
        for f in no_tracker[:10]:
            print(f"  {f}")
        if len(no_tracker) > 10:
            print(f"  ... and {len(no_tracker) - 10} more")

    if missing_file:
        print(f"\nTracker entries with missing files ({len(missing_file)}):")
        for f in missing_file[:10]:
            print(f"  {f}")

    if dup_first:
        print(f"\nDuplicate first-anchor stories (inspect for repeated content):")
        for anchor, files in list(dup_first.items())[:10]:
            print(f"  {anchor}: {files}")

    if mismatches[:5]:
        print(f"\nn_times_used drift (label / stored / fresh):")
        for label, stored, fresh in mismatches[:5]:
            print(f"  {label}: stored={stored} → fresh={fresh}")
        if len(mismatches) > 5:
            print(f"  ... and {len(mismatches) - 5} more")

    if sha_mismatches:
        print(f"\nsha256 mismatches (file modified after generation):")
        for anchor, fpath, stored, actual in sha_mismatches[:10]:
            print(f"  {anchor}: stored={stored} actual={actual}  ({fpath})")

    if all_leaks:
        from collections import Counter
        top_leaks = Counter(all_leaks).most_common(10)
        print(f"\nPre-anchor leaks ({len(all_leaks)} total, {len(set(all_leaks))} distinct words):")
        for word, count in top_leaks:
            print(f"  {word}: leaked in {count} anchor stories")

    if overrep[:5]:
        print(f"\nTop 5 most-seen words (above standard={STANDARD_TARGET}):")
        for label, n in overrep[:5]:
            print(f"  {label}: {n}")

    if not any([no_tracker, missing_file, dup_first, mismatches, sha_mismatches]):
        print("\nAll accounting checks passed.")


def cmd_run(args):
    if not VOCAB_FILE.exists():
        sys.exit(f"Vocab file not found: {VOCAB_FILE}")
    if not _HAS_WORDFREQ:
        print("WARNING: wordfreq not installed — install with: pip install wordfreq")

    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("Set OPENROUTER_API_KEY before running.")

    max_passes = 1 if getattr(args, "once", False) else getattr(args, "max_passes", None)

    acquire_lock()
    try:
        _cmd_run_inner(args, api_key, max_passes)
    finally:
        release_lock()


def _cmd_run_inner(args, api_key: str, max_passes: int | None):
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    vocab      = load_vocab()
    state      = load_state()
    all_labels = set(vocab.keys())
    workers    = args.workers

    # Sync fully from tracker on startup (tally_tracker resets first, so no stale data)
    if TRACKER_FILE.exists():
        print("Syncing from tracker...")
    tally_tracker(vocab)
    save_vocab(vocab)

    print(f"Mode: {state['mode']}  |  pass {state['pass_id']}  |  workers {workers}")
    if max_passes:
        print(f"Max passes: {max_passes}")
    defs = compute_deficits(vocab)
    print(f"Floor deficit: {defs['floor_deficit']}   Standard deficit: {defs['standard_deficit']}\n")
    passes_this_run = 0

    while True:
        mode = state["mode"]
        defs = compute_deficits(vocab)

        # ── DONE ──────────────────────────────────────────────────────────
        if mode == "done":
            print("All words at standard target. Generation complete.")
            break

        # ── ANCHOR PASS ───────────────────────────────────────────────────
        elif mode == "anchor":
            pending = anchors_needing_first_story(vocab)
            if not pending:
                print("All tier-1 anchors written. Switching to organic.")
                state["mode"] = "organic"
                save_state(state)
                continue

            batch = pending[:batch_size_for(defs, "anchor")]
            print(f"Anchor pass {state['pass_id']}: {len(batch)} stories  "
                  f"({len(pending)} remaining)")
            def_before = compute_deficits(vocab)

            total_ok, new_tier = run_batch_chunked(
                batch, state["current_tier"], api_key, vocab, all_labels,
                mode="anchor",
                is_first_fn=lambda r: True,
                reanchor=False, reanchor_reason=None,
                workers=workers,
            )
            state["current_tier"] = new_tier

            if total_ok == 0:
                print("Pass produced zero stories. Stopping.")
                save_state(state)
                break

            state["pass_id"] += 1
            passes_this_run += 1
            def_after = compute_deficits(vocab)
            append_receipt(state, def_before, def_after, len(batch), None)
            save_state(state)
            if max_passes and passes_this_run >= max_passes:
                print(f"Reached max-passes={max_passes}. Stopping.")
                break

        # ── ORGANIC ───────────────────────────────────────────────────────
        elif mode == "organic":
            if defs["standard_deficit"] == 0:
                print("Standard deficit is zero. Done!")
                state["mode"] = "done"
                save_state(state)
                break

            batch = select_by_underrep(vocab, batch_size_for(defs, mode),
                                       max_n_used=STANDARD_TARGET)
            if not batch:
                print("No candidates remaining. Done.")
                state["mode"] = "done"
                save_state(state)
                break

            print(f"Organic pass {state['pass_id']}: {len(batch)} stories")
            def_before = compute_deficits(vocab)

            total_ok, new_tier = run_batch_chunked(
                batch, state["current_tier"], api_key, vocab, all_labels,
                mode="organic",
                is_first_fn=lambda r: not r.get("anchor_written", False),
                reanchor=False, reanchor_reason=None,
                workers=workers,
            )
            state["current_tier"] = new_tier

            if total_ok == 0:
                print("Pass produced zero stories. Stopping.")
                save_state(state)
                break

            state["pass_id"] += 1
            passes_this_run += 1
            def_after  = compute_deficits(vocab)
            new_mode   = check_alarm(state, def_before, def_after)
            append_receipt(state, def_before, def_after, len(batch),
                           new_mode is not None)
            if new_mode:
                print(f"Alarm fired → switching to {new_mode}")
                state["mode"] = new_mode
            save_state(state)
            if max_passes and passes_this_run >= max_passes:
                print(f"Reached max-passes={max_passes}. Stopping.")
                break

        # ── FLOOR MOP-UP ──────────────────────────────────────────────────
        elif mode == "floor_mop_up":
            if defs["floor_deficit"] == 0:
                print("Floor deficit cleared. Switching back to organic.")
                state["mode"] = "organic"
                state["floor_stall_count"] = 0
                save_state(state)
                continue

            under_floor = sorted(
                [r for r in vocab.values() if r.get("n_times_used", 0) < FLOOR_TARGET],
                key=lambda r: underrep_score(r["label"], r.get("n_times_used", 0)),
                reverse=True,
            )
            batch = under_floor[:50]
            print(f"Floor mop-up pass {state['pass_id']}: {len(batch)} re-anchors  "
                  f"({len(under_floor)} words under floor)")
            def_before = compute_deficits(vocab)

            total_ok, new_tier = run_batch_chunked(
                batch, state["current_tier"], api_key, vocab, all_labels,
                mode="floor_mop_up",
                is_first_fn=lambda r: False,
                reanchor=True, reanchor_reason="floor_mop_up",
                workers=workers,
            )
            state["current_tier"] = new_tier

            if total_ok == 0:
                print("Mop-up produced zero stories. Stopping.")
                save_state(state)
                break

            state["pass_id"] += 1
            passes_this_run += 1
            def_after = compute_deficits(vocab)
            append_receipt(state, def_before, def_after, len(batch), None)

            if def_after["floor_deficit"] == 0:
                print("Floor cleared. Switching to organic.")
                state["mode"] = "organic"
                state["floor_stall_count"] = 0
            save_state(state)
            if max_passes and passes_this_run >= max_passes:
                print(f"Reached max-passes={max_passes}. Stopping.")
                break

        # ── STANDARD SOFT MOP-UP ──────────────────────────────────────────
        elif mode == "standard_soft_mop_up":
            if defs["standard_deficit"] == 0:
                state["mode"] = "done"
                save_state(state)
                break

            candidates = sorted(
                [r for r in vocab.values()
                 if FLOOR_TARGET <= r.get("n_times_used", 0) < STANDARD_TARGET],
                key=lambda r: underrep_score(r["label"], r.get("n_times_used", 0)),
                reverse=True,
            )
            if not candidates:
                state["mode"] = "done"
                save_state(state)
                break

            batch = candidates[:50]
            print(f"Standard mop-up pass {state['pass_id']}: {len(batch)} re-anchors  "
                  f"({len(candidates)} words under standard)")
            def_before = compute_deficits(vocab)

            total_ok, new_tier = run_batch_chunked(
                batch, state["current_tier"], api_key, vocab, all_labels,
                mode="standard_soft_mop_up",
                is_first_fn=lambda r: False,
                reanchor=True, reanchor_reason="standard_soft_mop_up",
                workers=workers,
            )
            state["current_tier"] = new_tier

            if total_ok == 0:
                print("Mop-up produced zero stories. Stopping.")
                save_state(state)
                break

            state["pass_id"] += 1
            passes_this_run += 1
            def_after = compute_deficits(vocab)
            append_receipt(state, def_before, def_after, len(batch), None)

            if def_after["standard_deficit"] == 0:
                state["mode"] = "done"
            save_state(state)
            if max_passes and passes_this_run >= max_passes:
                print(f"Reached max-passes={max_passes}. Stopping.")
                break

        else:
            print(f"Unknown mode: {mode!r}. Stopping.")
            break


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Teaching story generator with living list tracking."
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="Main generation loop (runs until done)")
    p.add_argument("--workers",    type=int, default=4)
    p.add_argument("--max-passes", type=int, default=None,
                   help="Stop after N passes (default: run until done)")
    p.add_argument("--once",       action="store_true",
                   help="Run exactly one pass then stop (equivalent to --max-passes 1)")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("status", help="Show mode, deficits, stall counts")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("tally", help="Recompute n_times_used from tracker and save vocab")
    p.set_defaults(func=cmd_tally)

    p = sub.add_parser("audit", help="Integrity check: orphans, duplicates, drift")
    p.set_defaults(func=cmd_audit)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

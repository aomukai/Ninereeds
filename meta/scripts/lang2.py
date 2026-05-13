#!/usr/bin/env python3
"""
Lang-2 corpus creation machine.

Phase 1 — plan:
  Reads inventory/allowlist.txt, batches words, sends to DeepSeek to enumerate
  semantic frames per word where the cross-linguistic divergence is instructive
  (i.e. DE/JP/ZH use different words for different English frames of the same word).
  Appends one job line per frame to lang_2_jobs.jsonl. Idempotent: words already
  in lang_2_planned.txt are skipped.

Phase 2 — gen:
  Reads lang_2_jobs.jsonl, skips frames whose output file already exists, batches
  the rest, generates file content via DeepSeek, and writes to lang_2/.
  Idempotent: safe to interrupt and restart at any time.

Phase 3 — report:
  Prints a progress summary without touching the API.

Usage:
  python3 meta/scripts/lang2.py plan   [--workers 4] [--batch 20] [--limit N] [--dry-run]
  python3 meta/scripts/lang2.py gen    [--workers 4] [--batch 5]  [--limit N] [--dry-run]
  python3 meta/scripts/lang2.py report

Auth (same priority as rest of project):
  1. OPENROUTER_API_KEY env var
  2. OPENAI_API_KEY env var
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT    = Path(__file__).resolve().parent.parent.parent
ALLOWLIST    = REPO_ROOT / "inventory" / "allowlist.txt"
LANG_DIR     = REPO_ROOT / "training_data" / "lang"
PLANNED_FILE = LANG_DIR / "lang_2_planned.txt"
JOBS_FILE    = LANG_DIR / "lang_2_jobs.jsonl"
OUT_DIR      = LANG_DIR / "lang_2"
BASE_URL     = "https://openrouter.ai/api/v1"
MODEL        = "deepseek/deepseek-v4-flash"

_lock = threading.Lock()


def log(msg: str) -> None:
    with _lock:
        print(msg, flush=True)


def load_api_key() -> str:
    for var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        if key := os.environ.get(var):
            return key
    return ""


# ─────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────

GLOBAL_RULES = """\
## Global rules — apply to every sentence in every language

Naturalise, don't translate.
  The goal is the same meaning expressed as a native speaker would say it.
  Surface form does not have to match across languages.

Cross-linguistic differences are features, not problems.
  When DE/JP/ZH make a different choice than English, show that choice clearly.
  Do not flatten it to make the languages look more parallel than they are.

Japanese plain form throughout. No ます/です. No keigo.
  Dictionary form or た form. Never polite forms.

German V2 word order.
  The verb is always the second constituent.
  Time adverbials trigger inversion: Gestern hat Tom ... (not Gestern Tom hat ...).
  Past tense: hat + past participle for most verbs; ist + past participle for motion/state-change.

Mandarin aspect particles.
  了 for completed action. 在 for ongoing. 会 for future intention.
  Adjective predicates: 很[ADJ] is the neutral copular form. 是[ADJ]的 is marked. Use 很.

Pronoun drop.
  Japanese and Mandarin drop subject and object pronouns when the referent is clear.
  Do not restore pronouns that the language would naturally omit.

No redundancy.
  Do not restate a noun just introduced. Use a pronoun or drop it per language rules.
  Do not restate possession that the subject already implies.

Japanese verb semantics.
  持っている = physically holding or carrying a small object (a bag, a cup, a pen).
  Animals: 飼っている. Persons in one's life: ～がいる. Static ownership: describe with adjective.
  Do not use 持っている for animals, people, or things you own but don't physically carry.

Japanese particles.
  は/が subject, を direct object, で location of action, に direction or time point, の possession.
  Never omit particles. Never add particles that don't belong.

Japanese classifiers.
  羽 (wa) birds | 匹 (hiki) small animals | 頭 (tō) large animals
  本 (hon) long thin objects | 枚 (mai) flat objects | 人 (nin) people | つ (tsu) general objects
  Do not default to つ for everything. Pick the classifier that fits the category.
  Quantity without definite reference: [NOUN][NUMBER][COUNTER].
  Specific established group: [NUMBER][COUNTER]の[NOUN].

Mandarin classifiers.
  只 (zhī) small animals, birds | 个 (gè) general, people informal
  本 (běn) books | 张 (zhāng) flat objects | 条 (tiáo) long flexible objects
  Do not default to 个 for everything.

German possessives.
  Agree with the gender and case of the noun they modify, not the owner.
  Check before writing: mein/meine/meinen/meinem etc.

Cross-person possession.
  Use Tom's bag, Kate's book — not his own bag, her own book.
  Self-possession is usually redundant. Cross-person possession is genuinely informative."""


PLAN_PROMPT_TPL = """\
For each English word below, identify the distinct semantic frames — meanings \
where German, Japanese (plain form), or Mandarin Chinese would use a DIFFERENT word \
than for another frame of the same English word.

The English word "run" is a good reference example. It has at least six frames \
(physical movement, functioning/operating, managing/leading, competing, \
liquid flow, series/sequence) and each target language uses different words for them. \
That cross-linguistic split is exactly what you are looking for.

Include a frame only if ALL THREE conditions hold:
1. The meaning is distinct enough that a German, Japanese, or Mandarin speaker \
   would choose a different word than for another frame of the same English word.
2. The frame can be demonstrated in a short, natural sentence suitable for language learners.
3. The contrast across languages is genuinely instructive — it teaches something about \
   how languages carve up meaning differently.

Skip frames that are:
- Too abstract to demonstrate in a concrete sentence
- Identical across all four languages (no useful contrast)
- Minor variants of a frame you already listed for the same word

For each frame provide:
  "desc"      — one sentence describing what this frame means
  "template"  — one of: "verb_tense" | "adj_adv" | "noun_number" | "combination"
  "note"      — one sentence on what cross-linguistic contrast this frame reveals

template guidance:
  verb_tense  — the word is being used as a verb; the file will show past / present / future
  adj_adv     — the word is an adjective used both as a predicate and as an adverb
  noun_number — the word is a concrete countable noun; the file will show singular and plural with classifiers
  combination — the frame mixes verb tense with possession, pronoun, or location

If a word has no frames worth teaching at this level, return an empty list for "frames".

Words:
{words}

Return JSON only — no commentary, no markdown fences:
{{"words": [{{"word": "...", "frames": [{{"desc": "...", "template": "...", "note": "..."}}]}}]}}"""


GEN_PROMPT_TPL = """\
Generate lang_2 training files. Each file covers one semantic frame of an English word \
and shows how that meaning is expressed naturally in English, German, Japanese (plain form), \
and Mandarin Chinese. The sentences are corpus data for a language model — they must be \
natural, grammatically correct, and cross-linguistically informative.

{rules}

## Output format

Each file contains 3 to 5 sentence groups separated by blank lines.
Each group is exactly 4 lines in order: English / German / Japanese / Mandarin.
Vary subject, tense, and object across groups to show the frame is productive.

## Template guidance

verb_tense — show past, present continuous, and future.
  Use concrete agents: dog, child, teacher, woman, boy, Tom, Kate.
  German past: hat + past participle (or ist + pp for motion / state-change).
  German present continuous: German has no continuous; use simple present.
  German future: wird + infinitive.
  Japanese past: verb た form. Ongoing: verb て + いる. Future intent: だろう or と思う.
  Mandarin: 了 completed, 在 ongoing, 会 future.

adj_adv — show the root as both a predicate adjective and a verb modifier.
  Group 1: [NOUN] is [ADJ]. (predicate use)
  Group 2: [NOUN/SUBJECT] [VERB]s [ADV]ly. (adverb use)
  Japanese adverb formation: い-adj → drop い add く; な-adj → add に.
  Mandarin adverb: [ADV]地[VERB], or bare adjective before verb for some.
  Mandarin adjective predicate: 很[ADJ] — neutral. Never 是[ADJ]的.

noun_number — show singular, then plural, with correct classifiers.
  Group 1: One [NOUN]. / Ein/Eine [NOUN_DE]. / [NOUN_JP]が一[COUNTER_JP]。/ 一[COUNTER_ZH][NOUN_ZH]。
  Group 2: Two [NOUN_PLURAL]. / Zwei [NOUN_DE_PL]. / [NOUN_JP]が二[COUNTER_JP]。/ 两[COUNTER_ZH][NOUN_ZH]。
  Add 1–2 more groups showing the noun in a short sentence context.

combination — combine verb tense with at least one of: possession, pronoun, or location.
  Use cross-person possession (Tom's bag, Kate's book) not self-possession.
  Show pronoun replacement on second mention where the language allows.

## Frames to generate

{frames}

Return JSON only — no commentary, no markdown fences:
{{"files": [{{"frame_id": "...", "groups": [["EN", "DE", "JP", "ZH"], ...]}}]}}"""


# ─────────────────────────────────────────────────────────────────
# Plan phase
# ─────────────────────────────────────────────────────────────────

def load_planned_words() -> set[str]:
    if not PLANNED_FILE.exists():
        return set()
    return {
        w.strip()
        for w in PLANNED_FILE.read_text(encoding="utf-8").splitlines()
        if w.strip()
    }


def _parse_plan_response(raw: str, words: list[str]) -> tuple[list[dict], bool]:
    """Parse a plan API response. Returns (jobs, success). success=False means retry."""
    if raw.startswith("```"):
        raw = re.sub(r"^```[^\n]*\n", "", raw)
        raw = re.sub(r"\n?```$", "", raw.strip())

    data = None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

    if data is None:
        log(f"  PLAN PARSE FAIL for {words[0]}… raw:\n{raw[:200]}")
        return [], False

    input_set = set(words)
    jobs = []
    for entry in data.get("words", []):
        word = entry.get("word", "").strip()
        if word not in input_set:
            continue
        frames = entry.get("frames", [])
        for i, frame in enumerate(frames, 1):
            fid = f"{word}_{i}"
            job = {
                "word":     word,
                "frame_id": fid,
                "desc":     frame.get("desc", "").strip(),
                "template": frame.get("template", "verb_tense").strip(),
                "note":     frame.get("note", "").strip(),
            }
            jobs.append(job)
            log(f"  FRAME {fid}: {job['desc'][:60]}")

        if not frames:
            log(f"  NO FRAMES: {word}")

    return jobs, True


def plan_batch(
    words: list[str],
    client: OpenAI,
    dry_run: bool,
) -> tuple[list[dict], bool]:
    """Send one batch to the frame-identification API.

    Returns (jobs, success). success=False means the batch should be retried —
    words will NOT be marked as planned, so they stay in the pending queue.
    """
    if dry_run:
        log(f"  [DRY-RUN] plan: {words}")
        return [], True

    prompt = PLAN_PROMPT_TPL.format(words="\n".join(f"- {w}" for w in words))

    for attempt in (1, 2):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=32768,
            )
        except Exception as e:
            log(f"  PLAN API ERROR (attempt {attempt}) for {words[0]}…: {e}")
            if attempt == 2:
                return [], False
            continue

        raw = (resp.choices[0].message.content or "").strip()
        jobs, ok = _parse_plan_response(raw, words)
        if ok:
            return jobs, True
        if attempt == 2:
            return [], False
        log(f"  Retrying batch starting with {words[0]}…")

    return [], False  # unreachable


def run_plan(args: argparse.Namespace, client: OpenAI) -> None:
    all_words = [
        w.strip()
        for w in ALLOWLIST.read_text(encoding="utf-8").splitlines()
        if w.strip() and " " not in w  # skip multi-word entries for now
    ]

    planned = load_planned_words()
    pending = [w for w in all_words if w not in planned]

    if args.limit:
        pending = pending[: args.limit]

    total = len(pending)
    if total == 0:
        print(f"Nothing to plan — all words already in {PLANNED_FILE.name}.")
        return

    print(f"Words to plan: {total}  (already planned: {len(planned)})")

    batches = [pending[i : i + args.batch] for i in range(0, total, args.batch)]
    print(f"Batches: {len(batches)}  (batch size: {args.batch})")

    LANG_DIR.mkdir(parents=True, exist_ok=True)

    total_frames = 0

    def process(batch: list[str]) -> tuple[list[dict], list[str], bool]:
        jobs, success = plan_batch(batch, client, args.dry_run)
        return jobs, batch, success

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(process, b): b for b in batches}
        for fut in as_completed(futs):
            jobs, batch, success = fut.result()
            if not args.dry_run and success:
                with _lock:
                    if jobs:
                        with JOBS_FILE.open("a", encoding="utf-8") as f:
                            for job in jobs:
                                f.write(json.dumps(job, ensure_ascii=False) + "\n")
                    with PLANNED_FILE.open("a", encoding="utf-8") as f:
                        for w in batch:
                            f.write(w + "\n")
            elif not success:
                log(f"  BATCH FAILED (not marked planned): {batch[0]}…{batch[-1]}")
            total_frames += len(jobs)

    print(f"\nDone. {total_frames} frame jobs written.")


# ─────────────────────────────────────────────────────────────────
# Gen phase
# ─────────────────────────────────────────────────────────────────

def load_jobs() -> list[dict]:
    if not JOBS_FILE.exists():
        return []
    jobs = []
    for line in JOBS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            jobs.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return jobs


def pending_jobs(jobs: list[dict]) -> list[dict]:
    seen: set[str] = set()
    pending = []
    for job in jobs:
        fid = job.get("frame_id", "")
        if not fid or fid in seen:
            continue
        seen.add(fid)
        if not (OUT_DIR / f"{fid}.md").exists():
            pending.append(job)
    return pending


def gen_batch(
    jobs: list[dict],
    client: OpenAI,
    dry_run: bool,
) -> tuple[list[str], list[str]]:
    """Generate content for a batch of frame jobs. Returns (written_ids, failed_ids)."""
    if dry_run:
        log(f"  [DRY-RUN] gen: {[j['frame_id'] for j in jobs]}")
        return [j["frame_id"] for j in jobs], []

    frames_text = "\n\n".join(
        f"frame_id: {j['frame_id']}\n"
        f"word: {j['word']}\n"
        f"template: {j['template']}\n"
        f"desc: {j['desc']}\n"
        f"note: {j['note']}"
        for j in jobs
    )

    prompt = GEN_PROMPT_TPL.format(rules=GLOBAL_RULES, frames=frames_text)

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=32768,
        )
    except Exception as e:
        log(f"  GEN API ERROR for {jobs[0]['frame_id']}…: {e}")
        return [], [j["frame_id"] for j in jobs]

    raw = (resp.choices[0].message.content or "").strip()
    tokens_in  = resp.usage.prompt_tokens     if resp.usage else "?"
    tokens_out = resp.usage.completion_tokens if resp.usage else "?"

    if raw.startswith("```"):
        raw = re.sub(r"^```[^\n]*\n", "", raw)
        raw = re.sub(r"\n?```$", "", raw.strip())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            log(f"  GEN PARSE FAIL for {jobs[0]['frame_id']}… raw:\n{raw[:200]}")
            return [], [j["frame_id"] for j in jobs]
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            log(f"  GEN PARSE FAIL (inner) for {jobs[0]['frame_id']}…")
            return [], [j["frame_id"] for j in jobs]

    expected_ids = {j["frame_id"] for j in jobs}
    written, failed = [], []

    for file_data in data.get("files", []):
        fid    = file_data.get("frame_id", "").strip()
        groups = file_data.get("groups", [])

        if not fid:
            continue

        if not (3 <= len(groups) <= 6):
            log(f"  SKIP {fid}: expected 3–6 groups, got {len(groups)}")
            failed.append(fid)
            continue

        bad = False
        for g in groups:
            if len(g) != 4 or not all(isinstance(s, str) and s.strip() for s in g):
                log(f"  SKIP {fid}: malformed group")
                bad = True
                break
        if bad:
            failed.append(fid)
            continue

        content = "\n\n".join("\n".join(g) for g in groups) + "\n"
        out_path = OUT_DIR / f"{fid}.md"
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")

        log(f"  OK {fid} ({tokens_in}→{tokens_out})")
        written.append(fid)

    returned = {f.get("frame_id", "") for f in data.get("files", [])}
    for job in jobs:
        fid = job["frame_id"]
        if fid not in returned and fid not in failed and fid not in written:
            log(f"  MISSING from response: {fid}")
            failed.append(fid)

    return written, failed


def run_gen(args: argparse.Namespace, client: OpenAI) -> None:
    jobs = load_jobs()
    if not jobs:
        print("No jobs found. Run 'plan' first.")
        return

    pending = pending_jobs(jobs)

    if args.limit:
        pending = pending[: args.limit]

    total = len(pending)
    if total == 0:
        print("Nothing to generate — all frames already have output files.")
        return

    print(f"Pending: {total} frames")

    batches = [pending[i : i + args.batch] for i in range(0, total, args.batch)]
    print(f"Batches: {len(batches)}  (batch size: {args.batch})")

    all_failed: list[str] = []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(gen_batch, b, client, args.dry_run): b for b in batches}
        for fut in as_completed(futs):
            _, failed = fut.result()
            all_failed.extend(failed)

    done = total - len(all_failed)
    print(f"\nDone: {done}/{total} written. Failed: {len(all_failed)}")
    if all_failed:
        print("Failed:", all_failed[:20])


# ─────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────

def run_report() -> None:
    all_words = [
        w.strip()
        for w in ALLOWLIST.read_text(encoding="utf-8").splitlines()
        if w.strip() and " " not in w
    ]

    planned_words = load_planned_words()
    unplanned     = len(all_words) - len(planned_words)

    jobs = load_jobs()

    # Deduplicate jobs by frame_id (keep first occurrence)
    seen: dict[str, dict] = {}
    for job in jobs:
        fid = job.get("frame_id", "")
        if fid and fid not in seen:
            seen[fid] = job

    generatable = len(seen)
    done = sum(1 for j in seen.values() if (OUT_DIR / f"{j['frame_id']}.md").exists())
    remaining   = generatable - done

    print(f"Allowlist words (single-word): {len(all_words)}")
    print(f"  Planned:   {len(planned_words)}")
    print(f"  Unplanned: {unplanned}")
    print()
    print(f"Frames identified: {generatable}")
    print(f"Files generated:   {done}")
    print(f"Files remaining:   {remaining}")

    if generatable > 0:
        print(f"Progress:          {done / generatable * 100:.1f}%")

    if seen:
        templates: dict[str, list[int]] = {}
        for j in seen.values():
            t = j.get("template", "unknown")
            if t not in templates:
                templates[t] = [0, 0]
            templates[t][1] += 1
            if (OUT_DIR / f"{j['frame_id']}.md").exists():
                templates[t][0] += 1

        print()
        print("By template:")
        for t, (d, n) in sorted(templates.items()):
            print(f"  {t:<15}  {d:>4} / {n}")


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Lang-2 corpus creation machine")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="Identify semantic frames per word")
    p_plan.add_argument("--workers", type=int, default=4)
    p_plan.add_argument("--batch",   type=int, default=20,
                        help="Words per API call (default 20)")
    p_plan.add_argument("--limit",   type=int, default=0,
                        help="Max words to plan this run (0=all pending)")
    p_plan.add_argument("--dry-run", action="store_true")

    p_gen = sub.add_parser("gen", help="Generate file content per frame")
    p_gen.add_argument("--workers", type=int, default=4)
    p_gen.add_argument("--batch",   type=int, default=5,
                       help="Frames per API call (default 5)")
    p_gen.add_argument("--limit",   type=int, default=0,
                       help="Max frames to generate this run (0=all pending)")
    p_gen.add_argument("--dry-run", action="store_true")

    sub.add_parser("report", help="Show progress summary")

    args = parser.parse_args()

    if args.cmd == "report":
        run_report()
        return

    api_key = load_api_key()
    if not api_key:
        print("ERROR: set OPENROUTER_API_KEY or OPENAI_API_KEY", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    if args.cmd == "plan":
        run_plan(args, client)
    elif args.cmd == "gen":
        run_gen(args, client)


if __name__ == "__main__":
    main()

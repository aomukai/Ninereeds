#!/usr/bin/env python3
"""
Lang-3c corpus creation machine — reflexive and benefactive frames.

Phase 1 — plan:
  Reads training_data/lang/lang_3c_verbs.txt, batches verbs, sends to DeepSeek
  to identify which of three patterns apply per verb (reflexive,
  agentive_benefactive, receptive_benefactive).
  Appends one job per applicable frame to lang_3_jobs.jsonl.
  Idempotent: verbs already in lang_3_planned.txt are skipped.

Phase 2 — gen:
  Reads lang_3_jobs.jsonl, skips frames whose output file already exists,
  batches the rest, generates file content via DeepSeek, writes to lang_3/.
  Idempotent: safe to interrupt and restart.

Phase 3 — report:
  Prints a progress summary without touching the API.

Usage:
  python3 meta/scripts/lang3c.py plan   [--workers 4] [--batch 10] [--limit N] [--dry-run]
  python3 meta/scripts/lang3c.py gen    [--workers 4] [--batch 5]  [--limit N] [--dry-run]
  python3 meta/scripts/lang3c.py report

Auth:
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
LANG_DIR     = REPO_ROOT / "training_data" / "lang"
VERB_LIST    = LANG_DIR / "lang_3c_verbs.txt"
PLANNED_FILE = LANG_DIR / "lang_3_planned.txt"
JOBS_FILE    = LANG_DIR / "lang_3_jobs.jsonl"
OUT_DIR      = LANG_DIR / "lang_3"
BASE_URL     = "https://openrouter.ai/api/v1"
MODEL        = "deepseek/deepseek-v4-flash"

_lock = threading.Lock()

PATTERNS = ("reflexive", "agentive_benefactive", "receptive_benefactive")

PATTERN_SUFFIXES = {
    "reflexive":             "reflexive",
    "agentive_benefactive":  "agentive",
    "receptive_benefactive": "receptive",
}


def log(msg: str) -> None:
    with _lock:
        print(msg, flush=True)


def load_api_key() -> str:
    for var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        if key := os.environ.get(var):
            return key
    return ""


def load_verb_list() -> list[str]:
    lines = VERB_LIST.read_text(encoding="utf-8").splitlines()
    verbs = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        word = line.split()[0].strip()  # strip trailing [*] markers
        if word and word not in verbs:
            verbs.append(word)
    return verbs


# ─────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────

GLOBAL_RULES = """\
## Global rules — apply to every sentence in every language

Naturalise, don't translate.
  The goal is the same meaning expressed as a native speaker would say it.
  Surface form does not have to match across languages.

Cross-linguistic differences are features, not problems.
  When DE/JP/ZH make a different choice than English, show it clearly.
  Do not flatten it to make the languages look more parallel than they are.

Japanese plain form throughout. No ます/です. No keigo.
  Dictionary form or た form. Never polite forms.

German V2 word order.
  The verb is always the second constituent.
  Time adverbials trigger inversion: Gestern hat Tom... (not Gestern Tom hat...).
  Reflexive pronoun sich follows the inflected verb: Er wäscht sich.

Mandarin aspect particles.
  了 for completed action. 在 for ongoing. 会 for future intention.

Pronoun drop.
  Japanese and Mandarin drop subject and object pronouns when the referent is clear.
  Do not restore pronouns the language would naturally omit.

Japanese て-form auxiliaries for benefactive direction.
  てあげる — agent gives the benefit outward to someone else. Never to the first person.
  てくれる — someone gives the benefit inward to the agent (or agent's in-group).
  てもらう — agent receives the benefit; someone does X for the agent.
  The verb before て is the main action verb. The auxiliary encodes who benefits.

Japanese reflexive body-part construction.
  身体部位 (body parts): use [body part]を + verb rather than 自分を.
  顔を洗う (wash one's face), 髪を切る (cut one's hair), 歯を磨く (brush one's teeth).
  自分 only when contrast or emphasis is needed (自分でやる — do it oneself).

Mandarin role markers.
  给 + recipient before the main verb: 给她做饭 (cook for her).
  让 + doer + verb: 让她来 (have/let her come), 让他修好了 (had him fix it).
  自己 for reflexive: 洗自己 (wash oneself); often dropped when clear.

Vary subjects across groups: Tom, Kate, the child, the teacher, she, he, they.
Do not explain grammar inside the generated files."""


PLAN_PROMPT_TPL = """\
For each English verb below, identify which of these three patterns apply.
A verb may yield 1, 2, or 3 jobs depending on how many patterns are genuinely productive.

Patterns:

1. reflexive
   The agent acts on themselves. German uses sich (accusative for most verbs; dative for
   body-part verbs: sich die Hände waschen). Japanese typically uses the body part as object
   (顔を洗う) or drops the object; 自分 only for contrast. Mandarin uses 自己 or drops it.
   Include this pattern only if the verb is naturally used reflexively in all four languages.

2. agentive_benefactive
   The agent does X for someone else's benefit. German: dative NP or für + accusative.
   Japanese: [VERB て]あげる. Mandarin: 给 + recipient + verb.
   English: "[VERB] for [recipient]."
   Include this pattern only if the verb has a clear, natural benefactive use.

3. receptive_benefactive
   Someone does X for the agent, or the agent has X done by someone.
   German: lassen + infinitive, or dative of interest.
   Japanese: [VERB て]もらう (agent receives benefit) or [VERB て]くれる (someone gives benefit to agent).
   Mandarin: 让 + doer + verb.
   English: "have [someone] do X" or "[someone] does X for me."
   Include this pattern only if it is a natural and instructive use of the verb.

For each applicable pattern, provide:
  "pattern"  — one of: "reflexive" | "agentive_benefactive" | "receptive_benefactive"
  "desc"     — one sentence describing the specific use in this pattern
  "note"     — one sentence on the key cross-linguistic contrast this pattern reveals for this verb

If a pattern is not applicable to a verb (unnatural or trivially identical across languages), omit it.

Verbs:
{verbs}

Return JSON only — no commentary, no markdown fences:
{{"verbs": [{{"verb": "...", "frames": [{{"pattern": "...", "desc": "...", "note": "..."}}]}}]}}"""


GEN_PROMPT_TPL = """\
Generate lang_3c training files. Each file covers one verb in one argument-flow pattern
and shows how that construction is expressed naturally in English, German, Japanese (plain form),
and Mandarin Chinese. The sentences are corpus data for a language model — they must be
natural, grammatically correct, and cross-linguistically informative.

{rules}

## Output format

Each file contains 3 to 5 sentence groups separated by blank lines.
Each group is exactly 4 lines in order: English / German / Japanese / Mandarin.
Vary subject, tense, and participants across groups to show the pattern is productive.

## Pattern-specific generation rules

reflexive:
  German: sich in accusative position for most verbs (sich waschen, sich erinnern).
    Dative sich for body-part verbs: sich die Hände waschen (wash one's hands).
  Japanese: use the body part as direct object where natural (顔を洗う, 髪を切る).
    Drop the reflexive object when it is obviously the agent's own body.
    Use 自分 only when contrast or emphasis is needed.
  Mandarin: 自己 for the reflexive object when needed; drop when the referent is obvious.
  English: "himself / herself / themselves" for clarity; often just the verb alone.
  Vary tense: past (た / 了 / hat gesehen), present/ongoing (ている / 在 / present), future (だろう / 会 / wird).

agentive_benefactive (doing X for someone else):
  German: dative NP for the recipient (ihr, dem Kind) or für + accusative NP.
    The verb itself does not change — only the dative NP shows the beneficiary.
  Japanese: [VERB て]あげる. The action verb comes first in て form; あげる is the auxiliary.
    Never use あげる when the recipient is the speaker or in-group — use くれる for that.
  Mandarin: 给 + recipient appears before the main verb. 给她做饭 — give-her cook-food.
  English: "[verb] for [recipient]" — no morphological marking.
  Vary IO: pronoun (her, him, them) in some groups; NP (the child, the teacher) in others.

receptive_benefactive (having X done / someone does X for the agent):
  German: lassen + infinitive for "have someone do X". Dative of interest for softer cases.
  Japanese:
    てもらう — the subject/agent receives the benefit. 彼女に直してもらった (I had her fix it).
    てくれる — someone performs the action for the benefit of the agent. 直してくれた (she fixed it for me).
    Distinguish: もらう centres on the agent's receiving; くれる centres on the other's giving.
  Mandarin: 让 + doer + verb for "have/let someone do X". 让她来 / 让他修好了.
  English: "have [someone] do X" or "[someone] does X for [agent]" — no grammatical marking.

## Frames to generate

{frames}

Return JSON only — no commentary, no markdown fences:
{{"files": [{{"frame_id": "...", "groups": [["EN", "DE", "JP", "ZH"], ...]}}]}}"""


# ─────────────────────────────────────────────────────────────────
# Plan phase
# ─────────────────────────────────────────────────────────────────

def load_planned_verbs() -> set[str]:
    if not PLANNED_FILE.exists():
        return set()
    return {
        w.strip()
        for w in PLANNED_FILE.read_text(encoding="utf-8").splitlines()
        if w.strip()
    }


def _parse_plan_response(raw: str, verbs: list[str]) -> tuple[list[dict], bool]:
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
        log(f"  PLAN PARSE FAIL for {verbs[0]}… raw:\n{raw[:200]}")
        return [], False

    input_set = set(verbs)
    jobs = []
    for entry in data.get("verbs", []):
        verb = entry.get("verb", "").strip()
        if verb not in input_set:
            continue
        frames = entry.get("frames", [])
        for frame in frames:
            pattern = frame.get("pattern", "").strip()
            if pattern not in PATTERNS:
                log(f"  SKIP unknown pattern '{pattern}' for {verb}")
                continue
            suffix = PATTERN_SUFFIXES[pattern]
            fid = f"{verb}_{suffix}"
            job = {
                "word":     verb,
                "frame_id": fid,
                "pattern":  pattern,
                "desc":     frame.get("desc", "").strip(),
                "note":     frame.get("note", "").strip(),
            }
            jobs.append(job)
            log(f"  FRAME {fid}: {job['desc'][:60]}")

        if not frames:
            log(f"  NO FRAMES: {verb}")

    return jobs, True


def plan_batch(
    verbs: list[str],
    client: OpenAI,
    dry_run: bool,
) -> tuple[list[dict], bool]:
    if dry_run:
        log(f"  [DRY-RUN] plan: {verbs}")
        return [], True

    prompt = PLAN_PROMPT_TPL.format(verbs="\n".join(f"- {v}" for v in verbs))

    for attempt in (1, 2):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=32768,
            )
        except Exception as e:
            log(f"  PLAN API ERROR (attempt {attempt}) for {verbs[0]}…: {e}")
            if attempt == 2:
                return [], False
            continue

        raw = (resp.choices[0].message.content or "").strip()
        jobs, ok = _parse_plan_response(raw, verbs)
        if ok:
            return jobs, True
        if attempt == 2:
            return [], False
        log(f"  Retrying batch starting with {verbs[0]}…")

    return [], False


def run_plan(args: argparse.Namespace, client: OpenAI) -> None:
    all_verbs = load_verb_list()
    planned   = load_planned_verbs()
    pending   = [v for v in all_verbs if v not in planned]

    if args.limit:
        pending = pending[: args.limit]

    total = len(pending)
    if total == 0:
        print(f"Nothing to plan — all verbs already in {PLANNED_FILE.name}.")
        return

    print(f"Verbs to plan: {total}  (already planned: {len(planned)})")

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
                        for v in batch:
                            f.write(v + "\n")
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
    if dry_run:
        log(f"  [DRY-RUN] gen: {[j['frame_id'] for j in jobs]}")
        return [j["frame_id"] for j in jobs], []

    frames_text = "\n\n".join(
        f"frame_id: {j['frame_id']}\n"
        f"word: {j['word']}\n"
        f"pattern: {j['pattern']}\n"
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
    all_verbs = load_verb_list()
    planned   = load_planned_verbs()
    unplanned = len(all_verbs) - len(planned)

    jobs = load_jobs()

    seen: dict[str, dict] = {}
    for job in jobs:
        fid = job.get("frame_id", "")
        if fid and fid not in seen:
            seen[fid] = job

    generatable = len(seen)
    done        = sum(1 for j in seen.values() if (OUT_DIR / f"{j['frame_id']}.md").exists())
    remaining   = generatable - done

    print(f"Verb list: {len(all_verbs)}")
    print(f"  Planned:   {len(planned)}")
    print(f"  Unplanned: {unplanned}")
    print()
    print(f"Frames identified: {generatable}")
    print(f"Files generated:   {done}")
    print(f"Files remaining:   {remaining}")

    if generatable > 0:
        print(f"Progress:          {done / generatable * 100:.1f}%")

    if seen:
        patterns: dict[str, list[int]] = {}
        for j in seen.values():
            p = j.get("pattern", "unknown")
            if p not in patterns:
                patterns[p] = [0, 0]
            patterns[p][1] += 1
            if (OUT_DIR / f"{j['frame_id']}.md").exists():
                patterns[p][0] += 1

        print()
        print("By pattern:")
        for p, (d, n) in sorted(patterns.items()):
            print(f"  {p:<25}  {d:>4} / {n}")


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Lang-3c corpus creation machine")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="Identify patterns per verb")
    p_plan.add_argument("--workers", type=int, default=4)
    p_plan.add_argument("--batch",   type=int, default=10,
                        help="Verbs per API call (default 10)")
    p_plan.add_argument("--limit",   type=int, default=0,
                        help="Max verbs to plan this run (0=all pending)")
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

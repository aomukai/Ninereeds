#!/usr/bin/env python3
"""
Lang-3d corpus generation — tiny parallel stories.

Phase 1 — plan:
  Generate scene outlines (setting, actors, objects, 6-sentence English arc,
  required Level-3 constructions). Appends to lang_3d_plans.jsonl. Idempotent.

Phase 2 — gen:
  For each planned scene without an output file, generate the full EN/DE/JP/ZH
  parallel story and write to lang_3d/. Idempotent: safe to interrupt and restart.

Phase 3 — report:
  Show progress, setting distribution, construction coverage.

Usage:
  python3 meta/scripts/lang3d.py plan  [--target 400] [--workers 4] [--batch 20] [--dry-run]
  python3 meta/scripts/lang3d.py gen   [--workers 4] [--limit N] [--dry-run]
  python3 meta/scripts/lang3d.py report

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
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT  = Path(__file__).resolve().parent.parent.parent
LANG_DIR   = REPO_ROOT / "training_data" / "lang"
PLANS_FILE = LANG_DIR / "lang_3d_plans.jsonl"
OUT_DIR    = LANG_DIR / "lang_3d"
BASE_URL   = "https://openrouter.ai/api/v1"
MODEL      = "deepseek/deepseek-v4-flash"

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
# Plans
# ─────────────────────────────────────────────────────────────────

def load_plans() -> list[dict]:
    if not PLANS_FILE.exists():
        return []
    plans = []
    for line in PLANS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                plans.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return plans


def next_story_num(plans: list[dict]) -> int:
    if not plans:
        return 1
    return max(p.get("num", 0) for p in plans) + 1


# ─────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────

PLAN_PROMPT_TPL = """\
Generate {batch_size} distinct scene plans for a multilingual language-learning corpus.

Each scene is a tiny story (6-10 sentences) about an ordinary everyday event.
The story will be told in parallel in English, German, Japanese, and Mandarin.
It must use at least 2 of the Level-3 grammar constructions listed below.

## Level-3 constructions

dative_double_object   — "Tom gives her an apple"        (IO before DO, no preposition)
dative_prepositional   — "Tom gives an apple to her"     (DO before IO, "to" marks recipient)
dative_genitive        — "Tom gives her the dog's ball"  (dative IO + genitive possessor on DO)
reflexive              — "Kate washes herself"           (agent acts on themselves)
agentive_benefactive   — "Tom cooked for Kate"           (agent does X for someone's benefit)
receptive_benefactive  — "Kate had Tom fix it"           (agent has X done for them)

## Vocabulary to draw from

Actors (2-3 per scene):
  Tom, Kate, the child, the teacher, the woman, the man, the neighbor, the student, the dog, the cat

Settings (vary across scenes):
  kitchen, bedroom, office, classroom, garden, park, shop, library, hospital,
  train station, restaurant, living room, bathroom, market, farm, workshop, school

Objects (2-4 per scene, concrete and common):
  book, letter, soup, bowl, pen, key, bag, flower, apple, knife, map, phone,
  message, ticket, coin, package, towel, medicine, food, toy, hat, report,
  photo, water, bread, cup, chair, tool, clothes, dish, glass, box, card

## Scene arc

S1: Introduce actors and situation concretely
S2: Someone needs, has, or finds something
S3: A dative transfer event (give / send / show / bring / hand / sell / lend / write / whisper / etc.)
S4: A reflexive or benefactive action
S5: A possession or genitive relation, or an intermediate step
S6+: Resolution — may extend to S8 as needed; keep it concrete

## Variety rules

Across the {batch_size} scenes in this batch:
- Vary settings, actor pairs, objects, and constructions
- No two scenes with the same setting + actor pair + core transfer event
- Include at least one reflexive or benefactive construction per scene
- Include at least one dative transfer per scene

## Output

Return JSON only — no commentary, no markdown fences:
{{"scenes": [
  {{
    "scene": "kitchen",
    "actors": ["Kate", "the child"],
    "objects": ["soup", "bowl"],
    "constructions": ["dative_double_object", "reflexive"],
    "outline": [
      "Kate is in the kitchen making soup.",
      "The child is hungry and asks for food.",
      "Kate gives the child a bowl of soup.",
      "The child washes their hands before eating.",
      "The bowl is Kate's favourite bowl.",
      "The child eats and feels better."
    ]
  }}
]}}"""


GLOBAL_RULES = """\
## Global rules

Naturalise, don't translate.
  The goal is the same meaning expressed as a native speaker would say it.
  Sentence structure may differ across languages when naturalness requires it.

Japanese plain form throughout. No desu/masu. No keigo.
  Past: verb-ta form. Ongoing: verb-te iru. Future intent: darou / to omou.
  CRITICAL: Japanese lines MUST be written in Japanese script (kanji + hiragana + katakana).
  NEVER use romaji (romanized Japanese). If you write Roman letters for Japanese, it is wrong.

German Perfekt for past narration: hat + past participle (sein + pp for motion/state-change).
German V2 word order: the verb is always the second constituent.
German grammatical gender: das Kind takes es (not er/sie), die Frau takes sie, der Mann takes er.

Mandarin: le for completed action, zai for ongoing, hui for future intent.
No tense morphology — time is shown through particles and context.

Pronoun drop: Japanese and Mandarin omit subject/object pronouns when the referent is clear.
Vary subjects naturally across sentences. Use pronouns or drop them as the language allows.

All sentences must be short and concrete. No metaphors. No literary prose."""


CONSTRUCTION_RULES = """\
## Construction rules

dative_double_object:
  EN: SUBJ VERB IO DO  (IO before DO, no preposition — "Tom gives her an apple")
  DE: dative case on IO, accusative on DO; same sentence for both EN word orders
  JP: IO-ni + DO-wo + verb  (ageru outward / kureru to speaker / morau agent receives)
  ZH: gei + IO + VERB + DO  (verb-specific: gei ta kan, gei ta jiang, gei haizi duan shang)

dative_prepositional:
  EN: SUBJ VERB DO to IO  (DO before IO, "to" marks recipient — "Tom gives an apple to her")
  DE: IDENTICAL to double_object — German has no "to" prepositional dative for these verbs
  JP: IDENTICAL to double_object — ni already marks the recipient unambiguously
  ZH: ba + DO + gei + IO  (topicalises the DO; natural when DO is definite)

dative_genitive:
  EN: SUBJ VERB IO POSS-apostrophe-s DO  ("Tom gives her the dog's ball")
  DE: four case-marked NPs in one clause — nominative subject, dative IO, accusative DO, genitive possessor
      Word order: SUBJ VERB IO(dat) DO(acc) POSS(gen)  e.g. "Er gibt dem Kind den Ball des Hundes."
  JP: IO-ni + POSS-no-DO-wo + verb  e.g. "Kare wa kodomo ni inu no booru wo ageta."
  ZH: gei + IO + POSS-de-DO  or  ba + POSS-de-DO + gei + IO

reflexive:
  EN: "Kate washes herself" — explicit reflexive object optional
  DE: sich (accusative for most verbs; dative for body-part verbs: sich die Haende waschen)
  JP: body part as object where natural (kao wo arau, kami wo kiru); jibun only for emphasis
  ZH: ziji or body part as object; drop when obvious from context

agentive_benefactive:
  EN: "Tom cooked for Kate" — no grammatical marking on the verb
  DE: dative NP for recipient, or fuer + accusative NP
  JP: VERB-te-ageru — encodes outward benefit; NEVER use ageru when the recipient is the speaker
  ZH: gei + recipient + VERB + DO  e.g. "gei ta zuo fan"

receptive_benefactive:
  EN: "Kate had Tom fix it" or "Tom fixed it for Kate"
  DE: lassen + infinitive, or dative of interest
  JP: VERB-te-morau (agent receives benefit) or VERB-te-kureru (someone gives benefit to agent)
  ZH: rang + doer + VERB  e.g. "rang ta lai xiu"

## German case reference

Dative pronouns: mir (me), dir (you), ihm (him), ihr (her), uns (us), ihnen (them)
Dative NPs: dem Kind (neut), der Frau (fem), dem Mann (masc), den Kindern (pl), dem Hund (masc)
Genitive NPs: des Kindes, der Frau, des Hundes, der Katze, der Lehrerin, des Mannes
Accusative articles: einen/eine/ein (indefinite masc/fem/neut), den/die/das (definite)

## Japanese te-form auxiliaries

te-ageru: agent gives benefit outward (not to speaker or in-group)
te-kureru: someone gives benefit inward to the agent or in-group
te-morau: agent is subject, receives benefit from someone
Never use te-ageru when the recipient is the first person."""


GEN_PROMPT_TPL = """\
Generate a short parallel story in English, German, Japanese (Japanese script only — kanji/hiragana/katakana, NO romaji), and Mandarin.
This is a language-learning corpus file — naturalness and grammatical accuracy are both required.

{global_rules}

{construction_rules}

## Story to generate

story_id: {story_id}
scene: {scene}
actors: {actors}
objects: {objects}
required constructions (include ALL of these naturally in the story):
{constructions}

Sentence outline (expand each step into one or two full sentences):
{outline}

## Format

Produce 6-10 sentence groups separated by blank lines.
Each group: exactly 4 lines in order — English / German / Japanese / Mandarin.
No headers. No labels. No grammar commentary inside the story.
All sentences short, concrete, and free of metaphor.

Return JSON only — no commentary, no markdown fences:
{{"story_id": "{story_id}", "groups": [["EN line", "DE line", "JP line", "ZH line"], ...]}}"""


# ─────────────────────────────────────────────────────────────────
# Plan phase
# ─────────────────────────────────────────────────────────────────

def _parse_plan_response(raw: str) -> tuple[list[dict], bool]:
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
        log(f"  PLAN PARSE FAIL raw:\n{raw[:200]}")
        return [], False

    scenes = []
    for s in data.get("scenes", []):
        if not all(k in s for k in ("scene", "actors", "objects", "constructions", "outline")):
            log("  PLAN SKIP: missing fields")
            continue
        if not isinstance(s["outline"], list) or len(s["outline"]) < 4:
            log("  PLAN SKIP: outline too short")
            continue
        scenes.append({
            "scene":         s["scene"],
            "actors":        s["actors"],
            "objects":       s["objects"],
            "constructions": s["constructions"],
            "outline":       s["outline"],
        })

    return scenes, True


def plan_batch_api(batch_size: int, client: OpenAI, dry_run: bool) -> tuple[list[dict], bool]:
    if dry_run:
        log(f"  [DRY-RUN] plan batch of {batch_size}")
        return [], True

    prompt = PLAN_PROMPT_TPL.format(batch_size=batch_size)

    for attempt in (1, 2):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=32768,
            )
        except Exception as e:
            log(f"  PLAN API ERROR (attempt {attempt}): {e}")
            if attempt == 2:
                return [], False
            continue

        raw = (resp.choices[0].message.content or "").strip()
        scenes, ok = _parse_plan_response(raw)
        if ok:
            return scenes, True
        if attempt == 2:
            return [], False
        log("  Retrying plan batch…")

    return [], False


def run_plan(args: argparse.Namespace, client: OpenAI) -> None:
    existing = load_plans()
    have     = len(existing)
    needed   = max(0, args.target - have)

    if needed == 0:
        print(f"Already have {have} plans — target {args.target} met.")
        return

    print(f"Have {have} plans, target {args.target}, generating {needed} more.")

    batches: list[int] = []
    remaining = needed
    while remaining > 0:
        bs = min(args.batch, remaining)
        batches.append(bs)
        remaining -= bs

    print(f"Batches: {len(batches)}  (batch size: {args.batch})")

    LANG_DIR.mkdir(parents=True, exist_ok=True)

    counter = [next_story_num(existing)]
    total_written = 0

    def process(bs: int) -> tuple[list[dict], bool]:
        return plan_batch_api(bs, client, args.dry_run)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(process, bs) for bs in batches]
        for fut in as_completed(futs):
            scenes, ok = fut.result()
            if not ok or not scenes:
                log("  PLAN BATCH FAILED or empty")
                continue
            with _lock:
                if not args.dry_run:
                    with PLANS_FILE.open("a", encoding="utf-8") as f:
                        for s in scenes:
                            s["num"]      = counter[0]
                            s["story_id"] = f"story_{counter[0]:04d}"
                            f.write(json.dumps(s, ensure_ascii=False) + "\n")
                            counter[0] += 1
                total_written += len(scenes)
            log(f"  +{len(scenes)} plans  (this run total: {total_written})")

    print(f"\nDone. {total_written} new plans written.")


# ─────────────────────────────────────────────────────────────────
# Gen phase
# ─────────────────────────────────────────────────────────────────

def gen_one(job: dict, client: OpenAI, dry_run: bool) -> tuple[str, bool]:
    story_id = job["story_id"]
    out_path = OUT_DIR / f"{story_id}.md"

    if dry_run:
        log(f"  [DRY-RUN] gen: {story_id}")
        return story_id, True

    actors_str        = ", ".join(job.get("actors", []))
    objects_str       = ", ".join(job.get("objects", []))
    constructions_str = "\n".join(f"  - {c}" for c in job.get("constructions", []))
    outline_str       = "\n".join(
        f"  {i+1}. {s}" for i, s in enumerate(job.get("outline", []))
    )

    prompt = GEN_PROMPT_TPL.format(
        global_rules=GLOBAL_RULES,
        construction_rules=CONSTRUCTION_RULES,
        story_id=story_id,
        scene=job.get("scene", ""),
        actors=actors_str,
        objects=objects_str,
        constructions=constructions_str,
        outline=outline_str,
    )

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
        )
    except Exception as e:
        log(f"  GEN API ERROR {story_id}: {e}")
        return story_id, False

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
            log(f"  PARSE FAIL {story_id}: raw:\n{raw[:200]}")
            return story_id, False
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            log(f"  PARSE FAIL (inner) {story_id}")
            return story_id, False

    groups = data.get("groups", [])
    if not (5 <= len(groups) <= 12):
        log(f"  SKIP {story_id}: expected 5-12 groups, got {len(groups)}")
        return story_id, False

    bad = False
    for g in groups:
        if len(g) != 4 or not all(isinstance(s, str) and s.strip() for s in g):
            log(f"  SKIP {story_id}: malformed group")
            bad = True
            break
    if bad:
        return story_id, False

    content = "\n\n".join("\n".join(g) for g in groups) + "\n"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    log(f"  OK {story_id} ({tokens_in}→{tokens_out})")
    return story_id, True


def run_gen(args: argparse.Namespace, client: OpenAI) -> None:
    plans = load_plans()
    if not plans:
        print("No plans found. Run 'plan' first.")
        return

    pending = [p for p in plans if not (OUT_DIR / f"{p['story_id']}.md").exists()]

    if args.limit:
        pending = pending[: args.limit]

    total = len(pending)
    if total == 0:
        print("Nothing to generate — all stories already exist.")
        return

    print(f"Pending: {total} stories")

    failed: list[str] = []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(gen_one, job, client, args.dry_run): job for job in pending}
        for fut in as_completed(futs):
            sid, ok = fut.result()
            if not ok:
                failed.append(sid)

    done = total - len(failed)
    print(f"\nDone: {done}/{total} written. Failed: {len(failed)}")
    if failed:
        print("Failed:", sorted(failed)[:20])


# ─────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────

def run_report() -> None:
    plans = load_plans()
    done  = sum(1 for p in plans if (OUT_DIR / f"{p['story_id']}.md").exists())

    print(f"Plans:     {len(plans)}")
    print(f"Generated: {done}")
    print(f"Remaining: {len(plans) - done}")

    if not plans:
        return

    settings     = Counter(p.get("scene", "unknown") for p in plans)
    constructions = Counter()
    for p in plans:
        for c in p.get("constructions", []):
            constructions[c] += 1

    print()
    print("Settings:")
    for scene, count in sorted(settings.items(), key=lambda x: -x[1]):
        bar = "#" * (count // 2)
        print(f"  {scene:<20} {count:>3}  {bar}")

    print()
    print("Constructions:")
    for c, count in sorted(constructions.items(), key=lambda x: -x[1]):
        print(f"  {c:<25} {count}")


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Lang-3d story corpus generator")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="Generate scene outlines")
    p_plan.add_argument("--target",  type=int, default=400,
                        help="Total plans to have after this run (default 400)")
    p_plan.add_argument("--workers", type=int, default=4)
    p_plan.add_argument("--batch",   type=int, default=20,
                        help="Scenes per API call (default 20)")
    p_plan.add_argument("--dry-run", action="store_true")

    p_gen = sub.add_parser("gen", help="Generate story files from plans")
    p_gen.add_argument("--workers", type=int, default=4)
    p_gen.add_argument("--limit",   type=int, default=0,
                       help="Max stories to generate this run (0=all pending)")
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

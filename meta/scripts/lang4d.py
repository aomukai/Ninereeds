#!/usr/bin/env python3
"""
Lang-4d corpus generation — tiny parallel stories integrating Level-4 constructions.

Phase 1 — plan:
  Generate scene outlines with required Level-4 constructions.
  Appends to lang_4d_plans.jsonl. Idempotent.

Phase 2 — gen:
  For each plan without an output file, generate the full EN/DE/JP/ZH parallel story.
  Writes to training_data/lang/lang_4d/. Idempotent.

Phase 3 — report:
  Progress summary, construction coverage.

Usage:
  python3 meta/scripts/lang4d.py plan  [--target 200] [--workers 4] [--batch 20] [--dry-run]
  python3 meta/scripts/lang4d.py gen   [--workers 4] [--limit N] [--dry-run]
  python3 meta/scripts/lang4d.py report

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
PLANS_FILE = LANG_DIR / "lang_4d_plans.jsonl"
OUT_DIR    = LANG_DIR / "lang_4d"
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
It must use at least 2 of the Level-4 grammar constructions listed below.

## Level-4 constructions

static_location     — subject is at rest at a location
                      EN: "The cat is under the table."
                      DE: dative with Wechselpräposition — "Die Katze liegt unter dem Tisch."
                      JP: NP の LOCALIZER に + いる/ある — "猫は机の下にいる。"
                      ZH: 在 + NP + localizer — "猫在桌子下面。"

goal_movement       — subject moves into/onto/toward a destination
                      EN: "The dog runs into the house."
                      DE: accusative with Wechselpräposition — "Der Hund läuft ins Haus."
                      JP: に/へ + motion verb — "犬が家の中に走って入った。"
                      ZH: directional complement — "狗跑进了房子。"

source_movement     — subject moves away from or out of a place
                      EN: "She came out of the room."
                      DE: aus/von + dative — "Sie kam aus dem Zimmer."
                      JP: から + motion verb — "部屋から出てきた。"
                      ZH: 从 + place + directional complement — "她从房间里走出来了。"

path_movement       — subject moves through / across / along / around / over
                      EN: "He walked across the bridge."
                      DE: durch/über/entlang + accusative — "Er ging über die Brücke."
                      JP: NP を + motion verb (を marks traversed space) — "橋を渡った。"
                      ZH: 穿过/沿着/绕过 + NP — "他穿过了公园。"

tool_instrument     — agent uses a tool to perform an action
                      EN: "She cut the bread with a knife."
                      DE: mit + dative — "Sie schnitt das Brot mit dem Messer."
                      JP: tool + で — "ナイフでパンを切った。"
                      ZH: 用 + tool + verb — "她用刀切了面包。"

body_instrument     — agent uses a body part as instrument
                      EN: "He pushed the door with his hand."
                      DE: mit + dative body part — "Er schob die Tür mit der Hand auf."
                      JP: body part + で — "手でドアを押した。"
                      ZH: 用 + body part + verb — "他用手推开了门。"

vehicle_means       — agent travels by a means of transport
                      EN: "They went to school by bicycle."
                      DE: mit + dative vehicle — "Sie fuhren mit dem Fahrrad zur Schule."
                      JP: vehicle + で — "自転車で学校へ行った。"
                      ZH: specific motion verb (坐/骑/开/步行) — "他们骑自行车去学校了。"

## Vocabulary to draw from

Actors (2-3 per scene):
  Tom, Kate, the child, the teacher, the woman, the man, the neighbour, the student,
  the dog, the cat, the girl, the boy

Settings (vary across scenes):
  kitchen, bedroom, office, classroom, garden, park, shop, library, train station,
  restaurant, living room, market, farm, workshop, school, hospital, street, forest,
  river, bridge, station, garage, bakery, post office

Objects (2-4 per scene, concrete and common):
  book, bag, key, knife, scissors, pen, bread, bowl, cup, chair, table, door, window,
  bicycle, train ticket, letter, tool, towel, flower, hat, box, coat, bottle, map,
  ladder, rope, hammer, brush, notebook, apple, fish, newspaper, umbrella

## Scene arc

S1: Establish where someone or something is (static_location)
S2: Someone moves toward or into the scene (goal_movement)
S3: An action using a tool, body part, or means of transport
S4: Someone or something moves away, through, or across something
S5: Resolution — a result or state, possibly with another location or instrument

Stories may extend to S8. Keep sentences short and concrete. No metaphors.

## Variety rules

Across the {batch_size} scenes in this batch:
- Vary settings, actor pairs, objects, and constructions
- No two scenes with the same setting + actor pair + main action
- Include at least one movement construction (goal, source, or path) per scene
- Include at least one instrument or vehicle construction per scene
- Include at least one static location per scene

## Output

Return JSON only — no commentary, no markdown fences:
{{"scenes": [
  {{
    "scene": "kitchen",
    "actors": ["Kate", "the child"],
    "objects": ["knife", "bread", "bowl"],
    "constructions": ["static_location", "goal_movement", "tool_instrument"],
    "outline": [
      "Kate is standing at the counter in the kitchen.",
      "The child runs into the kitchen.",
      "Kate cuts the bread with a knife.",
      "She puts the bread into the bowl.",
      "The child carries the bowl to the table."
    ]
  }}
]}}"""


GLOBAL_RULES = """\
## Global rules

Naturalise, don't translate.
  The goal is the same meaning expressed as a native speaker would say it.
  Sentence structure may differ across languages when naturalness requires it.

Japanese plain form throughout. No desu/masu. No keigo.
  Past: ta form. Ongoing: te-iru. Future: darou / to omou.
  CRITICAL: Japanese lines MUST be written in Japanese script (kanji + hiragana + katakana).
  NEVER use romaji. Roman letters in Japanese output = wrong.

German V2 word order. Verb is always the second constituent.
  Time adverbials trigger inversion: Gestern ist Tom... (not Gestern Tom ist).
  Use sein in Perfekt for intransitive motion verbs:
    ist gelaufen, ist gesprungen, ist gefahren, ist gegangen, ist geschwommen, ist geklettert.
  Use haben for caused motion / placement:
    hat gelegt, hat gestellt, hat getragen, hat geschnitten, hat geschoben.

Mandarin: 了 for completed action, 在 for ongoing, 会 for future intent.
No tense morphology — time is shown through particles and context.

Pronoun drop: Japanese and Mandarin omit subject/object pronouns when clear from context.

All sentences must be short and concrete. No metaphors. No literary prose."""


CONSTRUCTION_RULES = """\
## Level-4 construction rules

static_location:
  DE: Wechselpräposition + DATIVE — "im Haus" (in+dem), "unter dem Tisch", "auf der Matte".
      Positional verbs: liegen (lie), sitzen (sit), stehen (stand), hängen (hang), warten (wait).
  JP: NP の LOCALIZER に + いる (animate) / ある (inanimate).
      Localizers: 下 (under), 上 (on/above), 中 (in), 隣 (beside), 前 (in front), 後ろ (behind).
      Activity at location uses で instead of に: 台所で働く (work in the kitchen).
  ZH: 在 + place NP + localizer (下面, 上面, 里面, 旁边, 前面, 后面, 中间).

goal_movement:
  DE: Wechselpräposition + ACCUSATIVE — "ins Haus" (in+das), "auf den Tisch", "unter das Bett".
      Motion verbs with sein in Perfekt: ist gelaufen, ist gesprungen, ist gefahren.
      nach + dative for geographic destinations; zu + dative for specific places.
  JP: NP に/へ + motion verb. No particle change — direction is in the verb.
      Directional compound verbs: 走って入る (run-enter), 走り込む (run-into).
  ZH: Directional complements attach to motion verb: 跑进 (run-enter), 走进 (walk-enter),
      爬上 (climb-onto), 跳下 (jump-off), 飞过来 (fly-over-here).

source_movement:
  DE: aus + dative for enclosed spaces (aus dem Haus, aus der Tasche).
      von + dative for open/named sources (vom Bahnhof, von der Schule).
  JP: NP から + motion verb.
  ZH: 从 + place + directional complement: 从房间里走出来, 从桌子上掉下来.

path_movement:
  DE: durch + accusative (through), über + accusative (across/over),
      entlang + accusative post-nominal (den Fluss entlang — along the river),
      um + accusative + herum (around).
  JP: NP を + motion verb — を marks the traversed space, not a direct object.
      橋を渡る (cross the bridge), 公園を歩く (walk through the park), トンネルを通る.
      に沿って for "along": 川に沿って歩く.
  ZH: 穿过 (through/across), 沿着 (along), 绕过 (around), 越过 (over/across).

tool_instrument:
  DE: mit + dative: mit dem Messer, mit der Schere, mit dem Pinsel.
  JP: tool + で: ナイフで, はさみで, 筆で.
  ZH: 用 + tool + verb: 用刀切, 用剪刀剪, 用筆写.

body_instrument:
  DE: mit + dative body part: mit der Hand, mit den Augen, mit dem Fuß.
      Special: zu Fuß gehen (on foot) — NOT mit dem Fuß.
  JP: body part + で: 手で, 足で, 目で, 耳で.
  ZH: 用 + body part: 用手, 用脚, 用眼睛, 用耳朵.

vehicle_means:
  DE: mit + dative vehicle: mit dem Zug, mit dem Fahrrad, mit dem Auto, mit dem Flugzeug.
      zu Fuß for on foot (NOT mit dem Fuß).
  JP: vehicle + で: 電車で, 自転車で, 車で, 飛行機で.
  ZH: SPECIFIC MOTION VERB — never 用 for vehicles:
      坐 (sit-in): 坐火车, 坐汽车, 坐飞机.
      骑 (ride): 骑自行车, 骑摩托车.
      开 (drive): 开车, 开船.
      步行/走路 for on foot.

## German case reference

Dative articles: dem (masc/neut), der (fem), den (pl, noun adds -n/-en if needed).
Accusative articles: den (masc), die (fem), das (neut), die (pl).
Contractions: in+dem=im, an+dem=am, in+das=ins, an+das=ans, zu+dem=zum, zu+der=zur."""


GEN_PROMPT_TPL = """\
Generate a short parallel story in English, German, Japanese (Japanese script only — \
kanji/hiragana/katakana, NO romaji), and Mandarin.
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

    counter    = [next_story_num(existing)]
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

    for attempt in (1, 2):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
            )
        except Exception as e:
            log(f"  GEN API ERROR (attempt {attempt}) {story_id}: {e}")
            if attempt == 2:
                return story_id, False
            continue

        raw = (resp.choices[0].message.content or "").strip()
        tokens_in  = resp.usage.prompt_tokens     if resp.usage else "?"
        tokens_out = resp.usage.completion_tokens if resp.usage else "?"

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
            log(f"  PARSE FAIL (attempt {attempt}) {story_id}: raw:\n{raw[:200]}")
            if attempt == 2:
                return story_id, False
            continue

        groups = data.get("groups", [])
        if not (5 <= len(groups) <= 12):
            log(f"  SKIP {story_id}: expected 5-12 groups, got {len(groups)}")
            if attempt == 2:
                return story_id, False
            continue

        bad = False
        for g in groups:
            if len(g) != 4 or not all(isinstance(s, str) and s.strip() for s in g):
                log(f"  SKIP {story_id}: malformed group")
                bad = True
                break
        if bad:
            if attempt == 2:
                return story_id, False
            continue

        content = "\n\n".join("\n".join(g) for g in groups) + "\n"
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        log(f"  OK {story_id} ({tokens_in}→{tokens_out})")
        return story_id, True

    return story_id, False


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

    settings      = Counter(p.get("scene", "unknown") for p in plans)
    constructions = Counter()
    for p in plans:
        for c in p.get("constructions", []):
            constructions[c] += 1

    print()
    print("Settings:")
    for scene, count in sorted(settings.items(), key=lambda x: -x[1])[:15]:
        bar = "#" * (count // 2)
        print(f"  {scene:<22} {count:>3}  {bar}")

    print()
    print("Constructions:")
    for c, count in sorted(constructions.items(), key=lambda x: -x[1]):
        print(f"  {c:<22} {count}")


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Lang-4d story corpus generator")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="Generate scene outlines")
    p_plan.add_argument("--target",  type=int, default=200,
                        help="Total plans to have after this run (default 200)")
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

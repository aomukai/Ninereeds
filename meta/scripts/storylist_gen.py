#!/usr/bin/env python3
"""Generate storylist.txt entries for grounded stories 196–750.

Reads world_bible.md and the first few existing entries as examples,
then calls DeepSeek in batches to produce new story specs in the same format.
NIM primary, OpenRouter fallback (same pattern as vignette_gen.py).

Usage:
  python3 meta/scripts/storylist_gen.py gen   [--group NAME] [--workers 1]
  python3 meta/scripts/storylist_gen.py status
"""

from __future__ import annotations
import argparse, json, os, pathlib, re, sys, time

ROOT         = pathlib.Path(__file__).resolve().parents[2]
CORPUS_ADMIN = ROOT / "training" / "corpus_admin" / "grounded_stories"
WORLD_BIBLE  = CORPUS_ADMIN / "world_bible.md"
STORY_LIST   = CORPUS_ADMIN / "storylist.txt"
PROGRESS_F   = CORPUS_ADMIN / "storylist_gen_progress.json"

# ── API ───────────────────────────────────────────────────────────────────────

def _read_dotenv() -> dict:
    env: dict[str, str] = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

_dotenv = _read_dotenv()

def _get(key: str) -> str | None:
    return os.environ.get(key) or _dotenv.get(key)

def _make_client(key: str, base_url: str):
    from openai import OpenAI
    k = _get(key)
    if not k:
        return None
    return OpenAI(api_key=k, base_url=base_url)

def _sources():
    src = []
    ds = _make_client("DEEPSEEK_API_KEY", "https://api.deepseek.com/v1")
    if ds:
        src.append((ds, "deepseek-chat", {}))
    nim = _make_client("NVIDIA_API_KEY", "https://integrate.api.nvidia.com/v1")
    if nim:
        src.append((nim, "deepseek-ai/deepseek-v4-pro",
                    {"extra_body": {"chat_template_kwargs": {"thinking": False}}}))
    orc = _make_client("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1")
    if orc:
        src.append((orc, "deepseek/deepseek-v4-flash", {}))
    return src

SOURCES = _sources()

def call_api(system: str, user: str) -> tuple[str, str]:
    if not SOURCES:
        raise RuntimeError("No API key. Set NVIDIA_API_KEY or OPENROUTER_API_KEY.")
    last_err = None
    for attempt in range(5):
        for client, model, extra in SOURCES:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user},
                    ],
                    max_tokens=4000,
                    temperature=0.85,
                    **extra,
                )
                content = resp.choices[0].message.content
                if content and content.strip():
                    return content.strip(), model
            except Exception as e:
                last_err = e
        if "429" in str(last_err):
            wait = 10 * (2 ** attempt)
            time.sleep(wait)
    raise RuntimeError(f"All API sources failed after retries: {last_err}")

# ── Group specifications ───────────────────────────────────────────────────────

# Characters: E=Emma T=Taro G=Gran B=Biscuit L=Bello
#             M=Mei D=Dou Y=Yun R=Riku S=Stefan H=Hana O=Owen C=Clara V=Vern

GROUPS: list[dict] = [
    {
        "name": "the_mill",
        "location": "The Mill",
        "char_pool": "E T M G Y B",
        "concepts": [
            "the water wheel turning fast vs slow depending on the stream level",
            "grain goes in at the top, flour comes out below — cause and effect",
            "flour dust in the air, on surfaces, on clothes",
            "the sluice lever and what happens when you open or close it",
            "the weight and sound of the millstones",
            "the stream in different weather (fast after rain, low in dry summer)",
            "Mei knowing where to stand, which board to step over",
        ],
        "edu_anchors": [
            "science_forces_basic (push/pull, water driving the wheel)",
            "math_measurement (how much grain, how much flour, comparing weights)",
            "science_material_world (stone, wood, flour — what things are made of and how they change)",
        ],
        "seasons": ["spring", "summer", "autumn", "winter"],
        "n_stories": 55,
        "start_id": 196,
    },
    {
        "name": "verns_workshop",
        "location": "Vern's Workshop",
        "char_pool": "V E T M G",
        "concepts": [
            "measuring and marking before cutting — the sequence matters",
            "fitting a joint without glue first, then correcting",
            "different woods by smell and touch (ash, oak, pine)",
            "the vise holding something still while you work",
            "a broken thing brought in for repair",
            "tool names used as habit, not instruction",
            "wood shavings, sawdust, the smell of linseed oil",
            "something made from start to finish — stages visible",
        ],
        "edu_anchors": [
            "math_measurement_length (measuring, marking, the ruler)",
            "math_geometry_compose_decompose (how shapes fit together, a joint)",
            "science_material_world (wood grain, hardness, what bends vs breaks)",
        ],
        "seasons": ["spring", "summer", "autumn", "winter"],
        "n_stories": 50,
        "start_id": 251,
    },
    {
        "name": "the_market",
        "location": "The Village — market stall (Yun and Mei)",
        "char_pool": "M Y E T G R S H",
        "concepts": [
            "weighing on the brass scale — heavier vs lighter",
            "counting items and making change",
            "what things cost and whether you have enough",
            "the stall table kept tidy between customers",
            "Yun knowing every regular customer",
            "Riku delivering something to the stall",
            "Stefan passing on his beat",
            "Hana's bread bought at the stall end of day",
            "what sells quickly vs what is left at closing",
        ],
        "edu_anchors": [
            "math_money_basic (coins, price, change)",
            "economics_goods_and_services (Hana bakes, Yun sells, Riku delivers)",
            "economics_markets_buyers_sellers (stall, choosing, paying)",
            "civics_community_helpers (the people who make the village work)",
        ],
        "seasons": ["spring", "summer", "autumn"],
        "n_stories": 45,
        "start_id": 301,
    },
    {
        "name": "the_hill",
        "location": "The Hill",
        "char_pool": "E T G O B L",
        "concepts": [
            "the cottage very small from the top",
            "weather coming in from the west — you can see it before it arrives",
            "Owen's sheep moving slowly across the slope",
            "sounds from the village carrying upward on still days",
            "the wind without trees to break it",
            "the gate at the top to somewhere else",
            "the mill chimney visible below",
            "the oak a dark shape at the field's edge",
        ],
        "edu_anchors": [
            "science_weather_seasons (reading the sky for weather)",
            "geography_geographic_features (hill, valley, stream visible below)",
            "science_land_water_erosion (rain on the slope, the stream running faster)",
        ],
        "seasons": ["spring", "summer", "autumn", "winter"],
        "n_stories": 45,
        "start_id": 346,
    },
    {
        "name": "root_cellar_kitchen",
        "location": "The Root Cellar (below Gran's cottage) or Gran's kitchen",
        "char_pool": "E T G M",
        "concepts": [
            "the heavy door, the iron prop bar, the steps down",
            "cool even in summer — the temperature doesn't follow the weather above",
            "smell of stored things: apples, onions, earth",
            "checking for rot — the potato that has gone soft",
            "Gran's jars with their labels in careful writing",
            "counting what is left by February or March",
            "fetching something specific — sent down with a lamp",
            "preserved vs fresh — what keeps and what doesn't",
        ],
        "edu_anchors": [
            "science_material_world (what changes over time, what preserves)",
            "math_quantity_extended (how many left, how many used)",
            "health_healthy_eating_basic (where food comes from, what Gran stores)",
            "time_past_present_future (what was put away in autumn, used in winter)",
        ],
        "seasons": ["autumn", "winter", "spring"],
        "n_stories": 50,
        "start_id": 391,
    },
    {
        "name": "dogs_and_cat",
        "location": "various — new locations encountered for the first time",
        "char_pool": "E T M G B L D",
        "concepts": [
            "Dou arriving without explanation at Gran's garden wall",
            "Biscuit deciding Dou is beneath his notice (and meaning it)",
            "Bello made quietly miserable by Dou's indifference",
            "Dou in the apple tree where no one can reach",
            "Biscuit at the mill — what he makes of the wheel and the noise",
            "Bello discovering the root cellar smell through the gap in the door",
            "Owen's sheepdog seen across the field — Biscuit's reaction",
            "Dou at the workshop — Vern doesn't stop working",
        ],
        "edu_anchors": [
            "science_animals_basic (how different animals behave differently)",
            "social_emotional_empathy_perspective_taking (reading what an animal wants or feels)",
        ],
        "seasons": ["spring", "summer", "autumn", "winter"],
        "n_stories": 40,
        "start_id": 441,
    },
    {
        "name": "school_extended",
        "location": "Schoolyard or Classroom",
        "char_pool": "E T M C",
        "concepts": [
            "the nature table through the seasons (what Clara puts on it, what the children bring)",
            "arithmetic at school vs arithmetic in the world",
            "the ash tree in the yard in different seasons",
            "playground physics — the climbing frame, balance, momentum",
            "a project made in stages over several days",
            "Mei arriving at the school for the first time",
            "the coat hooks, the labelled cards, order and belonging",
            "Clara calling on the quiet children",
        ],
        "edu_anchors": [
            "math_arithmetic_basic (sums on the blackboard, counting at school)",
            "science_living_nonliving (nature table — what is alive, what was)",
            "civics_rules_fairness (classroom rules, turns, fairness)",
            "social_emotional_friendship_cooperation (Mei meeting Emma's classmates)",
        ],
        "seasons": ["spring", "summer", "autumn", "winter"],
        "n_stories": 45,
        "start_id": 481,
    },
    {
        "name": "village_life",
        "location": "The Village main street, lane, side street",
        "char_pool": "E T G M Y R S H V O",
        "concepts": [
            "Riku's red bicycle and the letters — who gets what",
            "Stefan's beat — his slow walk, his nod",
            "Hana's bakery before dawn, the loaves in the window",
            "Owen at the gate on the lane in different weather",
            "an errand that takes longer than expected",
            "the side street — quieter, the vet, the doctor, Vern",
            "the village in different seasons (bare and cold in winter, full in summer)",
            "Mei and her grandmother on the walk home from market",
        ],
        "edu_anchors": [
            "civics_community_helpers (Riku, Stefan, Hana, Owen each doing their work)",
            "economics_goods_and_services (what each person makes or does for others)",
            "social_emotional_community_belonging (knowing people, being known)",
        ],
        "seasons": ["spring", "summer", "autumn", "winter"],
        "n_stories": 65,
        "start_id": 526,
    },
    {
        "name": "old_places_new",
        "location": "The Oak / The Pond / Meadow path / Gran's garden — familiar but with new angles",
        "char_pool": "E T G B L M D O",
        "concepts": [
            "Mei at the oak or pond for the first time — seeing through her eyes",
            "Dou at the pond — her approach to water is different from the dogs",
            "Owen stopping on the meadow path — a different perspective on the field",
            "a familiar place in weather not seen before",
            "the seasonal details pushed further (frost on the reeds, the pond in full summer heat)",
            "something noticed for the first time after many visits",
            "a plant or animal at a familiar place that has changed since last time",
        ],
        "edu_anchors": [
            "science_plants_lifecycle (the apple tree from blossom to windfall, the bean from seed to pod)",
            "science_animals_lifecycle (the robin's nest eggs to fledglings, the tadpoles)",
            "math_patterns (repeating patterns in the natural world — petals, fence posts, puddle ripples)",
            "social_emotional_identifying_emotions (Emma frustrated, Taro disappointed, Mei nervous)",
            "time_weekly_monthly (the pond changes week by week, the garden month by month)",
        ],
        "seasons": ["spring", "summer", "autumn", "winter"],
        "n_stories": 110,
        "start_id": 591,
    },
    {
        "name": "education_grounded",
        "location": "various — let the concept dictate the right location",
        "char_pool": "E T G M V C O Y B L D",
        "concepts": [
            # science
            "forces: objects move when pushed or pulled — the mill lever, Vern's vise squeezing, Taro pushing a heavy wheelbarrow",
            "needs of living things: plants need sunlight, water, soil — Gran's seedling that droops without water and recovers",
            "weather patterns: describe outdoor conditions (sunny, cloudy, rainy, windy) — what the sky looks like before rain arrives",
            "five senses: what Emma smells before she sees, what she hears before she finds, what she knows by touch alone",
            "living vs non-living: the nature table — what is alive, what was alive, what was never alive (leaf vs stone vs acorn)",
            "water states: water flows and fills containers; ice at the pond edge in winter; steam from Gran's pot — same thing, different forms",
            "magnets: Vern has a magnet in his workshop for finding dropped iron nails in the sawdust — show how it pulls",
            "animals lifecycle: the robin's eggs to fledglings; the tadpole's legs appearing over weeks",
            "plants lifecycle: from seed Gran plants, to the sprout, to the bean on the vine — weeks apart",
            # math
            "sorting and classifying: sorting apples by size, beans by colour — same property, different groupings",
            "patterns: repeating patterns in the physical world — the tiles at the mill, fence posts, blossom petals",
            "counting to the last one: Yun counts coins to the last, Gran counts eggs — the last number tells how many",
            "comparison and ordering: longer/shorter, heavier/lighter — Vern measuring two pieces, Yun's scale tipping",
            "measurement with tools: Vern's ruler, Gran's cup measure, Yun's brass scale — using a standard unit",
            "shapes composing: Vern shows how a square fits next to a triangle, how two pieces make one shape",
            # time and sequence
            "daily time — morning/afternoon/evening as observable changes in light, temperature, what people are doing",
            "past/present/future: the apple tree was bare in winter, has blossom now, will have apples in autumn",
            # social/emotional
            "identifying emotions: Emma frustrated, Taro disappointed, Mei nervous — what the body does, not the label",
            "sharing and kindness: dividing what was picked, letting someone go first — the action, not the lesson",
            "friendship cooperation: Mei and Emma lifting something together that neither can lift alone",
            # community/economics
            "community helpers: Riku delivers, Stefan patrols, Hana bakes, Owen tends the flock — each doing their specific work",
            "goods and services: Hana makes bread (a good); Vern fixes a broken thing (a service); Riku delivers (a service)",
            "needs vs wants: Emma at the market with coins — she needs bread, she wants the honey; she chooses",
            # health
            "personal hygiene: washing hands before helping Gran with bread — the germ logic shown through Gran's insistence",
        ],
        "edu_anchors": [
            "science_forces_basic (SCI-KG-FOR-001)",
            "science_needs_of_living_things (SCI-KG-PLT-001)",
            "science_living_nonliving (preschool)",
            "science_material_world / water states (preschool)",
            "science_animals_lifecycle (preschool)",
            "science_plants_lifecycle (preschool)",
            "math_classification / sorting (preschool)",
            "math_patterns (preschool)",
            "math_counting_cardinality (KG)",
            "math_comparison_ordering (KG)",
            "math_measurement (preschool)",
            "math_shapes_2d_3d (KG)",
            "time_daily_time (preschool)",
            "time_past_present_future (preschool)",
            "social_emotional_identifying_emotions (preschool)",
            "social_emotional_sharing_kindness (preschool)",
            "social_emotional_friendship_cooperation (KG)",
            "civics_community_helpers (KG)",
            "economics_goods_and_services (KG)",
            "economics_needs_vs_wants (KG)",
            "health_personal_hygiene (KG)",
        ],
        "seasons": ["spring", "summer", "autumn", "winter"],
        "n_stories": 50,
        "start_id": 701,
    },
]

# ── Progress tracking ─────────────────────────────────────────────────────────

def load_progress() -> dict:
    if PROGRESS_F.exists():
        return json.loads(PROGRESS_F.read_text(encoding="utf-8"))
    return {g["name"]: {"planned": g["n_stories"], "done": 0} for g in GROUPS}

def save_progress(prog: dict) -> None:
    PROGRESS_F.write_text(json.dumps(prog, indent=2, ensure_ascii=False), encoding="utf-8")

def stories_already_in_list() -> set[int]:
    if not STORY_LIST.exists():
        return set()
    ids: set[int] = set()
    for line in STORY_LIST.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^STORY:\s*(\d+)", line.strip())
        if m:
            ids.add(int(m.group(1)))
    return ids

# ── Example entries (pulled from storylist for the prompt) ────────────────────

EXAMPLE_ENTRIES = """\
STORY: 01
CLUSTER: oak tree (autumn)
LOCATION: The Oak
SEASON: autumn
CHARACTERS: E T B
KEY WORDS: acorn, squirrel, branch, bark, root, leaf, seed, hole, nut, crack, climb, carry, bury, drop
SEED: Biscuit finds the squirrel's hole at the base of the oak. Taro climbs the low branch. An acorn drops. Emma picks it up — it fits in her palm, small and round and brown, with a rough cap.

STORY: 50
CLUSTER: fish at different times of day
LOCATION: The Pond
SEASON: summer
CHARACTERS: E T
KEY WORDS: pond, fish, morning, afternoon, light, angle, shadow, surface, visible, still, gone, wait, look, same
SEED: The morning pond is still as glass — six fish visible from the flat stone. After lunch the sun has moved; the fish are harder to see. Same fish, different light.
OBSERVATION_STATE: Fish are visible only when the light is at the right angle and the water is still. This changes across the day — not because the fish moved, but because the conditions for seeing them changed.

STORY: 100
CLUSTER: getting dressed for cold
LOCATION: Gran's house (front door)
SEASON: winter
CHARACTERS: E T G
KEY WORDS: coat, boot, zip, lace, scarf, cold, frost, dress, order, slow, wait, layer, button, meadow
SEED: Getting dressed to go out in winter: coats first, then boots, then scarves. The order matters. Taro's zip sticks. Gran fixes it. The meadow path is white with frost when they finally open the door.
TEMPORAL_RELATION: Preparation has a necessary sequence (you cannot put boots on before a coat). Each step has a duration. The cold is encountered only at the end.

STORY: 130
CLUSTER: what happens when the jar falls
LOCATION: Gran's kitchen
SEASON: any
CHARACTERS: E T G
KEY WORDS: jar, tilt, tip, water, floor, spread, slow, fast, tiles, rug, cloth, mop, too late, next time
SEED: Taro's elbow nudges a jar. It tips. Water hits the floor and spreads — under the table, toward the rug, reaching things before anyone can stop it. Gran watches. Then: the cloth and the mop.
CAUSE_EFFECT: The jar tips → water on the floor → water spreads by gravity to low points → Gran uses a cloth for most of it and a mop for the corner. The chain is fast at first, then slow to clean up.
"""

# ── Prompt builder ────────────────────────────────────────────────────────────

SYSTEM = """\
You write story specification entries for a grounded story corpus.
Each entry specifies WHAT happens — not HOW to write it. The story is written separately by another model.
Your job is to generate concrete, varied, physically grounded scene specifications.

Rules:
- Every SEED must describe a physical, observable scene — something that can be shown through action and sensation.
- Do NOT state the educational concept directly. Show the situation; the concept emerges from it.
- Characters must come from the provided pool for each group.
- Vary the characters across entries — not every story needs all characters.
- Vary the seasons across entries within the group.
- Each CLUSTER name is short and descriptive (3–6 words, lowercase).
- NOTES (optional): one sentence of generation guidance for the author. Use sparingly.
- CAUSE_EFFECT, SPATIAL_CONCEPT, TEMPORAL_RELATION, OBSERVATION_STATE: use only when the concept is central to the story.
- Output ONLY the story entries. No preamble, no commentary, no numbering outside the format.
"""

def build_prompt(bible: str, group: dict, batch_start: int, batch_size: int, existing_ids: set[int]) -> str:
    ids = list(range(batch_start, batch_start + batch_size))
    char_pool = group["char_pool"]
    concepts_str = "\n".join(f"  - {c}" for c in group["concepts"])
    edu_str = "\n".join(f"  - {e}" for e in group["edu_anchors"])
    seasons_str = ", ".join(group["seasons"])

    return f"""{bible}

---

EXAMPLES OF CORRECT FORMAT:

{EXAMPLE_ENTRIES}

---

Now generate exactly {batch_size} story specification entries for the following group.

GROUP: {group["name"]}
LOCATION: {group["location"]}
CHARACTER POOL (use codes): {char_pool}
  E=Emma  T=Taro  G=Gran  B=Biscuit  L=Bello
  M=Mei   D=Dou   Y=Yun   R=Riku     S=Stefan
  H=Hana  O=Owen  C=Clara V=Vern

CONCEPT TERRITORY (show through action — never state directly):
{concepts_str}

EDUCATION ANCHORS (the scene should naturally embody these — no explanation):
{edu_str}

SEASONS AVAILABLE: {seasons_str}
STORY IDs TO USE (in order): {', '.join(str(i) for i in ids)}

Requirements:
- Use each ID exactly once, in order.
- Vary the characters: not every story needs all characters; some work with just two.
- Vary the seasons across the batch.
- SEED must be 2–4 sentences: observable actions, physical details, no moral or summary.
- Separate entries with a blank line.
- Use CAUSE_EFFECT / TEMPORAL_RELATION / SPATIAL_CONCEPT / OBSERVATION_STATE only when central.
- Do not repeat a concept angle already covered in a previous entry of this batch.
"""

# ── Parser ────────────────────────────────────────────────────────────────────

REQUIRED_FIELDS = {"STORY", "CLUSTER", "LOCATION", "SEASON", "CHARACTERS", "KEY WORDS", "SEED"}

def parse_entries(text: str) -> list[dict]:
    """Parse raw LLM output into list of entry dicts. Drops malformed entries."""
    # Split on blank lines between STORY: blocks
    raw_blocks = re.split(r"\n{2,}", text.strip())
    entries: list[dict] = []
    current: dict = {}

    for block in raw_blocks:
        lines = block.strip().splitlines()
        if not lines:
            continue
        # Check if this block starts a new story
        if re.match(r"^STORY:\s*\d+", lines[0].strip()):
            if current.get("STORY"):
                entries.append(current)
            current = {}
        # Parse key: value lines
        for line in lines:
            line = line.strip()
            if not line:
                continue
            m = re.match(r"^([A-Z][A-Z _]+):\s*(.*)", line)
            if m:
                key = m.group(1).strip()
                val = m.group(2).strip()
                current[key] = val

    if current.get("STORY"):
        entries.append(current)

    # Validate required fields
    valid: list[dict] = []
    for e in entries:
        missing = REQUIRED_FIELDS - set(e.keys())
        if missing:
            print(f"  [skip] STORY {e.get('STORY','?')} missing: {missing}")
        else:
            valid.append(e)
    return valid


def entry_to_text(e: dict) -> str:
    """Serialise a parsed entry back to storylist format."""
    ordered_keys = [
        "STORY", "CLUSTER", "LOCATION", "SEASON", "CHARACTERS",
        "KEY WORDS", "SEED",
        "SPATIAL_CONCEPT", "TEMPORAL_RELATION", "CAUSE_EFFECT",
        "OBSERVATION_STATE", "ARITHMETIC", "ANSWER", "STATES",
        "COUNTS", "PARAPHRASE", "NOTES",
    ]
    lines = []
    for key in ordered_keys:
        if key in e:
            lines.append(f"{key}: {e[key]}")
    # Any extra keys not in the ordered list
    for key, val in e.items():
        if key not in ordered_keys:
            lines.append(f"{key}: {val}")
    return "\n".join(lines)

# ── Generation ────────────────────────────────────────────────────────────────

BATCH_SIZE = 25

def gen_group(group: dict, prog: dict, existing_ids: set[int]) -> int:
    """Generate all pending entries for a group. Returns count added."""
    total = group["n_stories"]
    all_expected = set(range(group["start_id"], group["start_id"] + total))
    missing = sorted(all_expected - existing_ids)
    if not missing:
        g_prog = prog[group["name"]]
        g_prog["done"] = total
        save_progress(prog)
        print(f"  [{group['name']}] already complete ({total}/{total})")
        return 0

    bible = WORLD_BIBLE.read_text(encoding="utf-8")
    added = 0
    g_prog = prog[group["name"]]

    while missing:
        batch_ids = missing[:BATCH_SIZE]
        missing = missing[BATCH_SIZE:]

        print(f"  [{group['name']}] generating IDs {batch_ids[0]}–{batch_ids[-1]} "
              f"({len(batch_ids)} entries)...", flush=True)

        try:
            prompt = build_prompt(bible, group, batch_ids[0], len(batch_ids), existing_ids)
            raw, model = call_api(SYSTEM, prompt)
        except Exception as e:
            print(f"  [{group['name']}] API error: {e}")
            break

        entries = parse_entries(raw)
        if not entries:
            print(f"  [{group['name']}] no valid entries parsed — skipping batch")
            continue

        # Append to storylist.txt
        with STORY_LIST.open("a", encoding="utf-8") as f:
            for entry in entries:
                f.write("\n" + entry_to_text(entry) + "\n")
            existing_ids.update(int(e["STORY"]) for e in entries)

        added += len(entries)
        g_prog["done"] = total - len(missing)
        save_progress(prog)
        print(f"  [{group['name']}] +{len(entries)} entries via {model} "
              f"(total {g_prog['done']}/{total})", flush=True)

    return added

# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_gen(group_filter: str | None) -> None:
    prog = load_progress()
    existing_ids = stories_already_in_list()
    print(f"Existing story IDs in storylist: {len(existing_ids)} (max={max(existing_ids) if existing_ids else 0})")

    groups_to_run = [g for g in GROUPS if group_filter is None or g["name"] == group_filter]
    if not groups_to_run:
        sys.exit(f"No group named '{group_filter}'")

    total_added = 0
    for group in groups_to_run:
        if group["name"] not in prog:
            prog[group["name"]] = {"planned": group["n_stories"], "done": 0}
        print(f"\n── {group['name']} ({group['n_stories']} stories, start={group['start_id']}) ──")
        total_added += gen_group(group, prog, existing_ids)

    print(f"\nDone. Added {total_added} entries total.")

def cmd_status() -> None:
    prog = load_progress()
    existing_ids = stories_already_in_list()
    print(f"Storylist entries: {len(existing_ids)}")
    print(f"{'Group':<25} {'Done':>6} {'Planned':>8} {'%':>5}")
    print("-" * 48)
    total_done = total_planned = 0
    for g in GROUPS:
        gp = prog.get(g["name"], {"done": 0, "planned": g["n_stories"]})
        done, planned = gp["done"], gp["planned"]
        pct = f"{100*done//planned}%" if planned else "-"
        print(f"  {g['name']:<23} {done:>6} {planned:>8} {pct:>5}")
        total_done += done
        total_planned += planned
    print("-" * 48)
    print(f"  {'TOTAL':<23} {total_done:>6} {total_planned:>8}")

# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Generate grounded story list entries")
    sub = ap.add_subparsers(dest="cmd")

    p_gen = sub.add_parser("gen", help="Generate story spec entries")
    p_gen.add_argument("--group", default=None,
                       help="Run only this group (default: all)")

    sub.add_parser("status", help="Show generation progress")

    args = ap.parse_args()
    if args.cmd == "gen":
        cmd_gen(args.group)
    elif args.cmd == "status":
        cmd_status()
    else:
        ap.print_help()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
cluster_phases.py — semantic clustering of phase files for run_4.

Classifies every phase_1 through phase_6 file into one of the 13 triplet-story
categories using a keyword-based classifier (offline, deterministic).

Cluster order mirrors the triplet story categories:
  1. animals_and_nature
  2. body_and_health
  3. food_and_meals
  4. home_and_daily_life
  5. tools_and_making
  6. vehicles_and_travel
  7. weather_and_seasons
  8. people_and_relationships
  9. play_and_games
  10. school_and_learning
  11. math_and_science
  12. language_and_grammar
  13. abstract_concepts  (catch-all)

Within each cluster, files are sorted by phase number then alphabetically so the
curriculum level progression is preserved.

Usage:
  python3 meta/scripts/cluster_phases.py gen
  python3 meta/scripts/cluster_phases.py report
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PHASES_DIR = ROOT / "training_data" / "phases"
OUT_FILE = PHASES_DIR / "cluster_sequence.txt"

CATEGORIES = [
    "animals_and_nature",
    "body_and_health",
    "food_and_meals",
    "home_and_daily_life",
    "tools_and_making",
    "vehicles_and_travel",
    "weather_and_seasons",
    "people_and_relationships",
    "play_and_games",
    "school_and_learning",
    "math_and_science",
    "language_and_grammar",
    "abstract_concepts",
]

CATEGORY_ORDER = {cat: i for i, cat in enumerate(CATEGORIES)}

# ---------------------------------------------------------------------------
# Keyword sets per category — order within list does not matter
# ---------------------------------------------------------------------------

ANIMALS = {
    "alligator","amphibian","ant","ape","bat","bear","beaver","bee","beetle",
    "bird","buffalo","butterfly","camel","cat","caterpillar","chameleon",
    "cheetah","chicken","chipmunk","cobra","cockroach","cow","coyote","crab",
    "crane","cricket","crocodile","crow","deer","dinosaur","dog","dolphin",
    "dove","dragonfly","duck","eagle","earthworm","elephant","elk","falcon",
    "fish","flea","fly","fox","frog","giraffe","goat","gorilla","grasshopper",
    "hamster","hawk","hen","heron","hippo","horse","hummingbird","iguana",
    "insect","jaguar","jellyfish","kangaroo","kitten","ladybug","lamb","lion",
    "lizard","lobster","lynx","magpie","mammoth","mantis","mole","monkey",
    "moose","mosquito","moth","mouse","octopus","ostrich","otter","owl",
    "panther","parrot","peacock","pelican","penguin","pig","pigeon","piranha",
    "platypus","porcupine","puppy","rabbit","raccoon","rat","raven","reindeer",
    "rhino","robin","rooster","salamander","salmon","scorpion","seal","shark",
    "sheep","shrimp","slug","snail","snake","spider","squirrel","stag","stork",
    "swan","termite","tiger","toad","tortoise","toucan","turkey","turtle",
    "vulture","walrus","wasp","whale","wolf","worm","zebra",
    # nature / landscape
    "acorn","bark","bay","beach","boulder","branch","brook","bush","canyon",
    "cave","cliff","coast","coral","creek","dune","earth","estuary","fern",
    "field","flora","forest","fungus","glacier","gorge","grass","hill","ivy",
    "jungle","lagoon","lake","landscape","leaf","marsh","meadow","moss","mound",
    "mud","mushroom","nature","oak","pebble","pine","plant","plateau","pond",
    "pool","prairie","puddle","reed","reef","ridge","river","rock","root",
    "sand","savanna","seaweed","shell","shrub","soil","stem","stone","stream",
    "swamp","thicket","tide","twig","valley","vine","waterfall","wilderness",
    "wood","woods",
}

BODY = {
    "abdomen","ankle","arm","artery","back","belly","bladder","blood","bone",
    "brain","breath","buttock","calf","cartilage","cell","cheek","chest","chin",
    "collarbone","digestive","ear","elbow","eye","eyebrow","eyelid","face",
    "finger","fingerprint","flesh","foot","forehead","gum","hair","hand","head",
    "heart","heel","hip","jaw","joint","kidney","knee","kneecap","knuckle",
    "leg","lip","liver","lung","muscle","nail","neck","nerve","nose","nostril",
    "organ","palm","pulse","rib","retina","scalp","shin","shoulder","skeleton",
    "skin","skull","spine","stomach","tendon","throat","thumb","toe","tongue",
    "tooth","trachea","vein","wrist",
    # health / medical
    "clinic","disease","fever","flu","health","hospital","illness","injury",
    "medical","medicine","nurse","pain","patient","recovery","surgery","therapy",
    "vitamin","wound",
}

FOOD = {
    "almond","apple","apricot","artichoke","asparagus","avocado","bacon",
    "banana","basil","bean","beef","berry","biscuit","blueberry","broccoli",
    "butter","cabbage","cake","candy","carrot","cashew","casserole","cauliflower",
    "cereal","cheese","cherry","chili","chocolate","cinnamon","coconut","coffee",
    "cookie","corn","cream","cucumber","curry","custard","dates","dessert",
    "diet","dough","dressing","egg","feast","fig","fish","flour","food",
    "fruit","garlic","ginger","grape","ham","herb","honey","icing","jam","juice",
    "kale","ketchup","lemon","lettuce","lime","lunch","mango","meal","melon",
    "menu","milk","mint","miso","mustard","noodle","nutrition","nut","oat",
    "olive","onion","orange","pancake","pasta","peach","peanut","pear","pepper",
    "pickle","pineapple","pizza","plum","popcorn","potato","pretzel","pumpkin",
    "raisin","raspberry","recipe","rice","rind","salad","salt","sandwich","sauce",
    "seed","smoothie","snack","soup","spice","spinach","strawberry","sugar",
    "sushi","syrup","taco","tapioca","tea","tomato","tortilla","turnip",
    "vegetable","vinegar","walnut","watermelon","wheat","yam","yogurt","zucchini",
    # plants / gardening context
    "blossom","bud","bulb","cactus","dahlia","daisy","fern","flower","herb",
    "lavender","lily","orchid","petal","rose","sunflower","tulip","weed",
}

HOME = {
    "apartment","apron","armchair","attic","balcony","barn","basement","bathroom",
    "bedroom","blanket","bookcase","bookshelf","broom","bucket","cabinet","candle",
    "carpet","ceiling","cellar","chair","chimney","closet","coat","couch","curtain",
    "cushion","desk","door","doorknob","doorstep","drawer","driveway","fireplace",
    "floor","fork","frame","furniture","garage","garden","gate","glass","hallway",
    "hammock","hanger","home","house","household","jar","jug","kettle","kitchen",
    "knob","ladder","lamp","lampshade","latch","laundry","living room","loft",
    "mattress","mirror","mop","mug","napkin","pan","pantry","patio","pillow",
    "pitcher","plate","porch","pot","room","roof","rug","shelf","shawl","sink",
    "sofa","spoon","staircase","stool","table","tile","towel","tray","vase",
    "wall","wardrobe","window","windowsill","yard",
}

TOOLS = {
    "anchor","anvil","arrow","axe","bait","barometer","battery","bead","bellows",
    "blade","bolt","bottle","box","bracket","brick","brush","calculator","canteen",
    "chain","chalk","chisel","clamp","clip","clock","coin","comb","compass","cord",
    "crayon","crown","dial","drill","drum","envelope","fan","filter","flag","flask",
    "funnel","gauge","gear","globe","glove","gun","hammer","hinge","hook","hourglass",
    "instrument","knife","lantern","latch","lens","lever","lock","loom","magnet",
    "map","mask","meter","microscope","mold","needle","net","oar","pail","pen",
    "pencil","pin","pipe","piston","plug","plunger","pump","pulley","puzzle",
    "rope","ruler","saw","scale","scissors","screw","shield","shovel","sieve",
    "sponge","stamp","staple","string","tape","telescope","thermometer","thread",
    "timer","tongs","tool","torch","trap","tube","umbrella","watch","wedge",
    "wheel","whistle","wire","wrench","yardstick",
}

VEHICLES = {
    "airplane","ambulance","bicycle","boat","bus","canoe","cargo","cart","cruise",
    "ferry","flight","freight","helicopter","jet","kayak","locomotive","motorcycle",
    "parachute","plane","raft","rocket","sailboat","scooter","ship","skateboard",
    "sled","sleigh","spacecraft","spaceship","submarine","taxi","train","tractor",
    "truck","van","vehicle","vessel","wagon","yacht",
    # transport infrastructure
    "airport","dock","freeway","harbor","highway","motorway","overpass","pier",
    "port","runway","station","terminal","track","tunnel",
}

WEATHER = {
    "arctic","atmosphere","aurora","autumn","blizzard","breeze","climate","cloud",
    "cold","cyclone","dawn","desert","dew","drizzle","drought","dust","flood",
    "fog","freeze","frost","gale","hail","heat","humidity","hurricane","ice",
    "lava","lightning","meteorology","mist","monsoon","moon","pressure",
    "rainbow","rain","season","sky","sleet","snow","spring","storm","summer",
    "sun","sunlight","sunshine","sunset","temperature","thunder","tide","tornado",
    "twilight","volcano","warmth","wind","winter",
}

PEOPLE = {
    "adult","agent","alice","ambassador","architect","artist","astronaut","athlete",
    "aunt","author","baker","banker","brother","captain","cashier","chef","child",
    "citizen","coach","commander","conductor","cook","cousin","craftsman","dancer",
    "daughter","detective","diplomat","director","doctor","driver","educator",
    "elder","emma","emperor","employee","engineer","entrepreneur","farmer","father",
    "firefighter","fisherman","friend","gardener","general","governor","grandfather",
    "grandmother","guard","guest","guide","hero","historian","hughes","hunter",
    "judge","king","knight","lawyer","leader","librarian","manager","mayor",
    "merchant","midwife","minister","monk","mother","neighbor","nanny","nurse",
    "officer","orphan","parent","pastor","pilot","poet","police","politician",
    "president","priest","prince","princess","professor","queen","ranger","reader",
    "reporter","researcher","ruler","ruth","sailor","scientist","servant","sheriff",
    "sister","soldier","son","student","surgeon","teacher","uncle","veteran",
    "visitor","volunteer","warrior","writer","witch","wizard","worker",
    # social/relational
    "ancestor","audience","baby","boss","community","couple","crowd","culture",
    "custom","family","generation","government","group","habit","heritage",
    "identity","marriage","nation","neighbor","peer","people","person","race",
    "relationship","role","society","stranger","tradition","tribe",
}

PLAY = {
    "adventure","arena","balloon","ball","camp","carnival","celebrate","chase",
    "climb","clown","compete","contest","dare","explore","fair","fantasy","feast",
    "festival","frisbee","fun","game","hide","hopscotch","hunt","jump","kite",
    "leap","lego","marble","maze","party","playground","pretend","race","riddle",
    "skip","slide","sport","swing","tag","tournament","toy","treasure",
    "tricks","trophy","tumble",
}

SCHOOL = {
    "academy","alphabet","assignment","book","calculator","certificate","chapter",
    "class","classroom","college","course","curriculum","debate","degree","diploma",
    "discipline","education","encyclopedia","essay","exam","exercise","explanation",
    "grade","graduation","homework","knowledge","lab","lecture","lesson","library",
    "notebook","practice","presentation","principal","quiz","read","research",
    "review","schedule","science","semester","skill","study","subject","syllabus",
    "task","teacher","term","test","textbook","thesis","tutor","university","write",
}

MATH = {
    "addition","algebra","algorithm","angle","area","arithmetic","average",
    "axis","binary","calculate","chart","circle","coefficient","constant","count",
    "cube","data","decimal","denominator","digit","divide","division","equation",
    "estimate","exponent","factor","formula","fraction","geometry","graph","half",
    "hexagon","infinity","integer","kilogram","kilometer","length","liter",
    "logic","math","matrix","measure","meter","metric","minus","multiply",
    "negative","number","numerator","odd","operation","operator","pattern","percent",
    "perimeter","pi","plus","polygon","prime","probability","proof","proportion",
    "quantity","radius","ratio","rectangle","remainder","rounding","sequence",
    "set","shape","sort","sphere","square","statistic","subtract","sum",
    "symmetry","triangle","variable","velocity","volume","weight","zero",
    # numbers written out
    "one","two","three","four","five","six","seven","eight","nine","ten",
    "eleven","twelve","thirteen","hundred","thousand","million","billion",
    # science
    "atom","biology","cell","chemical","chemistry","circuit","climate",
    "compound","current","density","ecology","electricity","electron","element",
    "energy","evolution","experiment","force","fossil","gene","genetics","gravity",
    "heat","hypothesis","lab","light","magnet","mass","matter","molecule",
    "motion","nucleus","orbit","oxygen","particle","physics","planet","pressure",
    "proton","reaction","resistance","solar","solution","speed","temperature",
    "theory","universe","velocity","vibration","wave",
}

LANGUAGE = {
    "abbreviating","adjective","adverb","alphabet","analogy","announce","apostrophe",
    "article","ask","caption","clause","comma","communication","complement",
    "compose","conjunction","context","contraction","conversation","define",
    "describe","dialect","dialogue","dictionary","diphthong","discuss","essay",
    "expression","grammar","headline","idiom","instruction","jargon","language",
    "letter","meaning","metaphor","name","narrate","narrative","noun","paraphrase",
    "paragraph","phrase","poem","poetry","point","prefix","pronoun","punctuation",
    "question","quotation","reading","rhetoric","rhyme","sentence","sign","speech",
    "spelling","story","style","suffix","summary","syllable","symbol","syntax",
    "tale","text","tense","title","tone","translate","understanding","usage",
    "verb","vocabulary","word","writing",
}

CATEGORY_KEYWORDS: dict[str, set[str]] = {
    "animals_and_nature":    ANIMALS,
    "body_and_health":       BODY,
    "food_and_meals":        FOOD,
    "home_and_daily_life":   HOME,
    "tools_and_making":      TOOLS,
    "vehicles_and_travel":   VEHICLES,
    "weather_and_seasons":   WEATHER,
    "people_and_relationships": PEOPLE,
    "play_and_games":        PLAY,
    "school_and_learning":   SCHOOL,
    "math_and_science":      MATH,
    "language_and_grammar":  LANGUAGE,
}


def normalize(concept: str) -> str:
    """Strip _N suffix, clean punctuation, lowercase."""
    c = re.sub(r"_\d+$", "", concept)
    c = c.lower().strip()
    return c


def extract_stems(concept: str) -> list[str]:
    """Return the concept and common word-form variants to check."""
    c = normalize(concept)
    stems = [c]
    # "a X of Y" → extract X
    m = re.match(r"^a (.+?) of ", c)
    if m:
        stems.append(m.group(1))
    # "X like" → extract X
    m = re.match(r"^(.+?) like$", c)
    if m:
        stems.append(m.group(1))
    # gerund → try base verb (ing → e, ing → strip)
    if c.endswith("ing"):
        stems.append(c[:-3])        # running → runn (close enough for set lookup)
        stems.append(c[:-3] + "e")  # dancing → danc → dance
        stems.append(c[:-4])        # swimming → swimm → swim
    # adjective suffixes: remove common endings to get stem
    for suffix in ("ful", "less", "ness", "ment", "tion", "sion", "ity", "ive",
                   "ous", "al", "ary", "ery", "ory", "able", "ible", "ance", "ence"):
        if c.endswith(suffix) and len(c) > len(suffix) + 2:
            stems.append(c[:-len(suffix)])
    # Compound: "sleepy fish" → "fish"; "thirsty bunny" → "bunny"
    words = c.split()
    if len(words) >= 2:
        stems.extend(words)
    return stems


def classify_one(concept: str) -> str:
    """Return the best category for a concept string."""
    # Pure number → math
    clean = normalize(concept)
    if re.match(r"^\d+(\.\d+)?$", clean):
        return "math_and_science"

    stems = extract_stems(concept)

    # Priority order matches CATEGORIES list order
    for category in CATEGORIES[:-1]:  # skip abstract_concepts (catch-all)
        keyword_set = CATEGORY_KEYWORDS[category]
        for stem in stems:
            if stem in keyword_set:
                return category

    return "abstract_concepts"


# ---------------------------------------------------------------------------
# File collection and sequence generation
# ---------------------------------------------------------------------------

def collect_all_files() -> list[tuple[str, str, str]]:
    """Return list of (phase_num_str, concept, rel_path)."""
    entries = []
    for phase_num in range(1, 7):
        phase_dir = PHASES_DIR / f"phase_{phase_num}"
        if not phase_dir.exists():
            continue
        for path in sorted(phase_dir.glob("*.md")):
            concept = path.stem
            rel_path = f"phase_{phase_num}/{path.name}"
            entries.append((str(phase_num), concept, rel_path))
    return entries


def cmd_gen(args: argparse.Namespace) -> None:
    entries = collect_all_files()
    print(f"Total phase files: {len(entries)}")

    assignments: dict[str, str] = {}
    for phase, concept, rel in entries:
        assignments[concept] = classify_one(concept)

    def sort_key(entry: tuple) -> tuple:
        phase, concept, rel = entry
        cat = assignments.get(concept, "abstract_concepts")
        return (CATEGORY_ORDER[cat], int(phase), concept)

    sorted_entries = sorted(entries, key=sort_key)

    lines = [
        "# Semantic cluster sequence for phase training (run_4+)",
        "# Generated by meta/scripts/cluster_phases.py (keyword classifier)",
        "# Category order: " + ", ".join(CATEGORIES),
        "#",
        "# Format: phase_N/filename.md  (relative to training_data/phases/)",
        "#",
    ]
    current_cat = None
    for phase, concept, rel in sorted_entries:
        cat = assignments.get(concept, "abstract_concepts")
        if cat != current_cat:
            lines.append(f"# --- {cat} ---")
            current_cat = cat
        lines.append(rel)

    OUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(sorted_entries)} entries → {OUT_FILE}")

    counts = Counter(assignments.values())
    print("\nCluster distribution:")
    for cat in CATEGORIES:
        print(f"  {cat:<30} {counts.get(cat, 0):>5}")


def cmd_report(args: argparse.Namespace) -> None:
    if not OUT_FILE.exists():
        print("cluster_sequence.txt not found. Run gen first.")
        return
    lines = OUT_FILE.read_text(encoding="utf-8").splitlines()
    entries = [l for l in lines if l and not l.startswith("#")]
    print(f"cluster_sequence.txt: {len(entries)} entries")
    all_entries = collect_all_files()
    counts = Counter(classify_one(c) for _, c, _ in all_entries)
    for cat in CATEGORIES:
        print(f"  {cat:<30} {counts.get(cat, 0):>5}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Cluster phase files by semantic category")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("gen", help="Generate cluster_sequence.txt")
    sub.add_parser("report", help="Show cluster distribution")
    args = parser.parse_args()
    if args.cmd == "gen":
        cmd_gen(args)
    elif args.cmd == "report":
        cmd_report(args)


if __name__ == "__main__":
    main()

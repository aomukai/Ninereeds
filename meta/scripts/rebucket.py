#!/usr/bin/env python3
"""
rebucket.py — Move files from words/unsorted/ into semantic bucket directories.

Reads the expanded BUCKETS dict and moves any matching files from unsorted/
to their correct bucket. Safe to re-run: skips files already in a bucket dir.

Usage:
  python3 meta/scripts/rebucket.py [--dry-run]
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

REPO_ROOT  = Path(__file__).resolve().parent.parent.parent
WORDS_DIR  = REPO_ROOT / "training_data" / "redesign" / "words"
UNSORTED   = WORDS_DIR / "unsorted"

# ── Expanded bucket map ────────────────────────────────────────────────────────
# Keep existing 10 buckets and add new ones below.
# A word can only be in ONE bucket — first match wins when multiple apply.

BUCKETS: dict[str, str] = {

    # ── ANIMALS (all creatures) ────────────────────────────────────────────────
    "acorn": "nature",      # placed here first — acorn is nature, not animal
    "alligator": "animals", "amphibian": "animals", "ant": "animals",
    "anthill": "animals", "ape": "animals", "arthropod": "animals",
    "bat": "animals", "beaver": "animals", "bee": "animals", "beetle": "animals",
    "butterfly": "animals", "camel": "animals", "caterpillar": "animals",
    "chick": "animals", "chimp": "animals", "chimpanzee": "animals",
    "cobra": "animals", "crab": "animals", "crane": "animals",
    "cricket": "animals", "crocodile": "animals", "crow": "animals",
    "dolphin": "animals", "donkey": "animals", "dragonfly": "animals",
    "duck": "animals", "duckling": "animals", "eagle": "animals",
    "earthworm": "animals", "eel": "animals", "elephant": "animals",
    "ewe": "animals", "firefly": "animals", "flea": "animals",
    "fly": "animals", "fox": "animals", "frog": "animals",
    "geese": "animals", "giraffe": "animals", "gnat": "animals",
    "goat": "animals", "gorilla": "animals", "grasshopper": "animals",
    "hamster": "animals", "hawk": "animals", "hen": "animals",
    "hippo": "animals", "insect": "animals", "jellyfish": "animals",
    "kitten": "animals", "ladybug": "animals", "lamb": "animals",
    "lark": "animals", "leopard": "animals", "lion": "animals",
    "lizard": "animals", "mammal": "animals", "mole": "animals",
    "monkey": "animals", "mosquito": "animals", "moth": "animals",
    "octopus": "animals", "ostrich": "animals", "otter": "animals",
    "owl": "animals", "oyster": "animals", "panda": "animals",
    "parrot": "animals", "peacock": "animals", "pelican": "animals",
    "penguin": "animals", "pig": "animals", "pigeon": "animals",
    "pony": "animals", "porcupine": "animals", "puppy": "animals",
    "rat": "animals", "raven": "animals", "reindeer": "animals",
    "rhinoceros": "animals", "robin": "animals", "rooster": "animals",
    "salmon": "animals", "scorpion": "animals", "seagull": "animals",
    "seal": "animals", "shark": "animals", "sheep": "animals",
    "shrimp": "animals", "snail": "animals", "snake": "animals",
    "spider": "animals", "squirrel": "animals", "stork": "animals",
    "swan": "animals", "tadpole": "animals", "tiger": "animals",
    "toad": "animals", "tortoise": "animals", "trout": "animals",
    "turkey": "animals", "turtle": "animals", "vole": "animals",
    "walrus": "animals", "wasp": "animals", "weasel": "animals",
    "whale": "animals", "wren": "animals", "zebra": "animals",
    "elk": "animals", "bunny": "animals", "newt": "animals",
    "squid": "animals", "starfish": "animals", "bison": "animals",
    "buffalo": "animals", "jaguar": "animals", "kangaroo": "animals",
    "lynx": "animals", "moose": "animals", "pangolin": "animals",
    "platypus": "animals", "sloth": "animals", "tapir": "animals",

    # ── NATURE ────────────────────────────────────────────────────────────────
    "air": "nature", "autumn": "nature", "birch": "nature",
    "breeze": "nature", "cave": "nature", "cliff": "nature",
    "cloud": "nature", "coral": "nature", "creek": "nature",
    "desert": "nature", "dew": "nature", "dust": "nature",
    "echo": "nature", "fern": "nature", "fir": "nature",
    "fog": "nature", "forest": "nature", "frost": "nature",
    "glacier": "nature", "grass": "nature", "grassland": "nature",
    "gravel": "nature", "hail": "nature", "hay": "nature",
    "horizon": "nature", "ice": "nature", "jungle": "nature",
    "lake": "nature", "landscape": "nature", "leaf": "nature",
    "lightning": "nature", "maple": "nature", "marsh": "nature",
    "meadow": "nature", "mist": "nature", "moss": "nature",
    "mud": "nature", "mushroom": "nature", "mycelium": "nature",
    "oak": "nature", "ocean": "nature", "pine": "nature",
    "pinecone": "nature", "pond": "nature", "puddle": "nature",
    "rainbow": "nature", "rock": "nature", "root": "nature",
    "sand": "nature", "sea": "nature", "seashell": "nature",
    "seashore": "nature", "seaweed": "nature", "seed": "nature",
    "smoke": "nature", "snow": "nature", "soil": "nature",
    "spring": "nature", "storm": "nature", "stream": "nature",
    "summer": "nature", "sunrise": "nature", "sunset": "nature",
    "thunder": "nature", "tide": "nature", "tornado": "nature",
    "twig": "nature", "valley": "nature", "vine": "nature",
    "volcano": "nature", "wave": "nature", "wildflower": "nature",
    "willow": "nature", "winter": "nature", "worm": "nature",
    "pebble": "nature", "shadow": "nature", "snowball": "nature",
    "snowflake": "nature", "sunlight": "nature", "starlight": "nature",
    "driftwood": "nature", "swamp": "nature", "thorn": "nature",
    "lava": "nature", "magnet": "nature", "crystal": "nature",
    "pollen": "nature", "vapor": "nature", "galaxy": "nature",
    "planet": "nature", "atom": "nature", "oxygen": "nature",
    "carbon": "nature",

    # ── HOUSEHOLD ─────────────────────────────────────────────────────────────
    "blanket": "household", "broom": "household", "brush": "household",
    "bucket": "household", "button": "household", "candle": "household",
    "carpet": "household", "clock": "household", "comb": "household",
    "curtain": "household", "cushion": "household", "dish": "household",
    "drawer": "household", "fan": "household", "fork": "household",
    "frame": "household", "glue": "household", "hammer": "household",
    "hook": "household", "iron": "household", "jug": "household",
    "knife": "household", "lamp": "household", "latch": "household",
    "laundry": "household", "lock": "household", "mat": "household",
    "mattress": "household", "mirror": "household", "mop": "household",
    "mug": "household", "needle": "household", "pan": "household",
    "pencil": "household", "pillow": "household", "pin": "household",
    "pipe": "household", "plate": "household", "plug": "household",
    "pot": "household", "rack": "household", "rag": "household",
    "scissors": "household", "shelf": "household", "soap": "household",
    "spoon": "household", "stair": "household", "stove": "household",
    "switch": "household", "tray": "household", "umbrella": "household",
    "vase": "household", "wire": "household", "ladder": "household",
    "lunchbox": "household", "napkin": "household", "towel": "household",
    "blanket": "household", "cupboard": "household", "fridge": "household",
    "oven": "household", "sink": "household", "toilet": "household",
    "bathtub": "household", "shower": "household", "couch": "household",
    "sofa": "household", "nightstand": "household", "dresser": "household",
    "bookshelf": "household", "cabinet": "household", "dustpan": "household",
    "bucket": "household", "pail": "household", "ladle": "household",
    "tongs": "household", "whisk": "household", "spatula": "household",
    "sieve": "household", "colander": "household", "grater": "household",
    "peeler": "household", "kettle": "household", "teapot": "household",
    "pitcher": "household", "thermos": "household", "canteen": "household",
    "jar": "household", "lid": "household", "tin": "household",
    "wrapper": "household", "foil": "household", "cling": "household",
    "tissue": "household", "sponge": "household", "scrubber": "household",
    "plunger": "household", "hose": "household", "funnel": "household",
    "pulley": "household", "lever": "household", "wrench": "household",
    "screwdriver": "household", "drill": "household", "saw": "household",
    "axe": "household", "shovel": "household", "rake": "household",
    "hoe": "household", "trowel": "household", "paintbrush": "household",
    "roller": "household", "tape": "household", "ruler": "household",
    "stapler": "household", "eraser": "household", "marker": "household",
    "chalk": "household", "clipboard": "household", "binder": "household",
    "folder": "household", "envelope": "household", "stamp": "household",
    "sticker": "household", "ribbon": "household", "string": "household",
    "cord": "household", "cable": "household", "charger": "household",

    # ── FOOD ──────────────────────────────────────────────────────────────────
    "almond": "food", "banana": "food", "bean": "food",
    "berry": "food", "broccoli": "food", "butter": "food",
    "cabbage": "food", "cake": "food", "candy": "food",
    "carrot": "food", "cauliflower": "food", "celery": "food",
    "cereal": "food", "cheese": "food", "cherry": "food",
    "chicken": "food", "chocolate": "food", "coffee": "food",
    "cookie": "food", "corn": "food", "cucumber": "food",
    "dairy": "food", "dessert": "food", "dough": "food",
    "flour": "food", "garlic": "food", "ginger": "food",
    "grape": "food", "honey": "food", "juice": "food",
    "kale": "food", "lemon": "food", "lettuce": "food",
    "mango": "food", "melon": "food", "mint": "food",
    "noodle": "food", "oat": "food", "oil": "food",
    "onion": "food", "orange": "food", "pancake": "food",
    "pasta": "food", "peach": "food", "pear": "food",
    "pea": "food", "pepper": "food", "pickle": "food",
    "pineapple": "food", "pizza": "food", "plum": "food",
    "popcorn": "food", "potato": "food", "pumpkin": "food",
    "radish": "food", "raisin": "food", "salad": "food",
    "sauce": "food", "sausage": "food", "seafood": "food",
    "spinach": "food", "strawberry": "food", "sugar": "food",
    "syrup": "food", "tea": "food", "tomato": "food",
    "vanilla": "food", "vegetable": "food", "vinegar": "food",
    "walnut": "food", "watermelon": "food", "wheat": "food",
    "yeast": "food", "yogurt": "food", "yolk": "food",
    "citrus": "food", "chestnut": "food", "blueberry": "food",
    "muffin": "food", "waffle": "food", "toast": "food",
    "sandwich": "food", "soup": "food", "stew": "food",
    "broth": "food", "salsa": "food", "cream": "food",
    "butter": "food", "jam": "food", "jelly": "food",
    "peanut": "food", "soy": "food", "tofu": "food",
    "cocoa": "food", "lemonade": "food", "milkshake": "food",
    "soda": "food", "protein": "food", "nutrition": "food",
    "vitamin": "food", "fiber": "food", "calcium": "food",
    "plantain": "food", "parsnip": "food", "turnip": "food",

    # ── BODY ──────────────────────────────────────────────────────────────────
    "ankle": "body", "beard": "body", "belly": "body",
    "blood": "body", "bone": "body", "brain": "body",
    "breast": "body", "breath": "body", "cheek": "body",
    "chest": "body", "chin": "body", "claw": "body",
    "collarbone": "body", "elbow": "body", "eyebrow": "body",
    "eyelid": "body", "fang": "body", "finger": "body",
    "fingernail": "body", "fingerprint": "body", "fingertip": "body",
    "fist": "body", "flesh": "body", "forehead": "body",
    "gum": "body", "heartbeat": "body", "heel": "body",
    "hip": "body", "jaw": "body", "jawbone": "body",
    "joint": "body", "kidney": "body", "knee": "body",
    "kneecap": "body", "knuckle": "body", "lip": "body",
    "liver": "body", "lung": "body", "muscle": "body",
    "neck": "body", "nerve": "body", "nipple": "body",
    "palm": "body", "pore": "body", "pupil": "body",
    "rib": "body", "retina": "body", "shoulder": "body",
    "shoulderblade": "body", "shin": "body", "shinbone": "body",
    "skin": "body", "skull": "body", "spine": "body",
    "stomach": "body", "thigh": "body", "thumb": "body",
    "thumbnail": "body", "toe": "body", "toenail": "body",
    "tongue": "body", "vein": "body", "waist": "body",
    "whisker": "body", "wrist": "body", "earlobe": "body",
    "throat": "body", "heart": "body", "iris": "body",
    "tendon": "body", "artery": "body",

    # ── PEOPLE ────────────────────────────────────────────────────────────────
    "adult": "people", "ancestor": "people", "artist": "people",
    "athlete": "people", "author": "people", "baker": "people",
    "boss": "people", "builder": "people", "butcher": "people",
    "captain": "people", "carpenter": "people", "cashier": "people",
    "chef": "people", "citizen": "people", "classmate": "people",
    "cook": "people", "counselor": "people", "customer": "people",
    "daughter": "people", "detective": "people", "doctor": "people",
    "driver": "people", "elder": "people", "employee": "people",
    "engineer": "people", "farmer": "people", "firefighter": "people",
    "fisherman": "people", "gardener": "people", "girl": "people",
    "grandfather": "people", "grandmother": "people", "grandpa": "people",
    "grandparent": "people", "guard": "people", "guest": "people",
    "guide": "people", "historian": "people", "housekeeper": "people",
    "hunter": "people", "husband": "people", "janitor": "people",
    "judge": "people", "king": "people", "knight": "people",
    "lawyer": "people", "leader": "people", "librarian": "people",
    "mechanic": "people", "merchant": "people", "mom": "people",
    "musician": "people", "neighbor": "people", "nurse": "people",
    "officer": "people", "painter": "people", "parent": "people",
    "passenger": "people", "patient": "people", "pharmacist": "people",
    "physicist": "people", "pilot": "people", "poet": "people",
    "police": "people", "president": "people", "prince": "people",
    "princess": "people", "queen": "people", "sailor": "people",
    "scholar": "people", "scientist": "people", "shepherd": "people",
    "sibling": "people", "sister": "people", "soldier": "people",
    "son": "people", "stranger": "people", "student": "people",
    "surgeon": "people", "tailor": "people", "teenager": "people",
    "toddler": "people", "trainer": "people", "traveler": "people",
    "tutor": "people", "uncle": "people", "villain": "people",
    "visitor": "people", "volunteer": "people", "waiter": "people",
    "warrior": "people", "wife": "people", "worker": "people",
    "boy": "people", "brother": "people", "boyfriend": "people",
    "girlfriend": "people", "cousin": "people", "dad": "people",
    "dean": "people", "caregiver": "people", "actor": "people",
    "reporter": "people", "pilot": "people", "athlete": "people",
    "coach": "people", "biologist": "people", "ecologist": "people",
    "mathematician": "people", "architect": "people", "librarian": "people",
    "logger": "people", "miller": "people", "woodcutter": "people",
    "potter": "people", "weaver": "people", "bystander": "people",
    "upstander": "people", "sidekick": "people", "hero": "people",
    "villain": "people", "rookie": "people", "beginner": "people",

    # ── PLACES ────────────────────────────────────────────────────────────────
    "airport": "places", "apartment": "places", "area": "places",
    "attic": "places", "auditorium": "places", "backyard": "places",
    "bakery": "places", "barn": "places", "basement": "places",
    "bathroom": "places", "bedroom": "places", "bridge": "places",
    "cafeteria": "places", "cabin": "places", "castle": "places",
    "church": "places", "city": "places", "classroom": "places",
    "clinic": "places", "coast": "places", "country": "places",
    "countryside": "places", "courtyard": "places", "driveway": "places",
    "factory": "places", "farm": "places", "farmhouse": "places",
    "farmyard": "places", "field": "places", "garage": "places",
    "garden": "places", "gym": "places", "hall": "places",
    "hallway": "places", "harbor": "places", "highway": "places",
    "hospital": "places", "hotel": "places", "hut": "places",
    "island": "places", "kitchen": "places", "lab": "places",
    "lane": "places", "library": "places", "mall": "places",
    "market": "places", "marketplace": "places", "museum": "places",
    "neighborhood": "places", "office": "places", "orchard": "places",
    "palace": "places", "park": "places", "path": "places",
    "pier": "places", "playground": "places", "playroom": "places",
    "plaza": "places", "port": "places", "prison": "places",
    "ranch": "places", "restaurant": "places", "road": "places",
    "room": "places", "rooftop": "places", "school": "places",
    "schoolyard": "places", "shop": "places", "shore": "places",
    "sidewalk": "places", "stadium": "places", "station": "places",
    "store": "places", "street": "places", "temple": "places",
    "theater": "places", "town": "places", "tunnel": "places",
    "university": "places", "village": "places", "warehouse": "places",
    "well": "places", "workshop": "places", "yard": "places",
    "zoo": "places", "den": "places", "hive": "places",
    "burrow": "places", "warren": "places", "kennel": "places",
    "nest": "places", "doghouse": "places", "birdhouse": "places",
    "fishpond": "places", "cornfield": "places", "vineyard": "places",
    "prairie": "places", "district": "places", "region": "places",
    "subway": "places", "station": "places", "dock": "places",
    "airport": "places", "lobby": "places", "porch": "places",
    "patio": "places", "fort": "places",

    # ── CLOTHING ──────────────────────────────────────────────────────────────
    "apron": "clothing", "backpack": "clothing", "bandage": "clothing",
    "belt": "clothing", "blanket": "clothing", "boot": "clothing",
    "cap": "clothing", "cape": "clothing", "coat": "clothing",
    "costume": "clothing", "dress": "clothing", "glove": "clothing",
    "hat": "clothing", "helmet": "clothing", "jacket": "clothing",
    "jeans": "clothing", "lace": "clothing", "mask": "clothing",
    "mitten": "clothing", "pajama": "clothing", "pants": "clothing",
    "raincoat": "clothing", "robe": "clothing", "sandal": "clothing",
    "scarf": "clothing", "shirt": "clothing", "shoe": "clothing",
    "shoelace": "clothing", "shorts": "clothing", "skirt": "clothing",
    "sleeve": "clothing", "slipper": "clothing", "sock": "clothing",
    "suit": "clothing", "sweater": "clothing", "sweatshirt": "clothing",
    "tie": "clothing", "trousers": "clothing", "tuxedo": "clothing",
    "undershirt": "clothing", "vest": "clothing", "veil": "clothing",
    "wool": "clothing", "garment": "clothing", "fabric": "clothing",
    "cotton": "clothing", "silk": "clothing", "leather": "clothing",
    "fleece": "clothing",

    # ── TOOLS / VEHICLES / DEVICES ────────────────────────────────────────────
    "airplane": "tools", "alarm": "tools", "anchor": "tools",
    "arrow": "tools", "axle": "tools", "ball": "tools",
    "bicycle": "tools", "binoculars": "tools", "boat": "tools",
    "bus": "tools", "calculator": "tools", "calendar": "tools",
    "camera": "tools", "cannon": "tools", "car": "tools",
    "cart": "tools", "compass": "tools", "computer": "tools",
    "crane": "tools", "drum": "tools", "flute": "tools",
    "fuel": "tools", "gear": "tools", "go-kart": "tools",
    "guitar": "tools", "harp": "tools", "helicopter": "tools",
    "kite": "tools", "microscope": "tools", "microphone": "tools",
    "motorcycle": "tools", "motorboat": "tools", "net": "tools",
    "oar": "tools", "paddle": "tools", "parachute": "tools",
    "pen": "tools", "pencil": "tools", "phone": "tools",
    "piano": "tools", "radio": "tools", "raft": "tools",
    "rocket": "tools", "rod": "tools", "rowboat": "tools",
    "sailboat": "tools", "sled": "tools", "spaceship": "tools",
    "spear": "tools", "submarine": "tools", "sword": "tools",
    "telescope": "tools", "television": "tools", "tent": "tools",
    "thermometer": "tools", "torch": "tools", "tractor": "tools",
    "train": "tools", "truck": "tools", "tugboat": "tools",
    "van": "tools", "violin": "tools", "wagon": "tools",
    "weapon": "tools", "wheel": "tools", "wheelbarrow": "tools",
    "whistle": "tools", "xylophone": "tools", "cymbal": "tools",
    "battery": "tools", "engine": "tools", "motor": "tools",
    "generator": "tools", "pump": "tools", "crane": "tools",
    "magnet": "tools", "lever": "tools", "pulley": "tools",
    "fulcrum": "tools", "gear": "tools", "valve": "tools",
    "scanner": "tools", "printer": "tools", "keyboard": "tools",
    "screen": "tools", "monitor": "tools", "tablet": "tools",
    "robot": "tools", "drone": "tools",

    # ── EMOTIONS ──────────────────────────────────────────────────────────────
    "afraid": "emotions", "aggression": "emotions", "amazed": "emotions",
    "amazement": "emotions", "anger": "emotions", "angry": "emotions",
    "annoyed": "emotions", "annoyance": "emotions", "anxiety": "emotions",
    "apology": "emotions", "appreciation": "emotions", "boredom": "emotions",
    "bored": "emotions", "calm": "emotions", "calmness": "emotions",
    "cheerful": "emotions", "compassion": "emotions", "confusion": "emotions",
    "courage": "emotions", "curious": "emotions", "curiosity": "emotions",
    "depression": "emotions", "desire": "emotions", "disappointment": "emotions",
    "disappointed": "emotions", "disgust": "emotions", "dislike": "emotions",
    "doubt": "emotions", "eager": "emotions", "embarrassment": "emotions",
    "emotion": "emotions", "empathy": "emotions", "enjoyment": "emotions",
    "excitement": "emotions", "excited": "emotions", "exhaustion": "emotions",
    "fear": "emotions", "frustration": "emotions", "frustrated": "emotions",
    "glad": "emotions", "gratitude": "emotions", "grateful": "emotions",
    "grief": "emotions", "guilt": "emotions", "happiness": "emotions",
    "happy": "emotions", "hate": "emotions", "heartbreak": "emotions",
    "hope": "emotions", "hopeful": "emotions", "hunger": "emotions",
    "jealousy": "emotions", "jealous": "emotions", "joy": "emotions",
    "kindness": "emotions", "loneliness": "emotions", "lonely": "emotions",
    "longing": "emotions", "love": "emotions", "mood": "emotions",
    "nervousness": "emotions", "nervous": "emotions", "pain": "emotions",
    "panic": "emotions", "patience": "emotions", "peace": "emotions",
    "peaceful": "emotions", "pride": "emotions", "proud": "emotions",
    "regret": "emotions", "relieved": "emotions", "sadness": "emotions",
    "sad": "emotions", "shame": "emotions", "shock": "emotions",
    "sorrow": "emotions", "stress": "emotions", "surprise": "emotions",
    "tension": "emotions", "thankfulness": "emotions", "thankful": "emotions",
    "thirst": "emotions", "trust": "emotions", "unhappiness": "emotions",
    "unhappy": "emotions", "worry": "emotions", "wonder": "emotions",
    "suffering": "emotions", "satisfaction": "emotions", "satisfied": "emotions",
    "cheerful": "emotions", "moody": "emotions", "wellbeing": "emotions",
    "wellness": "emotions", "temptation": "emotions", "courage": "emotions",
    "bravery": "emotions", "heroism": "emotions", "compassion": "emotions",
    "loyalty": "emotions", "jealousy": "emotions",

    # ── COGNITION ─────────────────────────────────────────────────────────────
    "ability": "cognition", "abstract": "cognition", "abstraction": "cognition",
    "accuracy": "cognition", "analyzing": "cognition", "assumption": "cognition",
    "attention": "cognition", "awareness": "cognition", "belief": "cognition",
    "comprehending": "cognition", "concept": "cognition", "conclusion": "cognition",
    "consciousness": "cognition", "creativity": "cognition", "decide": "cognition",
    "decision": "cognition", "deduction": "cognition", "definition": "cognition",
    "discovery": "cognition", "dream": "cognition", "estimate": "cognition",
    "evidence": "cognition", "focus": "cognition", "genius": "cognition",
    "hypothesis": "cognition", "idea": "cognition", "identity": "cognition",
    "imagination": "cognition", "imagine": "cognition", "inference": "cognition",
    "insight": "cognition", "intelligence": "cognition", "intention": "cognition",
    "intuition": "cognition", "judgment": "cognition", "knowledge": "cognition",
    "learning": "cognition", "logic": "cognition", "memory": "cognition",
    "mind": "cognition", "observation": "cognition", "opinion": "cognition",
    "perception": "cognition", "plan": "cognition", "prediction": "cognition",
    "principle": "cognition", "problem": "cognition", "proof": "cognition",
    "reasoning": "cognition", "recognition": "cognition", "reflection": "cognition",
    "remembering": "cognition", "skill": "cognition", "strategy": "cognition",
    "theory": "cognition", "thought": "cognition", "understanding": "cognition",
    "wisdom": "cognition", "worldview": "cognition", "daydream": "cognition",
    "scepticism": "cognition", "skepticism": "cognition", "belief": "cognition",
    "curiosity": "cognition", "creativity": "cognition",

    # ── COMMUNICATION ─────────────────────────────────────────────────────────
    "advertisement": "communication", "advice": "communication",
    "agreement": "communication", "announcement": "communication",
    "answer": "communication", "apology": "communication",
    "argument": "communication", "article": "communication",
    "asking": "communication", "book": "communication",
    "call": "communication", "chat": "communication",
    "command": "communication", "complaint": "communication",
    "conversation": "communication", "declaration": "communication",
    "description": "communication", "dialogue": "communication",
    "discussion": "communication", "document": "communication",
    "email": "communication", "explanation": "communication",
    "fable": "communication", "feedback": "communication",
    "greeting": "communication", "information": "communication",
    "instruction": "communication", "interview": "communication",
    "invitation": "communication", "joke": "communication",
    "language": "communication", "lecture": "communication",
    "letter": "communication", "lie": "communication",
    "message": "communication", "narrative": "communication",
    "news": "communication", "newspaper": "communication",
    "note": "communication", "novel": "communication",
    "phrase": "communication", "poem": "communication",
    "poetry": "communication", "promise": "communication",
    "prose": "communication", "publication": "communication",
    "question": "communication", "quote": "communication",
    "read": "communication", "report": "communication",
    "request": "communication", "riddle": "communication",
    "rumor": "communication", "saying": "communication",
    "sentence": "communication", "signal": "communication",
    "slogan": "communication", "song": "communication",
    "speech": "communication", "statement": "communication",
    "story": "communication", "suggestion": "communication",
    "summary": "communication", "tale": "communication",
    "text": "communication", "title": "communication",
    "topic": "communication", "verse": "communication",
    "vocabulary": "communication", "voice": "communication",
    "warning": "communication", "word": "communication",
    "writing": "communication", "magazine": "communication",
    "narration": "communication", "narrator": "communication",
    "comedian": "communication", "comedy": "communication",
    "drama": "communication", "storybook": "communication",

    # ── MOVEMENT ──────────────────────────────────────────────────────────────
    "ascending": "movement", "arriving": "movement", "bounce": "movement",
    "chasing": "movement", "climbing": "movement", "crawling": "movement",
    "creeping": "movement", "crossing": "movement", "dancing": "movement",
    "departing": "movement", "descending": "movement", "dipping": "movement",
    "diving": "movement", "dragging": "movement", "drifting": "movement",
    "dropping": "movement", "falling": "movement", "fleeing": "movement",
    "floating": "movement", "flying": "movement", "following": "movement",
    "gallop": "movement", "gliding": "movement", "hiking": "movement",
    "hopping": "movement", "hovering": "movement", "jogging": "movement",
    "jumping": "movement", "kicking": "movement", "launching": "movement",
    "leaping": "movement", "marching": "movement", "moving": "movement",
    "pouncing": "movement", "pulling": "movement", "pushing": "movement",
    "racing": "movement", "rising": "movement", "rolling": "movement",
    "rotating": "movement", "rowing": "movement", "running": "movement",
    "sailing": "movement", "skating": "movement", "skiing": "movement",
    "sliding": "movement", "slipping": "movement", "soaring": "movement",
    "spinning": "movement", "sprinting": "movement", "strolling": "movement",
    "swinging": "movement", "swimming": "movement", "throwing": "movement",
    "trotting": "movement", "tumbling": "movement", "turning": "movement",
    "waddling": "movement", "walking": "movement", "wandering": "movement",

    # ── SOCIAL ────────────────────────────────────────────────────────────────
    "accountability": "social", "agreeing": "social", "aid": "social",
    "assisting": "social", "authority": "social", "care": "social",
    "celebrating": "social", "collaboration": "social", "commitment": "social",
    "community": "social", "competition": "social", "conflict": "social",
    "consent": "social", "cooperation": "social", "culture": "social",
    "disagreement": "social", "fairness": "social", "forgiveness": "social",
    "friendship": "social", "generosity": "social", "governance": "social",
    "honesty": "social", "honor": "social", "justice": "social",
    "kindness": "social", "law": "social", "leadership": "social",
    "loyalty": "social", "marriage": "social", "mentoring": "social",
    "morality": "social", "parenting": "social", "participation": "social",
    "partnership": "social", "peace": "social", "permission": "social",
    "politeness": "social", "politics": "social", "power": "social",
    "punishment": "social", "relationship": "social", "respect": "social",
    "responsibility": "social", "reward": "social", "rights": "social",
    "rule": "social", "sharing": "social", "solidarity": "social",
    "teamwork": "social", "tradition": "social", "trust": "social",
    "truth": "social", "unity": "social", "upbringing": "social",
    "vote": "social", "welcome": "social", "war": "social",

    # ── STATES (physical or mental conditions) ────────────────────────────────
    "asleep": "states", "awake": "states", "aware": "states",
    "blind": "states", "broken": "states", "busy": "states",
    "calm": "states", "clean": "states", "closed": "states",
    "cold": "states", "cozy": "states", "crowded": "states",
    "damp": "states", "dead": "states", "dirty": "states",
    "dormant": "states", "dry": "states", "empty": "states",
    "exhausted": "states", "fat": "states", "filled": "states",
    "fit": "states", "fixed": "states", "flat": "states",
    "free": "states", "fresh": "states", "frozen": "states",
    "full": "states", "healthy": "states", "heavy": "states",
    "hidden": "states", "hungry": "states", "hurt": "states",
    "icy": "states", "idle": "states", "ill": "states",
    "injured": "states", "isolated": "states", "lazy": "states",
    "live": "states", "lively": "states", "locked": "states",
    "loose": "states", "lost": "states", "messy": "states",
    "missing": "states", "moist": "states", "muddy": "states",
    "neat": "states", "nervous": "states", "noisy": "states",
    "open": "states", "ordinary": "states", "organized": "states",
    "overflowing": "states", "packed": "states", "painful": "states",
    "permanent": "states", "poor": "states", "quiet": "states",
    "raw": "states", "ready": "states", "rotten": "states",
    "ruined": "states", "rusty": "states", "safe": "states",
    "sick": "states", "silent": "states", "sleepy": "states",
    "solid": "states", "sore": "states", "stable": "states",
    "steady": "states", "sticky": "states", "stiff": "states",
    "stuck": "states", "tired": "states", "torn": "states",
    "unconscious": "states", "uncertain": "states", "unclean": "states",
    "unhealthy": "states", "unstable": "states", "upset": "states",
    "visible": "states", "vulnerable": "states", "warm": "states",
    "weak": "states", "well": "states", "wet": "states",
    "wild": "states", "wrong": "states",

    # ── MATERIALS / SUBSTANCES ────────────────────────────────────────────────
    "acid": "materials", "ash": "materials", "bark": "materials",
    "brick": "materials", "bronze": "materials", "chalk": "materials",
    "clay": "materials", "cloth": "materials", "coal": "materials",
    "copper": "materials", "crystal": "materials", "diamond": "materials",
    "dust": "materials", "fiber": "materials", "foam": "materials",
    "fur": "materials", "gas": "materials", "gasoline": "materials",
    "glass": "materials", "gold": "materials", "grease": "materials",
    "ink": "materials", "jade": "materials", "latex": "materials",
    "liquid": "materials", "lotion": "materials", "marble": "materials",
    "metal": "materials", "mineral": "materials", "molecule": "materials",
    "mud": "materials", "oil": "materials", "opal": "materials",
    "paint": "materials", "paper": "materials", "petroleum": "materials",
    "plastic": "materials", "plaster": "materials", "powder": "materials",
    "quartz": "materials", "rubber": "materials", "rust": "materials",
    "sand": "materials", "sap": "materials", "sawdust": "materials",
    "silk": "materials", "silver": "materials", "smoke": "materials",
    "soap": "materials", "steel": "materials", "stone": "materials",
    "timber": "materials", "tin": "materials", "velvet": "materials",
    "vinyl": "materials", "wax": "materials", "wood": "materials",
    "wool": "materials", "cardboard": "materials", "concrete": "materials",
    "plywood": "materials", "resin": "materials", "tar": "materials",
    "thread": "materials", "yarn": "materials", "rope": "materials",
    "cotton": "materials", "leather": "materials", "denim": "materials",
    "ceramic": "materials", "porcelain": "materials",

    # ── QUANTITIES / MATH ─────────────────────────────────────────────────────
    "addition": "quantities", "algebra": "quantities", "amount": "quantities",
    "arithmetic": "quantities", "calculation": "quantities", "century": "quantities",
    "count": "quantities", "decade": "quantities", "difference": "quantities",
    "digit": "quantities", "dimension": "quantities", "division": "quantities",
    "dozen": "quantities", "equal": "quantities", "fraction": "quantities",
    "frequency": "quantities", "geometry": "quantities", "gram": "quantities",
    "half": "quantities", "hundred": "quantities", "inch": "quantities",
    "infinite": "quantities", "kilogram": "quantities", "length": "quantities",
    "liter": "quantities", "math": "quantities", "mathematics": "quantities",
    "measure": "quantities", "measurement": "quantities", "meter": "quantities",
    "mile": "quantities", "million": "quantities", "minus": "quantities",
    "multiple": "quantities", "multiplication": "quantities", "nine": "quantities",
    "number": "quantities", "numeral": "quantities", "once": "quantities",
    "one": "quantities", "ounce": "quantities", "percent": "quantities",
    "quantity": "quantities", "quarter": "quantities", "ratio": "quantities",
    "second": "quantities", "seven": "quantities", "six": "quantities",
    "size": "quantities", "subtraction": "quantities", "sum": "quantities",
    "ten": "quantities", "thirteen": "quantities", "thousand": "quantities",
    "three": "quantities", "total": "quantities", "triple": "quantities",
    "twice": "quantities", "two": "quantities", "unit": "quantities",
    "volume": "quantities", "weight": "quantities", "width": "quantities",
    "zero": "quantities", "cent": "quantities", "dime": "quantities",
    "nickel": "quantities", "dollar": "quantities", "penny": "quantities",
    "inch": "quantities", "foot": "quantities", "yard": "quantities",
    "minute": "quantities", "hour": "quantities",

    # ── COLORS ────────────────────────────────────────────────────────────────
    "black": "colors", "blue": "colors", "brown": "colors",
    "colorful": "colors", "cream": "colors", "golden": "colors",
    "gray": "colors", "green": "colors", "grey": "colors",
    "orange": "colors", "pale": "colors", "pink": "colors",
    "purple": "colors", "red": "colors", "silver": "colors",
    "tan": "colors", "teal": "colors", "violet": "colors",
    "white": "colors", "yellow": "colors",

    # ── SHAPES / GEOMETRY ─────────────────────────────────────────────────────
    "angle": "shapes", "arch": "shapes", "circle": "shapes",
    "circular": "shapes", "cone": "shapes", "cube": "shapes",
    "curve": "shapes", "cylinder": "shapes", "diamond": "shapes",
    "dome": "shapes", "edge": "shapes", "flat": "shapes",
    "globe": "shapes", "grid": "shapes", "layer": "shapes",
    "line": "shapes", "loop": "shapes", "oval": "shapes",
    "point": "shapes", "pyramid": "shapes", "rectangle": "shapes",
    "ring": "shapes", "round": "shapes", "sharp": "shapes",
    "sphere": "shapes", "spiral": "shapes", "square": "shapes",
    "star": "shapes", "straight": "shapes", "strip": "shapes",
    "symmetric": "shapes", "thin": "shapes", "triangle": "shapes",
    "tube": "shapes", "wave": "shapes", "wide": "shapes",
    "zigzag": "shapes",

    # ── SPACE / SPATIAL ───────────────────────────────────────────────────────
    "above": "space", "below": "space", "inside": "space",
    "outside": "space", "near": "space", "far": "space",
    "left": "space", "right": "space", "front": "space",
    "between": "space", "apart": "space", "aisle": "space",
    "around": "space", "back": "space", "backward": "space",
    "beside": "space", "beyond": "space", "border": "space",
    "center": "space", "close": "space", "corner": "space",
    "deep": "space", "direction": "space", "distance": "space",
    "down": "space", "east": "space", "edge": "space",
    "end": "space", "entrance": "space", "exit": "space",
    "forward": "space", "high": "space", "horizontal": "space",
    "in": "space", "location": "space", "low": "space",
    "middle": "space", "nearby": "space", "north": "space",
    "on": "space", "opposite": "space", "out": "space",
    "over": "space", "parallel": "space", "position": "space",
    "region": "space", "side": "space", "south": "space",
    "spatial": "space", "straight": "space", "through": "space",
    "top": "space", "toward": "space", "under": "space",
    "up": "space", "uphill": "space", "upright": "space",
    "upside": "space", "vertical": "space", "west": "space",
    "within": "space",

    # ── TIME / TEMPORAL ───────────────────────────────────────────────────────
    "age": "time", "afternoon": "time", "always": "time",
    "ancient": "time", "anymore": "time", "bedtime": "time",
    "birthday": "time", "cycle": "time", "date": "time",
    "dawn": "time", "decade": "time", "duration": "time",
    "early": "time", "era": "time", "eternal": "time",
    "evening": "time", "everyday": "time", "final": "time",
    "forever": "time", "frequent": "time", "future": "time",
    "generation": "time", "history": "time", "holiday": "time",
    "instant": "time", "interval": "time", "last": "time",
    "late": "time", "lifetime": "time", "lunchtime": "time",
    "midnight": "time", "milestone": "time", "moment": "time",
    "month": "time", "next": "time", "nighttime": "time",
    "noon": "time", "once": "time", "ongoing": "time",
    "past": "time", "pause": "time", "period": "time",
    "previous": "time", "prior": "time", "recent": "time",
    "regular": "time", "season": "time", "sequence": "time",
    "simultaneous": "time", "someday": "time", "soon": "time",
    "sudden": "time", "temporary": "time", "then": "time",
    "timeline": "time", "timing": "time", "today": "time",
    "tomorrow": "time", "tonight": "time", "week": "time",
    "weekday": "time", "weekend": "time", "year": "time",
    "yesterday": "time", "mealtime": "time", "playtime": "time",
    "springtime": "time", "noon": "time",

    # ── LANGUAGE / LINGUISTICS ────────────────────────────────────────────────
    "adjective": "language", "adverb": "language", "apostrophe": "language",
    "article": "language", "conjunction": "language", "grammar": "language",
    "idiom": "language", "lemma": "language", "metaphor": "language",
    "noun": "language", "paragraph": "language", "phrase": "language",
    "preposition": "language", "pronoun": "language", "punctuation": "language",
    "sentence": "language", "suffix": "language", "syllable": "language",
    "symbol": "language", "synonym": "language", "translation": "language",
    "verb": "language", "vocabulary": "language", "vowel": "language",
    "word": "language", "analogy": "language", "definition": "language",
    "description": "language", "dictionary": "language", "grammar": "language",
    "language": "language", "meaning": "language", "name": "language",
    "narrative": "language", "prefix": "language", "prose": "language",
    "script": "language", "text": "language", "title": "language",
    "translation": "language", "verse": "language", "writing": "language",

    # ── Conflict overrides (last entry wins — these fix wrong duplicates) ─────
    # Nature: dust/mud/sand/smoke/wave are natural phenomena, not materials/shapes
    "dust": "nature", "mud": "nature", "sand": "nature",
    "smoke": "nature", "wave": "nature",
    # Animals: crane is a bird, not a construction tool
    "crane": "animals",
    # Household: soap and blanket are household items
    "soap": "household", "blanket": "household",
    # Food: cream and orange are primarily food, not colors
    "cream": "food", "orange": "food",
    # Materials: silver is a metal, not just a color
    "silver": "materials",
    # Shapes: straight and flat are shape descriptors
    "straight": "shapes", "flat": "shapes",
    # Emotions: calm and nervous are emotional/mental states
    "calm": "emotions", "nervous": "emotions",
    # Cognition: belief, curiosity, creativity are mental concepts
    "belief": "cognition", "curiosity": "cognition", "creativity": "cognition",
    # Social: trust, loyalty, peace, kindness are social values
    "trust": "social", "loyalty": "social", "peace": "social", "kindness": "social",
}

# ── Existing 10 buckets (keep files that are already there) ──────────────────

EXISTING = {
    "dog", "cat", "bird", "fish", "horse", "rabbit", "bear", "wolf", "mouse", "deer",
    "tree", "flower", "water", "fire", "stone", "earth", "sky", "sun", "moon",
    "rain", "wind", "river", "mountain",
    "table", "chair", "door", "window", "key", "cup", "bowl", "book", "rope",
    "box", "bag", "bed", "floor", "wall",
    "bread", "apple", "egg", "milk", "meat", "salt", "rice", "soup", "fruit",
    "hand", "eye", "ear", "nose", "mouth", "foot", "head", "arm", "leg",
    "face", "teeth", "hair",
    "child", "friend", "family", "teacher", "mother", "father", "person",
    "baby", "man", "woman",
    "run", "walk", "eat", "sleep", "look", "speak", "carry", "give", "take",
    "open", "close", "build", "fall", "hold",
    "big", "small", "hot", "cold", "hard", "soft", "heavy", "light", "dark",
    "bright", "fast", "slow", "old", "new",
    "above", "below", "inside", "outside", "near", "far", "left", "right",
    "front", "between",
    "day", "night", "morning", "before", "after", "now",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Move unsorted concept files to semantic buckets")
    parser.add_argument("--dry-run", action="store_true", help="Print what would move without doing it")
    args = parser.parse_args()

    if not UNSORTED.exists():
        print("No unsorted/ directory found.", file=sys.stderr)
        sys.exit(1)

    # Build word→bucket lookup (skip words already in existing buckets on disk)
    moved   = 0
    skipped = 0
    unknown = 0

    # Index: unsorted files by word stem (everything before first underscore or end)
    # Files are named: word_angleslug.md — word itself may contain underscores
    # Strategy: check against BUCKETS keys directly
    bucket_words = set(BUCKETS.keys())

    # Collect all files from unsorted
    unsorted_files = sorted(UNSORTED.glob("*.md"))
    print(f"Unsorted files: {len(unsorted_files)}")

    for f in unsorted_files:
        stem = f.stem  # e.g. "afraid_boundary" or "alligator_what_is"
        # Try longest-prefix match against bucket words
        matched_word = None
        matched_bucket = None
        for word in bucket_words:
            if stem == word or stem.startswith(word + "_"):
                # Prefer longer word match to avoid "gold" matching "golden"
                if matched_word is None or len(word) > len(matched_word):
                    matched_word = word
                    matched_bucket = BUCKETS[word]

        if matched_bucket is None:
            unknown += 1
            continue

        dest_dir = WORDS_DIR / matched_bucket
        dest_file = dest_dir / f.name

        if dest_file.exists():
            skipped += 1
            continue

        if args.dry_run:
            print(f"  WOULD MOVE: {f.name} → {matched_bucket}/")
            moved += 1
        else:
            dest_dir.mkdir(parents=True, exist_ok=True)
            f.rename(dest_file)
            moved += 1

    action = "Would move" if args.dry_run else "Moved"
    print(f"{action}: {moved} files")
    print(f"Skipped (already at dest): {skipped}")
    print(f"Remaining unsorted: {unknown}")

    # Report bucket sizes
    print("\nBucket sizes after reorganization:")
    for bucket_dir in sorted(WORDS_DIR.iterdir()):
        if bucket_dir.is_dir():
            count = len(list(bucket_dir.glob("*.md")))
            print(f"  {bucket_dir.name:15s} {count:5d} files")


if __name__ == "__main__":
    main()

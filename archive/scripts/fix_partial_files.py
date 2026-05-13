#!/usr/bin/env python3
"""
Fix partial/incomplete training files by expanding them to proper 4-block format.
Targets: Phase 4 (23 files), Phase 5 (3 files), Phase 6 (17 files)
"""
from __future__ import annotations
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Phase 4 concept definitions: (concept, article, appearance, loc_prefix, behavior, purpose)
# Each entry: (filename, concept, "a"/"an", appearance_lines[], location_lines[], behavior_lines[], purpose_lines[])
PHASE4_CONCEPTS = [
    ("phase_4_12.md", "flower", "a",
     ["A flower has bright petals.", "A flower has a stem.", "A flower has color.", "A flower has a center.", "A flower has a smell.", "A flower has bright petals and color."],
     ["A flower grows in a garden.", "A flower grows in a field.", "A flower grows in a pot.", "A flower grows in the sun.", "A flower grows in soil.", "A flower grows in a garden and a field."],
     ["A flower opens in the sun.", "A flower turns toward light.", "A flower drops seeds.", "A flower fades after time.", "A flower blooms in spring.", "A flower opens in the sun and drops seeds."],
     ["A flower is for making seeds.", "A flower is for feeding bees.", "A flower is for decoration.", "A flower is for growing new plants.", "A flower is for color in a garden.", "A flower is for making seeds and decoration."]),

    ("phase_4_19.md", "chicken", "a",
     ["A chicken has feathers.", "A chicken has two legs.", "A chicken has a beak.", "A chicken has a comb on its head.", "A chicken has wings.", "A chicken has feathers and a beak."],
     ["A chicken lives in a coop.", "A chicken walks in a yard.", "A chicken stays near a barn.", "A chicken sits in a nest.", "A chicken pecks on the ground.", "A chicken lives in a coop and walks in a yard."],
     ["A chicken pecks at grain.", "A chicken scratches the dirt.", "A chicken clucks softly.", "A chicken sits on eggs.", "A chicken flaps its wings.", "A chicken pecks at grain and sits on eggs."],
     ["A chicken is for laying eggs.", "A chicken is for giving meat.", "A chicken is for pest control.", "A chicken is for providing feathers.", "A chicken is for making compost.", "A chicken is for laying eggs and giving meat."]),

    ("phase_4_23.md", "mouse", "a",
     ["A mouse has small ears.", "A mouse has a pointed nose.", "A mouse has a long tail.", "A mouse has fur.", "A mouse has whiskers.", "A mouse has small ears and a long tail."],
     ["A mouse lives in a hole.", "A mouse lives in a wall.", "A mouse lives in a field.", "A mouse lives under a floor.", "A mouse lives in a barn.", "A mouse lives in a hole and a wall."],
     ["A mouse squeaks softly.", "A mouse scurries quickly.", "A mouse gnaws on wood.", "A mouse gathers food.", "A mouse hides from cats.", "A mouse squeaks softly and scurries quickly."],
     ["A mouse is for eating seeds.", "A mouse is for being prey.", "A mouse is for spreading seeds.", "A mouse is for aerating soil.", "A mouse is for testing traps.", "A mouse is for eating seeds and being prey."]),

    ("phase_4_31.md", "grasshopper", "a",
     ["A grasshopper has long legs.", "A grasshopper has wings.", "A grasshopper has antennae.", "A grasshopper is green.", "A grasshopper has a hard shell.", "A grasshopper has long legs and wings."],
     ["A grasshopper lives in grass.", "A grasshopper lives in a field.", "A grasshopper lives in a meadow.", "A grasshopper sits on a leaf.", "A grasshopper hides under plants.", "A grasshopper lives in grass and a meadow."],
     ["A grasshopper jumps high.", "A grasshopper hops away.", "A grasshopper chirps at night.", "A grasshopper eats leaves.", "A grasshopper flies short distances.", "A grasshopper jumps high and eats leaves."],
     ["A grasshopper is for being prey.", "A grasshopper is for pollination.", "A grasshopper is for feeding birds.", "A grasshopper is for aerating soil.", "A grasshopper is for testing insect life.", "A grasshopper is for being prey and feeding birds."]),

    ("phase_4_33.md", "tadpole", "a",
     ["A tadpole has a round body.", "A tadpole has a long tail.", "A tadpole is dark.", "A tadpole has gills.", "A tadpole has no legs.", "A tadpole has a round body and a tail."],
     ["A tadpole swims in a pond.", "A tadpole lives in still water.", "A tadpole stays near the surface.", "A tadpole hides under lily pads.", "A tadpole grows in shallow water.", "A tadpole swims in a pond and shallow water."],
     ["A tadpole wiggles its tail.", "A tadpole swims in circles.", "A tadpole eats algae.", "A tadpole grows legs over time.", "A tadpole breathes with gills.", "A tadpole wiggles its tail and eats algae."],
     ["A tadpole is for growing into a frog.", "A tadpole is for eating algae.", "A tadpole is for feeding fish.", "A tadpole is for showing life cycles.", "A tadpole is for pond ecology.", "A tadpole is for growing into a frog and pond ecology."]),

    ("phase_4_35.md", "snake", "a",
     ["A snake has scales.", "A snake has no legs.", "A snake has a long body.", "A snake has a forked tongue.", "A snake has sharp teeth.", "A snake has scales and a long body."],
     ["A snake lives in grass.", "A snake lives in a cave.", "A snake lives in a desert.", "A snake lives near water.", "A snake hides under rocks.", "A snake lives in grass and near water."],
     ["A snake slithers on the ground.", "A snake flicks its tongue.", "A snake hunts for prey.", "A snake sheds its skin.", "A snake curls up to rest.", "A snake slithers on the ground and sheds its skin."],
     ["A snake is for controlling pests.", "A snake is for being part of nature.", "A snake is for balancing ecosystems.", "A snake is for eating rodents.", "A snake is for showing adaptation.", "A snake is for controlling pests and balancing ecosystems."]),

    ("phase_4_36.md", "alligator", "an",
     ["An alligator has a long snout.", "An alligator has sharp teeth.", "An alligator has rough skin.", "An alligator has four legs.", "An alligator has a strong tail.", "An alligator has a long snout and sharp teeth."],
     ["An alligator lives in a swamp.", "An alligator lives in a river.", "An alligator basks on a bank.", "An alligator floats in water.", "An alligator hides in reeds.", "An alligator lives in a swamp and a river."],
     ["An alligator swims in water.", "An alligator snaps its jaws.", "An alligator hunts for fish.", "An alligator basks in the sun.", "An alligator guards its nest.", "An alligator swims in water and basks in the sun."],
     ["An alligator is for keeping balance.", "An alligator is for digging holes.", "An alligator is for creating habitats.", "An alligator is for controlling prey.", "An alligator is for showing ancient life.", "An alligator is for keeping balance and creating habitats."]),

    ("phase_4_43.md", "jellyfish", "a",
     ["A jellyfish has a bell shape.", "A jellyfish has tentacles.", "A jellyfish is see-through.", "A jellyfish is soft.", "A jellyfish floats in water.", "A jellyfish has a bell shape and tentacles."],
     ["A jellyfish floats in the ocean.", "A jellyfish drifts in currents.", "A jellyfish lives in salt water.", "A jellyfish stays near the surface.", "A jellyfish travels in groups.", "A jellyfish floats in the ocean and drifts in currents."],
     ["A jellyfish pulses its bell.", "A jellyfish drifts with waves.", "A jellyfish stings for food.", "A jellyfish catches small fish.", "A jellyfish moves with currents.", "A jellyfish pulses its bell and stings for food."],
     ["A jellyfish is for feeding sea turtles.", "A jellyfish is for ocean drift observation.", "A jellyfish is for providing shelter.", "A jellyfish is for indicating water conditions.", "A jellyfish is for being part of food webs.", "A jellyfish is for feeding sea turtles and ocean ecology."]),

    ("phase_4_45.md", "seaweed", "",
     ["Seaweed has long strands.", "Seaweed is green or brown.", "Seaweed is slippery.", "Seaweed grows in water.", "Seaweed has no roots.", "Seaweed has long strands and grows in water."],
     ["Seaweed grows in the ocean.", "Seaweed grows on rocks.", "Seaweed grows near the shore.", "Seaweed floats in tide pools.", "Seaweed grows in shallow water.", "Seaweed grows in the ocean and near the shore."],
     ["Seaweed sways with currents.", "Seaweed provides shelter.", "Seaweed absorbs sunlight.", "Seaweed releases oxygen.", "Seaweed grows in colonies.", "Seaweed sways with currents and provides shelter."],
     ["Seaweed is for making food.", "Seaweed is for sheltering fish.", "Seaweed is for producing oxygen.", "Seaweed is for thickening products.", "Seaweed is for absorbing nutrients.", "Seaweed is for making food and producing oxygen."]),

    ("phase_4_51.md", "valley", "a",
     ["A valley has low ground.", "A valley has hills on sides.", "A valley is wide.", "A valley has grass.", "A valley has a river.", "A valley has low ground and hills on sides."],
     ["A valley lies between mountains.", "A valley is in a forest.", "A valley is near a river.", "A valley is in a countryside.", "A valley is below peaks.", "A valley lies between mountains and near a river."],
     ["A valley collects water.", "A valley channels rivers.", "A valley provides flat land.", "A valley shelters wildlife.", "A valley gathers sediment.", "A valley collects water and provides flat land."],
     ["A valley is for farming.", "A valley is for building towns.", "A valley is for wildlife habitat.", "A valley is for river flow.", "A valley is for travel routes.", "A valley is for farming and building towns."]),

    ("phase_4_55.md", "orchard", "an",
     ["An orchard has rows of trees.", "An orchard has many fruit trees.", "An orchard is large.", "An orchard has open space.", "An orchard has paths between rows.", "An orchard has rows of trees and open space."],
     ["An orchard is on a farm.", "An orchard is in the countryside.", "An orchard is on flat land.", "An orchard is near a road.", "An orchard is in a sunny area.", "An orchard is on a farm and in the countryside."],
     ["An orchard grows fruit each year.", "An orchard blooms in spring.", "An orchard produces harvest.", "An orchard attracts bees.", "An orchard provides shade.", "An orchard grows fruit each year and blooms in spring."],
     ["An orchard is for growing fruit.", "An orchard is for harvesting crops.", "An orchard is for feeding people.", "An orchard is for making cider.", "An orchard is for supporting bees.", "An orchard is for growing fruit and feeding people."]),

    ("phase_4_57.md", "rice", "",
     ["Rice is a small grain.", "Rice is white or brown.", "Rice is hard when dry.", "Rice is soft when cooked.", "Rice grows on stalks.", "Rice is a small grain and grows on stalks."],
     ["Rice grows in a paddy.", "Rice grows in water.", "Rice grows in warm climates.", "Rice grows on a farm.", "Rice grows in flooded fields.", "Rice grows in a paddy and in water."],
     ["Rice grows tall in water.", "Rice turns from green to gold.", "Rice is harvested by hand.", "Rice is threshed from stalks.", "Rice is milled for eating.", "Rice grows tall and is harvested."],
     ["Rice is for eating with meals.", "Rice is for making flour.", "Rice is for feeding many people.", "Rice is for making sake.", "Rice is for animal feed.", "Rice is for eating with meals and making flour."]),

    ("phase_4_59.md", "corn", "",
     ["Corn is a tall plant.", "Corn has a thick stalk.", "Corn has long leaves.", "Corn grows ears.", "Corn has yellow kernels.", "Corn is a tall plant with yellow kernels."],
     ["Corn grows in a field.", "Corn grows in rows.", "Corn grows in warm soil.", "Corn grows in summer.", "Corn grows on a farm.", "Corn grows in a field and in rows."],
     ["Corn grows from a seed.", "Corn reaches toward the sun.", "Corn produces ears.", "Corn is pollinated by wind.", "Corn is harvested in fall.", "Corn grows from a seed and produces ears."],
     ["Corn is for eating on the cob.", "Corn is for making flour.", "Corn is for feeding animals.", "Corn is for making oil.", "Corn is for biofuel.", "Corn is for eating and feeding animals."]),

    ("phase_4_60.md", "bean", "a",
     ["A bean is small and oval.", "A bean is green or brown.", "A bean grows in a pod.", "A bean is smooth.", "A bean is firm.", "A bean is small and oval and grows in a pod."],
     ["A bean grows on a vine.", "A bean grows in a garden.", "A bean grows in a field.", "A bean climbs a pole.", "A bean grows in warm soil.", "A bean grows on a vine and in a garden."],
     ["A bean sprouts from soil.", "A bean climbs upward.", "A bean produces flowers.", "A bean makes pods.", "A bean is picked when ripe.", "A bean sprouts from soil and climbs upward."],
     ["A bean is for eating as food.", "A bean is for making soup.", "A bean is for planting next year.", "A bean is for adding protein.", "A bean is for feeding soil.", "A bean is for eating and planting."]),

    ("phase_4_61.md", "pea", "a",
     ["A pea is small and round.", "A pea is green.", "A pea grows in a pod.", "A pea is soft.", "A pea is sweet.", "A pea is small and round and green."],
     ["A pea grows on a vine.", "A pea grows in a garden.", "A pea grows in cool weather.", "A pea hangs from a plant.", "A pea grows in a row.", "A pea grows on a vine and in a garden."],
     ["A pea grows inside a pod.", "A pea swells as it grows.", "A pea turns from flower to fruit.", "A pea is picked before it hardens.", "A pea rolls out of a pod.", "A pea grows inside a pod and is picked."],
     ["A pea is for eating as food.", "A pea is for making soup.", "A pea is for planting.", "A pea is for adding sweetness.", "A pea is for feeding livestock.", "A pea is for eating and planting."]),

    ("phase_4_62.md", "orange", "an",
     ["An orange is round.", "An orange is orange in color.", "An orange has a peel.", "An orange has segments inside.", "An orange is juicy.", "An orange is round and orange with a peel."],
     ["An orange grows on a tree.", "An orange grows in a grove.", "An orange grows in warm climates.", "An orange hangs from a branch.", "An orange grows in sunlight.", "An orange grows on a tree and in a grove."],
     ["An orange ripens on a tree.", "An orange turns from green to orange.", "An orange absorbs sunlight.", "An orange grows larger each day.", "An orange is picked by hand.", "An orange ripens on a tree and turns orange."],
     ["An orange is for eating as fruit.", "An orange is for making juice.", "An orange is for vitamin C.", "An orange is for flavoring foods.", "An orange is for making marmalade.", "An orange is for eating and making juice."]),

    ("phase_4_67.md", "pumpkin", "a",
     ["A pumpkin is large and round.", "A pumpkin is orange.", "A pumpkin has a thick skin.", "A pumpkin has a stem.", "A pumpkin has ridges.", "A pumpkin is large and round and orange."],
     ["A pumpkin grows on a vine.", "A pumpkin grows in a patch.", "A pumpkin grows on the ground.", "A pumpkin grows in a field.", "A pumpkin grows in fall.", "A pumpkin grows on a vine and in a patch."],
     ["A pumpkin starts as a flower.", "A pumpkin grows from a seed.", "A pumpkin swells on the vine.", "A pumpkin turns orange in sun.", "A pumpkin is harvested before frost.", "A pumpkin grows from a seed and swells on the vine."],
     ["A pumpkin is for carving.", "A pumpkin is for making pie.", "A pumpkin is for decoration.", "A pumpkin is for roasting seeds.", "A pumpkin is for soup.", "A pumpkin is for carving and making pie."]),

    ("phase_4_69.md", "onion", "an",
     ["An onion is round.", "An onion has layers.", "An onion is white or purple.", "An onion has a papery skin.", "An onion has a strong smell.", "An onion is round with layers and a strong smell."],
     ["An onion grows in the ground.", "An onion grows in a garden.", "An onion grows in a field.", "An onion grows in a row.", "An onion grows under soil.", "An onion grows in the ground and a garden."],
     ["An onion sprouts green shoots.", "An onion grows underground.", "An onion swells as it matures.", "An onion is pulled from soil.", "An onion is dried after harvest.", "An onion sprouts and grows underground."],
     ["An onion is for cooking food.", "An onion is for adding flavor.", "An onion is for making soup.", "An onion is for salads.", "An onion is for pickling.", "An onion is for cooking and adding flavor."]),

    ("phase_4_71.md", "lettuce", "",
     ["Lettuce has green leaves.", "Lettuce forms a head.", "Lettuce is crisp.", "Lettuce has layers.", "Lettuce is light and fresh.", "Lettuce has green leaves and forms a head."],
     ["Lettuce grows in a garden.", "Lettuce grows in cool weather.", "Lettuce grows in a row.", "Lettuce grows in a bed.", "Lettuce grows in spring.", "Lettuce grows in a garden and in cool weather."],
     ["Lettuce sprouts from seed.", "Lettuce forms leaves first.", "Lettuce grows a head.", "Lettuce is harvested at the base.", "Lettuce bolts in heat.", "Lettuce sprouts from seed and grows a head."],
     ["Lettuce is for making salad.", "Lettuce is for wrapping food.", "Lettuce is for adding crunch.", "Lettuce is for sandwiches.", "Lettuce is for garnishing plates.", "Lettuce is for making salad and sandwiches."]),

    ("phase_4_72.md", "cabbage", "a",
     ["A cabbage is round.", "A cabbage has tight leaves.", "A cabbage is green or purple.", "A cabbage is dense.", "A cabbage has a core.", "A cabbage is round with tight leaves."],
     ["A cabbage grows in a garden.", "A cabbage grows in cool weather.", "A cabbage grows in a field.", "A cabbage grows in a row.", "A cabbage grows in spring.", "A cabbage grows in a garden and in cool weather."],
     ["A cabbage starts as a seedling.", "A cabbage forms leaves outward.", "A cabbage wraps into a head.", "A cabbage grows from the inside.", "A cabbage is harvested by cutting.", "A cabbage starts as a seedling and forms a head."],
     ["A cabbage is for making coleslaw.", "A cabbage is for fermenting.", "A cabbage is for cooking.", "A cabbage is for wrapping rolls.", "A cabbage is for soups.", "A cabbage is for making coleslaw and fermenting."]),

    ("phase_4_73.md", "spinach", "",
     ["Spinach has dark green leaves.", "Spinach leaves are smooth.", "Spinach grows in bunches.", "Spinach has thin stems.", "Spinach is tender.", "Spinach has dark green leaves and thin stems."],
     ["Spinach grows in a garden.", "Spinach grows in cool weather.", "Spinach grows in a bed.", "Spinach grows in rows.", "Spinach grows in spring or fall.", "Spinach grows in a garden and in cool weather."],
     ["Spinach sprouts from seed.", "Spinach grows leaves quickly.", "Spinach matures in weeks.", "Spinach is picked leaf by leaf.", "Spinach bolts in hot weather.", "Spinach sprouts from seed and grows leaves quickly."],
     ["Spinach is for eating fresh.", "Spinach is for cooking.", "Spinach is for salads.", "Spinach is for adding iron.", "Spinach is for smoothies.", "Spinach is for eating fresh and cooking."]),

    ("phase_4_74.md", "broccoli", "",
     ["Broccoli has green flower heads.", "Broccoli has thick stalks.", "Broccoli has small buds.", "Broccoli is firm.", "Broccoli grows upright.", "Broccoli has green flower heads and thick stalks."],
     ["Broccoli grows in a garden.", "Broccoli grows in cool weather.", "Broccoli grows in a bed.", "Broccoli grows in rows.", "Broccoli grows in spring.", "Broccoli grows in a garden and in cool weather."],
     ["Broccoli sprouts from seed.", "Broccoli grows a central head.", "Broccoli produces side shoots.", "Broccoli is harvested by cutting.", "Broccoli flowers if left too long.", "Broccoli sprouts from seed and grows a central head."],
     ["Broccoli is for eating as food.", "Broccoli is for adding vitamins.", "Broccoli is for steaming.", "Broccoli is for roasting.", "Broccoli is for salads.", "Broccoli is for eating and adding vitamins."]),

    ("phase_4_091.md", "hatch", "",
     ["Hatch is a crack in a shell.", "Hatch is a breaking open.", "Hatch is a small opening.", "Hatch is a chick emerging.", "Hatch is a new beginning.", "Hatch is a crack in a shell and a new beginning."],
     ["Hatch happens in a nest.", "Hatch happens under a mother.", "Hatch happens in an incubator.", "Hatch happens in warm places.", "Hatch happens at the right time.", "Hatch happens in a nest and under a mother."],
     ["Hatch cracks the shell open.", "Hatch lets a chick out.", "Hatch takes time and effort.", "Hatch follows weeks of warmth.", "Hatch starts a new life.", "Hatch cracks the shell and starts a new life."],
     ["Hatch is for starting new life.", "Hatch is for continuing species.", "Hatch is for renewal.", "Hatch is for growth.", "Hatch is for replenishing populations.", "Hatch is for starting new life and renewal."]),
]

# Phase 5 files
PHASE5_FIXES = {
    "phase_5_15.md": (
        "a duck",
        "The duck waddles to the pond.",
        "The duck dips its beak in water.",
        "The duck drinks cool water.",
        "The duck shakes its feathers.",
        "The duck feels cool and wet.",
        "The duck waddles to the pond and drinks cool water.",
    ),
    "phase_5_45.md": (
        "children",
        "Children play in a park.",
        "Children learn in a school.",
        "Children laugh with friends.",
        "Children grow every day.",
        "Children learn new things.",
        "Children play in a park and learn in a school.",
    ),
    "phase_5_2000.md": (
        "won",
        "Won is coming in first place.",
        "Won is finishing ahead of others.",
        "Won is achieving a goal.",
        "Won is being the best.",
        "Won is earning a prize.",
        "Won is coming in first and earning a prize.",
    ),
}

# Phase 6 files - rewrite to proper 4-block
PHASE6_CONTENT = {
    "phase_6_298.md": {
        "concept": "survive",
        "article": "",
        "blocks": [
            ("What does survive look like?", [
                "Survive is living through danger.",
                "Survive is finding food and water.",
                "Survive is staying safe.",
                "Survive is lasting through hard times.",
                "Survive is continuing to exist.",
                "Survive is living through danger and finding food.",
            ]),
            ("Where does survive appear?", [
                "Survive happens in the wild.",
                "Survive happens during a storm.",
                "Survive happens in a desert.",
                "Survive happens in a cold place.",
                "Survive happens in many situations.",
                "Survive happens in the wild and during a storm.",
            ]),
            ("What does survive do?", [
                "Survive keeps a creature alive.",
                "Survive helps overcome obstacles.",
                "Survive drives adaptation.",
                "Survive builds strength.",
                "Survive tests limits.",
                "Survive keeps a creature alive and builds strength.",
            ]),
            ("What is survive for?", [
                "Survive is for staying alive.",
                "Survive is for continuing a species.",
                "Survive is for reaching safety.",
                "Survive is for overcoming challenges.",
                "Survive is for enduring hardship.",
                "Survive is for staying alive and continuing a species.",
            ]),
        ],
    },
    "phase_6_494.md": {
        "concept": "different",
        "article": "",
        "blocks": [
            ("What does different look like?", [
                "Different is not the same.",
                "Different has another shape.",
                "Different has another color.",
                "Different is unlike another.",
                "Different stands apart.",
                "Different is not the same and stands apart.",
            ]),
            ("Where is different?", [
                "Different is in a classroom.",
                "Different is among a group.",
                "Different is in a comparison.",
                "Different is between two things.",
                "Different is in a set of objects.",
                "Different is in a classroom and among a group.",
            ]),
            ("What does different do?", [
                "Different shows contrast.",
                "Different highlights variety.",
                "Different creates choice.",
                "Different marks distinction.",
                "Different separates items.",
                "Different shows contrast and highlights variety.",
            ]),
            ("What is different for?", [
                "Different is for making choices.",
                "Different is for identifying objects.",
                "Different is for comparing things.",
                "Different is for variety.",
                "Different is for sorting.",
                "Different is for making choices and comparing things.",
            ]),
        ],
    },
    "phase_6_497.md": {
        "concept": "able",
        "article": "",
        "blocks": [
            ("What does able look like?", [
                "Able is having the power to act.",
                "Able is being capable.",
                "Able is having a skill.",
                "Able is being ready.",
                "Able is having the means.",
                "Able is having the power to act and being capable.",
            ]),
            ("Where is able?", [
                "Able is in a person.",
                "Able is in a tool.",
                "Able is in a trained animal.",
                "Able is in a prepared team.",
                "Able is in a skilled worker.",
                "Able is in a person and in a trained animal.",
            ]),
            ("What does able do?", [
                "Able enables action.",
                "Able allows completion.",
                "Able makes success possible.",
                "Able gives competence.",
                "Able supports achievement.",
                "Able enables action and makes success possible.",
            ]),
            ("What is able for?", [
                "Able is for doing work.",
                "Able is for completing tasks.",
                "Able is for solving problems.",
                "Able is for helping others.",
                "Able is for achieving goals.",
                "Able is for doing work and achieving goals.",
            ]),
        ],
    },
    "phase_6_579.md": {
        "concept": "unclear",
        "article": "",
        "blocks": [
            ("What does unclear look like?", [
                "Unclear is hard to see.",
                "Unclear is blurry.",
                "Unclear is faint.",
                "Unclear is hazy.",
                "Unclear is not distinct.",
                "Unclear is hard to see and blurry.",
            ]),
            ("Where is unclear?", [
                "Unclear is in a fog.",
                "Unclear is in a shadow.",
                "Unclear is in dark water.",
                "Unclear is on a dusty window.",
                "Unclear is in a noisy room.",
                "Unclear is in a fog and in a shadow.",
            ]),
            ("What does unclear do?", [
                "Unclear hides details.",
                "Unclear confuses the eye.",
                "Unclear makes guessing hard.",
                "Unclear blurs the truth.",
                "Unclear makes things uncertain.",
                "Unclear hides details and confuses the eye.",
            ]),
            ("What is unclear for?", [
                "Unclear is for creating mystery.",
                "Unclear is for testing vision.",
                "Unclear is for requiring focus.",
                "Unclear is for slowing perception.",
                "Unclear is for showing limits.",
                "Unclear is for creating mystery and testing vision.",
            ]),
        ],
    },
    "phase_6_588.md": {
        "concept": "unconscious",
        "article": "",
        "blocks": [
            ("What does unconscious look like?", [
                "Unconscious is not awake.",
                "Unconscious is still and quiet.",
                "Unconscious is unaware.",
                "Unconscious is unresponsive.",
                "Unconscious has closed eyes.",
                "Unconscious is not awake and still and quiet.",
            ]),
            ("Where is unconscious?", [
                "Unconscious is in a hospital bed.",
                "Unconscious is after a fall.",
                "Unconscious is during deep sleep.",
                "Unconscious is under medicine.",
                "Unconscious is after a hard hit.",
                "Unconscious is in a hospital bed and after a fall.",
            ]),
            ("What does unconscious do?", [
                "Unconscious stops responses.",
                "Unconscious pauses awareness.",
                "Unconscious rests the body.",
                "Unconscious prevents movement.",
                "Unconscious blocks sensation.",
                "Unconscious stops responses and rests the body.",
            ]),
            ("What is unconscious for?", [
                "Unconscious is for healing.",
                "Unconscious is for avoiding pain.",
                "Unconscious is for deep rest.",
                "Unconscious is for medical procedures.",
                "Unconscious is for recovery.",
                "Unconscious is for healing and deep rest.",
            ]),
        ],
    },
    "phase_6_704.md": {
        "concept": "eternal",
        "article": "",
        "blocks": [
            ("What does eternal look like?", [
                "Eternal has no end.",
                "Eternal lasts forever.",
                "Eternal is endless.",
                "Eternal is timeless.",
                "Eternal goes on and on.",
                "Eternal has no end and lasts forever.",
            ]),
            ("Where is eternal?", [
                "Eternal is in stories.",
                "Eternal is in the stars.",
                "Eternal is in the sky.",
                "Eternal is in ancient stone.",
                "Eternal is in deep space.",
                "Eternal is in stories and in the stars.",
            ]),
            ("What does eternal do?", [
                "Eternal continues without stopping.",
                "Eternal never fades.",
                "Eternal remains unchanged.",
                "Eternal outlasts everything.",
                "Eternal endures forever.",
                "Eternal continues without stopping and never fades.",
            ]),
            ("What is eternal for?", [
                "Eternal is for imagining forever.",
                "Eternal is for expressing permanence.",
                "Eternal is for describing enduring love.",
                "Eternal is for showing infinity.",
                "Eternal is for timeless concepts.",
                "Eternal is for imagining forever and expressing permanence.",
            ]),
        ],
    },
    "phase_6_711.md": {
        "concept": "unreadable",
        "article": "",
        "blocks": [
            ("What does unreadable look like?", [
                "Unreadable is hard to read.",
                "Unreadable is smudged.",
                "Unreadable is too small.",
                "Unreadable is in bad light.",
                "Unreadable is a strange script.",
                "Unreadable is hard to read and smudged.",
            ]),
            ("Where is unreadable?", [
                "Unreadable is on an old scroll.",
                "Unreadable is in the dark.",
                "Unreadable is on a wet page.",
                "Unreadable is on faded paper.",
                "Unreadable is in messy handwriting.",
                "Unreadable is on an old scroll and on a wet page.",
            ]),
            ("What does unreadable do?", [
                "Unreadable hides meaning.",
                "Unreadable blocks understanding.",
                "Unreadable stops communication.",
                "Unreadable creates confusion.",
                "Unreadable prevents learning.",
                "Unreadable hides meaning and blocks understanding.",
            ]),
            ("What is unreadable for?", [
                "Unreadable is for testing patience.",
                "Unreadable is for code.",
                "Unreadable is for protecting secrets.",
                "Unreadable is for requiring tools.",
                "Unreadable is for slowing reading.",
                "Unreadable is for testing patience and protecting secrets.",
            ]),
        ],
    },
}


def write_phase4(filepath: str, concept: str, article: str,
                  appear: list, loc: list, behav: list, purp: list) -> None:
    a = article + " " if article else ""
    lines = []
    blk1_tag = f"look like"
    blk2_tag = f"appear"
    blk3_tag = f"do"
    blk4_tag = f"for"

    blocks = [
        (f"What does {a}{concept} {blk1_tag}?", appear),
        (f"Where does {a}{concept} {blk2_tag}?", loc),
        (f"What does {a}{concept} {blk3_tag}?", behav),
        (f"What is {a}{concept} {blk4_tag}?", purp),
    ]

    for i, (question, body) in enumerate(blocks):
        lines.append(f"[user]{question}")
        lines.append(f"[Ninereeds]This is {a}{concept}.")
        for b in body:
            lines.append(b)
        if i < 3:
            lines.append("")

    path = REPO / filepath
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  Wrote {filepath}")


def write_phase5(filepath: str, concept: str, *body_lines: str) -> None:
    path = REPO / filepath
    lines = [
        f"[user]What does {concept} do?",
        f"[Ninereeds]This is {concept}.",
    ]
    for b in body_lines:
        lines.append(b)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  Wrote {filepath}")


def write_phase6(filepath: str, data: dict) -> None:
    concept = data["concept"]
    article = data.get("article", "")
    a = article + " " if article else ""
    path = REPO / filepath
    lines = []
    for i, (question, body) in enumerate(data["blocks"]):
        lines.append(f"[user]{question}")
        lines.append(f"[Ninereeds]This is {a}{concept}.")
        for b in body:
            lines.append(b)
        if i < 3:
            lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  Wrote {filepath}")


def main():
    phase_dir = "training_data/phases"

    print("Writing Phase 4 files...")
    for entry in PHASE4_CONCEPTS:
        filename, concept, article, appear, loc, behav, purp = entry
        filepath = f"{phase_dir}/phase_4/{filename}"
        write_phase4(filepath, concept, article, appear, loc, behav, purp)

    print("Writing Phase 5 files...")
    for filename, (concept, *body) in PHASE5_FIXES.items():
        filepath = f"{phase_dir}/phase_5/{filename}"
        write_phase5(filepath, concept, *body)

    print("Writing Phase 6 files...")
    for filename, data in PHASE6_CONTENT.items():
        filepath = f"{phase_dir}/phase_6/{filename}"
        write_phase6(filepath, data)

    print("\nDone!")
    print(f"Total: {len(PHASE4_CONCEPTS)} Phase 4 + {len(PHASE5_FIXES)} Phase 5 + {len(PHASE6_CONTENT)} Phase 6 = {len(PHASE4_CONCEPTS) + len(PHASE5_FIXES) + len(PHASE6_CONTENT)} files")


if __name__ == "__main__":
    main()

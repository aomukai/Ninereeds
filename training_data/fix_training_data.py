#!/usr/bin/env python3
"""Fix duplicate sentence 6s in training data phases 1–3.

For each concept group (4 stories):
  Story 1: sentence 6 kept as-is (canonical definition)
  Story 2: sentence 6 replaced with a location/movement variant
  Story 3: sentence 6 replaced with a state-change variant
  Story 4: sentence 6 replaced with a function variant

Phase 2 also:
  - Fixes sentence 2 article: "A snowball is..." → "The snowball is..."
  - Fixes mass-noun openings: "This is a sunlight." → "This is sunlight."

Usage:
  python training_data/fix_training_data.py
"""

from pathlib import Path

BASE = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Sentence 6 variants.
# Key: sentence 1 exactly as it appears in the file.
# Value: dict mapping story position (2, 3, 4) to the replacement sentence 6.
# ---------------------------------------------------------------------------

VARIANTS = {

    # =========================================================================
    # PHASE 1
    # =========================================================================

    # --- Celestial / weather ---
    "This is the sun.": {
        2: "The sun is a bright light in the sky.",
        3: "The sun is a ball of heat that rises and sets.",
        4: "The sun is a warm light above the ground.",
    },
    "This is the moon.": {
        2: "The moon is a pale light that moves in the night sky.",
        3: "The moon is a round body that rises and fades.",
        4: "The moon is a soft light in the night sky.",
    },
    "This is a star.": {
        2: "A star is a small fixed point of light in the night sky.",
        3: "A star is a bright point that appears at night.",
        4: "A star is a tiny light that shines in the dark.",
    },
    "This is a cloud.": {
        2: "A cloud is a soft white shape in the sky.",
        3: "A cloud is a mass of water that can grow and break.",
        4: "A cloud is a body of water drops that brings rain.",
    },
    "This is rain.": {
        2: "Rain is water that falls to the ground.",
        3: "Rain is water that can pour and stop.",
        4: "Rain is water that wets and fills the land.",
    },
    "This is snow.": {
        2: "Snow is frozen water that covers the ground.",
        3: "Snow is frozen water that can pile up and melt.",
        4: "Snow is frozen water that cools and covers the land.",
    },
    "This is wind.": {
        2: "Wind is moving air that travels over land.",
        3: "Wind is air that can grow strong and die down.",
        4: "Wind is air that pushes and moves things.",
    },

    # --- Nature ---
    "This is a river.": {
        2: "A river is a body of water that moves between banks.",
        3: "A river is a body of water that can grow and flood.",
        4: "A river is a moving body of water that shapes the land.",
    },
    "This is a stone.": {
        2: "A stone is a hard piece of rock found on the ground.",
        3: "A stone is a hard piece of rock that can crack and break.",
        4: "A stone is a hard piece of rock used to hold things in place.",
    },
    "This is fire.": {
        2: "Fire is hot light that rises from burning.",
        3: "Fire is burning heat that grows and fades.",
        4: "Fire is burning heat that warms and gives light.",
    },

    # --- Animals ---
    "This is a dog.": {
        2: "A dog is a furry animal that runs and roams.",
        3: "A dog is an animal with fur that can run and rest.",
        4: "A dog is a furry animal kept by people.",
    },
    "This is a cat.": {
        2: "A cat is a furry animal that moves and climbs.",
        3: "A cat is an animal with fur that can sit, walk, and leap.",
        4: "A cat is a furry animal that hunts and rests.",
    },
    "This is a bird.": {
        2: "A bird is an animal with wings that lives in trees.",
        3: "A bird is a feathered animal that can fly and land.",
        4: "A bird is a winged animal that builds nests.",
    },
    "This is a fish.": {
        2: "A fish is a wet animal that moves through water.",
        3: "A fish is an animal that can swim and turn.",
        4: "A fish is an animal that swims and feeds in water.",
    },
    "This is a frog.": {
        2: "A frog is an animal that lives near water.",
        3: "A frog is an animal that can jump and swim.",
        4: "A frog is an animal that leaps and catches prey.",
    },
    "This is a horse.": {
        2: "A horse is a large animal that lives on a farm.",
        3: "A horse is an animal with hooves that can run and stop.",
        4: "A horse is a large animal that carries and pulls.",
    },
    "This is a butterfly.": {
        2: "A butterfly is an insect that flies from flower to flower.",
        3: "A butterfly is a winged insect that can open and close its wings.",
        4: "A butterfly is a winged insect that feeds on flowers.",
    },
    "This is a turtle.": {
        2: "A turtle is an animal that lives on land and in water.",
        3: "A turtle is an animal with a shell that can pull into its shell.",
        4: "A turtle is a slow animal with a hard shell for protection.",
    },
    "This is a worm.": {
        2: "A worm is a soft animal that lives in the soil.",
        3: "A worm is a long soft animal that can move through the ground.",
        4: "A worm is a soft animal that moves and feeds in the soil.",
    },
    "This is a bunny.": {
        2: "A bunny is a small furry animal that hops.",
        3: "A bunny is a soft animal that can hop and run.",
        4: "A bunny is a small soft animal with long ears.",
    },

    # --- Kitchen / household ---
    "This is a cup.": {
        2: "A cup is a small container that holds a drink.",
        3: "A cup is a small container that can fill and empty.",
        4: "A cup is a small container used for drinking.",
    },
    "This is a spoon.": {
        2: "A spoon is a small tool with a bowl end.",
        3: "A spoon is a tool that can scoop and pour.",
        4: "A spoon is a tool used for eating and stirring.",
    },
    "This is a plate.": {
        2: "A plate is a flat dish used to hold food.",
        3: "A plate is a flat dish that can fill and empty.",
        4: "A plate is a flat dish used for serving food.",
    },
    "This is a bowl.": {
        2: "A bowl is a deep dish found at the table.",
        3: "A bowl is a deep dish that can fill, spill, and empty.",
        4: "A bowl is a deep dish used for soup and cereal.",
    },
    "This is a chair.": {
        2: "A chair is a piece of furniture found in a room.",
        3: "A chair is a piece of furniture that can hold weight and move.",
        4: "A chair is a piece of furniture used for sitting.",
    },
    "This is a table.": {
        2: "A table is a flat piece of furniture in a room.",
        3: "A table is a piece of furniture with a top that can hold and support.",
        4: "A table is a flat piece of furniture used for placing things.",
    },
    "This is a door.": {
        2: "A door is a barrier found in a wall.",
        3: "A door is a barrier that can open, close, and lock.",
        4: "A door is a barrier used to enter and leave a room.",
    },
    "This is a window.": {
        2: "A window is a clear opening in a wall.",
        3: "A window is an opening in a wall that can open and close.",
        4: "A window is a clear opening used for light and air.",
    },
    "This is a bed.": {
        2: "A bed is a piece of furniture in a bedroom.",
        3: "A bed is a piece of furniture that can hold and support a body.",
        4: "A bed is a piece of furniture used for sleeping and resting.",
    },
    "This is a lamp.": {
        2: "A lamp is a device that sits in a room.",
        3: "A lamp is a device that can turn on and off.",
        4: "A lamp is a device used to light a room.",
    },

    # --- Food ---
    "This is an apple.": {
        2: "An apple is a round fruit found on a tree.",
        3: "An apple is a round fruit that can ripen and rot.",
        4: "An apple is a round fruit eaten fresh.",
    },
    "This is a banana.": {
        2: "A banana is a long fruit found on a plant.",
        3: "A banana is a long fruit that can ripen and soften.",
        4: "A banana is a long fruit eaten by peeling.",
    },
    "This is bread.": {
        2: "Bread is baked food found in a kitchen.",
        3: "Bread is food made from dough that can rise and bake.",
        4: "Bread is baked food used for eating and spreading.",
    },
    "This is milk.": {
        2: "Milk is a white liquid kept in a glass or bottle.",
        3: "Milk is a white liquid that can be warm or cold.",
        4: "Milk is a white liquid used for drinking and cooking.",
    },
    "This is an egg.": {
        2: "An egg is a food with a shell found in a nest.",
        3: "An egg is a shelled food that can crack and cook.",
        4: "An egg is a shelled food used for cooking.",
    },
    "This is a carrot.": {
        2: "A carrot is an orange vegetable that grows in the ground.",
        3: "A carrot is a root vegetable that can be pulled and eaten.",
        4: "A carrot is a crunchy vegetable eaten raw or cooked.",
    },
    "This is cheese.": {
        2: "Cheese is food made from milk found in a kitchen.",
        3: "Cheese is food made from milk that can melt and harden.",
        4: "Cheese is food made from milk used for eating.",
    },
    "This is water.": {
        2: "Water is a clear liquid found in rivers and cups.",
        3: "Water is a clear liquid that can flow, freeze, and evaporate.",
        4: "Water is a clear liquid used for drinking and washing.",
    },
    "This is a cookie.": {
        2: "A cookie is a small baked food found in a kitchen.",
        3: "A cookie is a small baked food that can crumble and soften.",
        4: "A cookie is a small sweet food eaten as a treat.",
    },
    "This is a berry.": {
        2: "A berry is a small soft fruit found on a bush.",
        3: "A berry is a small fruit that can ripen and fall.",
        4: "A berry is a small soft fruit eaten fresh.",
    },

    # --- Clothing ---
    "This is a shoe.": {
        2: "A shoe is a foot covering worn on the ground.",
        3: "A shoe is a foot covering that can get wet and dry.",
        4: "A shoe is a foot covering used for walking.",
    },
    "This is a sock.": {
        2: "A sock is a soft covering worn inside a shoe.",
        3: "A sock is a soft foot covering that can stretch and wear thin.",
        4: "A sock is a soft covering used to keep a foot warm.",
    },
    "This is a hat.": {
        2: "A hat is a head covering worn in sun or cold.",
        3: "A hat is a head covering that can sit, fall, and be lifted.",
        4: "A hat is a head covering used for warmth or shade.",
    },
    "This is a coat.": {
        2: "A coat is a piece of clothing worn outside.",
        3: "A coat is a warm piece of clothing that can get wet and dry.",
        4: "A coat is a piece of clothing used for keeping warm.",
    },
    "This is a shirt.": {
        2: "A shirt is a piece of clothing worn on the upper body.",
        3: "A shirt is a piece of clothing that can be put on and taken off.",
        4: "A shirt is a piece of clothing used to cover the upper body.",
    },
    "This is pants.": {
        2: "Pants are clothing worn on the lower body.",
        3: "Pants are clothing that can be pulled on and off.",
        4: "Pants are clothing used to cover the legs.",
    },
    "This is a glove.": {
        2: "A glove is a hand covering worn in the cold.",
        3: "A glove is a hand covering that can slip on and off.",
        4: "A glove is a hand covering used for warmth and protection.",
    },
    "This is a scarf.": {
        2: "A scarf is a piece of cloth worn around the neck.",
        3: "A scarf is a cloth that can wrap, loosen, and fall.",
        4: "A scarf is a cloth worn for warmth around the neck.",
    },
    "This is a belt.": {
        2: "A belt is a strap worn around the waist.",
        3: "A belt is a strap that can tighten, loosen, and break.",
        4: "A belt is a strap used to hold clothing in place.",
    },
    "This is a button.": {
        2: "A button is a small fastener found on clothing.",
        3: "A button is a small fastener that can close and open.",
        4: "A button is a small fastener used to join pieces of clothing.",
    },

    # --- Tools ---
    "This is a hammer.": {
        2: "A hammer is a tool with a heavy head.",
        3: "A hammer is a tool that can swing and strike.",
        4: "A hammer is a tool used for hitting nails.",
    },
    "This is a rope.": {
        2: "A rope is a long line that can be coiled or stretched.",
        3: "A rope is a long strong line that can stretch and fray.",
        4: "A rope is a strong line used for tying and pulling.",
    },
    "This is a wheel.": {
        2: "A wheel is a round object fixed to a vehicle.",
        3: "A wheel is a round object that can spin and stop.",
        4: "A wheel is a round object used for rolling and turning.",
    },
    "This is a key.": {
        2: "A key is a metal tool carried in a pocket.",
        3: "A key is a small tool that can open and lock.",
        4: "A key is a tool used for opening and locking.",
    },
    "This is a bucket.": {
        2: "A bucket is a container with a handle for carrying.",
        3: "A bucket is a container that can fill, spill, and empty.",
        4: "A bucket is a container used for carrying water and things.",
    },
    "This is a shovel.": {
        2: "A shovel is a tool with a blade at the end.",
        3: "A shovel is a tool that can dig, lift, and move soil.",
        4: "A shovel is a tool used for digging and moving earth.",
    },
    "This is a broom.": {
        2: "A broom is a long tool found in a house.",
        3: "A broom is a tool that can sweep and push dust.",
        4: "A broom is a tool used for sweeping floors.",
    },
    "This is a nail.": {
        2: "A nail is a small metal pin found in wood.",
        3: "A nail is a small metal pin that can be driven and pulled.",
        4: "A nail is a small metal pin used for joining wood.",
    },
    "This is a hook.": {
        2: "A hook is a curved object fixed to a wall.",
        3: "A hook is a curved object that can catch and hold.",
        4: "A hook is a curved object used for hanging things.",
    },
    "This is a lever.": {
        2: "A lever is a bar placed on a fixed point.",
        3: "A lever is a bar that can push down and lift up.",
        4: "A lever is a bar used for lifting heavy things.",
    },

    # --- Vehicles ---
    "This is a car.": {
        2: "A car is a vehicle that travels on roads.",
        3: "A car is a vehicle that can start, move, and stop.",
        4: "A car is a vehicle used for carrying people.",
    },
    "This is a boat.": {
        2: "A boat is a vehicle that moves on water.",
        3: "A boat is a vehicle that can float, move, and stop.",
        4: "A boat is a vehicle used for crossing water.",
    },
    "This is a train.": {
        2: "A train is a vehicle that moves along tracks.",
        3: "A train is a vehicle that can speed up and slow down.",
        4: "A train is a vehicle used for carrying people and goods.",
    },
    "This is a bike.": {
        2: "A bike is a two-wheeled vehicle ridden on a road.",
        3: "A bike is a vehicle with two wheels that can balance and fall.",
        4: "A bike is a vehicle used for riding and traveling.",
    },
    "This is a plane.": {
        2: "A plane is a vehicle that flies in the sky.",
        3: "A plane is a vehicle that can take off, fly, and land.",
        4: "A plane is a vehicle used for flying people and goods.",
    },
    "This is a bus.": {
        2: "A bus is a large vehicle that moves along roads.",
        3: "A bus is a large vehicle that can fill up and empty.",
        4: "A bus is a large vehicle used for carrying many people.",
    },
    "This is a sled.": {
        2: "A sled is a flat vehicle used on snow.",
        3: "A sled is a flat vehicle that can slide and stop.",
        4: "A sled is a vehicle used for sliding on snow.",
    },
    "This is a wagon.": {
        2: "A wagon is a flat vehicle pulled along a path.",
        3: "A wagon is a vehicle that can roll, tip, and stop.",
        4: "A wagon is a vehicle used for carrying loads.",
    },
    "This is a truck.": {
        2: "A truck is a large vehicle that moves on roads.",
        3: "A truck is a large vehicle that can load, move, and stop.",
        4: "A truck is a vehicle used for carrying heavy goods.",
    },
    "This is a ship.": {
        2: "A ship is a large vehicle that crosses water.",
        3: "A ship is a large vessel that can sail and anchor.",
        4: "A ship is a large vehicle used for carrying people and cargo.",
    },

    # --- Toys / objects ---
    "This is a block.": {
        2: "A block is a solid piece that can be stacked.",
        3: "A block is a solid piece that can be stacked and knocked down.",
        4: "A block is a solid piece used for building and playing.",
    },
    "This is a ball.": {
        2: "A ball is a round object that rolls.",
        3: "A ball is a round object that can bounce and stop.",
        4: "A ball is a round object used for throwing and catching.",
    },
    "This is a box.": {
        2: "A box is a container found in a room or on a shelf.",
        3: "A box is a container that can open, close, and hold things.",
        4: "A box is a container used for storing and carrying things.",
    },
    "This is a book.": {
        2: "A book is a set of pages found on a shelf.",
        3: "A book is a set of pages that can open, turn, and close.",
        4: "A book is a set of pages used for reading.",
    },
    "This is a doll.": {
        2: "A doll is a toy kept in a room or carried.",
        3: "A doll is a toy that can be dressed, moved, and held.",
        4: "A doll is a toy used for pretend play.",
    },
    "This is a crayon.": {
        2: "A crayon is a coloring tool held in a hand.",
        3: "A crayon is a tool that can draw, break, and wear down.",
        4: "A crayon is a tool used for coloring and drawing.",
    },
    "This is paper.": {
        2: "Paper is a flat material found on a desk.",
        3: "Paper is a flat material that can fold, tear, and burn.",
        4: "Paper is a flat material used for writing and drawing.",
    },
    "This is a ring.": {
        2: "A ring is a circular band worn on a finger.",
        3: "A ring is a small circular band that can slip on and off.",
        4: "A ring is a circular band worn for decoration.",
    },
    "This is a stick.": {
        2: "A stick is a thin piece of wood found on the ground.",
        3: "A stick is a thin piece of wood that can bend and break.",
        4: "A stick is a thin piece of wood used for poking and pointing.",
    },
    "This is a brick.": {
        2: "A brick is a solid block found in a wall.",
        3: "A brick is a solid block that can stack and fall.",
        4: "A brick is a solid block used for building walls.",
    },

    # --- Body parts ---
    "This is a hand.": {
        2: "A hand is a body part that can reach and grasp.",
        3: "A hand is a body part that can open, close, and grip.",
        4: "A hand is a body part used for holding and touching.",
    },
    "This is a foot.": {
        2: "A foot is a body part that touches the ground.",
        3: "A foot is a body part that can step, push, and rest.",
        4: "A foot is a body part used for walking and standing.",
    },
    "This is an eye.": {
        2: "An eye is a body part that takes in light.",
        3: "An eye is a body part that can open, close, and blink.",
        4: "An eye is a body part used for seeing the world.",
    },
    "This is an ear.": {
        2: "An ear is a body part found on the side of the head.",
        3: "An ear is a body part that can hear loud and soft sounds.",
        4: "An ear is a body part used for hearing.",
    },
    "This is a nose.": {
        2: "A nose is a body part that sticks out from the face.",
        3: "A nose is a body part that can breathe in and out.",
        4: "A nose is a body part used for smelling and breathing.",
    },
    "This is a mouth.": {
        2: "A mouth is a body part that opens on the face.",
        3: "A mouth is a body part that can open, chew, and close.",
        4: "A mouth is a body part used for eating and speaking.",
    },
    "This is a tooth.": {
        2: "A tooth is a hard body part found in the mouth.",
        3: "A tooth is a hard body part that can bite and wear down.",
        4: "A tooth is a hard body part used for biting and chewing.",
    },
    "This is skin.": {
        2: "Skin is the outer body covering that wraps the body.",
        3: "Skin is the body's outer layer that can stretch and heal.",
        4: "Skin is the outer body covering that protects what is inside.",
    },
    "This is hair.": {
        2: "Hair is strands that grow on the head.",
        3: "Hair is strands that can grow, cut, and fall.",
        4: "Hair is strands that grow and protect the head.",
    },
    "This is a belly.": {
        2: "A belly is the front body part below the chest.",
        3: "A belly is a body part that can fill, empty, and grow.",
        4: "A belly is the front part of the body that holds food.",
    },

    # --- Places ---
    "This is a home.": {
        2: "A home is a place with rooms and walls.",
        3: "A home is a place that can be built, lived in, and left.",
        4: "A home is a place used for living, eating, and sleeping.",
    },
    "This is a farm.": {
        2: "A farm is a place with fields and animals.",
        3: "A farm is a place where crops can grow and animals can live.",
        4: "A farm is a place used for growing food and keeping animals.",
    },
    "This is a forest.": {
        2: "A forest is a large area full of trees.",
        3: "A forest is a large area that can grow and change with seasons.",
        4: "A forest is a large wooded area that shelters animals.",
    },
    "This is a garden.": {
        2: "A garden is a small place with soil and plants.",
        3: "A garden is a place where plants can grow and wilt.",
        4: "A garden is a place used for growing plants and flowers.",
    },
    "This is a beach.": {
        2: "A beach is a sandy place next to the water.",
        3: "A beach is a sandy place that can get wet and dry.",
        4: "A beach is a sandy place where people walk and play.",
    },
    "This is a road.": {
        2: "A road is a long flat path through land.",
        3: "A road is a flat path that can get wet, crack, and wear.",
        4: "A road is a flat path used for walking and driving.",
    },
    "This is a bridge.": {
        2: "A bridge is a structure that spans over a gap.",
        3: "A bridge is a structure that can hold heavy weight and bend.",
        4: "A bridge is a structure used for crossing over water or gaps.",
    },
    "This is a field.": {
        2: "A field is a wide open area of land.",
        3: "A field is an open area that can grow grass and flood.",
        4: "A field is a large open area used for growing crops.",
    },
    "This is a pond.": {
        2: "A pond is a small still body of water.",
        3: "A pond is a small body of water that can freeze and thaw.",
        4: "A pond is a small body of water where animals live.",
    },

    # =========================================================================
    # PHASE 2
    # =========================================================================

    # --- Snow / water / light compounds ---
    "This is a snowball.": {
        2: "A snowball is a round ball of packed snow.",
        3: "A snowball is a ball of snow that can roll and break.",
        4: "A snowball is a ball of snow thrown in play.",
    },
    "This is a snowflake.": {
        2: "A snowflake is a small piece of snow that falls from the sky.",
        3: "A snowflake is a small piece of snow that melts on touch.",
        4: "A snowflake is a small piece of snow that wets what it lands on.",
    },
    "This is a snowdrift.": {
        2: "A snowdrift is a pile of snow against a wall or fence.",
        3: "A snowdrift is a pile of snow that can grow and spread.",
        4: "A snowdrift is a pile of snow that blocks paths.",
    },
    "This is a raindrop.": {
        2: "A raindrop is a drop of water that falls from the sky.",
        3: "A raindrop is a drop of water that spreads when it lands.",
        4: "A raindrop is a drop of water that adds to puddles.",
    },
    "This is a rainfall.": {
        2: "A rainfall is water that falls over fields and roofs.",
        3: "A rainfall is water that can grow heavy and stop.",
        4: "A rainfall is water that fills and feeds the land.",
    },
    "This is a waterfall.": {
        2: "A waterfall is water that falls from a cliff into a pool.",
        3: "A waterfall is water that falls and turns to mist.",
        4: "A waterfall is water that shapes rock and fills pools.",
    },
    "This is a riverbank.": {
        2: "A riverbank is the muddy side of a river.",
        3: "A riverbank is the side of a river that erodes over time.",
        4: "A riverbank is the side of a river that guides the flow.",
    },
    # These three have wrong article in S1 — fixed by MASS_NOUN_FIXES below.
    "This is a sunlight.": {
        2: "Sunlight is bright light that reaches from the sun to the ground.",
        3: "Sunlight is light from the sun that shifts and fades.",
        4: "Sunlight is light from the sun that warms and lights.",
    },
    "This is a moonlight.": {
        2: "Moonlight is pale light that falls from the moon at night.",
        3: "Moonlight is light from the moon that grows and fades.",
        4: "Moonlight is soft light from the moon that lights the dark.",
    },
    "This is a starlight.": {
        2: "Starlight is faint light that reaches from stars to the ground.",
        3: "Starlight is light from stars that appears at night.",
        4: "Starlight is light from stars that fills the night sky.",
    },

    # --- Animal structures ---
    "This is a spiderweb.": {
        2: "A spiderweb is a sticky web stretched across a gap.",
        3: "A spiderweb is a web made by a spider that can catch and break.",
        4: "A spiderweb is a web made by a spider for catching food.",
    },
    "This is a beehive.": {
        2: "A beehive is a home for bees found near flowers.",
        3: "A beehive is a home for bees that grows and fills with honey.",
        4: "A beehive is a home for bees that stores honey.",
    },
    "This is a birdhouse.": {
        2: "A birdhouse is a small house for birds up on a pole or tree.",
        3: "A birdhouse is a house for birds that can crack and be fixed.",
        4: "A birdhouse is a house for birds that shelters eggs.",
    },
    "This is an anthill.": {
        2: "An anthill is a home for ants built in the ground.",
        3: "An anthill is a home for ants that can grow and be broken.",
        4: "An anthill is a home for ants with tunnels inside.",
    },
    "This is a fishpond.": {
        2: "A fishpond is a still body of water in a garden.",
        3: "A fishpond is a pond with fish that can grow weedy and clear.",
        4: "A fishpond is a pond with fish that can be fed and kept.",
    },
    "This is a doghouse.": {
        2: "A doghouse is a small house for a dog in a yard.",
        3: "A doghouse is a house for a dog that can get wet and dry.",
        4: "A doghouse is a house for a dog that gives shelter.",
    },
    "This is a firefly.": {
        2: "A firefly is an insect with a glow found in the night air.",
        3: "A firefly is an insect that can glow and dim its light.",
        4: "A firefly is an insect that makes light in the dark.",
    },

    # --- Household compound objects ---
    "This is a bookshelf.": {
        2: "A bookshelf is a shelf for books mounted on a wall.",
        3: "A bookshelf is a shelf for books that can fill and empty.",
        4: "A bookshelf is a shelf used to store and organize books.",
    },
    "This is a doorbell.": {
        2: "A doorbell is a device set in a wall beside a door.",
        3: "A doorbell is a device that can ring and stop.",
        4: "A doorbell is a device used to signal someone is at the door.",
    },
    "This is a doorstep.": {
        2: "A doorstep is a low step at the front of a door.",
        3: "A doorstep is a step at a door that can get wet and worn.",
        4: "A doorstep is a step at a door where people stand and enter.",
    },
    "This is a doorknob.": {
        2: "A doorknob is a round handle on the side of a door.",
        3: "A doorknob is a handle for a door that can turn and click.",
        4: "A doorknob is a handle used to open and close a door.",
    },
    "This is a windowsill.": {
        2: "A windowsill is a flat ledge at the base of a window.",
        3: "A windowsill is a ledge at a window that can get wet and dry.",
        4: "A windowsill is a ledge at a window where things are placed.",
    },
    "This is a cupboard.": {
        2: "A cupboard is a shelved space fixed to a kitchen wall.",
        3: "A cupboard is a storage space that can open, fill, and empty.",
        4: "A cupboard is a storage space used for keeping food and dishes.",
    },
    "This is a bedsheet.": {
        2: "A bedsheet is a flat sheet that lies over a mattress.",
        3: "A bedsheet is a sheet for a bed that can wrinkle and be washed.",
        4: "A bedsheet is a sheet used to cover a bed for sleep.",
    },
    "This is a lampshade.": {
        2: "A lampshade is a cover that sits on top of a lamp.",
        3: "A lampshade is a cover for a lamp that can tip and be replaced.",
        4: "A lampshade is a cover for a lamp that shapes the light.",
    },

    # --- Food compounds ---
    "This is a breadcrumb.": {
        2: "A breadcrumb is a small piece of bread that falls from a loaf.",
        3: "A breadcrumb is a small piece of bread that can crumble and dry.",
        4: "A breadcrumb is a small piece of bread left after eating.",
    },
    "This is an eggshell.": {
        2: "An eggshell is the hard outer coat that wraps an egg.",
        3: "An eggshell is the outer covering of an egg that can crack and break.",
        4: "An eggshell is the outer covering of an egg that protects what is inside.",
    },
    "This is a milkshake.": {
        2: "A milkshake is a thick cold drink served in a glass.",
        3: "A milkshake is a cold drink made from milk that can melt and warm.",
        4: "A milkshake is a cold drink made from milk for sipping.",
    },
    "This is a cupcake.": {
        2: "A cupcake is a small sweet cake with a soft top.",
        3: "A cupcake is a small cake that can rise, cool, and crumble.",
        4: "A cupcake is a small cake eaten as a sweet treat.",
    },
    "This is a popcorn.": {
        2: "Popcorn is light puffed corn found in a bowl.",
        3: "Popcorn is corn that heats, pops, and cools.",
        4: "Popcorn is puffed corn eaten as a crunchy snack.",
    },

    # --- Clothing compounds ---
    "This is a shoelace.": {
        2: "A shoelace is a thin lace threaded through a shoe.",
        3: "A shoelace is a lace for a shoe that can tie and come undone.",
        4: "A shoelace is a lace used to hold a shoe on a foot.",
    },
    "This is a sweatshirt.": {
        2: "A sweatshirt is a thick warm shirt worn over the body.",
        3: "A sweatshirt is a warm shirt that can get wet and dry.",
        4: "A sweatshirt is a warm shirt worn for warmth and comfort.",
    },
    "This is a raincoat.": {
        2: "A raincoat is a waterproof coat worn in the rain.",
        3: "A raincoat is a coat for rain that can get wet and dry.",
        4: "A raincoat is a coat worn to keep dry in the rain.",
    },
    "This is a hatband.": {
        2: "A hatband is a strip of material around the base of a hat.",
        3: "A hatband is a band for a hat that can loosen and fray.",
        4: "A hatband is a band that holds and trims a hat.",
    },

    # --- Tool compounds ---
    "This is a wheelbarrow.": {
        2: "A wheelbarrow is a one-wheeled cart used in a garden.",
        3: "A wheelbarrow is a cart with one wheel that can tip and empty.",
        4: "A wheelbarrow is a cart with one wheel used for carrying heavy loads.",
    },
    "This is a screwdriver.": {
        2: "A screwdriver is a tool with a tip that fits into screws.",
        3: "A screwdriver is a tool that can turn, grip, and slip.",
        4: "A screwdriver is a tool used for driving and removing screws.",
    },
    "This is a dustpan.": {
        2: "A dustpan is a flat pan held near the floor.",
        3: "A dustpan is a pan for collecting dust that can fill and empty.",
        4: "A dustpan is a pan used with a broom to collect dust.",
    },
    "This is a handsaw.": {
        2: "A handsaw is a toothed blade held in one hand.",
        3: "A handsaw is a saw that can cut through wood with back-and-forth motion.",
        4: "A handsaw is a saw used by hand for cutting wood.",
    },

    # --- Boat compounds ---
    "This is a rowboat.": {
        2: "A rowboat is a small boat that sits on still water.",
        3: "A rowboat is a boat moved by oars that can turn and stop.",
        4: "A rowboat is a boat moved by oars used for crossing water.",
    },
    "This is a sailboat.": {
        2: "A sailboat is a boat with a sail on open water.",
        3: "A sailboat is a boat moved by wind that can sail and stop.",
        4: "A sailboat is a boat moved by wind used for sailing.",
    },
    "This is a tugboat.": {
        2: "A tugboat is a small powerful boat in a harbor.",
        3: "A tugboat is a boat that can attach, pull, and release.",
        4: "A tugboat is a boat used for pulling large ships.",
    },
    "This is a motorboat.": {
        2: "A motorboat is a fast boat with a motor on water.",
        3: "A motorboat is a boat moved by a motor that can speed up and slow down.",
        4: "A motorboat is a boat moved by a motor used for fast travel on water.",
    },
    "This is a steamboat.": {
        2: "A steamboat is a large boat with a smokestack on a river.",
        3: "A steamboat is a boat powered by steam that can build up and move.",
        4: "A steamboat is a boat powered by steam used for river travel.",
    },

    # --- Toy / play compounds ---
    "This is a dollhouse.": {
        2: "A dollhouse is a small house for dolls with tiny rooms inside.",
        3: "A dollhouse is a house for dolls that can open and be rearranged.",
        4: "A dollhouse is a small house for dolls used for pretend play.",
    },
    "This is a basketball.": {
        2: "A basketball is a large round ball on a court.",
        3: "A basketball is a round ball that can bounce, spin, and fly.",
        4: "A basketball is a large round ball used for shooting into a hoop.",
    },
    "This is a softball.": {
        2: "A softball is a large soft ball used on a field.",
        3: "A softball is a ball that can be pitched, hit, and caught.",
        4: "A softball is a large ball used for hitting with a bat.",
    },
    "This is a stickball.": {
        2: "A stickball is a small rubber ball used on a street.",
        3: "A stickball is a ball that can bounce, fly, and roll.",
        4: "A stickball is a small ball used for hitting with a stick.",
    },
    "This is a sandbox.": {
        2: "A sandbox is a low box of sand found in a yard.",
        3: "A sandbox is a box of sand that can be dug and shaped.",
        4: "A sandbox is a box of sand used for digging and playing.",
    },
    "This is a seesaw.": {
        2: "A seesaw is a long board balanced on a pivot point.",
        3: "A seesaw is a board that can tip up and come back down.",
        4: "A seesaw is a board used for riding up and down.",
    },
    "This is a pinwheel.": {
        2: "A pinwheel is a spinning toy held on a stick in the wind.",
        3: "A pinwheel is a toy that can spin fast and slow down.",
        4: "A pinwheel is a toy that spins to show the movement of wind.",
    },

    # --- Body part compounds ---
    "This is an earlobe.": {
        2: "An earlobe is the soft lower tip of an ear.",
        3: "An earlobe is the lower part of an ear that can be pinched and pulled.",
        4: "An earlobe is the soft part at the bottom of an ear.",
    },
    "This is a kneecap.": {
        2: "A kneecap is a small round bone on the front of the leg.",
        3: "A kneecap is a bone at the front of the knee that can flex and absorb impact.",
        4: "A kneecap is a bone that protects the knee joint.",
    },
    "This is an eyelid.": {
        2: "An eyelid is a thin soft cover over an eye.",
        3: "An eyelid is a cover for the eye that can open, close, and blink.",
        4: "An eyelid is a cover for the eye that protects and keeps it moist.",
    },
    "This is a fingertip.": {
        2: "A fingertip is the small soft end of a finger.",
        3: "A fingertip is the end of a finger that can press, tap, and feel.",
        4: "A fingertip is the end of a finger used for touching and feeling.",
    },
    "This is a thumbnail.": {
        2: "A thumbnail is the hard flat nail on the end of a thumb.",
        3: "A thumbnail is the nail on a thumb that can grow and break.",
        4: "A thumbnail is the nail on a thumb used for pressing and gripping.",
    },
    "This is a backbone.": {
        2: "A backbone is a row of bones that runs down the center of the back.",
        3: "A backbone is the line of bones in the back that bends and holds.",
        4: "A backbone is the line of bones in the back that holds the body up.",
    },
    "This is a jawbone.": {
        2: "A jawbone is the hard bone at the bottom of the face.",
        3: "A jawbone is the bone of the jaw that can open, close, and chew.",
        4: "A jawbone is the bone of the jaw that holds the teeth and moves for eating.",
    },
    "This is a forehead.": {
        2: "A forehead is the flat area of skin above the eyes.",
        3: "A forehead is the front of the head above the eyes that can wrinkle and sweat.",
        4: "A forehead is the front part of the head above the eyes where warmth is felt.",
    },
    "This is a shinbone.": {
        2: "A shinbone is the hard bone just under the skin on the front of the leg.",
        3: "A shinbone is the bone in the front of the lower leg that can be bruised.",
        4: "A shinbone is the bone in the front of the lower leg that supports and protects.",
    },
    "This is a collarbone.": {
        2: "A collarbone is a long bone across the top of the chest.",
        3: "A collarbone is a bone at the top of the chest that can bear pressure and break.",
        4: "A collarbone is a bone at the top of the chest that connects the shoulder.",
    },

    # --- Place compounds ---
    "This is a farmhouse.": {
        2: "A farmhouse is a house that stands in the middle of a farm.",
        3: "A farmhouse is a house on a farm that can weather and wear.",
        4: "A farmhouse is a house on a farm where farmers live.",
    },
    "This is a farmyard.": {
        2: "A farmyard is the open area around a barn on a farm.",
        3: "A farmyard is the yard of a farm that can fill with mud and animals.",
        4: "A farmyard is the yard of a farm where animals move and work is done.",
    },
    "This is a treetop.": {
        2: "A treetop is the highest part of a tree above the branches.",
        3: "A treetop is the top of a tree that sways and bends in wind.",
        4: "A treetop is the top of a tree where birds rest and nest.",
    },
    "This is a seashore.": {
        2: "A seashore is the strip of land at the edge of the sea.",
        3: "A seashore is the edge of the sea that gets wet and dries with the tide.",
        4: "A seashore is the edge of the sea where waves break and people walk.",
    },
    "This is a cornfield.": {
        2: "A cornfield is a wide flat field full of corn stalks.",
        3: "A cornfield is a field where corn grows, ripens, and is cut.",
        4: "A cornfield is a field where corn is grown for food.",
    },
    "This is a hilltop.": {
        2: "A hilltop is the open flat area at the top of a hill.",
        3: "A hilltop is the top of a hill that can be wet, dry, or windy.",
        4: "A hilltop is the top of a hill that gives a wide view.",
    },
    "This is a woodland.": {
        2: "A woodland is a quiet area filled with trees and soft ground.",
        3: "A woodland is an area covered with trees that can grow thick and thin.",
        4: "A woodland is an area of trees where animals and plants live.",
    },
    "This is a riverbed.": {
        2: "A riverbed is the stony ground that lies under a river.",
        3: "A riverbed is the ground under a river that can shift and erode.",
        4: "A riverbed is the ground under a river that shapes and guides the flow.",
    },

    # =========================================================================
    # PHASE 3
    # =========================================================================

    # --- Container + substance ---
    "This is a cup of water.": {
        2: "A cup of water is water held in a cup.",
        3: "A cup of water is water in a cup that can tip and spill.",
        4: "A cup of water is water in a cup for drinking.",
    },
    "This is a glass of milk.": {
        2: "A glass of milk is milk held in a glass.",
        3: "A glass of milk is milk in a glass that can tip and spill.",
        4: "A glass of milk is milk in a glass for drinking.",
    },
    "This is a bowl of soup.": {
        2: "A bowl of soup is hot soup sitting in a bowl.",
        3: "A bowl of soup is soup in a bowl that can tilt and spill.",
        4: "A bowl of soup is soup in a bowl for eating.",
    },
    "This is a bag of flour.": {
        2: "A bag of flour is flour stored in a soft bag.",
        3: "A bag of flour is flour in a bag that can tip and spill.",
        4: "A bag of flour is flour in a bag used for baking.",
    },
    "This is a bottle of oil.": {
        2: "A bottle of oil is oil kept in a clear bottle.",
        3: "A bottle of oil is oil in a bottle that can tip and pour.",
        4: "A bottle of oil is oil in a bottle used for cooking.",
    },
    "This is a pot of water.": {
        2: "A pot of water is water held in a pot on a stove.",
        3: "A pot of water is water in a pot that can heat and boil.",
        4: "A pot of water is water in a pot used for cooking.",
    },
    "This is a jar of honey.": {
        2: "A jar of honey is honey stored in a sealed jar.",
        3: "A jar of honey is honey in a jar that can tilt and pour.",
        4: "A jar of honey is honey in a jar used for spreading and eating.",
    },
    "This is a bucket of water.": {
        2: "A bucket of water is water carried in a bucket.",
        3: "A bucket of water is water in a bucket that can tip and spill.",
        4: "A bucket of water is water in a bucket used for washing.",
    },

    # --- Natural unit concepts ---
    "This is a drop of rain.": {
        2: "A drop of rain is a tiny amount of water falling from a cloud.",
        3: "A drop of rain is water from a cloud that can fall, hit, and spread.",
        4: "A drop of rain is water from a cloud that wets the ground.",
    },
    "This is a gust of wind.": {
        2: "A gust of wind is a sudden burst of air moving across the land.",
        3: "A gust of wind is a strong move of air that can push and die down.",
        4: "A gust of wind is a strong move of air that pushes and bends things.",
    },
    "This is a ray of sun.": {
        2: "A ray of sun is a beam of light that travels from the sun to the ground.",
        3: "A ray of sun is light from the sun that can shift and fade.",
        4: "A ray of sun is light from the sun that warms and lights what it touches.",
    },
    "This is a blade of grass.": {
        2: "A blade of grass is a thin green piece of grass in a field.",
        3: "A blade of grass is a long piece of grass that can bend and stand back up.",
        4: "A blade of grass is a thin green piece of grass that grows from the ground.",
    },
    "This is a flake of snow.": {
        2: "A flake of snow is a tiny frozen crystal that falls from a cloud.",
        3: "A flake of snow is frozen water from a cloud that can fall and melt.",
        4: "A flake of snow is frozen water from a cloud that wets what it lands on.",
    },
    "This is a crack of thunder.": {
        2: "A crack of thunder is a sharp loud sound that rolls through the sky.",
        3: "A crack of thunder is a loud sound in a storm that can spread and fade.",
        4: "A crack of thunder is a loud sound in a storm that shakes the air.",
    },
    "This is a beam of light.": {
        2: "A beam of light is a straight line of light that travels through a room.",
        3: "A beam of light is a line of light that can shift and fade.",
        4: "A beam of light is a line of light that helps things be seen.",
    },
    "This is a patch of ice.": {
        2: "A patch of ice is a flat frozen surface on the ground.",
        3: "A patch of ice is a flat piece of frozen water that can melt and spread.",
        4: "A patch of ice is a flat piece of frozen water that makes surfaces slick.",
    },
    "This is a pile of snow.": {
        2: "A pile of snow is a heap of snow that sits on the ground.",
        3: "A pile of snow is snow in a heap that can grow and melt.",
        4: "A pile of snow is a heap of snow that blocks and covers.",
    },
    "This is a sheet of rain.": {
        2: "A sheet of rain is a wide curtain of rain that falls from the sky.",
        3: "A sheet of rain is a wide fall of rain that hits and spreads.",
        4: "A sheet of rain is a wide fall of rain that soaks the ground.",
    },

    # --- Part-of concepts ---
    "This is the top of the hill.": {
        2: "The top of the hill is the highest open point above the slope.",
        3: "The top of the hill is the highest part of a hill that can change with weather.",
        4: "The top of the hill is the highest part of a hill that gives a wide view.",
    },
    "This is the edge of the road.": {
        2: "The edge of the road is the outermost line of a road.",
        3: "The edge of the road is the side of a road that can crack and wear down.",
        4: "The edge of the road is the side of a road that marks where the road ends.",
    },
    "This is the foot of the tree.": {
        2: "The foot of the tree is the wide base where the tree meets the ground.",
        3: "The foot of the tree is the base of a tree that can crack and grow.",
        4: "The foot of the tree is the base of a tree that holds the tree upright.",
    },
    "This is the bank of the river.": {
        2: "The bank of the river is the sloped edge that runs beside the water.",
        3: "The bank of the river is the side of a river that erodes and shifts.",
        4: "The bank of the river is the side of a river that guides the flow.",
    },
    "This is the rim of the cup.": {
        2: "The rim of the cup is the circular top edge around the cup.",
        3: "The rim of the cup is the top edge of a cup that can chip and crack.",
        4: "The rim of the cup is the top edge of a cup where the lips touch.",
    },
    "This is the tip of the branch.": {
        2: "The tip of the branch is the thin far end of a branch in the air.",
        3: "The tip of the branch is the end of a branch that can bend and shake.",
        4: "The tip of the branch is the end of a branch where leaves and buds grow.",
    },
    "This is the back of the hand.": {
        2: "The back of the hand is the outer surface above the palm.",
        3: "The back of the hand is the outer side of a hand that can redden and dry.",
        4: "The back of the hand is the outer side of a hand that protects the bones inside.",
    },
    "This is the neck of the bottle.": {
        2: "The neck of the bottle is the narrow top section above the body.",
        3: "The neck of the bottle is the thin top of a bottle that can drip and dry.",
        4: "The neck of the bottle is the thin top of a bottle that controls the pour.",
    },
    "This is a block of wood.": {
        2: "A block of wood is a solid piece of wood that sits on a flat surface.",
        3: "A block of wood is a solid piece of wood that can drop, crack, and splinter.",
        4: "A block of wood is a solid piece of wood used for building and support.",
    },
}

# Mass-noun S1 fixes (applied as string replacement after processing).
MASS_NOUN_FIXES = {
    "This is a sunlight.": "This is sunlight.",
    "This is a moonlight.": "This is moonlight.",
    "This is a starlight.": "This is starlight.",
    "This is a popcorn.": "This is popcorn.",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_stories(text):
    stories, cur = [], []
    for line in text.splitlines():
        line = line.strip()
        if line:
            cur.append(line)
        else:
            if cur:
                stories.append(cur)
                cur = []
    if cur:
        stories.append(cur)
    return stories


def group_by_concept(stories):
    """Group consecutive stories that share the same sentence 1."""
    groups, cur_s1, cur = [], None, []
    for story in stories:
        s1 = story[0] if story else None
        if s1 != cur_s1:
            if cur:
                groups.append(cur)
            cur_s1, cur = s1, [story]
        else:
            cur.append(story)
    if cur:
        groups.append(cur)
    return groups


def extract_concept(s1):
    """'This is a ball.' → ('a', 'ball')"""
    s = s1.rstrip('.')
    words = s.split(None, 2)
    if len(words) < 3:
        return '', s1
    rest = words[2]
    for art in ['an ', 'a ', 'the ']:
        if rest.lower().startswith(art):
            return art.strip(), rest[len(art):]
    return '', rest


def fix_s2_article(sentence, concept):
    """'A snowball is round...' → 'The snowball is round...'"""
    for art in ['An ', 'A ']:
        if sentence.startswith(art + concept):
            return 'The ' + sentence[len(art):]
    return sentence


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def process_phase(path, fix_s2=False):
    text = path.read_text(encoding='utf-8')
    stories = parse_stories(text)
    groups = group_by_concept(stories)

    fixed_stories = []
    for group in groups:
        s1 = group[0][0]
        _, concept = extract_concept(s1)
        concept_variants = VARIANTS.get(s1, {})

        for pos, story in enumerate(group, 1):
            story = list(story)

            # Fix sentence 2 article (Phase 2 only)
            if fix_s2 and len(story) >= 2:
                story[1] = fix_s2_article(story[1], concept)

            # Apply sentence 6 variant for stories 2, 3, 4+
            if pos > 1 and pos in concept_variants and len(story) == 6:
                story[5] = concept_variants[pos]

            fixed_stories.append(story)

    # Reconstruct
    lines = []
    for story in fixed_stories:
        lines.extend(story)
        lines.append('')

    result = '\n'.join(lines).strip() + '\n'

    # Fix mass-noun S1s
    for wrong, right in MASS_NOUN_FIXES.items():
        result = result.replace(wrong, right)

    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    files = [
        ("phase 1.md",  False),
        ("phase 2.md",  True),   # fix_s2=True
        ("phase 3.md",  False),
    ]

    for fname, fix_s2 in files:
        path = BASE / fname
        print(f"Processing {fname}...")
        result = process_phase(path, fix_s2=fix_s2)
        path.write_text(result, encoding='utf-8')
        print(f"  Done.")

    print("\nAll phases fixed.")


if __name__ == "__main__":
    main()

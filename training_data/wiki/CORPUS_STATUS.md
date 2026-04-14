# Corpus Status

## What we're building

A Level 1 training corpus for the BDH (Baby Dragon Hatchling) language model.
Each entry follows this format:

```
[user]what is a X?
[assistant]5-6 simple sentences. Identity + 2-3 concrete facts + 1 contrast.
X is not Y.
```

**Target level:** simple child-facing language, roughly preschool to 1st grade in tone, with room to grow later. No jargon, no Latin taxonomy, no encyclopedic depth.
**Contrast rule:** Every entry ends with "X is not Y." Both X and Y must be defined somewhere in the corpus (no dangling contrasts).

---

## Files and their status

### Clean and aligned to current Level 1 target
These files are in good shape for the current manual-cleanup pass.

| File | Notes |
|---|---|
| abstract_operators_entries.md | Entry count: 4. Reduced to actual abstract/meta anchors: `category`, `feeling`, `material`, `size` |
| animals_birds_entries.md | Entry count: 13. Lowered register; simpler distinctions, less bird-book language |
| animals_fish_entries.md | Entry count: 10. Renamed from `animals_fish_sea_entries.md`; focused on water animals only |
| animals_insects_arthropods_entries.md | Entry count: 13. Reordered with `insect` and `arthropod` first; contrasts cleaned |
| animals_reptiles_amphibians_entries.md | Entry count: 9. Added `reptile`, `amphibian`, `toad`; simplified throughout |
| agreement_and_disagreement_entries.md | Entry count: 8. New response-and-alignment category; anchors `agreement`, `disagreement`, `yes`, `no`, `I agree`, `I disagree`, `me too`, `not me` |
| accidents_and_mistakes_entries.md | Entry count: 9. New unintended-problem category; anchors `accident`, `mistake`, `oops`, `by mistake`, `I didn't mean to`, `spill`, `bump`, `fall down`, `it was an accident` |
| art_and_creative_expression_entries.md | Entry count: 9. New making-and-expression category; anchors `art`, `creativity`, `draw`, `paint`, `craft`, `decorate`, `erase`, `clay`, `collage` |
| animal_care_and_pet_keeping_entries.md | Entry count: 9. New pet-responsibility category; anchors `pet care`, `pet keeping`, `pet food`, `water bowl`, `leash`, `collar`, `litter box`, `grooming`, `vet` |
| animal_habitats_and_homes_entries.md | Entry count: 8. New habitat-and-shelter category; anchors `animal habitat`, `animal home`, `nest`, `burrow`, `den`, `hive`, `web`, `reef` |
| body_states_and_internal_cues_entries.md | Entry count: 10. New immediate-body-signal category; anchors `body signal`, `dizzy`, `itchy`, `sore`, `shiver`, `sweat`, `breathe fast`, `heart beats fast`, `need the bathroom`, `tummy hurts` |
| boundaries_and_consent_entries.md | Entry count: 8. New personal-limits category; anchors `boundary`, `personal space`, `stop`, `not okay`, `my body`, `I don't want to`, `consent`, `you may not` |
| categories_and_grouping_entries.md | Entry count: 10. New classification-language category; anchors `category`, `types of`, `belongs to`, `does not belong`, `sort`, `group`, `set`, `in the same group`, `classify`, `which one fits` |
| chores_and_home_responsibilities_entries.md | Entry count: 11. New home-task category; anchors `chore`, `responsibility`, `clean up`, `put something away`, `make the bed`, `set the table`, `sweep the floor`, `water plants`, `feed a pet`, `take out the trash`, `tidy up` |
| clothing_and_apparel_entries.md | Entry count: 14. Expanded category; now anchors `clothing`, `coat`, `jacket`, `shirt`, `hat`, `glove`, `mitten`, `pants`, `skirt`, `dress`, `sock`, `shoe`, `button`, `zipper` |
| civic_responsibility_and_community_rules_entries.md | Entry count: 9. New public-rules category; anchors `responsibility`, `authority`, `community rules`, `follow the rules`, `what's allowed`, `citizen`, `vote`, `classroom jobs`, `right` |
| communication_acts_and_language_entries.md | Entry count: 10. New conversation-mechanics category; anchors `communication`, `ask`, `answer`, `whisper`, `shout`, `explain`, `promise`, `what does that mean`, `can you say it again`, `I meant` |
| community_places_and_services_entries.md | Entry count: 12. New town-services category; anchors `community place`, `service`, `library`, `hospital`, `grocery store`, `fire station`, `police station`, `post office`, `museum`, `restaurant`, `bakery`, `bus stop` |
| conflict_resolution_and_relationship_repair_entries.md | Entry count: 7. New social-repair category; anchors `conflict resolution`, `compromise`, `forgive`, `apologize`, `let's try again`, `that's okay`, `how can we fix this` |
| construction_and_material_transformations_entries.md | Entry count: 9. New maker-change category; anchors `construction`, `repair`, `glue something`, `fold something`, `tear something`, `flatten something`, `mold something`, `shred something`, `crush something` |
| collections_and_collecting_entries.md | Entry count: 10. New collecting-practice category; anchors `collection`, `sticker`, `card`, `series`, `organize`, `trade`, `duplicate`, `complete`, `album`, `swap` |
| containers_and_capacity_entries.md | Entry count: 11. New container-usage category; anchors `container`, `bag`, `jar`, `bottle`, `basket`, `pocket`, `drawer`, `fit`, `spill`, `overflow`, `put it in` |
| cooking_and_food_preparation_entries.md | Entry count: 12. New cooking-process category; anchors `cooking`, `food preparation`, `recipe`, `ingredient`, `chop food`, `peel food`, `stir food`, `whisk`, `bake`, `simmer`, `season food`, `knead dough` |
| classroom_objects_and_school_tools_entries.md | Entry count: 9. New classroom-item category; anchors `school tool`, `ruler`, `eraser`, `glue`, `scissors`, `marker`, `whiteboard`, `glue stick`, `sharpener` |
| daily_routines_and_self_care_entries.md | Entry count: 11. New routine category; anchors `routine`, `wake up`, `get ready`, `get dressed`, `wash your hands`, `eat breakfast`, `go to school`, `pack a backpack`, `line up`, `go to bed`, `pajamas` |
| data_charts_and_graphs_entries.md | Entry count: 11. New classroom-data category; anchors `data`, `chart`, `graph`, `tally`, `tally mark`, `survey`, `result`, `most`, `least`, `bar graph`, `picture graph` |
| directions_and_navigation_entries.md | Entry count: 11. New route-and-direction category; anchors `left`, `right`, `up`, `down`, `forward`, `backward`, `turn`, `go straight`, `map`, `route`, `address` |
| degrees_of_truth_entries.md | Entry count: 9. New partial-accuracy category; anchors `half-true`, `sort of`, `mostly`, `not exactly`, `exaggerate`, `approximately`, `that's not quite right`, `roughly`, `close enough` |
| environmental_care_and_stewardship_entries.md | Entry count: 9. New earth-care category; anchors `environment`, `recycle`, `litter`, `pollution`, `conserve water`, `protect animals`, `plant a tree`, `save energy`, `take care of the earth` |
| evidence_and_justification_entries.md | Entry count: 9. New support-and-explanation category; anchors `justification`, `reason why`, `because I saw it`, `I know this because`, `example`, `for instance`, `that proves`, `I can show you`, `back it up` |
| exceptions_and_qualifications_entries.md | Entry count: 9. New flexible-rule category; anchors `usually`, `sometimes`, `except`, `not always`, `most of the time`, `in this case`, `special case`, `it depends`, `unless` |
| fractions_and_sharing_quantities_entries.md | Entry count: 9. New part-sharing math category; anchors `fraction`, `quarter`, `third`, `equal parts`, `share evenly`, `cut in half`, `one out of three`, `divide into` |
| foods_and_drinks_entries.md | Entry count: 14. Rewritten into simpler Level 1 voice; anchors reordered |
| food_groups_and_nutrition_entries.md | Entry count: 9. New food-category layer; anchors `food group`, `nutrition`, `grain`, `protein food`, `dairy`, `vitamin`, `healthy food`, `balanced meal`, `junk food` |
| friends_and_peer_interactions_entries.md | Entry count: 9. New peer-social category; anchors `friendship`, `classmate`, `teammate`, `play together`, `invite`, `argue`, `make up`, `playdate`, `be my friend` |
| future_planning_and_goals_entries.md | Entry count: 9. New long-horizon future category; anchors `plan`, `dream for the future`, `when I'm older`, `want to be`, `someday I will`, `future goal`, `work toward`, `prepare for`, `hope to` |
| growth_and_life_stages_human_entries.md | Entry count: 9. New human-development category; anchors `life stage`, `baby`, `toddler`, `child`, `teenager`, `adult`, `grown-up`, `grow up`, `when I was little` |
| garden_and_planting_basics_entries.md | Entry count: 10. New gardening-practice category; anchors `gardening`, `soil`, `compost`, `pot`, `garden bed`, `plant a seed`, `root`, `sprout`, `weed`, `give it water and sun` |
| greetings_and_social_salutations_entries.md | Entry count: 9. New conversation-opening category; anchors `greeting`, `hello`, `hi`, `good morning`, `good night`, `goodbye`, `see you later`, `nice to meet you`, `welcome` |
| group_roles_and_participation_entries.md | Entry count: 11. New role-in-group category; anchors `group role`, `leader`, `follower`, `helper`, `partner`, `team member`, `audience`, `volunteer`, `captain`, `timekeeper`, `whose turn is it` |
| health_and_wellness_entries.md | Entry count: 12. New wellness category; anchors `health`, `wellness`, `fever`, `cough`, `sore throat`, `headache`, `stomachache`, `cut`, `bruise`, `bandage`, `medicine`, `germ` |
| hobbies_and_interests_entries.md | Entry count: 8. New free-time preference category; anchors `hobby`, `interest`, `favorite thing to do`, `free time`, `collect`, `reading for fun`, `music as a hobby`, `building as a hobby` |
| holidays_and_celebrations_entries.md | Entry count: 8. New special-day category; anchors `holiday`, `celebration`, `party`, `gift`, `candle`, `special day`, `tradition`, `present` |
| humor_and_figurative_language_entries.md | Entry count: 8. New nonliteral-language category; anchors `joke`, `tease`, `sarcasm`, `idiom`, `exaggeration`, `pun`, `riddle`, `just kidding` |
| home_objects_entries_part1.md | Entry count: 7. Clean enough for current pass; migrated `book` to school category |
| home_objects_entries_part2.md | Entry count: 5. Cleaned and reordered with `furniture` as anchor; clothing removed |
| home_objects_entries_part3.md | Entry count: 6. Cleaned; `paper` migrated to school category |
| imagination_and_pretend_play_entries.md | Entry count: 9. New pretend-play category; anchors `imagination`, `pretend`, `pretend play`, `make-believe`, `dress up`, `role play`, `imaginary friend`, `symbolic play`, `game of pretend` |
| inclusion_bullying_and_kindness_entries.md | Entry count: 10. New anti-harm social category; anchors `include`, `exclude`, `bullying`, `stand up for someone`, `respect`, `compassion`, `leave them out`, `that's not kind`, `bystander`, `upstander` |
| intentions_and_plans_in_action_entries.md | Entry count: 9. New immediate-planning category; anchors `intention`, `I'm going to`, `I plan to`, `next I will`, `I'm about to`, `let's`, `shall we`, `I decided to`, `I changed my mind` |
| learning_memory_and_metacognition_entries.md | Entry count: 9. New internal-learning category; anchors `learn`, `remember`, `forget`, `practice`, `try again`, `figure out`, `I don't understand`, `I need to practice`, `I forgot` |
| logic_entries.md | Entry count: 60. Merged former `logic_core_entries.md` into this file; now the single canonical logic file |
| machines_and_simple_mechanisms_entries.md | Entry count: 9. New mechanism category; anchors `machine`, `simple machine`, `ramp`, `wheel`, `axle`, `gear`, `pulley`, `roll`, `slide` |
| meals_and_mealtime_talk_entries.md | Entry count: 9. New routine-and-talk category; anchors `meal`, `breakfast`, `lunch`, `dinner`, `snack`, `hungry`, `full`, `pass something`, `all done` |
| money_trade_and_shopping_entries.md | Entry count: 19. Expanded category; now anchors `money`, `coin`, `dollar`, `penny`, `nickel`, `dime`, `quarter`, `change`, `allowance`, `store`, `customer`, `shopkeeper`, `buy`, `sell`, `pay`, `cost`, `price`, `save`, `spend` |
| musical_instruments_entries.md | Entry count: 13. New school-music category; anchors `musical instrument`, `guitar`, `piano`, `drum`, `violin`, `flute`, `trumpet`, `recorder`, `xylophone`, `string instrument`, `wind instrument`, `percussion`, `play an instrument` |
| natural_life_cycles_and_processes_entries.md | Entry count: 10. New natural-process category; anchors `life cycle`, `plant growth`, `hatching`, `metamorphosis`, `pollination`, `hibernation`, `decomposition`, `water cycle`, `day and night pattern`, `season change` |
| numbers_beyond_10_and_large_number_talk_entries.md | Entry count: 9. New extended-number category; anchors `eleven`, `twelve`, `thirteen`, `twenty`, `one hundred`, `one thousand`, `a lot`, `about twenty`, `more than fifty` |
| opinions_persuasion_and_simple_debate_entries.md | Entry count: 10. New opinion-register category; anchors `opinion`, `I think`, `in my opinion`, `agree`, `disagree`, `persuasion`, `convince`, `reason in an argument`, `evidence`, `debate` |
| ownership_and_sharing_entries.md | Entry count: 8. New social-ownership category; anchors `ownership`, `mine`, `yours`, `borrow`, `return`, `sharing`, `can I use that`, `that's mine` |
| online_safety_and_privacy_entries.md | Entry count: 10. New internet-safety category; anchors `private`, `public`, `password`, `personal information`, `stranger online`, `report`, `block`, `don't share that`, `screen time`, `ask a grown-up` |
| personal_identity_and_self_description_entries.md | Entry count: 8. New self-introduction category; anchors `identity`, `name`, `age`, `birthday`, `grade`, `I am`, `I live in`, `about me facts` |
| perspective_taking_and_theory_of_mind_entries.md | Entry count: 8. New other-minds category; anchors `perspective`, `believe`, `misunderstand`, `I thought`, `they felt`, `she wanted`, `he didn't know that`, `put yourself in someone else's place` |
| play_games_and_sports_entries.md | Entry count: 10. New group-play category; anchors `play`, `game`, `sport`, `team`, `score`, `win`, `lose`, `cheat`, `tag`, `hide and seek` |
| praise_criticism_and_feedback_entries.md | Entry count: 9. New evaluation-language category; anchors `praise`, `criticism`, `feedback`, `well done`, `good job`, `you can do better`, `I like how you`, `encourage`, `what could be different` |
| safety_rules_and_emergency_awareness_entries.md | Entry count: 10. New safety-and-help category; anchors `safety`, `danger`, `careful`, `emergency`, `trusted adult`, `call for help`, `look both ways`, `helmet`, `seatbelt`, `not safe` |
| seasonal_activities_entries.md | Entry count: 8. New season-behavior category; anchors `seasonal activities`, `what do people do in spring`, `what do people do in summer`, `what do people do in autumn`, `what do people do in winter`, `puddle jumping`, `picnic`, `harvest` |
| sleep_and_rest_entries.md | Entry count: 10. New bedtime-and-rest category; anchors `rest`, `sleepy`, `nap`, `blanket`, `pillow`, `dream`, `nightmare`, `time for bed`, `lullaby`, `night light` |
| lost_and_found_misplacing_objects_entries.md | Entry count: 8. New missing-object category; anchors `lost`, `found`, `where is it`, `I can't find it`, `have you seen my`, `search`, `lost and found`, `left it somewhere` |
| location_and_direction_in_action_entries.md | Entry count: 8. New action-direction phrase category; anchors `come here`, `go there`, `bring it to me`, `put it on the table`, `take it outside`, `move it over`, `set it down`, `point to it` |
| levels_of_intensity_and_gradation_entries.md | Entry count: 9. New degree-word category; anchors `level of intensity`, `a little`, `a bit`, `a lot`, `very`, `really`, `enough`, `too much`, `barely` |
| movement_and_physical_action_entries.md | Entry count: 8. New bridge category; anchors `movement`, `exercise`, `balance`, `stretch`, `kick`, `bounce`, `spin`, `dance` without duplicating the main verbs file |
| material_composition_entries.md | Entry count: 9. New material-identity category; anchors `material`, `made of`, `wood`, `metal`, `plastic`, `glass`, `paper`, `fabric`, `rubber` |
| places_and_landforms_entries.md | Entry count: 40. Reordered for concept ownership; now canonical home for `forest`, `garden`, `meadow`, `orchard`, `hill` |
| plants_and_nature_entries.md | Entry count: 17. Early entries simplified; duplicate place concepts removed |
| school_life_and_learning_entries.md | Entry count: 16. New category; currently anchors `school`, `classroom`, `lesson`, `homework`, `book`, `paper`, `pencil`, `pen`, `crayon` |
| safety_signs_and_symbols_entries.md | Entry count: 11. New signs category; anchors `sign`, `symbol`, `stop sign`, `exit sign`, `danger sign`, `caution sign`, `no entry sign`, `pedestrian crossing sign`, `poison symbol`, `first aid symbol`, `slippery floor sign` |
| sensory_experiences_entries.md | Entry count: 15. New descriptive-sensory category; anchors `sound`, `loud`, `quiet`, `noisy`, `silent`, `bright`, `dim`, `sticky`, `sweet`, `sour`, `bang`, `squeak`, `roar`, `chirp`, `melody` |
| secrets_surprises_and_keeping_promises_entries.md | Entry count: 8. New trust-and-hidden-information category; anchors `secret`, `surprise`, `keep a promise`, `break a promise`, `I promised I wouldn't tell`, `surprise party`, `pinky promise`, `unsafe secret` |
| shadow_and_light_phenomena_entries.md | Entry count: 11. New light-behavior category; anchors `shadow`, `reflection`, `mirror`, `silhouette`, `beam of light`, `shine`, `glow`, `glare`, `transparent`, `opaque`, `blocks the light` |
| smells_and_tastes_entries.md | Entry count: 11. New smell-and-flavor category; anchors `smell`, `stinky`, `fresh`, `yummy`, `yucky`, `delicious`, `salty`, `bitter`, `spicy`, `it smells like`, `it tastes like` |
| sibling_relationships_and_dynamics_entries.md | Entry count: 10. New sibling-life category; anchors `sibling`, `older brother`, `younger sister`, `bossing around`, `sharing a room`, `tattletale`, `it's not fair`, `only child`, `twins`, `annoying` |
| simple_physics_energy_and_power_entries.md | Entry count: 9. New practical-energy category; anchors `energy`, `power`, `electricity`, `battery`, `fuel`, `plug`, `switch`, `flashlight`, `solar power` |
| space_entries.md | Entry count: 36. Rewritten around spatial relations and simple spatial ideas; shape/geometry teaching stays in `mathematical_concepts_entries.md` |
| STEM_entries.md | Entry count: 51. Rewritten into simpler bridge language across matter, motion, change, life, and senses |
| social_emotional_learning_competencies_entries.md | Entry count: 8. New SEL-framework category; anchors `self-management`, `social awareness`, `empathy`, `self-regulation`, `responsible decision-making`, `impulse control`, `how would you feel if`, `that was a good choice` |
| states_of_being_and_condition_entries.md | Entry count: 10. New adjective-state category; anchors `condition`, `open`, `closed`, `on`, `off`, `clean`, `dirty`, `broken`, `fixed`, `asleep` |
| story_roles_and_plot_elements_entries.md | Entry count: 9. New story-content category; anchors `character`, `setting`, `hero`, `villain`, `sidekick`, `conflict in a story`, `climax`, `moral`, `the bad guy` |
| storytelling_and_narrative_structure_entries.md | Entry count: 11. New narrative-sequencing category; anchors `story`, `beginning`, `middle`, `end`, `first`, `next`, `then`, `before`, `after`, `finally`, `at the end` |
| technology_and_digital_media_entries.md | Entry count: 10. New everyday-device category; anchors `technology`, `phone`, `tablet`, `computer`, `screen`, `app`, `video`, `message`, `swipe`, `tap` |
| time_entries.md | Entry count: 32. Rewritten into simpler child-facing time language; reduced abstract and philosophical phrasing |
| tools_and_kitchenware_entries.md | Entry count: 13. Cleaned and clarified; now includes `kitchenware` anchor |
| topology_parts_entries.md | Entry count: 8. Reworked into true part-whole entries (`neck of a bottle`, `rim of a cup`, etc.) |
| verbs_entries.md | Entry count: 77. Duplicate `drive`/`sail` removed; major simplification pass completed |
| vehicles_transport_entries.md | Entry count: 11. Polished into the current Level 1 voice; now also anchors `transport` |
| waiting_and_patience_entries.md | Entry count: 9. New self-control category; anchors `waiting`, `patience`, `turn`, `not yet`, `a little longer`, `hurry up`, `almost ready`, `wait your turn`, `stand in line` |
| weather_and_celestial_entries.md | Entry count: 17. Rewritten into simple child-facing voice; `weather` and `wave` added |
| uncertainty_and_guessing_entries.md | Entry count: 8. New hedge-and-possibility category; anchors `uncertainty`, `maybe`, `probably`, `I guess`, `not sure`, `could be`, `might`, `I wonder` |
| wants_needs_and_preferences_entries.md | Entry count: 9. New self-expression category; anchors `want`, `need`, `preference`, `I want`, `I need`, `I like`, `I dislike`, `favorite`, `prefer` |

### Clean earlier / low concern
These looked solid before the current cleanup sprint and were not major problem files.

| File | Known issues |
|---|---|
| animals_mammals_entries.md | Entry count: 22. Strong overall; now includes `human`, `monkey`, `ape`, `chimp` |
| body_parts_entries.md | Entry count: 20. No current cleanup concerns |
| colors_entries.md | Entry count: 20. Color spectrum + light/dark |
| emotions_entries.md | Entry count: 37. Expanded emotion category; now also includes `frustration`, `confusion`, `nervousness`, `jealousy`, `embarrassment`, and `relief` |
| foods_fruits_entries.md | Entry count: 21. Includes nuts cluster |
| home_rooms_entries.md | Entry count: 6. `room` moved to top as anchor |
| mathematical_concepts_entries.md | Entry count: 28. Number/shape/operation concepts + 1-10 word-to-symbol bridge + plus/minus/equals |
| measurement_and_comparison_entries.md | Entry count: 14. New measurement category; anchors `measurement`, `comparison`, `bigger`, `smaller`, `taller`, `shorter`, `heavier`, `lighter`, `length`, `height`, `weight`, `capacity`, `distance`, `estimate` |
| people_roles_entries.md | Entry count: 14. Family and social roles |
| professions_entries.md | Entry count: 23. Strong overall |

### Still worth a future pass
These are not blockers, but they may still want style cleanup, dependency review, or expansion later.

| File | Notes |
|---|---|
| foods_vegetables_entries.md | Entry count: 13. Not touched in the current cleanup sprint |
| mathematical_problems_entries.md | Entry count: 45. Still likely wants prose simplification pass |
| STEM_entries.md | Entry count: 51. May still overlap with weather/light/ice concepts and could use later ownership review |
| logic_entries.md | Entry count: 60. May still overlap with time concepts (`past`, `present`, `future`) |
| space_entries.md | Entry count: 36. May still overlap with mathematical shape vocabulary |

---

## Functional role groups

These groups are for balance evaluation, not for strict ontology.
The goal is to judge size against function, not to force every file toward the same entry count.

### Core generative infrastructure

These categories carry general sentence-building, reasoning, description, and everyday regulation load.
High depth is expected here, because these files support many other domains.

- `abstract_operators_entries.md`, `agreement_and_disagreement_entries.md`, `body_parts_entries.md`, `body_states_and_internal_cues_entries.md`, `colors_entries.md`, `communication_acts_and_language_entries.md`, `directions_and_navigation_entries.md`, `emotions_entries.md`, `greetings_and_social_salutations_entries.md`, `health_and_wellness_entries.md`, `logic_entries.md`, `mathematical_concepts_entries.md`, `measurement_and_comparison_entries.md`, `movement_and_physical_action_entries.md`, `people_roles_entries.md`, `personal_identity_and_self_description_entries.md`, `sensory_experiences_entries.md`, `space_entries.md`, `states_of_being_and_condition_entries.md`, `time_entries.md`, `topology_parts_entries.md`, `uncertainty_and_guessing_entries.md`, `verbs_entries.md`, `waiting_and_patience_entries.md`, `wants_needs_and_preferences_entries.md`

### World-anchor inventories

These files mainly give the model enough breadth to recognize and talk about common parts of the world.
They usually want broad passive coverage, but not exhaustive encyclopedic depth.

- `animal_care_and_pet_keeping_entries.md`, `animal_habitats_and_homes_entries.md`, `animals_birds_entries.md`, `animals_fish_entries.md`, `animals_insects_arthropods_entries.md`, `animals_mammals_entries.md`, `animals_reptiles_amphibians_entries.md`, `classroom_objects_and_school_tools_entries.md`, `clothing_and_apparel_entries.md`, `community_places_and_services_entries.md`, `food_groups_and_nutrition_entries.md`, `foods_and_drinks_entries.md`, `foods_fruits_entries.md`, `foods_vegetables_entries.md`, `garden_and_planting_basics_entries.md`, `home_objects_entries_part1.md`, `home_objects_entries_part2.md`, `home_objects_entries_part3.md`, `home_rooms_entries.md`, `machines_and_simple_mechanisms_entries.md`, `material_composition_entries.md`, `musical_instruments_entries.md`, `numbers_beyond_10_and_large_number_talk_entries.md`, `places_and_landforms_entries.md`, `plants_and_nature_entries.md`, `professions_entries.md`, `school_life_and_learning_entries.md`, `simple_physics_energy_and_power_entries.md`, `tools_and_kitchenware_entries.md`, `vehicles_transport_entries.md`, `weather_and_celestial_entries.md`

### Example-bearing pragmatic and social sets

These categories work best as representative sets of common patterns, scripts, and situations.
They usually do not need huge inventories; too much depth here can create odd weighting or redundancy.

- `accidents_and_mistakes_entries.md`, `art_and_creative_expression_entries.md`, `boundaries_and_consent_entries.md`, `chores_and_home_responsibilities_entries.md`, `civic_responsibility_and_community_rules_entries.md`, `collections_and_collecting_entries.md`, `conflict_resolution_and_relationship_repair_entries.md`, `construction_and_material_transformations_entries.md`, `cooking_and_food_preparation_entries.md`, `daily_routines_and_self_care_entries.md`, `environmental_care_and_stewardship_entries.md`, `evidence_and_justification_entries.md`, `friends_and_peer_interactions_entries.md`, `future_planning_and_goals_entries.md`, `growth_and_life_stages_human_entries.md`, `hobbies_and_interests_entries.md`, `holidays_and_celebrations_entries.md`, `humor_and_figurative_language_entries.md`, `imagination_and_pretend_play_entries.md`, `inclusion_bullying_and_kindness_entries.md`, `learning_memory_and_metacognition_entries.md`, `meals_and_mealtime_talk_entries.md`, `money_trade_and_shopping_entries.md`, `online_safety_and_privacy_entries.md`, `opinions_persuasion_and_simple_debate_entries.md`, `ownership_and_sharing_entries.md`, `play_games_and_sports_entries.md`, `praise_criticism_and_feedback_entries.md`, `safety_rules_and_emergency_awareness_entries.md`, `safety_signs_and_symbols_entries.md`, `seasonal_activities_entries.md`, `secrets_surprises_and_keeping_promises_entries.md`, `sibling_relationships_and_dynamics_entries.md`, `sleep_and_rest_entries.md`, `social_emotional_learning_competencies_entries.md`, `technology_and_digital_media_entries.md`

### Bridge and modifier categories

These files connect, qualify, structure, or lightly abstract other knowledge.
They should usually stay compact and high-signal unless repeated use shows a real need for expansion.

- `categories_and_grouping_entries.md`, `containers_and_capacity_entries.md`, `data_charts_and_graphs_entries.md`, `degrees_of_truth_entries.md`, `exceptions_and_qualifications_entries.md`, `fractions_and_sharing_quantities_entries.md`, `group_roles_and_participation_entries.md`, `intentions_and_plans_in_action_entries.md`, `levels_of_intensity_and_gradation_entries.md`, `location_and_direction_in_action_entries.md`, `natural_life_cycles_and_processes_entries.md`, `perspective_taking_and_theory_of_mind_entries.md`, `STEM_entries.md`, `story_roles_and_plot_elements_entries.md`, `storytelling_and_narrative_structure_entries.md`

### Working interpretation

- `Core generative infrastructure` can justifiably be large.
- `World-anchor inventories` should be broad enough for passive recognition and common recall, but not encyclopedic.
- `Example-bearing pragmatic and social sets` should usually stay selective and representative.
- `Bridge and modifier categories` should stay tight unless repeated corpus use proves they need more depth.

---

## Dependencies

This section is about learning readiness.
The question is not only "what does this file contain?"
The question is also "what should the model already understand before this file is likely to teach cleanly?"

### Dependency types

- **Vocabulary prerequisites:** concrete words the file will rely on directly, such as body parts, common objects, motion words, or basic time words.
- **Concept prerequisites:** earlier ideas the file builds on, such as category membership, part-whole reasoning, cause and effect, ownership, or sequence.
- **Pragmatic prerequisites:** social or discourse habits the file assumes, such as turn-taking, repair, asking, comparing, or perspective-shifting.

### Dependency profile by role

#### Core generative infrastructure

These files should usually come earliest or be reinforced repeatedly, because many later files depend on them.

- Typical vocabulary prerequisites: high-frequency body, object, place, and action words
- Typical concept prerequisites: very light; many of these files are themselves prerequisites for the rest of the corpus
- Typical pragmatic prerequisites: minimal; these often establish the core interaction layer
- Examples:
  - `time_entries.md` depends on basic event language and sequence words
  - `space_entries.md` depends on concrete object language and location talk
  - `logic_entries.md` depends on stable concrete examples before abstract contrasts will make sense
  - `emotions_entries.md` depends on simple people-and-event understanding before more nuanced feeling labels become useful

#### World-anchor inventories

These files usually depend on the core layer being stable first.
A model needs enough general language to attach the inventory items to something meaningful.

- Typical vocabulary prerequisites: basic nouns, adjectives, and action words
- Typical concept prerequisites: category membership, part-whole structure, simple function or habitat reasoning
- Typical pragmatic prerequisites: low; these are more recognition-heavy than interaction-heavy
- Examples:
  - `animals_birds_entries.md` depends on the broader idea of `animal`, visible body-part words, and simple habitat/action language
  - `musical_instruments_entries.md` depends on object language, sound words, and action words like play, hit, blow, or hold
  - `community_places_and_services_entries.md` depends on person-role and action-function language
  - `material_composition_entries.md` depends on object recognition plus `made of` or part-material reasoning

#### Example-bearing pragmatic and social sets

These files need the model to already have enough core language to understand the script, not just the words.
They are often late because they combine feeling, intention, consequence, and social repair.

- Typical vocabulary prerequisites: feelings, action words, time words, person-role language
- Typical concept prerequisites: cause and effect, goals, rules, ownership, fairness, truth, and choice
- Typical pragmatic prerequisites: turn-taking, asking, answering, reacting, apologizing, or interpreting another person's move
- Examples:
  - `conflict_resolution_and_relationship_repair_entries.md` depends on emotions, problem/solution logic, and peer interaction language
  - `online_safety_and_privacy_entries.md` depends on rules, boundaries, technology words, and trusted-adult framing
  - `praise_criticism_and_feedback_entries.md` depends on action quality, goals, effort, and evaluation language
  - `secrets_surprises_and_keeping_promises_entries.md` depends on truth, trust, intention, and safety reasoning

#### Bridge and modifier categories

These files usually depend on both vocabulary and structure already being present.
They do not stand well on their own because their job is to qualify or organize other knowledge.

- Typical vocabulary prerequisites: enough noun and verb coverage to have something to sort, compare, qualify, or divide
- Typical concept prerequisites: same/different, part-whole, degree, category, rule, sequence, or evidence
- Typical pragmatic prerequisites: often medium; many of these support explanation rather than basic naming
- Examples:
  - `categories_and_grouping_entries.md` depends on having multiple stable object domains already learned
  - `degrees_of_truth_entries.md` depends on truth-language, uncertainty, and comparison
  - `fractions_and_sharing_quantities_entries.md` depends on number language plus part-whole and fairness
  - `story_roles_and_plot_elements_entries.md` depends on `storytelling_and_narrative_structure_entries.md`, emotion language, and problem/solution logic

### Representative dependency chains

These are not strict one-file-only pipelines.
They are working examples of the kinds of dependencies the wiki should respect.

- `body_parts_entries.md` -> `body_states_and_internal_cues_entries.md` -> `health_and_wellness_entries.md`
- `space_entries.md` -> `directions_and_navigation_entries.md` -> `location_and_direction_in_action_entries.md`
- `people_roles_entries.md` -> `friends_and_peer_interactions_entries.md` -> `conflict_resolution_and_relationship_repair_entries.md`
- `logic_entries.md` -> `uncertainty_and_guessing_entries.md` -> `degrees_of_truth_entries.md` -> `evidence_and_justification_entries.md`
- `foods_and_drinks_entries.md` -> `meals_and_mealtime_talk_entries.md` -> `food_groups_and_nutrition_entries.md`
- `plants_and_nature_entries.md` -> `garden_and_planting_basics_entries.md` -> `environmental_care_and_stewardship_entries.md`
- `animals_*` core files -> `animal_habitats_and_homes_entries.md` -> `animal_care_and_pet_keeping_entries.md`
- `storytelling_and_narrative_structure_entries.md` -> `story_roles_and_plot_elements_entries.md` -> `humor_and_figurative_language_entries.md`
- `communication_acts_and_language_entries.md` -> `agreement_and_disagreement_entries.md` -> `praise_criticism_and_feedback_entries.md`
- `ownership_and_sharing_entries.md` -> `fractions_and_sharing_quantities_entries.md` -> `fairness`-heavy social files such as `sibling_relationships_and_dynamics_entries.md`

### Working use

This section should be used in three ways:

- before adding new entries to ask whether the file has enough earlier support
- during cleanup to see whether a file is too abstract for its current prerequisites
- during balance review to decide whether a sparse file is actually underbuilt or simply waiting on earlier concepts

For file-specific dependency notes, `training_data/wiki/wiki_category_backlog.md` remains the detailed category-level source of truth.

---

## Design principles

- **Vocabulary dependency:** No word appears in a problem or entry before it has been defined elsewhere in the corpus.
- **Bidirectional contrasts:** If entry A says "A is not B", entry B should exist and ideally say "B is not A."
- **No computation math** in concept files. Math concepts file covers number/shape/operation as language. Math problems file covers grade 1 arithmetic with known vocabulary only.
- **Cross-domain linking:** Entries reference other domains naturally (e.g. professions link to tools, animals link to plants).
- **Clear concept ownership:** prefer one canonical `what is X?` home per concept whenever possible.
- **General before specific:** broader anchors should usually appear before narrower concepts inside a file.

## Known dangling contrasts

These words appear as contrast targets (`X is not Y`) but do not yet have their
own entry. Each one is a candidate for later expansion.

| Word | Appears in | Priority |
|---|---|---|
| tiger | animals_mammals | medium |
| magazine | school_life_and_learning | low |
| fog | weather_and_celestial | medium |
| breeze | weather_and_celestial | low |
| lightning | weather_and_celestial | high |
| darkness | weather_and_celestial | medium |
| puddle | weather_and_celestial | low |
| climate | weather_and_celestial | low |
| raven | animals_birds | low |
| plantain | foods_fruits | low |
| numeral | mathematical_concepts | low |

## Next steps

1. Start the broader quality pass now that the missing-category batch is complete
2. Review untouched or partially touched files like `foods_vegetables_entries.md`
3. Run a corpus-wide dependency and contrast pass across the whole wiki
4. Tighten category balance, ownership, and overlap across the full 88-category set
5. Use `wiki_implementation_todo.md` as the practical queue for partial-category expansion and recurring anchor-review checks

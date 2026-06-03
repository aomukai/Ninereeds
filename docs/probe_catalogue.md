# Ninereeds Probe Catalogue
# docs/probe_catalogue.md
#
# Purpose: Structured activation probes for brain_map.py
# Each probe pokes a concept and we observe WHICH cluster lights up
# and WHETHER that cluster is tight (good) or fuzzy (needs work).
#
# Workflow:
#   1. Run probes → brain_map.py produces PCA scatter + similarity heatmap
#   2. Unexpected cluster activation → grep corpus for the concept
#   3. Audit co-occurrence patterns → identify teaching cause
#   4. Fix corpus or add targeted teaching stories
#
# Probe format (JSONL, one probe per line):
#   {"id": "...", "lang": "EN", "text": "...", "expected_cluster": "...", "category": "..."}
#
# Result interpretation:
#   PASS:  probe activates inside expected cluster, cluster is tight (high μ)
#   WARN:  probe activates near expected cluster but with bleed into adjacent cluster
#   FAIL:  probe activates inside wrong cluster entirely
#   FUZZY: probe activates in expected cluster but cluster μ is low (< 0.75)

---

## CLUSTER GROUP 1: Animals

### 1.1 Superordinate — does an ANIMAL cluster exist?

Probe a spread of animals and check whether they form one superordinate cluster
or fragment into unrelated positions.

Expected geometry: all animal probes within one macro-region of PCA space,
with mammal/bird/fish as visible subclusters inside it.

| id | lang | probe text | expected cluster |
|----|------|-----------|-----------------|
| an_super_01 | EN | What is a dog? | animals/mammals |
| an_super_02 | EN | What is a cat? | animals/mammals |
| an_super_03 | EN | What is a rabbit? | animals/mammals |
| an_super_04 | EN | What is a horse? | animals/mammals |
| an_super_05 | EN | What is an eagle? | animals/birds |
| an_super_06 | EN | What is a sparrow? | animals/birds |
| an_super_07 | EN | What is a crow? | animals/birds |
| an_super_08 | EN | What is a salmon? | animals/fish |
| an_super_09 | EN | What is a frog? | animals/amphibians |
| an_super_10 | EN | What is a snake? | animals/reptiles |

FAIL condition: dog and bicycle activate in the same region.
WARN condition: birds and fish are indistinguishable subclusters.
PASS condition: mammals/birds/fish form visible subclusters within one animal macro-region.

### 1.2 Property probes — do animals have correct attributes?

| id | lang | probe text | expected cluster | notes |
|----|------|-----------|-----------------|-------|
| an_prop_01 | EN | Does a dog bark? | animals/mammals | boolean YES |
| an_prop_02 | EN | Does a cat bark? | animals/mammals | boolean NO — tests dog/cat boundary |
| an_prop_03 | EN | Does a dog fly? | animals/mammals | boolean NO — tests animal/bird boundary |
| an_prop_04 | EN | Does an eagle fly? | animals/birds | boolean YES |
| an_prop_05 | EN | Does a fish walk? | animals/fish | boolean NO |
| an_prop_06 | EN | Does a dog swim? | animals/mammals | boolean YES — careful, confirms but tricky |
| an_prop_07 | EN | Can a cat purr? | animals/mammals | boolean YES |
| an_prop_08 | EN | Can a rabbit hop? | animals/mammals | boolean YES |
| an_prop_09 | EN | Is a frog a mammal? | animals/amphibians | boolean NO |
| an_prop_10 | EN | Is a snake an insect? | animals/reptiles | boolean NO |

FAIL condition: "does a cat bark?" activates dog cluster rather than cat cluster.
FAIL condition: "does a dog fly?" shows bleed into bird cluster.

### 1.3 Cross-language coherence

Same concept across all 4 languages — should activate the same cluster.

| id | lang | probe text | expected cluster |
|----|------|-----------|-----------------|
| an_lang_01 | EN | What is a cat? | animals/mammals |
| an_lang_02 | DE | Was ist eine Katze? | animals/mammals |
| an_lang_03 | JP | 猫とは何ですか？ | animals/mammals |
| an_lang_04 | ZH | 貓是什麼？ | animals/mammals |
| an_lang_05 | EN | What is a dog? | animals/mammals |
| an_lang_06 | DE | Was ist ein Hund? | animals/mammals |
| an_lang_07 | JP | 犬とは何ですか？ | animals/mammals |
| an_lang_08 | ZH | 狗是什麼？ | animals/mammals |

PASS condition: all 4 language variants of "cat" cluster tightly together (μ ≥ 0.85)
WARN condition: EN/DE cluster but JP/ZH are offset (known risk from C13 scan)
FAIL condition: language variants are more similar to other concepts in that language
               than to the same concept in other languages

---

## CLUSTER GROUP 2: Vehicles & Objects

### 2.1 Vehicle superordinate

| id | lang | probe text | expected cluster |
|----|------|-----------|-----------------|
| veh_01 | EN | What is a car? | vehicles |
| veh_02 | EN | What is a bus? | vehicles |
| veh_03 | EN | What is a train? | vehicles |
| veh_04 | EN | What is a bicycle? | vehicles |
| veh_05 | EN | What is a boat? | vehicles |

FAIL condition: bicycle activates inside animals cluster.
This would indicate bicycle appeared in animal-context stories (e.g. "the child rode
her bicycle past the dog") and was never taught as a vehicle specifically.
GREP: search teaching_stories/ and phase_A/ for "bicycle" — check co-occurrence context.

### 2.2 Vehicle vs. animal boundary

Critical boundary test. These probes should activate in clearly separated regions.

| id | lang | probe text | expected |
|----|------|-----------|---------|
| boundary_01 | EN | Is a car an animal? | vehicles — boolean NO |
| boundary_02 | EN | Is a horse a vehicle? | animals — boolean NO |
| boundary_03 | EN | Can a bus bark? | vehicles — boolean NO |
| boundary_04 | EN | Can a dog drive? | animals — boolean NO |

FAIL: any of these activates ambiguously between the two clusters.

### 2.3 Object integrity

| id | lang | probe text | expected cluster |
|----|------|-----------|-----------------|
| obj_01 | EN | What is a stone? | objects/materials |
| obj_02 | EN | What is a bucket? | objects/containers |
| obj_03 | EN | What is a door? | objects/construction |
| obj_04 | EN | What is an apple? | objects/food |
| obj_05 | EN | What is a key? | objects/tools |

---

## CLUSTER GROUP 3: Emotions

### 3.1 Emotion superordinate + subclusters

| id | lang | probe text | expected cluster |
|----|------|-----------|-----------------|
| em_01 | EN | What is sadness? | emotions |
| em_02 | EN | What is anger? | emotions |
| em_03 | EN | What is fear? | emotions |
| em_04 | EN | What is happiness? | emotions |
| em_05 | EN | What is loneliness? | emotions |
| em_06 | EN | What is surprise? | emotions |

PASS: all emotions cluster together, distinct from movement/physical clusters.
WARN: loneliness bleeds toward abstract_properties (it's on the boundary legitimately).
FAIL: sadness activates inside movement cluster (crying is a movement — known bleed risk).

### 3.2 Observable state discrimination (boolean)

These are the core tests for whether boolean teaching worked.

| id | lang | probe text | expected |
|----|------|-----------|---------|
| em_bool_01 | EN | The boy is crying. Is he happy? | emotions — NO |
| em_bool_02 | EN | The boy is crying. Is he sad? | emotions — YES |
| em_bool_03 | EN | The girl is smiling. Is she angry? | emotions — NO |
| em_bool_04 | EN | The girl is smiling. Is she happy? | emotions — YES |
| em_bool_05 | EN | The man is shouting. Is he calm? | emotions — NO |
| em_bool_06 | EN | The man is shouting. Is he angry? | emotions — YES |
| em_bool_07 | EN | The child is shaking. Is she cold or afraid? | emotions+physical — disambiguation |

em_bool_07 is a hard probe — shaking is ambiguous. We expect activation in BOTH
emotion and physical clusters. A clean result here would be genuinely impressive.

### 3.3 Emotion vs. movement boundary

Known risk: crying, running, laughing are both emotions AND movements.

| id | lang | probe text | expected |
|----|------|-----------|---------|
| em_move_01 | EN | What does crying look like? | emotions — observable manifestation |
| em_move_02 | EN | What does laughing look like? | emotions — observable manifestation |
| em_move_03 | EN | Is crying a movement? | boundary probe — expect both clusters |
| em_move_04 | EN | Is laughing the same as happiness? | boundary probe |

---

## CLUSTER GROUP 4: Movement & Physical Actions

| id | lang | probe text | expected cluster |
|----|------|-----------|-----------------|
| mv_01 | EN | What does running look like? | movement |
| mv_02 | EN | What does falling look like? | movement |
| mv_03 | EN | What does jumping look like? | movement |
| mv_04 | EN | What does carrying look like? | movement |
| mv_05 | EN | Can a stone run? | movement — boolean NO (object boundary) |
| mv_06 | EN | Can a dog run? | movement — boolean YES |
| mv_07 | EN | Can a fish jump? | movement — boolean YES (edge case) |

---

## CLUSTER GROUP 5: Time & Sequence

| id | lang | probe text | expected cluster |
|----|------|-----------|-----------------|
| time_01 | EN | What does ago mean? | time_sequence |
| time_02 | EN | What comes after winter? | time_sequence |
| time_03 | EN | What happened yesterday? | time_sequence |
| time_04 | EN | What does before mean? | time_sequence |
| time_05 | DE | Was bedeutet gestern? | time_sequence |
| time_06 | JP | 昨日とはどういう意味ですか？ | time_sequence |
| time_07 | ZH | 昨天是什麼意思？ | time_sequence |

PASS: time probes form a distinct cluster, separate from spatial/place probes.
WARN: "yesterday" bleeds toward place cluster (temporal-spatial confusion).

---

## CLUSTER GROUP 6: Abstract Concepts

These are the hardest probes — testing whether campaign 14 actually grounded B/D/E.

### 6.1 Cognitive verbs

| id | lang | probe text | expected cluster |
|----|------|-----------|-----------------|
| cog_01 | EN | What does it mean to know something? | cognitive_verbs |
| cog_02 | EN | What does it mean to think? | cognitive_verbs |
| cog_03 | EN | What does it mean to remember? | cognitive_verbs |
| cog_04 | EN | What does it mean to forget? | cognitive_verbs |
| cog_05 | EN | What does it mean to understand? | cognitive_verbs |

### 6.2 Abstract properties

| id | lang | probe text | expected cluster |
|----|------|-----------|-----------------|
| abs_01 | EN | What is patience? | abstract_properties |
| abs_02 | EN | What is honesty? | abstract_properties |
| abs_03 | EN | What is ability? | abstract_properties |
| abs_04 | EN | What is acceptance? | abstract_properties |
| abs_05 | EN | What does abiding mean? | abstract_properties |

FAIL condition: abstract probes scatter randomly across the PCA space with no cluster.
This would mean B/D/E concepts were not absorbed — campaign 14 failed its primary goal.
PASS condition: abstract probes form a loose but coherent cluster, clearly offset from
               physical/animal/vehicle clusters. Looser than concrete clusters is expected
               and acceptable.

---

## CLUSTER GROUP 7: Grammar & Case

These probes test whether the grammar cluster (visible at -125 on PCA dim 1 in C13)
survived campaign 14 and remains isolated from semantic content.

| id | lang | probe text | expected cluster |
|----|------|-----------|-----------------|
| gr_01 | EN | Who gives the boy the apple? | grammar/nominative |
| gr_02 | EN | What does Emma give the boy? | grammar/accusative |
| gr_03 | EN | To whom does Gran bring the bread? | grammar/dative |
| gr_04 | DE | Wer gibt dem Jungen den Apfel? | grammar/nominative |
| gr_05 | DE | Was gibt Emma dem Jungen? | grammar/accusative |
| gr_06 | DE | Wem bringt Gran das Brot? | grammar/dative |
| gr_07 | JP | 誰がその少年にリンゴをあげますか？ | grammar/nominative |
| gr_08 | ZH | 誰給男孩蘋果？ | grammar/nominative |

PASS: grammar probes remain in their isolated cluster at extreme PCA dim 1 position.
FAIL: grammar probes have migrated toward semantic content clusters — would mean
      the bridge course blurred the boundary rather than sharpening it.

---

## CLUSTER GROUP 8: Spatial / Positional

| id | lang | probe text | expected cluster |
|----|------|-----------|-----------------|
| sp_01 | EN | Where is Biscuit? | spatial |
| sp_02 | EN | What is above the mountain? | spatial |
| sp_03 | EN | What is under the tree? | spatial |
| sp_04 | EN | What is in front of the school? | spatial |
| sp_05 | DE | Was ist über dem Berg? | spatial |
| sp_06 | JP | 山の上には何がありますか？ | spatial |

---

## CLUSTER GROUP 9: Numbers & Arithmetic

| id | lang | probe text | expected cluster |
|----|------|-----------|-----------------|
| num_01 | EN | What is 2 + 3? | arithmetic |
| num_02 | EN | What is 5 + 5? | arithmetic |
| num_03 | EN | How many noodles are there? | numbers |
| num_04 | EN | If X is 2, what is X + 3? | symbolic_substitution |
| num_05 | DE | Was ist 3 + 4? | arithmetic |
| num_06 | JP | 2たす3は何ですか？ | arithmetic |
| num_07 | ZH | 2加3等於多少？ | arithmetic |

PASS: arithmetic probes cluster tightly (μ was 0.86 in C13 — expect similar or better).

---

## DIAGNOSTIC WORKFLOW

### When a probe FAILS (wrong cluster activation):

1. Note the probe ID and the cluster it activated instead of expected.
2. Grep the corpus:
   ```
   grep -r "bicycle" training_data/ --include="*.md" -l
   ```
3. Check co-occurrence: what other concepts appear in the same files?
4. Check domain in phase_vocab.jsonl: is it correctly labelled?
5. Check teaching_stories/ tier and domain subfolder: is it in the right bucket?
6. If corpus cause identified: add targeted teaching story or boolean story.
7. If vocab mislabelled: fix phase_vocab.jsonl and flag for retraining.

### When a cluster is FUZZY (right region, low μ):

1. Check how many teaching stories cover that domain.
2. Check tier distribution — is there a tier_1 anchor story?
3. Check cross-language coverage — does JP/ZH have sufficient stories?
4. Consider adding more organic stories for that domain in next campaign.

### When cross-language SPLITS (EN/DE cluster but JP/ZH offset):

1. Count files per language in that domain:
   ```
   ls training_data/teaching_stories/tier_*/emotions_feelings/*_JP.md | wc -l
   ```
   (Note: teaching stories are not language-split by filename — check content)
2. Check if JP/ZH language course covers relevant vocabulary.
3. Consider targeted JP/ZH teaching stories for that domain.

---

## PROBE IMPLEMENTATION NOTES

- All probes run through brain_map.py with seed=1337 for determinism
- Probes use the same format as existing anchor_probe.py probes
- Tier-4 boolean probes require yes/no capable model — run AFTER boolean training
- Grammar probes should be run against BOTH phase_A winner AND campaign_14 winner
  to check whether grammar cluster survived the new training
- Minimum 3 probes per cluster for meaningful PCA positioning
- Add new probes for any cluster that shows unexpected activation patterns

---

## EXPECTED CLUSTER SIGNATURES (campaign 14 targets)

Based on C13 scan results and campaign 14 goals:

| Cluster | C13 μ | C14 target μ | Notes |
|---------|--------|--------------|-------|
| cognitive | 0.98 | ≥ 0.95 | Should survive |
| multilingual EN | 0.99 | ≥ 0.99 | Should survive |
| multilingual DE | 0.99 | ≥ 0.99 | Should survive |
| multilingual JP | 0.76 | ≥ 0.85 | Target improvement |
| multilingual ZH | 0.69 | ≥ 0.80 | Target improvement |
| grammar dative | 0.48 | 0.45–0.55 | Intentionally loose |
| grammar accusative | 0.92 | ≥ 0.90 | Should survive |
| arithmetic | 0.86 | ≥ 0.86 | Should survive |
| emotions | n/a | ≥ 0.80 | New — B/D/E target |
| movement | n/a | ≥ 0.80 | New — B/D/E target |
| abstract_properties | n/a | ≥ 0.70 | New — loose expected |
| vehicles | n/a | ≥ 0.85 | Should be clear |
| animals/mammals | n/a | ≥ 0.88 | Should be clear |

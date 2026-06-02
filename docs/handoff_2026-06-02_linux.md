# Handoff — 2026-06-02 (Linux session, end of day)

## What this session accomplished

### Corpus
- Teaching stories: 5,006 stories generated and committed (anchor + organic + mop-up passes complete)
- Boolean stories: 800 stories generated and committed (200 per tier, observable-domain words, elimination structure)
- All accounting clean: zero deficits, zero drift, zero sha256 mismatches

### Tools built
- `meta/scripts/story_gen_boolean.py` — boolean story generator (plan → run → status commands)
- `meta/scripts/brain_map.py` — activation atlas scanner (probe → hubs → map commands)
  - Records xy_sparse (Hebbian co-firing) at last prompt token, all layers
  - Cosine similarity heatmap + t-SNE scatter output
  - Hub detection (high-breadth co-firing candidates)
  - Geometry saved to .npz; no hardcoded config

### Docs updated
- `docs/boolean_stories.md` — boolean story spec
- `docs/curriculum_topology.md` — major rewrite: corrected bridge interpretation,
  confirmed vs pending findings, triplet integration design, corrected curriculum order
- `docs/brain_map.md` — v1 findings with correct interpretation, v2 requirements,
  terminology table (semantic neurons → category-exclusive co-firing dimensions etc.)

### Brain map results — C13 winner (correctly interpreted)
Run: 180 probes, 13 categories, `checkpoints/c13_Phase_C_winner.pt`

The scanner is an activation-geometry diagnostic, NOT a semantic map yet.
Template confound not controlled in v1 — see brain_map.md for full correction.

What IS valid:
- 289 high-breadth co-firing candidates (hub structure real, causal role unconfirmed)
- Dative: high construction-level coherence (über ≈ 0.908, in-static ≈ 0.989)
  but aggregate dative misleading — never lump constructions together
- Scanner detects prompt-family differences; does not confirm concept existence
- Geometry saved: can rerun hubs/map without checkpoint

What was CORRECTED after GPT review:
- Emotion/cognitive clusters: likely template-shell effects, not semantic clusters
- Multilingual EN↔DE: was within-language template consistency, NOT cross-concept alignment
- "87% silent" ≠ unused capacity (limited probe battery, stricter xy_sparse measure)
- "Confirmed grounding" downgraded to "leading hypothesis, template controls pending"

### Key research conclusions from this session
1. Bridge-as-kickstarter = surface form pre-loading, not semantic warm-up. Bridge belongs
   AFTER stable semantic substrate, as corrective pressure on actual misconceptions.
2. Loss curves unreliable as primary metric. Right stack: neuron map + competency probes +
   shaped score as regression gate only.
3. Grounding hypothesis remains leading explanation for B/D/E failure, but needs template
   controls before "confirmed."
4. Dative instability: construction-level coherence is fine; aggregation was the problem.

---

## Current state (confirmed)

```
training_data/teaching_stories/   5,006 teaching + 800 boolean = 5,806 files
checkpoints/c13_Phase_C_winner.pt  shaped 0.925, base for Campaign 14
tmp/brain_map_activations.npz      180-probe activation scan (reusable)
tmp/brain_map_probes.jsonl         probe metadata
tmp/brain_map_hubs.json            hub analysis results
```

---

## Campaign 14 design (decided, not yet built)

Corrected curriculum order:
```
Phase A → Phase B
  → grounded stories (interleaved from start, ~1 per 100 files, 780 files total)
  → teaching stories (domain-sorted: concrete → action → social → temporal
                       → emotion → cognitive → abstract → math)
     interleaved with boolean stories (1 per ~20 teaching, domain-aligned)
     interleaved with triplets (aligned by bucket, tiers 1-2 first)
  → PROBE CHECKPOINT — brain map v2 + competency probes
  → bridge course (corrective, targeted at actual misconceptions found)
  → B/D/E retry
```

Teaching story domain order:
1. objects, materials, places, animals, body, colors (Phase A anchored)
2. movement, life actions, processes
3. people, social, desire verbs, society (Phase B anchored)
4. time sequence
5. emotions_feelings (tier-1 B/D/E target)
6. cognitive verbs, communication
7. abstract properties, abstract concepts
8. mathematics (most abstract, last)

Triplet buckets (aligned interleaving):
- Concrete/physical → animals_and_nature, body_and_health, food_and_meals, home, weather
- Action/movement → tools_and_making, play_and_games, vehicles_and_travel
- Social/people → people_and_relationships, school_and_learning
- Emotional → people_and_relationships (higher tiers)
- Cognitive → language_and_grammar, school_and_learning
- Abstract → abstract_concepts
- Mathematical → math_and_science

---

## What needs to be built next

1. **Teaching story order manifest** — domain-sorted, same format as curriculum_manifest.md
   - Check `meta/scripts/build_curriculum_order.py` for reuse
   - Input: `tmp/phase_vocab.jsonl` (has domains per word)
   - Output: ordered list of teaching story filenames

2. **Triplet bucket assignment** — map 13 triplet categories to 8 teaching domain blocks

3. **Interleaving manifest generator** — combines teaching stories + boolean + triplets + grounded
   at configurable ratios into a single training order

4. **brain_map.py v2 probe design** (template controls, construction-split grammar, negative controls)

---

## Campaign 15 design (queued, details TBD)

Three prioritised experiments (from GPT deep research):
1. Atlas reproducibility + cluster drift — run brain map on phaseA winner, compare signatures
2. Teaching stories + triplets interleaving matrix — sequential vs aligned vs random
3. Register-alignment crossover — add triplet-format probes to brain_map.py, test if same
   concept activates different circuits in Q&A vs story format

---

## Python environment

Training + brain map: `/home/aomukai/.unsloth/studio/unsloth_studio/bin/python`
Story generation: system python3 (has openai, wordfreq)
API key: in `.env` at repo root

## Repo

Primary: `/media/aomukai/SSD External/Ninereeds` (this repo, external SSD)
Internal copy: `~/Ninereeds` (checkpoints live here, torch lives here)
Both share the same physical directory for claude/ memory.

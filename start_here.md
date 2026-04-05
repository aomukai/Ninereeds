I'm building a cognitive OS for a small language model called BDH. Read bdh_cognitive_os_design.md for the full spec and bdh.py for the model architecture. The trained model is at core/bdh_100m_final.pt. Do not modify bdh.py — treat it as a read-only dependency.

## Status

### Milestone 1 — complete
- inference.py: loads checkpoint, byte-level tokenisation, seeded generation
- harness.py: full live loop — classify → shape → specialist → reload → final output → save artifacts
- prompt_shaper.py: routes user input to completion-friendly shapes (definition, qa, story, passthrough, fill)
- eval.py: comparative eval with scoring and failure mode detection
- Locked generation settings: temperature=0.8, top_k=None

### Milestone 2 — LoRA research complete

**What we built:**
- HebbianLoRA on encoder + encoder_v (design doc spec) — 540K trainable params, 2.09%
- SurfaceLoRA on lm_head — output-layer shaping, low risk
- Three-layer training data: short anchor → expanded Q/A → subject repetition
- Contrastive pairs: similar concepts adjacent to maximise disambiguation pressure
- train_lora.py: full trainer with checkpointing and delta_norm logging
- test_lora.py: seeded base vs LoRA side-by-side comparison

**Core finding:**
HebbianLoRA on the shared encoder = global bias, not local selection.
All 6 layers share one encoder — any delta shifts the whole representation space.
Surface LoRA (lm_head) confirmed working: "A X is" output structure appears even on unseen prompts.
Routing (concept → correct completion) is the unsolved problem.
Root cause: the model needs a world model, not more LoRA iterations.
56 training examples cannot build concept separation for reliable routing.

**Conclusion:**
The model is not learning language anymore — it's learning a world model.
Build the OS infrastructure first. Return to training with the full system in place.

### Curriculum pipeline — ready, data generation in progress

The world model problem needs grounded concept stories, not Q/A pairs.
Inspired by toddler language acquisition: short stories that teach identity, properties,
state transitions, and category — one concept at a time.

**Story format (6 sentences):**
```
This is a ball.
The ball is round.
The ball is red.
The ball is on the floor.
The ball rolls to the wall.
A ball is a toy.
```

**Pipeline:**
- Prompt designed (see below) — tested with Nemotron, produces clean output
- workflow/parse_stories.py: converts story text files → pairwise.jsonl + sliding.jsonl
- Output goes to knowledge/curriculum/
- Planned: 60-120 stories, 15-20 concepts, 3-4 stories per concept

**Nemotron generation prompt:**
```
Write a 6-sentence story for a very young child about [concept].

Rules:
- Use only simple sentences.
- Use the exact word "[concept]" in every sentence. Do not use pronouns.
- Only "[concept]" may perform actions.
- Other objects may appear only as places, locations, or things acted upon. They must not act.
- Each sentence must describe one fact, property, or action of "[concept]".
- Include exactly one sentence where "[concept]" moves or changes state.
- Use literal, concrete language only. No metaphors, no imagination.

Structure:
1. Introduce the concept: "This is a [concept]."
2–4. Give simple properties or actions.
5. Show movement or a change of state.
6. End with a category statement: "A [concept] is ..."

Keep vocabulary simple and repetitive.
Output only the 6 sentences. Do not add explanations.
```

**Concepts to cover (Nemotron's recommendation):**
ball, cup, spoon, blanket, dog, cat, tree, house, car, book, shoe, hat, box, chair,
table, window, door, light, water, food — and others as needed.

**This is Dream LoRA territory**, not Skill LoRA. It builds the base world model.
Requires human approval before promoting. Train offline after OS is in place.

### Next: build the OS
Continue from design doc §3–§9. Priority order:

1. **loras/index.json** — LoRA registry with metadata and centroid vectors
2. **Classification logic** — latent similarity → LoRA selection (§7)
3. **Dream queue** — flag gaps from runs, store candidates for offline training (§4)
4. **chat.py** — interactive interface over the live loop (§8)

Build the system described in the design doc. Update this file as the project evolves.

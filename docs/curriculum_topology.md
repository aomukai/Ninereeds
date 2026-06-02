# Curriculum Topology

A structured reference of the Ninereeds corpus, training history, and open
research questions. Useful as a briefing document for deep research tools
(GPT Deep Research, Gemini Deep Research) to generate curriculum ordering
proposals, and as a living record of what has been learned so far.

Last updated: 2026-06-02

---

## The core research question

Transformer training laws (scaling laws, loss curves, data-to-parameter ratios)
do not apply to BDH. Ninereeds is Hebbian-trained: learning is local and
associative, not gradient-based. There is no established prior art for this
training regime at this scale with this curriculum structure.

The mission is to discover what laws govern BDH training. Every campaign is an
experiment toward that goal, not just a training run.

**Loss curves are unreliable as the primary evaluation signal.** Predicting the
next token correctly measures surface-form compliance, not concept formation.
The shaped score measures format fidelity and vocabulary recall — both are useful
diagnostics but neither tells you whether the model *understands* what it is
producing. The activation map (see below) has already demonstrated this gap.

The right evaluation stack:
1. **Neuron map** — which concepts formed coherent clusters? Is the cluster
   stable or scattered?
2. **Competency probes** — targeted questions per concept and POS class, across
   all 4 languages, at each training checkpoint
3. **Shaped score** — useful as a regression gate; not a measure of understanding

---

## Corpus inventory (as of 2026-06-02)

```
training_data/
  phase_A/              1,494 units — concrete anchors (objects, nature, basic properties)
  phase_B/              1,148 units — agents & social (was phase_C in old numbering)
  teaching_stories/     5,006 stories × 4 languages — narrative grounding for B/D/E concepts
                        + 800 boolean stories (completing 2026-06-02)
  grounded_stories/     195 stories × 4 languages — canon cast, village world
  lang/lang_1–5/        ~18k files — multilingual vocabulary curriculum
  grammar/              1,921 files — function-first, case-aware (German spine)
  wiki/level_1–4/       2,110 EN × 4 languages — broader concept knowledge
  triplet_stories/      1,345 EN × 4 languages, tier 1–4
                        13 categories: abstract_concepts, animals_and_nature, body_and_health,
                        food_and_meals, home_and_daily_life, language_and_grammar,
                        math_and_science, people_and_relationships, play_and_games,
                        school_and_learning, tools_and_making, vehicles_and_travel,
                        weather_and_seasons
  reasoning/            27 EN × 4 languages — arithmetic, logic, epistemic uncertainty
  philosophy/           144 multilingual files — Socratic dialogues

archive/
  phases/phase_B_old/   old emotions/movement (B/D/E failed C13 — archived)
  phases/phase_D_old/
  phases/phase_E_old/
```

The old phase numbering (1–6) has been retired. Current active phases are A and B.
Teaching stories replace the failed B/D/E static-format files.

---

## Corpus roles and design intent

### Phase A — concrete anchors
- Format: `[user]`/`[Ninereeds]`, 4 block pairs per file
- Question forms: what does X look like / where is X found / what happens to X / what does X do
- Response: 5 property lines + 1 summary, no pronouns, no negation, one sentence per line
- Content: objects, nature, body, basic properties — anything with a static visual referent

### Phase B — agents & social
- Same format as Phase A
- Question forms: what is X-ing / when does X happen / what does X bring / what does X give
- Content: social concepts, agent roles, relational knowledge

### Teaching stories
- Format: `[user]`/`[Ninereeds]`, 4 language blocks (EN→DE→JP→ZH)
- Tiers 1–3: 1 pair per language; Tier 4: 2 pairs per language
- Omniscient narrator, no named characters, village world setting
- Content: all 5,153 vocab words; tier-1 words (B/D/E) get anchor stories first
- Boolean subset (800 stories): elimination structure (wrong guess → No; correct → Yes)
  teaches yes/no discrimination through observable evidence

### Grounded stories
- Plain prose narrative, no `[user]`/`[Ninereeds]` tags
- Canon cast: Emma, Taro, Gran, Biscuit, Bello (introduced gradually from story 48)
- 12 locations; curriculum blocks: spatial → temporal → causal → two-dog → arithmetic
- Must NOT be fed as a contiguous block (catastrophic forgetting confirmed, run 2)
- Must interleave at ~0.5% of corpus

### Triplet stories
- Format: `[user]tell me a story about X` → `[Ninereeds]` narrative response
- Single block per file (one language per file); 4 separate files per story (EN/DE/JP/ZH)
- 1,345 stories × 4 tiers × 4 languages = 5,380 files
- Tier 1: picture-book level; Tier 4: extended paragraph, named characters
- **Design intent:** originally conceived as vocabulary reinforcement between lang and wiki.
  Teach the word in lang_1, see it used naturally in a triplet story, then deepen via wiki.
  The triplets show vocabulary in varied, natural narrative contexts the model hasn't seen.
- **Integration question:** triplets may be most effective interleaved during teaching story
  training, not as a separate block — see curriculum ordering section below.

### Grammar corpus
- Function-first, case-aware German spine
- Numeric cluster order = intended training order (00–bridge_course)
- Tests: dative (static), accusative (movement), genitive, V2 word order, ditransitive
- **Timing question:** see corrected bridge interpretation below

### Wiki
- 4 levels, broader concept knowledge than phases
- Child-facing explanatory language, category ownership, relational knowledge
- Level 1–2 probably precedes triplet tiers 3–4; Level 3–4 follow

---

## Empirical findings by campaign

### Campaigns 1–12 (runs 1–12)

**Format compliance dominates volume.** Small well-formed files outperform
oversampling. The shaped score is highly sensitive to `[user]`/`[Ninereeds]`
format fidelity — malformed files have outsized impact at this model size because
there is no error averaging from scale.

**Epoch sweet spot.** Run 4 identified an optimal epoch count beyond which the
model overfits to surface form rather than generalising.

**Scaling ablation (runs 10–12).** 25M → 151M → 604M. Per-layer weights at 151M
opened capability headroom. 604M showed capacity but needed more data to fill it.
The 25M model is used for fast validation; 150M for confirmed campaigns.

**4-lingual beats English-only.** Multilingual training from the start outperforms
English-only + later localisation.

### Campaign 13 — Bridge → Phase A → Phase C (now Phase B)

**Result:** shaped score 0.925 on 25M. Best checkpoint: `checkpoints/c13_Phase_C_winner.pt`

**Bridge as kickstarter (+0.007):** Bridge → Phase A beats Phase A alone. The
shaped score improved. This was initially read as evidence that Bridge provides a
useful semantic warm-up. **This reading is now known to be wrong — see below.**

**Bridge as connector (−0.008 to −0.018):** Inserting Bridge between phases
consistently hurts. This finding still holds.

**Phase A + Phase B absorb cleanly.** 0.925 is the ceiling for this curriculum.

**B/D/E permanently fail (4 attempts each).** Emotions, cognitive verbs, and
abstraction do not absorb in the static property-listing format.

### Corrected interpretation of Bridge-as-kickstarter (2026-06-02)

The +0.007 shaped score improvement from Bridge → Phase A was interpreted as
semantic warm-up. The activation map disproves this.

**What actually happened:** Bridge introduces connective vocabulary surface forms
(word, sentence, plan, goal, question, answer, etc.) before there is any semantic
substrate for those words to attach to. The model learned to produce these words
in the correct positions in the training format — which improved format compliance
and therefore the shaped score — without forming any semantic associations for
them. The shaped score improved because *format got tighter*, not because the
model understood more.

**Corrected role of the bridge course:** the bridge is a corrective layer, not a
warm-up layer. Its purpose is to address specific misconceptions that have actually
formed after the core semantic substrate is in place. The right time to use it is
after Phase A + Phase B + stories have run and been probed, not before.

**Analogy:** teaching a child the word "therefore" before they can reason. The
word appears in the right positions in their speech without carrying any logical
force. The shaped score would improve; reasoning would not.

### Activation map findings — C13 winner (2026-06-02)

A neuron-level activation atlas was run on the C13 winner checkpoint using 180
probes across 13 concept categories. Key findings:

**87% of neurons are silent across all probes.** Only ~25,000 neurons fire at all
across 180 concept probes. The 25M model has significant unused capacity. The
B/D/E failure is not a capacity problem.

**B/D/E concepts are internally represented.** Both emotion (mean intra-cluster
similarity 0.835) and cognitive (0.976) form coherent activation clusters — the
cognitive cluster is tighter than the Phase A noun cluster (0.876). The concepts
exist in the weight space. What is missing is behavioral grounding — the model
cannot format a response around them. This confirms the grounding hypothesis as
an empirical finding, not a working assumption.

**Dative instability explained at neuron level.** Dative probes have 2,083
exclusive neurons — more than any other category — but the lowest intra-cluster
similarity (0.482). Many dedicated circuits, firing inconsistently. The model has
learned many conflicting versions of dative rather than one stable one. Introducing
the grammar corpus before a stable semantic substrate exists would add more
conflicting surface forms on top of the existing ones.

**Hub structure: 289 routing neurons (0.15%).** Head 1 across all layers is the
dominant routing channel. Only 289 neurons out of 196,608 fire across ≥70% of
concept categories. The network has a very compact routing layer.

**Semantic neuron counts by category:**

| Category | Exclusive neurons |
|---|---|
| grammar_dative | 2,083 |
| grammar_v2 | 1,458 |
| phase_b | 1,332 |
| phase_a | 651 |
| emotion | 454 |
| grammar_accusative | 430 |
| multilingual_ZH | 693 |
| arithmetic | 247 |
| cognitive | 85 |

**Arithmetic is small but coherent** (247 exclusive neurons, 0.860 similarity).
Concepts share circuits rather than each owning dedicated neurons — this is
healthier than dative's large-but-scattered pattern.

**Multilingual EN and DE are nearly identical** (0.989 and 0.985). JP (0.756)
and ZH (0.689) are more variable — the byte-encoding of CJK scripts activates
more diverse circuits per prompt.

---

## Known failure modes

**B/D/E absorption failure** — emotions, cognitive verbs, abstraction do not land
in the static property format. The activation map confirms the concepts exist
internally; the failure is behavioral (no grounding). Teaching stories address this.

**Bridge mistiming** — Bridge used as a cold-start primer teaches surface forms
without semantic substrate. Shaped score improves; understanding does not. Bridge
should be used as a corrective layer after the semantic substrate is probed and
confirmed.

**Dative instability** — many conflicting activation patterns for the same case
relationship. Needs a stable semantic substrate before grammar corpus can resolve
rather than compound the inconsistency.

**Book loop** — repetitive generation under sustained output pressure. Minimised
by loop count gate in shaped score.

**JP garbling** — Japanese degrades to phonetic approximations or mixed script.
Cause: early calques. Naturalness-first prompt corrects new corpus; old files
repaired.

**Arithmetic retrieval framing** — correct relationships present but
framing-sensitive. Model learned form, not operation.

**Catastrophic forgetting (stories as block)** — confirmed run 2. Must interleave
at ~0.5% of corpus. Hard constraint.

**Boolean discrimination absent** — model has never been trained to produce yes/no.
800-story boolean extension addresses this.

---

## Corpus roles and the curriculum question: triplets

Triplets were originally designed as a vocabulary reinforcement layer between lang
and wiki: *teach the word → see it in natural narrative → deepen it via wiki*.
Each triplet story uses a vocabulary item in a broader, varied narrative context
— the kind of varied exposure that prevents a concept from getting locked to a
single surface form.

This original intent is sound but the timing was wrong. Triplets placed after
a static-format corpus (phases) and before wiki makes sense only if the model
has already formed stable semantic clusters for those concepts. Placed too early,
triplets introduce narrative format variation before the concepts themselves are
grounded — the model sees the word in many contexts before it knows what the word
means.

**Triplets vs teaching stories:**

| | Teaching stories | Triplets |
|---|---|---|
| Format | `[user]What does X look like?` | `[user]tell me a story about X` |
| Language | 4-language parallel per file | 1 language per file |
| Purpose | Ground specific B/D/E concepts | Varied natural exposure to any concept |
| Narrator | Omniscient, no named characters | Named characters in higher tiers |
| Tier range | 1–4 (grammar complexity) | 1–4 (narrative complexity) |
| Concept scope | All 5,153 vocab words | 1,345 stories across 13 categories |

These are complementary, not interchangeable. Teaching stories establish *what a
concept is* through a consistent question frame. Triplets show *the concept in
varied use*. The natural order is teaching stories first, triplets after — the
same word appears in its concept-grounding frame first, then in varied natural
contexts.

**Interleaving hypothesis:** rather than running teaching stories to completion
then running all triplets, interleaving may be more effective. Every N teaching
stories for concept X, insert a triplet story that uses X in a broader narrative.
This matches how human vocabulary deepens — concept definition, then varied use,
alternating. The interference geometry experiment (which corpus pairs cause
forgetting) applies here: do teaching stories and triplets reinforce each other,
or does format switching cause forgetting?

**Triplet category alignment with teaching story domains:**

| Triplet category | Teaching story domain |
|---|---|
| animals_and_nature | animals, nature_environment |
| abstract_concepts | abstract_properties, abstract_states |
| people_and_relationships | emotions_feelings, social_interaction |
| body_and_health | movement_physical_actions |
| math_and_science | mathematics |
| language_and_grammar | communication_reasoning |

Aligned interleaving (teaching stories for animals → triplet animals stories →
teaching stories for abstract → triplet abstract stories) is worth testing before
unaligned random interleaving.

---

## Corrected curriculum hypothesis (2026-06-02)

Based on Campaign 13 findings and the activation map:

```
Phase A (concrete anchors)
  → Phase B (agents & social)
  → grounded stories (195, interleaved at ~0.5%)
  → teaching stories (5,006 concept + 800 boolean)
     interleaved with triplets (aligned by category, tier 1–2 first)
  → PROBE — neuron map + competency probes
     confirm clusters are clean before proceeding
  → bridge course (corrective — targets actual misconceptions that formed)
  → B/D/E retry
  → triplet tiers 3–4 + wiki level 1–2 (alternating)
  → reasoning
  → philosophy
```

The probe checkpoint before bridge is not optional. Running bridge as a corrective
layer without first establishing what misconceptions actually formed is guesswork.
The neuron map and competency probes give us a real target.

**The three open ordering questions:**

1. **Teaching stories + triplets: interleaved or sequential?** Interleaving is the
   hypothesis; sequential is the control. This is testable in Campaign 14/15.

2. **Grounded stories: before or after teaching stories?** Grounded stories
   establish character continuity and the named-character world that teaching stories
   cannot use (omniscient narrator only). They probably belong before teaching stories
   so the narrative world exists before concept-grounding stories use it. But this is
   untested.

3. **Which triplet tiers go where?** Tier 1–2 (picture-book level) probably
   interleave with teaching story early passes. Tier 3–4 (more complex, named
   characters) probably follow after the semantic substrate is more stable.

---

## Success criteria

A curriculum ordering is successful if it produces a checkpoint where:

- **B/D/E concepts absorbed** — confirmed by competency probes, not just shaped score
- **Cluster coherence** — neuron map shows tight intra-category similarity for
  emotion, cognitive, abstract (target: approaching Phase A level, ~0.85+)
- **Boolean discrimination works** — yes/no correct across all 4 languages
- **Dative stability** — consistent case form across rephrasings (intra-cluster
  similarity improves from current 0.482)
- **Arithmetic robustness** — correct across ≥ 3 surface rephrasings
- **Multilingual integrity** — DE/JP/ZH maintain register and script
- **No pronoun/negation bleed** — zero instances in `[Ninereeds]` output
- **Shaped score stable** — sustained across ≥ 3 probe rounds (regression gate only,
  not primary success criterion)

---

## How to use this document for deep research

1. Feed this document together with `training/docs/pipeline.md` and activation
   map results (`tmp/brain_map_hubs.json`) to a deep research tool.
2. Ask it to:
   - Given the confirmed grounding finding, propose a precise interleaving schedule
     for teaching stories and triplets (how many of each, in what ratio, by category)
   - Identify whether the dative instability pattern suggests the grammar corpus
     should be split (static-location dative first, then other case forms)
   - Propose what the competency probe battery should look like at the bridge
     checkpoint specifically
   - Identify whether the multilingual EN/DE convergence vs JP/ZH divergence
     suggests language-specific curriculum interventions
3. Cross-reference proposals against the corrected bridge interpretation.
4. Test divergences as controlled experiments.

---

## Related docs

- `training/docs/pipeline.md` — full corpus layer descriptions and intended sequence
- `docs/boolean_stories.md` — boolean teaching story spec
- `docs/probe_catalogue.md` — competency probe design (to be written)
- `docs/grammar_plan.md` — grammar corpus design rationale
- `docs/brain_map.md` — activation atlas plan and methodology
- `tmp/brain_map_hubs.json` — hub detection results from C13 winner
- `training/logs/` — campaign reports
- `todo.md` — active work queue

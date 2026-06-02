# Boolean Story Extension — Design Spec

## Purpose

A post-generation pass that creates a boolean-teaching layer within
`training_data/teaching_stories/`. These stories teach yes/no discrimination
through observable-state reasoning, and serve double duty as coverage for
underrepresented words — the most pedagogically fragile part of the living list.

The goal is to give Ninereeds the boolean foundation needed for any competency
probe to yield interpretable results. Without this layer, a probe question like
"does a cat bark?" has no fair answer — the model has never been taught to
produce yes or no.

## When to run

After the main `story_gen_v2.py` run reaches `done`. Read the final living list,
not an in-progress one — we want the real underrepresentation picture.

## Word eligibility

Observable domains only:

| Domain | Why eligible |
|---|---|
| `emotions_feelings` | States with behavioral signatures (crying, laughing, flinching) |
| `movement_physical_actions` | Visible actions (running, falling, reaching) |
| `animals` | Behavioral attributes (barking, purring, nesting) |
| `objects_things` | Physical states (wet, broken, floating) |
| `nature_environment` | Observable conditions (raining, dark, frozen) |

Exclude: `mathematics`, `abstract_properties`, `cognitive_verbs`,
`communication_reasoning` — these cannot be pointed at in a scene.

Eligibility requires `anchor_written=True` and at least one of:
- High underrep score: Zipf high, `n_times_used` low — important word that barely landed
- `n_times_used` ≤ floor target (3) — barely above "might as well not have been introduced"

## Wrong answer selection

For each anchor word, select 1–2 wrong-answer words from the same domain that:
- Have contrasting observable manifestations (the scene cannot be mistaken for them)
- Are themselves underrepresented — the elimination chain becomes additional coverage

Example: anchor = `sadness`. Wrong answers = `happiness` (laughing, smiling),
`anger` (scowling, shouting). Each wrong-answer word that appears in the story
is counted in the tracker — two-for-one coverage.

## Story structure

Always tier 4 (2 turns per language, 8 blocks total).

```
Turn 1 — wrong guess:
  [user]   Scene establishing observable evidence. Is [subject] [wrong word]?
  [Ninereeds] No. [Wrong word] looks like [wrong manifestation].
             That is not what this looks like.

Turn 2 — correct confirmation:
  [user]   Is [subject] [anchor]?
  [Ninereeds] Yes. [Anchor] looks like [correct manifestation].
             [Observable evidence] is what [anchor] looks like from the outside.
             [One-line principle connecting evidence to concept.]
```

The final line of turn 2 is the pedagogical payload — it states the general rule,
not just the instance. "Tears are what sadness looks like from the outside."

### Example (anchor: sadness)

```
[user]
A boy sits by the road with tears running down his face. Is he happy?

[Ninereeds]
No, the boy is not happy. Happy children laugh and run. The boy is not
laughing. The boy is not running. He is sitting still with tears on his face.

[user]
Is he sad?

[Ninereeds]
Yes, the boy is sad. Sadness brings tears. Sitting still and crying is what
sadness looks like from the outside. When something hurts inside, the tears
come out.
```

## Language treatment

Same scene localised naturally into all 4 languages. Boolean markers localise:

| Language | Yes | No |
|---|---|---|
| EN | Yes | No |
| DE | Ja | Nein |
| JP | そうだ | そうではない |
| ZH | 是的 | 不是 |

JP: plain form throughout. ZH: Traditional Chinese only.

## Integration

Same output directory (`training_data/teaching_stories/`), same tracker format,
same sha256 accounting. Boolean stories are not a separate corpus — they live in
the same pool. The tracker records them with a `boolean: true` flag so they can
be filtered for analysis if needed.

## Target volume

10–20% of the final main story count. Exact number chosen after the main run
finishes, based on the shape of the underrepresentation tail.

Priority order:
1. Observable-domain words at `n_times_used` ≤ 2 (anchor written but barely present)
2. Observable-domain words between floor (3) and standard (5) with high Zipf score
3. Remaining observable-domain words above standard but with high underrep score

## Implementation

Separate script: `meta/scripts/story_gen_boolean.py`

Same API and output conventions as `story_gen_v2.py`:
- Reads final `tmp/phase_vocab.jsonl`
- Builds a candidate list ranked by priority order above
- Writes a job queue; runs generation with the boolean prompt
- Resumable: same lock/tracker pattern

The boolean prompt differs from the main prompt in three ways:
- Specifies the wrong-answer word(s) explicitly
- Specifies the 2-turn elimination structure
- Requires yes/no as the opening word of each Ninereeds turn

## Relationship to the probe catalogue

Once this layer exists, Layer 4 boolean probes become fair tests. The model will
have seen "Is X doing Y? No, because Z. Is X doing W? Yes, because V." in
observable contexts across all four languages. "Does a cat bark?" then has a
real chance of a clean yes/no response rather than a hedged property list.

See `docs/probe_catalogue.md` (to be written) for the full probe design.

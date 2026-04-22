# Triplet Stories Batch — Review Notes for Claude Code

Review target:
- `training_data/triplet_stories/tier_1/`

Current files reviewed:
- `animals_and_nature.md`
- `body_and_health.md`
- `food_and_meals.md`
- `home_and_daily_life.md`
- `people_and_relationships.md`
- `play_and_games.md`
- `school_and_learning.md`
- `tools_and_making.md`
- `vehicles_and_travel.md`
- `weather_and_seasons.md`

## High-level verdict

This batch is a **real usable first draft**, but it is **not evenly calibrated** to the intended Story Layer 1 target.

Main pattern:
- some files are already close to the desired layer
- some drift upward into denser, more descriptive, more adult-sounding prose
- some entries become generic moral/generalization statements instead of concrete little scenes
- at least one file (`play_and_games.md`) is structurally inconsistent with the current Tier 1 rewrite-stage spec because it uses a different sentence count and a different ending shape

## Stronger files

These look closest to the intended early-layer style and probably need only light cleanup:
- `animals_and_nature.md`
- `body_and_health.md`
- `food_and_meals.md`
- `tools_and_making.md`
- `vehicles_and_travel.md`

Typical strengths in the stronger files:
- 5 sentences per story
- short sentences
- low abstraction
- clear anchor/support alignment
- endings usually stay grounded even when the story shape is still older than the current spec

## Files needing the most attention

### 1. `school_and_learning.md`

This is the clearest high-priority rewrite candidate.

Observed issues:
- sentence lengths are much higher than the rest of the batch
- vocabulary is often too advanced or too writerly for the intended early layer
- many stories feel like object descriptions written for an older reader rather than child-level event scenes
- some wording becomes technical or overly specific without clear benefit

Examples of drift:
- `ceramic cup`
- `graphite core`
- `wood casing`
- `main compartment`
- `drafting table`
- `perfectly straight line`
- `lesson plans`
- `focused attention`
- `today's lesson`

Rewrite guidance:
- simplify heavily
- prefer visible actions over hidden attributes
- remove most material-science/detail language unless absolutely necessary
- keep each story closer to a child doing a simple school action
- make the triplet support words visibly active in the scene

### 2. `home_and_daily_life.md`

This file is usable, but several stories drift too long or too descriptive.

Observed issues:
- a number of stories exceed the intended short-sentence feel
- some sentences become mechanically explanatory rather than story-like
- a few lines feel awkward or slightly unnatural

Examples:
- `The bowl stays steady on the table while the spoon moves the soup.`
- `The window stays open to let the morning air and sun inside.`
- `The hand holds the handle of the broom to move the broom back and forth.`
- `The thirsty hands lift the heavy cup to drink the water.`

Rewrite guidance:
- shorten long sentences
- avoid body-part agents like `thirsty hands`
- prefer simple visible action chains
- cut redundant support-word restatement when it does not help the scene

### 3. `play_and_games.md`

This file has a structural mismatch with the current Layer 1 rule.

Observed issues:
- stories use **6 sentences**, not the current Tier 1 rewrite-stage target
- some stories also lean slightly upward in complexity
- several entries use `will`, which pushes them toward explanatory future statements rather than simple immediate scenes

Examples:
- `A child will throw the ball high.`
- `A child will play with the doll every day.`
- `A child will stack each block to build a tower.`

Rewrite guidance:
- normalize this file to the same sentence-count convention as the rest of the tier
- prefer present-tense simple event lines over `will`
- keep the action immediate and concrete

### 4. `people_and_relationships.md`

This file is coherent, but many entries become generalized moral statements instead of concrete little stories.

Observed issues:
- several stories read like mini aphorisms or generic lessons
- some entries feel more like value statements than observed scenes
- some family-role entries may need style review for tone/generality

Examples:
- `Love guides daily family routines.`
- `Share builds a kind heart daily.`
- `Share reduces arguments between children.`
- `Help arrives when tasks are hard.`
- `Invite plans meals and games carefully.`
- `Birthday hides a special gift under the tree.`

Rewrite guidance:
- replace abstract moralizing with concrete scenes
- keep "kind/fair/help" grounded in actions, not slogans
- prefer one visible event over a general lesson
- recheck entries like `birthday` for context realism (`under the tree` reads Christmas-like, not birthday-like)

### 5. `weather_and_seasons.md`

This file is mostly workable, but some stories are a bit dense or scenic for Layer 1.

Observed issues:
- a few stories stretch sentence length
- some wording becomes more literary than necessary
- some entries feel like descriptive nature writing instead of the simplest child-facing event framing

Examples:
- `The thin layer of frost forms on the grass in the cold morning.`
- `The long days of summer bring hot weather.`
- `The howling wind shakes the tall trees during the storm.`

Rewrite guidance:
- keep the domain, but simplify the phrasing
- prefer direct visible outcomes over scenic atmosphere

## Specific things Claude should check everywhere

1. **Sentence-count consistency**
- Story Layer 1 files should follow one consistent template.
- Right now the old batch uses mixed shorter templates, while the current Tier 1 rewrite-stage spec calls for 8 sentences.
- Normalize the whole tier to one stable pattern.

2. **Sentence simplicity**
- Favor short plain sentences.
- Avoid drifting into long modifier chains.
- If a sentence feels like narrated exposition instead of child-level story action, simplify it.

3. **Concrete scene over definition-like prose**
- A story line should show something happening.
- Avoid lines that only describe stable properties unless they directly help the scene.

4. **Avoid abstract moral/general lesson tone**
- Especially in `people_and_relationships.md`.
- Prefer `A child shares a toy with a friend.` over `Share builds a kind heart.`

5. **Avoid overly technical or adult-sounding vocabulary**
- Especially in `school_and_learning.md`.
- Replace words like `graphite`, `ceramic`, `compartment`, `drafting`, `aligned`, `focused attention` unless they are clearly justified and already safely grounded.

6. **Triplet visibility**
- All three triplet components should visibly matter in the story.
- Some stories mention the support words, but the scene still feels driven by generic filler.
- Tighten each story so the anchor/support relation feels necessary.

7. **Ending quality**
- End inside the scene instead of drifting into a slogan, moral, or mechanical add-on.
- If a contrast line is kept anywhere, make sure it is truly grounded and useful rather than inherited automatically from the old template.
- Recheck whether the ending feels like part of the scene the child can picture.

8. **Dialogue staging**
- If any rewrites add dialogue, do **not** jump straight to raw quoted dialogue by default.
- Story Layer 1 should prefer narrated indirect discourse.

## Recommended review order

1. `school_and_learning.md` — strongest rewrite need
2. `play_and_games.md` — fix structural mismatch first
3. `people_and_relationships.md` — reduce moral/generalized tone
4. `home_and_daily_life.md` — simplify denser stories
5. `weather_and_seasons.md` — simplify denser descriptions
6. `animals_and_nature.md`
7. `body_and_health.md`
8. `food_and_meals.md`
9. `tools_and_making.md`
10. `vehicles_and_travel.md`

## Suggested completion standard

Treat the batch as clean enough when:
- all files use the same Layer 1 structural template
- no file obviously drifts above the intended sentence complexity
- stories feel like concrete mini-scenes, not definitions or slogans
- support concepts are visible and genuinely integrated
- endings stay grounded and scene-based
- dialogue, if present, follows the staged rollout rules

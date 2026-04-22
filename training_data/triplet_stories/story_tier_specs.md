# Story Tier Specs

Canonical rewrite-stage spec for `training_data/triplet_stories/`.

These stories are short training scenes for a language model with Hebbian learning.
They are not wiki entries, not definitions, and not moral lessons.

Their job is to:
- show familiar words in clear grounded situations
- vary sentence structures without becoming confusing
- build a bridge between language and world-knowledge through simple events
- stay easy for a young child to follow

---

## Tier 1

### Purpose
Tier 1 is the first story layer after the earlier definitional curriculum and wiki material.

Tier 1 should:
- keep scenes simple, concrete, and easy to picture
- show the anchor and support concepts together in a small event
- introduce basic pronoun use in the clearest possible way
- help the model move from repeated noun phrases toward simple reference tracking
- stay close to immediate visible action, not explanation

### Required shape
- 8 sentences per story
- one anchor + two support concepts
- one small scene or event
- one main subject only
- clear beginning, middle, and end
- end inside the scene, not with a lesson or summary

### Tier 1 should contain
- a clearly visible anchor
- both support concepts used naturally in the event
- simple concrete actions
- simple locations, objects, and sensory details when useful
- a clear first mention of the main subject
- later sentences may use `he`, `she`, or `it` only after the referent is obvious

### Tier 1 is teaching
- noun-to-pronoun reference in a clear single-subject story
- simple event sequencing
- familiar words appearing in slightly varied sentence shapes
- grounded co-occurrence of anchor and support concepts

### Avoid in Tier 1
- names for recurring characters
- multi-character social tracking
- long causal chains
- abstract lessons or morals
- textbook phrasing
- poetic or literary inversion
- heavy description with little action
- ambiguous pronouns
- quoted dialogue as a default form

---

## Tier 2

### Purpose
Tier 2 builds on Tier 1 by adding more narrative structure and discourse variety.

Tier 2 should:
- keep stories concrete and child-readable
- make event chains longer
- introduce named characters where useful
- expand reference handling from noun to name to pronoun
- give the model richer but still controlled sentence variation

### Required shape
- 12 sentences per story
- one anchor + two support concepts
- one clear scene with a longer event chain
- usually one main character, sometimes one secondary participant if needed
- the story moves through a fuller sequence of actions
- end inside the scene, with the event resolved or naturally paused

### Tier 2 should contain
- a clear setting or scene frame
- the anchor introduced as the central subject
- when useful, a simple recurring name for the main subject
- support concepts integrated into the action, not pasted in
- a longer chain of events than Tier 1
- one mild obstacle, surprise, delay, or change
- a clear resolution or settling point by the end

### Tier 2 is teaching
- setting-first or scene-first framing
- noun to name to pronoun alternation
- longer reference chains without confusion
- richer temporal flow across a story
- broader sentence variation than Tier 1
- coherent mini-narratives built from familiar vocabulary

### Avoid in Tier 2
- dense adult-sounding prose
- too many characters
- confusing pronoun chains
- abstract reflection or hidden psychological narration
- sudden jumps in time with no clear bridge
- moralizing or summary endings
- overuse of quoted dialogue
- clever phrasing that reduces clarity

---

## Tier difference at a glance

### Tier 1
- 8 sentences
- one simple concrete event
- one clearly introduced subject
- first safe use of pronouns
- no names needed
- minimal discourse complexity

### Tier 2
- 12 sentences
- longer event chain
- scene-setting matters more
- named characters can appear
- noun / name / pronoun alternation
- one mild obstacle or change is allowed
- more sentence variety, still tightly controlled

---

## Global rules for both tiers
- stories are scenes, not definitions
- teach through what happens, not through explanation
- anchor and support concepts must all visibly matter
- keep everything grounded in child-level everyday reality unless the source material clearly requires otherwise
- avoid filler sentences that only add atmosphere
- do not end with "the lesson is" energy
- keep the meaning recoverable from context
- simplicity matters more than prettiness

# NOUN CLASSES

## N_CONCRETE_AGENT

Physical entity capable of intentional action.

Examples:
dog
teacher
child
bird

Allowed:

N1 subject + verb
N2 property

Examples:
The dog runs.
The teacher speaks.
The child is tired.

## N_CONCRETE_OBJECT

Physical entity without agency.

Examples:
stone
table
block of wood
blade of grass

Allowed:

N2 property

Optional:

passive environmental interaction

Examples:
The stone is heavy.
The blade of grass moves.

Forbidden:
intentional actions

## N_NATURAL_FORCE

Environmental/process entities.

Examples:
rain
wind
fire
sunlight

Allowed:

N3 environmental action
N2 property

Examples:
The wind blows.
The fire burns.

## N_ABSTRACT_QUALITY

Nonphysical qualities or concepts.

Examples:
ability
accuracy
acceptance
accountability
absence

Allowed:

A1 abstract + adjective
A2 affects
A3 possessed quality

Examples:
Ability is useful.
Accuracy improves results.
The leader has accountability.

## N_EVENT

Nominalized processes/events.

Examples:
accident
explosion
meeting
arrival

Allowed:

event occurs
event affects

Examples:
The accident causes damage.
The arrival surprises people.

These differ from abstract nouns because they represent bounded happenings.

## N_SOCIAL_STRUCTURE

Institutional/social constructs.

Examples:
accord
account
agreement
law

Allowed:

social effect templates

Examples:
The accord builds trust.
The account stores information.

This category helps avoid weird abstract handling.

# VERB CLASSES

This is probably the most important part.

## V_PHYSICAL_ACTION

Observable bodily/mechanical action.

Examples:
run
cut
write
carry

Allowed:

V1
V2
V4

Examples:
The boy runs.
The woman writes carefully.
People exercise to improve health.

## V_MENTAL_ACTION

Internal cognitive activity.

Examples:
accepting
considering
remembering

Allowed:

gerund abstraction
mental-action templates

Examples:
Accepting is difficult.
The student considers carefully.

Avoid overly introspective outputs.

## V_PROCESS

Slow/state/process change.

Examples:
accumulating
absorbing
aging

Allowed:

gerund abstraction
environmental/process templates

Examples:
Accumulating takes time.
The sponge absorbs water.

## V_SOCIAL_ACTION

Communication/social interaction verbs.

Examples:
accusing
agreeing
helping

Allowed:

social interaction templates

Examples:
The woman accuses unfairly.
Agreeing builds trust.

These need careful filtering because they can drift into emotionally loaded outputs.

# ADJECTIVE CLASSES

## ADJ_PHYSICAL

Observable sensory property.

Examples:
heavy
cold
sharp
bright

Allowed:

comparisons
property templates

## ADJ_EMOTIONAL

Emotion/cognitive-state descriptors.

Examples:
afraid
happy
anxious

Allowed:

state templates

Examples:
The child is afraid.

## ADJ_EVALUATIVE

Judgment/value descriptors.

Examples:
acceptable
accurate
important
abnormal

Allowed:

abstract evaluations
noun qualification

Examples:
Accurate information is useful.
Abnormal behavior is dangerous.

## ADJ_PROCESS_PARTICIPLE

Participial adjectives.

Examples:
absorbing
accepting
abiding

Allowed:

participle adjective templates

Examples:
The absorbing story interests readers.
The accepting teacher helps students.

# SPECIAL CLASSES

## MULTIWORD_ATOMIC

Examples:
blade of grass
block of wood

Rules:

never split internally
treat as single noun token

## DUAL_CLASS_WORD

Very important.

Words that can behave as multiple categories.

Examples:
accepting
abiding
accident

These should explicitly store:

primary class
secondary class

Example:

accepting:

## V_MENTAL_ACTION
## ADJ_PROCESS_PARTICIPLE

Then generation randomly selects from allowed compatible templates.

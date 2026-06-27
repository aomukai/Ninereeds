# TODO

Active tasks only. When a task is done: delete it here, add an entry to `history.md`.

---

## Next Campaign Design

### Design concept-card tutor loop / Mommy Says machine

Create the C18-ready design for per-concept adaptive teaching.

References:

- C17 handoff: `training/logs/campaign_17_reports/01_handoff.md`
- Tutor-loop spec: `training/pipeline/tutor_loop.md`
- Existing Mommy Says design: `training/pipeline/mommy_says_machine.md`
- Iteration schema: `training/pipeline/iteration_schema.md`

Design points to resolve:

- concept-card schema and persistent concept state
- prerequisite handling and dependency discovery
- protected-anchor policy in scheduler config
- PPP lesson generation interface for DeepSeek / LM Studio / template backends
- Ninereeds inference, grading, and validation loop
- training-answer extraction with block-size budgets
- SRS scheduling across concept difficulty and answer complexity
- promotion, rollback, and repair rules
- output layout for logs, diagnosis, validated corpus, and failed turns
- first prototype card set, likely `dog`, `tree`, `plant`, `animal`, `mammal`, `airport`, `airplane`, `water`, identity, and unknown-boundary anchors

Do not start broad training from C17 repair branches. Protected C17 checkpoint remains `core/c17_contrast_angle_1200_e4.pt`.

---

## Pipeline Infrastructure

- Extend `meta/scripts/campaign_runner.py` only after the tutor-loop design is settled.
- Later experiment: single-domain specialist ladder, e.g. animals only, scaling from short Q/A to richer prose and checking whether competence survives when adding a second specialty.

---

## Standing

- Fix 387 inverted K-8 education files in `training_data/04_education/dialogues/`.
- Update `angle_gen.py` BUCKETS dict to match `rebucket.py` if old redesign generator is reused.
- JP-specific corpus from imabi.org / guidetojapanese.org if the JP gap is confirmed structural.
- Wiki splitting into single-concept files for future fine-grained ordering.

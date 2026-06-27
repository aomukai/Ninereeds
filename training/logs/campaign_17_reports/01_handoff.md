# Campaign 17 Handoff

Date: 2026-06-28

## Status

Campaign 17 is closed.

Protected checkpoint:

- `core/c17_contrast_angle_1200_e4.pt`

Do not promote or continue from repair branches unless the next experiment is
explicitly testing recovery behavior. The repair branches are useful evidence,
not stable successors.

## Main Result

C17 did not produce a final chat model, but it did narrow the training method.

Best result:

- branch: contrast-angle 1,200 concepts
- checkpoint: `core/c17_contrast_angle_1200_e4.pt`
- default eval: 5/7, avg 0.905
- interpretation: small chunks with high cross-concept contrast reduced mixing
  better than full-corpus training or dependency order alone

Failed or weaker paths:

- full mixed corpus: 1/7, avg 0.262
- full dependency/curriculum corpus: 1/7, avg 0.143
- sorted 1,200-concept ladder: peaked at 4/7, avg 0.857
- broad boundary repair: repaired some target probes but damaged default grounding
- micro boundary repair: too weak to repair targets, still disturbed default grounding

## Key Findings

- Alphabetic order was a problem, but not the only problem.
- Contrast ordering helped more than dependency ordering for the current model.
- More data is not automatically better on this architecture.
- The model can learn small kernels, but scaling volume causes interference.
- Repair data has dose thresholds: too much damages baseline, too little still
  perturbs without repairing.
- Concept failures are likely individual: one concept may need prerequisites,
  another contrast, another a similar cluster, another postponement.
- Short-answer stability must come before triplets, stories, wiki articles, or
  free prose.

## Important Artifacts

Reports and summaries:

- Raw campaign report: `training/logs/campaign_17_reports/00_prelaunch.md`
- Runner summary: `training/logs/campaign_17_reports/campaign_runner_summary.jsonl`
- Manual gates: `training/logs/campaign_17_reports/c17_*_manual_gate.md`
- Default eval reports: `training/logs/grounding_eval/`

Runner and recipe tools:

- `meta/scripts/build_c17_recipe.py`
- `meta/scripts/campaign_runner.py`
- `meta/scripts/build_c17_boundary_repair.py`
- `meta/scripts/build_c17_boundary_repair_v2.py`
- `meta/scripts/build_c17_boundary_micro_v3.py`

Configs:

- `training/pipeline/campaign_runner_c17.json`
- `training/pipeline/campaign_runner_c17_boundary_repair.json`
- `training/pipeline/campaign_runner_c17_boundary_v2.json`
- `training/pipeline/campaign_runner_c17_boundary_micro_v3.json`

Design docs:

- Iteration schema: `training/pipeline/iteration_schema.md`
- Tutor loop: `training/pipeline/tutor_loop.md`
- Existing Mommy Says machine design: `training/pipeline/mommy_says_machine.md`

## Best Checkpoints by Meaning

- Protected C17 best: `core/c17_contrast_angle_1200_e4.pt`
- Best sorted/dependency evidence: `core/c17_ladder_1200_e2.pt` or `core/c17_ladder_1200_e3.pt`
- Best repair evidence: `core/c17_damaged_concepts_v2_e1.pt`
- Do not continue: `core/c17_contrast_review_repair_v2_e*.pt`
- Do not promote: any `core/c17_boundary_micro_v3_*` checkpoint

## Next Direction

Design the concept-card tutor loop before more broad training.

The next system should treat each concept as a stateful learning problem:

- declared prerequisites
- positive anchors
- negative contrasts
- similar and distant concepts
- unknown-boundary facts
- protected-anchor replay
- SRS box
- answer complexity level
- failure history

The tutor should run a PPP cycle:

1. positive presentation
2. negative presentation
3. W-questions
4. OR-questions
5. controlled practice
6. guided practice
7. free practice only after gates pass

Only validated short `training_answer` fields should enter the training corpus.
Long diagnostic answers and failed free-practice turns are logs only.

## C18 Design Task

Start with a design/prototype, not a training run.

Recommended first implementation target:

- concept card schema
- concept state JSON
- tutor backend interface: template first, DeepSeek/LM Studio later
- Ninereeds inference wrapper
- grader and validator
- JSONL extraction with block-size budgets
- scheduler with protected anchors and rollback policy
- first card set: dog, tree, plant, animal, mammal, airport, airplane, water,
  identity, unknown-boundary anchors

The active task is tracked in `todo.md`.

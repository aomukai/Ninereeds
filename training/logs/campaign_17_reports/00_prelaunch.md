# Campaign 17 Prelaunch

Date: 2026-06-27

## State

- Training process: none running at prelaunch check.
- Failed mixed corpus: `training/corpus/kernel_c17_mixed.jsonl`
- Failed mixed corpus report: `training/corpus/kernel_c17_mixed_report.md`
- Failed mixed corpus examples: 249,482
- Failed mixed corpus identity/control share: 12.000%
- Corrected corpus: `training/corpus/kernel_c17_curriculum_singleturn.jsonl`
- Corrected corpus report: `training/corpus/kernel_c17_curriculum_singleturn_report.md`
- Corrected corpus examples: 202,635
- Corrected corpus identity/control share: 12.000%
- Compact ladder corpus: `training/corpus/kernel_c17_ladder_1200_e1.jsonl`
- Compact ladder report: `training/corpus/kernel_c17_ladder_1200_e1_report.md`
- Compact ladder examples: 47,763
- Concept-block contrast corpus: `training/corpus/kernel_c17_contrast_1200_e1.jsonl`
- Small-chunk contrast corpus: `training/corpus/kernel_c17_contrast_angle_1200_e1.jsonl`
- Identity source audit: passed, 219 files

## Research Question

Can the JSONL kernel corpus produce a chat-capable Ninereeds core that improves grounding while preserving identity and unknown-boundary behavior?

## Recipe Reset

The first continued run on `training/corpus/kernel_c17_mixed.jsonl` failed grounding eval:

- checkpoint: `core/c17_kernel_continue_e1.pt`
- eval: `training/logs/grounding_eval/c17_kernel_continue_e1.md`
- result: 1/7 pass, avg score 0.262

Likely causes:

- alphabetic concept order
- full-vocabulary shock from the proof kernel
- incidental mentions outnumbering direct anchors
- multi-turn prompt context with short prompt tails
- continuation LR too high for a useful proof checkpoint

Corrected recipe:

- dependency/cluster order from `training/corpus_admin/curriculum_order.json`
- source roots: `training_data/kernel_from_redesign/` + `training_data/kernel_gap_fill/`
- single-turn examples only
- lowercase user prompt copies preserved
- identity/control interleaved at 12%
- no triplet/story layer yet
- continuation LR lowered to `1e-4`

The full corrected curriculum run still failed grounding eval:

- checkpoint: `core/c17_kernel_curriculum_e1.pt`
- eval: `training/logs/grounding_eval/c17_kernel_curriculum_e1.md`
- result: 1/7 pass, avg score 0.143

Current quick-iteration recipe:

- restart from `core/kernel_e1_focus_repair.pt`
- cap at first 1,200 curriculum-ranked concepts
- keep single-turn only
- bookend the main corpus with `training/corpus/kernel_repair_focus_x20.jsonl`
- keep 12% identity/control interleave
- compare ordering modes before adding triplet/story material

Compact ladder result:

- checkpoint: `core/c17_ladder_1200_e1.pt`
- train log: `training/logs/campaign_17_reports/c17_ladder_1200_e1_train.log`
- final epoch loss: 0.8099
- eval: `training/logs/grounding_eval/c17_ladder_1200_e1.md`
- result: 3/7 pass, avg score 0.595
- manual read: identity and dog anchors improved; airport/airplane still cross-contaminate; unrelated concepts such as tree can still collapse into animal wording
- decision: not promotion-ready; use as evidence that compact, bookended training helps, then compare against stronger contrast ordering

Contrast-angle e1 result:

- checkpoint: `core/c17_contrast_angle_1200_e1.pt`
- train log: `training/logs/campaign_17_reports/c17_contrast_angle_1200_e1_train.log`
- final epoch loss: 0.6179
- eval: `training/logs/grounding_eval/c17_contrast_angle_1200_e1.md`
- result: 4/7 pass, avg score 0.822
- decision: best C17 signal so far; continue multi-epoch comparison instead of promoting after one epoch

Ordering candidates:

- `kernel_c17_ladder_1200_e1.jsonl`: dependency/curriculum order
- `kernel_c17_contrast_1200_e1.jsonl`: concept-block contrast across clusters/categories
- `kernel_c17_contrast_angle_1200_e1.jsonl`: small-chunk contrast across clusters/categories by angle pass

## Later Branch: Specialist Domains

One possible architecture probe is to train a narrow specialist before asking the model to multiplex many domains.

Example branch:

- start with one bounded cluster, such as animals
- train short direct Q/A first
- scale language gradually from short sentences to longer descriptions
- later add animal-only triplets, story material, and eventually curated article material
- evaluate whether the model can become fluent and roughly "smart elementary school student" level inside that one domain
- only then add a second specialty and check whether the first specialty survives

Diagnostic value:

- If one-domain specialization cannot reach stable competence, the issue is not mainly cross-domain interference.
- If one-domain specialization works but adding more domains breaks it, the main problem is likely capacity, interference, ordering, or merge strategy.
- If separate specialists work but sequential specialties interfere, later work can test targeted training, transplanting, or merge methods.

Observed motivation:

- a tiny roughly 50-word kernel can be coherent
- scaling toward roughly 5,000 concepts currently degrades coherence and grounding
- a single-cluster specialist can test whether the architecture learns deeply when the concept space is narrow

## Training Commands

Compact ladder continued run from the current kernel proof winner:

```bash
CUDA_VISIBLE_DEVICES=0 PYTORCH_ALLOC_CONF=expandable_segments:True \
setsid -f bash -lc 'env CUDA_VISIBLE_DEVICES=0 PYTORCH_ALLOC_CONF=expandable_segments:True /home/aomukai/.unsloth/studio/unsloth_studio/bin/python train.py \
  --phase 0 \
  --jsonl-data training/corpus/kernel_c17_ladder_1200_e1.jsonl \
  --mask-instruction-loss \
  --prompt-loss-weight 0.0 \
  --prompt-tail-bytes 96 \
  --block-size 128 \
  --resume core/kernel_e1_focus_repair.pt \
  --output core/c17_ladder_1200_e1.pt \
  --epochs 1 --amp-bf16 --no-shuffle \
  --lr 1e-4 \
  --batch-size 4 \
  > training/logs/campaign_17_reports/c17_ladder_1200_e1_train.log 2>&1'
```

Contrast-angle continued run, after the ladder result is evaluated:

```bash
CUDA_VISIBLE_DEVICES=0 PYTORCH_ALLOC_CONF=expandable_segments:True \
setsid -f bash -lc 'env CUDA_VISIBLE_DEVICES=0 PYTORCH_ALLOC_CONF=expandable_segments:True /home/aomukai/.unsloth/studio/unsloth_studio/bin/python train.py \
  --phase 0 \
  --jsonl-data training/corpus/kernel_c17_contrast_angle_1200_e1.jsonl \
  --mask-instruction-loss \
  --prompt-loss-weight 0.0 \
  --prompt-tail-bytes 96 \
  --block-size 128 \
  --resume core/kernel_e1_focus_repair.pt \
  --output core/c17_contrast_angle_1200_e1.pt \
  --epochs 1 --amp-bf16 --no-shuffle \
  --lr 1e-4 \
  --batch-size 4 \
  > training/logs/campaign_17_reports/c17_contrast_angle_1200_e1_train.log 2>&1'
```

Unattended multi-epoch watchdog:

```bash
setsid -f bash -lc '/home/aomukai/.unsloth/studio/unsloth_studio/bin/python -u meta/scripts/c17_watchdog.py --max-epoch 4 --poll-seconds 1800 >> training/logs/campaign_17_reports/c17_watchdog.stdout.log 2>&1'
```

Watchdog behavior:

- checks every 30 minutes
- never starts a new train run while a Campaign 17 train process is active
- evaluates each checkpoint after each epoch
- writes greedy manual probe reports after each eval
- continues sorted and contrast tracks through epoch 4 unless interrupted
- current run after watchdog restart: sorted e2 from `core/c17_ladder_1200_e1.pt`

Watchdog outputs:

- main log: `training/logs/campaign_17_reports/c17_watchdog.log`
- stdout/stderr: `training/logs/campaign_17_reports/c17_watchdog.stdout.log`
- summary JSONL: `training/logs/campaign_17_reports/c17_watchdog_summary.jsonl`
- manual gates: `training/logs/campaign_17_reports/c17_*_manual_gate.md`

Adaptive campaign runner:

```bash
setsid -f bash -lc '/home/aomukai/.unsloth/studio/unsloth_studio/bin/python -u meta/scripts/campaign_runner.py --config training/pipeline/campaign_runner_c17.json --max-epoch 4 --poll-seconds 1800 >> training/logs/campaign_17_reports/campaign_runner.stdout.log 2>&1'
```

Runner behavior:

- checks VRAM before every train run
- chooses train parameters from available VRAM:
  - `full`: >=5500 MiB free, batch 4, grad accumulation 1
  - `medium`: >=3800 MiB free, batch 2, grad accumulation 2, Adam8bit
  - `low`: >=2500 MiB free, batch 1, grad accumulation 4, Adam8bit
- waits instead of training below the low tier
- retries with a smaller tier if a run OOMs
- evaluates and writes manual probe reports after each checkpoint
- resumes from existing checkpoint/eval/manual-gate artifacts

Runner outputs:

- main log: `training/logs/campaign_17_reports/campaign_runner.log`
- stdout/stderr: `training/logs/campaign_17_reports/campaign_runner.stdout.log`
- summary JSONL: `training/logs/campaign_17_reports/campaign_runner_summary.jsonl`
- config: `training/pipeline/campaign_runner_c17.json`

Boundary repair continuation:

- repair corpus: `training/corpus/kernel_c17_boundary_repair.jsonl`
- contrast-review corpus: `training/corpus/kernel_c17_contrast_review_repair.jsonl`
- repair report: `training/corpus/kernel_c17_boundary_repair_report.md`
- boundary eval suite: `training/corpus_admin/probe_sets/c17_boundary.jsonl`
- config: `training/pipeline/campaign_runner_c17_boundary_repair.json`
- base: `core/c17_contrast_angle_1200_e4.pt`
- baseline boundary eval on base: `training/logs/grounding_eval/c17_contrast_angle_1200_e4_boundary.md`, 1/6 pass, avg 0.584
- schedule: one boundary-repair epoch, then contrast-review epochs from the repaired checkpoint

Iteration schema:

- schema: `training/pipeline/iteration_schema.md`
- protect current best: `core/c17_contrast_angle_1200_e4.pt`
- branch from current best for repair tests
- run default eval and target eval after each epoch
- keep a branch only if default eval does not regress and target eval improves
- roll back to current best if default eval drops below the gate

Boundary repair v2:

- repair corpus: `training/corpus/kernel_c17_boundary_repair_v2.jsonl`
- damaged-concepts corpus: `training/corpus/kernel_c17_damaged_concepts_v2.jsonl`
- contrast-review corpus: `training/corpus/kernel_c17_contrast_review_repair_v2.jsonl`
- target eval: `training/corpus_admin/probe_sets/c17_boundary_v2.jsonl`
- config: `training/pipeline/campaign_runner_c17_boundary_v2.json`
- active schedule: damaged-concepts diagnostic, then low-dose boundary repair, then low-dose contrast review
- learning rate: `2e-5`

Boundary repair v2 result:

- `core/c17_damaged_concepts_v2_e1.pt`: default 5/7 avg 0.869; boundary_v2 7/7 avg 0.964
- `core/c17_boundary_repair_v2_e1.pt`: default 4/7 avg 0.857; boundary_v2 5/7 avg 0.869
- `core/c17_contrast_review_repair_v2_e1.pt`: default 4/7 avg 0.822; boundary_v2 5/7 avg 0.881
- `core/c17_contrast_review_repair_v2_e2.pt`: default 4/7 avg 0.822; boundary_v2 5/7 avg 0.881
- interpretation: damaged-concepts-only low-LR repair is the best repair branch so far, but still does not beat protected best `core/c17_contrast_angle_1200_e4.pt` on default avg
- decision: keep protected best; do not continue the contrast-review-repair branch without a new dose/schedule

Boundary repair micro v3:

- builder: `meta/scripts/build_c17_boundary_micro_v3.py`
- config: `training/pipeline/campaign_runner_c17_boundary_micro_v3.json`
- report: `training/corpus/kernel_c17_boundary_micro_v3_report.md`
- base for every candidate: `core/c17_contrast_angle_1200_e4.pt`
- learning rate: `1e-5`
- candidates:
  - `training/corpus/kernel_c17_boundary_micro_v3_targeted_1x.jsonl`: 82 examples
  - `training/corpus/kernel_c17_boundary_micro_v3_balanced_1x.jsonl`: 92 examples
  - `training/corpus/kernel_c17_boundary_micro_v3_targeted_2x.jsonl`: 116 examples
  - `training/corpus/kernel_c17_boundary_micro_v3_balanced_2x.jsonl`: 136 examples
- purpose: test whether the v2 boundary gain can be approached with lower repair dose while preserving the default gate
- promotion rule: do not promote unless default score matches or beats `core/c17_contrast_angle_1200_e4.pt` and boundary_v2 remains improved

Boundary repair micro v3 result:

- `core/c17_boundary_micro_v3_targeted_1x_e1.pt`: default 4/7 avg 0.857; boundary_v2 2/7 avg 0.607
- `core/c17_boundary_micro_v3_balanced_1x_e1.pt`: default 4/7 avg 0.857; boundary_v2 2/7 avg 0.607
- `core/c17_boundary_micro_v3_targeted_2x_e1.pt`: default 4/7 avg 0.857; boundary_v2 2/7 avg 0.607
- `core/c17_boundary_micro_v3_balanced_2x_e1.pt`: default 4/7 avg 0.857; boundary_v2 2/7 avg 0.607
- interpretation: these files are below the effective repair threshold while still disturbing the default gate; lower dose alone is not a viable fix
- decision: keep protected best `core/c17_contrast_angle_1200_e4.pt`; treat v2 damaged-concepts-only as the best evidence that concept-local repair can work, but do not promote it because default avg remains below protected best
- next useful direction: build concept-card/tutor-loop diagnostics instead of more hand-sized global repair files

Use `--batch-size 1 --grad-accum-steps 2 --adam8bit` if GPU 0 is memory-tight.

## Post-Epoch Evaluation

```bash
CKPT=core/c17_ladder_1200_e1.pt
NAME=c17_ladder_1200_e1

CUDA_VISIBLE_DEVICES=0 /home/aomukai/.unsloth/studio/unsloth_studio/bin/python meta/scripts/eval_grounding.py \
  --checkpoint "$CKPT" \
  --name "$NAME"

CUDA_VISIBLE_DEVICES=0 python meta/scripts/brain_map.py probe \
  --checkpoint "$CKPT" \
  --probes training/corpus_admin/probe_sets/redesign_current.jsonl \
  --name "${NAME}_redesign_current"
python meta/scripts/brain_map.py hubs --name "${NAME}_redesign_current" --threshold 0.7
python meta/scripts/brain_map.py trace \
  --checkpoint "$CKPT" \
  --probes training/corpus_admin/probe_sets/redesign_current.jsonl \
  --name "${NAME}_redesign_current"
```

Then copy the candidate to `chat/ninereeds.pt` and run a manual chat gate for identity, known facts, false links, and missing specifics.

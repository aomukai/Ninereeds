# Ninereeds Automation Pipeline

Design reference for the campaign automation layer. Describes what the current
`c15_pipeline.py` does, what `campaign_runner.py` should do, and the notification /
status-tracking contract.

Corpus layer descriptions and curriculum ordering are in `docs/curriculum_topology.md`.
Step-by-step training procedure is in `training/docs/training.md`.

Last updated: 2026-06-21

---

## Current automation: `meta/scripts/c15_pipeline.py`

Runs blocks 2–5 of Campaign 15 sequentially without human intervention.

### What it does

For each block:
1. Check GPU 0 free memory (≥ 1300 MiB); wait 30s and retry if below threshold.
2. Launch `train.py` with `CUDA_VISIBLE_DEVICES=0`, `PYTORCH_ALLOC_CONF=expandable_segments:True`.
3. Poll for all 3 epoch checkpoints (60s interval).
4. Run `eval.py` on each epoch checkpoint (CUDA:0).
5. Run `brain_map.py probe` + `brain_map.py hubs` for both language and thinking probe sets.
6. Read `arithmetic_jp` after-hub from each thinking hubs JSON.
7. Pick winner: highest `arithmetic_jp`; tiebreak by shaped score.
8. Copy winner to `checkpoints/<name>_winner.pt`.
9. Move to next block.

### What it does NOT do

- Corpus building (assumes pre-built .txt files exist)
- Notifications (no signal when a block completes)
- Campaign config (blocks are hardcoded)
- OOM retry (if training OOMs, the subprocess exits and the pipeline hangs on checkpoint wait)
- Per-block report stubs
- Status file

### Invocation

```bash
cd "/media/aomukai/SSD External/Ninereeds"
nohup /home/aomukai/.unsloth/studio/unsloth_studio/bin/python \
  meta/scripts/c15_pipeline.py \
  --start-block 3 \
  --base checkpoints/c15_arith_grounded_winner.pt \
  > training/logs/campaign_15_reports/c15_pipeline.log 2>&1 &
```

`--start-block N` skips to block N. If epoch checkpoints for block N already exist,
training is skipped and eval starts immediately.

### Known constraints

- `min_free_mib=1300` threshold: with mnm.exe at 7.4 GB VRAM, only ~1300–1600 MiB is
  ever free. The threshold is set to confirm eval has released memory, not to compete with
  the game.
- Training uses `--batch-size 1 --grad-accum-steps 2 --adam8bit` when VRAM is tight.
  This reduces peak VRAM by ~350 MB vs default batch=4.
- CUDA_VISIBLE_DEVICES=0 is hardcoded for both training and eval.

---

## Planned: `meta/scripts/campaign_runner.py`

A general-purpose campaign runner that handles a full campaign from corpus build
through all blocks, with notifications and robust error handling.

### Design goals

1. **Config-driven** — no hardcoded block lists; reads a YAML campaign config.
2. **Notifications** — `notify-send` after every significant step.
3. **Status file** — writes `training/logs/campaign_N/status.json` after each step.
4. **OOM retry** — automatically retries with reduced batch if training OOMs.
5. **Corpus build** — calls `build_training_corpus.py` if the corpus .txt does not exist.
6. **Report stubs** — auto-generates the markdown header for each block report.

### Campaign config format (YAML)

```yaml
# training/corpus_admin/campaign16.yaml
campaign: 16
base: checkpoints/c15_education_winner.pt
log_dir: training/logs/campaign_16_reports
notify: true

blocks:
  - id: 1
    name: c16_language
    corpus_manifest: training/corpus_admin/campaign16_manifest.txt
    epochs: 3
    batch_size: 4
    notes: "Full curriculum retrain with EDJC rotation"

  - id: 2
    name: c16_arith_grounded
    corpus: training/corpus/c16_arith_grounded.txt
    epochs: 3
    batch_size: 1
    grad_accum: 2
    adam8bit: true
    notes: "Arith prepended at 2% of grounded stories"

  - id: 3
    name: c16_reasoning
    corpus: training/corpus/c16_reasoning.txt
    epochs: 3
    batch_size: 1
    grad_accum: 2
    adam8bit: true
    notes: "ArithB paraphrase + reasoning"

  - id: 4
    name: c16_vignettes
    corpus: training/corpus/c16_vignettes.txt
    epochs: 1
    batch_size: 4
    notes: "1 epoch only — arith_jp collapses at E2/E3 (confirmed C15)"

  - id: 5
    name: c16_education
    corpus: training/corpus/c16_education.txt
    epochs: 3
    batch_size: 4
    notes: "CKS K-8 dialogues"
```

### Notification contract

Each `notify-send` call carries:
- Title: block name + step
- Body: key metric(s)
- Urgency: `normal` for step done, `critical` for error

```bash
# Examples
notify-send "C16 B1 training done" "E3 complete — running brain scans" --urgency normal
notify-send "C16 B1 winner: E2" "arith_jp=0.987  shaped=0.958" --urgency normal
notify-send "C16 COMPLETE" "Final winner: c16_education_winner.pt" --urgency critical
notify-send "C16 B3 OOM — retrying" "batch=1 adam8bit grad_accum=2" --urgency critical
```

### Status file format

Written to `training/logs/campaign_N/status.json` after every state change:

```json
{
  "campaign": 16,
  "started": "2026-06-22T10:00:00",
  "current_block": 3,
  "blocks": {
    "1": {"status": "done", "winner": "E2", "arith_jp": 0.987, "shaped": 0.958},
    "2": {"status": "done", "winner": "E1", "arith_jp": 0.990, "shaped": 0.976},
    "3": {"status": "training", "epoch": 2}
  }
}
```

### OOM retry logic

```
attempt 1: batch_size from config (e.g. 4)
  → OOM detected (train.py exits non-zero within 60s of launch)
attempt 2: batch_size=1, grad_accum=2, adam8bit=True, expandable_segments=True
  → notify-send "OOM retry with reduced batch"
  → OOM again → abort block, notify user, stop pipeline
```

### Winner selection

Same logic as `c15_pipeline.py`:
1. Primary: highest `arithmetic_jp` after-hub (thinking brain_map)
2. Tiebreak: highest shaped score

Full brain scan tables are written to the eval log for human review. The automated
pick is logged with the full epoch comparison table.

---

## Probe sets

| Set | Path | Probes | Categories |
|---|---|---|---|
| Language | `training/corpus_admin/probe_sets/language.jsonl` | 104 | 16 |
| Thinking | `training/corpus_admin/probe_sets/thinking.jsonl` | 94 | 14 |

Thinking categories: arithmetic (EN/DE/JP/ZH), arithmetic_para, arithmetic_grounded,
identity, comparison, successor, zero, sequence, rule_application, contrastive, grounded_causal.

Primary winner metric: `arithmetic_jp` from thinking set.

---

## Related files

- `docs/curriculum_topology.md` — corpus inventory, campaign findings, ordering hypothesis
- `training/docs/training.md` — step-by-step training procedure, eval commands
- `meta/scripts/c15_pipeline.py` — current automation script
- `training/corpus_admin/probe_sets/` — language and thinking probe JSONL files

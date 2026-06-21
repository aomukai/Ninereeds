# Campaign Runbook

Pre-launch checklist and step-by-step procedure for every campaign.
This is the document you open when starting a new campaign.

Reference docs (not procedure):
- `curriculum_topology.md` — what we know, what we've tried, corpus inventory
- `training.md` — intervention registry, conventions, guardrails
- `pipeline.md` — automation spec (campaign_runner.py)

---

## Evaluation philosophy

Training Ninereeds is not traditional ML. Loss curves track pattern fit, not comprehension.
The correct training signal is practical: does the model chat better than it did before?

**The epoch loop:**
1. Train one epoch
2. Brain scan — are concept clusters forming? any routing hub collapse?
3. `eval_concept.py` — does it answer varied questions about random words correctly?
4. Chat session — human impression: does it understand questions? does it talk about Rome?
5. Compare to previous epoch across all three signals
6. If better on balance: save as provisional winner, train next epoch
7. If regressed on balance: previous epoch was the peak, stop

**Decision criteria (in order):**
1. Chat session impression — primary. This is what we are building toward.
2. `eval_concept` flag count and reading of the log — practical comprehension.
3. Brain scan after-hub scores — structural signal: are concepts represented or just routed?
4. Shaped score — secondary confirmation only.
5. Training loss — ignore. It does not track comprehension.

**Stopping rule:** stop at the first epoch where the chat session and eval_concept both feel
worse than the previous epoch. The winner is the last epoch before regression, not the
lowest-loss epoch and not necessarily the highest probe score.

---

## Part 1 — Pre-launch checklist

Every item must be confirmed before training starts. If any item is unknown, resolve it first.

### Research question
- [ ] State in one sentence what this campaign is testing or trying to improve

### Base checkpoint
- [ ] Path confirmed: `checkpoints/<name>.pt`
- [ ] Shaped score and `arithmetic_jp` after-hub known (run eval + brain scan if not)
- [ ] It is a promoted winner, not an intermediate epoch checkpoint

### Block sequence
- [ ] All blocks defined: name, corpus .txt path, epoch count, batch size
- [ ] Vignettes block: **1 epoch only** (confirmed C15: arith_jp drops −0.08 per epoch beyond E1)
- [ ] Arithmetic is not a standalone block — embedded at ≤2% of grounded stories

### Corpus
- [ ] Each corpus .txt built with `build_training_corpus.py --order-file <manifest>`
- [ ] Each build report ends with: `All files validated — corpus is clean.`
- [ ] Zero skipped files in every block

### Infrastructure
- [ ] GPU free memory checked: if < 2 GB, plan for `--batch-size 1 --grad-accum-steps 2 --adam8bit`
- [ ] `PYTORCH_ALLOC_CONF=expandable_segments:True` ready for memory-tight blocks
- [ ] Probe sets exist: `training/corpus_admin/probe_sets/language.jsonl` + `thinking.jsonl`
- [ ] Log directory created: `training/logs/campaign_N_reports/`

### Automation
- [ ] `training/pipeline/campaign_N.yaml` written (block list, base, notify: true)
- [ ] `notify-send` confirmed available on this machine

---

## Part 2 — Campaign procedure

### Step 0 — Orient (run this first, every session)

```bash
ps aux | grep train.py | grep -v grep      # is training already running?
ls -lh core/c1*.pt 2>/dev/null | tail -10  # what checkpoints exist?
tail -5 training/logs/campaign_N_reports/*.log 2>/dev/null    # pipeline state
```

Three states:
- **Training running** — do not launch. Monitor until epoch checkpoint appears, then go to Step 3.
- **Training done, reports incomplete** — go to Step 3 for each unfilled epoch.
- **Campaign complete** — write summary report, update `index.md` and `history.md`, plan next campaign.

---

### Step 1 — Read the previous campaign report

Open the latest report in `training/logs/campaign_N_reports/`.
Read: block results table, winner rationale, key findings, what to try next.
**Do not choose an intervention from memory.** The report is the source of truth.

---

### Step 2 — Launch training

Train **one epoch at a time**. Do not pre-schedule multiple epochs — each epoch gets a full
eval before deciding whether to train another.

**Manually (current approach):**
```bash
PYTHON=/home/aomukai/.unsloth/studio/unsloth_studio/bin/python
CUDA_VISIBLE_DEVICES=0 PYTORCH_ALLOC_CONF=expandable_segments:True \
nohup $PYTHON train.py \
  --phase 0 \
  --corpus-file training/corpus/<block>.txt \
  --output core/<name>_e1.pt \
  --resume checkpoints/<base>.pt \
  --epochs 1 --amp-bf16 --no-shuffle \
  --batch-size 4 \
  > training/logs/campaign_N_reports/<block>_e1_train.log 2>&1 &
echo "PID: $!"
```

Add `--batch-size 1 --grad-accum-steps 2 --adam8bit` if VRAM is tight.
Use `CUDA_VISIBLE_DEVICES=0` for both training and eval. Never use GPU 1 (daily-use card).

Monitor: poll for the output file, not the log tail (log is buffered).
```bash
until [ -f core/<name>_e1.pt ]; do sleep 60; done && echo "E1 done"
```

---

### Step 3 — Eval the epoch

Run all three evaluations as soon as the checkpoint appears. Do them in order — chat session
last, because it is the most expensive and is the deciding signal.

```bash
CKPT=core/<name>_eK.pt
NAME=<name>_eK

# 1. Brain scan
CUDA_VISIBLE_DEVICES=0 python meta/scripts/brain_map.py probe \
  --checkpoint $CKPT \
  --probes training/corpus_admin/probe_sets/thinking.jsonl \
  --name ${NAME}_thinking
python meta/scripts/brain_map.py hubs --name ${NAME}_thinking --threshold 0.7

# 2. Concept eval — sample 30 random words, varied question phrasing
CUDA_VISIBLE_DEVICES=0 python meta/scripts/eval_concept.py \
  --checkpoint $CKPT --words 30
# Read the output log. Note: flag counts, obvious failures, overall impression.

# 3. Chat session — copy checkpoint to chat/ninereeds.pt, open chat
cp "$CKPT" chat/ninereeds.pt
cd chat && python3 chat.py
# Pick 5–10 random topics. Ask each in 2–3 different ways.
# Note: does it understand the question? does it stay on topic? does it know "I don't know"?
```

Record in the block report:
- Brain scan: `arithmetic_jp` after-hub (structural signal), any notable category changes
- eval_concept: flag count, any ROME/FOREIGN/EMPTY hits, your reading of the log
- Chat impression: 2–3 sentence summary of what worked and what didn't

---

### Step 4 — Continue or stop

After reviewing all three eval signals:

**Continue (train next epoch):** chat session and eval_concept both feel better or equal to
the previous epoch, and brain scan shows no hub collapse.

**Stop (winner found):** chat session or eval_concept feels worse than the previous epoch.
The winner is the **previous** epoch's checkpoint, not this one.

```bash
# If continuing:
# → Use current checkpoint as --resume for next epoch (same block, same corpus)

# If stopping:
BEST=core/<name>_e(K-1).pt
DEST=checkpoints/<campaign>_<block>_winner.pt
cp "$BEST" "$DEST"
ls -lh "$DEST"
```

**Never use training loss as a stopping criterion. Never pick the lowest-loss epoch.**

---

### Step 5 — Promote the winner

```bash
BEST=core/<name>_eK.pt
DEST=checkpoints/<campaign>_<block>_winner.pt

cp "$BEST" "$DEST"
ls -lh "$DEST"   # confirm before deleting anything

# Delete the other epoch files for this block
find core/ -name "<name>_e*.pt" ! -name "<name>_eK.pt" -delete
ls core/<name>*.pt   # confirm what remains
```

---

### Step 6 — Write the block report

File: `training/logs/campaign_N_reports/NN_<block_name>.md`

Required sections:
1. Setup table (base checkpoint, corpus, files, epochs, batch size, any special flags)
2. Motivation (what is this block testing, why this corpus)
3. Results table (all epochs: shaped, EN, DE, JP, ZH, arith_jp after-hub, spatial after-hub)
4. Full brain scan tables (copy from hub JSON outputs)
5. Winner selection (which epoch, why, what was traded off)
6. Key observations (what this block revealed for the next block or campaign)

---

### Step 7 — Repeat for next block

Use the promoted winner as the base for the next block. Return to Step 2.

---

### Step 8 — Campaign wrap-up

After all blocks complete:

1. Update `index.md` Current State table
2. Add campaign summary entry to `history.md`
3. Update `docs/curriculum_topology.md` Campaign results section
4. Delete tasks from `todo.md` that are now complete
5. Add C(N+1) design tasks to `todo.md`

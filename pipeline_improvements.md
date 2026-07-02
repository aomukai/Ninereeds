# MSM Pipeline Improvements

Design notes for making the autonomous Ninereeds training loop robust, token-aware, and low-observation.

Status: draft implementation spec
Created: 2026-07-03
Scope: Codex/orchestrator, Hermes, DeepSeek, training-machine worker, rate-limit brakes, and auto-escalation policy

---

## 1. Design Goal

The lab should run as a 24/7 research loop with minimal human observation.

The system should continue autonomously while conditions are routine, pause safely when a boundary is reached, and page Andi only when manual attention is required.

The main principle is:

```text
Codex thinks.
DeepSeek does tactical language/report/script work.
Gemma/Ninereeds executes fixed sessions.
Hermes pages the human.
Shell/Python does boring monitoring and IO.
```

Codex reasoning tokens are precious. Codex should be used for analysis, campaign policy, boundary decisions, update approval, recovery strategy, and repo changes. Codex should not be used for repetitive IO, log watching, simple status checks, or routine auto-advance decisions.

---

## 2. Machine Split

### Main machine

Owns the control plane.

Responsibilities:

```text
- Codex/orchestrator session
- Hermes watchdog and Discord interface
- DeepSeek API/report worker, unless deliberately moved
- status parsing and rate-limit brake generation
- rsync backups from training machine
- checkpoint pulls for local chat UI
- final authority over update promotion
```

### Training machine

Owns the execution plane.

Responsibilities:

```text
- Pop!_OS / Linux-only ext4 system drive
- NVIDIA driver and RTX 3060 worker
- Ninereeds repo clone
- Gemma/local inference worker
- llama.cpp and small helper models if needed
- training/session execution
- raw logs and session artifacts
- immutable checkpoint files
```

The training machine should be boring and stable. It should run 24/7, have SSH enabled, avoid desktop use, avoid unrelated workloads, and never be the only place that knows something went wrong.

---

## 3. Hermes Scope

Hermes is a pager, not an agent.

Hermes may:

```text
- poll sentinel files
- check trainbox SSH reachability
- check heartbeat freshness
- check disk/GPU status using deterministic commands
- read small JSON/MD status files
- send Discord messages
- write hermes.jsonl
- optionally use Nemotron/NIM for compact message wording or hourly summaries
```

Hermes may not:

```text
- rewrite plans
- edit TODOs
- approve updates
- promote checkpoints
- repair corpus files
- decide campaign strategy
- mutate concept state
- run broad LLM analysis over repository context
- call Codex-like orchestration logic
```

Reason: Hermes injects too much operational context into its model session and becomes bad at actual orchestration. Codex is stronger when run inside the repo environment designed for it. Hermes should remain stupid, powerless, and reliable.

---

## 4. Existing Sentinel Contract

Use the existing canonical sentinel names:

```text
HUMAN_ATTENTION
BLOCKED
TRAINING_MACHINE_DOWN
API_CREDITS_EXHAUSTED
PROMOTION_REVIEW_REQUIRED
```

Sentinel files may live anywhere under:

```text
training/msm/
```

Preferred sentinel body:

```json
{
  "created_at": "2026-07-03T00:00:00+09:00",
  "source": "orchestrator|hermes|trainbox|deepseek",
  "session_id": "optional",
  "update_id": "optional",
  "reason": "short human-readable reason",
  "requested_action": "what Andi should fix or decide"
}
```

Plain text is acceptable during crashes.

Do not create new sentinel names unless the existing set becomes ambiguous. For Codex rate limiting, prefer `BLOCKED` with a clear JSON reason over adding `CODEX_RATE_LIMITED`.

---

## 5. Codex Rate-Limit Watch

### 5.1 Problem

Codex is the expensive reasoning layer. Even if each decision is short, a one-word-at-a-time 24/7 training loop can burn through allotment by accumulation.

The risk is not one 20-minute coding session. The risk is many tiny decisions every few minutes:

```text
Kleinvieh macht auch Mist.
```

The system needs a passive brake before Codex hits a hard wall.

### 5.2 Source of truth

Codex CLI `/status` shows the relevant interactive status, including model/session details and rate-limit information in the TUI. `/usage` can show daily, weekly, or cumulative account token activity. `/statusline` configures what `/status` displays; include useful fields such as model, context stats, rate limits, token counters, session id, directory, and version when available.

Important implementation note:

```text
/status, /usage, and /statusline are TUI slash commands, not normal shell commands.
Codex-the-agent should not be expected to execute /status and parse its own TUI output.
```

Therefore, the watchdog should observe Codex from outside, not ask Codex to self-inspect.

### 5.3 Passive observation via tmux

Run Codex in tmux:

```bash
tmux new -s codex 'cd ~/Ninereeds && codex'
```

Inside Codex, configure `/statusline` once so the visible `/status` display includes at least:

```text
- model or model+reasoning
- rate limits
- token counters
- context stats
- session id
- current directory/project root
```

Hermes/cron can then capture the visible pane without injecting commands into the Codex session:

```bash
tmux capture-pane -t codex -p -S -120 > ~/Ninereeds/training/msm/state/codex_pane_snapshot.txt
```

Avoid `tmux send-keys '/status' Enter` or `tmux send-keys '/statusline' Enter` as the default monitor path. It is too invasive because it injects control input into the live orchestrator UI.

### 5.4 Output files

The watchdog writes:

```text
training/msm/state/codex_pane_snapshot.txt
training/msm/state/codex_status.json
training/msm/state/codex_status.md
training/msm/state/codex_brake.json
```

`codex_status.json` is observational.

Example:

```json
{
  "updated_at": "2026-07-03T00:55:00+09:00",
  "source": "tmux capture-pane of Codex TUI",
  "parse_ok": true,
  "five_hour_percent_left": 10,
  "five_hour_resets": "05:36",
  "weekly_percent_left": 90,
  "weekly_resets": "15:24 on 8 Jul",
  "five_hour_percent_used": 90,
  "weekly_percent_used": 10,
  "highest_percent_used": 90,
  "last_hour_delta_used": 4,
  "projected_exhaustion": "safe|warning|danger|unknown"
}
```

`codex_brake.json` is normative. Codex must obey it before starting new work.

Example:

```json
{
  "updated_at": "2026-07-03T00:55:00+09:00",
  "source": "hermes_cron",
  "action": "pause_until_reset",
  "reason": "5h Codex usage reached 90% used",
  "reset_at": "2026-07-03T05:36:00+09:00",
  "five_hour_percent_left": 10,
  "weekly_percent_left": 90,
  "highest_percent_used": 90
}
```

Allowed `action` values:

```text
continue
conservative_mode
finish_current_only
pause_until_reset
blocked_unknown_reset
```

### 5.5 Threshold policy

Recommended thresholds:

```text
0-69% used:
  action = continue
  normal campaign mode

70-84% used:
  action = conservative_mode
  no optional probes, no code cleanup, no exploratory branches

85-89% used:
  action = finish_current_only
  finish current safe boundary, then pause or wait

>= 90% used:
  action = pause_until_reset
  do not launch new sessions or new Codex reasoning work

parse failure or reset unknown when high usage suspected:
  action = blocked_unknown_reset
  write BLOCKED sentinel
```

Use hysteresis:

```text
Enter pause at >= 90% used.
Resume only after reset time has passed and the next status parse confirms safe state.
Do not bounce between pause and continue repeatedly.
```

### 5.6 Codex standing rule

Add to `AGENTS.md` or the MSM runbook:

```text
Before starting any new MSM orchestration step, read:

  training/msm/state/codex_brake.json

If missing, continue but write a warning to orchestrator.jsonl.

If action == continue:
  proceed normally.

If action == conservative_mode:
  avoid optional probes, scans, cleanup, nonessential repo edits, and exploratory branches.

If action == finish_current_only:
  finish the current safe boundary, persist state, then stop or sleep.

If action == pause_until_reset:
  do not start a new session.
  do not call DeepSeek for new work.
  do not apply updates.
  write a pause note to training/msm/logs/orchestrator.jsonl.
  sleep until reset_at if running in an autonomous shell loop.
  after waking, re-read codex_brake.json.

If action == blocked_unknown_reset:
  write or preserve BLOCKED sentinel and stop.
```

### 5.7 Cron cadence

Use two layers:

```text
Every 1-5 minutes:
  deterministic watchdog checks trainbox, heartbeat, disk, GPU, sentinel files, Codex pane/status.
  no LLM call required.

Every 1 hour:
  optional Hermes/Nemotron digest to Discord.
```

A crash should not wait 59 minutes to be noticed. The hourly model call is for summaries, not urgent detection.

### 5.8 Example parser skeleton

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO="$HOME/Ninereeds"
STATE="$REPO/training/msm/state"
mkdir -p "$STATE"

SNAP="$STATE/codex_pane_snapshot.txt"
OUT_MD="$STATE/codex_status.md"
OUT_JSON="$STATE/codex_status.json"
BRAKE_JSON="$STATE/codex_brake.json"

tmux capture-pane -t codex -p -S -120 > "$SNAP"

python3 - "$SNAP" "$OUT_MD" "$OUT_JSON" "$BRAKE_JSON" <<'PY'
import sys, re, json, datetime
from pathlib import Path

snap, out_md, out_json, brake_json = map(Path, sys.argv[1:])
text = snap.read_text(errors="ignore")
now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

# Adapt patterns to actual Codex TUI output.
m5 = re.search(r"5h limit:\s*.*?(\d+)% left \(resets ([^)]+)\)", text)
mw = re.search(r"Weekly limit:\s*.*?(\d+)% left \(resets ([^)]+)\)", text)

five_left = int(m5.group(1)) if m5 else None
week_left = int(mw.group(1)) if mw else None
five_used = 100 - five_left if five_left is not None else None
week_used = 100 - week_left if week_left is not None else None
used_values = [v for v in (five_used, week_used) if v is not None]
highest = max(used_values) if used_values else None

if highest is None:
    action = "blocked_unknown_reset"
elif highest >= 90:
    action = "pause_until_reset"
elif highest >= 85:
    action = "finish_current_only"
elif highest >= 70:
    action = "conservative_mode"
else:
    action = "continue"

status = {
    "updated_at": now,
    "source": "tmux capture-pane of Codex TUI",
    "parse_ok": bool(m5 or mw),
    "five_hour_percent_left": five_left,
    "five_hour_resets": m5.group(2).strip() if m5 else None,
    "weekly_percent_left": week_left,
    "weekly_resets": mw.group(2).strip() if mw else None,
    "five_hour_percent_used": five_used,
    "weekly_percent_used": week_used,
    "highest_percent_used": highest,
}

brake = {
    "updated_at": now,
    "source": "hermes_cron",
    "action": action,
    "reason": "Codex usage threshold policy",
    "reset_at": None,
    "five_hour_percent_left": five_left,
    "weekly_percent_left": week_left,
    "highest_percent_used": highest,
}

out_json.write_text(json.dumps(status, indent=2) + "\n")
brake_json.write_text(json.dumps(brake, indent=2) + "\n")

out_md.write_text(
    "# Codex status\n\n"
    f"- Updated: {now}\n"
    f"- Parse OK: {status['parse_ok']}\n"
    f"- 5h limit: {five_left}% left, resets {status['five_hour_resets']}\n"
    f"- Weekly limit: {week_left}% left, resets {status['weekly_resets']}\n"
    f"- Highest used: {highest}%\n"
    f"- Brake action: {action}\n"
)
PY
```

---

## 6. Codex Usage Burn-Rate Reporting

Hermes should report not only absolute usage but also slope.

Desired Discord digest fields:

```text
Codex status:
  5h limit: 10% used / 90% left, resets 05:36
  weekly limit: 10% used / 90% left, resets Jul 8 15:24
  last hour: +4% used
  projected 5h exhaustion: safe
  projected weekly exhaustion: safe
  action: continue
```

Burn rate is what tells whether the pipeline is sustainable.

If the loop repeatedly approaches 90% too quickly, possible mitigations:

```text
- increase DeepSeek auto-advance authority within campaign policy
- batch more words per Codex campaign decision
- lower Codex wake frequency
- only wake Codex on boundary cases
- make report_card.json more compact and decision-ready
- prevent Codex from reading raw logs unless escalated
```

---

## 7. Escalation Ladder

The pipeline should flow without Codex until evidence calls for a decision.

### Level 0 — deterministic checks

Handled by shell/Python.

Examples:

```text
- script file exists
- raw_chat.jsonl exists
- report_card.json is valid JSON
- required schema fields exist
- trainbox SSH reachable
- nvidia-smi works
- disk has enough free space
- heartbeat is fresh
```

Failure handling:

```text
- retry deterministic operation if safe
- otherwise write BLOCKED or TRAINING_MACHINE_DOWN
- Hermes pages Andi
```

### Level 1 — DeepSeek auto-pass / auto-next

Handled by DeepSeek under a Codex-authored campaign policy.

Allowed when:

```text
- report_card.json validates
- primary campaign metrics pass
- no critical failure mode
- no protected-anchor failure
- no schema deviation
- no update/promotion decision needed
- retry count below limit
- campaign policy allows auto-advance
```

Action:

```text
- mark session as passed under current policy
- update auto_advance_state.json
- move to next cached word/card
- do not wake Codex
```

### Level 2 — DeepSeek local retry / repair

Handled by DeepSeek when failure is simple and anticipated by the campaign policy.

Allowed when:

```text
- failure type is known and policy has a retry recipe
- failure is limited to current word/card
- no protected anchor failed
- no update is being applied
- retry count is below limit
```

Action:

```text
- generate repair script
- run same word/card again
- write retry metadata
- escalate if repeated failure count reaches limit
```

### Level 3 — Codex decision

Codex wakes when judgment is required.

Escalate to Codex if:

```text
- primary campaign metrics fail beyond retry policy
- same failure repeats across N sessions
- failure mode is unexpected or contradictory
- protected anchor fails
- DeepSeek marks uncertainty or low confidence
- update candidate is ready
- promotion decision is required
- campaign queue is exhausted
- policy ambiguity occurs
- report/schema artifacts conflict
- raw logs appear suspicious
- Codex brake action permits decision but requires conservative handling
```

Codex may decide:

```text
- accept evidence
- continue auto-advance with updated policy
- retry same card
- repair replay
- run protected anchors
- run grounding eval
- run brain map
- approve/reject micro-update candidate
- alter campaign thresholds
- pause or escalate to user
```

### Level 4 — Hermes / user

Hermes pages Andi when the system cannot safely continue without manual action.

Examples:

```text
- training machine crashed or SSH unreachable
- GPU worker unavailable
- API credits exhausted
- Codex rate wall or unknown reset
- manual promotion review required
- filesystem/disk issue
- repo state conflict that Codex cannot safely resolve
```

Use existing sentinels.

---

## 8. Campaign Policy and Word Queue

Codex should decide the campaign policy once, then let DeepSeek auto-advance through a bounded queue.

### 8.1 Policy files

Recommended files:

```text
training/msm/state/active_campaign_policy.json
training/msm/state/word_queue.json
training/msm/state/auto_advance_state.json
```

### 8.2 `active_campaign_policy.json`

Example:

```json
{
  "campaign_id": "c18_topic_adherence_animals",
  "created_at": "2026-07-03T00:00:00+09:00",
  "author": "codex_orchestrator",
  "objective": "stay_on_topic",
  "auto_advance_allowed": true,
  "max_auto_advance_words": 20,
  "max_retries_per_word": 2,
  "checkpoint_policy": "no_micro_update_without_orchestrator",
  "primary_metrics": {
    "on_topic_rate_min": 0.85,
    "malformed_rate_max": 0.25,
    "repetition_collapse_max": 0.10,
    "empty_or_near_empty_max": 0.10
  },
  "secondary_metrics": {
    "language_correctness": "low_priority",
    "style_quality": "ignore_unless_unreadable"
  },
  "deepseek_allowed_actions": [
    "PASS_AUTONEXT",
    "PASS_BUT_BUFFER",
    "RETRY_SAME_WORD",
    "ESCALATE_CODEX",
    "ESCALATE_HUMAN"
  ],
  "escalate_if": [
    "off_topic_rate_above_threshold",
    "same_failure_repeats_3_sessions",
    "protected_anchor_failed",
    "critical_failure_mode",
    "malformed_rate_above_threshold",
    "deepseek_uncertain",
    "update_candidate_ready",
    "codex_brake_pause",
    "queue_exhausted"
  ]
}
```

### 8.3 `word_queue.json`

Example:

```json
{
  "campaign_id": "c18_topic_adherence_animals",
  "queue_created_at": "2026-07-03T00:00:00+09:00",
  "current_index": 0,
  "items": [
    {"word": "cat", "card_id": "cat_boundary_l1", "status": "pending"},
    {"word": "dog", "card_id": "dog_boundary_l1", "status": "pending"},
    {"word": "bird", "card_id": "bird_boundary_l1", "status": "pending"}
  ]
}
```

### 8.4 `auto_advance_state.json`

Example:

```json
{
  "campaign_id": "c18_topic_adherence_animals",
  "updated_at": "2026-07-03T00:10:00+09:00",
  "current_word": "cat",
  "current_card_id": "cat_boundary_l1",
  "last_session_id": "SESSION_ID",
  "last_action": "PASS_AUTONEXT",
  "auto_advanced_count": 3,
  "retry_counts": {
    "cat_boundary_l1": 0,
    "dog_boundary_l1": 1
  },
  "next_word": "bird",
  "requires_codex": false,
  "reason": "primary campaign metrics passed"
}
```

---

## 9. DeepSeek Auto-Advance Contract

DeepSeek may auto-advance only inside Codex-authored policy.

DeepSeek reads:

```text
training/msm/state/active_campaign_policy.json
training/msm/state/word_queue.json
training/msm/state/auto_advance_state.json
current session report_card.json
current turn_grades.jsonl if needed
```

DeepSeek writes:

```text
updated auto_advance_state.json
session decision note
next script.json for Gemma if auto-advancing or retrying
```

DeepSeek may output one of:

```text
PASS_AUTONEXT
PASS_BUT_BUFFER
RETRY_SAME_WORD
ESCALATE_CODEX
ESCALATE_HUMAN
```

### PASS_AUTONEXT

Use when:

```text
- primary campaign metrics pass
- no protected anchor failure
- no critical failure mode
- no update/promotion needed
```

Action:

```text
Move to next word/card.
Do not wake Codex.
```

### PASS_BUT_BUFFER

Use when:

```text
- output is acceptable under campaign objective
- useful correction/training examples exist
- no immediate update is requested
```

Action:

```text
Write proposed_training.jsonl if appropriate.
Do not approve training.
Do not apply update.
Continue or auto-next if policy allows.
```

### RETRY_SAME_WORD

Use when:

```text
- failure is local and repairable
- retry count is below policy limit
- policy defines the failure as retryable
```

Action:

```text
Generate bounded repair script.
Retry same word/card.
```

### ESCALATE_CODEX

Use when:

```text
- policy boundary reached
- repeated failure
- unexpected failure
- uncertainty
- update candidate is ready
- protected anchor issue
- queue exhausted
```

Action:

```text
Write a compact escalation summary.
Stop auto-advance.
Codex reads summary and decides.
```

### ESCALATE_HUMAN

Use when:

```text
- human approval/fix is required
- credentials/credits are needed
- machine status requires manual action
```

Action:

```text
Write appropriate sentinel.
Hermes pings Andi.
```

---

## 10. Codex Minimal-Read Decision Policy

Codex should not read broad context by default.

Read every decision:

```text
training/msm/state/codex_brake.json
training/msm/state/active_campaign_policy.json
training/msm/state/auto_advance_state.json
current report_card.json
relevant concept_state entry
last_decision.json
protected-anchor status
```

Do not read by default:

```text
raw_chat.jsonl
full report.md
old logs
entire TODO files
whole repository
large historical campaign logs
```

Read larger context only when:

```text
- report_card indicates contradiction
- malformed/repetition/off-topic rates exceed policy
- protected anchor fails
- update/promotion candidate exists
- DeepSeek escalates uncertainty
- schema artifacts conflict
- code repair is required
```

Routine clean passes should be handled by DeepSeek auto-advance, not Codex.

---

## 11. Update and Promotion Boundary

Keep this boundary strict:

```text
DeepSeek may propose training turns.
DeepSeek may not approve training turns.
DeepSeek may not promote checkpoints.
DeepSeek may not apply micro-updates unless explicitly delegated by Codex policy and existing gates allow it.
```

Codex/orchestrator remains final authority for:

```text
- copying accepted records into approved_training.jsonl
- writing update_manifest.json
- applying buffered micro-update backend
- accepting or rejecting update candidate
- promoting checkpoint
- updating current_chat_checkpoint.txt
```

The chat UI should only pull accepted/promoted checkpoints by default.

---

## 12. Checkpoint Sync to Main Chat Script

The main machine should pull checkpoints from the training machine, not rely on training-machine push.

Use immutable checkpoint names on the training machine and a pointer file:

```text
training/msm/state/current_chat_checkpoint.txt
```

Example content:

```text
core/c18_msm_cat_boundary_1430.pt
```

Main machine pull flow:

```text
1. read current_chat_checkpoint.txt over SSH
2. rsync checkpoint to local .tmp file
3. verify file exists and has plausible size
4. mv .tmp to final immutable local checkpoint
5. update chat/ninereeds.pt symlink atomically
```

Reason: the current chat script expects:

```text
chat/ninereeds.pt
```

Recommended local structure:

```text
~/Ninereeds/chat/ninereeds.pt -> checkpoints/CHECKPOINT_NAME.pt
~/Ninereeds/chat/checkpoints/CHECKPOINT_NAME.pt
```

Example pull script:

```bash
#!/usr/bin/env bash
set -euo pipefail

REMOTE="trainbox"
REMOTE_REPO="/home/aomukai/Ninereeds"
LOCAL_REPO="/home/aomukai/Ninereeds"

CKPT="$(ssh "$REMOTE" "cat '$REMOTE_REPO/training/msm/state/current_chat_checkpoint.txt'")"
BASENAME="$(basename "$CKPT")"
LOCAL_DIR="$LOCAL_REPO/chat/checkpoints"
LOCAL_FINAL="$LOCAL_DIR/$BASENAME"
LOCAL_TMP="$LOCAL_FINAL.tmp"
CHAT_LINK="$LOCAL_REPO/chat/ninereeds.pt"

mkdir -p "$LOCAL_DIR"

rsync -ah --progress --partial \
  "$REMOTE:$REMOTE_REPO/$CKPT" \
  "$LOCAL_TMP"

python3 - "$LOCAL_TMP" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1])
if not p.exists() or p.stat().st_size < 1024:
    raise SystemExit(f"bad checkpoint file: {p}")
print(f"checkpoint file exists: {p} ({p.stat().st_size:,} bytes)")
PY

mv -f "$LOCAL_TMP" "$LOCAL_FINAL"
ln -sfn "checkpoints/$BASENAME" "$CHAT_LINK"
```

---

## 13. Training Machine Health Watch

Training machine should write a heartbeat file every 30-60 seconds:

```text
training/msm/state/trainbox_heartbeat.json
```

Example:

```json
{
  "host": "trainbox",
  "time": "2026-07-03T00:00:00+09:00",
  "status": "alive",
  "gpu_visible": true,
  "current_session": "SESSION_ID",
  "gpu_temp_c": 62,
  "gpu_memory_used_mb": 8420,
  "gpu_memory_total_mb": 12288,
  "disk_free_gb": 320,
  "last_error": null
}
```

Hermes/main-machine watchdog checks:

```bash
ssh trainbox 'hostname && uptime'
ssh trainbox 'nvidia-smi --query-gpu=name,temperature.gpu,memory.used,memory.total,utilization.gpu --format=csv'
ssh trainbox 'df -h /'
ssh trainbox 'test -f ~/Ninereeds/training/msm/HUMAN_ATTENTION && echo HUMAN_ATTENTION || true'
```

If SSH fails or heartbeat is stale:

```text
write TRAINING_MACHINE_DOWN
Hermes pings Andi
avoid tight retry loop
```

---

## 14. Safe Autonomous Loop Shape

The autonomous loop should never be one giant unbounded Codex turn.

Preferred shape:

```text
1. watchdog updates codex_brake.json
2. Codex reads brake before a new orchestration boundary
3. Codex writes campaign policy or decision
4. DeepSeek/Gemma run bounded work
5. DeepSeek writes report artifacts
6. DeepSeek auto-advances if policy allows
7. Codex wakes only at boundary/escalation/update/policy exhaustion
8. all state persists to JSON/JSONL artifacts
```

If Codex is unavailable or rate-limited:

```text
- finish current safe boundary if already running
- do not launch new sessions
- do not apply updates
- preserve artifacts
- write BLOCKED if manual attention is needed
- Hermes reports status
```

The desired failure mode is:

```text
The lab pauses safely and resumes later.
```

Not:

```text
The lab keeps mutating state while the orchestrator is blind.
```

---

## 15. Implementation Checklist

### Rate-limit brake

```text
[ ] Run Codex inside tmux session named codex.
[ ] Configure /statusline with rate limits and token counters.
[x] Create scripts/watch_codex_status.py or .sh.
[x] Write codex_status.json/md.
[x] Write codex_brake.json.
[x] Add threshold/hysteresis policy.
[x] Add Codex standing rule to AGENTS.md/runbook.
[ ] Add Hermes digest of codex_status.md.
```

### Escalation ladder

```text
[x] Create active_campaign_policy.json schema.
[x] Create word_queue.json schema.
[x] Create auto_advance_state.json schema.
[x] Teach DeepSeek allowed outputs: PASS_AUTONEXT, PASS_BUT_BUFFER, RETRY_SAME_WORD, ESCALATE_CODEX, ESCALATE_HUMAN.
[x] Add retry limits.
[x] Add queue exhaustion escalation.
[x] Add protected-anchor and update-candidate hard stops.
```

### Hermes

```text
[ ] Implement deterministic sentinel scanner.
[ ] Implement trainbox heartbeat check.
[ ] Implement Discord webhook sender.
[ ] Make Hermes read status files only.
[ ] Keep Hermes powerless: no repo mutation, no planning, no update approval.
```

### Training machine

```text
[ ] Install Linux on dedicated ext4 SSD.
[ ] Enable SSH.
[ ] Disable sleep/suspend.
[ ] Configure BIOS restore-on-power-loss if available.
[ ] Install NVIDIA driver and verify nvidia-smi.
[ ] Clone Ninereeds.
[ ] Set up Gemma/llama.cpp/local worker.
[ ] Implement heartbeat writer.
```

### Checkpoint sync

```text
[ ] Write current_chat_checkpoint.txt only after checkpoint acceptance/promotion.
[ ] Implement main-machine pull script.
[ ] Use immutable checkpoint filenames.
[ ] Use atomic symlink update for chat/ninereeds.pt.
```

---

## 16. Non-Goals

This document does not define:

```text
- exact training math
- exact BDH architecture changes
- full update_artifact_schema.md replacement
- Discord bot UX beyond notification payloads
- final DeepSeek prompt wording
- final JSON schemas for validation
```

Those belong in implementation files once the pipeline scaffolding is built.

---

## 17. Core Rule Summary

```text
Codex is the campaign brain.
DeepSeek is the tactical worker.
Gemma is the mechanical runner.
Hermes is the pager.
Shell/Python is the watchdog.

Routine success should auto-advance.
Interesting evidence should escalate to Codex.
Unsafe states should page Andi.
Rate limits should pause the lab before they break it.
```

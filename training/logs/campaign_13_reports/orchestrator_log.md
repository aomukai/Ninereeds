# Campaign 13 Orchestrator Log

Started: 2026-05-30 22:29:17

## Design

Bridge vs no-bridge comparison for Phase A through E.
Regression: phase is deferred (pushed to end of queue).
Permanent failure: phase regresses when tried last in queue.

[2026-05-30 22:29:17] 
============================================================
  Phase A-only: evaluating E5 and picking winner
============================================================

## Phase A-only: evaluating E5 and picking winner

[2026-05-30 22:29:17] Waiting for E5 checkpoint ...
[2026-05-30 22:29:17] E5 found; eval + probe ...
[2026-05-30 22:30:56] E5: raw=0.904  shaped=0.900  loops=2
[2026-05-30 22:30:56] Phase A-only winner: E3 (shaped=0.914)
### Phase A-only epoch scores

| Epoch | Shaped |
|---|---|
| E1 | 0.906 |
| E2 | 0.903 |
| E3 | 0.914 ← winner |
| E4 | 0.907 |
| E5 | 0.900 |

[2026-05-30 22:30:56] 
============================================================
  Building corpora
============================================================

## Building corpora

[2026-05-30 22:30:56]   corpus exists: campaign_13_bridge.txt
[2026-05-30 22:30:56]   corpus exists: campaign_13_phase_B.txt
[2026-05-30 22:30:56]   corpus exists: campaign_13_phase_C.txt
[2026-05-30 22:30:56]   corpus exists: campaign_13_phase_D.txt
[2026-05-30 22:30:56]   corpus exists: campaign_13_phase_E.txt
[2026-05-30 22:30:56] 
============================================================
  Fresh → Bridge(1ep) → Phase A(3ep)
============================================================

## Fresh → Bridge(1ep) → Phase A(3ep)

[2026-05-30 22:30:56]   'c13_fresh_bridge': all checkpoints exist — skipping training, re-running eval
[2026-05-30 22:30:56]   eval e1 ...
[2026-05-30 22:31:39]   probe e1 ...
[2026-05-30 22:32:33]   E1: loss=3.8527  raw=0.697  shaped=0.703  loops=0
[2026-05-30 22:32:33]   best: E1 shaped=0.703
[2026-05-30 22:32:33] Bridge base shaped=0.703
[2026-05-30 22:32:33]   'c13_fresh_bridge_phaseA': all checkpoints exist — skipping training, re-running eval
[2026-05-30 22:32:33]   eval e1 ...
[2026-05-30 22:33:16]   probe e1 ...
[2026-05-30 22:34:11]   E1: loss=1.2726  raw=0.903  shaped=0.896  loops=3
[2026-05-30 22:34:11]   eval e2 ...
[2026-05-30 22:34:54]   probe e2 ...
[2026-05-30 22:35:49]   E2: loss=0.7102  raw=0.905  shaped=0.921  loops=2
[2026-05-30 22:35:49]   eval e3 ...
[2026-05-30 22:36:32]   probe e3 ...
[2026-05-30 22:37:28]   E3: loss=0.5828  raw=0.920  shaped=0.891  loops=2
[2026-05-30 22:37:28]   best: E2 shaped=0.921
[2026-05-30 22:37:28] 
============================================================
  Phase A final comparison
============================================================

## Phase A final comparison

| Variant | Best epoch | Shaped | Δ vs baseline | |
|---|---|---|---|---|
| Phase A-only | E3 | 0.914 | +0.914 |  |
| Bridge+Phase A | E2 | 0.921 | +0.921 | ✓ winner |

**Winner:** Bridge+Phase A  shaped=0.921  Δ=+0.921  `c13_fresh_bridge_phaseA_e2.pt`

[2026-05-30 22:37:28]   promoted → checkpoints/c13_phaseA_winner.pt
[2026-05-30 22:37:28] Phase A overall winner: Bridge+Phase A shaped=0.921
[2026-05-30 22:37:28] 
============================================================
  Phase B attempt 1 — direct (3ep)
============================================================

## Phase B attempt 1 — direct (3ep)

[2026-05-30 22:37:28]   'c13_Phase_B_direct': all checkpoints exist — skipping training, re-running eval
[2026-05-30 22:37:28]   eval e1 ...
[2026-05-30 22:38:11]   probe e1 ...
[2026-05-30 22:39:06]   E1: loss=0.7592  raw=0.897  shaped=0.910  loops=4
[2026-05-30 22:39:06]   eval e2 ...
[2026-05-30 22:39:49]   probe e2 ...
[2026-05-30 22:40:45]   E2: loss=0.6304  raw=0.903  shaped=0.915  loops=5
[2026-05-30 22:40:45]   eval e3 ...
[2026-05-30 22:41:28]   probe e3 ...
[2026-05-30 22:42:23]   E3: loss=0.5274  raw=0.917  shaped=0.905  loops=2
[2026-05-30 22:42:23]   best: E2 shaped=0.915
[2026-05-30 22:42:23] 
============================================================
  Phase B attempt 1 — bridge-pre (1ep bridge + 3ep phase)
============================================================

## Phase B attempt 1 — bridge-pre (1ep bridge + 3ep phase)

[2026-05-30 22:42:23]   'c13_Phase_B_bridge_pre': all checkpoints exist — skipping training, re-running eval
[2026-05-30 22:42:23]   eval e1 ...
[2026-05-30 22:43:06]   probe e1 ...
[2026-05-30 22:44:01]   E1: loss=1.122  raw=0.812  shaped=0.865  loops=0
[2026-05-30 22:44:01]   best: E1 shaped=0.865
[2026-05-30 22:44:01]   'c13_Phase_B_bridged': all checkpoints exist — skipping training, re-running eval
[2026-05-30 22:44:01]   eval e1 ...
[2026-05-30 22:44:44]   probe e1 ...
[2026-05-30 22:45:39]   E1: loss=0.7608  raw=0.903  shaped=0.900  loops=3
[2026-05-30 22:45:39]   eval e2 ...
[2026-05-30 22:46:22]   probe e2 ...
[2026-05-30 22:47:17]   E2: loss=0.631  raw=0.894  shaped=0.896  loops=3
[2026-05-30 22:47:17]   eval e3 ...
[2026-05-30 22:48:00]   probe e3 ...
[2026-05-30 22:48:56]   E3: loss=0.5277  raw=0.910  shaped=0.913  loops=3
[2026-05-30 22:48:56]   best: E3 shaped=0.913
[2026-05-30 22:48:56] 
============================================================
  Phase B attempt 1 — comparison
============================================================

## Phase B attempt 1 — comparison

| Variant | Best epoch | Shaped | Δ vs baseline | |
|---|---|---|---|---|
| Direct | E2 | 0.915 | -0.006 | ✓ winner |
| Bridge+Direct | E3 | 0.913 | -0.008 |  |

**REGRESSION** — best 0.915 < baseline 0.921. Phase deferred.

[2026-05-30 22:48:56] DEFERRED: Phase B (attempt 1) → end of queue.
[2026-05-30 22:48:56] 
============================================================
  Phase C attempt 1 — direct (3ep)
============================================================

## Phase C attempt 1 — direct (3ep)

[2026-05-30 22:48:56]   'c13_Phase_C_direct': all checkpoints exist — skipping training, re-running eval
[2026-05-30 22:48:56]   eval e1 ...
[2026-05-30 22:49:38]   probe e1 ...
[2026-05-30 22:50:33]   E1: loss=0.7626  raw=0.908  shaped=0.876  loops=2
[2026-05-30 22:50:33]   eval e2 ...
[2026-05-30 22:51:16]   probe e2 ...
[2026-05-30 22:52:12]   E2: loss=0.6329  raw=0.912  shaped=0.907  loops=4
[2026-05-30 22:52:12]   eval e3 ...
[2026-05-30 22:52:54]   probe e3 ...
[2026-05-30 22:53:50]   E3: loss=0.5356  raw=0.904  shaped=0.925  loops=2
[2026-05-30 22:53:50]   best: E3 shaped=0.925
[2026-05-30 22:53:50] 
============================================================
  Phase C attempt 1 — bridge-pre (1ep bridge + 3ep phase)
============================================================

## Phase C attempt 1 — bridge-pre (1ep bridge + 3ep phase)

[2026-05-30 22:53:50]   'c13_Phase_C_bridge_pre': all checkpoints exist — skipping training, re-running eval
[2026-05-30 22:53:50]   eval e1 ...
[2026-05-30 22:54:32]   probe e1 ...
[2026-05-30 22:55:28]   E1: loss=1.122  raw=0.812  shaped=0.865  loops=0
[2026-05-30 22:55:28]   best: E1 shaped=0.865
[2026-05-30 22:55:28]   'c13_Phase_C_bridged': all checkpoints exist — skipping training, re-running eval
[2026-05-30 22:55:28]   eval e1 ...
[2026-05-30 22:56:10]   probe e1 ...
[2026-05-30 22:57:05]   E1: loss=0.7635  raw=0.904  shaped=0.903  loops=4
[2026-05-30 22:57:05]   eval e2 ...
[2026-05-30 22:57:48]   probe e2 ...
[2026-05-30 22:59:05]   E2: loss=0.6335  raw=0.915  shaped=0.901  loops=5
[2026-05-30 22:59:05]   eval e3 ...
[2026-05-30 23:00:08]   probe e3 ...
[2026-05-30 23:01:30]   E3: loss=0.5361  raw=0.906  shaped=0.910  loops=8
[2026-05-30 23:01:30]   best: E3 shaped=0.910
[2026-05-30 23:01:30] 
============================================================
  Phase C attempt 1 — comparison
============================================================

## Phase C attempt 1 — comparison

| Variant | Best epoch | Shaped | Δ vs baseline | |
|---|---|---|---|---|
| Direct | E3 | 0.925 | +0.004 | ✓ winner |
| Bridge+Direct | E3 | 0.910 | -0.011 |  |

**Winner:** Direct  shaped=0.925  Δ=+0.004  `c13_Phase_C_direct_e3.pt`

[2026-05-30 23:01:30]   promoted → checkpoints/c13_Phase_C_winner.pt
[2026-05-30 23:01:30] SUCCESS: Phase C — new baseline shaped=0.925
[2026-05-30 23:01:30] 
============================================================
  Phase D attempt 1 — direct (3ep)
============================================================

## Phase D attempt 1 — direct (3ep)

[2026-05-30 23:01:30]   'c13_Phase_D_direct': all checkpoints exist — skipping training, re-running eval
[2026-05-30 23:01:30]   eval e1 ...
[2026-05-30 23:02:33]   probe e1 ...
[2026-05-30 23:04:00]   E1: loss=0.6617  raw=0.900  shaped=0.904  loops=3
[2026-05-30 23:04:00]   eval e2 ...
[2026-05-30 23:05:08]   probe e2 ...
[2026-05-30 23:06:36]   E2: loss=0.555  raw=0.905  shaped=0.912  loops=0
[2026-05-30 23:06:36]   eval e3 ...
[2026-05-30 23:07:44]   probe e3 ...
[2026-05-30 23:09:11]   E3: loss=0.4562  raw=0.925  shaped=0.920  loops=4
[2026-05-30 23:09:11]   best: E3 shaped=0.920
[2026-05-30 23:09:11] 
============================================================
  Phase D attempt 1 — bridge-pre (1ep bridge + 3ep phase)
============================================================

## Phase D attempt 1 — bridge-pre (1ep bridge + 3ep phase)

[2026-05-30 23:09:11]   'c13_Phase_D_bridge_pre': all checkpoints exist — skipping training, re-running eval
[2026-05-30 23:09:11]   eval e1 ...
[2026-05-30 23:10:19]   probe e1 ...
[2026-05-30 23:11:47]   E1: loss=1.0236  raw=0.772  shaped=0.787  loops=0
[2026-05-30 23:11:47]   best: E1 shaped=0.787
[2026-05-30 23:11:47]   'c13_Phase_D_bridged': all checkpoints exist — skipping training, re-running eval
[2026-05-30 23:11:47]   eval e1 ...
[2026-05-30 23:12:56]   probe e1 ...
[2026-05-30 23:14:25]   E1: loss=0.6629  raw=0.905  shaped=0.893  loops=3
[2026-05-30 23:14:25]   eval e2 ...
[2026-05-30 23:15:32]   probe e2 ...
[2026-05-30 23:17:00]   E2: loss=0.5553  raw=0.916  shaped=0.910  loops=2
[2026-05-30 23:17:00]   eval e3 ...
[2026-05-30 23:18:09]   probe e3 ...
[2026-05-30 23:19:36]   E3: loss=0.4564  raw=0.916  shaped=0.912  loops=2
[2026-05-30 23:19:36]   best: E3 shaped=0.912
[2026-05-30 23:19:36] 
============================================================
  Phase D attempt 1 — comparison
============================================================

## Phase D attempt 1 — comparison

| Variant | Best epoch | Shaped | Δ vs baseline | |
|---|---|---|---|---|
| Direct | E3 | 0.920 | -0.005 | ✓ winner |
| Bridge+Direct | E3 | 0.912 | -0.013 |  |

**REGRESSION** — best 0.920 < baseline 0.925. Phase deferred.

[2026-05-30 23:19:36] DEFERRED: Phase D (attempt 1) → end of queue.
[2026-05-30 23:19:36] 
============================================================
  Phase E attempt 1 — direct (3ep)
============================================================

## Phase E attempt 1 — direct (3ep)

[2026-05-30 23:19:36]   'c13_Phase_E_direct': all checkpoints exist — skipping training, re-running eval
[2026-05-30 23:19:36]   eval e1 ...
[2026-05-30 23:20:44]   probe e1 ...
[2026-05-30 23:22:12]   E1: loss=0.6742  raw=0.903  shaped=0.912  loops=3
[2026-05-30 23:22:12]   eval e2 ...
[2026-05-30 23:23:20]   probe e2 ...
[2026-05-30 23:24:48]   E2: loss=0.5647  raw=0.920  shaped=0.914  loops=4
[2026-05-30 23:24:48]   eval e3 ...
[2026-05-30 23:25:55]   probe e3 ...
[2026-05-30 23:27:23]   E3: loss=0.4649  raw=0.916  shaped=0.921  loops=4
[2026-05-30 23:27:23]   best: E3 shaped=0.921
[2026-05-30 23:27:23] 
============================================================
  Phase E attempt 1 — bridge-pre (1ep bridge + 3ep phase)
============================================================

## Phase E attempt 1 — bridge-pre (1ep bridge + 3ep phase)

[2026-05-30 23:27:23]   'c13_Phase_E_bridge_pre': all checkpoints exist — skipping training, re-running eval
[2026-05-30 23:27:23]   eval e1 ...
[2026-05-30 23:28:30]   probe e1 ...
[2026-05-30 23:29:59]   E1: loss=1.0236  raw=0.772  shaped=0.787  loops=0
[2026-05-30 23:29:59]   best: E1 shaped=0.787
[2026-05-30 23:29:59]   'c13_Phase_E_bridged': all checkpoints exist — skipping training, re-running eval
[2026-05-30 23:29:59]   eval e1 ...
[2026-05-30 23:31:06]   probe e1 ...
[2026-05-30 23:32:34]   E1: loss=0.6759  raw=0.898  shaped=0.896  loops=2
[2026-05-30 23:32:34]   eval e2 ...
[2026-05-30 23:33:42]   probe e2 ...
[2026-05-30 23:35:10]   E2: loss=0.5653  raw=0.911  shaped=0.899  loops=3
[2026-05-30 23:35:10]   eval e3 ...
[2026-05-30 23:36:15]   probe e3 ...
[2026-05-30 23:37:41]   E3: loss=0.4653  raw=0.904  shaped=0.913  loops=0
[2026-05-30 23:37:41]   best: E3 shaped=0.913
[2026-05-30 23:37:41] 
============================================================
  Phase E attempt 1 — comparison
============================================================

## Phase E attempt 1 — comparison

| Variant | Best epoch | Shaped | Δ vs baseline | |
|---|---|---|---|---|
| Direct | E3 | 0.921 | -0.004 | ✓ winner |
| Bridge+Direct | E3 | 0.913 | -0.012 |  |

**REGRESSION** — best 0.921 < baseline 0.925. Phase deferred.

[2026-05-30 23:37:41] DEFERRED: Phase E (attempt 1) → end of queue.
[2026-05-30 23:37:41] 
============================================================
  Phase B attempt 2 — direct (3ep)
============================================================

## Phase B attempt 2 — direct (3ep)

[2026-05-30 23:37:41]   'c13_Phase_B_direct_retry2': all checkpoints exist — skipping training, re-running eval
[2026-05-30 23:37:41]   eval e1 ...
[2026-05-30 23:38:48]   probe e1 ...
[2026-05-30 23:40:15]   E1: loss=0.6941  raw=0.899  shaped=0.910  loops=2
[2026-05-30 23:40:15]   eval e2 ...
[2026-05-30 23:41:22]   probe e2 ...
[2026-05-30 23:42:47]   E2: loss=0.5879  raw=0.893  shaped=0.906  loops=2
[2026-05-30 23:42:47]   eval e3 ...
[2026-05-30 23:43:54]   probe e3 ...
[2026-05-30 23:45:21]   E3: loss=0.4868  raw=0.899  shaped=0.899  loops=2
[2026-05-30 23:45:21]   best: E1 shaped=0.910
[2026-05-30 23:45:21] 
============================================================
  Phase B attempt 2 — bridge-pre (1ep bridge + 3ep phase)
============================================================

## Phase B attempt 2 — bridge-pre (1ep bridge + 3ep phase)

[2026-05-30 23:45:21]   'c13_Phase_B_bridge_pre_retry2': all checkpoints exist — skipping training, re-running eval
[2026-05-30 23:45:21]   eval e1 ...
[2026-05-30 23:46:28]   probe e1 ...
[2026-05-30 23:47:55]   E1: loss=1.0236  raw=0.772  shaped=0.787  loops=0
[2026-05-30 23:47:55]   best: E1 shaped=0.787
[2026-05-30 23:47:55]   'c13_Phase_B_bridged_retry2': all checkpoints exist — skipping training, re-running eval
[2026-05-30 23:47:55]   eval e1 ...
[2026-05-30 23:49:01]   probe e1 ...
[2026-05-30 23:50:28]   E1: loss=0.6952  raw=0.901  shaped=0.899  loops=3
[2026-05-30 23:50:28]   eval e2 ...
[2026-05-30 23:51:35]   probe e2 ...
[2026-05-30 23:53:01]   E2: loss=0.5887  raw=0.890  shaped=0.908  loops=6
[2026-05-30 23:53:01]   eval e3 ...
[2026-05-30 23:54:07]   probe e3 ...
[2026-05-30 23:55:34]   E3: loss=0.4877  raw=0.914  shaped=0.921  loops=3
[2026-05-30 23:55:34]   best: E3 shaped=0.921
[2026-05-30 23:55:34] 
============================================================
  Phase B attempt 2 — comparison
============================================================

## Phase B attempt 2 — comparison

| Variant | Best epoch | Shaped | Δ vs baseline | |
|---|---|---|---|---|
| Direct | E1 | 0.910 | -0.015 |  |
| Bridge+Direct | E3 | 0.921 | -0.004 | ✓ winner |

**REGRESSION** — best 0.921 < baseline 0.925. Phase deferred.

[2026-05-30 23:55:34] DEFERRED: Phase B (attempt 2) → end of queue.
[2026-05-30 23:55:34] 
============================================================
  Phase D attempt 2 — direct (3ep)
============================================================

## Phase D attempt 2 — direct (3ep)

[2026-05-30 23:55:34]   'c13_Phase_D_direct_retry2': all checkpoints exist — skipping training, re-running eval
[2026-05-30 23:55:34]   eval e1 ...
[2026-05-30 23:56:39]   probe e1 ...
[2026-05-30 23:58:06]   E1: loss=0.7047  raw=0.890  shaped=0.901  loops=7
[2026-05-30 23:58:06]   eval e2 ...
[2026-05-30 23:59:13]   probe e2 ...
[2026-05-31 00:00:39]   E2: loss=0.5903  raw=0.899  shaped=0.911  loops=6
[2026-05-31 00:00:39]   eval e3 ...
[2026-05-31 00:01:45]   probe e3 ...
[2026-05-31 00:03:11]   E3: loss=0.4805  raw=0.906  shaped=0.908  loops=2
[2026-05-31 00:03:11]   best: E2 shaped=0.911
[2026-05-31 00:03:11] 
============================================================
  Phase D attempt 2 — bridge-pre (1ep bridge + 3ep phase)
============================================================

## Phase D attempt 2 — bridge-pre (1ep bridge + 3ep phase)

[2026-05-31 00:03:11]   'c13_Phase_D_bridge_pre_retry2': all checkpoints exist — skipping training, re-running eval
[2026-05-31 00:03:11]   eval e1 ...
[2026-05-31 00:04:17]   probe e1 ...
[2026-05-31 00:05:44]   E1: loss=0.7579  raw=0.809  shaped=0.804  loops=1
[2026-05-31 00:05:44]   best: E1 shaped=0.804
[2026-05-31 00:05:44]   'c13_Phase_D_bridged_retry2': all checkpoints exist — skipping training, re-running eval
[2026-05-31 00:05:44]   eval e1 ...
[2026-05-31 00:06:51]   probe e1 ...
[2026-05-31 00:08:18]   E1: loss=0.7061  raw=0.884  shaped=0.895  loops=3
[2026-05-31 00:08:18]   eval e2 ...
[2026-05-31 00:09:26]   probe e2 ...
[2026-05-31 00:10:53]   E2: loss=0.5906  raw=0.889  shaped=0.905  loops=9
[2026-05-31 00:10:53]   eval e3 ...
[2026-05-31 00:11:58]   probe e3 ...
[2026-05-31 00:13:26]   E3: loss=0.4808  raw=0.905  shaped=0.907  loops=5
[2026-05-31 00:13:26]   best: E3 shaped=0.907
[2026-05-31 00:13:26] 
============================================================
  Phase D attempt 2 — comparison
============================================================

## Phase D attempt 2 — comparison

| Variant | Best epoch | Shaped | Δ vs baseline | |
|---|---|---|---|---|
| Direct | E2 | 0.911 | -0.014 | ✓ winner |
| Bridge+Direct | E3 | 0.907 | -0.018 |  |

**REGRESSION** — best 0.911 < baseline 0.925. Phase deferred.

[2026-05-31 00:13:26] DEFERRED: Phase D (attempt 2) → end of queue.
[2026-05-31 00:13:26] 
============================================================
  Phase E attempt 2 — direct (3ep)
============================================================

## Phase E attempt 2 — direct (3ep)

[2026-05-31 00:13:26]   'c13_Phase_E_direct_retry2': all checkpoints exist — skipping training, re-running eval
[2026-05-31 00:13:26]   eval e1 ...
[2026-05-31 00:14:33]   probe e1 ...
[2026-05-31 00:16:01]   E1: loss=0.7154  raw=0.892  shaped=0.892  loops=3
[2026-05-31 00:16:01]   eval e2 ...
[2026-05-31 00:17:08]   probe e2 ...
[2026-05-31 00:18:34]   E2: loss=0.5998  raw=0.919  shaped=0.898  loops=2
[2026-05-31 00:18:34]   eval e3 ...
[2026-05-31 00:19:40]   probe e3 ...
[2026-05-31 00:21:07]   E3: loss=0.4886  raw=0.900  shaped=0.899  loops=5
[2026-05-31 00:21:07]   best: E3 shaped=0.899
[2026-05-31 00:21:07] 
============================================================
  Phase E attempt 2 — bridge-pre (1ep bridge + 3ep phase)
============================================================

## Phase E attempt 2 — bridge-pre (1ep bridge + 3ep phase)

[2026-05-31 00:21:07]   'c13_Phase_E_bridge_pre_retry2': all checkpoints exist — skipping training, re-running eval
[2026-05-31 00:21:07]   eval e1 ...
[2026-05-31 00:22:13]   probe e1 ...
[2026-05-31 00:23:38]   E1: loss=0.7579  raw=0.809  shaped=0.804  loops=1
[2026-05-31 00:23:38]   best: E1 shaped=0.804
[2026-05-31 00:23:38]   'c13_Phase_E_bridged_retry2': all checkpoints exist — skipping training, re-running eval
[2026-05-31 00:23:38]   eval e1 ...
[2026-05-31 00:24:43]   probe e1 ...
[2026-05-31 00:26:10]   E1: loss=0.7171  raw=0.892  shaped=0.905  loops=5
[2026-05-31 00:26:10]   eval e2 ...
[2026-05-31 00:27:17]   probe e2 ...
[2026-05-31 00:28:43]   E2: loss=0.6005  raw=0.909  shaped=0.912  loops=2
[2026-05-31 00:28:43]   eval e3 ...
[2026-05-31 00:29:50]   probe e3 ...
[2026-05-31 00:31:17]   E3: loss=0.4895  raw=0.923  shaped=0.891  loops=2
[2026-05-31 00:31:17]   best: E2 shaped=0.912
[2026-05-31 00:31:17] 
============================================================
  Phase E attempt 2 — comparison
============================================================

## Phase E attempt 2 — comparison

| Variant | Best epoch | Shaped | Δ vs baseline | |
|---|---|---|---|---|
| Direct | E3 | 0.899 | -0.026 |  |
| Bridge+Direct | E2 | 0.912 | -0.013 | ✓ winner |

**REGRESSION** — best 0.912 < baseline 0.925. Phase deferred.

[2026-05-31 00:31:17] DEFERRED: Phase E (attempt 2) → end of queue.
[2026-05-31 00:31:17] 
============================================================
  Phase B attempt 3 — direct (3ep)
============================================================

## Phase B attempt 3 — direct (3ep)

[2026-05-31 00:31:17]   'c13_Phase_B_direct_retry3': all checkpoints exist — skipping training, re-running eval
[2026-05-31 00:31:17]   eval e1 ...
[2026-05-31 00:32:24]   probe e1 ...
[2026-05-31 00:33:51]   E1: loss=0.738  raw=0.903  shaped=0.917  loops=1
[2026-05-31 00:33:51]   eval e2 ...
[2026-05-31 00:34:59]   probe e2 ...
[2026-05-31 00:36:28]   E2: loss=0.6257  raw=0.895  shaped=0.912  loops=2
[2026-05-31 00:36:28]   eval e3 ...
[2026-05-31 00:37:35]   probe e3 ...
[2026-05-31 00:39:02]   E3: loss=0.5133  raw=0.902  shaped=0.908  loops=5
[2026-05-31 00:39:02]   best: E1 shaped=0.917
[2026-05-31 00:39:02] 
============================================================
  Phase B attempt 3 — bridge-pre (1ep bridge + 3ep phase)
============================================================

## Phase B attempt 3 — bridge-pre (1ep bridge + 3ep phase)

[2026-05-31 00:39:02]   'c13_Phase_B_bridge_pre_retry3': all checkpoints exist — skipping training, re-running eval
[2026-05-31 00:39:02]   eval e1 ...
[2026-05-31 00:40:09]   probe e1 ...
[2026-05-31 00:41:39]   E1: loss=0.7579  raw=0.809  shaped=0.804  loops=1
[2026-05-31 00:41:39]   best: E1 shaped=0.804
[2026-05-31 00:41:39]   'c13_Phase_B_bridged_retry3': all checkpoints exist — skipping training, re-running eval
[2026-05-31 00:41:39]   eval e1 ...
[2026-05-31 00:42:46]   probe e1 ...
[2026-05-31 00:44:13]   E1: loss=0.7395  raw=0.898  shaped=0.907  loops=6
[2026-05-31 00:44:13]   eval e2 ...
[2026-05-31 00:45:21]   probe e2 ...
[2026-05-31 00:46:49]   E2: loss=0.6257  raw=0.900  shaped=0.900  loops=3
[2026-05-31 00:46:49]   eval e3 ...
[2026-05-31 00:47:56]   probe e3 ...
[2026-05-31 00:49:24]   E3: loss=0.5132  raw=0.908  shaped=0.914  loops=4
[2026-05-31 00:49:24]   best: E3 shaped=0.914
[2026-05-31 00:49:24] 
============================================================
  Phase B attempt 3 — comparison
============================================================

## Phase B attempt 3 — comparison

| Variant | Best epoch | Shaped | Δ vs baseline | |
|---|---|---|---|---|
| Direct | E1 | 0.917 | -0.008 | ✓ winner |
| Bridge+Direct | E3 | 0.914 | -0.011 |  |

**REGRESSION** — best 0.917 < baseline 0.925. Phase deferred.

[2026-05-31 00:49:24] DEFERRED: Phase B (attempt 3) → end of queue.
[2026-05-31 00:49:24] 
============================================================
  Phase D attempt 3 — direct (3ep)
============================================================

## Phase D attempt 3 — direct (3ep)

[2026-05-31 00:49:24]   'c13_Phase_D_direct_retry3': all checkpoints exist — skipping training, re-running eval
[2026-05-31 00:49:24]   eval e1 ...
[2026-05-31 00:50:31]   probe e1 ...
[2026-05-31 00:51:58]   E1: loss=0.7047  raw=0.890  shaped=0.901  loops=7
[2026-05-31 00:51:58]   eval e2 ...
[2026-05-31 00:53:05]   probe e2 ...
[2026-05-31 00:54:33]   E2: loss=0.5903  raw=0.899  shaped=0.911  loops=6
[2026-05-31 00:54:33]   eval e3 ...
[2026-05-31 00:55:41]   probe e3 ...
[2026-05-31 00:57:10]   E3: loss=0.4805  raw=0.906  shaped=0.908  loops=2
[2026-05-31 00:57:10]   best: E2 shaped=0.911
[2026-05-31 00:57:10] 
============================================================
  Phase D attempt 3 — bridge-pre (1ep bridge + 3ep phase)
============================================================

## Phase D attempt 3 — bridge-pre (1ep bridge + 3ep phase)

[2026-05-31 00:57:10]   'c13_Phase_D_bridge_pre_retry3': all checkpoints exist — skipping training, re-running eval
[2026-05-31 00:57:10]   eval e1 ...
[2026-05-31 00:58:17]   probe e1 ...
[2026-05-31 00:59:45]   E1: loss=0.7579  raw=0.809  shaped=0.804  loops=1
[2026-05-31 00:59:45]   best: E1 shaped=0.804
[2026-05-31 00:59:45]   'c13_Phase_D_bridged_retry3': all checkpoints exist — skipping training, re-running eval
[2026-05-31 00:59:45]   eval e1 ...
[2026-05-31 01:00:52]   probe e1 ...
[2026-05-31 01:02:19]   E1: loss=0.7061  raw=0.884  shaped=0.895  loops=3
[2026-05-31 01:02:19]   eval e2 ...
[2026-05-31 01:03:25]   probe e2 ...
[2026-05-31 01:04:52]   E2: loss=0.5906  raw=0.889  shaped=0.905  loops=9
[2026-05-31 01:04:52]   eval e3 ...
[2026-05-31 01:05:58]   probe e3 ...
[2026-05-31 01:07:26]   E3: loss=0.4808  raw=0.905  shaped=0.907  loops=5
[2026-05-31 01:07:26]   best: E3 shaped=0.907
[2026-05-31 01:07:26] 
============================================================
  Phase D attempt 3 — comparison
============================================================

## Phase D attempt 3 — comparison

| Variant | Best epoch | Shaped | Δ vs baseline | |
|---|---|---|---|---|
| Direct | E2 | 0.911 | -0.014 | ✓ winner |
| Bridge+Direct | E3 | 0.907 | -0.018 |  |

**REGRESSION** — best 0.911 < baseline 0.925. Phase deferred.

[2026-05-31 01:07:26] DEFERRED: Phase D (attempt 3) → end of queue.
[2026-05-31 01:07:26] 
============================================================
  Phase E attempt 3 — direct (3ep)
============================================================

## Phase E attempt 3 — direct (3ep)

[2026-05-31 01:07:26]   train 'c13_Phase_E_direct_retry3' (3 ep, batch=4, resume=c13_Phase_C_direct_e3.pt)
[2026-05-31 01:56:48]   eval e1 ...
[2026-05-31 01:57:55]   probe e1 ...
[2026-05-31 01:59:24]   E1: loss=0.7154  raw=0.892  shaped=0.892  loops=3
[2026-05-31 01:59:24]   eval e2 ...
[2026-05-31 02:00:33]   probe e2 ...
[2026-05-31 02:02:01]   E2: loss=0.5998  raw=0.919  shaped=0.898  loops=2
[2026-05-31 02:02:01]   eval e3 ...
[2026-05-31 02:03:08]   probe e3 ...
[2026-05-31 02:04:38]   E3: loss=0.4886  raw=0.900  shaped=0.899  loops=5
[2026-05-31 02:04:38]   best: E3 shaped=0.899
[2026-05-31 02:04:38] 
============================================================
  Phase E attempt 3 — bridge-pre (1ep bridge + 3ep phase)
============================================================

## Phase E attempt 3 — bridge-pre (1ep bridge + 3ep phase)

[2026-05-31 02:04:38]   train 'c13_Phase_E_bridge_pre_retry3' (1 ep, batch=4, resume=c13_Phase_C_direct_e3.pt)
[2026-05-31 02:04:43]   OOM at batch=4; retrying batch=2
[2026-05-31 02:04:43]   train 'c13_Phase_E_bridge_pre_retry3' (1 ep, batch=2, resume=c13_Phase_C_direct_e3.pt)
[2026-05-31 02:05:09]   eval e1 ...
[2026-05-31 02:06:17]   probe e1 ...
[2026-05-31 02:07:46]   E1: loss=0.6  raw=0.801  shaped=0.804  loops=1
[2026-05-31 02:07:46]   best: E1 shaped=0.804
[2026-05-31 02:07:46]   train 'c13_Phase_E_bridged_retry3' (3 ep, batch=4, resume=c13_Phase_E_bridge_pre_retry3_e1.pt)
[2026-05-31 02:07:51]   OOM at batch=4; retrying batch=2
[2026-05-31 02:07:51]   train 'c13_Phase_E_bridged_retry3' (3 ep, batch=2, resume=c13_Phase_E_bridge_pre_retry3_e1.pt)
[2026-05-31 03:02:53]   eval e1 ...
[2026-05-31 03:03:59]   probe e1 ...
[2026-05-31 03:05:28]   E1: loss=0.7785  raw=0.871  shaped=0.873  loops=5
[2026-05-31 03:05:28]   eval e2 ...
[2026-05-31 03:06:38]   probe e2 ...
[2026-05-31 03:08:08]   E2: loss=0.6475  raw=0.882  shaped=0.908  loops=2
[2026-05-31 03:08:08]   eval e3 ...
[2026-05-31 03:09:17]   probe e3 ...
[2026-05-31 03:10:44]   E3: loss=0.5248  raw=0.927  shaped=0.915  loops=3
[2026-05-31 03:10:44]   best: E3 shaped=0.915
[2026-05-31 03:10:44] 
============================================================
  Phase E attempt 3 — comparison
============================================================

## Phase E attempt 3 — comparison

| Variant | Best epoch | Shaped | Δ vs baseline | |
|---|---|---|---|---|
| Direct | E3 | 0.899 | -0.026 |  |
| Bridge+Direct | E3 | 0.915 | -0.010 | ✓ winner |

**REGRESSION** — best 0.915 < baseline 0.925. Phase deferred.

[2026-05-31 03:10:44] DEFERRED: Phase E (attempt 3) → end of queue.
[2026-05-31 03:10:44] 
============================================================
  Phase B attempt 4 — direct (3ep)
============================================================

## Phase B attempt 4 — direct (3ep)

[2026-05-31 03:10:44]   train 'c13_Phase_B_direct_retry4' (3 ep, batch=4, resume=c13_Phase_C_direct_e3.pt)
[2026-05-31 03:10:48]   OOM at batch=4; retrying batch=2
[2026-05-31 03:10:48]   train 'c13_Phase_B_direct_retry4' (3 ep, batch=2, resume=c13_Phase_C_direct_e3.pt)
[2026-05-31 04:27:47]   eval e1 ...
[2026-05-31 04:28:55]   probe e1 ...
[2026-05-31 04:30:23]   E1: loss=0.8004  raw=0.882  shaped=0.898  loops=4
[2026-05-31 04:30:23]   eval e2 ...
[2026-05-31 04:31:30]   probe e2 ...
[2026-05-31 04:32:58]   E2: loss=0.6748  raw=0.893  shaped=0.897  loops=2
[2026-05-31 04:32:58]   eval e3 ...
[2026-05-31 04:34:05]   probe e3 ...
[2026-05-31 04:35:32]   E3: loss=0.5503  raw=0.898  shaped=0.905  loops=3
[2026-05-31 04:35:32]   best: E3 shaped=0.905
[2026-05-31 04:35:32] 
============================================================
  Phase B attempt 4 — bridge-pre (1ep bridge + 3ep phase)
============================================================

## Phase B attempt 4 — bridge-pre (1ep bridge + 3ep phase)

[2026-05-31 04:35:32]   train 'c13_Phase_B_bridge_pre_retry4' (1 ep, batch=4, resume=c13_Phase_C_direct_e3.pt)
[2026-05-31 04:35:37]   OOM at batch=4; retrying batch=2
[2026-05-31 04:35:37]   train 'c13_Phase_B_bridge_pre_retry4' (1 ep, batch=2, resume=c13_Phase_C_direct_e3.pt)
[2026-05-31 04:36:03]   eval e1 ...
[2026-05-31 04:37:11]   probe e1 ...
[2026-05-31 04:38:39]   E1: loss=0.6  raw=0.801  shaped=0.804  loops=1
[2026-05-31 04:38:39]   best: E1 shaped=0.804
[2026-05-31 04:38:39]   train 'c13_Phase_B_bridged_retry4' (3 ep, batch=4, resume=c13_Phase_B_bridge_pre_retry4_e1.pt)
[2026-05-31 04:38:43]   OOM at batch=4; retrying batch=2
[2026-05-31 04:38:43]   train 'c13_Phase_B_bridged_retry4' (3 ep, batch=2, resume=c13_Phase_B_bridge_pre_retry4_e1.pt)
[2026-05-31 05:31:22]   eval e1 ...
[2026-05-31 05:32:04]   probe e1 ...
[2026-05-31 05:32:59]   E1: loss=0.8025  raw=0.892  shaped=0.909  loops=3
[2026-05-31 05:32:59]   eval e2 ...
[2026-05-31 05:33:41]   probe e2 ...
[2026-05-31 05:34:36]   E2: loss=0.6748  raw=0.908  shaped=0.898  loops=3
[2026-05-31 05:34:36]   eval e3 ...
[2026-05-31 05:35:18]   probe e3 ...
[2026-05-31 05:36:13]   E3: loss=0.5504  raw=0.907  shaped=0.907  loops=6
[2026-05-31 05:36:13]   best: E1 shaped=0.909
[2026-05-31 05:36:13] 
============================================================
  Phase B attempt 4 — comparison
============================================================

## Phase B attempt 4 — comparison

| Variant | Best epoch | Shaped | Δ vs baseline | |
|---|---|---|---|---|
| Direct | E3 | 0.905 | -0.020 |  |
| Bridge+Direct | E1 | 0.909 | -0.016 | ✓ winner |

**REGRESSION** — best 0.909 < baseline 0.925. Phase deferred.

[2026-05-31 05:36:13] PERMANENT FAILURE: Phase B after 4 attempts.
[2026-05-31 05:36:13] 
============================================================
  Phase D attempt 4 — direct (3ep)
============================================================

## Phase D attempt 4 — direct (3ep)

[2026-05-31 05:36:13]   train 'c13_Phase_D_direct_retry4' (3 ep, batch=4, resume=c13_Phase_C_direct_e3.pt)
[2026-05-31 06:10:55]   eval e1 ...
[2026-05-31 06:11:37]   probe e1 ...
[2026-05-31 06:12:32]   E1: loss=0.7047  raw=0.890  shaped=0.901  loops=7
[2026-05-31 06:12:32]   eval e2 ...
[2026-05-31 06:13:14]   probe e2 ...
[2026-05-31 06:14:09]   E2: loss=0.5903  raw=0.899  shaped=0.911  loops=6
[2026-05-31 06:14:09]   eval e3 ...
[2026-05-31 06:14:51]   probe e3 ...
[2026-05-31 06:15:46]   E3: loss=0.4805  raw=0.906  shaped=0.908  loops=2
[2026-05-31 06:15:46]   best: E2 shaped=0.911
[2026-05-31 06:15:46] 
============================================================
  Phase D attempt 4 — bridge-pre (1ep bridge + 3ep phase)
============================================================

## Phase D attempt 4 — bridge-pre (1ep bridge + 3ep phase)

[2026-05-31 06:15:46]   train 'c13_Phase_D_bridge_pre_retry4' (1 ep, batch=4, resume=c13_Phase_C_direct_e3.pt)
[2026-05-31 06:16:02]   eval e1 ...
[2026-05-31 06:16:44]   probe e1 ...
[2026-05-31 06:17:39]   E1: loss=0.7579  raw=0.809  shaped=0.804  loops=1
[2026-05-31 06:17:39]   best: E1 shaped=0.804
[2026-05-31 06:17:39]   train 'c13_Phase_D_bridged_retry4' (3 ep, batch=4, resume=c13_Phase_D_bridge_pre_retry4_e1.pt)
[2026-05-31 06:52:21]   eval e1 ...
[2026-05-31 06:53:03]   probe e1 ...
[2026-05-31 06:53:58]   E1: loss=0.7061  raw=0.884  shaped=0.895  loops=3
[2026-05-31 06:53:58]   eval e2 ...
[2026-05-31 06:54:40]   probe e2 ...
[2026-05-31 06:55:35]   E2: loss=0.5906  raw=0.889  shaped=0.905  loops=9
[2026-05-31 06:55:35]   eval e3 ...
[2026-05-31 06:56:18]   probe e3 ...
[2026-05-31 06:57:12]   E3: loss=0.4808  raw=0.905  shaped=0.907  loops=5
[2026-05-31 06:57:12]   best: E3 shaped=0.907
[2026-05-31 06:57:12] 
============================================================
  Phase D attempt 4 — comparison
============================================================

## Phase D attempt 4 — comparison

| Variant | Best epoch | Shaped | Δ vs baseline | |
|---|---|---|---|---|
| Direct | E2 | 0.911 | -0.014 | ✓ winner |
| Bridge+Direct | E3 | 0.907 | -0.018 |  |

**REGRESSION** — best 0.911 < baseline 0.925. Phase deferred.

[2026-05-31 06:57:12] PERMANENT FAILURE: Phase D after 4 attempts.
[2026-05-31 06:57:12] 
============================================================
  Phase E attempt 4 — direct (3ep)
============================================================

## Phase E attempt 4 — direct (3ep)

[2026-05-31 06:57:12]   train 'c13_Phase_E_direct_retry4' (3 ep, batch=4, resume=c13_Phase_C_direct_e3.pt)
[2026-05-31 07:27:44]   eval e1 ...
[2026-05-31 07:28:26]   probe e1 ...
[2026-05-31 07:29:21]   E1: loss=0.7154  raw=0.892  shaped=0.892  loops=3
[2026-05-31 07:29:21]   eval e2 ...
[2026-05-31 07:30:04]   probe e2 ...
[2026-05-31 07:30:58]   E2: loss=0.5998  raw=0.919  shaped=0.898  loops=2
[2026-05-31 07:30:58]   eval e3 ...
[2026-05-31 07:31:41]   probe e3 ...
[2026-05-31 07:32:36]   E3: loss=0.4886  raw=0.900  shaped=0.899  loops=5
[2026-05-31 07:32:36]   best: E3 shaped=0.899
[2026-05-31 07:32:36] 
============================================================
  Phase E attempt 4 — bridge-pre (1ep bridge + 3ep phase)
============================================================

## Phase E attempt 4 — bridge-pre (1ep bridge + 3ep phase)

[2026-05-31 07:32:36]   train 'c13_Phase_E_bridge_pre_retry4' (1 ep, batch=4, resume=c13_Phase_C_direct_e3.pt)
[2026-05-31 07:32:51]   eval e1 ...
[2026-05-31 07:33:33]   probe e1 ...
[2026-05-31 07:34:28]   E1: loss=0.7579  raw=0.809  shaped=0.804  loops=1
[2026-05-31 07:34:28]   best: E1 shaped=0.804
[2026-05-31 07:34:28]   train 'c13_Phase_E_bridged_retry4' (3 ep, batch=4, resume=c13_Phase_E_bridge_pre_retry4_e1.pt)
[2026-05-31 08:05:00]   eval e1 ...
[2026-05-31 08:05:42]   probe e1 ...
[2026-05-31 08:06:37]   E1: loss=0.7171  raw=0.892  shaped=0.905  loops=5
[2026-05-31 08:06:37]   eval e2 ...
[2026-05-31 08:07:19]   probe e2 ...
[2026-05-31 08:08:14]   E2: loss=0.6005  raw=0.909  shaped=0.912  loops=2
[2026-05-31 08:08:14]   eval e3 ...
[2026-05-31 08:08:57]   probe e3 ...
[2026-05-31 08:09:51]   E3: loss=0.4895  raw=0.923  shaped=0.891  loops=2
[2026-05-31 08:09:51]   best: E2 shaped=0.912
[2026-05-31 08:09:51] 
============================================================
  Phase E attempt 4 — comparison
============================================================

## Phase E attempt 4 — comparison

| Variant | Best epoch | Shaped | Δ vs baseline | |
|---|---|---|---|---|
| Direct | E3 | 0.899 | -0.026 |  |
| Bridge+Direct | E2 | 0.912 | -0.013 | ✓ winner |

**REGRESSION** — best 0.912 < baseline 0.925. Phase deferred.

[2026-05-31 08:09:51] PERMANENT FAILURE: Phase E after 4 attempts.
[2026-05-31 08:09:51] 
============================================================
  Final summary
============================================================

## Final summary

### Succeeded

- Phase C: shaped=0.925

### Permanently failed (regression in all queue positions)

- Phase B
- Phase D
- Phase E

### Final checkpoint

`c13_Phase_C_direct_e3.pt` shaped=0.925

Completed: 2026-05-31 08:09:51
[2026-05-31 08:09:51] Done. Master log: /home/aomukai/Ninereeds/training/logs/campaign_13_reports/orchestrator_log.md
[2026-05-31 08:09:51] Per-epoch detail: /home/aomukai/Ninereeds/training/logs/campaign_13_reports/<run>_e<N>_results.txt
[2026-05-31 08:10:17] Orchestrator complete — starting extension.
[2026-05-31 08:10:17]   fallback: using most recent winner c13_Phase_C_winner.pt
[2026-05-31 08:10:59] Final checkpoint eval: shaped=0.925

---

# Extension Pass

Started: 2026-05-31 08:10:59

Base checkpoint: `c13_Phase_C_winner.pt`  shaped=0.925

No bridge between phases (bridge consistently hurt in base run).

[2026-05-31 08:10:59] 
============================================================
  Extension pass 1
============================================================

## Extension pass 1

[2026-05-31 08:10:59] 
============================================================
  Phase_A_ext (2 ep, pass 1)
============================================================

## Phase_A_ext (2 ep, pass 1)

[2026-05-31 08:10:59]   train 'c13_Phase_A_ext_p1' (2 ep, batch=4, resume=c13_Phase_C_winner.pt)
[2026-05-31 08:50:51]   E1: loss=0.6964  raw=0.897  shaped=0.912  loops=2
[2026-05-31 08:52:28]   E2: loss=0.5539  raw=0.913  shaped=0.914  loops=1
[2026-05-31 08:52:28]   best: E2 shaped=0.914
| Phase_A_ext | E2 | 0.914 | -0.011 | no improvement |
[2026-05-31 08:52:28]   No improvement: Phase_A_ext (best=0.914 vs 0.925)
[2026-05-31 08:52:28] 
============================================================
  Phase_B_ext (5 ep, pass 1)
============================================================

## Phase_B_ext (5 ep, pass 1)

[2026-05-31 08:52:28]   train 'c13_Phase_B_ext_p1' (5 ep, batch=4, resume=c13_Phase_C_winner.pt)
[2026-05-31 10:05:27]   E1: loss=0.7446  raw=0.895  shaped=0.895  loops=1
[2026-05-31 10:07:05]   E2: loss=0.6653  raw=0.896  shaped=0.905  loops=3
[2026-05-31 10:08:42]   E3: loss=0.5917  raw=0.910  shaped=0.913  loops=4
[2026-05-31 10:10:19]   E4: loss=0.5085  raw=0.892  shaped=0.906  loops=3
[2026-05-31 10:11:56]   E5: loss=0.4197  raw=0.910  shaped=0.904  loops=5
[2026-05-31 10:11:56]   best: E3 shaped=0.913
| Phase_B_ext | E3 | 0.913 | -0.012 | no improvement |
[2026-05-31 10:11:56]   No improvement: Phase_B_ext (best=0.913 vs 0.925)
[2026-05-31 10:11:56] 
============================================================
  Phase_C_ext (2 ep, pass 1)
============================================================

## Phase_C_ext (2 ep, pass 1)

[2026-05-31 10:11:56]   train 'c13_Phase_C_ext_p1' (2 ep, batch=4, resume=c13_Phase_C_winner.pt)
[2026-05-31 10:47:59]   E1: loss=0.676  raw=0.896  shaped=0.885  loops=2
[2026-05-31 10:49:36]   E2: loss=0.5561  raw=0.907  shaped=0.925  loops=1
[2026-05-31 10:49:36]   best: E2 shaped=0.925
| Phase_C_ext | E2 | 0.925 | +0.000 | no improvement |
[2026-05-31 10:49:36]   No improvement: Phase_C_ext (best=0.925 vs 0.925)
[2026-05-31 10:49:36] 
============================================================
  Phase_D_ext (5 ep, pass 1)
============================================================

## Phase_D_ext (5 ep, pass 1)

[2026-05-31 10:49:36]   train 'c13_Phase_D_ext_p1' (5 ep, batch=4, resume=c13_Phase_C_winner.pt)
[2026-05-31 11:49:01]   E1: loss=0.7109  raw=0.868  shaped=0.893  loops=2
[2026-05-31 11:50:38]   E2: loss=0.6296  raw=0.900  shaped=0.910  loops=4
[2026-05-31 11:52:15]   E3: loss=0.5567  raw=0.899  shaped=0.895  loops=9
[2026-05-31 11:53:52]   E4: loss=0.4732  raw=0.910  shaped=0.902  loops=3
[2026-05-31 11:55:30]   E5: loss=0.3848  raw=0.914  shaped=0.910  loops=1
[2026-05-31 11:55:30]   best: E2 shaped=0.910
| Phase_D_ext | E2 | 0.910 | -0.015 | no improvement |
[2026-05-31 11:55:30]   No improvement: Phase_D_ext (best=0.910 vs 0.925)
[2026-05-31 11:55:30] 
============================================================
  Phase_E_ext (5 ep, pass 1)
============================================================

## Phase_E_ext (5 ep, pass 1)

[2026-05-31 11:55:30]   train 'c13_Phase_E_ext_p1' (5 ep, batch=4, resume=c13_Phase_C_winner.pt)
[2026-05-31 12:47:58]   E1: loss=0.7213  raw=0.892  shaped=0.894  loops=3
[2026-05-31 12:49:35]   E2: loss=0.6383  raw=0.914  shaped=0.912  loops=3
[2026-05-31 12:51:13]   E3: loss=0.5642  raw=0.910  shaped=0.901  loops=5
[2026-05-31 12:52:50]   E4: loss=0.4784  raw=0.906  shaped=0.909  loops=3
[2026-05-31 12:54:27]   E5: loss=0.3874  raw=0.905  shaped=0.907  loops=0
[2026-05-31 12:54:27]   best: E2 shaped=0.912
| Phase_E_ext | E2 | 0.912 | -0.013 | no improvement |
[2026-05-31 12:54:27]   No improvement: Phase_E_ext (best=0.912 vs 0.925)
[2026-05-31 12:54:27] Pass 1: no phase improved. Extension complete.
[2026-05-31 12:54:27] 
============================================================
  Extension complete
============================================================

## Extension complete


### Extension final result

Checkpoint: `c13_Phase_C_winner.pt`  shaped=0.925

Completed: 2026-05-31 12:54:27
[2026-05-31 12:54:27] Done. Final: c13_Phase_C_winner.pt shaped=0.925

# Linux session handoff — 2026-05-28

## What was done today (Windows session)

- Phase B (grammar corpus): already complete before this session
- Phase G (phase localization 5806×3): already complete before this session
- Phase G2 (naturalness audit): **partially complete** — see below

Created `meta/scripts/audit_localizations_win.py` (Windows variant of the audit script:
UTF-8 console fix, POSIX path keys in JSONL, `.env` overrides shell env vars).

Fixed `.env` format (bare key → `OPENROUTER_API_KEY=...`).

---

## Audit log state at handoff

| Corpus | Status | Flagged records | Notes |
|---|---|---:|---|
| reasoning JP | **COMPLETE** | 0 | clean |
| reasoning ZH | **COMPLETE** | 0 | clean |
| triplets JP | **COMPLETE** | 753 / 765 records | 56% flag rate |
| triplets ZH | **COMPLETE** | 302 / 331 records | 22% flag rate |
| phases JP | **COMPLETE** | 5,196 / 5,236 records | 89.5% flag rate, 570 clean |
| phases ZH | **PARTIAL** | 2,312 / 2,475 records | stopped in phase_5 ~'c' |

Logs: `tmp/audit_JP_phases.jsonl`, `tmp/audit_ZH_phases.jsonl`, etc.

---

## Step 1 — Resume ZH phases audit

ZH stopped mid phase_5 (last files: `competing_ZH`, `celebrating_ZH`). Resume is automatic
— already-audited flagged files are skipped via JSONL dedup. ~1,900 files remaining
(phase_5 tail + all of phase_6).

**Via OpenRouter** (fast):
```bash
KEY=$(grep OPENROUTER_API_KEY .env | cut -d= -f2-)
OPENROUTER_API_KEY="$KEY" nohup python3 -B meta/scripts/audit_localizations.py run \
  --corpus phases --lang ZH --model google/gemma-4-26b-a4b-it --workers 4 \
  >> tmp/audit_phases_ZH_openrouter.log 2>&1 &
```

**Via local LM Studio** (free):
```bash
nohup python3 -B meta/scripts/audit_localizations.py run \
  --corpus phases --lang ZH --local --workers 2 \
  >> tmp/audit_phases_ZH_local.log 2>&1 &
```

Check progress: `python3 -B meta/scripts/audit_localizations.py report`

---

## Step 2 — Fix pass (after ZH audit completes)

Model: **`google/gemma-4-E4B-it` in LM Studio** (~2.5–3 GB VRAM Q4). Free, fast.

`fix_localizations.py` needs to be adapted before running:
1. Point at LM Studio local endpoint
2. Disable thinking: `enable_thinking=False`
3. Replace full-rewrite prompt with surgical substitution prompt:
   - Show original file
   - Show issue list as `[{"line": "...", "suggestion": "..."}]`
   - Instruct: output the file with ONLY those exact lines replaced, nothing else changed
4. Keep existing structure validator

```bash
# After adapting fix_localizations.py:
python3 -B meta/scripts/fix_localizations.py run --lang JP --local --workers 4
python3 -B meta/scripts/fix_localizations.py run --lang ZH --local --workers 4
```

---

## Step 3 — Wiki localization (overnight Thu → Fri)

Use DeepSeek via OpenRouter. Write a new script (e.g. `meta/scripts/localize_wiki.py`)
modelled on `localize_phases.py` but with the naturalness-first prompt baked in from
the start.

**Key prompt principle — learned from phase localization mistakes:**
> Preserve the meaning, not the wording. A native speaker should not be able to tell
> this came from English. Do NOT translate word-for-word.

- Say "localize naturally" not "translate"
- Include anti-calque examples for JP and ZH in the system prompt
- JP: plain form, no romaji; avoid 持つ for inanimate features (use がある), avoid
  着地する for non-aircraft, avoid calque verb choices for falling/sitting/resting objects
- ZH: Traditional Chinese only; same anti-calque guidance

Reference: `localize_phases.py` post-2026-05-28 prompt fix for the naturalness guidance block.

---

## Relevant files

| File | Purpose |
|---|---|
| `meta/scripts/audit_localizations.py` | Audit script (Linux original) |
| `meta/scripts/audit_localizations_win.py` | Windows variant |
| `meta/scripts/fix_localizations.py` | Fix script — needs prompt adaptation |
| `tmp/audit_JP_phases.jsonl` | JP phase audit log (complete) |
| `tmp/audit_ZH_phases.jsonl` | ZH phase audit log (partial — resume) |
| `tmp/audit_JP_triplets.jsonl` | JP triplets audit log (complete) |
| `tmp/audit_ZH_triplets.jsonl` | ZH triplets audit log (complete) |
| `docs/grammar_plan.md` | Grammar curriculum design |
| `todo.md` | Full task queue with Phase G2 resume commands |

---
name: project-phase-localization
description: "Phase G complete (5806×3); Phase G2 naturalness audit in progress, resume on Linux"
metadata: 
  node_type: memory
  type: project
  originSessionId: f86256f4-a5c7-42f5-82ac-e80061cc1e4a
---

**Phase G (localize_phases.py): COMPLETE 2026-05-28.**
All 5806 English phase files localized into DE/JP/ZH. Prompt fix applied during session:
uses "localize naturally" (not "translate"), anti-calque guidance with JP/ZH examples,
corrected STRUCTURAL_RULES (removed hardcoded "6 lines", clarified 1-to-1 line mapping).

**Phase G2 (naturalness audit): IN PROGRESS — resume on next Linux session.**

Audit scripts:
- `meta/scripts/audit_localizations.py` — detect; writes JSONL to tmp/audit_<lang>_<corpus>.jsonl
- `meta/scripts/fix_localizations.py` — repair from audit log (prompt needs surgical-substitution update before use)
- Always run with `python3 -B` to bypass stale .pyc files

Audit log state (as of 2026-05-28 shutdown):

| Corpus | Lang | Files | Status | Flagged |
|---|---|---|---|---|
| reasoning | JP | 27 | COMPLETE | 0 |
| reasoning | ZH | 27 | COMPLETE | 0 |
| grounded | JP | 48 | needs re-run (was partial mid-bug) | — |
| grounded | ZH | 48 | needs re-run (was partial mid-bug) | — |
| triplets | JP | 1345 | COMPLETE | 753 |
| triplets | ZH | 1345 | COMPLETE | 302 |
| phases | JP | 5806 | 2477/5806 (43%) — killed at shutdown | 2468 |
| phases | ZH | 5806 | not started | — |

Phase files have ~99% flag rate — generated before the 2026-05-28 naturalness prompt fix,
contain systematic calques (持つ, 座る, 着地する for inanimate objects).

Audit logs committed to git: tmp/audit_JP_phases.jsonl, tmp/audit_JP_triplets.jsonl, tmp/audit_ZH_triplets.jsonl

Before fix pass: update fix_localizations.py to use surgical substitutions (not full rewrites).

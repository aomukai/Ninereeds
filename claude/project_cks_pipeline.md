---
name: project-cks-pipeline
description: CKS education corpus pipeline — all 5 phases complete, 418 dialogue files ready for Campaign 16
metadata:
  type: project
---

The CKS (Core Knowledge Sequence) pipeline converts K-8 curriculum PDFs into Ninereeds training dialogues. This is the Campaign 16 corpus — runs after language (C14) and thinking/reasoning (C15).

**Pipeline status (2026-06-18): ALL PHASES COMPLETE**

| Phase | What | Status |
|---|---|---|
| 1 | Ontology extraction (Claude reads PDFs → JSONL) | COMPLETE |
| 2 | Lesson skeleton (DeepSeek adds `facts` + `misconceptions`) | COMPLETE |
| 2.5 | Audit (Claude verifies skeletons) | COMPLETE |
| 3 | Dependency linking pass (populate `future_extensions`) | COMPLETE |
| 4 | Dialogue generation (DeepSeek → `.md` files) | COMPLETE |
| 5 | Manifest (order by tier, interleave domains) | COMPLETE |

**Key files:**
- Spec: `training_data/ninereeds_cks_curriculum.md` (v2.2)
- Phase 1: `training_data/04_education/phase1_preschool.jsonl` (39 nodes) + `phase1_k8.jsonl` (262 nodes)
- Phase 2: `training_data/04_education/phase2_merged.jsonl` (301 nodes with facts + misconceptions)
- Phase 4 output: `training_data/04_education/dialogues/preschool/{domain}/` and `k8/band_{a,b,c}/{domain}/`
- Runner scripts: `meta/scripts/phase2_gen.py`, `meta/scripts/phase4_gen.py`
- Manifest: `training/corpus_admin/campaign16_manifest.txt` (418 files, tier 0→9)
- Block files: `training/corpus_admin/campaign16_blocks/tier_N.txt` (10 files, one per tier)
- Manifest builder: `meta/scripts/build_campaign16_manifest.py`

**Corpus facts:**
- 301 nodes total: 10 domains (math, science, time, geography, language, arts, civics, economics, health, social_emotional)
- Preschool: 39 nodes × 4 languages (en/de/jp/zh) = 156 dialogue files
- K–8: 262 nodes × 1 language (domain-assigned) = 262 dialogue files
- Total: 418 `.md` files, all validated (0 issues)
- Language distribution: JP 120, EN 112, DE 101, ZH 85 (max/min ratio 1.41x — within spec's 2x target)

**Manifest order:** Tier 0 (preschool concrete anchors) → Tier 9 (grade 8). Within each tier: round-robin by domain (alphabetical). Preschool nodes emit en/de/jp/zh consecutively. K-8 nodes emit single assigned language. Tier boundaries: KG=1, G1=2, G2=3, G3=4, G4=5, G5=6, G6=7, G7=8, G8=9.

**Phase 4 runner notes:**
- `phase4_gen.py` uses NIM (DeepSeek V4 Pro, free) primary / OpenRouter (V4 Flash, paid) fallback
- Validation: checks `[user]`/`[Ninereeds]` tags, Ninereeds turns end with `?` or `？`, vocab anchors (EN only)
- Full-width `？` accepted for JP/ZH; vocab anchor check EN-only (German/JP/ZH use native vocabulary)
- Key prompt constraint: Ninereeds turns must be ONE question; misconceptions must be embedded INSIDE the question ("If X, why isn't Y?" not "Y? I thought X.")

**Why:** CKS is the knowledge-grounding corpus for Campaign 16. It teaches Ninereeds named facts about the world (science, history, geography, math concepts) in dialogue format, grounded by misconceptions that give the dialogue natural tension.

**Campaign sequence:** C14 (language) → C15 (thinking/reasoning) → C16 (education/CKS). Do not start C16 until C15 confirms reasoning is stable.

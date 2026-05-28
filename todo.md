# TODO

Active work queue. See `docs/training.md` for the full procedure.
Completed phases: `archive/milestones/2026-05-29_corpus_milestone.md`.

---

## Current Direction

Corpus is fully localised and clean. Next priorities:

1. **Phase D** — Run 13: grammar-ordered corpus, sequential training
2. **Phase I** — Adversarial corpus critic (run before or alongside run 13)
3. **Phase E** — Wiki split for finer curriculum ordering (lower urgency)
4. **Phase H** — Ordering manifests (depends on E)

---

## Phase C — Grammar Corpus Builder (one item remaining)

- [x] `build_training_corpus.py` includes `training_data/grammar` in numeric order
- [x] `bridge_design.md` excluded from training sweep
- [ ] Build run-specific corpus output: `training/corpus/run13_grammar_ordered.txt`
- [ ] Confirm grammar insertion point (hypothesis: after `lang_2`, before `lang_3/4`)

---

## Phase D — Run 13

Goal: test whether grammar-function ordering improves dative/accusative
behaviour, spatial output, and general routing at 150M.

Run shape:
- model: `--scale-150m`
- corpus: ordered full corpus with grammar inserted after `lang_2`
- training mode: `--sequential` (no shuffle)
- epochs: 3

Primary probes:
```
Die Wolke ist über dem Berg.
Das Kind geht in den Garten.
Emma gibt dem Jungen den Apfel.
Der Becher ist auf dem Tisch.
Emma stellt den Becher auf den Tisch.
```

Secondary checks: JP `にある`/`を` usage, spatial EN/DE output, arithmetic
echo pressure, shaped score and loop count as promotion gates.

Deliverables:
- [ ] `training/corpus/run13_grammar_ordered.txt`
- [ ] `training/corpus/run13_build_report.txt`
- [ ] `training/logs/run_13_report.md`
- [ ] per-epoch probe + eval results

---

## Phase E — Wiki Splitting

Status: planned (lower urgency — wiki is already localised).

Wiki levels 1–4 are localised but not split into single-concept files.
Splitting enables finer curriculum ordering and concept-by-concept sequencing.

Plan:
- split to `training_data/wiki_split/` (mirror, not destructive)
- level 1: one `[user]` block per file
- level 2–4: split by meaningful subsection; do not orphan follow-up prompts

Validation: same `[user]`/`[Ninereeds]` totals as source; no empty files.

---

## Phase H — Ordering Manifests

Status: planned (depends on Phase E).

Required once wiki is split:
- `training_data/wiki_split/manifest.md`
- optional: `training_data/phases/phase_manifest.md`

Corpus builder should prefer manifest order over filesystem order when a
manifest is present.

---

## Phase I — Adversarial Corpus Critic

Status: planned. Run before run 13 if time allows; essential before any
full-scale training run.

The corpus is the only lever on a small model. One malformed file has
outsized impact. This critic assumes guilt and maps every potential issue —
it does not fix, only triage.

### Verdict levels

| Verdict | Meaning |
|---|---|
| `PASS` | No issues |
| `PATCH` | Deterministic fix (wrong tag casing, extra line, etc.) |
| `REGENERATE` | Needs full regeneration |
| `HUMAN_REVIEW` | Ambiguous — human decides |

### Reason tags

```
[STRUCT]          [user]/[Ninereeds] count wrong or tag format broken
[POS]             Wrong register or pronoun leaked
[SEMANTIC_DRIFT]  Meaning drifted from expected concept definition
[JP_NATURALNESS]  Calque verb, wrong counter, unnatural expression
[ZH_SIMPLIFIED]   Simplified Chinese found
[ZH_NATURALNESS]  Calque or unnatural phrasing
[DE_CASE]         Wrong dative/accusative form
[ALLOWLIST]       Vocabulary outside inventory/allowlist.txt
[NEGATION]        Negation in body lines
[DUPLICATE]       Duplicate or conflicting concept definition
[HALLUCINATION]   Factual claim that is wrong or unverifiable
```

### Architecture

1. **Deterministic pre-screen** (no API) — catches `[STRUCT]`, `[ZH_SIMPLIFIED]`,
   `[NEGATION]`, `[ALLOWLIST]`. Emits `PATCH`/`PASS` directly.
2. **LLM critic** (DeepSeek batch) — `REGENERATE` or `HUMAN_REVIEW` with tags.
3. **Fix dispatcher** — routes verdicts to the right handler.

Output: `tmp/critic_triage.jsonl`, `critic_patch_queue.txt`,
`critic_regen_queue.txt`, `critic_human_queue.txt`.

Coverage priority:
1. `training_data/phases/` — highest training weight
2. `training_data/grammar/` — case errors poison case learning
3. `training_data/lang/`
4. `training_data/triplet_stories/`
5. `training_data/reasoning/`, `training_data/philosophy/`

Implementation: `meta/scripts/corpus_critic.py`

---

## Stop Gates

Before training:
- sequential/no-shuffle mode confirmed working
- grammar corpus builder includes grammar in correct position
- no files skipped by corpus builder

After each epoch:
- loops ≥ 4 → pause
- abrupt stops ≥ 2 → pause
- shaped score collapses vs baseline → pause
- grammar probes improve but shaped score fails promotion → pause

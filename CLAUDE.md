# Ninereeds — Claude session guide

## What this project is

Ninereeds is a small Hebbian-trained AI. It trains on a hand-crafted corpus of structured
`[user]`/`[Ninereeds]` dialogue files. Because the model is small, there is no error
averaging from scale — every malformed training file has outsized impact. Quality gates
are more important here than in a typical project.

## Dispatch policy

**Claude handles:** planning, routing, verification, small targeted edits.
**DeepSeek handles:** bulk file I/O — rewriting, repairing, generating corpus files.

Do not use Claude tokens for corpus file work. Write a prompt, send it to DeepSeek,
read the result back, verify it, record progress. That is the full loop.

## Platform rules

| Mechanism | Works on | Notes |
|---|---|---|
| Direct OpenRouter API (urllib / openai client) | Windows + Linux | Preferred everywhere |
| `opencode` CLI subprocess | Linux only | `~/.opencode/bin/opencode` does not exist on Windows |
| bash scripts in `meta/scripts/` | Linux only | opencode wrappers |

**On Windows, never reach for opencode.** Use the direct API runners instead.
If you wake up on Linux and want to use opencode, confirm `~/.opencode/bin/opencode` exists first.

## Auth

All direct API runners read the key in this order:

1. `OPENROUTER_API_KEY` env var ← set this, works on both platforms
2. `OPENAI_API_KEY` env var (fallback)
3. `~/.local/share/opencode/auth.json` → `.openrouter.key` (Linux only, used by `worker_repair.py`)
4. `WORKER_API_KEY` env var (used by `worker_repair.py`)

## Repo structure

```
archive/          ← obsolete scripts, old prompts, historical artifacts
docs/             ← design docs, vision docs, reference notes
inventory/        ← allowlist.txt and other word/concept lists
loras/            ← LoRA adapter files
meta/
  scripts/        ← all batch runners, generators, verifiers
  workflow/       ← audit and analysis tools
tmp/              ← temporary outputs: logs, batch files, intermediate results
training/         ← training harness, rounds, logs, teacher skills
training_data/    ← corpus: phases, wiki, philosophy, reasoning, stories, lang
```

Root entry points (do not move): `bdh.py`, `train.py`, `inference.py`, `eval.py`,
`harness.py`, `prompt_shaper.py`.

## Tool index

### Cross-platform (direct API — use these on Windows or Linux)

**`meta/scripts/repair_formatting_opencode.py`** — formatting queue runner
- Queue: `training_data/phases/repair_formatting.txt`
- Progress: `training_data/phases/repair_progress_formatting.txt`
- Run: `python3 meta/scripts/repair_formatting_opencode.py --batch 250 --workers 6 --timeout 300`
- Verifies `[user]`/`[Ninereeds]` structure after every write; retries once on bad output
- Appends progress ledger only after confirmed write to disk

**`meta/scripts/extract_vocab.py`** — vocabulary extraction runner
- Extracts and normalises verbs, adjectives, nouns from any corpus directory
- Queue: any `files.txt` (absolute paths, one per line); progress: `files_done.txt` in same dir
- Run: `python3 meta/scripts/extract_vocab.py --queue training_data/wiki/files.txt --workers 4 --timeout 300`
- `max_tokens=32768` — do not lower; DeepSeek V4 Flash is a thinking model and reasoning tokens eat the budget before output is written. 16k causes `length` stop and truncated responses.
- Output: `nouns.txt`, `verbs.txt`, `adjectives.txt` in the queue's directory (deduped, sorted, merged incrementally)

**`meta/scripts/worker_repair.py`** — damage_map queue runner
- Queue: `training_data/phases/damage_map.txt`
- Uses `openai` client pointed at OpenRouter (install: `pip install openai`)
- Run: `python3 meta/scripts/worker_repair.py --batch 30 --workers 5`
- Claims entries before parallel work; returns failures to front of queue

**`meta/scripts/lang_gen.py`** — multilingual lang file generator
- Reads `inventory/allowlist.txt`, generates lang_1 files via DeepSeek
- Run: `python3 meta/scripts/lang_gen.py [--batch 10] [--workers 4] [--dry-run]`

**`meta/scripts/lang4.py`** — lang_4 structural corpus generator (4A/4B/4C)
- Jobs: hard-coded matrix (116 frames)
- Output: `training_data/lang/lang_4/`
- Run: `python3 meta/scripts/lang4.py gen --workers 4 --batch 5`

**`meta/scripts/lang4d.py`** — lang_4d story corpus generator
- Plans: `training_data/lang/lang_4d_plans.jsonl` · Output: `training_data/lang/lang_4d/`
- Run: `python3 meta/scripts/lang4d.py plan --target 200` then `gen --workers 4`

**`meta/scripts/lang3c.py`** — lang_3c corpus generator (reflexive + benefactive)
- Verb list: `training_data/lang/lang_3c_verbs.txt`
- Jobs: `training_data/lang/lang_3_jobs.jsonl` · Progress: `lang_3_planned.txt`
- Output: `training_data/lang/lang_3/`
- Run: `python3 meta/scripts/lang3c.py plan --workers 4 --batch 10` then `gen --workers 4 --batch 5`

### Linux only (opencode)

**`meta/scripts/opencode_ds.sh`** — single DeepSeek call
- `meta/scripts/opencode_ds.sh prompt.txt` or `cat prompt.txt | meta/scripts/opencode_ds.sh`
- Reads API key from opencode auth store

**`meta/scripts/opencode_ds_fanout.sh`** — parallel fan-out
- `meta/scripts/opencode_ds_fanout.sh --workers 10 tmp/prompts/*.txt`
- One opencode process per prompt file; output lands in `tmp/opencode_fanout/`

### Audit and analysis (any platform, read-only)

| Script | Purpose |
|---|---|
| `meta/workflow/vocabulary_audit.py` | Scan corpus for vocabulary issues |
| `meta/workflow/vocabulary_gap_check.py` | Check coverage gaps |
| `meta/workflow/audit_documentation.py` | Documentation audit |
| `meta/scripts/build_dependency_graph.py` | Rebuild `inventory/dependency_graph.json` from phase file names |
| `meta/scripts/pos_check.py` | Part-of-speech validation |
| `meta/scripts/strip_opener.py` | Strip bad opener lines |
| `meta/scripts/extract_verbs.py` | Verb extraction for review |
| `meta/scripts/sort_allowlist_by_frequency.py` | Re-sort inventory/allowlist.txt by corpus frequency |

## Active queues (as of 2026-05-14)

| Queue | Total | Done | Remaining | Status |
|---|---|---|---|---|
| formatting | 275 | 275 | 0 | **DONE** |
| duplicate | 58 | 58 | 0 | **DONE** |

## Lang curriculum status (as of 2026-05-14)

All lang levels complete through Level 4:

| Level | Files | Notes |
|---|---|---|
| lang_1 | ~5k | One file per allowlist word; EN/DE/JP/ZH |
| lang_2 | ~6k | Semantic frames; adj/adv/noun/pronoun/combo |
| lang_3a | 83 | Dative double-object and prepositional; 52 verbs |
| lang_3b | 33 | Dative + genitive possessor; 33 verbs |
| lang_3c | 99 | Reflexive and benefactive; 47 verbs |
| lang_3d | 400 | Tiny parallel stories integrating all Level-3 constructions |
| lang_4 | 116 | Prepositions: static location (4A), movement (4B), instrument (4C) |
| lang_4d | 200 | Tiny parallel stories integrating all Level-4 constructions |

lang_4 complete (2026-05-14): 116 files in training_data/lang/lang_4/, generated by meta/scripts/lang4.py.
lang_4d complete (2026-05-14): 200 story files in training_data/lang/lang_4d/, generated by meta/scripts/lang4d.py.
Templates at training_data/lang/level_4_templates.md.
Lang curriculum complete through level 4. Next: Level 5 (Q&A pairs / fragment answers).

## Corpus structure

```
training_data/
  phases/
    phase_1/ … phase_6/   ← structured [user]/[Ninereeds] dialogue files
    repair_formatting.txt  ← formatting queue (done)
    repair_duplicate.txt   ← duplicate queue (done)
  lang/
    lang_1/               ← multilingual word files (EN/DE/JP/ZH), complete
    level_2a_templates.md ← lang_2 generation templates: verbs, adj/adv, nouns
    level_2b_templates.md ← lang_2 generation templates: pronouns, possession
    level_2c_templates.md ← lang_2 generation templates: combinations
  wiki/                   ← reference material
  triplet_stories/        ← narrative training data
  reasoning/              ← reasoning examples
  philosophy/             ← philosophical framing
```

## Corpus file format

Every phase file must have exactly 4 `[user]`/`[Ninereeds]` block pairs separated by blank lines.

```
[user]what does X look like?
[Ninereeds]This is X.
X is [property].
X is [property].
X is [property].
X is [property].
X is [property].
X is [A] and [B].

[user]where does X appear?
...
```

Rules:
- `[Ninereeds]` opener is on the same line as the tag: `[Ninereeds]This is X.`
- 5 body lines after the opener, 1 summary combining two properties
- One sentence per line, one period per line
- No pronouns (it, its, they, them, he, she, etc.)
- No negation in body lines
- Subject of every line is X or a part of X

## Hard constraints

- Never modify `bdh.py` or anything in `core/` (model weights live there when training runs)
- No training run until a full corpus audit returns GO
- Only mark queue items done with file-level evidence (read the file back after write)
- Do not start vocabulary rewrites without user sign-off

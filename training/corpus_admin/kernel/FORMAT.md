# Kernel Corpus File Format

## Decision

Use two formats:

- Source/audit format: one Markdown dialogue file per concept angle.
- Training format: prompt/completion JSONL built from the Markdown files.

Do not train the full kernel corpus as one concatenated text file. The experiment showed that concatenated text teaches file transitions and stray continuation behavior. JSONL with masked instruction loss trains the response behavior directly.

## Source Directory Layout

Small experiment:

```text
training_data/kernel/<category>/<concept>/<angle>.md
```

Full vocabulary run:

```text
training_data/kernel_full/<category>/<concept>/<angle>.md
```

Converted redesign base:

```text
training_data/kernel_from_redesign/<category>/<concept>/<angle>.md
```

Gap-fill files generated for missing angles:

```text
training_data/kernel_gap_fill/<category>/<concept>/<angle>.md
```

Each concept directory also has:

```text
_meta.json
```

The metadata records the input concept JSON, provider, model, and generation timestamp.

## Source File Syntax

Use only these tags:

```text
[user]
[Ninereeds]
```

The tag and content should be on the same line:

```text
[user]what is a dog?
[Ninereeds]A dog is an animal. A dog is a mammal. A dog is often a pet.
```

Rules:

- 1 to 4 exchanges per file.
- No Markdown fences.
- No comments.
- No leading space after `[user]` or `[Ninereeds]`.
- Responses should be 1 to 4 short sentences.
- Prefer repeated concept names over pronouns.
- Use plain English.
- Avoid contractions.
- Avoid long explanations.

## Required Angle Files

Every concept should produce exactly these 14 files:

```text
what_is.md
classification.md
properties.md
behavior.md
location.md
connections.md
negative_category.md
negative_part.md
yes_no_true.md
yes_no_false.md
unknown_name.md
unknown_internal.md
followup_known.md
followup_unknown.md
```

For abstract concepts, keep the same filenames but adapt the question naturally. Example: `location.md` can answer where the concept appears in language or life.

## Angle Purpose

`what_is.md`
Defines the concept directly.

`classification.md`
States the category and rejects one nearby wrong category if useful.

`properties.md`
Names important visible, functional, or semantic properties.

`behavior.md`
Says what the concept does, what happens with it, or how it is used.

`location.md`
Says where the concept can be found or where it occurs.

`connections.md`
Lists related concepts and categories.

`negative_category.md`
Rejects a false category.

`negative_part.md`
Rejects a false part, property, behavior, or relation.

`yes_no_true.md`
Asks a true yes/no question and starts the answer with `Yes.`

`yes_no_false.md`
Asks a false yes/no question and starts the answer with `No.`

`unknown_name.md`
Handles unknown specific identity, owner, name, source, address, or exact instance.

`unknown_internal.md`
Handles unknown thoughts, feelings, reasons, exact counts, current state, or private details.

`followup_known.md`
A two- or three-turn chat where the user asks `what else?` and Ninereeds adds known facts.

`followup_unknown.md`
A two- or three-turn chat where the user asks a missing specific fact and Ninereeds says it does not know.

## Training JSONL Format

Build JSONL from source files:

```json
{"prompt":"[user]what is a dog?\n[Ninereeds]","completion":"A dog is an animal. A dog is a mammal. A dog is often a pet."}
```

For multi-turn files, each assistant turn becomes one training example with the previous turns included in the prompt.

Example:

```json
{"prompt":"[user]what is a dog?\n[Ninereeds]A dog is an animal.\n[user]what else?\n[Ninereeds]","completion":"A dog has four legs. A dog has fur."}
```

Training should use:

```bash
--jsonl-data training/corpus/kernel_full.jsonl
--mask-instruction-loss
--prompt-loss-weight 0.0
--prompt-tail-bytes 96
--block-size 128
```

## Seed JSONL Format

Hand-authored rich seed:

```json
{"concept_id":"dog","category":"animals","kind":"concrete_noun","positive":["animal","mammal","pet","fur","four legs"],"negative":["machine","vehicle","tool","place"],"unknown":["specific name","specific thoughts","specific location"]}
```

Full-vocabulary inferred seed:

```json
{"concept_id":"water","category":"materials","kind":"concrete_noun","source":"inventory/allowlist.txt","generation_mode":"infer_simple_facts"}
```

DeepSeek may infer simple positive, negative, and unknown facts when these fields are absent.

Gap-fill seed after converting redesign:

```json
{"concept_id":"dog","category":"animals","kind":"concrete_noun","existing_angles":["behavior","connections","what_is"],"missing_angles":["classification","yes_no_true"],"generation_mode":"fill_missing_kernel_angles"}
```

When `missing_angles` is present, the generator must produce only those files.

## Recommended Full-Vocabulary Path

Convert the existing redesign corpus first. It already contains grounded dialogue files and should not be discarded.

```bash
python3 meta/scripts/convert_redesign_to_kernel.py --clean
```

Validate the converted files:

```bash
python3 meta/scripts/generate_kernel_corpus.py validate \
  --words-file training/corpus_admin/kernel/kernel_full_words.jsonl \
  --out-root training_data/kernel_from_redesign
```

Build the converted JSONL:

```bash
python3 meta/scripts/generate_kernel_corpus.py build-jsonl \
  --words-file training/corpus_admin/kernel/kernel_full_words.jsonl \
  --out-root training_data/kernel_from_redesign \
  --output training/corpus/kernel_from_redesign.jsonl \
  --report training/corpus/kernel_from_redesign_jsonl_report.md \
  --lowercase-user-copy
```

Then generate only missing kernel angles:

```bash
python3 meta/scripts/build_kernel_gap_seed.py \
  --words-file training/corpus_admin/kernel/kernel_full_words.jsonl \
  --source-root training_data/kernel_from_redesign \
  --output training/corpus_admin/kernel/kernel_gap_words.jsonl
```

Generate gap files:

```bash
python3 meta/scripts/generate_kernel_corpus.py gen \
  --words-file training/corpus_admin/kernel/kernel_gap_words.jsonl \
  --out-root training_data/kernel_gap_fill \
  --source openrouter \
  --workers 3
```

This is preferable to regenerating everything from scratch. Full regeneration is useful only for concepts absent from redesign, malformed source files, or after the converted-plus-gap model fails a grounding gate.

## Full Vocabulary Commands

Build seed list:

```bash
python3 meta/scripts/build_kernel_vocab_seed.py \
  --output training/corpus_admin/kernel/kernel_full_words.jsonl
```

Generate with providers:

```bash
python3 meta/scripts/generate_kernel_corpus.py gen \
  --words-file training/corpus_admin/kernel/kernel_full_words.jsonl \
  --out-root training_data/kernel_full \
  --source openrouter \
  --workers 3
```

```bash
python3 meta/scripts/generate_kernel_corpus.py gen \
  --words-file training/corpus_admin/kernel/kernel_full_words.jsonl \
  --out-root training_data/kernel_full \
  --source deepseek \
  --workers 2
```

```bash
python3 meta/scripts/generate_kernel_corpus.py gen \
  --words-file training/corpus_admin/kernel/kernel_full_words.jsonl \
  --out-root training_data/kernel_full \
  --source nvidia \
  --workers 1
```

Validate:

```bash
python3 meta/scripts/generate_kernel_corpus.py validate \
  --words-file training/corpus_admin/kernel/kernel_full_words.jsonl \
  --out-root training_data/kernel_full
```

Build training JSONL:

```bash
python3 meta/scripts/generate_kernel_corpus.py build-jsonl \
  --words-file training/corpus_admin/kernel/kernel_full_words.jsonl \
  --out-root training_data/kernel_full \
  --output training/corpus/kernel_full.jsonl \
  --report training/corpus/kernel_full_jsonl_report.md \
  --repeat-identity 5 \
  --repeat-kernel 1 \
  --lowercase-user-copy
```

Train:

```bash
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
/home/aomukai/.unsloth/studio/unsloth_studio/bin/python train.py \
  --phase 0 \
  --jsonl-data training/corpus/kernel_full.jsonl \
  --mask-instruction-loss \
  --prompt-tail-bytes 96 \
  --prompt-loss-weight 0.0 \
  --output core/kernel_full_scratch.pt \
  --epochs 4 \
  --lr 3e-4 \
  --batch-size 8 \
  --block-size 128 \
  --amp-bf16
```

## Scaling Rule

Generate and train in waves:

- Wave 0: 50 concepts, already done.
- Wave 1: 200 to 500 concepts.
- Wave 2: 1,000 concepts.
- Wave 3: full allowlist.

Do not jump directly to 5,156 concepts unless the 200 to 500 concept run improves the grounding gate.

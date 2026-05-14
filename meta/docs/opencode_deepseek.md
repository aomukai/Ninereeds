# DeepSeek via opencode

This repo uses `opencode` from bash for outsourced file work.

## Policy

- Do not use worker MCP delegation for corpus execution.
- Do not use `spawn_agent` or any worker-routing layer as the default outsourcing path.
- If work needs to be outsourced, send it to DeepSeek via `opencode`.
- Keep Codex as the strategic and verification layer.

## Canonical model

```bash
openrouter/deepseek/deepseek-v4-flash
```

Confirmed working in this repo as of 2026-05-07 through:

```bash
~/.opencode/bin/opencode run \
  -m "openrouter/deepseek/deepseek-v4-flash" \
  --dangerously-skip-permissions \
  "Reply with exactly: OPENCODE_OK"
```

## Important behavior

DeepSeek v4 flash is a thinking model.

Practical consequences:

- Expect slow completions on long prompts.
- Leave a large output budget available.
- Keep prompts lean so the budget goes to reasoning and final file text.
- Prefer one bounded file task per call when output shape must be strict.
- For bulk work, fan out many small calls instead of one giant prompt.

In `opencode`, there is no per-call `max_tokens` flag in the normal wrapper flow. The practical way to leave room is:

- keep the prompt short
- attach only the minimum file context
- avoid bloated instructions
- avoid asking for explanations when only file text is needed

If using the OpenRouter API directly instead of `opencode`, set a large completion budget explicitly.

## Output-shape hazards

DeepSeek may sometimes return:

- a receipt block instead of file text if the prompt strongly resembles an executor contract
- multi-sentence packed lines when the target format requires one sentence per line
- valid-looking rewrites with weak semantic drift

Countermeasures:

- require `Output ONLY the rewritten file`
- verify the written file after every run
- keep a progress ledger
- use small bounded batches
- save bad raw responses for debugging

## Canonical bash wrapper

Use:

```bash
meta/scripts/opencode_ds.sh
```

Examples:

```bash
meta/scripts/opencode_ds.sh prompts/my_prompt.txt
```

```bash
cat prompts/my_prompt.txt | meta/scripts/opencode_ds.sh
```

```bash
meta/scripts/opencode_ds.sh --json prompts/my_prompt.txt
```

## Parallel fanout

Use:

```bash
meta/scripts/opencode_ds_fanout.sh prompts/dupe_batch/*.txt
```

Defaults:

- up to 10 concurrent DeepSeek instances
- one prompt file per worker call
- each prompt writes its raw output to `tmp/opencode_fanout/`

Example:

```bash
meta/scripts/opencode_ds_fanout.sh --workers 10 tmp/prompts/*.txt
```

## Recommended executor prompt shape

Use a short instruction header, then the exact file payload.

Good pattern:

```text
Rewrite the target file to remove duplicate lines.
Output only the rewritten file.
Do not return a receipt.
Do not explain anything.

Target file: ...
Issue: ...
Current file:
...
```

Avoid:

- long policy dumps
- unnecessary roleplay
- asking for both execution and reporting in the same call
- embedding unrelated repo context

## Verification

After every outsourced write:

- read the edited file back from disk
- verify the structure the task required
- append the progress ledger only after verification

For corpus rewrite batches, the verification layer stays local in Codex.

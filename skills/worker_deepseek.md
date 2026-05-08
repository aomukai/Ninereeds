# Worker: DeepSeek v4 flash (via opencode)

## When to use

This is the canonical outsource path for this repo.

Use DeepSeek via `opencode` for:

- bulk corpus reads and writes
- bounded rewrite batches
- executor-style file tasks
- I/O-heavy cleanup work

Do not use worker MCP delegation for those tasks.

## Invocation

```bash
meta/scripts/opencode_ds.sh prompt.txt
```

For long prompts, use heredoc:

```bash
meta/scripts/opencode_ds.sh <<'EOF'
...executor prompt...
EOF
```

JSON event mode:

```bash
meta/scripts/opencode_ds.sh --json prompt.txt
```

Parallel fanout:

```bash
meta/scripts/opencode_ds_fanout.sh --workers 10 tmp/prompts/*.txt
```

Run from repo root. The wrapper uses `--dangerously-skip-permissions` for headless execution.

## Strengths
- Fast and cheap for bulk file work
- Reliable for structured JSON manipulation
- Good at following explicit step-by-step instructions

## Limits
- Less reliable for tasks requiring nuanced judgment about training data quality
- Occasionally needs re-runs for complex graph operations — always verify the receipt
- May return a receipt block instead of file text if prompted like an executor contract
- May pack two sentences into one line unless the prompt forbids it
- Needs room for long reasoning/output on hard rewrite tasks

## Rate limits
- Available via OpenRouter — generally no hard daily limits at this tier
- If a run fails with a rate error, wait 60 seconds and retry

## Notes
- opencode operates in the repo directory by default — no need to specify `--dir` when running from repo root
- The model ID `openrouter/deepseek/deepseek-v4-flash` is confirmed working as of 2026-05-07
- Keep prompts lean; DeepSeek v4 flash is a thinking model and performs better when output budget is not wasted on prompt bloat
- Prefer many small parallel calls over one giant prompt
- See `docs/opencode_deepseek.md` for the full standard

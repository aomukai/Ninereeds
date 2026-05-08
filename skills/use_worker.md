# Skill: Use Worker

This file now serves as a short routing note.

## Current policy

- Do not use worker MCP delegation for corpus execution.
- Do not use `spawn_agent` or similar worker-routing layers as the default outsource path.
- If work needs to be outsourced, use DeepSeek via `opencode` from bash.
- Keep Codex local for planning, prompt assembly, verification, and quality review.

## Start here

Read:

- `docs/opencode_deepseek.md`

That document is the canonical standard for:

- `opencode` invocation
- DeepSeek behavior notes
- JSON mode
- bash wrappers
- parallel fanout
- verification expectations

## Current wrappers

- `meta/scripts/opencode_ds.sh`
- `meta/scripts/opencode_ds_fanout.sh`

## Notes

Older codex/worker fallback guidance is obsolete for current repo practice.

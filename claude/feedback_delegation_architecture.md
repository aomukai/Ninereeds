---
name: Worker delegation architecture
description: Claude is the brain; bulk file work goes to codex (gpt-5.4-mini) or DeepSeek fallback
type: feedback
originSessionId: f214e64f-85e7-459c-96c1-d360ca2cd70b
---
Claude Code (me) handles: planning, routing, judgment, receipt verification, reading 1–5 files, writing single documents, quick grep/jq checks, decisions.

Primary worker: codex — OpenAI CLI, model gpt-5.4-mini. User has flat-rate $20/month OpenAI subscription — effectively free.
Command: `codex exec -m "gpt-5.4-mini" --dangerously-bypass-approvals-and-sandbox -s danger-full-access "YOUR PROMPT"`

Fallback worker (when codex is rate-limited): DeepSeek v4 flash via opencode. Costs real OpenRouter credits — only use when necessary.
Command: `~/.opencode/bin/opencode run -m "openrouter/deepseek/deepseek-v4-flash" --dangerously-skip-permissions "YOUR PROMPT"`

Read skills/use_worker.md, skills/worker_codex.md, and skills/worker_deepseek.md before dispatching work.

Worker receipt must include: named files processed, last ledger line read directly from the file, node/record count from actual output, files remaining.

**Why:** Bulk file I/O consumes significant Claude Code tokens; workers do it cheaply and correctly.

**How to apply:** Any task touching more than ~5 corpus files goes to a worker. Never do bulk corpus work inline.

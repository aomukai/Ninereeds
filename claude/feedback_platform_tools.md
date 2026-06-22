---
name: Tool index and platform rules
description: opencode is Linux-only; direct OpenRouter API runners work on Windows and Linux; CLAUDE.md is the authoritative tool index
type: feedback
originSessionId: fda6aad1-4831-426b-a6b5-1b5eb95bc0ab
---
On Windows, opencode CLI does not exist. Do not attempt to use it or call scripts that depend on it.

**Why:** opencode installs to `~/.opencode/bin/opencode` on Linux. On Windows the npm shim exists but headless operation fails. Attempting to use it costs time and fails silently or with encoding errors.

**How to apply:**
- On Windows: use `meta/repair_formatting_opencode.py` (now patched to direct API) or `skills/worker_repair.py`
- On Linux: opencode scripts in `meta/scripts/` are available, but direct API runners also work there
- Auth: set `OPENROUTER_API_KEY` env var — works on both platforms
- When waking up fresh, read `CLAUDE.md` in the repo root — it has the full tool index, platform split, active queue status, and resume commands

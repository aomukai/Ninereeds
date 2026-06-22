---
name: feedback-memory-location
description: All memories go to claude/ inside the repo — same physical disk on both OSes, no syncing needed
metadata:
  type: feedback
---

Save all memory files to `claude/<file>.md` inside the repo. Update `claude/MEMORY.md` as the index.

Do NOT write to the platform-local `~/.claude/projects/<slug>/memory/` path — it diverges between OSes and is irrelevant now.

**Why:** Both Windows and Linux mount the same physical directory (`D:\Ninereeds` / `/mnt/d/Ninereeds`). `claude/` is gitignored but physically shared, so it's always current on both platforms without any syncing.

**How to apply:** Any memory write goes to `claude/` only. On session start, read `claude/MEMORY.md` as the authoritative index.

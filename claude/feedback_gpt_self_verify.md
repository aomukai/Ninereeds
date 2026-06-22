---
name: GPT executor self-verification step
description: Always add a re-read/verify step to GPT executor prompts for rewrite tasks
type: feedback
originSessionId: f214e64f-85e7-459c-96c1-d360ca2cd70b
---
After GPT finishes writing a file, it sometimes produces errors it would catch if it re-read the output: missing subject prefixes in body lines, base verb instead of gerund, truncated question lines, etc.

**Why:** GPT (gpt-5.4-mini) was sloppy on verb rewrites — produced files with empty Q1 lines (`[user]what is `), orphan body lines missing subjects (`pushing back against pressure.` instead of `Resisting is pushing back...`), and used base verb form instead of gerund throughout.

**How to apply:** Whenever writing an executor prompt for a rewrite or generation task (not just a template patch), add a self-check step at the end of the task, before writing each file:

  "After writing each file, re-read it and verify:
   - Every [user] question line contains the full word (not truncated)
   - Every [Ninereeds] body line starts with the correct subject
   - The gerund/target word appears consistently throughout
   - No blank or orphan lines in [Ninereeds] blocks
   Fix any issues before moving to the next file."

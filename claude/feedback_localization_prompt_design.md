---
name: feedback-localization-prompt-design
description: "Localization prompts must say \"localize naturally\" not \"translate\" — literal translation produces systematic calques in JP/ZH"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f86256f4-a5c7-42f5-82ac-e80061cc1e4a
---

Always use "localize naturally" (never "translate") in any prompt that produces JP or ZH corpus content.

**Why:** The phase localization run before 2026-05-28 used a "translate" framing and produced systematic calques throughout all 5806 JP phase files — inanimate objects using human action verbs (持つ, 座る, 着地する), word-for-word structural copies of English phrases. The audit flagged ~99% of JP phase files as having critical issues. The fix required a full repair pass.

**How to apply:**
- Any new localization script or prompt must include the "localize naturally" directive
- Include anti-calque examples in the system prompt for JP and ZH (e.g. "don't use 持つ for inanimate features — use がある instead")
- The fixed `localize_phases.py` prompt (post 2026-05-28) is the reference — copy its naturalness guidance into new scripts
- The wiki localization (planned Thu 2026-05-29 overnight) must use this principle from the start
- Core rule: **preserve the meaning, not the wording**

from pathlib import Path
import re

BASE = Path("training_data/phases")
issues = []
for p in sorted(BASE.rglob("phase_*.md")):
    text = p.read_text("utf-8")
    rel = str(p.relative_to(BASE.parent.parent))
    if "=== END ===" in text:
        issues.append("ENDMARKER: " + rel)
    if "ROUTING DONE" in text:
        issues.append("ROUTING: " + rel)
    if re.search(r"^`{3}\s*$", text, re.MULTILINE):
        issues.append("FENCE: " + rel)
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s == "[Ninereeds]" and i + 1 < len(lines) and lines[i + 1].strip() == "":
            issues.append("BLANK_NIN: " + rel)
            break
    uc = len(re.findall(r"^\[user\]", text, re.MULTILINE))
    nc = len(re.findall(r"^\[Ninereeds\]", text, re.MULTILINE))
    if uc != nc:
        issues.append("TAG_MISMATCH: " + rel + " u=" + str(uc) + " n=" + str(nc))
    blocks = re.split(r"\n\s*\n", text.strip())
    bc = sum(1 for b in blocks if b.startswith("[user]"))
    if bc != 4:
        issues.append("BLOCK_COUNT: " + rel + " has " + str(bc))
if not issues:
    print("ALL CLEAN")
else:
    for i in issues:
        print(i)

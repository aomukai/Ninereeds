from pathlib import Path
import re

BASE = Path(__file__).resolve().parent.parent
PHASES = BASE / "training_data" / "phases"

issues = []
for p in sorted(PHASES.rglob("phase_*.md")):
    text = p.read_text("utf-8")
    rel = p.relative_to(BASE)
    name = p.name

    if "=== END ===" in text:
        issues.append(f"ENDMARKER: {name}")
    if "ROUTING DONE" in text:
        issues.append(f"ROUTING: {name}")
    if re.search(r"^```\s*$", text, re.MULTILINE):
        issues.append(f"FENCE: {name}")

    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if ln.strip() == "[Ninereeds]" and i + 1 < len(lines) and lines[i + 1].strip() == "":
            issues.append(f"BLANK_NIN: {name}")
            break

    # Count blocks
    user_count = len(re.findall(r"^\[user\]", text, re.MULTILINE))
    nin_count = len(re.findall(r"^\[Ninereeds\]", text, re.MULTILINE))
    if user_count != nin_count:
        issues.append(f"TAG_MISMATCH: {name} u={user_count} n={nin_count}")

if not issues:
    print("ALL CLEAN - no issues found")
else:
    for i in issues:
        print(i)
    print(f"\nTotal: {len(issues)}")

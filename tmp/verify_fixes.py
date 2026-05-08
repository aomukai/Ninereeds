from pathlib import Path

def verify_file(path_str):
    f = Path(path_str)
    if not f.exists():
        return ["FILE NOT FOUND"]
    content = f.read_text(encoding="utf-8")
    issues = []
    
    if "[user]" not in content or "[Ninereeds]" not in content:
        return ["missing [user]/[Ninereeds] tags"]
    
    if "```" in content:
        issues.append("stray code fence")
    
    lines = content.splitlines()
    blocks = []
    cur = []
    for line in lines:
        if not line.strip():
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(line)
    if cur:
        blocks.append(cur)
    
    is_phase4 = "phase_4" in path_str
    if is_phase4:
        if len(blocks) not in [1, 2]:
            issues.append("phase4: expected 1-2 blocks, got " + str(len(blocks)))
    elif len(blocks) != 4:
        issues.append("expected 4 blocks, got " + str(len(blocks)))
    
    for i, block in enumerate(blocks):
        if len(block) < 2:
            issues.append("b" + str(i+1) + ": too short")
            continue
        if not block[0].startswith("[user]"):
            issues.append("b" + str(i+1) + ": no [user] first line")
        if not block[1].startswith("[Ninereeds]"):
            issues.append("b" + str(i+1) + ": no [Ninereeds] second line")
        else:
            nr = block[1]
            has_opener = ("This is" in nr) or ("is here" in nr) or ("describes something" in nr)
            if not has_opener:
                issues.append("b" + str(i+1) + ": bad opener: " + repr(nr[:60]))
        for j, line in enumerate(block[2:], 3):
            if line.startswith("[user]") or line.startswith("[Ninereeds]"):
                issues.append("b" + str(i+1) + " line " + str(j) + ": nested tag")
    
    return issues

targets = [
    "training_data/phases/phase_1/phase_1_1247.md",
    "training_data/phases/phase_6/phase_6_488.md",
    "training_data/phases/phase_6/phase_6_697.md",
    "training_data/phases/phase_6/phase_6_888.md",
    "training_data/phases/phase_5/phase_5_1993.md",
    "training_data/phases/phase_5/phase_5_1994.md",
]

all_clean = True
for fp in targets:
    issues = verify_file(fp)
    if issues:
        all_clean = False
        print("ISSUES:", fp)
        for i in issues:
            print("  -", i)
    else:
        f = Path(fp)
        c = f.read_text(encoding="utf-8")
        body_lines = [l for l in c.splitlines() if l.strip()]
        tags = [l for l in body_lines if l.strip().startswith("[user]") or l.strip().startswith("[Ninereeds]")]
        print("OK:", fp, "(" + str(len(body_lines)) + " content lines,", str(len(tags)) + " tags)")

if all_clean:
    print()
    print("ALL 6 FILES VERIFIED CLEAN")

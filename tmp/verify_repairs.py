import subprocess, re, sys
from pathlib import Path

REPO = Path("D:/Ninereeds")

def verify_rewrite(path_str, content):
    errors = []
    if "[user]" not in content or "[Ninereeds]" not in content:
        errors.append("missing required tags")
    if "```" in content:
        errors.append("stray code fence")
    if len(content.strip()) < 40:
        errors.append("content too short")

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
    if not blocks:
        errors.append("no content blocks")

    for bi, block in enumerate(blocks, 1):
        if len(block) < 3:
            errors.append(f"block {bi} too short ({len(block)} lines)")
            continue
        if not block[0].startswith("[user]"):
            errors.append(f"block {bi} missing [user]")
        if not block[1].startswith("[Ninereeds]"):
            errors.append(f"block {bi} missing [Ninereeds]")
    return errors


result = subprocess.run(["git", "diff", "--name-only"], capture_output=True, text=True, cwd=REPO)
modified = [m.strip() for m in result.stdout.splitlines() if m.strip().endswith(".md")]

bad_files = []
for path in modified:
    full_path = REPO / path
    try:
        content = full_path.read_text(encoding="utf-8")
    except Exception as e:
        bad_files.append((path, [str(e)]))
        continue
    errors = verify_rewrite(path, content)
    if errors:
        bad_files.append((path, errors))

if bad_files:
    print(f"FILES WITH ISSUES: {len(bad_files)}")
    for path, errors in bad_files:
        print(f"  {path}: {errors}")
    sys.exit(1)
else:
    print(f"All {len(modified)} modified files pass verify_rewrite checks")

content = open("training_data/phases/phase_4/phase_4_12.md").read()
lines = content.splitlines()
assert "[user]" in content and "[Ninereeds]" in content
assert "```" not in content
assert len(content.strip()) >= 40
blocks = []; cur = []
for line in lines:
    if not line.strip():
        if cur: blocks.append(cur); cur = []
    else: cur.append(line)
if cur: blocks.append(cur)
assert len(blocks) >= 1
for bi, block in enumerate(blocks, 1):
    assert len(block) >= 3
    assert block[0].startswith("[user]")
    assert block[1].startswith("[Ninereeds]")
    assert block[1].count(".") == 1
    for line in block[2:]:
        assert not line.startswith("[user]") and not line.startswith("[Ninereeds]")
        assert line.count(".") == 1
print("ALL CHECKS PASSED")
print(f"Blocks: {len(blocks)}, Lines: {len(lines)}")
for bi, block in enumerate(blocks, 1):
    print(f"  Block {bi}: {len(block)} lines, opener: {block[0][:50]}...")

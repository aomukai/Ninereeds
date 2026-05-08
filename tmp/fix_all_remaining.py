from pathlib import Path

REPO = Path(r"D:\Ninereeds")

TRAILING_VERBS = sorted([
    " happen", " look like", " mean", " do", " give", " bring", " for",
    " used for", " made of", " look", " feel", " sound", " describe",
    " taste", " smell", " called", " known as", " appear",
], key=len, reverse=True)

def extract_concept(question):
    q = question.replace("[user]", "").strip().rstrip("?")
    prefixes = [
        "what is ", "what does ", "what are ", "what do ",
        "when does ", "when is ", "where can you find ", "where is ",
        "where does ",
    ]
    for p in prefixes:
        if q.lower().startswith(p):
            q = q[len(p):].strip()
            break

    for tv in TRAILING_VERBS:
        if q.lower().endswith(tv):
            q = q[:-len(tv)].strip()
            break
    return q

def fix_file(path_str):
    path = REPO / path_str
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

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

    changed = 0
    for bi, block in enumerate(blocks):
        if not block or not block[0].strip().startswith("[user]"):
            continue

        concept = extract_concept(block[0])
        if not concept:
            continue

        concept_lower = concept.lower()
        concept_cap = concept[0].upper() + concept[1:]

        nin_idx = None
        nin_text = None
        for i, line in enumerate(block):
            s = line.strip()
            if s.startswith("[Ninereeds]"):
                nin_idx = i
                nin_text = s[len("[Ninereeds]"):].strip()
                break

        if nin_idx is None:
            continue

        # If already has correct anchor, skip
        after_this = nin_text
        for prefix in ["This is ", "this is "]:
            if after_this.startswith(prefix):
                after_this = after_this[len(prefix):].strip().rstrip(".")
                break
        if after_this.lower() == concept_lower:
            continue

        new_block = [block[0]]
        new_block.append(f"[Ninereeds]This is {concept_lower}.")

        body = [nin_text]
        for line in block[nin_idx+1:]:
            s = line.strip()
            if s.startswith("[Ninereeds]"):
                s = s[len("[Ninereeds]"):].strip()
            if s:
                body.append(s)

        cleaned = []
        for bt in body:
            if not bt:
                continue
            words = bt.split()
            if words and words[0].lower() == concept_lower:
                words[0] = concept_cap
            cleaned.append(" ".join(words))

        if len(cleaned) >= 6:
            body_lines = cleaned[:5]
            summary = cleaned[-1]
        elif len(cleaned) >= 2:
            body_lines = cleaned[:-1]
            summary = cleaned[-1]
        elif len(cleaned) == 1:
            body_lines = cleaned
            summary = cleaned[-1]
        else:
            body_lines = []
            summary = ""

        new_block.extend(body_lines)
        if summary:
            new_block.append(summary)
        blocks[bi] = new_block
        changed += 1

    if changed:
        result = "\n\n".join("\n".join(b) for b in blocks)
        path.write_text(result, encoding="utf-8")
        print(f"  FIXED {path_str}: {changed} block(s)")
    return changed


files = [
    "training_data/phases/phase_4/phase_4_087.md",
    "training_data/phases/phase_6/phase_6_1026.md",
    "training_data/phases/phase_6/phase_6_1028.md",
    "training_data/phases/phase_6/phase_6_1033.md",
    "training_data/phases/phase_6/phase_6_1035.md",
    "training_data/phases/phase_6/phase_6_1056.md",
    "training_data/phases/phase_6/phase_6_1061.md",
    "training_data/phases/phase_6/phase_6_1067.md",
    "training_data/phases/phase_6/phase_6_1068.md",
    "training_data/phases/phase_6/phase_6_1071.md",
    "training_data/phases/phase_6/phase_6_1075.md",
    "training_data/phases/phase_6/phase_6_298.md",
    "training_data/phases/phase_6/phase_6_42.md",
    "training_data/phases/phase_6/phase_6_497.md",
    "training_data/phases/phase_6/phase_6_54.md",
    "training_data/phases/phase_6/phase_6_579.md",
    "training_data/phases/phase_6/phase_6_588.md",
    "training_data/phases/phase_6/phase_6_70.md",
    "training_data/phases/phase_6/phase_6_704.md",
    "training_data/phases/phase_6/phase_6_71.md",
    "training_data/phases/phase_6/phase_6_711.md",
]

total = 0
for f in files:
    total += fix_file(f)
print(f"\nTotal: {total} blocks fixed")

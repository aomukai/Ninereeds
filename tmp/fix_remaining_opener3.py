from pathlib import Path

REPO = Path(r"D:\Ninereeds")

TRAILING_VERBS = [
    " happen", " look like", " mean", " do", " give", " bring", " for",
    " used for", " made of", " made from", " look", " feel", " sound",
    " taste", " smell", " called", " known as",
]

def extract_concept_from_question(question: str) -> str:
    q = question.replace("[user]", "").strip().rstrip("?")
    prefixes = [
        "what is ", "what does ", "what are ", "what do ",
        "when does ", "where can you find ", "where is ",
        "when is ",
    ]
    concept = q
    for p in prefixes:
        if q.lower().startswith(p):
            concept = q[len(p):].strip()
            break

    concept_lower = concept.lower()
    for tv in sorted(TRAILING_VERBS, key=len, reverse=True):
        if concept_lower.endswith(tv):
            concept = concept[:-len(tv)].strip()
            break

    return concept

def fix_file(path_str: str) -> int:
    path = REPO / path_str
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    blocks = []
    current = []
    for line in lines:
        if not line.strip():
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(line)
    if current:
        blocks.append(current)

    fixed_count = 0

    for bi, block in enumerate(blocks):
        if not block:
            continue

        first = block[0].strip()
        if not first.startswith("[user]"):
            continue

        ninereeds_idx = None
        for i, line in enumerate(block):
            s = line.strip()
            if s.startswith("[Ninereeds]"):
                ninereeds_idx = i
                break

        if ninereeds_idx is None:
            continue

        ninereeds_line = block[ninereeds_idx]
        ninereeds_text = ninereeds_line[len("[Ninereeds]"):].strip()

        concept = extract_concept_from_question(first)
        if not concept:
            continue

        concept_cap = concept[0].upper() + concept[1:] if concept else ""
        concept_lower = concept.lower()

        # Check if the "This is" anchor is wrong (has extra words)
        needs_fix = False
        if ninereeds_text.startswith("This is") or ninereeds_text.startswith("this is"):
            # Extract what comes after "This is"
            after_this = ninereeds_text
            for prefix in ["This is ", "this is ", "This is", "this is"]:
                if after_this.startswith(prefix):
                    after_this = after_this[len(prefix):].strip().rstrip(".")
                    break
            if after_this.lower() != concept_lower:
                needs_fix = True
                print(f"    anchor '{after_this}' != concept '{concept_lower}' -> fixing")
        elif not (ninereeds_text.startswith("This is") or ninereeds_text.startswith("this is")):
            needs_fix = True

        if not needs_fix:
            continue

        new_block = [block[0]]
        new_block.append(f"[Ninereeds]This is {concept_lower}.")

        body_lines = []
        for i, line in enumerate(block[1:], 1):
            s = line.strip()
            if i - 1 == 0:
                body_lines.append(ninereeds_text)
            else:
                if s.startswith("[Ninereeds]"):
                    s = s[len("[Ninereeds]"):].strip()
                if s.startswith("[user]"):
                    continue
                body_lines.append(s)

        body_lines = [b for b in body_lines if b]

        cleaned_body = []
        for bt in body_lines:
            bt = bt.strip()
            if not bt:
                continue
            words = bt.split()
            if words:
                first_word = words[0]
                if first_word.lower() == concept_lower:
                    words[0] = concept_cap
                cleaned_body.append(" ".join(words))
            else:
                cleaned_body.append(bt)

        if len(cleaned_body) >= 6:
            body = cleaned_body[:5]
            summary = cleaned_body[-1]
        elif len(cleaned_body) >= 2:
            body = cleaned_body[:-1]
            summary = cleaned_body[-1]
        else:
            body = cleaned_body
            summary = cleaned_body[-1] if cleaned_body else ""

        for b in body:
            new_block.append(b)
        new_block.append(summary)

        blocks[bi] = new_block
        fixed_count += 1

    if fixed_count > 0:
        result = "\n\n".join("\n".join(b) for b in blocks)
        path.write_text(result, encoding="utf-8")
        print(f"  FIXED {path_str}: {fixed_count} block(s)")

    return fixed_count


files_to_fix = [
    "training_data/phases/phase_3/phase_3_237.md",
    "training_data/phases/phase_3/phase_3_238.md",
    "training_data/phases/phase_3/phase_3_239.md",
    "training_data/phases/phase_3/phase_3_250.md",
    "training_data/phases/phase_3/phase_3_252.md",
    "training_data/phases/phase_3/phase_3_253.md",
    "training_data/phases/phase_3/phase_3_255.md",
    "training_data/phases/phase_3/phase_3_260.md",
    "training_data/phases/phase_3/phase_3_293.md",
    "training_data/phases/phase_3/phase_3_304.md",
    "training_data/phases/phase_3/phase_3_316.md",
    "training_data/phases/phase_3/phase_3_319.md",
    "training_data/phases/phase_3/phase_3_322.md",
    "training_data/phases/phase_5/phase_5_46.md",
    "training_data/phases/phase_5/phase_5_1893.md",
    "training_data/phases/phase_5/phase_5_1971.md",
    "training_data/phases/phase_5/phase_5_1976.md",
]

total = 0
for f in files_to_fix:
    count = fix_file(f)
    total += count

print(f"\nTotal blocks fixed: {total}")

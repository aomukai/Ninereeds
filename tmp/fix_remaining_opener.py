from pathlib import Path

REPO = Path(r"D:\Ninereeds")

def extract_concept_from_question(question: str) -> str:
    q = question.replace("[user]", "").strip().rstrip("?")
    prefixes = [
        "what is ", "what does ", "what are ", "what do ",
        "when does ", "where can you find ", "where is ",
    ]
    for p in prefixes:
        if q.lower().startswith(p):
            return q[len(p):].strip()
    return q.strip()

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

        # Must start with [user]
        first = block[0].strip()
        if not first.startswith("[user]"):
            continue

        # Must have a [Ninereeds] line
        ninereeds_idx = None
        ninereeds_text = None
        for i, line in enumerate(block):
            s = line.strip()
            if s.startswith("[Ninereeds]"):
                ninereeds_idx = i
                ninereeds_text = s[len("[Ninereeds]"):].strip()
                break

        if ninereeds_idx is None:
            continue

        # If already has "This is" opener, skip
        if ninereeds_text.startswith("This is") or ninereeds_text.startswith("this is"):
            continue

        # Extract concept
        concept = extract_concept_from_question(first)
        if not concept:
            continue

        concept_cap = concept[0].upper() + concept[1:] if concept else ""
        concept_lower = concept.lower()

        # Build new block
        new_block = [block[0]]  # [user] line

        # New [Ninereeds] with "This is" opener
        new_block.append(f"[Ninereeds]This is {concept_lower}.")

        # Old ninereeds text becomes first body line
        # Strip any leading redundant "[Ninereeds]" from body lines
        body_lines = []
        for i, line in enumerate(block[1:], 1):
            s = line.strip()
            if i - 1 == 0:
                # This was the [Ninereeds] line - use its text as body
                # Keep the old content (already extracted as ninereeds_text)
                body_lines.append(ninereeds_text)
            else:
                # Check if this line starts with [Ninereeds] and strip it
                if s.startswith("[Ninereeds]"):
                    s = s[len("[Ninereeds]"):].strip()
                # Also check for "[user]" which shouldn't be here
                if s.startswith("[user]"):
                    continue  # shouldn't happen but safety
                body_lines.append(s)

        # Filter empty body lines
        body_lines = [b for b in body_lines if b]

        # Ensure proper capitalization: each body line should start with concept_cap
        cleaned_body = []
        for bt in body_lines:
            bt = bt.strip()
            if not bt:
                continue
            words = bt.split()
            if words:
                first_word = words[0]
                # If the first word is the concept (lowercase), capitalize it
                if first_word.lower() == concept_lower:
                    words[0] = concept_cap
                elif first_word.lower().startswith(concept_lower) and len(first_word) > len(concept_lower) and first_word[len(concept_lower)] == 's':
                    # "Parentings" -> "Parenting" mis-capitalization
                    pass  # Keep as-is, it's a plural form
                cleaned_body.append(" ".join(words))
            else:
                cleaned_body.append(bt)

        # Split into 5 body + 1 summary (or keep as-is if we have fewer)
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

# Now handle phase_3_61.md separately (completely broken format)
p61 = REPO / "training_data/phases/phase_3/phase_3_61.md"
if p61.exists():
    text61 = p61.read_text(encoding="utf-8")
    # Replace the broken 4-line format with proper 4-block format
    new61 = """[user]What does gradual mean?
[Ninereeds]This is gradual.
A gradual thing changes slowly.
A gradual thing is not sudden.
A gradual thing moves step by step.
A gradual thing takes time.
A gradual thing builds over time.
A gradual thing is slow and steady.

[user]Where can you find gradual?
[Ninereeds]This is gradual.
Gradual is in a sunrise.
Gradual is on a slope.
Gradual is in a growing plant.
Gradual is in an aging tree.
Gradual is in a changing season.
Gradual is in a sunrise and on a slope.

[user]What does gradual do?
[Ninereeds]This is gradual.
Gradual spreads a change over time.
Gradual makes a shift feel gentle.
Gradual lets a thing adjust.
Gradual builds a result step by step.
Gradual prevents a sudden shock.
Gradual spreads change and prevents shock.

[user]What is gradual for?
[Ninereeds]This is gradual.
Gradual is for slow change.
Gradual is for gentle transition.
Gradual is for steady growth.
Gradual is for careful adjustment.
Gradual is for safe progress.
Gradual is for slow change and safe progress."""
    p61.write_text(new61, encoding="utf-8")
    print("  FIXED phase_3_61.md (complete rewrite)")
    total += 4

print(f"\nTotal: {total}")

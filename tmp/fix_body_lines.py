"""Add 5th body line to each block of 31-line phase training files."""
import os

additions = {
    'training_data/phases/phase_1/phase_1_126.md': (
        'Corn has yellow kernels.',
        'Corn grows in soil.',
        'Corn is watered by rain.',
        'Corn is ground into cornmeal.',
    ),
    'training_data/phases/phase_1/phase_1_653.md': (
        'A mask has strings to tie.',
        'A mask is on a face.',
        'A mask protects the mouth.',
        'A mask is for a nurse.',
    ),
    'training_data/phases/phase_1/phase_1_660.md': (
        'Metal is strong.',
        'Metal is in a tool.',
        'Metal bends under heat.',
        'Metal is for making wires.',
    ),
    'training_data/phases/phase_1/phase_1_643.md': (
        'Lotion has a smell.',
        'Lotion is on a sink.',
        'Lotion rubs into skin.',
        'Lotion is for soft skin.',
    ),
    'training_data/phases/phase_1/phase_1_641.md': (
        'A lollipop is hard.',
        'A lollipop is in a store.',
        'A lollipop lasts a long time.',
        'A lollipop is for a happy moment.',
    ),
    'training_data/phases/phase_1/phase_1_663.md': (
        'A microscope has a light.',
        'A microscope is in a classroom.',
        'A microscope helps a scientist.',
        'A microscope is for exploring tiny worlds.',
    ),
    'training_data/phases/phase_1/phase_1_670.md': (
        'A mitten is soft.',
        'A mitten is on a shelf.',
        'A mitten traps the warm air.',
        'A mitten is for a child.',
    ),
    'training_data/phases/phase_1/phase_1_668.md': (
        'Mist is soft.',
        'Mist is over a lake.',
        'Mist fades in the sun.',
        'Mist is for a cool morning.',
    ),
    'training_data/phases/phase_1/phase_1_671.md': (
        'Mold looks like fuzz.',
        'Mold is on old food.',
        'Mold spreads in warmth.',
        'Mold is for breaking things down.',
    ),
    'training_data/phases/phase_1/phase_1_666.md': (
        'Mint has a strong smell.',
        'Mint is in a sunny spot.',
        'Mint grows back each year.',
        'Mint is for a fresh taste.',
    ),
    'training_data/phases/phase_6/phase_6_58.md': (
        'link can be a hyperlink on a screen.',
        'link can be in a document.',
        'link can take a person to a new topic.',
        'link can look like a word a person clicks.',
    ),
    'training_data/phases/phase_6/phase_6_56.md': (
        'life can be found in a garden.',
        'life can be in a desert.',
        'life can adapt to new spaces.',
        'life can look fragile or strong.',
    ),
    'training_data/phases/phase_6/phase_6_53.md': (
        'letter can be at the end of a word.',
        'letter can be on a keyboard.',
        'letter can start a sentence.',
        'letter can look different in a name.',
    ),
    'training_data/phases/phase_6/phase_6_643.md': (
        'Behavior is a pattern of actions.',
        'Behavior is in homes.',
        'Behavior shows habits.',
        'Behavior is for repeating actions.',
    ),
    'training_data/phases/phase_6/phase_6_70.md': (
        'Matter can be a liquid.',
        'Matter can be in a tree.',
        'Matter can be a solid.',
        'Matter can look heavy or light.',
    ),
    'training_data/phases/phase_1/phase_1_664.md': (
        'Milk is cold.',
        'Milk is in a bottle.',
        'Milk helps the body grow.',
        'Milk is for a healthy body.',
    ),
    'training_data/phases/phase_6/phase_6_1046.md': (
        'Threeness is a property of number nine.',
        'Threeness appears in clock faces.',
        'Threeness groups items into sets of three.',
        'Threeness is for counting in groups.',
    ),
}

def fix_31line_file(filepath, adjs):
    with open(filepath, encoding='utf-8') as f:
        lines = [l.rstrip('\n') for l in f.readlines()]

    orig_len = len(lines)
    if orig_len >= 35:
        return False

    # For 31-line files, block structure is:
    # Block N starts at (N-1)*8, has 7 lines + 1 blank
    # Body4 is at block_start + 5
    body4_indices = [5, 13, 21, 29]

    block_idx = 0
    new_lines = []
    for i, line in enumerate(lines):
        new_lines.append(line)
        if block_idx < 4 and i == body4_indices[block_idx]:
            new_lines.append(adjs[block_idx])
            block_idx += 1

    with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
        for line in new_lines:
            f.write(line + '\n')

    print(f"{filepath}: {orig_len} -> {len(new_lines)} lines")
    return True


fixed_count = 0
for filepath, adjs in sorted(additions.items()):
    if not os.path.exists(filepath):
        print(f"NOT FOUND: {filepath}")
        continue
    if fix_31line_file(filepath, adjs):
        fixed_count += 1

print(f"\nFixed {fixed_count} files")

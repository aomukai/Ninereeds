#!/usr/bin/env python3
"""
Split wiki files into single-concept output files.

Rules:
  - wiki_1 and wiki_2/3/4 files WITHOUT ## sections:
      one [user]/[Ninereeds] pair per output file
  - wiki_2/3/4 files WITH ## sections:
      one ## section (all pairs within it) per output file

Output tree:
  training_data/wiki_split/wiki_N/topic/NNN_concept/EN.md

Validation: after splitting, [user] and [Ninereeds] counts must
match the source exactly.

Usage:
  python3 meta/scripts/split_wiki.py [--dry-run] [--level 1|2|3|4]
"""

import argparse
import re
import sys
from pathlib import Path

WIKI_ROOT = Path("training_data/wiki")
SPLIT_ROOT = Path("training_data/wiki_split")

WIKI_LEVELS = ["wiki_1", "wiki_2", "wiki_3", "wiki_4"]


# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    text = text.lower().strip().rstrip("?.")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    text = re.sub(r"^_+|_+$", "", text)
    return text[:64]


STRIP_PREFIXES = [
    r"^what is an? ",
    r"^what is the ",
    r"^what is ",
    r"^what does it mean to ",
    r"^what does ",
    r"^what are ",
    r"^how does ",
    r"^how do ",
    r"^how is ",
    r"^how are ",
    r"^why does ",
    r"^why do ",
    r"^why is ",
    r"^why are ",
    r"^can ",
    r"^do ",
    r"^does ",
    r"^is ",
    r"^are ",
]


def concept_from_question(question: str) -> str:
    """Derive a short concept slug from a [user] question line."""
    q = question.strip().rstrip("?.")
    for pattern in STRIP_PREFIXES:
        q = re.sub(pattern, "", q, flags=re.I)
    return slugify(q) or slugify(question)


def topic_from_filename(name: str) -> str:
    """Derive topic slug from a wiki source filename (no extension)."""
    for suffix in ("_entries", "_level2", "_level3", "_level4"):
        name = name.replace(suffix, "")
    return slugify(name)


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_pairs(text: str) -> list[str]:
    """
    Return a list of [user]/[Ninereeds] block strings,
    each starting with [user] and ending before the next [user].
    """
    blocks = re.split(r"(?=^\[user\])", text, flags=re.MULTILINE)
    out = []
    for block in blocks:
        block = block.strip()
        if "[user]" in block and "[Ninereeds]" in block:
            out.append(block)
    return out


def parse_sections(text: str) -> list[tuple[str, str]]:
    """
    Split on ## headings. Return list of (heading_text, content).
    content contains only the [user]/[Ninereeds] pairs, stripped of
    the heading line itself.
    """
    parts = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    out = []
    for part in parts:
        part = part.strip()
        if not part.startswith("## "):
            continue
        heading_match = re.match(r"^## (.+)$", part, re.MULTILINE)
        if not heading_match:
            continue
        heading = heading_match.group(1).strip()
        # Content = everything from first [user] onward
        first_user = part.find("[user]")
        if first_user == -1:
            continue
        content = part[first_user:].strip()
        if "[Ninereeds]" not in content:
            continue
        out.append((heading, content))
    return out


# ---------------------------------------------------------------------------
# Split one source file → list of (slug, content)
# ---------------------------------------------------------------------------

def split_file(path: Path) -> list[tuple[str, str]]:
    """
    Return list of (concept_slug, file_content) tuples for a wiki source file.
    Strategy is chosen based on whether ## sections are present.
    """
    text = path.read_text(encoding="utf-8")

    if re.search(r"^## ", text, re.MULTILINE):
        # Section-based split
        sections = parse_sections(text)
        return [(slugify(heading), content) for heading, content in sections]
    else:
        # Pair-based split (one pair per file)
        pairs = parse_pairs(text)
        results = []
        for pair in pairs:
            user_match = re.match(r"\[user\](.*?)$", pair, re.MULTILINE)
            question = user_match.group(1).strip() if user_match else ""
            concept = concept_from_question(question)
            results.append((concept, pair))
        return results


# ---------------------------------------------------------------------------
# Write output files
# ---------------------------------------------------------------------------

def write_split(level: str, topic: str, entries: list[tuple[str, str]],
                dry_run: bool) -> int:
    """
    Write NNN_concept/EN.md files under SPLIT_ROOT/level/topic/.
    Returns number of files written.
    """
    written = 0
    seen_slugs: dict[str, int] = {}

    for i, (slug, content) in enumerate(entries, start=1):
        # Disambiguate duplicate slugs within a topic
        if slug in seen_slugs:
            seen_slugs[slug] += 1
            slug = f"{slug}_{seen_slugs[slug]:02d}"
        else:
            seen_slugs[slug] = 1

        folder_name = f"{i:03d}_{slug}"
        out_dir = SPLIT_ROOT / level / topic / folder_name
        out_file = out_dir / "EN.md"

        if dry_run:
            print(f"  WOULD WRITE {out_file}")
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file.write_text(content + "\n", encoding="utf-8")

        written += 1

    return written


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def count_tags(path: Path, tag: str) -> int:
    text = path.read_text(encoding="utf-8")
    return len(re.findall(rf"^\{tag}\]", text, re.MULTILINE))


def validate_level(level: str) -> bool:
    src_dir = WIKI_ROOT / level
    dst_dir = SPLIT_ROOT / level

    src_user = sum(
        count_tags(f, "[user") for f in src_dir.rglob("*.md")
    )
    src_ninereeds = sum(
        count_tags(f, "[Ninereeds") for f in src_dir.rglob("*.md")
    )

    dst_user = sum(
        count_tags(f, "[user") for f in dst_dir.rglob("EN.md")
    )
    dst_ninereeds = sum(
        count_tags(f, "[Ninereeds") for f in dst_dir.rglob("EN.md")
    )

    ok = (src_user == dst_user) and (src_ninereeds == dst_ninereeds)
    status = "OK" if ok else "MISMATCH"
    print(f"  [{status}] {level}: "
          f"[user] {src_user} → {dst_user}  "
          f"[Ninereeds] {src_ninereeds} → {dst_ninereeds}")
    return ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Split wiki files into concept files")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be written without writing")
    parser.add_argument("--level", choices=["1", "2", "3", "4"],
                        help="Only split this wiki level (default: all)")
    parser.add_argument("--validate-only", action="store_true",
                        help="Only run validation against existing split")
    args = parser.parse_args()

    levels = [f"wiki_{args.level}"] if args.level else WIKI_LEVELS

    if args.validate_only:
        print("Validating existing split...")
        all_ok = all(validate_level(lv) for lv in levels)
        sys.exit(0 if all_ok else 1)

    total_files = 0
    total_sources = 0

    for level in levels:
        src_dir = WIKI_ROOT / level
        if not src_dir.exists():
            print(f"Skipping {level} — source directory not found")
            continue

        print(f"\n{level}")
        level_files = 0

        for src_file in sorted(src_dir.glob("*.md")):
            topic = topic_from_filename(src_file.stem)
            entries = split_file(src_file)
            if not entries:
                print(f"  WARNING: no entries found in {src_file.name}")
                continue

            written = write_split(level, topic, entries, dry_run=args.dry_run)
            level_files += written
            total_sources += 1
            action = "would write" if args.dry_run else "wrote"
            print(f"  {src_file.name} → {written} files  [{topic}]")

        print(f"  subtotal: {level_files} output files from {total_sources} source files")
        total_files += level_files

    print(f"\nTotal output files: {total_files}")

    if not args.dry_run:
        print("\nValidation:")
        all_ok = all(validate_level(lv) for lv in levels)
        if all_ok:
            print("  All counts match — split is clean.")
        else:
            print("  COUNT MISMATCH — check the output above.")
            sys.exit(1)


if __name__ == "__main__":
    main()

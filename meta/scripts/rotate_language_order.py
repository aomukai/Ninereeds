#!/usr/bin/env python3
"""
Rotate the language block order within internal 4-language files.

Current order in all files: EN → DE → JP → ZH (English-first bias).
Target: rotate so each position is equally occupied across the corpus.

  File index % 4 == 0  →  EN DE JP ZH  (EDJC — no change)
  File index % 4 == 1  →  DE JP ZH EN  (DJCE)
  File index % 4 == 2  →  JP ZH EN DE  (JCED)
  File index % 4 == 3  →  ZH EN DE JP  (CEDJ)

Supported corpora:
  boolean_stories   training_data/01_language/boolean_stories/
  philosophy        training_data/05_philosophy/
  lang              training_data/01_language/lang/  (lang_1–5, all levels)
  lang_1 … lang_5   individual lang levels

Usage:
  python3 meta/scripts/rotate_language_order.py boolean_stories [--dry-run]
  python3 meta/scripts/rotate_language_order.py philosophy       [--dry-run]
  python3 meta/scripts/rotate_language_order.py lang             [--dry-run]
  python3 meta/scripts/rotate_language_order.py lang_1           [--dry-run]
  python3 meta/scripts/rotate_language_order.py all             [--dry-run]
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

LANG_ORDER = ["en", "de", "jp", "zh"]   # assumed current order

ROTATIONS = [
    ["en", "de", "jp", "zh"],   # index % 4 == 0  EDJC — no change
    ["de", "jp", "zh", "en"],   # index % 4 == 1  DJCE
    ["jp", "zh", "en", "de"],   # index % 4 == 2  JCED
    ["zh", "en", "de", "jp"],   # index % 4 == 3  CEDJ
]


# ---------------------------------------------------------------------------
# Language detection — used only for validation, not for splitting
# ---------------------------------------------------------------------------

def detect_lang(text: str) -> str:
    for c in text:
        if '぀' <= c <= 'ヿ':   # hiragana/katakana — exclusively Japanese
            return "jp"
    for c in text:
        if '一' <= c <= '鿿':   # CJK unified — Chinese when no kana present
            return "zh"
    if any(c in text for c in "äöüÄÖÜßàáâãèéêëìíîïñòóôõùúûÿ"):
        return "de"
    return "en"   # may be a false positive for plain-ASCII German; see positional note below


# ---------------------------------------------------------------------------
# Parsers — positional, not language-detection-based
# Splitting relies on blank lines between blocks; the current order
# EN/DE/JP/ZH is assumed (and optionally validated).
# ---------------------------------------------------------------------------

def _split_blank_lines(text: str) -> list[str]:
    """Split on one or more blank lines, returning non-empty chunks."""
    return [b.strip() for b in re.split(r"\n{2,}", text.strip()) if b.strip()]


def _user_tag_present(block: str) -> bool:
    return block.startswith("[user]") or block.startswith("[user] ")


def parse_boolean(text: str) -> tuple[list[str], str]:
    """Parse boolean_stories file into 4 language blocks.

    Returns (blocks, format_name). Each block is a string containing all
    [user]/[Ninereeds] pairs for one language.

    Three sub-formats:
      tagged   — explicit [EN]/[DE]/[JP]/[ZH] markers (3 files)
      plain_1  — 4 blank-separated pairs, 1 pair per language
      plain_4  — 8 blank-separated pairs, 2 pairs per language
    """
    text = text.replace("\r\n", "\n")

    # Tagged format: [EN] / [DE] / [JP] / [ZH] markers
    if re.search(r"(?m)^\[(EN|DE|JP|ZH|JA)\]$", text):
        lang_map = {"JA": "jp"}   # normalise JA → jp
        parts = re.split(r"(?m)^\[(EN|DE|JP|ZH|JA)\]$", text.strip())
        # parts: ['prefix', 'EN', content, 'DE', content, ...]
        # prefix may be the unmarked EN section (no [EN] marker in some files)
        blocks_by_lang: dict[str, str] = {}
        prefix = parts[0].strip()
        if prefix and ("[user]" in prefix or "[user] " in prefix):
            blocks_by_lang["en"] = prefix
        for i in range(1, len(parts), 2):
            lang = lang_map.get(parts[i], parts[i].lower())
            blocks_by_lang[lang] = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if set(blocks_by_lang) != {"en", "de", "jp", "zh"}:
            raise ValueError(f"Tagged format: unexpected language keys {set(blocks_by_lang)}")
        return [blocks_by_lang[l] for l in LANG_ORDER], "tagged"

    # Plain format: split on blank lines
    all_blocks = _split_blank_lines(text)

    # Check for narrative-prefixed variant: blocks that contain [user] but don't start with it
    # (each language section is: narrative sentence + 2 user/Ninereeds pairs, as one chunk)
    has_user = [("[user]" in b or "[user] " in b) for b in all_blocks]
    user_start = [_user_tag_present(b) for b in all_blocks]

    # Count blocks that START with [user]
    user_pairs = [b for b in all_blocks if _user_tag_present(b)]

    if len(user_pairs) == 4:
        return user_pairs, "plain_1"

    if len(user_pairs) == 8:
        # 2 pairs per language: group into 4 lang-blocks of 2
        lang_blocks = ["\n\n".join(user_pairs[i * 2 : i * 2 + 2]) for i in range(4)]
        return lang_blocks, "plain_4"

    # Narrative-prefixed: each language section is a block starting with a prose sentence,
    # followed by [user]/[Ninereeds] pairs — no [user] at block start.
    narrative_blocks = [b for b, h in zip(all_blocks, has_user) if h and not _user_tag_present(b)]
    if len(narrative_blocks) == 4:
        return narrative_blocks, "plain_4_narrative"

    # Also handle mixed: some plain_1 blocks but some narrative blocks
    total_user_containing = sum(1 for h in has_user if h)
    raise ValueError(
        f"Unexpected number of [user] blocks: starts_with={len(user_pairs)}, contains={total_user_containing}"
    )


def parse_lang(text: str) -> tuple[list[str], str]:
    """Parse a lang_1–5 file (4-line EN/DE/JP/ZH stanzas, blank-line separated).

    Returns (blocks, "lang_stanza") where blocks has 4 elements, one per language.
    Each block is all lines for that language across every stanza, joined by '\\n'.
    Positional assumption: line 0 = EN, 1 = DE, 2 = JP, 3 = ZH within each stanza.
    """
    text = text.replace("\r\n", "\n").strip()
    stanzas = [s.strip() for s in re.split(r"\n{2,}", text) if s.strip()]
    if not stanzas:
        raise ValueError("Empty file")

    stanza_lines: list[list[str]] = []   # stanza_lines[s][lang_idx] = line text
    for stanza in stanzas:
        lines = [l for l in stanza.split("\n") if l.strip()]
        if len(lines) != 4:
            raise ValueError(f"Stanza has {len(lines)} lines (expected 4): {stanza[:60]!r}")
        stanza_lines.append(lines)

    # Group by language position across all stanzas
    per_lang = []
    for lang_idx in range(4):
        per_lang.append("\n".join(s[lang_idx] for s in stanza_lines))

    return per_lang, "lang_stanza"


def parse_philosophy(text: str) -> tuple[list[str], str]:
    """Split philosophy file into 4 language blocks at [statement] boundaries."""
    text = text.replace("\r\n", "\n").strip()
    indices = [m.start() for m in re.finditer(r"(?m)^\[statement\]", text)]
    if len(indices) != 4:
        raise ValueError(f"Expected 4 [statement] blocks, found {len(indices)}")
    blocks = []
    for i, start in enumerate(indices):
        end = indices[i + 1] if i + 1 < len(indices) else len(text)
        blocks.append(text[start:end].rstrip("\n"))
    return blocks, "philosophy"


# ---------------------------------------------------------------------------
# Reassemble — mirror the original join style per format
# ---------------------------------------------------------------------------

def reassemble(blocks: list[str], fmt: str) -> str:
    if fmt == "tagged":
        langs = LANG_ORDER   # will be replaced by caller with target order
        # caller passes blocks already in target order; we re-add the markers
        # NOTE: the caller must pass (reordered_blocks, target_langs)
        raise RuntimeError("Use reassemble_tagged instead")

    sep = "\n\n"
    if fmt == "plain_4":
        # Each block already contains 2 pairs joined with \n\n; add \n\n between blocks
        return sep.join(blocks) + "\n"
    else:
        return sep.join(blocks) + "\n"


def reassemble_tagged(blocks: list[str], target_langs: list[str]) -> str:
    parts = []
    for lang, block in zip(target_langs, blocks):
        parts.append(f"[{lang.upper()}]\n{block}")
    return "\n\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Reorder + validate
# ---------------------------------------------------------------------------

def reorder_and_validate(
    blocks: list[str], target: list[str], fmt: str
) -> tuple[list[str], list[str]]:
    """Return (reordered_blocks, detected_langs).

    Uses positional assumption: current order is EN/DE/JP/ZH.
    Validates via language detection; warns but does not abort on mismatch.
    """
    detected = [detect_lang(b) for b in blocks]
    # Reorder: map position 0→en, 1→de, 2→jp, 3→zh
    pos = {lang: i for i, lang in enumerate(LANG_ORDER)}
    reordered = [blocks[pos[lang]] for lang in target]
    return reordered, detected


# ---------------------------------------------------------------------------
# File processor
# ---------------------------------------------------------------------------

def process_file(
    path: Path, index: int,
    parser,
    dry_run: bool,
) -> str:
    text = path.read_text(encoding="utf-8")

    try:
        blocks, fmt = parser(text)
    except ValueError as e:
        return f"FAIL (parse): {e}"

    target = ROTATIONS[index % 4]
    if target == LANG_ORDER:
        return "SKIP (EDJC — no change needed)"

    # Skip files already rotated (first block isn't EN)
    first_lang = detect_lang(blocks[0])
    if first_lang != "en":
        return f"SKIP (already rotated — leads with {first_lang.upper()})"

    try:
        reordered, detected = reorder_and_validate(blocks, target, fmt)
    except (ValueError, KeyError) as e:
        return f"FAIL (reorder): {e}"

    if fmt == "tagged":
        output = reassemble_tagged(reordered, target)
    elif fmt == "lang_stanza":
        # reordered[i] = all lines for target lang i, one per stanza, joined by \n
        # Re-interleave into stanzas: each stanza = one line per (new) language
        lines_by_lang = [block.split("\n") for block in reordered]
        n_stanzas = len(lines_by_lang[0])
        stanzas_out = []
        for s in range(n_stanzas):
            stanzas_out.append("\n".join(ll[s] for ll in lines_by_lang))
        output = "\n\n".join(stanzas_out) + "\n"
    else:
        output = "\n\n".join(reordered) + "\n"

    if not dry_run:
        path.write_text(output, encoding="utf-8")

    order_str = "→".join(l.upper() for l in target)
    warn = ""
    if detected != LANG_ORDER:
        warn = f"  [lang-detect mismatch: {detected}]"
    return f"OK ({fmt}, {order_str}){warn}"


# ---------------------------------------------------------------------------
# Corpus runners
# ---------------------------------------------------------------------------

def run_corpus(name: str, directory: Path, parser, dry_run: bool, recursive: bool = False) -> None:
    files = sorted(directory.rglob("*.md") if recursive else directory.glob("*.md"))
    if not files:
        print(f"  No .md files found in {directory}")
        return

    counts: dict[str, int] = {"ok": 0, "skip": 0, "fail": 0}
    warnings: list[str] = []
    fails: list[str] = []

    for idx, path in enumerate(files):
        status = process_file(path, idx, parser, dry_run)
        tag = status.split()[0]
        if tag == "OK":
            counts["ok"] += 1
            if "lang-detect mismatch" in status:
                warnings.append(f"  {path.name}: {status}")
        elif tag == "SKIP":
            counts["skip"] += 1
        else:
            counts["fail"] += 1
            fails.append(f"  {path.name}: {status}")

    for line in fails:
        print(line)
    if warnings:
        print(f"  [{len(warnings)} lang-detect warnings — positional reorder still applied]")

    print(
        f"  {name}: {counts['ok']} rotated, {counts['skip']} skipped, {counts['fail']} failed"
        f"  ({'dry-run' if dry_run else 'written'})"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

LANG_LEVELS = ["lang_1", "lang_2", "lang_3", "lang_4", "lang_5"]

CORPORA: dict[str, tuple] = {
    "boolean_stories": (
        ROOT / "training_data/01_language/boolean_stories",
        parse_boolean,
        False,  # not recursive
    ),
    "philosophy": (
        ROOT / "training_data/05_philosophy",
        parse_philosophy,
        False,
    ),
}
# Individual lang levels (recursive — files live in subdirectories)
for _level in LANG_LEVELS:
    CORPORA[_level] = (
        ROOT / f"training_data/01_language/lang/{_level}",
        parse_lang,
        True,
    )
# "lang" is handled as a multi-directory alias in main(); not a single directory entry


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus", choices=[*CORPORA, "all", "lang"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.corpus == "lang":
        # Process each lang level separately (index resets per level; avoids picking up template files)
        for level in LANG_LEVELS:
            directory, parse_fn, recursive = CORPORA[level]
            print(f"\n{'='*50}")
            print(f"  {level}")
            print(f"{'='*50}")
            run_corpus(level, directory, parse_fn, args.dry_run, recursive=recursive)
        return

    if args.corpus == "all":
        targets = list(CORPORA.items())
    else:
        targets = [(args.corpus, CORPORA[args.corpus])]

    for name, entry in targets:
        directory, parse_fn, recursive = entry
        print(f"\n{'='*50}")
        print(f"  {name}")
        print(f"{'='*50}")
        run_corpus(name, directory, parse_fn, args.dry_run, recursive=recursive)

    print()


if __name__ == "__main__":
    main()

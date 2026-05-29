#!/usr/bin/env python3
"""
build_training_corpus.py

Validates and concatenates the full Ninereeds training corpus into a single
file ready for train.py.

For each file:
  - Validates the expected format for its directory type
  - Auto-fixes minor issues (trailing whitespace, CRLF line endings,
    leading space after [user] tag in story files)
  - Skips files with structural problems and logs them

Formats by directory:
  phases/         — [user]/[Ninereeds] dialogue, exactly 4 pairs per file
  lang/           — 4-line EN/DE/JP/ZH stanzas, no tags
  wiki/           — [user]/[Ninereeds] dialogue, variable pairs
  reasoning/      — [user]/[Ninereeds] dialogue, variable pairs
  grammar/        — [user]/[Ninereeds] dialogue, ordered by numeric subdirectory
  triplet_stories/ — [user]/[Ninereeds] dialogue, exactly 1 pair per file
  philosophy/     — [STATEMENT_EN/DE/JA/ZH], [USER_EN/DE/JA/ZH],
                    [NINEREEDS_EN/DE/JA/ZH] multilingual block format

Usage:
  python3 meta/scripts/build_training_corpus.py
  python3 meta/scripts/build_training_corpus.py --output training/corpus/my_corpus.txt
  python3 meta/scripts/build_training_corpus.py --dry-run
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "training_data"


# ---------------------------------------------------------------------------
# Common fix: normalize line endings, strip trailing whitespace
# ---------------------------------------------------------------------------

def fix_common(text: str) -> tuple[str, bool]:
    original = text
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    cleaned = "\n".join(lines) + "\n"
    return cleaned, cleaned != original


# ---------------------------------------------------------------------------
# Validators
# Each returns (cleaned_text, issues_list).
# Empty issues_list = OK. Non-empty = structural problem; file will be skipped.
# ---------------------------------------------------------------------------

def fix_extra_ninereeds_tags(text: str) -> tuple[str, bool]:
    """Remove [Ninereeds] prefix from all but the first line of each response block.

    Fixes files where every body line carries [Ninereeds] instead of just the opener.
    """
    lines = text.split("\n")
    result: list[str] = []
    in_response = False
    changed = False
    tag = "[Ninereeds]"

    for line in lines:
        if line.startswith("[user]"):
            in_response = False
            result.append(line)
        elif line.startswith(tag) and not in_response:
            in_response = True
            result.append(line)
        elif line.startswith(tag) and in_response:
            result.append(line[len(tag):])
            changed = True
        else:
            if not line.strip():
                in_response = False
            result.append(line)

    return "\n".join(result), changed


def check_phases(text: str) -> tuple[str, list[str]]:
    """Phase files: at least 1 [user]/[Ninereeds] pair with matching counts.

    Files with 1, 2, 3, or 4 pairs are all valid training data.
    Auto-fixes: extra [Ninereeds] tags on body lines (every-line-tagged pattern).
    """
    text, _ = fix_common(text)
    text, _ = fix_extra_ninereeds_tags(text)
    issues: list[str] = []

    user_count = len(re.findall(r"^\[user\]", text, re.MULTILINE))
    nr_count = len(re.findall(r"^\[Ninereeds\]", text, re.MULTILINE))

    if user_count == 0:
        issues.append("no [user] tags found")
    elif user_count != nr_count:
        issues.append(f"mismatched: {user_count} [user] vs {nr_count} [Ninereeds]")
    else:
        nr_with_content = len(re.findall(r"^\[Ninereeds\].+", text, re.MULTILINE))
        if nr_with_content != nr_count:
            empty = nr_count - nr_with_content
            issues.append(f"{empty} [Ninereeds] opener(s) have no content on their line")

    return text, issues


def check_lang(text: str) -> tuple[str, list[str]]:
    """Lang files: stanzas of exactly 4 non-empty lines (EN/DE/JP/ZH), separated by blank lines."""
    text, _ = fix_common(text)
    if not text.strip():
        return text, ["empty file"]

    stanzas = [s.strip() for s in re.split(r"\n\n+", text.strip())]
    stanzas = [s for s in stanzas if s]
    issues: list[str] = []

    for i, stanza in enumerate(stanzas):
        lines = [ln for ln in stanza.split("\n") if ln.strip()]
        if len(lines) != 4:
            issues.append(f"stanza {i + 1}: {len(lines)} lines (expected 4)")
            if len(issues) >= 3:
                issues.append("…further stanza errors truncated")
                break

    return text, issues


def check_story(text: str) -> tuple[str, list[str]]:
    """Triplet story: exactly 1 [user]/[Ninereeds] pair. Fixes leading space after [user]."""
    text = re.sub(r"^\[user\] +", "[user]", text, flags=re.MULTILINE)
    text, _ = fix_common(text)

    user_count = len(re.findall(r"^\[user\]", text, re.MULTILINE))
    nr_count = len(re.findall(r"^\[Ninereeds\]", text, re.MULTILINE))
    issues: list[str] = []
    if user_count != 1:
        issues.append(f"[user] count {user_count}, expected 1")
    if nr_count != 1:
        issues.append(f"[Ninereeds] count {nr_count}, expected 1")
    return text, issues


def check_dialogue(text: str) -> tuple[str, list[str]]:
    """Reasoning/wiki: variable [user]/[Ninereeds] pairs. May have # header lines."""
    text, _ = fix_common(text)
    user_count = len(re.findall(r"^\[user\]", text, re.MULTILINE))
    nr_count = len(re.findall(r"^\[Ninereeds\]", text, re.MULTILINE))
    issues: list[str] = []
    if user_count == 0:
        issues.append("no [user] tags found")
    elif user_count != nr_count:
        issues.append(f"mismatched: {user_count} [user] vs {nr_count} [Ninereeds]")
    return text, issues


def check_bridge_file(text: str) -> tuple[str, list[str]]:
    """Bridge course annotation file: bracket-annotated plain prose, no [user]/[Ninereeds] tags."""
    text, _ = fix_common(text)
    issues: list[str] = []
    if not text.strip():
        issues.append("empty file")
        return text, issues
    if "[user]" in text or "[Ninereeds]" in text:
        issues.append("bridge file must not contain [user] or [Ninereeds] tags")
        return text, issues
    if re.search(r"^SECTION\b", text, re.MULTILINE):
        issues.append("bridge file contains SECTION header labels")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 8:
        issues.append(f"bridge file too short: {len(lines)} non-empty lines")
    # Annotated block: first 4 non-empty lines must contain at least one bracket marker
    if len(lines) >= 4:
        ann_text = " ".join(lines[:4])
        if not re.search(r"[(\[{<*]", ann_text):
            issues.append("annotated block (first 4 lines) contains no role brackets")
    # Plain block: last 4 non-empty lines must contain no bracket markers
    if len(lines) >= 4:
        plain_text = " ".join(lines[-4:])
        if re.search(r"[()[\]{}<>*]", plain_text):
            issues.append("plain block (last 4 lines) contains bracket markers")
    return text, issues


def check_grammar_file(text: str) -> tuple[str, list[str]]:
    """Grammar file dispatcher: bridge annotation format or standard dialogue format."""
    if "[user]" not in text and "[Ninereeds]" not in text:
        return check_bridge_file(text)
    return check_dialogue(text)


def check_grounded_story(text: str) -> tuple[str, list[str]]:
    """Grounded story: plain prose, no [user]/[Ninereeds] tags expected."""
    text, _ = fix_common(text)
    issues: list[str] = []
    if not text.strip():
        issues.append("empty file")
        return text, issues
    if re.search(r"^\[user\]|\[Ninereeds\]", text, re.MULTILINE):
        issues.append("unexpected [user]/[Ninereeds] tags in plain prose file")
    chars = len(text.replace("\n", "").replace(" ", ""))
    if chars < 50:
        issues.append(f"too short ({chars} chars)")
    return text, issues


def check_philosophy(text: str) -> tuple[str, list[str]]:
    """Philosophy: multilingual block tags [STATEMENT_EN], [USER_EN], [NINEREEDS_EN]."""
    text, _ = fix_common(text)
    issues: list[str] = []
    for tag in ("[STATEMENT_EN]", "[USER_EN]", "[NINEREEDS_EN]"):
        if tag not in text:
            issues.append(f"missing {tag}")
    return text, issues


# ---------------------------------------------------------------------------
# Directory processor
# ---------------------------------------------------------------------------

@dataclass
class DirStats:
    label: str
    total: int = 0
    included: int = 0
    fixed: int = 0
    skipped: int = 0
    issue_log: list[tuple[str, list[str]]] = field(default_factory=list)


def process_dir(
    directory: Path,
    checker: Callable[[str], tuple[str, list[str]]],
    label: str,
    out_parts: list[str],
    pattern: str = "*.md",
) -> DirStats:
    stats = DirStats(label=label)
    for path in sorted(directory.glob(pattern)):
        raw = path.read_text(encoding="utf-8", errors="replace")
        cleaned, issues = checker(raw)
        stats.total += 1
        if issues:
            stats.skipped += 1
            stats.issue_log.append((path.name, issues))
        else:
            stats.included += 1
            if cleaned != raw:
                stats.fixed += 1
            out_parts.append(cleaned.rstrip("\n"))
    return stats


def process_tree(
    directory: Path,
    checker: Callable[[str], tuple[str, list[str]]],
    label: str,
    out_parts: list[str],
    pattern: str = "*.md",
) -> DirStats:
    """Process files recursively in deterministic path order.

    Used for ordered curricula such as grammar, where numeric subdirectories
    define the intended sequence.
    """
    stats = DirStats(label=label)
    for path in sorted(directory.rglob(pattern)):
        if path.name in {"manifest.md", "lexicon.md", "prepositions.md", "bridge_design.md"}:
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        cleaned, issues = checker(raw)
        stats.total += 1
        rel = path.relative_to(directory).as_posix()
        if issues:
            stats.skipped += 1
            stats.issue_log.append((rel, issues))
        else:
            stats.included += 1
            if cleaned != raw:
                stats.fixed += 1
            out_parts.append(cleaned.rstrip("\n"))
    return stats


# ---------------------------------------------------------------------------
# Curriculum traversal order
# Follows the training pipeline staging from docs/training_pipeline.md:
# lang_1-2, phases 1-3, lang_3-4, phases 4-6, lang_5, wiki, reasoning,
# triplet stories, philosophy.
# Note: train.py shuffles all windows within each epoch, so file order in
# the concatenated corpus affects only which windows span file boundaries,
# not the overall training distribution.
# ---------------------------------------------------------------------------

CURRICULUM_ORDER: list[tuple] = [
    ("lang/lang_1",            check_lang,             "lang_1"),
    ("lang/lang_2",            check_lang,             "lang_2"),
    ("grammar",                check_grammar_file,     "grammar",             "*.md", "tree"),
    ("phases/phase_1",         check_phases,           "phase_1"),
    ("phases/phase_2",         check_phases,           "phase_2"),
    ("phases/phase_3",         check_phases,           "phase_3"),
    ("lang/lang_3",            check_lang,             "lang_3"),
    ("lang/lang_4",            check_lang,             "lang_4"),
    ("phases/phase_4",         check_phases,           "phase_4"),
    ("phases/phase_5",         check_phases,           "phase_5"),
    ("phases/phase_6",         check_phases,           "phase_6"),
    ("lang/lang_5",            check_lang,             "lang_5"),
    ("wiki/wiki_1",            check_dialogue,         "wiki_1"),
    ("wiki/wiki_2",            check_dialogue,         "wiki_2"),
    ("wiki/wiki_3",            check_dialogue,         "wiki_3"),
    ("wiki/wiki_4",            check_dialogue,         "wiki_4"),
    ("reasoning",              check_dialogue,         "reasoning"),
    ("grounded_stories",       check_grounded_story,   "grounded_stories",  "story_*.md"),
    ("triplet_stories/tier_1", check_story,            "triplet_tier_1"),
    ("triplet_stories/tier_2", check_story,            "triplet_tier_2"),
    ("triplet_stories/tier_3", check_story,            "triplet_tier_3"),
    ("triplet_stories/tier_4", check_story,            "triplet_tier_4"),
    ("philosophy",             check_philosophy,       "philosophy"),
]


# ---------------------------------------------------------------------------
# JSONL order-file processor (used when --order-file is given)
# Reads a training/training_order/phase_X_order.jsonl and processes every
# file listed in JSONL order.  Validator is inferred from the file path.
# ---------------------------------------------------------------------------

def infer_checker(path: Path) -> Callable[[str], tuple[str, list[str]]]:
    """Return the appropriate validator for a file based on its directory."""
    parts = path.parts
    # Walk up the path parts looking for known directory names
    for part in parts:
        if part in ("phase_A", "phase_B", "phase_C", "phase_D", "phase_E"):
            return check_phases
        if part == "bridge":
            return check_bridge_file
        if part == "grammar":
            return check_grammar_file
        if part == "grounded_stories":
            return check_grounded_story
        if part == "lang":
            return check_lang
        if part in ("wiki", "reasoning"):
            return check_dialogue
        if part == "triplet_stories":
            return check_story
        if part == "philosophy":
            return check_philosophy
    return check_phases  # safe default


def process_order_file(order_file: Path, out_parts: list[str]) -> DirStats:
    """
    Process files in the exact order given by a JSONL training order file.
    Each line is a unit: {"files": ["path/to/file.md", ...], ...}
    Paths in the JSONL are relative to the repo root.
    """
    import json as _json
    stats = DirStats(label=order_file.stem)
    lines = order_file.read_text(encoding="utf-8").splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        unit = _json.loads(line)
        for rel_path in unit.get("files", []):
            path = ROOT / rel_path
            if not path.exists():
                stats.total += 1
                stats.skipped += 1
                stats.issue_log.append((rel_path, ["file not found"]))
                continue
            checker = infer_checker(path)
            raw = path.read_text(encoding="utf-8", errors="replace")
            cleaned, issues = checker(raw)
            stats.total += 1
            if issues:
                stats.skipped += 1
                stats.issue_log.append((rel_path, issues))
            else:
                stats.included += 1
                if cleaned != raw:
                    stats.fixed += 1
                out_parts.append(cleaned.rstrip("\n"))
    return stats


# ---------------------------------------------------------------------------
# Sequence-file phase processor (used when --cluster-sequence is given)
# ---------------------------------------------------------------------------

PHASE_DIRS = {f"phase_{n}" for n in range(1, 7)}


def process_phase_sequence(seq_file: Path, out_parts: list[str]) -> DirStats:
    """Process phase files in the order given by a cluster_sequence.txt file."""
    stats = DirStats(label="phases_clustered")
    lines = seq_file.read_text(encoding="utf-8").splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # line format: phase_N/filename.md
        parts = line.split("/", 1)
        if len(parts) != 2 or parts[0] not in PHASE_DIRS:
            continue
        path = DATA / "phases" / parts[0] / parts[1]
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        cleaned, issues = check_phases(raw)
        stats.total += 1
        if issues:
            stats.skipped += 1
            stats.issue_log.append((line, issues))
        else:
            stats.included += 1
            if cleaned != raw:
                stats.fixed += 1
            out_parts.append(cleaned.rstrip("\n"))
    return stats


# ---------------------------------------------------------------------------
# Corpus builder
# ---------------------------------------------------------------------------

def build_corpus(output: Path, report: Path, dry_run: bool,
                 order_file: Path | None = None,
                 cluster_sequence: Path | None = None,
                 oversample_reasoning: int = 1) -> bool:
    out_parts: list[str] = []
    all_stats: list[DirStats] = []

    # --order-file mode: process exactly the files listed in the JSONL, in order.
    # Bypasses the full CURRICULUM_ORDER traversal entirely.
    if order_file is not None:
        abs_order = order_file if order_file.is_absolute() else ROOT / order_file
        order_file = abs_order
        print(f"  Order file: {order_file.relative_to(ROOT)}")
        stats = process_order_file(order_file, out_parts)
        all_stats.append(stats)
        skip_note = f"  ({stats.skipped} skipped)" if stats.skipped else ""
        fix_note  = f"  ({stats.fixed} fixed)"   if stats.fixed   else ""
        print(f"  {stats.label:<24}  {stats.included:>5}/{stats.total}{fix_note}{skip_note}")

        corpus = "\n\n".join(out_parts)
        corpus_bytes = len(corpus.encode("utf-8"))
        total_skipped = stats.skipped

        print()
        print(f"  Files:    {stats.included:,} / {stats.total:,} included")
        print(f"  Fixed:    {stats.fixed:,}")
        print(f"  Skipped:  {total_skipped:,}")
        print(f"  Size:     {corpus_bytes / 1024 / 1024:.2f} MB  ({corpus_bytes:,} bytes)")

        report_lines = [
            "# Training Corpus Build Report",
            f"Order file: {order_file}",
            "",
            f"Total files:    {stats.total:,}",
            f"Included:       {stats.included:,}",
            f"Fixed (minor):  {stats.fixed:,}",
            f"Skipped:        {total_skipped:,}",
            f"Corpus size:    {corpus_bytes / 1024 / 1024:.2f} MB",
            "",
        ]
        if stats.issue_log:
            report_lines += ["## Issues", ""]
            for fname, issues in stats.issue_log:
                for iss in issues:
                    report_lines.append(f"  - {fname}: {iss}")

        if not dry_run:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(corpus, encoding="utf-8")
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
            print(f"  Corpus → {output}")
            print(f"  Report → {report}")
        else:
            print("  [dry-run] no files written")

        if total_skipped == 0:
            print("\n  All files validated — corpus is clean.")
            return True
        else:
            print("\n  Structural issues found — see report.")
            return False

    if oversample_reasoning > 1:
        print(f"  Reasoning oversampling: ×{oversample_reasoning}")

    # Phase directories that will be skipped if using cluster_sequence
    phase_dirs_to_skip = set()
    if cluster_sequence is not None:
        phase_dirs_to_skip = PHASE_DIRS
        print(f"  Phase ordering: cluster_sequence ({cluster_sequence.name})")

    for entry in CURRICULUM_ORDER:
        rel_dir, checker, label = entry[:3]
        pattern = entry[3] if len(entry) > 3 else "*.md"
        traversal = entry[4] if len(entry) > 4 else "dir"

        # Skip individual phase dirs if using cluster_sequence
        dir_base = rel_dir.split("/")[-1] if "/" in rel_dir else rel_dir
        if dir_base in phase_dirs_to_skip:
            continue

        directory = DATA / rel_dir
        if not directory.exists():
            print(f"  [missing] {rel_dir}")
            continue
        repeat = oversample_reasoning if label == "reasoning" else 1
        for pass_n in range(repeat):
            if traversal == "tree":
                stats = process_tree(directory, checker, label, out_parts, pattern)
            else:
                stats = process_dir(directory, checker, label, out_parts, pattern)
            if pass_n == 0:
                all_stats.append(stats)
                skip_note = f"  ({stats.skipped} skipped)" if stats.skipped else ""
                fix_note = f"  ({stats.fixed} fixed)" if stats.fixed else ""
                suffix = f" ×{repeat}" if repeat > 1 else ""
                print(f"  {label:<24}  {stats.included:>5}/{stats.total}{fix_note}{skip_note}{suffix}")

        # After lang_2 (just before where phase_1 would appear), inject clustered phases
        if cluster_sequence is not None and label == "lang_2":
            phase_stats = process_phase_sequence(cluster_sequence, out_parts)
            all_stats.append(phase_stats)
            skip_note = f"  ({phase_stats.skipped} skipped)" if phase_stats.skipped else ""
            fix_note = f"  ({phase_stats.fixed} fixed)" if phase_stats.fixed else ""
            print(f"  {'phases_clustered':<24}  {phase_stats.included:>5}/{phase_stats.total}{fix_note}{skip_note}")

    corpus = "\n\n".join(out_parts)
    corpus_bytes = len(corpus.encode("utf-8"))

    total_files = sum(s.total for s in all_stats)
    total_included = sum(s.included for s in all_stats)
    total_fixed = sum(s.fixed for s in all_stats)
    total_skipped = sum(s.skipped for s in all_stats)

    print()
    print(f"  Files:    {total_included:,} / {total_files:,} included")
    print(f"  Fixed:    {total_fixed:,}")
    print(f"  Skipped:  {total_skipped:,}")
    print(f"  Size:     {corpus_bytes / 1024 / 1024:.2f} MB  ({corpus_bytes:,} bytes)")

    # Build report
    report_lines = [
        "# Training Corpus Build Report",
        "",
        f"Total files:    {total_files:,}",
        f"Included:       {total_included:,}",
        f"Fixed (minor):  {total_fixed:,}",
        f"Skipped:        {total_skipped:,}",
        f"Corpus size:    {corpus_bytes / 1024 / 1024:.2f} MB",
        "",
        "## Per-directory",
        "",
    ]
    for s in all_stats:
        status = f"{s.included}/{s.total}"
        if s.fixed:
            status += f"  fixed={s.fixed}"
        if s.skipped:
            status += f"  SKIPPED={s.skipped}"
        report_lines.append(f"### {s.label}  {status}")
        if s.issue_log:
            report_lines.append("")
            report_lines.append("Issues:")
            for fname, issues in s.issue_log:
                for iss in issues:
                    report_lines.append(f"  - {fname}: {iss}")
        report_lines.append("")

    if not dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(corpus, encoding="utf-8")
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        print(f"  Corpus → {output}")
        print(f"  Report → {report}")
    else:
        print("  [dry-run] no files written")

    return total_skipped == 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Build Ninereeds training corpus")
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "training/corpus/full_corpus.txt",
        help="Output corpus file (default: training/corpus/full_corpus.txt)",
    )
    parser.add_argument(
        "--report", type=Path,
        default=ROOT / "training/corpus/build_report.txt",
        help="Output report file (default: training/corpus/build_report.txt)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate and report without writing any output files",
    )
    parser.add_argument(
        "--order-file", type=Path, default=None,
        help="JSONL training order file (e.g. training/training_order/phase_A_order.jsonl). "
             "When given, processes exactly the files listed in that order and skips the "
             "full CURRICULUM_ORDER traversal.  This is the preferred mode for campaign training.",
    )
    parser.add_argument(
        "--cluster-sequence", type=Path, default=None,
        help="If given, use this file for phase ordering instead of alphabetical sort. "
             "See meta/scripts/cluster_phases.py to generate one.",
    )
    parser.add_argument(
        "--oversample-reasoning", type=int, default=1, metavar="N",
        help="Include the reasoning section N times in the corpus (default: 1). "
             "Use to increase reasoning weight without adding new data.",
    )
    args = parser.parse_args()

    print(f"\nBuilding training corpus")
    print(f"Data root: {DATA}")
    print()

    ok = build_corpus(args.output, args.report, args.dry_run,
                      order_file=args.order_file,
                      cluster_sequence=args.cluster_sequence,
                      oversample_reasoning=args.oversample_reasoning)

    if ok:
        print("\n  All files validated — corpus is clean.")
        sys.exit(0)
    else:
        print("\n  Structural issues found — see build_report.txt.")
        print("  Skipped files were excluded from the corpus.")
        sys.exit(1)


if __name__ == "__main__":
    main()

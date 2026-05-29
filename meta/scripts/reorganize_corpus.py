#!/usr/bin/env python3
"""
One-time corpus reorganisation: move files into custom phase dirs and generate
canonical JSONL training order files.

THIS SCRIPT IS A ONE-TIME MIGRATION TOOL.

The phase_X_order.jsonl files it produces in training/training_order/ are the
canonical training order from that point on.  Future experiments edit those
JSONL files directly.  Do NOT re-run this script to change training order —
edit the JSONL instead.  Re-running requires --force and will discard any
manual edits to the JSONL files.

Run with the project Python:
  /home/aomukai/.unsloth/studio/unsloth_studio/bin/python meta/scripts/reorganize_corpus.py

Steps:
  1. Read training/corpus_admin/curriculum_order.json
  2. Create training_data/phase_A/ … phase_E/
  3. Copy concept files (all language variants) into the appropriate phase dir
  4. Move training_data/grammar/bridge_course/ → training_data/bridge/
  5. Move training_data/phases/         → archive/phases/
  6. Generate training/training_order/phase_X_order.jsonl  (one per custom phase)
  7. Generate training/training_order/grammar_order.jsonl
  8. Generate training/training_order/bridge_order.jsonl
  9. Generate training/training_order/grounded_stories_order.jsonl

Usage:
  python meta/scripts/reorganize_corpus.py --dry-run   # show plan, touch nothing
  python meta/scripts/reorganize_corpus.py             # execute (safe: won't overwrite JSONL)
  python meta/scripts/reorganize_corpus.py --force     # overwrite existing JSONL (destructive)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORDER_DIR = ROOT / "training" / "training_order"
PHASE_LETTER = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}
LANG_SUFFIXES = ("", "_DE", "_JP", "_ZH")


# ── helpers ───────────────────────────────────────────────────────────────────

def find_concept_files(concept_key: str, old_phase_dirs: list[Path]) -> list[Path]:
    """
    Find all language-variant files for a concept key across old phase dirs.
    concept_key is the raw key from the graph (may include _2 suffix).
    Returns paths that exist on disk, sorted: EN, DE, JP, ZH.
    """
    # The file stem is the concept key itself (spaces preserved in filename)
    stem = concept_key  # e.g. "home", "police officer", "home_2"
    found: list[Path] = []
    for d in old_phase_dirs:
        for suffix in LANG_SUFFIXES:
            p = d / f"{stem}{suffix}.md"
            if p.exists():
                found.append(p)
    return found


def concept_files_in_new_dir(concept_key: str, phase_dir: Path) -> list[str]:
    """Return the expected new paths (as strings) for a concept's files."""
    stem = concept_key
    paths = []
    for suffix in LANG_SUFFIXES:
        p = phase_dir / f"{stem}{suffix}.md"
        paths.append(str(p.relative_to(ROOT)))
    return paths


def last_in_cluster(idx: int, units: list[dict]) -> bool:
    """True if unit at idx is the last one with the same cluster tag."""
    cur_cluster = next((t for t in units[idx]["tags"] if t.startswith("cluster:")), None)
    if idx + 1 >= len(units):
        return True
    nxt_cluster = next((t for t in units[idx + 1]["tags"] if t.startswith("cluster:")), None)
    return cur_cluster != nxt_cluster


# ── JSONL writers ─────────────────────────────────────────────────────────────

def write_phase_jsonl(
    letter: str,
    groups: list[dict],
    phase_dir: Path,
    out_path: Path,
    dry_run: bool,
) -> int:
    """
    Write phase_X_order.jsonl.  Returns number of units written.
    probe_after=true on the last unit of every cluster.
    """
    units: list[dict] = []
    seq = 1

    for grp in groups:
        cluster_id = grp["cluster"]
        label = grp["label"]
        concepts = grp["concepts"]

        for concept_entry in concepts:
            canon = concept_entry["canonical"]
            all_keys = concept_entry["all_keys"]  # includes _N variants

            # Collect files for every key variant
            files: list[str] = []
            for key in all_keys:
                for suffix in LANG_SUFFIXES:
                    rel = str((phase_dir / f"{key}{suffix}.md").relative_to(ROOT))
                    files.append(rel)

            unit_id = f"{letter}_{seq:04d}"
            unit = {
                "unit_id": unit_id,
                "label": canon,
                "depth": grp["depth"],
                "cluster": cluster_id,
                "allowlist_rank": concept_entry.get("allowlist_rank",
                    next((v.get("allowlist_rank", 9999)
                          for v in [concept_entry]), 9999)),
                "source_keys": all_keys,
                "files": files,
                "tags": [
                    f"phase_{letter}",
                    re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_"),
                    f"cluster:{cluster_id}",
                    f"depth:{grp['depth']}",
                ],
                "probe_after": False,
            }
            units.append(unit)
            seq += 1

    # Set probe_after on last unit of each cluster
    for i, unit in enumerate(units):
        if last_in_cluster(i, units):
            unit["probe_after"] = True

    if not dry_run:
        with open(out_path, "w", encoding="utf-8") as f:
            for unit in units:
                f.write(json.dumps(unit, ensure_ascii=False) + "\n")

    return len(units)


def write_grammar_jsonl(
    grammar_dir: Path,
    out_path: Path,
    dry_run: bool,
) -> int:
    """
    Generate grammar_order.jsonl from the numbered grammar subdirs (00–10).
    Each file is one unit.  probe_after=true at the end of each subdir.
    bridge_course is excluded (handled separately).
    """
    lang_sfx = ("_DE", "_JP", "_ZH")
    units: list[dict] = []
    seq = 1

    subdirs = sorted(
        (d for d in grammar_dir.iterdir()
         if d.is_dir() and d.name != "bridge_course"),
        key=lambda d: d.name,
    )

    for subdir in subdirs:
        en_files = sorted(
            p for p in subdir.glob("*.md")
            if not any(p.stem.endswith(s) for s in ("_DE", "_JP", "_ZH"))
        )
        subdir_units: list[dict] = []
        for en_file in en_files:
            stem = en_file.stem
            files = [str(en_file.relative_to(ROOT))]
            for sfx in lang_sfx:
                lf = subdir / f"{stem}{sfx}.md"
                if lf.exists():
                    files.append(str(lf.relative_to(ROOT)))
            unit = {
                "unit_id": f"G_{seq:04d}",
                "label": stem,
                "subdir": subdir.name,
                "files": files,
                "tags": ["grammar", subdir.name],
                "probe_after": False,
            }
            subdir_units.append(unit)
            seq += 1

        if subdir_units:
            subdir_units[-1]["probe_after"] = True  # probe at end of each subdir
        units.extend(subdir_units)

    if not dry_run:
        with open(out_path, "w", encoding="utf-8") as f:
            for unit in units:
                f.write(json.dumps(unit, ensure_ascii=False) + "\n")

    return len(units)


def write_bridge_jsonl(
    bridge_dir: Path,
    out_path: Path,
    dry_run: bool,
) -> int:
    """Generate bridge_order.jsonl.  All 100 bridge files, probe_after at end."""
    lang_sfx = ("_DE", "_JP", "_ZH")
    units: list[dict] = []
    seq = 1

    en_files = sorted(
        p for p in bridge_dir.glob("*.md")
        if not any(p.stem.endswith(s) for s in ("_DE", "_JP", "_ZH"))
    )
    for en_file in en_files:
        stem = en_file.stem
        files = [str(en_file.relative_to(ROOT))]
        for sfx in lang_sfx:
            lf = bridge_dir / f"{stem}{sfx}.md"
            if lf.exists():
                files.append(str(lf.relative_to(ROOT)))
        units.append({
            "unit_id": f"BR_{seq:04d}",
            "label": stem,
            "files": files,
            "tags": ["bridge"],
            "probe_after": False,
        })
        seq += 1

    if units:
        units[-1]["probe_after"] = True

    if not dry_run:
        with open(out_path, "w", encoding="utf-8") as f:
            for unit in units:
                f.write(json.dumps(unit, ensure_ascii=False) + "\n")

    return len(units)


def write_grounded_stories_jsonl(
    stories_dir: Path,
    out_path: Path,
    dry_run: bool,
) -> int:
    """
    Generate grounded_stories_order.jsonl.
    Groups EN/DE/JP/ZH variants of each story into one unit.
    """
    lang_sfx = ("_DE", "_JP", "_ZH")
    en_files = sorted(
        p for p in stories_dir.glob("*.md")
        if not any(p.stem.endswith(s) for s in ("_DE", "_JP", "_ZH", "_de", "_jp", "_zh"))
    )
    units: list[dict] = []
    seq = 1
    for en_file in en_files:
        stem = en_file.stem
        files = [str(en_file.relative_to(ROOT))]
        for sfx in lang_sfx:
            lf = stories_dir / f"{stem}{sfx}.md"
            if lf.exists():
                files.append(str(lf.relative_to(ROOT)))
        units.append({
            "unit_id": f"GS_{seq:04d}",
            "label": stem,
            "files": files,
            "tags": ["grounded_stories"],
            "probe_after": False,
        })
        seq += 1

    if units:
        units[-1]["probe_after"] = True

    if not dry_run:
        with open(out_path, "w", encoding="utf-8") as f:
            for unit in units:
                f.write(json.dumps(unit, ensure_ascii=False) + "\n")

    return len(units)


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-time corpus reorganisation and JSONL order file generation."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show plan and counts; move nothing, write nothing")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing JSONL files (destructive — discards manual edits)")
    parser.add_argument("--skip-move", action="store_true",
                        help="Skip file moves; only generate JSONL (useful if files already moved)")
    args = parser.parse_args()

    print("=== Corpus Reorganisation ===\n")
    if args.dry_run:
        print("  [DRY RUN — nothing will be moved or written]\n")

    # ── Load curriculum order ─────────────────────────────────────────────────
    order_path = ROOT / "training" / "corpus_admin" / "curriculum_order.json"
    print(f"Loading {order_path.relative_to(ROOT)}...")
    with open(order_path) as f:
        order = json.load(f)
    groups: list[dict] = order["groups"]
    print(f"  {len(groups)} groups loaded\n")

    # ── Guard: refuse to overwrite existing JSONL without --force ─────────────
    ORDER_DIR.mkdir(parents=True, exist_ok=True)
    existing = list(ORDER_DIR.glob("*.jsonl"))
    if existing and not args.force and not args.dry_run:
        print("ERROR: JSONL order files already exist:")
        for p in sorted(existing):
            print(f"  {p.relative_to(ROOT)}")
        print("\nThe JSONL files are canonical. Edit them directly for experiments.")
        print("To regenerate from scratch, pass --force (this discards manual edits).")
        raise SystemExit(1)
    if existing and args.force:
        print(f"  --force: will overwrite {len(existing)} existing JSONL file(s)\n")

    # ── Paths ─────────────────────────────────────────────────────────────────
    old_phases_root = ROOT / "training_data" / "phases"
    old_phase_dirs = [old_phases_root / f"phase_{i}" for i in range(1, 7)]
    new_phase_dirs = {
        letter: ROOT / "training_data" / f"phase_{letter}"
        for letter in "ABCDE"
    }
    old_bridge = ROOT / "training_data" / "grammar" / "bridge_course"
    new_bridge = ROOT / "training_data" / "bridge"
    stories_dir = ROOT / "training_data" / "grounded_stories"
    grammar_dir = ROOT / "training_data" / "grammar"
    archive_phases = ROOT / "archive" / "phases"

    # ── Step 1: Create new phase dirs ────────────────────────────────────────
    print("Phase directories:")
    for letter, d in new_phase_dirs.items():
        status = "exists" if d.exists() else "will create"
        print(f"  training_data/phase_{letter}/  ({status})")
        if not args.dry_run and not args.skip_move:
            d.mkdir(parents=True, exist_ok=True)

    # ── Step 2: Copy concept files into new phase dirs ────────────────────────
    print("\nCopying concept files to new phase dirs...")
    copy_counts: dict[str, int] = {l: 0 for l in "ABCDE"}
    missing_concepts: list[str] = []

    # Build tier→letter→groups mapping
    by_letter: dict[str, list[dict]] = {l: [] for l in "ABCDE"}
    for grp in groups:
        letter = PHASE_LETTER.get(grp["tier"])
        if letter:
            by_letter[letter].append(grp)

    for letter, letter_groups in by_letter.items():
        phase_dir = new_phase_dirs[letter]
        for grp in letter_groups:
            for concept_entry in grp["concepts"]:
                for key in concept_entry["all_keys"]:
                    found = find_concept_files(key, old_phase_dirs)
                    if not found:
                        missing_concepts.append(key)
                    for src in found:
                        dst = phase_dir / src.name
                        if not args.dry_run and not args.skip_move:
                            shutil.copy2(src, dst)
                        copy_counts[letter] += 1

    for letter in "ABCDE":
        print(f"  phase_{letter}: {copy_counts[letter]} files")
    if missing_concepts:
        print(f"  ⚠ {len(missing_concepts)} concept keys had no files on disk:")
        for m in missing_concepts[:10]:
            print(f"    {m}")
        if len(missing_concepts) > 10:
            print(f"    … +{len(missing_concepts)-10} more")

    # ── Step 3: Move bridge_course → training_data/bridge/ ───────────────────
    print(f"\nBridge course:")
    if old_bridge.exists():
        n = len(list(old_bridge.glob("*.md")))
        print(f"  grammar/bridge_course/ ({n} files) → training_data/bridge/")
        if not args.dry_run and not args.skip_move:
            if new_bridge.exists():
                shutil.rmtree(new_bridge)
            shutil.copytree(old_bridge, new_bridge)
    else:
        print(f"  ⚠ grammar/bridge_course/ not found — skipping")

    # ── Step 4: Archive old phases dir ───────────────────────────────────────
    print(f"\nArchiving original phases:")
    if old_phases_root.exists():
        total = sum(1 for _ in old_phases_root.rglob("*.md"))
        print(f"  training_data/phases/ ({total} files) → archive/phases/")
        if not args.dry_run and not args.skip_move:
            archive_phases.parent.mkdir(parents=True, exist_ok=True)
            if archive_phases.exists():
                shutil.rmtree(archive_phases)
            shutil.copytree(old_phases_root, archive_phases)
            # Don't delete yet — verify JSONL first, then delete manually
            print("  (original left in place — delete training_data/phases/ manually after verifying)")
    else:
        print("  training_data/phases/ not found — skipping")

    # ── Step 5–8: Generate JSONL order files ─────────────────────────────────
    print("\nGenerating JSONL order files...")

    # Phase A–E
    for letter, letter_groups in by_letter.items():
        out = ORDER_DIR / f"phase_{letter}_order.jsonl"
        n = write_phase_jsonl(
            letter, letter_groups, new_phase_dirs[letter], out, args.dry_run
        )
        print(f"  phase_{letter}_order.jsonl  {n} units")

    # Grammar
    out = ORDER_DIR / "grammar_order.jsonl"
    n = write_grammar_jsonl(grammar_dir, out, args.dry_run)
    print(f"  grammar_order.jsonl       {n} units")

    # Bridge
    bridge_src = new_bridge if (new_bridge.exists() and not args.dry_run) else old_bridge
    if bridge_src.exists():
        out = ORDER_DIR / "bridge_order.jsonl"
        n = write_bridge_jsonl(bridge_src, out, args.dry_run)
        print(f"  bridge_order.jsonl        {n} units")
    else:
        print("  bridge_order.jsonl        (skipped — bridge dir not found)")

    # Grounded stories
    if stories_dir.exists():
        out = ORDER_DIR / "grounded_stories_order.jsonl"
        n = write_grounded_stories_jsonl(stories_dir, out, args.dry_run)
        print(f"  grounded_stories_order.jsonl  {n} units")
    else:
        print("  grounded_stories_order.jsonl  (skipped — dir not found)")

    print(f"\n=== {'Dry run complete' if args.dry_run else 'Done'} ===")
    if not args.dry_run:
        print("  Next: verify JSONL files look correct")
        print("  Then: delete training_data/phases/ manually once satisfied")
        print("  To change training order: edit the JSONL files directly")


if __name__ == "__main__":
    main()

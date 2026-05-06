#!/usr/bin/env python3

from pathlib import Path
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="List files whose [Ninereeds] line starts with a given prefix."
    )
    parser.add_argument(
        "--root",
        default="training_data/phases",
        help="Root directory to scan for phase files.",
    )
    parser.add_argument(
        "--prefix",
        default="[Ninereeds]This is",
        help="Prefix to match at the start of a [Ninereeds] line.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output file path.",
    )
    args = parser.parse_args()

    root = Path(args.root)
    output = Path(args.output)
    rows = []

    for path in sorted(root.glob("phase_*/phase_*.md")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue

        for line_no, line in enumerate(lines, start=1):
            if line.startswith(args.prefix):
                rows.append(f"{path}\t{line_no}\t{line}")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")

    print(f"matches\t{len(rows)}")
    print(f"output\t{output}")


if __name__ == "__main__":
    main()

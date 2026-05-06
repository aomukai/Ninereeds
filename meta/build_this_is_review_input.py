#!/usr/bin/env python3

from pathlib import Path


def load_lines(path: Path):
    if not path.exists():
        return []
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    root = Path("/home/aomukai/Ninereeds")
    weird_path = root / "training_data/phases/this_is_weird.txt"
    the_path = root / "training_data/phases/this_is_the.txt"
    output_path = root / "training_data/phases/this_is_review_input.txt"

    weird = load_lines(weird_path)
    weird_set = set(weird)
    the_lines = load_lines(the_path)

    rows = []
    for line in weird:
        rows.append(f"WEIRD\t{line}")

    for line in the_lines:
        if line in weird_set:
            continue
        rows.append(f"THE_CASE\t{line}")

    output_path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")

    print(f"weird\t{len(weird)}")
    print(f"the_only\t{len(the_lines) - len([x for x in the_lines if x in weird_set])}")
    print(f"output\t{output_path}")


if __name__ == "__main__":
    main()

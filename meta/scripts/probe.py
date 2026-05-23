#!/usr/bin/env python3
"""
probe.py — format-native inference probes for Ninereeds after a training run.

Tests whether the model learned the corpus structure by prompting it in the
exact training format and inspecting what comes out.

Usage:
  python3 meta/scripts/probe.py --checkpoint core/run_1.pt
  python3 meta/scripts/probe.py --checkpoint core/run_1.pt --temperature 0.5 --tokens 120
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from inference import BDHInference

# ---------------------------------------------------------------------------
# Probe sets — one per corpus layer type
# ---------------------------------------------------------------------------

PHASE_PROBES = [
    # word known from phase_1 — concrete noun
    "[user]What does an acorn look like?\n[Ninereeds]",
    # abstract adjective from phase_1
    "[user]What does bright look like?\n[Ninereeds]",
    # phase_5 / phase_6 style (gerunds / bridge words)
    "[user]What does battling mean?\n[Ninereeds]",
    "[user]What does explanation look like?\n[Ninereeds]",
]

LANG_PROBES = [
    # lang_1 style — vocabulary equivalence
    "Abbreviating is shortening.\n",
    # lang_2 style — semantic frame
    "The peace is abiding.\nDer Frieden ist ",
    # lang_4 style — spatial construction
    "A cloud is above the mountain.\nEine Wolke ist ",
    # lang_5 style — question-answer
    "Whom did Tom answer?\nWem hat Tom ",
]

MULTILINGUAL_PROBES = [
    # German question in [user] format (from triplet stories)
    "[user]Erzähl mir eine Geschichte über den Herbst.\n[Ninereeds]",
    # Japanese prompt
    "[user]秋について話してください。\n[Ninereeds]",
]

REASONING_PROBES = [
    # reasoning format
    "[user]what is zero?\n[Ninereeds]",
    "[user]what is two plus two?\n[Ninereeds]",
]

ALL_PROBES = [
    ("Phase — concrete noun",     PHASE_PROBES[0]),
    ("Phase — abstract adj",      PHASE_PROBES[1]),
    ("Phase — gerund",            PHASE_PROBES[2]),
    ("Phase — bridge word",       PHASE_PROBES[3]),
    ("Lang_1 — vocab",            LANG_PROBES[0]),
    ("Lang_2 — semantic frame",   LANG_PROBES[1]),
    ("Lang_4 — spatial",          LANG_PROBES[2]),
    ("Lang_5 — Q&A",              LANG_PROBES[3]),
    ("Triplet — DE story prompt", MULTILINGUAL_PROBES[0]),
    ("Triplet — JP story prompt", MULTILINGUAL_PROBES[1]),
    ("Reasoning — number",        REASONING_PROBES[0]),
    ("Reasoning — arithmetic",    REASONING_PROBES[1]),
]


# ---------------------------------------------------------------------------
# Lightweight output analysis
# ---------------------------------------------------------------------------

def analyse(label: str, prompt: str, output: str) -> dict:
    full = prompt + output

    has_ninereeds_tag = bool(re.search(r"^\[Ninereeds\]", full, re.MULTILINE))
    lines = [l for l in output.split("\n") if l.strip()]
    has_sentences = any(l.endswith(".") for l in lines)
    has_pronoun = bool(re.search(r"\b(it|its|they|them|he|she|his|her)\b", output, re.I))
    has_negation = bool(re.search(r"\b(not|isn't|doesn't|can't|won't|aren't)\b", output, re.I))
    is_garbled = len([c for c in output if ord(c) > 127]) / max(len(output), 1) > 0.4

    return {
        "label":            label,
        "prompt":           prompt,
        "output":           output,
        "line_count":       len(lines),
        "has_sentences":    has_sentences,
        "ninereeds_tag":    has_ninereeds_tag,
        "pronoun":          has_pronoun,
        "negation":         has_negation,
        "garbled":          is_garbled,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Format-native probes for Ninereeds")
    parser.add_argument("--checkpoint", required=True, help="Path to checkpoint")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--tokens", type=int, default=120, help="Max new tokens per probe")
    parser.add_argument("--top-k", type=int, default=None)
    args = parser.parse_args()

    ckpt = ROOT / args.checkpoint
    if not ckpt.exists():
        print(f"Checkpoint not found: {ckpt}")
        sys.exit(1)

    print(f"\nNinereeds format probes")
    print(f"Checkpoint: {ckpt}")
    print(f"Temperature: {args.temperature}  max_tokens: {args.tokens}")
    print()

    model = BDHInference(
        checkpoint_path=ckpt,
        max_new_tokens=args.tokens,
        temperature=args.temperature,
        top_k=args.top_k,
    )

    results = []
    for label, prompt in ALL_PROBES:
        output = model.generate_text(prompt)
        r = analyse(label, prompt, output)
        results.append(r)

        flags = []
        if r["garbled"]:     flags.append("GARBLED")
        if r["pronoun"]:     flags.append("pronoun")
        if r["negation"]:    flags.append("negation")
        if not r["has_sentences"]: flags.append("no-sentences")
        flag_str = "  [" + ", ".join(flags) + "]" if flags else ""

        print(f"── {label}{flag_str}")
        print(f"   Prompt:  {prompt!r}")
        print(f"   Output:  {output!r}")
        print(f"   Lines: {r['line_count']}  sentences: {r['has_sentences']}  "
              f"[Ninereeds] tag: {r['ninereeds_tag']}")
        print()

    # Summary
    garbled = sum(1 for r in results if r["garbled"])
    pronouns = sum(1 for r in results if r["pronoun"])
    negations = sum(1 for r in results if r["negation"])
    with_sentences = sum(1 for r in results if r["has_sentences"])

    print(f"── Summary ({len(results)} probes)")
    print(f"   Garbled output:  {garbled}/{len(results)}")
    print(f"   Has sentences:   {with_sentences}/{len(results)}")
    print(f"   Pronoun use:     {pronouns}/{len(results)}")
    print(f"   Negation use:    {negations}/{len(results)}")


if __name__ == "__main__":
    main()

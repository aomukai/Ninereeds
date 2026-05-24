#!/usr/bin/env python3
"""
probe.py — format-native inference probes for Ninereeds after a training run.

Tests whether the model learned the corpus structure by prompting it in the
exact training format and inspecting what comes out.

Usage:
  python3 meta/scripts/probe.py --checkpoint core/run_1.pt
  python3 meta/scripts/probe.py --checkpoint core/run_1.pt --temperature 0.5 --tokens 120
  python3 meta/scripts/probe.py --checkpoint core/run_1.pt --seed 42
"""
from __future__ import annotations

import argparse
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from inference import BDHInference

# ---------------------------------------------------------------------------
# Fixed probe sets — one per corpus layer type
# ---------------------------------------------------------------------------

PHASE_PROBES = [
    "[user]What does an acorn look like?\n[Ninereeds]",
    "[user]What does bright look like?\n[Ninereeds]",
    "[user]What does battling mean?\n[Ninereeds]",
    "[user]What does explanation look like?\n[Ninereeds]",
]

LANG_PROBES = [
    "Abbreviating is shortening.\n",
    "The peace is abiding.\nDer Frieden ist ",
    "A cloud is above the mountain.\nEine Wolke ist ",
    "Whom did Tom answer?\nWem hat Tom ",
]

MULTILINGUAL_PROBES = [
    "[user]Erzähl mir eine Geschichte über den Herbst.\n[Ninereeds]",
    "[user]秋について話してください。\n[Ninereeds]",
]

REASONING_PROBES = [
    "[user]what is zero?\n[Ninereeds]",
]

FIXED_PROBES = [
    ("Phase — concrete noun",     PHASE_PROBES[0]),
    ("Phase — abstract adj",      PHASE_PROBES[1]),
    ("Phase — gerund",            PHASE_PROBES[2]),
    ("Phase — bridge word",       PHASE_PROBES[3]),
    ("Lang_1 — vocab",            LANG_PROBES[0]),
    ("Lang_2 — semantic frame",   LANG_PROBES[1]),
    ("Lang_4 — spatial (base)",   LANG_PROBES[2]),
    ("Lang_5 — Q&A",              LANG_PROBES[3]),
    ("Triplet — DE story prompt", MULTILINGUAL_PROBES[0]),
    ("Triplet — JP story prompt", MULTILINGUAL_PROBES[1]),
    ("Reasoning — number",        REASONING_PROBES[0]),
]

# ---------------------------------------------------------------------------
# Fixed comparison table — identical across all runs for cross-run tracking
# (label, prompt, pass_if_contains)
# Complements the randomised probes: random probes estimate variance,
# these give directly comparable pass/fail across run_10/11/12.
# ---------------------------------------------------------------------------

FIXED_COMPARISON_TABLE = [
    ("FC — 1+1=2",        "[user]what is one plus one?\n[Ninereeds]",           "two"),
    ("FC — 2+2=4",        "[user]what is two plus two?\n[Ninereeds]",           "four"),
    ("FC — 3+1=4",        "[user]what is three plus one?\n[Ninereeds]",         "four"),
    ("FC — zero",         "[user]what is zero?\n[Ninereeds]",                   "number"),
    ("FC — dative über",  "Die Wolke ist über",                                  "dem"),
    ("FC — acc movement", "Das Kind geht in",                                    "den"),
    ("FC — JP autumn",    "[user]秋について話してください。\n[Ninereeds]",        "秋"),
    ("FC — ZH autumn",    "[user]告诉我关于秋天的故事。\n[Ninereeds]",           "秋"),
]

# ---------------------------------------------------------------------------
# Randomised arithmetic probes
# ---------------------------------------------------------------------------

_NUM_WORDS = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
}


def make_arithmetic_probes(n: int = 3) -> list[dict]:
    """Return n random arithmetic probes for sums in range 1–5 + 1–5 = 2–10."""
    pairs = [(a, b) for a in range(1, 6) for b in range(1, 6)]
    selected = random.sample(pairs, min(n, len(pairs)))
    probes = []
    for a, b in selected:
        total = a + b
        prompt = f"[user]what is {_NUM_WORDS[a]} plus {_NUM_WORDS[b]}?\n[Ninereeds]"
        probes.append({
            "label":    f"Arithmetic — {a}+{b}={total}",
            "prompt":   prompt,
            "a": a, "b": b, "total": total,
            "expected": _NUM_WORDS[total],
        })
    return probes

# ---------------------------------------------------------------------------
# Randomised German dative probes (über + location noun)
# ---------------------------------------------------------------------------

# (EN singular, DE nominative, gender m/f/n)
# dative: m/n → "über dem X", f → "über der X"
_DATIVE_NOUN_POOL = [
    # masculine (der → über dem)
    ("tree",        "Baum",     "m"),
    ("table",       "Tisch",    "m"),
    ("forest",      "Wald",     "m"),
    ("river",       "Fluss",    "m"),
    ("tower",       "Turm",     "m"),
    ("stone",       "Stein",    "m"),
    ("garden",      "Garten",   "m"),
    ("hill",        "Hügel",    "m"),
    ("well",        "Brunnen",  "m"),
    ("cliff",       "Felsen",   "m"),
    # feminine (die → über der)
    ("meadow",      "Wiese",    "f"),
    ("city",        "Stadt",    "f"),
    ("school",      "Schule",   "f"),
    ("street",      "Straße",   "f"),
    ("bridge",      "Brücke",   "f"),
    ("wall",        "Mauer",    "f"),
    ("kitchen",     "Küche",    "f"),
    ("staircase",   "Treppe",   "f"),
    ("border",      "Grenze",   "f"),
    ("plain",       "Ebene",    "f"),
    # neuter (das → über dem)
    ("house",       "Haus",     "n"),
    ("roof",        "Dach",     "n"),
    ("field",       "Feld",     "n"),
    ("window",      "Fenster",  "n"),
    ("valley",      "Tal",      "n"),
    ("gate",        "Tor",      "n"),
    ("village",     "Dorf",     "n"),
    ("castle",      "Schloss",  "n"),
    ("sea",         "Meer",     "n"),
    ("boat",        "Boot",     "n"),
]


def _dative_article(gender: str) -> str:
    return "der" if gender == "f" else "dem"


def make_dative_probes(n: int = 2) -> list[dict]:
    """Return n random über+dative probes, one noun per gender group where possible."""
    # Stratify: pick at least one from each gender group when n >= 3
    by_gender: dict[str, list] = {"m": [], "f": [], "n": []}
    for entry in _DATIVE_NOUN_POOL:
        by_gender[entry[2]].append(entry)

    selected: list = []
    if n >= 3:
        # one from each gender, then fill remaining randomly
        for g in ("m", "f", "n"):
            selected.append(random.choice(by_gender[g]))
        extras = random.sample(
            [e for e in _DATIVE_NOUN_POOL if e not in selected],
            max(0, n - 3),
        )
        selected.extend(extras)
    else:
        selected = random.sample(_DATIVE_NOUN_POOL, n)

    probes = []
    for en_word, de_word, gender in selected:
        article = _dative_article(gender)
        expected = f"über {article} {de_word}"
        wrong_article = "dem" if gender == "f" else "der"
        wrong = f"über {wrong_article} {de_word}"
        prompt = f"A cloud is above the {en_word}.\nEine Wolke ist "
        probes.append({
            "label":         f"Dative — über {article} {de_word} ({gender})",
            "prompt":        prompt,
            "de_word":       de_word,
            "gender":        gender,
            "expected":      expected,
            "wrong":         wrong,
        })
    return probes

# ---------------------------------------------------------------------------
# Output analysis
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
        "label":         label,
        "prompt":        prompt,
        "output":        output,
        "line_count":    len(lines),
        "has_sentences": has_sentences,
        "ninereeds_tag": has_ninereeds_tag,
        "pronoun":       has_pronoun,
        "negation":      has_negation,
        "garbled":       is_garbled,
    }


def analyse_arithmetic(probe: dict, output: str) -> dict:
    expected = probe["expected"]
    # require "is <word>" or "equals <word>" context — prevents "plus ten" false positives
    correct = bool(re.search(rf"\b(?:is|equals)\s+{re.escape(expected)}\b", output, re.I))
    lines = [l for l in output.split("\n") if l.strip()]
    return {
        "label":         probe["label"],
        "prompt":        probe["prompt"],
        "output":        output,
        "expected":      expected,
        "correct":       correct,
        "line_count":    len(lines),
        "has_sentences": any(l.endswith(".") for l in lines),
        "ninereeds_tag": True,  # prompt already contains it
        "garbled":       False,
        "pronoun":       False,
        "negation":      False,
    }


def analyse_dative(probe: dict, output: str) -> dict:
    expected = probe["expected"]   # e.g. "über dem Baum"
    wrong    = probe["wrong"]      # e.g. "über der Baum"
    correct  = expected.lower() in output.lower()
    wrong_art = wrong.lower() in output.lower()
    lines = [l for l in output.split("\n") if l.strip()]
    return {
        "label":         probe["label"],
        "prompt":        probe["prompt"],
        "output":        output,
        "expected":      expected,
        "correct":       correct,
        "wrong_article": wrong_art,
        "line_count":    len(lines),
        "has_sentences": any(l.endswith(".") for l in lines),
        "ninereeds_tag": False,
        "garbled":       False,
        "pronoun":       False,
        "negation":      False,
    }

# ---------------------------------------------------------------------------
# Printing helpers
# ---------------------------------------------------------------------------

def print_result(r: dict) -> None:
    flags = []
    if r.get("garbled"):         flags.append("GARBLED")
    if r.get("pronoun"):         flags.append("pronoun")
    if r.get("negation"):        flags.append("negation")
    if not r.get("has_sentences"): flags.append("no-sentences")
    flag_str = "  [" + ", ".join(flags) + "]" if flags else ""

    print(f"── {r['label']}{flag_str}")
    print(f"   Prompt:  {r['prompt']!r}")
    print(f"   Output:  {r['output']!r}")
    print(f"   Lines: {r['line_count']}  sentences: {r['has_sentences']}  "
          f"[Ninereeds] tag: {r['ninereeds_tag']}")
    print()


def print_arithmetic_result(r: dict) -> None:
    status = "CORRECT" if r["correct"] else f"WRONG (expected '{r['expected']}')"
    print(f"── {r['label']}  → {status}")
    print(f"   Prompt:  {r['prompt']!r}")
    print(f"   Output:  {r['output']!r}")
    print()


def print_dative_result(r: dict) -> None:
    if r["correct"]:
        status = f"CORRECT ({r['expected']})"
    elif r["wrong_article"]:
        status = f"WRONG ARTICLE (got '{r['wrong']}', expected '{r['expected']}')"
    else:
        status = f"MISSING (expected '{r['expected']}')"
    print(f"── {r['label']}  → {status}")
    print(f"   Prompt:  {r['prompt']!r}")
    print(f"   Output:  {r['output']!r}")
    print()


def analyse_fixed_comparison(label: str, prompt: str, expected: str, output: str) -> dict:
    passed = expected.lower() in output.lower()
    return {"label": label, "prompt": prompt, "expected": expected,
            "output": output, "passed": passed}


def print_fixed_comparison_result(r: dict) -> None:
    status = "PASS" if r["passed"] else f"FAIL (want '{r['expected']}')"
    print(f"── {r['label']}  → {status}")
    print(f"   Prompt:  {r['prompt']!r}")
    print(f"   Output:  {r['output']!r}")
    print()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Format-native probes for Ninereeds")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--tokens", type=int, default=120)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for arithmetic/dative probe selection")
    parser.add_argument("--n-arith", type=int, default=3,
                        help="Number of random arithmetic probes (default 3)")
    parser.add_argument("--n-dative", type=int, default=3,
                        help="Number of random dative probes (default 3)")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    ckpt = ROOT / args.checkpoint
    if not ckpt.exists():
        print(f"Checkpoint not found: {ckpt}")
        sys.exit(1)

    print(f"\nNinereeds format probes")
    print(f"Checkpoint: {ckpt}")
    print(f"Temperature: {args.temperature}  max_tokens: {args.tokens}")
    if args.seed is not None:
        print(f"Seed: {args.seed}")
    print()

    model = BDHInference(
        checkpoint_path=ckpt,
        max_new_tokens=args.tokens,
        temperature=args.temperature,
        top_k=args.top_k,
    )

    # ── Fixed comparison table (identical across all runs) ────────────────
    print("=" * 60)
    print("  Fixed comparison probes (cross-run reproducible)")
    print("=" * 60)
    fc_results = []
    for label, prompt, expected in FIXED_COMPARISON_TABLE:
        output = model.generate_text(prompt)
        r = analyse_fixed_comparison(label, prompt, expected, output)
        fc_results.append(r)
        print_fixed_comparison_result(r)

    fc_passed = sum(1 for r in fc_results if r["passed"])
    fc_pairs = "  ".join(
        f"{r['label'].split('— ')[1]}{'✓' if r['passed'] else '✗'}"
        for r in fc_results
    )
    print(f"   Fixed comparison: {fc_passed}/{len(fc_results)} pass  ({fc_pairs})")
    print()

    # ── Fixed probes ──────────────────────────────────────────────────────
    print("=" * 60)
    print("  Format probes")
    print("=" * 60)
    fixed_results = []
    for label, prompt in FIXED_PROBES:
        output = model.generate_text(prompt)
        r = analyse(label, prompt, output)
        fixed_results.append(r)
        print_result(r)

    # ── Randomised arithmetic probes ──────────────────────────────────────
    print("=" * 60)
    print("  Randomised arithmetic probes")
    print("=" * 60)
    arith_probes = make_arithmetic_probes(args.n_arith)
    arith_results = []
    for p in arith_probes:
        output = model.generate_text(p["prompt"])
        r = analyse_arithmetic(p, output)
        arith_results.append(r)
        print_arithmetic_result(r)

    # ── Randomised dative probes ──────────────────────────────────────────
    print("=" * 60)
    print("  Randomised dative probes (über + location noun)")
    print("=" * 60)
    dative_probes = make_dative_probes(args.n_dative)
    dative_results = []
    for p in dative_probes:
        output = model.generate_text(p["prompt"])
        r = analyse_dative(p, output)
        dative_results.append(r)
        print_dative_result(r)

    # ── Summary ───────────────────────────────────────────────────────────
    all_results = fixed_results + arith_results + dative_results
    garbled      = sum(1 for r in all_results if r.get("garbled"))
    pronouns     = sum(1 for r in all_results if r.get("pronoun"))
    negations    = sum(1 for r in all_results if r.get("negation"))
    with_sentences = sum(1 for r in all_results if r.get("has_sentences"))

    arith_correct = sum(1 for r in arith_results if r["correct"])
    arith_pairs   = "  ".join(
        f"{r['label'].split('— ')[1]}{'✓' if r['correct'] else '✗'}"
        for r in arith_results
    )

    dative_correct     = sum(1 for r in dative_results if r["correct"])
    dative_wrong_art   = sum(1 for r in dative_results if r.get("wrong_article"))

    print(f"── Summary ({len(all_results)} format+random probes  +  {len(fc_results)} fixed comparison)")
    print(f"   Fixed comparison:{fc_passed:>3}/{len(fc_results)} pass  ({fc_pairs})")
    print(f"   Garbled output:  {garbled}/{len(all_results)}")
    print(f"   Has sentences:   {with_sentences}/{len(all_results)}")
    print(f"   Pronoun use:     {pronouns}/{len(all_results)}")
    print(f"   Negation use:    {negations}/{len(all_results)}")
    print(f"   Arithmetic:      {arith_correct}/{len(arith_results)} correct"
          + (f"  ({arith_pairs})" if arith_results else ""))
    print(f"   Dative (über):   {dative_correct}/{len(dative_results)} correct"
          + (f"  ({dative_wrong_art} wrong-article)" if dative_wrong_art else ""))


if __name__ == "__main__":
    main()

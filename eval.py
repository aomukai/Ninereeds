"""Eval harness for BDH.

Runs each prompt raw AND shaped with the same seed so the comparison is fair.
Scores for: garbage, repetition, drift, sentence formation.
Flags failure modes: loops, prompt-ignore, abrupt stop, hollow structure, lang confusion.

72 prompts: 18 semantic slots × 4 languages (EN / DE / JP / ZH).
Per-language shaped averages are the primary multilingual diagnostic.
EN-only avg is historically comparable to pre-72 runs.
"""

from __future__ import annotations

import json
import re
import string
import unicodedata
from datetime import datetime
from pathlib import Path

import torch

from inference import BDHInference

ROOT = Path(__file__).resolve().parent
RUNS_DIR = ROOT / "runs"

# ---------------------------------------------------------------------------
# Prompt battery — 18 semantic slots × 4 languages = 72 entries
# shaped/shape fields are pre-computed; no runtime auto-detection needed.
# ---------------------------------------------------------------------------

PROMPTS: list[dict] = [
    # ── English ─────────────────────────────────────────────────────────────
    {"text": "What is a book?",                     "shaped": "A book is",                              "shape": "definition", "lang": "en"},
    {"text": "What is a friend?",                   "shaped": "A friend is",                            "shape": "definition", "lang": "en"},
    {"text": "What is a school?",                   "shaped": "A school is",                            "shape": "definition", "lang": "en"},
    {"text": "Why do birds sing?",                  "shaped": "Q: Why do birds sing?\nA:",              "shape": "qa",         "lang": "en"},
    {"text": "Why do we sleep?",                    "shaped": "Q: Why do we sleep?\nA:",                "shape": "qa",         "lang": "en"},
    {"text": "How does a rainbow form?",            "shaped": "Q: How does a rainbow form?\nA:",        "shape": "qa",         "lang": "en"},
    {"text": "I am hungry because",                 "shaped": "I am hungry because ",                   "shape": "fill",       "lang": "en"},
    {"text": "The old man walked slowly because",   "shaped": "The old man walked slowly because ",     "shape": "fill",       "lang": "en"},
    {"text": "She was afraid because",              "shaped": "She was afraid because ",                "shape": "fill",       "lang": "en"},
    {"text": "The children laughed as they",        "shaped": "The children laughed as they ",          "shape": "fill",       "lang": "en"},
    {"text": "Once upon a time there was a",        "shaped": "Once upon a time there was a",           "shape": "passthrough","lang": "en"},
    {"text": "She opened the door and saw",         "shaped": "She opened the door and saw ",           "shape": "story",      "lang": "en"},
    {"text": "It was a dark and quiet night when",  "shaped": "It was a dark and quiet night when",     "shape": "passthrough","lang": "en"},
    {"text": "The best thing about summer is",      "shaped": "The best thing about summer is ",        "shape": "fill",       "lang": "en"},
    {"text": "My favourite memory is",              "shaped": "My favourite memory is ",                "shape": "fill",       "lang": "en"},
    {"text": "The reason I like reading is",        "shaped": "The reason I like reading is ",          "shape": "fill",       "lang": "en"},
    {"text": "If I could change one thing, I would","shaped": "If I could change one thing, I would ",  "shape": "fill",       "lang": "en"},
    {"text": "Language is the way people",          "shaped": "Language is the way people ",            "shape": "fill",       "lang": "en"},

    # ── German ──────────────────────────────────────────────────────────────
    {"text": "Was ist ein Buch?",                          "shaped": "Ein Buch ist",                           "shape": "definition", "lang": "de"},
    {"text": "Was ist ein Freund?",                        "shaped": "Ein Freund ist",                         "shape": "definition", "lang": "de"},
    {"text": "Was ist eine Schule?",                       "shaped": "Eine Schule ist",                        "shape": "definition", "lang": "de"},
    {"text": "Warum singen Vögel?",                        "shaped": "Q: Warum singen Vögel?\nA:",             "shape": "qa",         "lang": "de"},
    {"text": "Warum schlafen wir?",                        "shaped": "Q: Warum schlafen wir?\nA:",             "shape": "qa",         "lang": "de"},
    {"text": "Wie entsteht ein Regenbogen?",               "shaped": "Q: Wie entsteht ein Regenbogen?\nA:",    "shape": "qa",         "lang": "de"},
    {"text": "Ich bin hungrig, weil",                      "shaped": "Ich bin hungrig, weil ",                 "shape": "fill",       "lang": "de"},
    {"text": "Der alte Mann ging langsam, weil",           "shaped": "Der alte Mann ging langsam, weil ",      "shape": "fill",       "lang": "de"},
    {"text": "Sie hatte Angst, weil",                      "shaped": "Sie hatte Angst, weil ",                 "shape": "fill",       "lang": "de"},
    {"text": "Die Kinder lachten, als sie",                "shaped": "Die Kinder lachten, als sie ",           "shape": "fill",       "lang": "de"},
    {"text": "Es war einmal ein",                          "shaped": "Es war einmal ein ",                     "shape": "fill",       "lang": "de"},
    {"text": "Sie öffnete die Tür und sah",               "shaped": "Sie öffnete die Tür und sah ",          "shape": "fill",       "lang": "de"},
    {"text": "Es war eine dunkle, stille Nacht, als",      "shaped": "Es war eine dunkle, stille Nacht, als ", "shape": "fill",       "lang": "de"},
    {"text": "Das Beste am Sommer ist",                    "shaped": "Das Beste am Sommer ist ",               "shape": "fill",       "lang": "de"},
    {"text": "Meine schönste Erinnerung ist",             "shaped": "Meine schönste Erinnerung ist ",        "shape": "fill",       "lang": "de"},
    {"text": "Der Grund, warum ich gerne lese, ist",       "shaped": "Der Grund, warum ich gerne lese, ist ",  "shape": "fill",       "lang": "de"},
    {"text": "Wenn ich eine Sache ändern könnte, würde ich","shaped":"Wenn ich eine Sache ändern könnte, würde ich ","shape":"fill", "lang": "de"},
    {"text": "Sprache ist die Art, wie Menschen",          "shaped": "Sprache ist die Art, wie Menschen ",     "shape": "fill",       "lang": "de"},

    # ── Japanese ────────────────────────────────────────────────────────────
    {"text": "本とは何ですか？",           "shaped": "本は",                               "shape": "definition", "lang": "jp"},
    {"text": "友達とは何ですか？",         "shaped": "友達は",                             "shape": "definition", "lang": "jp"},
    {"text": "学校とは何ですか？",         "shaped": "学校は",                             "shape": "definition", "lang": "jp"},
    {"text": "鳥はなぜ歌うのですか？",    "shaped": "Q: 鳥はなぜ歌うのですか？\nA:",      "shape": "qa",         "lang": "jp"},
    {"text": "なぜ眠るのですか？",         "shaped": "Q: なぜ眠るのですか？\nA:",          "shape": "qa",         "lang": "jp"},
    {"text": "虹はどのようにできますか？", "shaped": "Q: 虹はどのようにできますか？\nA:", "shape": "qa",         "lang": "jp"},
    {"text": "お腹がすいたのは",           "shaped": "お腹がすいたのは",                  "shape": "fill",       "lang": "jp"},
    {"text": "老人がゆっくり歩いたのは",   "shaped": "老人がゆっくり歩いたのは",          "shape": "fill",       "lang": "jp"},
    {"text": "彼女が怖かったのは",         "shaped": "彼女が怖かったのは",                "shape": "fill",       "lang": "jp"},
    {"text": "子供たちは笑いながら",       "shaped": "子供たちは笑いながら",              "shape": "fill",       "lang": "jp"},
    {"text": "昔々、ある",                 "shaped": "昔々、ある",                         "shape": "fill",       "lang": "jp"},
    {"text": "彼女がドアを開けると",       "shaped": "彼女がドアを開けると",              "shape": "fill",       "lang": "jp"},
    {"text": "暗くて静かな夜のこと、",    "shaped": "暗くて静かな夜のこと、",             "shape": "fill",       "lang": "jp"},
    {"text": "夏の一番いいところは",       "shaped": "夏の一番いいところは",              "shape": "fill",       "lang": "jp"},
    {"text": "一番の思い出は",             "shaped": "一番の思い出は",                    "shape": "fill",       "lang": "jp"},
    {"text": "本を読むのが好きな理由は",   "shaped": "本を読むのが好きな理由は",          "shape": "fill",       "lang": "jp"},
    {"text": "もし一つのことを変えられるなら","shaped":"もし一つのことを変えられるなら",  "shape": "fill",       "lang": "jp"},
    {"text": "言葉とは人が",               "shaped": "言葉とは人が",                      "shape": "fill",       "lang": "jp"},

    # ── Chinese ─────────────────────────────────────────────────────────────
    {"text": "书是什么？",                 "shaped": "书是",                               "shape": "definition", "lang": "zh"},
    {"text": "朋友是什么？",               "shaped": "朋友是",                             "shape": "definition", "lang": "zh"},
    {"text": "学校是什么？",               "shaped": "学校是",                             "shape": "definition", "lang": "zh"},
    {"text": "鸟儿为什么唱歌？",           "shaped": "Q: 鸟儿为什么唱歌？\nA:",           "shape": "qa",         "lang": "zh"},
    {"text": "我们为什么要睡觉？",         "shaped": "Q: 我们为什么要睡觉？\nA:",         "shape": "qa",         "lang": "zh"},
    {"text": "彩虹是怎么形成的？",         "shaped": "Q: 彩虹是怎么形成的？\nA:",         "shape": "qa",         "lang": "zh"},
    {"text": "我肚子饿了，因为",           "shaped": "我肚子饿了，因为",                  "shape": "fill",       "lang": "zh"},
    {"text": "老人走得很慢，因为",         "shaped": "老人走得很慢，因为",                "shape": "fill",       "lang": "zh"},
    {"text": "她感到害怕，因为",           "shaped": "她感到害怕，因为",                  "shape": "fill",       "lang": "zh"},
    {"text": "孩子们边笑边",               "shaped": "孩子们边笑边",                      "shape": "fill",       "lang": "zh"},
    {"text": "从前有一个",                 "shaped": "从前有一个",                         "shape": "fill",       "lang": "zh"},
    {"text": "她打开门，看见",             "shaped": "她打开门，看见",                    "shape": "fill",       "lang": "zh"},
    {"text": "那是一个黑暗宁静的夜晚，当", "shaped": "那是一个黑暗宁静的夜晚，当",        "shape": "fill",       "lang": "zh"},
    {"text": "夏天最好的事情是",           "shaped": "夏天最好的事情是",                  "shape": "fill",       "lang": "zh"},
    {"text": "我最美好的记忆是",           "shaped": "我最美好的记忆是",                  "shape": "fill",       "lang": "zh"},
    {"text": "我喜欢阅读的原因是",         "shaped": "我喜欢阅读的原因是",                "shape": "fill",       "lang": "zh"},
    {"text": "如果我能改变一件事，我会",   "shaped": "如果我能改变一件事，我会",          "shape": "fill",       "lang": "zh"},
    {"text": "语言是人们",                 "shaped": "语言是人们",                         "shape": "fill",       "lang": "zh"},
]

LANGS = ["en", "de", "jp", "zh"]

# Locked config — best from previous eval
LOCKED_CONFIG = {"temperature": 0.8, "top_k": None, "max_new_tokens": 80}

# Fixed seeds — one per prompt, same seed for raw and shaped
SEEDS = [42 + i * 7 for i in range(len(PROMPTS))]


# ---------------------------------------------------------------------------
# Scoring — language-agnostic
# ---------------------------------------------------------------------------

def _cjk_ratio(text: str) -> float:
    """Fraction of chars in CJK / kana ranges."""
    n = sum(
        1 for c in text
        if '぀' <= c <= 'ヿ'   # hiragana + katakana
        or '一' <= c <= '鿿'   # CJK unified ideographs
        or '㐀' <= c <= '䶿'   # CJK ext-A
        or '豈' <= c <= '﫿'   # CJK compatibility
    )
    return n / max(len(text), 1)


def _is_cjk_text(text: str) -> bool:
    return _cjk_ratio(text) > 0.25


def score_output(text: str) -> dict[str, float]:
    # content_ratio: fraction of chars that are letters, numbers, punctuation, or whitespace
    # (replaces ASCII-only printable_ratio; now correct for DE/JP/ZH)
    def _is_content(c: str) -> bool:
        return c.isspace() or unicodedata.category(c)[0] in "LNP"
    content_ratio = sum(1 for c in text if _is_content(c)) / max(len(text), 1)

    # token_ratio: fraction of whitespace-split tokens that carry at least one letter
    # (replaces [a-zA-Z]{2+} word_ratio; now correct for all scripts)
    tokens = text.split()
    meaningful = [t for t in tokens if any(unicodedata.category(c)[0] == "L" for c in t)]
    token_ratio = len(meaningful) / max(len(tokens), 1)

    # no_repeat: char 4-gram for CJK (no spaces to split on), word trigram for Latin scripts
    if _is_cjk_text(text):
        chars = [c for c in text if not c.isspace()]
        if len(chars) >= 8:
            fourgrams = [tuple(chars[i:i + 4]) for i in range(len(chars) - 3)]
            no_repeat = len(set(fourgrams)) / max(len(fourgrams), 1)
        else:
            no_repeat = 1.0
    else:
        words = [w.lower().strip(string.punctuation) for w in tokens]
        if len(words) >= 3:
            trigrams = [tuple(words[i:i + 3]) for i in range(len(words) - 2)]
            no_repeat = len(set(trigrams)) / max(len(trigrams), 1)
        else:
            no_repeat = 1.0

    # has_sentence: sentence-end punctuation in any language
    has_sentence = float(bool(re.search(r"[.!?。！？]", text)))

    # length_ok: for CJK use char count / 5 as proxy for token count
    effective_len = max(len(tokens), len(text) // 5)
    length_ok = min(effective_len / 10, 1.0)

    overall = (
        content_ratio * 0.30
        + token_ratio  * 0.25
        + no_repeat    * 0.20
        + has_sentence * 0.15
        + length_ok    * 0.10
    )

    return {
        "overall":   round(overall, 3),
        "content":   round(content_ratio, 3),
        "tokens":    round(token_ratio, 3),
        "no_repeat": round(no_repeat, 3),
        "sentence":  round(has_sentence, 3),
        "length":    round(length_ok, 3),
    }


# ---------------------------------------------------------------------------
# Failure mode detection — language-aware
# ---------------------------------------------------------------------------

def detect_failures(prompt: str, output: str) -> list[str]:
    failures = []
    tokens = output.split()
    cjk = _is_cjk_text(output)

    # Loop detection
    if cjk:
        chars = [c for c in output if not c.isspace()]
        if len(chars) >= 8:
            fourgrams = [tuple(chars[i:i + 4]) for i in range(len(chars) - 3)]
            if len(fourgrams) > len(set(fourgrams)):
                failures.append("loop")
    else:
        words = [w.lower().strip(string.punctuation) for w in tokens]
        if len(words) >= 8:
            fourgrams = [tuple(words[i:i + 4]) for i in range(len(words) - 3)]
            if len(fourgrams) > len(set(fourgrams)):
                failures.append("loop")

    # Abrupt stop
    if cjk:
        if len([c for c in output if not c.isspace()]) < 10:
            failures.append("abrupt_stop")
    else:
        if len(tokens) < 6:
            failures.append("abrupt_stop")

    # Hollow structure
    newline_ratio = output.count("\n") / max(len(output), 1)
    if newline_ratio > 0.15:
        failures.append("hollow_structure")

    # Prompt ignore: English questions only (heuristic only valid for EN)
    if prompt.strip().endswith("?") and all(ord(c) < 128 for c in prompt):
        first_word = tokens[0].lower().strip(string.punctuation) if tokens else ""
        if first_word in {"i", "he", "she", "they", "we", "it", "the", "a", "an", "so", "well"}:
            failures.append("prompt_ignore")

    # Language confusion: CJK prompt got a Latin-only response (or vice-versa)
    prompt_cjk = _cjk_ratio(prompt) > 0.25
    output_cjk = _cjk_ratio(output) > 0.10
    if prompt_cjk and not output_cjk and len(output) > 20:
        failures.append("lang_confusion")

    return failures


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def utc_timestamp() -> str:
    from datetime import timezone
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def generate_seeded(model: BDHInference, prompt: str, seed: int) -> str:
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    return model.generate_text(prompt)


def run_eval(checkpoint: str = "core/bdh_100m_final.pt") -> Path:
    ts = utc_timestamp()
    out_dir = RUNS_DIR / f"eval_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = LOCKED_CONFIG
    model = BDHInference(
        checkpoint_path=ROOT / checkpoint,
        max_new_tokens=cfg["max_new_tokens"],
        temperature=cfg["temperature"],
        top_k=cfg["top_k"],
    )

    results = []
    raw_scores: list[float] = []
    shaped_scores: list[float] = []
    lang_raw:    dict[str, list[float]] = {l: [] for l in LANGS}
    lang_shaped: dict[str, list[float]] = {l: [] for l in LANGS}

    for p, seed in zip(PROMPTS, SEEDS):
        raw_out    = generate_seeded(model, p["text"],   seed)
        shaped_out = generate_seeded(model, p["shaped"], seed)

        raw_sc    = score_output(raw_out)
        shaped_sc = score_output(shaped_out)
        raw_fail    = detect_failures(p["text"],   raw_out)
        shaped_fail = detect_failures(p["shaped"], shaped_out)

        delta = round(shaped_sc["overall"] - raw_sc["overall"], 3)

        raw_scores.append(raw_sc["overall"])
        shaped_scores.append(shaped_sc["overall"])
        lang_raw[p["lang"]].append(raw_sc["overall"])
        lang_shaped[p["lang"]].append(shaped_sc["overall"])

        results.append({
            "prompt":        p["text"],
            "shaped_prompt": p["shaped"],
            "shape_name":    p["shape"],
            "lang":          p["lang"],
            "seed":          seed,
            "raw":    {"output": raw_out,    "scores": raw_sc,    "failures": raw_fail},
            "shaped": {"output": shaped_out, "scores": shaped_sc, "failures": shaped_fail},
            "delta":  delta,
        })

    avg_raw    = round(sum(raw_scores)    / len(raw_scores),    3)
    avg_shaped = round(sum(shaped_scores) / len(shaped_scores), 3)
    avg_delta  = round(avg_shaped - avg_raw, 3)

    all_failures: dict[str, int] = {}
    for r in results:
        for f in r["raw"]["failures"] + r["shaped"]["failures"]:
            all_failures[f] = all_failures.get(f, 0) + 1

    summary = {
        "config":         cfg,
        "avg_raw":        avg_raw,
        "avg_shaped":     avg_shaped,
        "avg_delta":      avg_delta,
        "lang_avg_raw":    {l: round(sum(v) / len(v), 3) if v else 0.0 for l, v in lang_raw.items()},
        "lang_avg_shaped": {l: round(sum(v) / len(v), 3) if v else 0.0 for l, v in lang_shaped.items()},
        "failure_counts": all_failures,
        "results":        results,
    }

    (out_dir / "results.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # --- Print report ---
    en_avg = round(sum(lang_shaped["en"]) / len(lang_shaped["en"]), 3)
    print(f"\n{'='*60}")
    print(f"  RAW avg:    {avg_raw:.3f}   (72 prompts)")
    print(f"  SHAPED avg: {avg_shaped:.3f}   (delta {avg_delta:+.3f})")
    print(f"\n  Per-language shaped averages:")
    for lang in LANGS:
        scores = lang_shaped[lang]
        avg = round(sum(scores) / len(scores), 3) if scores else 0.0
        marker = " ← EN baseline" if lang == "en" else ""
        print(f"    {lang.upper()}  {avg:.3f}{marker}")
    print(f"{'='*60}")

    if all_failures:
        print("\n  Failure modes detected:")
        for f, count in sorted(all_failures.items(), key=lambda x: -x[1]):
            print(f"    {f:22s}  {count}x")

    print("\n  Per-prompt breakdown (shaped score, delta, failures):")
    for lang in LANGS:
        lang_results = [r for r in results if r["lang"] == lang]
        lang_avg = round(sum(r["shaped"]["scores"]["overall"] for r in lang_results) / len(lang_results), 3)
        print(f"\n  [ {lang.upper()} — avg {lang_avg:.3f} ]")
        for r in lang_results:
            score   = r["shaped"]["scores"]["overall"]
            fail_str = ", ".join(r["shaped"]["failures"]) or "—"
            print(f"  [{score:.2f}  {r['delta']:+.3f}] {r['prompt'][:42]!r:44s}  {fail_str}")

    print(f"\n  Worst shaped per language (floor):")
    for lang in LANGS:
        lang_results = [r for r in results if r["lang"] == lang]
        worst = min(lang_results, key=lambda r: r["shaped"]["scores"]["overall"])
        score = worst["shaped"]["scores"]["overall"]
        print(f"  {lang.upper()}  [{score:.2f}] {worst['shaped_prompt']!r}")
        print(f"         → {worst['shaped']['output']!r}")

    print(f"\nFull results saved to: {out_dir}")
    return out_dir


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="BDH eval harness")
    parser.add_argument(
        "--checkpoint",
        default="core/bdh_100m_final.pt",
        help="Path to checkpoint (default: core/bdh_100m_final.pt)",
    )
    args = parser.parse_args()
    run_eval(args.checkpoint)

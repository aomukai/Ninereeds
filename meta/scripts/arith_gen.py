#!/usr/bin/env python3
"""Generate compact multilingual arithmetic drill files for arithmetic_bridge/.

Phase A — 15 files (c01–c15): full arithmetic foundation (Peano progression)
  c01 identity       c02 same/different   c03 more/less      c04 successor
  c05 zero           c06 add within 5     c07 add within 10  c08 sub + inverse
  c09 comparison     c10 objects add      c11 objects sub     c12 probe format
  c13 sequences      c14 rule application c15 contrastive

Phase B — 5 files (p01–p05): paraphrase equivalence (same facts, varied question surface)
  p01 add paraphrase   p02 sub paraphrase   p03 count paraphrase
  p04 compare paraphrase   p05 word problems

COMPACT format (all Phase A except c12, all Phase B):
  [user]{short question or symbol prompt}
  [Ninereeds]{symbol line}.
  en: {English}.
  de: {German}.
  jp: {Japanese}。
  zh: {Chinese}。

PROBE format (c12 only) — no language labels, exact brain_map probe style:
  [user]what is two plus two?
  [Ninereeds]two plus two is four.

Training order: Phase A (c01→c15) all --no-shuffle, then Phase B (p01→p05) --no-shuffle.
Do not run Phase B until Phase A produces stable arithmetic retrieval on brain_map.

Usage:
  python3 meta/scripts/arith_gen.py [--phase a|b|all] [--pilot] [--force] [--report]
  python3 meta/scripts/arith_gen.py --phase b --workers 3
"""

from __future__ import annotations
import argparse, concurrent.futures, json, os, pathlib, re, sys, time

ROOT    = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "training_data" / "02_thinking" / "arithmetic_bridge"

# ── API (same pattern as phase4_gen.py) ───────────────────────────────────────

def _read_dotenv() -> dict:
    env: dict[str, str] = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

_dotenv = _read_dotenv()

def _get(key: str) -> str | None:
    return os.environ.get(key) or _dotenv.get(key)

def _make_client(key: str, base_url: str):
    from openai import OpenAI
    k = _get(key)
    if not k:
        return None
    return OpenAI(api_key=k, base_url=base_url)

def _sources():
    src = []
    nim = _make_client("NVIDIA_API_KEY", "https://integrate.api.nvidia.com/v1")
    if nim:
        src.append((nim, "deepseek-ai/deepseek-v4-pro",
                    {"extra_body": {"chat_template_kwargs": {"thinking": False}}}))
    orc = _make_client("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1")
    if orc:
        src.append((orc, "deepseek/deepseek-v4-flash", {}))
    return src

SOURCES = _sources()
if not SOURCES:
    sys.exit("No API key found. Set NVIDIA_API_KEY or OPENROUTER_API_KEY.")


def call_api(system: str, user: str) -> tuple[str, str]:
    last_err = None
    for client, model, extra in SOURCES:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=4096,
                temperature=0.3,
                **extra,
            )
            content = resp.choices[0].message.content
            if content and content.strip():
                return content.strip(), model
        except Exception as e:
            last_err = e
    raise RuntimeError(f"All API sources failed: {last_err}")


# ── System prompts ─────────────────────────────────────────────────────────────

COMPACT_SYSTEM = """\
You generate compact multilingual arithmetic training files for a byte-level AI with a 256-byte context window.

MANDATORY FORMAT — no exceptions, no deviations:

[user]{short question or symbolic prompt}
[Ninereeds]{symbolic form: e.g. "2 + 2 = 4."}.
en: {English sentence ending with period}.
de: {German sentence ending with period}.
jp: {Japanese sentence ending with 。}.
zh: {Chinese sentence ending with 。}.

Rules:
- Blank line between every exchange.
- No markdown, no headers, no explanatory text outside the exchange format.
- Each full exchange must be ≤ 160 bytes (critical for 256-byte training windows).
- The [Ninereeds] line starts with the symbolic form, then en:/de:/jp:/zh: lines.
- ALL FOUR language lines are required in every [Ninereeds] response.
- Japanese numbers use kanji where natural: 一二三四五六七八九十
- Chinese numbers use kanji where natural: 一二三四五六七八九十
- Do not repeat the same exchange twice.
- Do not add anything after the last exchange.

CORRECT EXAMPLE:
[user]2 + 2 =?
[Ninereeds]2 + 2 = 4.
en: two plus two is four.
de: zwei plus zwei ist vier.
jp: 二たす二は四です。
zh: 二加二等于四。

[user]is 2 the same as 2?
[Ninereeds]2 = 2.
en: two equals two. two is two.
de: zwei ist gleich zwei. zwei ist zwei.
jp: 二は二と同じです。二は二です。
zh: 二等于二。二就是二。\
"""

PROBE_SYSTEM = """\
You generate probe-format multilingual arithmetic drills. For each arithmetic fact, produce exactly four [user]/[Ninereeds] exchanges — one per language. NO language labels (no en:, de:, jp:, zh:). Each exchange is a direct question-answer pair in that language only.

Question format per language:
- English:  "what is {word} plus {word}?" / "what is {word} minus {word}?"
- German:   "was ist {word} plus {word}?" / "was ist {word} minus {word}?"
- Japanese: "{kanji}たす{kanji}はいくつですか？" / "{kanji}ひく{kanji}はいくつですか？"
- Chinese:  "{kanji}加{kanji}等于多少？" / "{kanji}减{kanji}等于多少？"

Answer format — one sentence, the fact only:
- English:  "{word} plus {word} is {word}."
- German:   "{word} plus {word} ist {word}."
- Japanese: "{kanji}たす{kanji}は{kanji}です。"
- Chinese:  "{kanji}加{kanji}等于{kanji}。"

Blank line between exchanges. No headers, no labels, no extra text.

CORRECT EXAMPLE for fact 2 + 2 = 4:
[user]what is two plus two?
[Ninereeds]two plus two is four.

[user]was ist zwei plus zwei?
[Ninereeds]zwei plus zwei ist vier.

[user]二たす二はいくつですか？
[Ninereeds]二たす二は四です。

[user]二加二等于多少？
[Ninereeds]二加二等于四。\
"""


# ── Job definitions ────────────────────────────────────────────────────────────

PHASE_A_IDS = {"c01","c02","c03","c04","c05","c06","c07","c08","c09","c10","c11","c12","c13","c14","c15"}
PHASE_B_IDS = {"p01","p02","p03","p04","p05"}

JOBS = [
    {
        "id": "c01",
        "filename": "c01_identity.md",
        "format": "compact",
        "min_exchanges": 10,
        "prompt": """\
Generate a compact multilingual arithmetic file teaching NUMBER IDENTITY.

Cover these facts across 12 exchanges:
EQUAL cases (number equals itself): 0=0, 1=1, 2=2, 3=3, 4=4, 5=5
NOT-EQUAL cases (different numbers): 1≠2, 2≠3, 3≠4, 2≠4, 1≠3, 3≠5

Mix question styles:
- Symbol style: [user]2 = 2?  or  [user]2 = 3?
- Word style:   [user]is 2 the same number as 2?  or  [user]is 2 the same as 3?

For ≠ cases, the response should state what the number IS equal to:
[user]2 = 3?
[Ninereeds]2 ≠ 3.
en: two is not three. two is two.
de: zwei ist nicht drei. zwei ist zwei.
jp: 二は三ではありません。二は二です。
zh: 二不等于三。二是二。

Generate all 12 exchanges in the MANDATORY FORMAT.\
""",
    },
    {
        "id": "c02",
        "filename": "c02_same_different.md",
        "format": "compact",
        "min_exchanges": 10,
        "prompt": """\
Generate a compact multilingual arithmetic file teaching SAME vs DIFFERENT quantities.

Cover 12 exchanges alternating between same and different:
- SAME: 2 blocks and 2 blocks, 3 apples and 3 apples, 1 coin and 1 coin, 4 fingers and 4 fingers
- DIFFERENT: 2 blocks and 3 blocks, 1 apple and 4 apples, 3 coins and 5 coins

Use concrete objects: blocks, apples, coins, fingers, cups, dots.
Also include 2 abstract exchanges: "the number 3 and the number 3 are the same number."

For SAME: symbol line uses =. For DIFFERENT: symbol line uses ≠.

Example SAME exchange:
[user]2 blocks and 2 blocks — same or different?
[Ninereeds]2 = 2.
en: two blocks and two blocks are the same amount.
de: zwei Blöcke und zwei Blöcke sind gleich viele.
jp: ブロック二個とブロック二個は同じ数です。
zh: 两个积木和两个积木数量相同。

Example DIFFERENT exchange:
[user]2 blocks and 3 blocks — same or different?
[Ninereeds]2 ≠ 3.
en: two blocks and three blocks are different amounts.
de: zwei Blöcke und drei Blöcke sind verschieden viele.
jp: ブロック二個とブロック三個は違う数です。
zh: 两个积木和三个积木数量不同。

Generate all 12 exchanges.\
""",
    },
    {
        "id": "c03",
        "filename": "c03_more_less.md",
        "format": "compact",
        "min_exchanges": 10,
        "prompt": """\
Generate a compact multilingual arithmetic file teaching MORE THAN / LESS THAN.

Cover 12 exchanges:
MORE THAN (> ): 1>0, 2>1, 3>2, 4>3, 5>4, 3>1, 4>2, 5>1
LESS THAN  (< ): 0<1, 1<2, 2<3, 3<4, 1<4, 2<5

Also include 2 combined exchanges:
"3 is more than 2 and less than 4."  (2 < 3 < 4)
"4 is more than 1 and less than 5."  (1 < 4 < 5)

Mix symbol questions and word questions.

Example MORE exchange:
[user]3 > 2?
[Ninereeds]3 > 2.
en: three is more than two.
de: drei ist mehr als zwei.
jp: 三は二より多い。
zh: 三比二多。

Example LESS exchange:
[user]2 < 3?
[Ninereeds]2 < 3.
en: two is less than three.
de: zwei ist weniger als drei.
jp: 二は三より少ない。
zh: 二比三少。

Generate all 12 exchanges.\
""",
    },
    {
        "id": "c04",
        "filename": "c04_successor.md",
        "format": "compact",
        "min_exchanges": 10,
        "prompt": """\
Generate a compact multilingual arithmetic file teaching SUCCESSOR (what comes next).

Cover 14 exchanges in two styles:

STYLE A — direct successor questions (8 exchanges):
"what comes after 1? 2." for 0→1, 1→2, 2→3, 3→4, 4→5, 5→6, 0→1 (word form), 3→4 (word form)

STYLE B — number sequence questions (6 exchanges):
"1, 2, 3, 4. what comes next? 5."
"0, 1, 2, 3. what comes next? 4."
"2, 3, 4, 5. what comes next? 6."
"1, 3, 5, 7. what comes next? 9." (odd — note the +2 pattern)
"2, 4, 6, 8. what comes next? 10." (even — note the +2 pattern)
"5, 4, 3, 2. what comes next? 1." (decreasing)

Example STYLE A:
[user]what comes after 2?
[Ninereeds]3 comes after 2.
en: three comes after two. two plus one is three.
de: drei kommt nach zwei. zwei plus eins ist drei.
jp: 二の次は三です。二に一を足すと三です。
zh: 二的下一个是三。二加一等于三。

Example STYLE B:
[user]1, 2, 3, 4. what comes next?
[Ninereeds]5.
en: five comes next. add one each time.
de: fünf kommt als nächstes. jedes Mal eins dazuzählen.
jp: 次は五です。毎回一ずつ増えます。
zh: 下一个是五。每次加一。

Generate all 14 exchanges.\
""",
    },
    {
        "id": "c05",
        "filename": "c05_zero.md",
        "format": "compact",
        "min_exchanges": 10,
        "prompt": """\
Generate a compact multilingual arithmetic file teaching ZERO as additive identity.

Cover 12 exchanges across these zero facts:
- Adding zero changes nothing: 2+0=2, 3+0=3, 0+4=4, 0+1=1
- Subtracting zero changes nothing: 3-0=3, 5-0=5
- Subtracting self gives zero: 2-2=0, 4-4=0, 1-1=0
- Zero plus zero: 0+0=0
- What is zero? (1 conceptual exchange)
- Zero compared: 0 < 1, 0 < 2 (1 combined exchange)

Example zero-identity exchange:
[user]2 + 0 =?
[Ninereeds]2 + 0 = 2.
en: two plus zero is two. adding zero changes nothing.
de: zwei plus null ist zwei. null addieren ändert nichts.
jp: 二たすゼロは二です。ゼロを足しても変わりません。
zh: 二加零等于二。加零不改变数值。

Example self-subtraction exchange:
[user]2 - 2 =?
[Ninereeds]2 - 2 = 0.
en: two minus two is zero. nothing is left.
de: zwei minus zwei ist null. es bleibt nichts übrig.
jp: 二ひく二はゼロです。何も残りません。
zh: 二减二等于零。什么都不剩了。

Generate all 12 exchanges.\
""",
    },
    {
        "id": "c06",
        "filename": "c06_add_within5.md",
        "format": "compact",
        "min_exchanges": 10,
        "prompt": """\
Generate a compact multilingual arithmetic file for ALL ADDITION FACTS WITHIN 5.

Cover every addition fact where both addends and the sum are ≤ 5:
1+1=2, 1+2=3, 2+1=3, 1+3=4, 3+1=4, 2+2=4, 1+4=5, 4+1=5, 2+3=5, 3+2=5

That is 10 facts = 10 exchanges. For each:
- Symbol question form: [user]1 + 1 =?
- The [Ninereeds] response includes the symbol line + all 4 language handles.
- Also include a surface-form variation in the en: line: "one and one make two."

Example:
[user]2 + 3 =?
[Ninereeds]2 + 3 = 5.
en: two plus three is five. two and three make five.
de: zwei plus drei ist fünf. zwei und drei ergibt fünf.
jp: 二たす三は五です。二と三で五になります。
zh: 二加三等于五。二和三合起来是五。

Generate all 10 exchanges, one per addition fact.\
""",
    },
    {
        "id": "c07",
        "filename": "c07_add_within10.md",
        "format": "compact",
        "min_exchanges": 10,
        "prompt": """\
Generate a compact multilingual arithmetic file for ADDITION FACTS where sum is 6–10.

Cover these facts (both orderings where applicable):
sum=6:  3+3=6, 4+2=6, 2+4=6, 5+1=6, 1+5=6
sum=7:  4+3=7, 3+4=7, 5+2=7, 2+5=7
sum=8:  4+4=8, 5+3=8, 3+5=8
sum=9:  5+4=9, 4+5=9
sum=10: 5+5=10

That is 15 facts — generate 12 (skip some mirror pairs to keep file compact).

Example:
[user]4 + 3 =?
[Ninereeds]4 + 3 = 7.
en: four plus three is seven.
de: vier plus drei ist sieben.
jp: 四たす三は七です。
zh: 四加三等于七。

Generate 12 exchanges.\
""",
    },
    {
        "id": "c08",
        "filename": "c08_sub_inverse.md",
        "format": "compact",
        "min_exchanges": 10,
        "prompt": """\
Generate a compact multilingual arithmetic file teaching SUBTRACTION AS INVERSE OF ADDITION.

CRITICAL: each exchange must show BOTH the addition AND its inverse subtraction in the SAME [Ninereeds] response. This ensures the inverse relationship co-activates within one 256-byte window.

Cover 10 fact pairs:
1+1=2 ↔ 2-1=1
1+2=3 ↔ 3-1=2, 3-2=1
2+2=4 ↔ 4-2=2
1+3=4 ↔ 4-1=3, 4-3=1
2+3=5 ↔ 5-2=3, 5-3=2
3+3=6 ↔ 6-3=3
4+2=6 ↔ 6-4=2, 6-2=4
4+3=7 ↔ 7-4=3, 7-3=4
5+5=10 ↔ 10-5=5

Example:
[user]2 + 2 and 4 - 2?
[Ninereeds]2 + 2 = 4. 4 - 2 = 2.
en: two plus two is four. four minus two is two.
de: zwei plus zwei ist vier. vier minus zwei ist zwei.
jp: 二たす二は四です。四ひく二は二です。
zh: 二加二等于四。四减二等于二。

Generate 10 exchanges, each pairing addition with its inverse.\
""",
    },
    {
        "id": "c09",
        "filename": "c09_comparison.md",
        "format": "compact",
        "min_exchanges": 10,
        "prompt": """\
Generate a compact multilingual arithmetic file comparing ARITHMETIC RESULTS.

Cover 12 exchanges where the question compares two computed values or an expression to a number:
- "is 2+3 more than 4?"  → yes: 5 > 4
- "is 2+1 the same as 4-1?"  → yes: 3 = 3
- "which is more: 3+1 or 2+2?"  → they are the same: 4 = 4
- "is 5-2 less than 4?"  → yes: 3 < 4
- Also include ordering: "4 > 3 > 2 > 1"

Mix symbol and word question forms. Show the computed result in the symbol line.

Example:
[user]2 + 3 > 4?
[Ninereeds]5 > 4. 2 + 3 = 5.
en: two plus three is five. five is more than four.
de: zwei plus drei ist fünf. fünf ist mehr als vier.
jp: 二たす三は五です。五は四より多い。
zh: 二加三等于五。五比四多。

Generate 12 exchanges.\
""",
    },
    {
        "id": "c10",
        "filename": "c10_objects_add.md",
        "format": "compact",
        "min_exchanges": 10,
        "prompt": """\
Generate a compact multilingual arithmetic file for OBJECT-GROUNDED ADDITION.

Use these object types across 12 exchanges: blocks, apples, coins, fingers, dogs, cups.
For each exchange: a concrete physical situation → the arithmetic result.
Include the symbolic form AND the physical object language in each response.

Example with blocks:
[user]2 red blocks and 2 more red blocks. how many?
[Ninereeds]2 + 2 = 4.
en: two red blocks and two more make four red blocks.
de: zwei rote Blöcke und zwei weitere ergeben vier rote Blöcke.
jp: 赤いブロックが二個あります。さらに二個。合わせて四個です。
zh: 两个红色积木再加两个，一共四个积木。

Example with apples:
[user]3 apples. 2 more apples. how many?
[Ninereeds]3 + 2 = 5.
en: three apples and two more apples make five apples.
de: drei Äpfel und zwei weitere Äpfel sind fünf Äpfel.
jp: リンゴが三個あります。さらに二個で五個です。
zh: 三个苹果再加两个，一共五个苹果。

Cover facts: 1+1, 2+2, 2+3, 3+1, 4+1, 3+3, 2+4, 4+2, 3+2, 5+1, 1+4, 2+1 (choose 12).
Use a different object for each exchange. Generate 12 exchanges.\
""",
    },
    {
        "id": "c11",
        "filename": "c11_objects_sub.md",
        "format": "compact",
        "min_exchanges": 10,
        "prompt": """\
Generate a compact multilingual arithmetic file for OBJECT-GROUNDED SUBTRACTION.

Use these object types: blocks, apples, coins, fingers, dogs, cups.
Each exchange: a taking-away or eating-up physical situation → the arithmetic result.
Include the symbolic form AND the physical language in each response.

Example:
[user]5 apples. eat 2. how many left?
[Ninereeds]5 - 2 = 3.
en: five apples minus two apples leaves three apples.
de: fünf Äpfel minus zwei Äpfel ergibt drei Äpfel.
jp: リンゴが五個あります。二個食べると三個残ります。
zh: 五个苹果吃掉两个，还剩三个。

Cover facts: 2-1=1, 3-1=2, 3-2=1, 4-1=3, 4-2=2, 4-3=1, 5-1=4, 5-2=3, 5-3=2, 5-4=1, 6-3=3, 4-4=0.
Use a different object for each exchange. Generate 12 exchanges.\
""",
    },
    {
        "id": "c12",
        "filename": "c12_probe_multilingual.md",
        "format": "probe",
        "min_exchanges": 20,  # 4 langs × 5+ facts
        "prompt": """\
Generate probe-format multilingual arithmetic drills.

For each arithmetic fact below, generate 4 exchanges (one per language) in this order: English, German, Japanese, Chinese. No language labels. Blank line between exchanges. Blank line between fact groups.

Cover these facts:
ADDITION: 1+1=2, 1+2=3, 2+2=4, 2+3=5, 3+3=6, 4+2=6, 3+4=7, 4+4=8, 5+4=9, 5+5=10
SUBTRACTION: 2-1=1, 3-2=1, 4-2=2, 5-2=3, 5-3=2, 4-3=1, 6-3=3, 4-1=3, 3-1=2, 5-4=1

That is 20 facts × 4 languages = 80 exchanges total.

CRITICAL: use EXACTLY the probe question format:
- EN: "what is {word} plus/minus {word}?"
- DE: "was ist {word} plus/minus {word}?"
- JP: "{kanji}たす/ひく{kanji}はいくつですか？"
- ZH: "{kanji}加/减{kanji}等于多少？"

Answer is ONE sentence only — the fact.\
""",
    },
    {
        "id": "c13",
        "filename": "c13_sequences.md",
        "format": "compact",
        "min_exchanges": 10,
        "prompt": """\
Generate a compact multilingual arithmetic file for NUMBER SEQUENCES and PATTERNS.

Cover 12 exchanges across three pattern types:

TYPE A — +1 sequences (4 exchanges):
"0, 1, 2, 3. what comes next? 4."
"1, 2, 3, 4. what comes next? 5."
"3, 4, 5, 6. what comes next? 7."
"6, 7, 8, 9. what comes next? 10."

TYPE B — +2 sequences (4 exchanges):
"0, 2, 4, 6. what comes next? 8." (even numbers)
"1, 3, 5, 7. what comes next? 9." (odd numbers)
"2, 4, 6, 8. what comes next? 10."
"0, 2, 4, 6, 8. what comes next? 10."

TYPE C — decreasing (2 exchanges) and rule statement (2 exchanges):
"5, 4, 3, 2. what comes next? 1."
"10, 8, 6, 4. what comes next? 2." (subtract 2)
Rule statement: "the rule is: add one each time."
Rule statement: "the rule is: add two each time. these are even numbers."

Example TYPE A:
[user]1, 2, 3, 4. what comes next?
[Ninereeds]5. rule: +1.
en: five comes next. add one each time.
de: fünf kommt als nächstes. jedes Mal eins addieren.
jp: 次は五です。毎回一ずつ増えます。
zh: 下一个是五。每次加一。

Example rule statement:
[user]2, 4, 6, 8. what is the rule?
[Ninereeds]rule: +2. these are even numbers.
en: add two each time. these are even numbers.
de: jedes Mal zwei addieren. das sind gerade Zahlen.
jp: 毎回二ずつ増えます。これらは偶数です。
zh: 每次加二。这些是偶数。

Generate all 12 exchanges.\
""",
    },
    {
        "id": "c14",
        "filename": "c14_rule_application.md",
        "format": "compact",
        "min_exchanges": 10,
        "prompt": """\
Generate a compact multilingual arithmetic file for RULE APPLICATION (ALeRT-style).

Format for each exchange:
[user]rule: {operation}. input: {number}.
[Ninereeds]output: {result}.
en: the rule says {operation}. {number} becomes {result}.
de: die Regel lautet {operation}. aus {number} wird {result}.
jp: ルール：{operation}。{number}は{result}になります。
zh: 规则：{operation}。{number}变成{result}。

Cover these rules and inputs across 12 exchanges:
- rule: add one → inputs: 0, 1, 2, 3, 4 (5 exchanges)
- rule: add two → inputs: 0, 2, 3 (3 exchanges)
- rule: subtract one → inputs: 2, 3, 5 (3 exchanges)
- rule: double (multiply by two) → inputs: 1, 2, 3 (1 exchange, pick one)

Example:
[user]rule: add one. input: 3.
[Ninereeds]output: 4.
en: the rule says add one. three becomes four.
de: die Regel lautet: eins addieren. aus drei wird vier.
jp: ルール：一を足す。三は四になります。
zh: 规则：加一。三变成四。

Generate 12 exchanges.\
""",
    },
    {
        "id": "c15",
        "filename": "c15_contrastive.md",
        "format": "compact",
        "min_exchanges": 10,
        "prompt": """\
Generate a compact multilingual arithmetic file with CONTRASTIVE RIGHT/WRONG examples (Bongard-style).

For each exchange: show the correct answer AND one incorrect answer, then state the correct one clearly.

Format:
[user]right or wrong: 2 + 2 = 5?
[Ninereeds]2 + 2 = 4, not 5.
en: two plus two is four, not five. four is correct.
de: zwei plus zwei ist vier, nicht fünf. vier ist richtig.
jp: 二たす二は四です。五ではありません。
zh: 二加二等于四，不是五。四才是正确答案。

Cover 12 contrastive exchanges:
- Addition errors: 2+2=5 (should be 4), 3+1=5 (should be 4), 2+3=4 (should be 5)
- Subtraction errors: 4-2=3 (should be 2), 3-1=1 (should be 2), 5-3=1 (should be 2)
- Comparison errors: "3 > 4" (wrong: 3 < 4), "2 = 3" (wrong: 2 ≠ 3)
- Successor errors: "after 3 comes 5" (wrong: 4), "after 4 comes 3" (wrong: 5)
- Zero errors: "2 + 0 = 0" (wrong: 2), "0 + 0 = 1" (wrong: 0)

Also include 2 Bongard-style block comparisons:
right: 2+2=4. right: 3+1=4. right: 5-1=4. rule: the answer is 4.
right: 1<2. right: 2<3. right: 3<4. no: 4<3. rule: each number is less than the next.

Generate 12 exchanges.\
""",
    },

    # ── Phase B: paraphrase equivalence ──────────────────────────────────────────

    {
        "id": "p01",
        "filename": "p01_add_paraphrase.md",
        "format": "compact",
        "min_exchanges": 10,
        "prompt": """\
Generate a compact multilingual arithmetic file for ADDITION PARAPHRASE EQUIVALENCE.

Same addition facts as before (sums 2–10), but ask each fact with a DIFFERENT question surface form.
Do NOT use "X + Y =?" style. Use natural language question forms only.

Use these 4 question frames, cycling through them:
  Frame 1: "how much is {word} and {word}?"
  Frame 2: "{word} and {word} together — how many?"
  Frame 3: "if you add {word} and {word}, what do you get?"
  Frame 4: "what does {word} plus {word} make?"

Cover 12 facts using all 4 frames (3 facts per frame):
  Frame 1: 1+1=2, 2+3=5, 4+3=7
  Frame 2: 1+2=3, 3+3=6, 4+4=8
  Frame 3: 1+3=4, 4+2=6, 5+4=9
  Frame 4: 2+2=4, 3+4=7, 5+5=10

The [Ninereeds] response format stays the same: symbol line + en:/de:/jp:/zh:

Example Frame 1:
[user]how much is two and three?
[Ninereeds]2 + 3 = 5.
en: two and three make five.
de: zwei und drei ergibt fünf.
jp: 二と三で五です。
zh: 二和三合起来是五。

Example Frame 3:
[user]if you add two and two, what do you get?
[Ninereeds]2 + 2 = 4.
en: adding two and two gives four.
de: zwei und zwei zusammen ergibt vier.
jp: 二と二を足すと四になります。
zh: 二加二得到四。

Generate all 12 exchanges.\
""",
    },
    {
        "id": "p02",
        "filename": "p02_sub_paraphrase.md",
        "format": "compact",
        "min_exchanges": 10,
        "prompt": """\
Generate a compact multilingual arithmetic file for SUBTRACTION PARAPHRASE EQUIVALENCE.

Same subtraction facts (results 0–5), but ask with natural language question forms.
Do NOT use "X - Y =?" style.

Use these 4 question frames:
  Frame 1: "take {word} from {word} — what is left?"
  Frame 2: "if you have {word} and use {word}, how many remain?"
  Frame 3: "what is {word} with {word} removed?"
  Frame 4: "{word} take away {word} — how much?"

Cover 12 facts:
  Frame 1: 3-1=2, 5-2=3, 4-3=1
  Frame 2: 5-1=4, 4-2=2, 6-3=3
  Frame 3: 3-2=1, 5-3=2, 4-1=3
  Frame 4: 2-1=1, 5-4=1, 4-4=0

Example Frame 1:
[user]take two from five — what is left?
[Ninereeds]5 - 2 = 3.
en: taking two from five leaves three.
de: wenn man zwei von fünf wegnimmt, bleiben drei.
jp: 五から二を取ると三が残ります。
zh: 五取走两个，剩下三个。

Example Frame 2:
[user]if you have four and use two, how many remain?
[Ninereeds]4 - 2 = 2.
en: four with two used leaves two.
de: von vier bleibt nach zwei verbrauchten zwei übrig.
jp: 四から二を使うと二が残ります。
zh: 有四个，用掉两个，还剩两个。

Generate all 12 exchanges.\
""",
    },
    {
        "id": "p03",
        "filename": "p03_count_paraphrase.md",
        "format": "compact",
        "min_exchanges": 10,
        "prompt": """\
Generate a compact multilingual arithmetic file for COUNTING / SUCCESSOR PARAPHRASE EQUIVALENCE.

Same successor facts (0→1 through 9→10), but use varied natural language framings.
Do NOT use "what comes after X?" (that is Phase A c04 style).

Use these 4 question frames:
  Frame 1: "count one more from {word}. what do you reach?"
  Frame 2: "{word} and one more is?"
  Frame 3: "the number after {word} is what?"
  Frame 4: "add one to {word}. result?"

Cover 12 successors:
  Frame 1: 0→1, 3→4, 7→8
  Frame 2: 1→2, 4→5, 8→9
  Frame 3: 2→3, 5→6, 9→10
  Frame 4: 0→1 (word form), 6→7, 4→5 (word form)

Also include 2 exchanges showing COUNTING as repeated successor:
"count from one to five: 1, 2, 3, 4, 5."

Example Frame 1:
[user]count one more from three. what do you reach?
[Ninereeds]3 + 1 = 4.
en: counting one more from three reaches four.
de: von drei einen weiterzählen ergibt vier.
jp: 三から一つ数えると四に着きます。
zh: 从三数一个，到达四。

Example Frame 2:
[user]four and one more is?
[Ninereeds]4 + 1 = 5.
en: four and one more is five.
de: vier und noch eins ist fünf.
jp: 四にもう一つで五です。
zh: 四再加一个是五。

Generate 12 exchanges.\
""",
    },
    {
        "id": "p04",
        "filename": "p04_compare_paraphrase.md",
        "format": "compact",
        "min_exchanges": 10,
        "prompt": """\
Generate a compact multilingual arithmetic file for COMPARISON PARAPHRASE EQUIVALENCE.

Same comparison facts (numbers 0–10), but ask with varied natural language forms.
Do NOT use "X > Y?" or "X < Y?" (that is Phase A c03/c09 style).

Use these 4 question frames:
  Frame 1: "which is bigger: {word} or {word}?"
  Frame 2: "is {word} a larger number than {word}?"
  Frame 3: "{word} or {word} — which is more?"
  Frame 4: "does {word} equal {word}, or is one bigger?"

Cover 12 comparisons (mix of >, <, = cases):
  Frame 1: 3>2, 5>1, 4=4, 2<5
  Frame 2: 4>3, 2<6, 3=3
  Frame 3: 6>4, 1<5
  Frame 4: 3≠5, 4=4, 2<3

For EQUAL answers, make clear both numbers are the same size.
For BIGGER answers, name the winner clearly.

Example Frame 1 (bigger):
[user]which is bigger: three or two?
[Ninereeds]3 > 2.
en: three is bigger than two. three is more.
de: drei ist größer als zwei. drei ist mehr.
jp: 三は二より大きい。三の方が多い。
zh: 三比二大。三更多。

Example Frame 4 (equal):
[user]does four equal four, or is one bigger?
[Ninereeds]4 = 4.
en: four equals four. they are the same size.
de: vier ist gleich vier. sie sind gleich groß.
jp: 四は四と同じです。同じ大きさです。
zh: 四等于四。它们一样大。

Generate 12 exchanges.\
""",
    },
    {
        "id": "p05",
        "filename": "p05_word_problems.md",
        "format": "compact",
        "min_exchanges": 10,
        "prompt": """\
Generate a compact multilingual arithmetic file for EMBEDDED WORD PROBLEMS.

These embed arithmetic facts inside a short physical situation — no named characters, no pronouns.
The model must extract the arithmetic from the narrative and state the result.

Use these object types: apples, blocks, coins, cups, fish, dogs, birds, flowers.
Cover 12 word problems across addition and subtraction:

ADDITION problems (6):
  "a basket holds two apples. three more apples are placed in the basket."
  "a table has four blocks. one more block is added."
  "a pond has three fish. two more fish swim in."
  "a bowl has two coins. four more coins are dropped in."
  "a tree has five birds. one more bird lands."
  "a garden has two flowers. three more flowers grow."

SUBTRACTION problems (6):
  "a basket holds five apples. two apples are taken out."
  "a table has four blocks. two blocks are removed."
  "a pond has six fish. three fish swim away."
  "a bowl has four coins. one coin is taken."
  "a tree has five birds. three birds fly away."
  "a garden has four flowers. one flower is picked."

Example addition:
[user]a basket holds two apples. three more apples are placed in the basket. how many apples?
[Ninereeds]2 + 3 = 5.
en: two apples and three more make five apples in the basket.
de: zwei Äpfel und drei weitere ergeben fünf Äpfel im Korb.
jp: リンゴが二個あり、さらに三個入れると五個になります。
zh: 篮子里有两个苹果，再放入三个，共有五个苹果。

Example subtraction:
[user]a pond has six fish. three fish swim away. how many fish remain?
[Ninereeds]6 - 3 = 3.
en: six fish with three gone leaves three fish in the pond.
de: sechs Fische minus drei wegschwimmende ergibt drei Fische im Teich.
jp: 六匹の魚から三匹が去ると、池には三匹残ります。
zh: 池塘有六条鱼，游走三条，还剩三条。

Generate all 12 exchanges.\
""",
    },
]

JOB_MAP = {j["id"]: j for j in JOBS}


# ── Validation ─────────────────────────────────────────────────────────────────

def validate(text: str, job: dict) -> list[str]:
    issues = []
    user_count = len(re.findall(r"^\[user\]", text, re.MULTILINE))
    nr_count   = len(re.findall(r"^\[Ninereeds\]", text, re.MULTILINE))

    if user_count < job["min_exchanges"]:
        issues.append(f"too few [user] turns: {user_count} < {job['min_exchanges']}")
    if nr_count != user_count:
        issues.append(f"tag mismatch: {user_count} [user] vs {nr_count} [Ninereeds]")

    if job["format"] == "compact":
        nr_blocks = re.findall(
            r"^\[Ninereeds\](.*?)(?=^\[user\]|\Z)", text, re.MULTILINE | re.DOTALL
        )
        missing_lang = []
        for i, block in enumerate(nr_blocks, 1):
            for label in ("en:", "de:", "jp:", "zh:"):
                if label not in block:
                    missing_lang.append(f"block {i} missing {label}")
        if missing_lang:
            issues.append("missing language labels: " + "; ".join(missing_lang[:5]))

        # Check no block is unexpectedly long (> 300 bytes — warns, doesn't fail)
        for i, block in enumerate(nr_blocks, 1):
            full = f"[Ninereeds]{block}"
            if len(full.encode("utf-8")) > 300:
                issues.append(f"block {i} oversized: {len(full.encode())} bytes")

    elif job["format"] == "probe":
        # Check all 4 languages appear
        has_jp = bool(re.search(r"[぀-ゟ゠-ヿ]", text))
        has_zh = bool(re.search(r"[一-鿿]", text))
        has_de = bool(re.search(r"\bwas ist\b", text, re.IGNORECASE))
        if not has_jp:
            issues.append("no Japanese characters found")
        if not has_zh:
            issues.append("no Chinese characters found")
        if not has_de:
            issues.append("no German ('was ist') found")
        # Check no language labels
        for label in ("en:", "de:", "jp:", "zh:"):
            if label in text:
                issues.append(f"probe format should not contain language label '{label}'")

    return issues


# ── Worker ─────────────────────────────────────────────────────────────────────

def process_job(job: dict, force: bool = False) -> dict:
    jid      = job["id"]
    outpath  = OUT_DIR / job["filename"]

    if outpath.exists() and not force:
        return {"id": jid, "status": "skip", "path": str(outpath)}

    system = COMPACT_SYSTEM if job["format"] == "compact" else PROBE_SYSTEM
    user   = job["prompt"]

    for attempt in range(1, 3):
        try:
            raw, model = call_api(system, user)
        except Exception as e:
            return {"id": jid, "status": "error", "msg": str(e)}

        # Strip markdown fences if model wrapped output
        text = re.sub(r"^```[^\n]*\n|```$", "", raw, flags=re.MULTILINE).strip()

        issues = validate(text, job)
        if not issues:
            outpath.write_text(text + "\n", encoding="utf-8")
            return {"id": jid, "status": "ok", "model": model, "path": str(outpath)}

        print(f"  [{jid}] attempt {attempt} issues: {issues}")
        if attempt == 1:
            # Retry with issues fed back to model
            feedback = (
                f"Your output had these problems:\n" +
                "\n".join(f"- {i}" for i in issues) +
                "\n\nPlease regenerate the complete file fixing all issues."
            )
            user = f"{job['prompt']}\n\n{feedback}"

    return {"id": jid, "status": "warn", "issues": issues, "path": str(outpath)}


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Generate arithmetic_bridge compact multilingual files")
    ap.add_argument("--phase",   default="a", choices=["a","b","all"],
                    help="which phase to run: a (c01-c15), b (p01-p05), all (default: a)")
    ap.add_argument("--pilot",   action="store_true", help="run first 5 jobs of selected phase")
    ap.add_argument("--force",   action="store_true", help="regenerate even if file exists")
    ap.add_argument("--report",  action="store_true", help="show job status without generating")
    ap.add_argument("--jobs",    default="",          help="comma-separated job IDs, e.g. c01,p02")
    ap.add_argument("--workers", type=int, default=2, help="parallel workers (default 2)")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Filter by phase first
    if args.phase == "a":
        phase_jobs = [j for j in JOBS if j["id"] in PHASE_A_IDS]
    elif args.phase == "b":
        phase_jobs = [j for j in JOBS if j["id"] in PHASE_B_IDS]
    else:
        phase_jobs = JOBS

    # Select jobs
    if args.jobs:
        ids = [j.strip() for j in args.jobs.split(",")]
        jobs = [JOB_MAP[i] for i in ids if i in JOB_MAP]
        unknown = [i for i in ids if i not in JOB_MAP]
        if unknown:
            print(f"Unknown job IDs: {unknown}")
    elif args.pilot:
        jobs = phase_jobs[:5]
    else:
        jobs = phase_jobs

    if args.report:
        print(f"\n{'ID':<6} {'File':<32} {'Exists':<7} {'Format'}")
        print("-" * 60)
        for j in jobs:
            p = OUT_DIR / j["filename"]
            print(f"  {j['id']:<6} {j['filename']:<32} {'yes' if p.exists() else 'no':<7} {j['format']}")
        print(f"\n{len(jobs)} jobs total.")
        return

    print(f"\nGenerating {len(jobs)} arithmetic bridge files → {OUT_DIR.relative_to(ROOT)}/")
    print(f"Workers: {args.workers}  |  Force: {args.force}\n")

    results = {"ok": [], "skip": [], "warn": [], "error": []}

    if args.workers == 1:
        for j in jobs:
            print(f"  [{j['id']}] {j['filename']} ...", flush=True)
            r = process_job(j, force=args.force)
            results[r["status"]].append(r)
            print(f"  [{j['id']}] {r['status']}" + (f" ({r.get('model','')})" if r["status"] == "ok" else ""))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(process_job, j, args.force): j for j in jobs}
            for fut in concurrent.futures.as_completed(futs):
                j = futs[fut]
                r = fut.result()
                results[r["status"]].append(r)
                suffix = f" ({r.get('model','')})" if r["status"] == "ok" else \
                         (f" — {r.get('msg','')[:60]}" if r["status"] == "error" else "")
                print(f"  [{j['id']}] {r['status']}{suffix}")

    print(f"\nDone: {len(results['ok'])} ok, {len(results['skip'])} skip, "
          f"{len(results['warn'])} warn, {len(results['error'])} error")

    if results["warn"]:
        print("\nWarnings:")
        for r in results["warn"]:
            print(f"  {r['id']}: {r.get('issues','')}")
    if results["error"]:
        print("\nErrors:")
        for r in results["error"]:
            print(f"  {r['id']}: {r.get('msg','')}")


if __name__ == "__main__":
    main()

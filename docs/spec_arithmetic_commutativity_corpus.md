# Corpus Spec: Arithmetic Commutativity & Non-Commutativity
**Status:** Draft — weekday corpus task, post-training-weekend  
**Fits into:** `arithmetic_bridge/` track — separate from Phase A–E entirely. Only introduced once the language curriculum is established and a reasoning campaign begins. Inserting arithmetic content during language phases adds noise without grounding.

---

## Motivation

The existing counting corpus (00–02) establishes number concepts and basic arithmetic in three languages. This extension adds a structural layer: the difference between operations where order is free (addition) and operations where order is load-bearing (subtraction).

This mirrors the grammar insight: German case inflection frees word order because the morphology carries relational information. English strict SVO is required *because* there is no such marking. Addition is commutative for the same reason cases are flexible — the operation itself preserves the relationship regardless of presentation order. Subtraction is not commutative for the same reason English word order is rigid — without a marker, sequence is the only carrier of meaning.

Teaching both, and the contrast between them, gives Ninereeds a cross-domain structural analogy that may support generalisation in both the reasoning and language tracks.

---

## Research Goal

The purpose of this corpus is not primarily arithmetic fluency.

The purpose is to teach structural relationships:

- Some operations preserve meaning when their inputs are reordered.
- Some operations change meaning when their inputs are reordered.
- Some roles are symmetric.
- Some roles are asymmetric.

Arithmetic provides a simple and highly controlled environment for introducing these concepts before they appear in more complex domains such as grammar, reasoning, and narrative causality.

This corpus therefore serves as a structural reasoning bridge rather than a mathematics curriculum.

---

## Register Sets

Each arithmetic fact is presented in three registers:

| Register | Example |
|---|---|
| Symbolic | `1+2=3` |
| Formal verbal | "one plus two equals three" |
| Informal verbal | "one and two is three" |

All three registers appear for every fact. This matches the bidirectional word↔symbol design of the existing bridge files.

### Note on informal subtraction

Natural language resists non-commutative informal phrasing. "Two and five, take away" is not natural. The informal register for subtraction should reflect this honestly — it may use "take away" directionality ("five take away two is three") and the non-commutative contrast should be shown in formal and symbolic registers primarily, with a note in informal that the phrasing itself encodes direction.

---

## File Structure

Mirrors existing naming convention. Suggested files:

```
03_arithmetic_commutative_DE.md       — addition pairs, German, all 3 registers
03_arithmetic_commutative_ZH.md       — addition pairs, Chinese, all 3 registers
03_arithmetic_commutative_JP.md       — addition pairs, Japanese, all 3 registers
03_arithmetic_commutative_EN.md       — addition pairs, English, all 3 registers

04_arithmetic_noncommutative_DE.md    — subtraction pairs + contrast, German
04_arithmetic_noncommutative_ZH.md    — subtraction pairs + contrast, Chinese
04_arithmetic_noncommutative_JP.md    — subtraction pairs + contrast, Japanese
04_arithmetic_noncommutative_EN.md    — subtraction pairs + contrast, English

05_arithmetic_contrast_EN.md          — explicit commutative vs non-commutative
                                         contrast, English only (anchor file)
```

The contrast file (05) is the pedagogical payoff — it names the difference explicitly after the model has seen both patterns. One language only to keep it clean.

---

## Content Spec: Commutative Files (03_*)

For each addition pair `a+b=c / b+a=c`:

```
[user] What is {a} plus {b}?
[Ninereeds] {a} plus {b} equals {c}.
[user] What is {b} plus {a}?
[Ninereeds] {b} plus {a} equals {c}.
[user] How do you write that in numbers?
[Ninereeds] {a}+{b}={c} and {b}+{a}={c}.
[user] What is {a} and {b}?
[Ninereeds] {a} and {b} is {c}.
[user] What is {b} and {a}?
[Ninereeds] {b} and {a} is {c}.
```

Number range: small pairs only (1–9), enough to establish the pattern without bloat. Approximately 10–12 pairs per file.

---

## Content Spec: Non-Commutative Files (04_*)

For each subtraction pair `a-b=c` with explicit contrast `b-a≠c`:

```
[user] What is {a} minus {b}?
[Ninereeds] {a} minus {b} equals {c}.
[user] What is {b} minus {a}?
[Ninereeds] {b} minus {a} does not equal {c}. The order matters.
[user] How do you write that in numbers?
[Ninereeds] {a}-{b}={c} but {b}-{a}≠{c}.
[user] How do you say "{a} minus {b}" informally?
[Ninereeds] {a} take away {b} is {c}.
[user] Why does the order matter here?
[Ninereeds] Subtraction has a starting number and an amount removed.
            The two roles are not the same.
            Changing the order swaps the roles and changes the result.
```

The "why does the order matter" turn is the structural payoff — it names the role asymmetry directly.

---

## Content Spec: Contrast File (05_arithmetic_contrast_EN.md)

Short. Explicit. Names the pattern.

```
[user] What is the difference between addition and subtraction?
[Ninereeds] Addition combines two amounts. The order does not change the result.
            Subtraction removes one amount from another. The order changes the result.

[user] Why does 1+2 equal 2+1?
[Ninereeds] Both combine the same two amounts.
            The two amounts have the same role.
            Changing the order does not change the result.

[user] Why does 5-2 not equal 2-5?
[Ninereeds] 5-2 starts from five and removes two.
            2-5 starts from two and removes five.
            The two numbers have different roles.
            Changing the order changes the result.

[user] What is a symmetric relationship?
[Ninereeds] A symmetric relationship stays the same when the order changes.
            Addition is symmetric.

[user] What is an asymmetric relationship?
[Ninereeds] An asymmetric relationship changes when the order changes.
            Subtraction is asymmetric.
```

This file should remain arithmetic-only.

Do not introduce language, grammar, German cases, English word order,
or other cross-domain analogies here.

The purpose of 05 is to determine whether the model can learn the
structural distinction itself before any cross-domain transfer is attempted.

---

## Content Spec: 06_arithmetic_language_bridge_EN.md

Optional. Not part of the initial arithmetic campaign.

Only introduced after arithmetic and grammar curricula have both been trained successfully.

Purpose: test whether Ninereeds can transfer structural concepts between domains.

```
[user] Why does 1+2 equal 2+1?
[Ninereeds] Addition combines the same two amounts.
            Changing the order does not change the result.

[user] Why does 5-2 not equal 2-5?
[Ninereeds] Subtraction uses different roles.
            One number is the starting amount.
            One number is the amount removed.

[user] Why can German sometimes change word order?
[Ninereeds] German uses case endings to show roles.
            The roles stay clear even when the order changes.

[user] Why is English word order more important?
[Ninereeds] English uses word position to show roles.
            Changing the order can change the meaning.

[user] What do subtraction and English word order have in common?
[Ninereeds] The roles are different.
            Changing the order changes the meaning.

[user] What do addition and German case endings have in common?
[Ninereeds] The relationships stay clear.
            Changing the order does not necessarily change the meaning.
```

This file is an explicit transfer experiment.

It should be trained only after the arithmetic curriculum and the
grammar curriculum have already demonstrated positive learning independently.

### Evaluation Criteria

The purpose of 06 is not to teach the analogy.

The purpose of 06 is to test whether the analogy can be formed from
previously learned arithmetic and grammar concepts.

#### Success

Ninereeds produces coherent cross-domain explanations without having
seen the analogy during training.

Examples:

- Explains that addition is insensitive to order while subtraction is not.
- Explains that German case marking allows more flexible word order.
- Explains that English relies more heavily on position.
- Correctly maps the structural similarities between the two domains.

The exact wording does not matter.

The structural relationship must be preserved.

This indicates transfer learning rather than memorization.

#### Partial Success

Ninereeds identifies some of the relevant concepts but produces
incomplete or inconsistent mappings.

Examples:

- Understands addition vs subtraction.
- Understands German vs English word order.
- Fails to connect the two reliably.

This suggests that the underlying concepts were learned but the
cross-domain bridge has not yet emerged.

#### Failure

Responses are incoherent, contradictory, or unrelated to the structural
distinction.

Examples:

- Repeats memorized arithmetic facts without discussing roles.
- Repeats memorized grammar facts without discussing roles.
- Cannot explain why order matters in one domain but not the other.

#### Strong Failure

The analogy only appears after training on 06 itself.

If the model cannot produce the analogy before seeing 06, but can
repeat it afterward, the file is acting as retrieval material rather
than a transfer test.

In that case, the analogy has been taught directly rather than
discovered.

The corpus should then be treated as instructional material rather than
evidence of emergent transfer.

---

## Generation Instructions for DeepSeek

- Follow the [user]/[Ninereeds] turn format exactly — no deviations
- Match register precisely: symbolic turns use only numerals and operators, formal turns use full words, informal turns use natural phrasing
- Do not add explanatory prose outside the turn format
- Keep Ninereeds responses short and declarative — same style as existing bridge files
- Generate all four language variants per file from the English anchor, preserving structure
- Flag any informal phrasing that feels unnatural in a given language for manual review

---

## Resolved Decisions

- Zero-result subtraction (`a−a=0`) should be included — it's a clean edge case that reinforces role asymmetry and anchors zero as a valid result. Include `a−0=a` as well to show that subtracting nothing leaves the starting number unchanged. Both fit in the 04 non-commutative files.
- Negative results (`2-5=-3`) are out of scope for now — introduces new concept before the structural point is established.
- Japanese counter words (一つ、二つ etc.) vs plain numerals — existing JP files use plain numerals, keep consistent.

---

## Corpus Location

These files belong in a dedicated `training_data/arithmetic_bridge/` directory, separate from `training_data/reasoning/`.

The full arithmetic_bridge curriculum in sequence:

```
arithmetic_bridge/
  00_bridge_word_to_symbol.md   (+ DE, JP, ZH)  ← move from reasoning/
  01_bridge_symbol_to_word.md   (+ DE, JP, ZH)  ← move from reasoning/
  02_counting_*.md               (+ DE, JP, ZH)  ← move from reasoning/
  03_arithmetic_commutative_*.md (+ DE, JP, ZH)  ← new (this spec)
  04_arithmetic_noncommutative_*.md (+ DE, JP, ZH) ← new (this spec)
  05_arithmetic_contrast_EN.md                    ← new (this spec)
```

The `reasoning/` track then covers material that assumes arithmetic vocabulary is already established: multi-step inference, probability, epistemic uncertainty, and so on.

**Note on 00/01 bridge file style:** the existing word↔symbol bridge files use a looser prose style (multi-sentence grounded responses). The new 03–05 files use the tighter declarative format. A light reformatting pass on 00/01 to match register is worth doing before training on the full arithmetic_bridge sequence — not a blocker for *generating* 03–05, but a blocker for *training* on the full sequence. Do not queue the arithmetic_bridge campaign until 00/01 reformatting is complete.

**Note on 05_arithmetic_contrast_EN.md:** this file may also serve as a late-stage bridge between the arithmetic and language tracks once grammar cases are introduced, since the German/English word-order analogy applies directly.

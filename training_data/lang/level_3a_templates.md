# Global Rules — All Levels

These rules apply to every file generated for the Ninereeds corpus.
When a template produces an unnatural result in any language, these rules override it.

---

## Core principle: naturalise, don't translate

The goal is not four parallel versions of the same sentence.
The goal is the same meaning expressed the way a native speaker would express it.
If the English template produces something no native speaker would say in German, Japanese, or Mandarin — rewrite until it sounds natural. Preserve the meaning. The surface form does not have to match.

---

## Show cross-linguistic differences

Languages differ at every level. These differences are features, not problems.
Surface them, don't flatten them.

**Pronoun drop**
Japanese and Mandarin drop subject and object pronouns when the referent is clear from context.

**Verb choice by semantic fit**
Choose the verb that fits the meaning, not the verb that looks like a translation.

**Aspect vs tense**
Mandarin has no grammatical tense. Time is marked by adverbials and aspect particles (了, 在, 过, 会).
Japanese tense is binary (past / non-past). Aspect is marked separately via て-form constructions.

**Register**
Japanese plain form throughout. No ます/です. No keigo.

---

## Naturalness checklist

Before finalising any sentence:

1. Would a native speaker say this, or does it sound like a textbook?
2. Is any word redundant given what came before?
3. Is the verb the right verb for this meaning in this language?
4. Are pronouns present only where the language actually requires them?
5. Does the sentence reveal something about how this language works?

---

# Level 3a — Dative (Indirect Object)

Level 3a introduces the indirect object. Each file covers one verb and one construction type.

English has two surface forms for the dative:
- Double-object: "Tom gives her an apple" (IO before DO, no preposition)
- Prepositional: "Tom gives an apple to her" (DO before IO, "to" marks recipient)

These are separate files. Verbs that allow both forms get two files. Verbs that only allow the prepositional form get one file.

---

## File naming

- `give_1.md` — double-object: "Tom gives her an apple"
- `give_2.md` — prepositional: "Tom gives an apple to her"
- `explain_1.md` — prepositional only (explain does not take double-object)

---

## Which verbs allow which constructions

| Construction | Verbs |
|---|---|
| Double-object AND prepositional | give, show, tell, send, bring, buy, lend, offer, teach, write, hand, pass |
| Prepositional only | explain, describe, suggest, announce, mention, introduce, report |

The distinction is not arbitrary: native Anglo-Saxon verbs typically allow both; Latinate verbs require the prepositional form. "She explained him the problem" is not English. Do not write it.

---

## How each language encodes the recipient

| Language | Mechanism | Example |
|---|---|---|
| English | word order (IO before DO) or "to" preposition | gives her an apple / gives an apple to her |
| German | dative case on the NP or pronoun | gibt ihr einen Apfel / gibt dem Kind einen Apfel |
| Japanese | に particle on the recipient NP + directional verb | 彼女にリンゴをあげる |
| Mandarin | 给 coverb before the recipient | 给她一个苹果 |

Note: German does NOT have a "to" prepositional form for most of these verbs. Both English constructions map to the same German sentence. This is part of what the file teaches.

---

## Reference tables

### German dative pronouns

| EN | DE |
|---|---|
| me | mir |
| you | dir |
| him | ihm |
| her | ihr |
| us | uns |
| them | ihnen |

### German dative NPs

| NP | Dative form |
|---|---|
| das Kind (neut) | dem Kind |
| die Frau (fem) | der Frau |
| der Mann (masc) | dem Mann |
| die Kinder (pl) | den Kindern |
| der Hund (masc) | dem Hund |

### Japanese directional verbs for giving

| Verb | Use when |
|---|---|
| あげる | agent gives to someone else (outward) |
| くれる | someone gives to me or my group (inward) |
| もらう | agent receives from someone |

Do NOT use あげる when the recipient is the speaker. Use くれる.

- "Tom gives her an apple" → トムは彼女にリンゴをあげた ✓
- "She gives me an apple" → 彼女はリンゴをくれた ✓ (recipient に私に usually omitted when it is me)
- "I receive an apple from her" → 彼女にリンゴをもらった ✓

### Mandarin dative constructions

| Construction | Use when | Example |
|---|---|---|
| 给 + IO + DO | IO is a pronoun or short NP | 给她一个苹果 |
| 把 + DO + 给 + IO + 了 | DO is definite or specific | 把苹果给了她 |

---

## Template 1 — Double-object construction

```
[SUBJ] [VERB_PAST] [IO_PRONOUN] [DO].
[SUBJ_DE] hat [IO_DAT] [DO_DE] [VERB_PAST_DE].
[SUBJ_JP]は[IO_JP]に[DO_JP]をあげた。
[SUBJ_ZH]给了[IO_ZH][DO_ZH]。

[SUBJ] [VERB_PRESENT] [IO_NP] [DO].
[SUBJ_DE] [VERB_DE] [IO_NP_DAT] [DO_DE].
[SUBJ_JP]は[IO_NP_JP]に[DO_JP]をあげる。
[SUBJ_ZH]给[IO_NP_ZH][DO_ZH]。

[SUBJ] will [VERB_BASE] [IO_PRONOUN] [DO].
[SUBJ_DE] wird [IO_DAT] [DO_DE] [VERB_BASE_DE].
[SUBJ_JP]は[IO_JP]に[DO_JP]をあげるだろう。
[SUBJ_ZH]会给[IO_ZH][DO_ZH]。
```

### Example — give_1.md

```
Tom gave her an apple.
Tom hat ihr einen Apfel gegeben.
トムは彼女にリンゴをあげた。
汤姆给了她一个苹果。

Tom gives the child a ball.
Tom gibt dem Kind einen Ball.
トムは子供にボールをあげる。
汤姆给孩子一个球。

Tom will give them a book.
Tom wird ihnen ein Buch geben.
トムは彼らに本をあげるだろう。
汤姆会给他们一本书。
```

What this shows:
- DE — dative pronouns ihr, ihnen; dative NP dem Kind (neuter); accusative einen Apfel, einen Ball, ein Buch — all agreeing with gender
- JP — に marks the recipient; あげる encodes outward benefit direction; verb stays the same regardless of who the recipient is
- ZH — 给 + recipient + DO is the natural order; 了 marks completion; no case or article on any noun

---

## Template 2 — Prepositional construction

```
[SUBJ] [VERB_PAST] [DO] to [IO_PRONOUN].
[SUBJ_DE] hat [IO_DAT] [DO_DE] [VERB_PAST_DE].
[SUBJ_JP]は[IO_JP]に[DO_JP]を[VERB_JP]た。
[SUBJ_ZH]把[DO_ZH]给了[IO_ZH]。

[SUBJ] [VERB_PRESENT] [DO] to [IO_NP].
[SUBJ_DE] [VERB_DE] [IO_NP_DAT] [DO_DE].
[SUBJ_JP]は[IO_NP_JP]に[DO_JP]を[VERB_JP]る。
[SUBJ_ZH]把[DO_ZH]给[IO_NP_ZH]。
```

Note: German and Japanese sentences are identical to Template 1 for the same verb. The EN/ZH surface form differs; the DE/JP surface form does not. This is the lesson.

### Example — give_2.md

```
Tom gave an apple to her.
Tom hat ihr einen Apfel gegeben.
トムは彼女にリンゴをあげた。
汤姆把苹果给了她。

Tom gives the ball to the child.
Tom gibt dem Kind den Ball.
トムは子供にボールをあげる。
汤姆把球给孩子。
```

What this shows:
- EN — "to her" makes the recipient visible via preposition; the DO comes first
- DE — maps to the same sentence as give_1.md; German has no "to" prepositional dative
- JP — maps to the same sentence as give_1.md; に already marks the recipient unambiguously
- ZH — 把 construction topicalises the DO; 给 then marks the recipient; this is the natural Chinese form when the DO is definite

### Example — explain_1.md (prepositional only)

```
She explained the rule to him.
Sie hat ihm die Regel erklärt.
彼女は彼にルールを説明した。
她把规则解释给了他。

The teacher explained the plan to the children.
Die Lehrerin hat den Kindern den Plan erklärt.
先生は子供たちに計画を説明した。
老师把计划解释给了孩子们。

She will explain the idea to us.
Sie wird uns die Idee erklären.
彼女は私たちにアイデアを説明するだろう。
她会把想法解释给我们。
```

What this shows:
- EN — explain does not allow double-object; "she explained him the rule" is ungrammatical
- DE — dative ihm, uns, den Kindern (plural); past participle erklärt at the end
- JP — same に structure regardless of verb; explain = 説明する
- ZH — 把-construction with 解释给; Mandarin regularly uses this when explaining something specific

---

## Rules

1. One file per verb per construction type.
2. Verbs allowing both constructions: two files (`verb_1.md` double-object, `verb_2.md` prepositional).
3. Verbs allowing prepositional only: one file (`verb_1.md`).
4. Each file: 3–5 sentence groups, varying tense and participants.
5. German always uses dative case — never a "to" preposition for these verbs.
6. Japanese: あげる / くれる / もらう depending on direction of benefit. Check the reference table.
7. Mandarin: 给 + IO + DO for pronouns and short NPs; 把 + DO + 给 + IO for definite DOs.
8. Vary IO between pronoun (her, him, them) and dative NP (the child, the woman, the children).
9. Use allowlist words for verbs, nouns, and objects.
10. German V2: verb is second constituent. Time adverbials trigger inversion.
11. Do not explain grammar inside the generated files.

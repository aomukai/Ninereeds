# Global Rules — All Levels

These rules apply to every file generated for the Ninereeds corpus.
When a template produces an unnatural result in any language, these rules override it.

---

## Core principle: naturalise, don't translate

The goal is the same meaning expressed the way a native speaker would express it.
Surface form does not have to match across languages.

---

## Show cross-linguistic differences

Languages differ at every level. These differences are features, not problems.
Surface them, don't flatten them.

**Register**
Japanese plain form throughout. No ます/です. No keigo.

**Aspect vs tense**
Mandarin has no grammatical tense. Time is marked by adverbials and aspect particles (了, 在, 过, 会).

**Pronoun drop**
Japanese and Mandarin drop subject and object pronouns when the referent is clear.

---

# Level 3b — Dative + Genitive

Level 3b combines two case relationships in a single sentence: an indirect object (dative) and a genitive possessor inside the direct object.

The canonical example: "He gives the child the dog's ball."
- The indirect object is "the child" (dative).
- The direct object is "the dog's ball" — a noun modified by a possessor (genitive).

No new grammatical features are introduced beyond what is in 3a and 2b. This level teaches Ninereeds to handle multiple case-marked NPs in the same clause.

---

## Structure

```
[SUBJ] [VERB] [IO] [POSS's DO].
```

- IO = indirect object (dative in German, に in Japanese, 给 in Mandarin)
- POSS = possessor of the direct object (genitive in German, の in Japanese, 的 in Mandarin)
- DO = the object being transferred

---

## Reference tables

### German genitive NPs

| NP | Genitive form |
|---|---|
| der Hund (masc) | des Hundes |
| das Kind (neut) | des Kindes |
| die Katze (fem) | der Katze |
| die Kinder (pl) | der Kinder |
| der Mann (masc) | des Mannes |
| die Frau (fem) | der Frau |

### German dative NPs (recap from 3a)

| NP | Dative form |
|---|---|
| das Kind (neut) | dem Kind |
| die Frau (fem) | der Frau |
| der Mann (masc) | dem Mann |
| die Kinder (pl) | den Kindern |

### German word order in the dative + genitive clause

Double-object order: SUBJ VERB IO(DAT) DO(ACC+GEN)
"Er gibt dem Kind den Ball des Hundes."
— dative NP comes before accusative NP, genitive modifier follows the noun it modifies.

### Japanese structure

に marks the IO. の marks possession inside the DO. Particle order is fixed:
[SUBJ]は + [IO]に + [POSS]の[DO]を + [VERB]

Example: 彼は子供に犬のボールをあげた。

### Mandarin structure

给 + IO + [POSS]的[DO]:
他给孩子狗的球。

或 把-construction with definite DO:
他把狗的球给了孩子。

---

## Template

```
[SUBJ] gave [IO] [POSS's DO].
[SUBJ_DE] hat [IO_DAT] [DO_ACC] [POSS_GEN] gegeben.
[SUBJ_JP]は[IO_JP]に[POSS_JP]の[DO_JP]をあげた。
[SUBJ_ZH]给[IO_ZH][POSS]的[DO_ZH]了。

[SUBJ] gives [IO] [POSS's DO].
[SUBJ_DE] gibt [IO_DAT] [DO_ACC] [POSS_GEN].
[SUBJ_JP]は[IO_JP]に[POSS_JP]の[DO_JP]をあげる。
[SUBJ_ZH]给[IO_ZH][POSS]的[DO_ZH]。

[SUBJ] will give [IO] [POSS's DO].
[SUBJ_DE] wird [IO_DAT] [DO_ACC] [POSS_GEN] geben.
[SUBJ_JP]は[IO_JP]に[POSS_JP]の[DO_JP]をあげるだろう。
[SUBJ_ZH]会给[IO_ZH][POSS]的[DO_ZH]。
```

### Example — give (dative + genitive)

```
He gave the child the dog's ball.
Er hat dem Kind den Ball des Hundes gegeben.
彼は子供に犬のボールをあげた。
他给孩子狗的球了。

She gives the woman the cat's food.
Sie gibt der Frau das Futter der Katze.
彼女は女性に猫のエサをあげる。
她给那个女人猫的食物。

Tom will give the children the teacher's book.
Tom wird den Kindern das Buch der Lehrerin geben.
トムは子供たちに先生の本をあげるだろう。
汤姆会给孩子们老师的书。
```

What this shows:
- DE — four case-marked NPs in one sentence: nominative subject, dative IO, accusative DO, genitive possessor. Each NP's article changes by case and gender.
- JP — の and に are both present; の marks possession inside the DO, に marks the recipient; the structure is clean and unambiguous
- ZH — 的 marks possession inside the DO; 给 marks the recipient; no case endings anywhere; word order does the work

---

## Variation: use with other dative verbs

The same template works with any 3a verb. Vary the verb across files.

```
She sent the child the teacher's letter.
Sie hat dem Kind den Brief der Lehrerin geschickt.
彼女は子供に先生の手紙を送った。
她给孩子寄了老师的信。

He showed the woman the dog's trick.
Er hat der Frau den Trick des Hundes gezeigt.
彼は女性に犬の芸を見せた。
他给那个女人看了狗的把戏。
```

---

## File naming

One file per verb. File names match 3a: `give.md`, `send.md`, `show.md`.
No construction-number suffix needed — 3b always uses the double-object structure.

---

## Rules

1. Every sentence in a 3b file contains both a dative IO and a genitive possessor on the DO.
2. Do not use a pronoun possessor in the DO slot (no "his ball", "her book") — use a named possessor or a noun possessor (the dog's, the teacher's). Pronouns on the DO collapse the genitive lesson.
3. German: accusative NP carries genitive modifier — check both the article on the DO and the ending on the possessor noun.
4. Japanese: の for possession inside the DO; に for the IO. Do not confuse them.
5. Mandarin: 的 inside the DO for possession; 给 for the recipient.
6. Vary possessors and IOs across groups within the file: pronoun IO in one group, NP IO in another.
7. Each file: 3–5 groups.
8. Use allowlist words for all nouns and verbs.
9. German V2 word order throughout.
10. Do not explain grammar inside the generated files.

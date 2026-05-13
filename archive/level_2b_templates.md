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
- EN: "Tom has a dog. He loves it."
- JP: 「トムは犬を飼っている。大好きだ。」 — subject and object both dropped, natural
- ZH: 「汤姆有一只狗。很爱它。」 — subject dropped, natural

**Verb choice by semantic fit**
Choose the verb that fits the meaning, not the verb that looks like a translation.
- EN: "has a dog" → DE: hat einen Hund ✓
- EN: "has a dog" → JP: 持っている ✗ (physically carrying) | 飼っている ✓ (keeping/raising)

**Possession restated vs dropped**
If possession is already established or implied by the subject, do not restate it.
- EN: "Tom has a dog. He loves his dog." → his dog is redundant
- Better: "Tom has a dog. He loves it." / JP: 「好きだ。」

**Aspect vs tense**
Mandarin has no grammatical tense. Time is marked by adverbials and aspect particles (了, 在, 过, 会).
Japanese tense is binary (past / non-past). Aspect is marked separately via て-form constructions.

**Register**
Japanese plain form throughout. No ます/です. No keigo.

---

## Redundancy rules

Do not restate what is already established in the same sentence or the sentence before it.

| Situation | Wrong | Right |
|---|---|---|
| Owner already named | Tom has his dog | Tom has a dog |
| Subject clear from context | 彼は彼の犬が好きだ | 好きだ／犬が好きだ |
| Object clear from prior sentence | Er liebt seinen Hund | Er liebt ihn |
| Plural obvious from context | 鳥たちが飛んでいる | 鳥が飛んでいる |

---

## Naturalness checklist

Before finalising any sentence:

1. Would a native speaker say this, or does it sound like a textbook?
2. Is any word redundant given what came before?
3. Is the verb the right verb for this meaning in this language?
4. Are pronouns present only where the language actually requires them?
5. Does the sentence reveal something about how this language works?

If a sentence fails any of these in any language, rewrite that language's version until it passes.

---

## Reference example

**Bad** — translated, redundant, unnatural:
```
Tom has his dog. He loves his dog.
Tom hat seinen Hund. Er liebt seinen Hund.
トムは彼の犬を持っている。彼は彼の犬が好きだ。
汤姆有他的狗。他爱他的狗。
```

**Good** — natural, shows cross-linguistic differences:
```
Tom has a dog. He loves it.
Tom hat einen Hund. Er liebt ihn.
トムは犬を飼っている。大好きだ。
汤姆有一只狗。很爱它。
```

What this shows:
- EN / DE — pronoun replaces noun on second mention; DE accusative ihn (not ihn + noun)
- JP — 飼っている not 持っている (living thing); subject and object both dropped; bare predicate is natural
- ZH — subject dropped; 一只 counter for animals, not 一个; ongoing state takes no aspect particle

---

## A note on instructional value

Sentences that are grammatically correct but unnatural are not useful for Ninereeds.
Ninereeds must learn language as it is used, not as it is described in grammars.
The corpus is the only input. Every unnatural sentence is a false signal.
Every natural sentence that surfaces a cross-linguistic difference is a lesson without an explanation.

---

# Level 2b — Pronouns and Possession

Level 2b introduces two features: pronouns and possession.
Each file focuses on one type. Do not combine pronoun and possession features — that is Level 2c.

---

## Reference tables

These tables are for use during generation. Do not reproduce them in the generated files.

### Personal pronouns

| Person | EN | DE | JP | ZH |
|---|---|---|---|---|
| 1sg | I | ich | 私は／ぼくは | 我 |
| 2sg | you | du | あなたは | 你 |
| 3sg masc | he | er | 彼は | 他 |
| 3sg fem | she | sie | 彼女は | 她 |
| 1pl | we | wir | 私たちは | 我们 |
| 3pl | they | sie | 彼らは | 他们 |

### Possessive pronouns (attributive)

| Person | EN | DE (masc / neut / fem / pl) | JP | ZH |
|---|---|---|---|---|
| 1sg | my | mein / mein / meine / meine | 私の | 我的 |
| 2sg | your | dein / dein / deine / deine | あなたの | 你的 |
| 3sg masc | his | sein / sein / seine / seine | 彼の | 他的 |
| 3sg fem | her | ihr / ihr / ihre / ihre | 彼女の | 她的 |
| 1pl | our | unser / unser / unsere / unsere | 私たちの | 我们的 |
| 3pl | their | ihr / ihr / ihre / ihre | 彼らの | 他们的 |

### Proper name possession

| Language | Form | Example |
|---|---|---|
| EN | Name + 's + noun | Tom's apple |
| DE | Name + s + noun (no apostrophe) | Toms Apfel |
| JP | Name + の + noun | トムのリンゴ |
| ZH | Name + 的 + noun | 汤姆的苹果 |

### Notes
- German possessives agree with the gender and case of the noun they modify, not the owner.
- Japanese の and Mandarin 的 are invariant — person and number do not change them.
- Japanese has no grammatical gender. Use 私は for neutral or female speakers, ぼくは for male child speakers.
- Use plain form throughout. No polite forms. German du throughout — no Sie.

---

## Subject pronoun templates

Shows a pronoun replacing a named subject already established in the prior sentence.

### Template

```
[NAME] [VERB]. [PRONOUN] [VERB] [ADVERB].
[NAME_DE] [VERB_DE]. [PRONOUN_DE] [VERB_DE] [ADVERB_DE].
[NAME_JP]は[VERB_JP]。[PRONOUN_JP]は[ADVERB_JP][VERB_JP]。
[NAME_ZH][VERB_ZH]。[PRONOUN_ZH][ADVERB_ZH][VERB_ZH]。
```

### Example — he

```
Tom runs. He runs fast.
Tom rennt. Er rennt schnell.
トムは走る。彼は速く走る。
汤姆跑。他跑得很快。
```

### Example — she

```
Kate reads. She reads carefully.
Kate liest. Sie liest sorgfältig.
ケイトは読む。彼女は丁寧に読む。
凯特读书。她仔细地读书。
```

### Example — they

```
The children play. They play outside.
Die Kinder spielen. Sie spielen draußen.
子供たちは遊ぶ。彼らは外で遊ぶ。
孩子们玩。他们在外面玩。
```

---

## Object pronoun templates

Shows a pronoun in object position.

### Object pronoun reference

| Person | EN | DE (accusative) | JP | ZH |
|---|---|---|---|---|
| 1sg | me | mich | 私を | 我 |
| 2sg | you | dich | あなたを | 你 |
| 3sg masc | him | ihn | 彼を | 他 |
| 3sg fem | her | sie | 彼女を | 她 |
| 1pl | us | uns | 私たちを | 我们 |
| 3pl | them | sie | 彼らを | 他们 |

### Template

```
[NAME] [VERB] [PRONOUN_OBJ].
[NAME_DE] [VERB_DE] [PRONOUN_OBJ_DE].
[NAME_JP]は[PRONOUN_OBJ_JP]を[VERB_JP]。
[NAME_ZH][VERB_ZH][PRONOUN_OBJ_ZH]。
```

### Example — him

```
Kate helps him.
Kate hilft ihm.
ケイトは彼を助ける。
凯特帮助他。
```

### Example — them

```
The teacher helps them.
Die Lehrerin hilft ihnen.
先生は彼らを助ける。
老师帮助他们。
```

---

## Pronoun possession templates

Shows an owned object with a pronoun possessive.
Choose nouns where ownership is genuinely informative — not a tautological restatement of the subject.

### Japanese verb note

持っている means physically holding or carrying something (a bag in hand, a pen, a cup).
Do not use 持っている for animals, people, or things you own but do not physically carry.

| Meaning | Japanese form |
|---|---|
| physically carrying a small object | 持っている |
| keeping an animal | 飼っている |
| having a person in one's life | ～がいる (姉がいる — I have a sister) |
| ownership without action | 「私の本」as subject, then describe with adjective |

### Template

```
[SUBJECT] has a [NOUN].
[SUBJECT_DE] hat [ARTICLE_DE] [NOUN_DE].
[SUBJECT_JP]は[NOUN_JP]を持っている。   ← only for small carried objects
[SUBJECT_ZH]有[COUNTER_ZH][NOUN_ZH]。
```

### Example — my

```
I have a book.
Ich habe ein Buch.
本を持っている。
我有一本书。
```

Note: Japanese drops the subject pronoun — first-person context is clear from the situation. No 私の needed; the verb implies the subject is the owner. Mandarin uses 一本 (volume counter for books), not 一个.

### Example — her

```
She has a bag.
Sie hat eine Tasche.
バッグを持っている。
她有一个包。
```

Note: Possession is established by the verb and subject alone. Restating 彼女の in Japanese or 她的 in Mandarin is redundant and unnatural.

---

## Proper name possession templates

Shows a named owner and a noun across all four languages.
Use two noun slots per entry to demonstrate the pattern is productive.

### Template

```
[NAME]'s [NOUN1] is [PROPERTY1].
[NAME_DE]s [NOUN1_DE] ist [PROPERTY1_DE].
[NAME_JP]の[NOUN1_JP]は[PROPERTY1_JP]だ。
[NAME_ZH]的[NOUN1_ZH]很[PROPERTY1_ZH]。

[NAME]'s [NOUN2] is [PROPERTY2].
[NAME_DE]s [NOUN2_DE] ist [PROPERTY2_DE].
[NAME_JP]の[NOUN2_JP]は[PROPERTY2_JP]だ。
[NAME_ZH]的[NOUN2_ZH]很[PROPERTY2_ZH]。
```

### Example — Tom

```
Tom's apple is red.
Toms Apfel ist rot.
トムのリンゴは赤い。
汤姆的苹果是红的。

Tom's dog is big.
Toms Hund ist groß.
トムの犬は大きい。
汤姆的狗很大。
```

### Example — Kate

```
Kate's book is old.
Kates Buch ist alt.
ケイトの本は古い。
凯特的书很旧。

Kate's cat is small.
Kates Katze ist klein.
ケイトの猫は小さい。
凯特的猫很小。
```

---

## Combined template — pronoun with possession

Sentence 1 introduces the subject and the owned object.
Sentence 2 uses a pronoun for the subject and drops the noun entirely — no restatement.
This is the bridge toward 2c.

### Template

```
[NAME] has a [NOUN]. [PRONOUN] loves it.
[NAME_DE] hat einen/eine [NOUN_DE]. [PRONOUN_DE] liebt ihn/sie/es.
[NAME_JP]は[NOUN_JP]を飼っている／持っている。大好きだ。
[NAME_ZH]有一[COUNTER_ZH][NOUN_ZH]。很爱它。
```

### Example

```
Tom has a dog. He loves it.
Tom hat einen Hund. Er liebt ihn.
トムは犬を飼っている。大好きだ。
汤姆有一只狗。很爱它。
```

What this shows:
- EN / DE — pronoun replaces noun on second mention; DE accusative ihn agrees with der Hund (masculine)
- JP — 飼っている for a living animal (not 持っている); subject dropped on second sentence; object dropped; bare predicate is natural
- ZH — subject dropped; 一只 counter for animals; 它 replaces the noun

---

## Rules

1. Default named subjects: Tom, Kate, the child. Vary with teacher, woman, boy.
2. Use only allowlist words for content nouns, verbs, and adjectives.
3. Pronouns and possessive markers (my, his, の, 的, mein etc.) are function words — always allowed.
4. German possessives agree with the gender and case of the noun they modify. Check the reference table.
5. Japanese particles: は/が for subject, を for object, の for possession. Never omit particles.
6. Plain form throughout. Dictionary form or た form. No polite forms.
7. Mandarin aspect: 了 for completed action, 在 for ongoing, 会 for future intention.
8. One file per pronoun or possessive type (e.g. `his.md`, `her.md`, `my.md`, `tom.md`).
9. Do not explain grammar inside the generated files.
10. Each file: 3–4 sentence pairs minimum to show the pattern is stable.
11. Do not restate a noun just introduced — use a pronoun or drop it per language rules.

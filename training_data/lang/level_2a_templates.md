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

**Counters, not plural suffixes**
English and German mark plural on the noun. Japanese and Mandarin use classifiers instead.
- EN: "two birds" → JP: 鳥が二羽 (counter 羽, no suffix on 鳥)
- Write 鳥たち only when meaning "those birds as a specific established group."

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

# Level 2a — Verb Tenses, Adjectives, Noun Number

Level 2a introduces three grammatical features, each in isolation.
Each file covers exactly one feature. Do not combine features across files — that is Level 2c.

The word list is the project allowlist, sorted by frequency (most common first).
Prioritise the high-frequency end for generation. Rare and obscure words can wait for later passes.

---

## Polysemy — one file per semantic frame

Level 2a does not generate one file per word from the allowlist.
It generates one file per **semantic frame** — the pairing of a word's meaning with the argument structure around it.

Some words carry multiple frames, each with its own grammar:

| Word | Frame 1 | Frame 2 |
|---|---|---|
| lay | [AGENT] lays [OBJECT] on [SURFACE] | [ANIMAL] lays an egg |
| run | [AGENT] runs (intransitive) | [AGENT] runs [ORGANIZATION] |
| break | [AGENT] breaks [OBJECT] (transitive) | [OBJECT] breaks (intransitive) |
| carry | [AGENT] carries [OBJECT] | [AGENT] carries [DISEASE / QUALITY] |

File names reflect the frame when the word is polysemous:
- `run.md` if only one frame is generated
- `lay_place.md` and `lay_egg.md` if both frames are generated

Do not mix frames within one file. Subject and object choices must fit the frame throughout.

---

## Verb templates — tense paradigm

Use for action verbs, process verbs, mental verbs.
One file per semantic frame. Each file covers all three tense slots.

### Template

```
Yesterday, [SUBJECT] [VERB_PAST].
Gestern [hat/ist] [SUBJECT_DE] [VERB_PAST_DE].
昨日、[SUBJECT_JP]は[VERB_PAST_JP]。
昨天，[SUBJECT_ZH][VERB_PAST_ZH]了。

Now, [SUBJECT] [VERB_PRESENT_CONTINUOUS].
Jetzt [VERB_PRESENT_DE] [SUBJECT_DE].
今、[SUBJECT_JP]は[VERB_PRESENT_JP]。
现在，[SUBJECT_ZH]在[VERB_PRESENT_ZH]。

Tomorrow, [SUBJECT] will [VERB_BASE].
Morgen wird [SUBJECT_DE] [VERB_BASE_DE].
明日、[SUBJECT_JP]は[VERB_FUTURE_JP]。
明天，[SUBJECT_ZH]会[VERB_BASE_ZH]。
```

### Example — run

```
Yesterday, the dog ran.
Gestern ist der Hund gerannt.
昨日、犬は走った。
昨天，狗跑了。

Now, the dog is running.
Jetzt rennt der Hund.
今、犬は走っている。
现在，狗在跑。

Tomorrow, the dog will run.
Morgen wird der Hund rennen.
明日、犬は走るだろう。
明天，狗会跑。
```

### Example — sleep

```
Yesterday, the child slept.
Gestern hat das Kind geschlafen.
昨日、子供は寝た。
昨天，孩子睡了。

Now, the child is sleeping.
Jetzt schläft das Kind.
今、子供は寝ている。
现在，孩子在睡觉。

Tomorrow, the child will sleep.
Morgen wird das Kind schlafen.
明日、子供は寝るだろう。
明天，孩子会睡觉。
```

---

## Adjective and adverb templates

Use for physical adjectives and evaluative adjectives.
Each file shows the same root word functioning as a noun modifier and as a verb modifier.

### Template

```
The [NOUN] is [ADJ].
[NOUN_DE] ist [ADJ_DE].
[NOUN_JP]は[ADJ_JP]。
[NOUN_ZH]很[ADJ_ZH]。

The [NOUN] [VERB] [ADV].
[NOUN_DE] [VERB_DE] [ADV_DE].
[NOUN_JP]は[ADV_JP][VERB_JP]。
[NOUN_ZH][ADV_ZH]地[VERB_ZH]。
```

Note: Mandarin adjective predicates use 很 (not 是...的). 很 is not emphatic "very" here — it is the standard copular pattern for adjectives. 乌龟是慢的 sounds marked; 乌龟很慢 is neutral.

### Example — slow

```
The turtle is slow.
Die Schildkröte ist langsam.
カメはゆっくりだ。
乌龟很慢。

The turtle walks slowly.
Die Schildkröte läuft langsam.
カメはゆっくり歩く。
乌龟慢慢地走。
```

### Example — careful

```
The teacher is careful.
Die Lehrerin ist sorgfältig.
先生は丁寧だ。
老师很仔细。

The teacher speaks carefully.
Die Lehrerin spricht sorgfältig.
先生は丁寧に話す。
老师仔细地说话。
```

---

## Noun number templates

Use for concrete nouns, agent nouns, and natural objects.
Each file shows singular and plural, using the correct classifier in Japanese and Mandarin.

### Template

```
One [NOUN].
Ein/Eine [NOUN_DE].
[NOUN_JP]が一[COUNTER_JP]。
一[COUNTER_ZH][NOUN_ZH]。

Two [NOUN_PLURAL].
Zwei [NOUN_DE_PLURAL].
[NOUN_JP]が二[COUNTER_JP]。
两[COUNTER_ZH][NOUN_ZH]。
```

Do not default to つ or 个 for every noun. Pick the classifier that fits the category — see counter reference below.

### Example — bird

```
One bird.
Ein Vogel.
鳥が一羽。
一只鸟。

Two birds.
Zwei Vögel.
鳥が二羽。
两只鸟。
```

### Example — apple

```
One apple.
Ein Apfel.
リンゴが一つ。
一个苹果。

Two apples.
Zwei Äpfel.
リンゴが二つ。
两个苹果。
```

---

## Counter reference

Japanese and Mandarin count with classifiers, not plural suffixes.
The classifier encodes the category of the thing counted.

### Japanese classifiers

| Counter | Reading | Category | Example |
|---|---|---|---|
| 羽 | wa | birds | 鳥が二羽 |
| つ | tsu | general objects | リンゴが二つ |
| 本 | hon | long thin objects — pens, bottles, rivers | 鉛筆が三本 |
| 枚 | mai | flat objects — paper, plates, leaves | 紙が四枚 |
| 匹 | hiki | small animals | 猫が二匹 |
| 頭 | tō | large animals | 馬が一頭 |
| 人 | nin | people | 子供が三人 |

Do not add plural markers to Japanese nouns. 鳥 is correct for any quantity. 鳥たち means "those birds as a specific established group," not simply birds in general.

**Quantity vs definite reference**
Word order changes meaning in Japanese:
- 侍七人 — seven samurai (a quantity; no prior context required)
- 七人の侍 — the seven samurai (a specific established group; the seven we already know about)

Use [NOUN][NUMBER][COUNTER] for plain counting.
Use [NUMBER][COUNTER]の[NOUN] only when referring to a group already established in context.

### Mandarin classifiers

| Counter | Pinyin | Category | Example |
|---|---|---|---|
| 只 | zhī | small animals, birds, one of a pair | 猫两只 |
| 个 | gè | general objects, people (informal) | 苹果一个 |
| 本 | běn | books and bound volumes | 书一本 |
| 张 | zhāng | flat objects — paper, tables, faces | 纸一张 |
| 条 | tiáo | long flexible objects — fish, roads, rivers | 鱼两条 |

---

## Rules

1. Use only words from `allowlist.txt` for nouns and verbs. Prioritise high-frequency entries.
2. Time markers (yesterday, today, tomorrow, now) are function words — always allowed.
3. Subject must be a concrete agent noun where possible: child, dog, teacher, woman, boy.
4. Each file covers one semantic frame. File name reflects the frame if the word is polysemous.
5. Do not explain grammar. Do not add notes inside the generated sentence files.
6. German verb position follows the V2 rule — verb is always the second constituent.
7. Japanese sentences end with 。 not .
8. Pick the right classifier for each noun. Do not default to つ or 个.
9. Do not translate literally if the result is unnatural. Prefer the natural target-language form.
10. Do not introduce pronouns or possession in 2a files. Those belong in 2b.

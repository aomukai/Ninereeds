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

# Level 2c — Combination and Consolidation

Level 2c combines features from 2a and 2b. No new grammatical features are introduced here.
The goal is natural sentences that bring together:
- verb tenses with time markers
- adjectives and adverbs
- singular and plural nouns with correct counters
- subject and object pronouns
- pronoun and proper-name possession

Sentences may be longer than in 2a/2b but must remain clearly parseable.
Aim for 20–30 files total. Breadth of combination matters more than length of individual files.

---

## Feature matrix

Each file should use a different combination from this matrix. Do not repeat combinations across files.

| Slot A — Subject | Slot B — Verb + Tense | Slot C — Object / Complement | Slot D — Modifier |
|---|---|---|---|
| proper name | past + time marker | direct object (noun) | adverb |
| pronoun subject | present continuous | cross-person possession (Name's) | location word |
| plural noun | future + time marker | pronoun object | time marker |
| possessed noun (his / her) | simple present | adjective complement | — (keep it short) |

### Example combinations

- A1 + B1 + C1 + D1 → Yesterday, Tom found Kate's bag quickly.
- A2 + B3 + C3 + D3 → Tomorrow, she will help them.
- A3 + B2 + C1 + D2 → The children are playing outside now.
- A4 + B4 + C4 → His dog is tired.

Note on possession in Slot C: use cross-person possession (Tom's bag, Kate's book) rather than self-possession (his own bag) — cross-person possession is genuinely informative, where self-possession is usually redundant.

---

## Pattern 1 — Time + Subject + Verb + Object

```
[TIME], [SUBJECT] [VERB_TENSE] [OBJECT].
[TIME_DE], [VERB_DE] [SUBJECT_DE] [OBJECT_DE].
[TIME_JP]、[SUBJECT_JP]は[OBJECT_JP]を[VERB_JP]。
[TIME_ZH]，[SUBJECT_ZH][VERB_ZH][OBJECT_ZH]了。
```

### Examples

```
Yesterday, Tom found Kate's bag.
Gestern hat Tom Kates Tasche gefunden.
昨日、トムはケイトのバッグを見つけた。
昨天，汤姆找到了凯特的包。
```

```
Tomorrow, she will bring a bag.
Morgen wird sie eine Tasche mitbringen.
明日、バッグを持ってくるだろう。
明天，她会带包来。
```

```
Now, the children are eating apples.
Jetzt essen die Kinder Äpfel.
今、子供たちはリンゴを食べている。
现在，孩子们在吃苹果。
```

---

## Pattern 2 — Subject + Verb + Adverb

```
[SUBJECT] [VERB_TENSE] [ADVERB].
[SUBJECT_DE] [VERB_DE] [ADVERB_DE].
[SUBJECT_JP]は[ADV_JP][VERB_JP]。
[SUBJECT_ZH][ADV_ZH]地[VERB_ZH]。
```

### Examples

```
She spoke carefully.
Sie sprach sorgfältig.
彼女は丁寧に話した。
她仔细地说话了。
```

```
They are walking slowly.
Sie gehen langsam.
彼らはゆっくり歩いている。
他们慢慢地走。
```

---

## Pattern 3 — Subject + Verb + Object + Location

```
[SUBJECT] [VERB_TENSE] [OBJECT] [LOCATION].
[SUBJECT_DE] [VERB_DE] [OBJECT_DE] [LOCATION_DE].
[SUBJECT_JP]は[LOCATION_JP]で[OBJECT_JP]を[VERB_JP]。
[SUBJECT_ZH]在[LOCATION_ZH][VERB_ZH][OBJECT_ZH]。
```

### Examples

```
Tom found his dog outside.
Tom hat seinen Hund draußen gefunden.
トムは外で犬を見つけた。
汤姆在外面找到了他的狗。
```

```
Kate reads in the classroom.
Kate liest im Klassenzimmer.
ケイトは教室で本を読む。
凯特在教室里读书。
```

---

## Pattern 4 — Subject + Verb + Pronoun Object

```
[SUBJECT] [VERB_TENSE] [PRONOUN_OBJ].
[SUBJECT_DE] [VERB_DE] [PRONOUN_OBJ_DE].
[SUBJECT_JP]は[PRONOUN_OBJ_JP]を[VERB_JP]。
[SUBJECT_ZH][VERB_ZH][PRONOUN_OBJ_ZH]。
```

### Examples

```
The teacher helped her.
Die Lehrerin hat ihr geholfen.
先生は彼女を助けた。
老师帮助了她。
```

```
Tom called them yesterday.
Tom hat sie gestern angerufen.
トムは昨日彼らに電話した。
汤姆昨天给他们打了电话。
```

---

## Pattern 5 — Possessed Subject + Verb + Complement

```
[NAME]'s [NOUN] is [ADJ].
[NAME_DE]s [NOUN_DE] ist [ADJ_DE].
[NAME_JP]の[NOUN_JP]は[ADJ_JP]だ。
[NAME_ZH]的[NOUN_ZH]很[ADJ_ZH]。
```

### Examples

```
Tom's dog is tired.
Toms Hund ist müde.
トムの犬は疲れている。
汤姆的狗很累。
```

```
Kate's book is old and heavy.
Kates Buch ist alt und schwer.
ケイトの本は古くて重い。
凯特的书又旧又重。
```

---

## Pattern 6 — Discourse pair (two sentences, shared referent)

Sentence 1 introduces a referent by name.
Sentence 2 replaces the name with a pronoun — or drops it entirely where the language allows.
This pattern teaches Ninereeds that pronouns depend on prior context to carry meaning.

```
[NAME] [VERB1]. [PRONOUN] [VERB2] [OBJECT].
[NAME_DE] [VERB1_DE]. [PRONOUN_DE] [VERB2_DE] [OBJECT_DE].
[NAME_JP]は[VERB1_JP]。[OBJECT_JP]を[VERB2_JP]。
[NAME_ZH][VERB1_ZH]。[VERB2_ZH][OBJECT_ZH]了。
```

Note: In the Japanese and Mandarin templates above, subject and possessive are dropped on the second sentence — the referent is clear from the first. Do not restore them.

### Examples

```
Tom ran. He dropped his bag.
Tom ist gerannt. Er hat seine Tasche fallen lassen.
トムは走った。バッグを落とした。
汤姆跑了。包掉了。
```

```
Kate arrived. She brought her books.
Kate ist angekommen. Sie hat ihre Bücher mitgebracht.
ケイトは到着した。本を持ってきた。
凯特到了。带来了书。
```

```
The children played. They were tired afterward.
Die Kinder haben gespielt. Danach waren sie müde.
子供たちは遊んだ。その後、疲れていた。
孩子们玩了。之后很累。
```

---

## Vocabulary rotation

Vary subjects, verbs, and objects across files. Do not reuse the same combination.

### Subjects
Tom, Kate, the child, the teacher, the woman, the boy, the dog, the children, they, she, he, we

### Verbs
run, walk, eat, drink, read, write, bring, find, help, call, carry, drop, lose, play, sleep, speak, watch, build, give, take

### Objects
book, bag, apple, water, dog, cat, ball, key, cup, door, chair, stone, bread, basket, blanket

### Time markers

| EN | DE | JP | ZH |
|---|---|---|---|
| yesterday | gestern | 昨日 | 昨天 |
| today | heute | 今日 | 今天 |
| tomorrow | morgen | 明日 | 明天 |
| now | jetzt | 今 | 现在 |
| later | später | 後で | 后来 |
| this morning | heute Morgen | 今朝 | 今天早上 |
| in the afternoon | am Nachmittag | 午後に | 下午 |
| at night | abends | 夜に | 晚上 |

### Location words

| EN | DE | JP | ZH |
|---|---|---|---|
| outside | draußen | 外で | 在外面 |
| inside | drinnen | 中で | 在里面 |
| in the classroom | im Klassenzimmer | 教室で | 在教室里 |
| in the garden | im Garten | 庭で | 在花园里 |
| at home | zu Hause | 家で | 在家 |
| on the table | auf dem Tisch | テーブルの上で | 在桌子上 |
| in the bag | in der Tasche | バッグの中で | 在包里 |

---

## Rules

1. Every file uses at least two features from the 2a / 2b inventory combined.
2. No file uses only one pattern type. Mix patterns within the file.
3. Each file: 4–6 sentence groups.
4. File names reflect the dominant combination: `past_possessive.md`, `pronoun_location.md`, `plural_adverb.md`.
5. Do not introduce any feature not already in 2a or 2b.
6. No indirect objects. That is Level 3.
7. German word order: time adverbials trigger V2 inversion — Gestern hat Tom, not Gestern Tom hat.
8. Japanese particles: は/が for subject, を for object, で for location, に for direction or time, の for possession.
9. Mandarin aspect: 了 for completed action, 在 for ongoing, 会 for future intention.
10. If a combination produces an awkward sentence in any language, change the verb or noun. Do not force unnatural constructions.

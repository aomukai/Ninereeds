# Level 2c Templates

These templates are for Deepseek generation.
2c is the consolidation stage before Level 3.
No new grammatical features are introduced here.
The goal is natural combination of everything learned in 2a and 2b:
- verb tenses with time markers
- adjectives and adverbs
- singular and plural nouns
- pronouns (subject and object)
- possession (pronoun and proper name)

Sentences may be longer than in 2a/2b but must remain clearly parseable.
All four languages must be present in every entry.

---

## COMBINATION RULES FOR DEEPSEEK

Deepseek should generate sentences by combining features from this matrix.
Each generated file should use a DIFFERENT combination.
Do not repeat the same combination across files.

### Feature Matrix

| Slot A (Subject)         | Slot B (Verb + Tense)         | Slot C (Object/Complement)     | Slot D (Modifier)         |
|--------------------------|-------------------------------|--------------------------------|---------------------------|
| proper name              | past + time marker            | direct object (noun)           | adverb                    |
| pronoun subject          | present continuous            | possessed object (name + 's)   | location word             |
| plural noun              | future + time marker          | pronoun object                 | time marker               |
| possessed noun (his/her) | simple present                | adjective complement           | (none — keep it short)    |

### Combination Examples

- A1 + B1 + C1 + D1 → "Yesterday, Tom ate her apple quickly."
- A2 + B3 + C3 + D3 → "Tomorrow, she will help them."
- A3 + B2 + C1 + D2 → "The children are playing outside now."
- A4 + B4 + C4 → "His dog is tired."

Generate at least 20 unique combinations. Vary subjects, verbs, and objects across files.

---

## SENTENCE PATTERN TEMPLATES

### Pattern 1 — Time + Subject + Verb + Object

```
[TIME], [SUBJECT] [VERB_TENSE] [OBJECT].
[TIME_DE], [VERB_DE] [SUBJECT_DE] [OBJECT_DE].
[TIME_JP]、[SUBJECT_JP]は[OBJECT_JP]を[VERB_JP]。
[TIME_ZH]，[SUBJECT_ZH][VERB_ZH][OBJECT_ZH]了。
```

Examples:

```
Yesterday, Tom lost his book.
Gestern hat Tom sein Buch verloren.
昨日、トムは彼の本をなくした。
昨天，汤姆丢了他的书。
```

```
Tomorrow, she will bring her bag.
Morgen wird sie ihre Tasche mitbringen.
明日、彼女は彼女のバッグを持ってくるだろう。
明天，她会带她的包。
```

```
Now, the children are eating their apples.
Jetzt essen die Kinder ihre Äpfel.
今、子供たちはリンゴを食べている。
现在，孩子们在吃他们的苹果。
```

---

### Pattern 2 — Subject + Verb + Adverb

```
[SUBJECT] [VERB_TENSE] [ADVERB].
[SUBJECT_DE] [VERB_DE] [ADVERB_DE].
[SUBJECT_JP]は[ADV_JP][VERB_JP]。
[SUBJECT_ZH][ADV_ZH]地[VERB_ZH]。
```

Examples:

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

### Pattern 3 — Subject + Verb + Object + Location

```
[SUBJECT] [VERB_TENSE] [OBJECT] [LOCATION].
[SUBJECT_DE] [VERB_DE] [OBJECT_DE] [LOCATION_DE].
[SUBJECT_JP]は[LOCATION_JP]で[OBJECT_JP]を[VERB_JP]。
[SUBJECT_ZH]在[LOCATION_ZH][VERB_ZH][OBJECT_ZH]。
```

Examples:

```
Tom found his dog outside.
Tom hat seinen Hund draußen gefunden.
トムは外で彼の犬を見つけた。
汤姆在外面找到了他的狗。
```

```
Kate reads her book in the classroom.
Kate liest ihr Buch im Klassenzimmer.
ケイトは教室で彼女の本を読む。
凯特在教室里读她的书。
```

---

### Pattern 4 — Subject + Verb + Pronoun Object

```
[SUBJECT] [VERB_TENSE] [PRONOUN_OBJ].
[SUBJECT_DE] [VERB_DE] [PRONOUN_OBJ_DE].
[SUBJECT_JP]は[PRONOUN_OBJ_JP]を[VERB_JP]。
[SUBJECT_ZH][VERB_ZH][PRONOUN_OBJ_ZH]。
```

Examples:

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

### Pattern 5 — Possessed Subject + Verb + Complement

```
[NAME]'s [NOUN] is [ADJ].
[NAME_DE]s [NOUN_DE] ist [ADJ_DE].
[NAME_JP]の[NOUN_JP]は[ADJ_JP]だ。
[NAME_ZH]的[NOUN_ZH]很[ADJ_ZH]。
```

Examples:

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

### Pattern 6 — Discourse Pair (two sentences, shared referent)

This is the most complex pattern in 2c.
Sentence 1 introduces a referent by name.
Sentence 2 replaces the name with a pronoun.
This teaches Ninereeds that pronouns are referentially dependent.

```
[NAME] [VERB1]. [PRONOUN] [VERB2] [OBJECT].
[NAME_DE] [VERB1_DE]. [PRONOUN_DE] [VERB2_DE] [OBJECT_DE].
[NAME_JP]は[VERB1_JP]。[PRONOUN_JP]は[OBJECT_JP]を[VERB2_JP]。
[NAME_ZH][VERB1_ZH]。[PRONOUN_ZH][VERB2_ZH][OBJECT_ZH]。
```

Examples:

```
Tom ran. He dropped his bag.
Tom ist gerannt. Er hat seine Tasche fallen lassen.
トムは走った。彼は彼のバッグを落とした。
汤姆跑了。他掉了他的包。
```

```
Kate arrived. She brought her books.
Kate ist angekommen. Sie hat ihre Bücher mitgebracht.
ケイトは到着した。彼女は彼女の本を持ってきた。
凯特到了。她带来了她的书。
```

```
The children played. They were tired afterward.
Die Kinder haben gespielt. Danach waren sie müde.
子供たちは遊んだ。その後、彼らは疲れていた。
孩子们玩了。之后他们很累。
```

---

## VARIATION GUIDELINES FOR DEEPSEEK

### Subjects to rotate through
Tom, Kate, the child, the teacher, the woman, the boy, the dog, the children, they, she, he, we

### Verbs to rotate through (use inflected forms appropriate to tense)
run, walk, eat, drink, read, write, bring, find, help, call, carry, drop, lose, play, sleep, speak, watch, build, give, take

### Objects to rotate through
book, bag, apple, water, dog, cat, ball, key, cup, door, chair, stone, bread, cookie, basket, blanket

### Time markers
yesterday, today, tomorrow, now, later, this morning, in the afternoon, at night
gestern, heute, morgen, jetzt, später, heute Morgen, am Nachmittag, abends
昨日、今日、明日、今、後で、今朝、午後に、夜に
昨天、今天、明天、现在、后来、今天早上、下午、晚上

### Location words
outside, inside, in the classroom, in the garden, at home, on the table, in the bag
draußen, drinnen, im Klassenzimmer, im Garten, zu Hause, auf dem Tisch, in der Tasche
外で、中で、教室で、庭で、家で、テーブルの上で、バッグの中で
在外面、在里面、在教室里、在花园里、在家、在桌子上、在包里

---

## GENERATION RULES FOR DEEPSEEK

1. Every file must use at least TWO features from the 2a/2b inventory combined.
2. No file should use only one pattern type. Mix at minimum Pattern X + Pattern Y across the file.
3. Each file contains 4–6 sentence groups minimum.
4. File names reflect the dominant feature combination: e.g. past_possessive.md, pronoun_location.md, plural_adverb.md
5. Do not introduce any grammatical feature not present in 2a or 2b.
6. Do not use indirect objects yet. That is Level 3.
7. German word order: time adverbials trigger verb-second inversion. "Gestern hat Tom..." not "Gestern Tom hat..."
8. Japanese particles must be correct throughout: は/が for subject, を for object, で for location, に for direction/time, の for possession.
9. Mandarin aspect markers: 了 for completed action, 在 for ongoing, 会 for future intention.
10. Keep sentences natural. If a combination produces an awkward sentence in any language, choose a different verb or noun. Do not force unnatural constructions.
11. Aim for 20–30 files total for 2c. Breadth of combination matters more than length of individual files.

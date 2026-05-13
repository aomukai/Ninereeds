# Global Generation Rules — All Levels

These rules apply to every file generated for the Ninereeds corpus.
They override template structures when templates produce unnatural output.
Read these before generating any sentence.

---

## CORE PRINCIPLE

**Naturalise, don't translate.**

The goal is not to produce four parallel versions of the same sentence.
The goal is to express the same meaning the way a native speaker would express it.
If the English template produces something no native speaker would say in German, Japanese, or Mandarin — rewrite it until it sounds natural. The meaning must be preserved. The surface form does not have to match.

---

## SHOW DIFFERENCES BETWEEN LANGUAGES

Languages differ at every level. These differences are features, not problems.
Deepseek must actively surface them, not flatten them.

### What to show

**Pronoun drop**
Japanese and Mandarin drop subject and object pronouns when the referent is clear from context.
Do not insert pronouns just because English has them.
- EN: "Tom has a dog. He loves it."
- JP: 「トムは犬を飼っている。大好きだ。」← subject and object both dropped, natural
- ZH: "汤姆有一只狗。很爱它。" ← subject dropped, natural

**Verb choice by semantic fit**
Different languages carve actions differently. Choose the verb that fits the meaning, not the verb that looks like a translation.
- EN: "has a dog" → DE: "hat einen Hund" ✓
- EN: "has a dog" → JP: 持っている ✗ (carrying) / 飼っている ✓ (keeping/raising)

**Possession restated vs dropped**
If possession is already established or implied, do not restate it.
- EN: "Tom has a dog. He loves his dog." → his dog is redundant
- Better: "Tom has a dog. He loves it." or in JP just 「好きだ。」

**Plural marking**
English and German mark plural on the noun. Japanese does not — use counters or context.
- EN: "two birds" → JP: 「鳥が二羽」← counter 羽, no plural suffix on 鳥
- Do not write 鳥たち unless the meaning is specifically "the birds (as a group we've been talking about)"

**Article system**
German has grammatical gender and case on articles. Japanese and Mandarin have no articles.
Do not insert の or 的 where possession is not actually meant.

**Word order as grammar**
German uses word order + case to signal roles. Japanese uses particles. Mandarin uses word order alone.
A sentence that is ambiguous in English may be unambiguous in German or Japanese due to these markers — and vice versa. Show this when it occurs naturally.

**Honorifics and register**
Japanese plain form throughout. No ます/です forms. No keigo.
Foreign names (Tom, Kate) do not require さん in casual plain-form speech.
Use さん only if the sentence context clearly implies a formal or respectful relationship.

**Aspect vs tense**
Mandarin has no grammatical tense. Time is marked by adverbials and aspect particles (了, 在, 过, 会).
Do not try to map English tense directly onto Mandarin. Map the *meaning* (completed, ongoing, future intention) onto the correct aspect marker.
Japanese tense is binary (past/non-past). Aspect is marked separately via て-form constructions.

---

## REDUNDANCY RULES

Do not restate what is already established in the same sentence or the previous sentence.

| Situation | Wrong | Right |
|---|---|---|
| Owner already named | Tom has his dog | Tom has a dog |
| Subject clear from context | 彼は彼の犬が好きだ | 好きだ／犬が好きだ |
| Object clear from previous sentence | Er liebt seinen Hund | Er liebt ihn |
| Plural obvious from context | 鳥たちが飛んでいる | 鳥が飛んでいる |

---

## NATURALNESS CHECKLIST

Before finalising any sentence, ask:

1. Would a native speaker say this, or does it sound like a textbook?
2. Is any word redundant given what came before?
3. Is the verb the right verb for this meaning in this language?
4. Are pronouns present only where the language actually uses them?
5. Does the sentence show something interesting about how this language works?
6. If the answer to 5 is no — can a small adjustment make it show something?

If a sentence passes this checklist in all four languages, it is ready.
If it fails in any language, rewrite that language's version until it passes.

---

## WHAT GOOD LOOKS LIKE

### Bad (translated, redundant, unnatural)
```
Tom has his dog. He loves his dog.
Tom hat seinen Hund. Er liebt seinen Hund.
トムは彼の犬を持っている。彼は彼の犬が好きだ。
汤姆有他的狗。他爱他的狗。
```

### Good (natural, shows cross-linguistic differences)
```
Tom has a dog. He loves it.
Tom hat einen Hund. Er liebt ihn.
トムは犬を飼っている。大好きだ。
汤姆有一只狗。很爱它。
```

What this shows:
- EN/DE: pronoun replaces noun on second mention
- DE: accusative pronoun ihn (not ihn + noun)
- JP: subject dropped, object dropped, bare predicate is natural
- ZH: subject dropped, aspect particle absent because the state is ongoing not completed
- JP: 飼っている not 持っている — verb choice reflects semantic category of object (living thing)
- ZH: 一只 counter for animals, not 一个

---

## A NOTE ON INSTRUCTIONAL VALUE

Sentences that are grammatically correct but unnatural are not useful for Ninereeds.
Ninereeds must learn language as it is used, not language as it is described in grammars.
The corpus is the only input. Every unnatural sentence is a false signal.
Every natural sentence that shows a cross-linguistic difference is a lesson without an explanation.



---

# Level 2a Templates

These templates are for Deepseek generation.
For each word, select the appropriate template set based on word class.
All four languages must be present in every entry.
Time markers are mandatory for verb tense entries — do not omit them.
Keep sentences short. Do not add words not on the allowlist.

---

## VERB TEMPLATES — Tense Paradigm

Use for: action verbs, process verbs, mental verbs.
One file per verb. File contains all tense slots.

### Template

```
Yesterday, [SUBJECT] [VERB_PAST].
Gestern [hat/ist] [SUBJECT] [VERB_PAST_DE].
昨日、[SUBJECT]は[VERB_PAST_JP]。
昨天，[SUBJECT][VERB_PAST_ZH]了。

Now, [SUBJECT] [VERB_PRESENT_CONTINUOUS].
Jetzt [VERB_PRESENT_DE] [SUBJECT].
今、[SUBJECT]は[VERB_PRESENT_JP]。
现在，[SUBJECT]在[VERB_PRESENT_ZH]。

Tomorrow, [SUBJECT] will [VERB_BASE].
Morgen wird [SUBJECT] [VERB_BASE_DE].
明日、[SUBJECT]は[VERB_FUTURE_JP]。
明天，[SUBJECT]会[VERB_BASE_ZH]。
```

### Example — run / rennen / 走る / 跑

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

### Example — sleep / schlafen / 寝る / 睡

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

## ADJECTIVE → ADVERB TEMPLATES

Use for: physical adjectives, evaluative adjectives.
Shows the same root word functioning as modifier of noun vs modifier of verb.

### Template

```
The [NOUN] is [ADJ].
[NOUN_DE] ist [ADJ_DE].
[NOUN_JP]は[ADJ_JP]。
[NOUN_ZH]是[ADJ_ZH]的。

The [NOUN] [VERB] [ADV].
[NOUN_DE] [VERB_DE] [ADV_DE].
[NOUN_JP]は[ADV_JP][VERB_JP]。
[NOUN_ZH][ADV_ZH]地[VERB_ZH]。
```

### Example — slow / langsam / ゆっくり / 慢

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

### Example — careful / sorgfältig / 丁寧 / 仔细

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

## NOUN NUMBER TEMPLATES

Use for: concrete nouns, agent nouns, natural objects.
Shows singular vs plural, and introduces Japanese counters as an alternative number strategy.

### Template

```
One [NOUN].
Ein/Eine [NOUN_DE].
[COUNTER_JP]一つの[NOUN_JP]。
一个[NOUN_ZH]。

Two [NOUN_PLURAL].
Zwei [NOUN_DE_PLURAL].
[NOUN_JP]が二[COUNTER_SUFFIX_JP]。
两个[NOUN_ZH]。
```

### Example — bird / Vogel / 鳥 / 鸟

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

### Example — apple / Apfel / リンゴ / 苹果

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

## COUNTER BRIDGE NOTE
## (for Deepseek: include this as a comment in counter-heavy entries)

Japanese does not mark plural on the noun itself.
Instead, counters encode the category of the thing being counted:
- 羽 (wa) for birds
- つ (tsu) for general objects
- 本 (hon) for long thin objects
- 枚 (mai) for flat objects
- 匹 (hiki) for small animals

This is not an error. It is the correct Japanese form.
Do not add plural markers to Japanese nouns.

---

## GENERATION RULES FOR DEEPSEEK

1. Use only words from allowlist.txt for nouns and verbs.
2. Time markers (yesterday/today/tomorrow etc.) are function words — always allowed.
3. Subject must be a concrete agent noun where possible (child, dog, teacher, woman, boy).
4. Each file covers one word fully across its paradigm slots.
5. File name = base English word (e.g. run.md, slow.md, bird.md).
6. Do not explain grammar. Do not add notes inside the sentence files.
7. German verb position follows V2 rule — verb is always second constituent.
8. Japanese sentences end with 。not .
9. Do not translate literally if the result is unnatural. Prefer natural target-language form.



---

# Level 2b Templates

These templates are for Deepseek generation.
2b introduces pronouns and possession.
All four languages must be present in every entry.
Keep sentences short. Use only allowlist words for content nouns and verbs.

---

## REFERENCE TABLES FOR DEEPSEEK
## Do not include these tables in generated files. Use them to produce correct forms.

### Personal Pronouns

| Person     | EN      | DE          | JP              | ZH    |
|------------|---------|-------------|-----------------|-------|
| 1sg        | I       | ich         | 私は／ぼくは     | 我    |
| 2sg        | you     | du          | あなたは         | 你    |
| 3sg masc   | he      | er          | 彼は             | 他    |
| 3sg fem    | she     | sie         | 彼女は           | 她    |
| 1pl        | we      | wir         | 私たちは         | 我们  |
| 3pl        | they    | sie         | 彼らは           | 他们  |

### Possessive Pronouns (attributive)

| Person     | EN      | DE (masc/neut/fem/pl)         | JP          | ZH    |
|------------|---------|-------------------------------|-------------|-------|
| 1sg        | my      | mein/mein/meine/meine         | 私の         | 我的  |
| 2sg        | your    | dein/dein/deine/deine         | あなたの     | 你的  |
| 3sg masc   | his     | sein/sein/seine/seine         | 彼の         | 他的  |
| 3sg fem    | her     | ihr/ihr/ihre/ihre             | 彼女の       | 她的  |
| 1pl        | our     | unser/unser/unsere/unsere     | 私たちの     | 我们的|
| 3pl        | their   | ihr/ihr/ihre/ihre             | 彼らの       | 他们的|

### Proper Name Possession

| Language | Form                        | Example                        |
|----------|-----------------------------|--------------------------------|
| EN       | Name + 's + noun            | Tom's apple                    |
| DE       | Name + s + noun (no apostrophe) | Toms Apfel                 |
| JP       | Name + の + noun            | トムのリンゴ                    |
| ZH       | Name + 的 + noun            | 汤姆的苹果                      |

### Notes for Deepseek
- German possessives inflect for the gender/case of the noun they modify, not the owner.
- Japanese possession is always の regardless of person or number.
- Mandarin possession is always 的 regardless of person or number.
- Japanese has no grammatical gender. Use 私は for neutral/female, ぼくは for male child speakers.
- Do not use keigo (polite forms) in Japanese. Use plain form throughout.
- German: du is informal. Use du consistently. Do not use Sie.

---

## PRONOUN TEMPLATES — Subject Pronouns

Shows pronoun replacing a named subject already introduced.

### Template

```
[NAME] [VERB]. [PRONOUN] [VERB] [ADVERB/TIME].
[NAME_DE] [VERB_DE]. [PRONOUN_DE] [VERB_DE] [ADVERB_DE].
[NAME_JP]は[VERB_JP]。[PRONOUN_JP][VERB_JP]。
[NAME_ZH][VERB_ZH]。[PRONOUN_ZH][VERB_ZH]。
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

## PRONOUN TEMPLATES — Object Pronouns

Shows pronoun in object position.

### Object Pronoun Reference Table

| Person     | EN   | DE (acc)  | JP (obj particle) | ZH  |
|------------|------|-----------|-------------------|-----|
| 1sg        | me   | mich      | 私を               | 我  |
| 2sg        | you  | dich      | あなたを           | 你  |
| 3sg masc   | him  | ihn       | 彼を               | 他  |
| 3sg fem    | her  | sie       | 彼女を             | 她  |
| 1pl        | us   | uns       | 私たちを           | 我们|
| 3pl        | them | sie       | 彼らを             | 他们|

### Template

```
[NAME] helps [PRONOUN_OBJ].
[NAME_DE] hilft [PRONOUN_OBJ_DE].
[NAME_JP]は[PRONOUN_OBJ_JP]助ける。
[NAME_ZH]帮助[PRONOUN_OBJ_ZH]。
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

## POSSESSIVE TEMPLATES — Pronoun Possession

Shows owned object with pronoun possessive.
The purpose is to show that ownership is marked differently per language —
not to produce sentences where possession is redundant or implied.
Choose nouns where ownership is genuinely informative.

### Verb note for Japanese
持っている = physically holding or carrying an object (a bag in hand, a pen)
持っている is WRONG for animals, people, or things you own but don't carry.
Use instead:
- 持っている → only for small carried objects (pen, cup, key)
- 飼っている → for animals
- ある／いる → for existence ("I have a sister" = 姉がいる)
- plain ownership without a verb → 「私の本」as subject, described by adjective

### Template

```
[SUBJECT] has [POSS] [NOUN].
[SUBJECT_DE] hat [POSS_DE] [NOUN_DE].
[SUBJECT_JP]は[NOUN_JP]を持っている。  ← only if NOUN is a small carried object
[SUBJECT_ZH]有[NOUN_ZH]。  ← 的 omitted when possession is already clear from subject
```

### Example — my

```
I have a book.
Ich habe ein Buch.
本を持っている。
我有一本书。
```

Note: Japanese drops subject (clear from context). No 私の needed — it's already my book if I have it.
Mandarin uses 一本 (flat-object counter for books), not 一个.

### Example — her

```
She has a bag.
Sie hat eine Tasche.
バッグを持っている。
她有一个包。
```

Note: Possession shown by the verb alone. Redundant possessive pronoun omitted in JP and ZH.

---

## POSSESSIVE TEMPLATES — Proper Name Possession

Shows named owner + noun across all four languages.
Use two different nouns per entry to show the pattern is productive.

### Template

```
[NAME]'s [NOUN1] is [PROPERTY].
[NAME_DE]s [NOUN1_DE] ist [PROPERTY_DE].
[NAME_JP]の[NOUN1_JP]は[PROPERTY_JP]だ。
[NAME_ZH]的[NOUN1_ZH][PROPERTY_ZH]。

[NAME]'s [NOUN2] is [PROPERTY2].
[NAME_DE]s [NOUN2_DE] ist [PROPERTY2_DE].
[NAME_JP]の[NOUN2_JP]は[PROPERTY2_JP]だ。
[NAME_ZH]的[NOUN2_ZH][PROPERTY2_ZH]。
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

## COMBINED TEMPLATE — Pronoun + Possession in one sentence

This is the bridge toward 2c. Shows both features working together.
Sentence 1 introduces subject and owned object.
Sentence 2 uses pronoun for subject, pronoun for object — no restatement.

### Template

```
[NAME] has a [NOUN]. [PRONOUN] loves it.
[NAME_DE] hat einen/eine [NOUN_DE]. [PRONOUN_DE] liebt ihn/sie/es.
[NAME_JP]は[NOUN_JP]を飼っている／持っている。大好きだ。
[NAME_ZH]有一[COUNTER][NOUN_ZH]。很爱它。
```

### Example

```
Tom has a dog. He loves it.
Tom hat einen Hund. Er liebt ihn.
トムは犬を飼っている。大好きだ。
汤姆有一只狗。很爱它。
```

What this shows:
- EN/DE: pronoun replaces noun on second mention (it → ihn, accusative)
- DE: 持つ problem avoided — animals use 飼う in JP
- JP: subject dropped on second sentence (clear from context), object dropped (clear from context)
- ZH: subject dropped, 一只 counter for animals, pronoun replaced by 它

---

## GENERATION RULES FOR DEEPSEEK

1. Use Tom, Kate, and the child as default named subjects. Vary occasionally with teacher, woman, boy.
2. Use only allowlist words for all content nouns, verbs, and adjectives.
3. Pronouns and possessive markers (my, his, の, 的, mein etc.) are function words — always allowed.
4. German possessives must agree with the gender and case of the noun they modify. Check the reference table.
5. Japanese object marker is を. Subject marker is は or が. Possession marker is の. Never omit particles.
6. Do not use polite Japanese verb forms. Use plain form (dictionary form or た form).
7. Mandarin: 的 marks possession. 在 marks location. 了 marks completion. Use naturally.
8. One file per pronoun or possessive type (e.g. his.md, her.md, my.md, tom.md).
9. Do not explain grammar inside generated files.
10. Each file should contain 3–4 sentence pairs minimum to show the pattern is stable.



---

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



---

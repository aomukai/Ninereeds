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

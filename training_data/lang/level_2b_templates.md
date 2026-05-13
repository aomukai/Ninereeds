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

### Template

```
[SUBJECT] has [POSS] [NOUN].
[SUBJECT_DE] hat [POSS_DE] [NOUN_DE].
[SUBJECT_JP]は[POSS_JP][NOUN_JP]を持っている。
[SUBJECT_ZH]有[POSS_ZH][NOUN_ZH]。
```

### Example — my

```
I have my book.
Ich habe mein Buch.
私は私の本を持っている。
我有我的书。
```

### Example — her

```
She has her bag.
Sie hat ihre Tasche.
彼女は彼女のバッグを持っている。
她有她的包。
```

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

### Template

```
[NAME] has [POSS_3rd] [NOUN]. [PRONOUN] likes [POSS_3rd] [NOUN].
[NAME_DE] hat [POSS_DE] [NOUN_DE]. [PRONOUN_DE] mag [POSS_DE] [NOUN_DE].
[NAME_JP]は[POSS_JP][NOUN_JP]を持っている。[PRONOUN_JP]は[POSS_JP][NOUN_JP]が好きだ。
[NAME_ZH]有[POSS_ZH][NOUN_ZH]。[PRONOUN_ZH]喜欢[POSS_ZH][NOUN_ZH]。
```

### Example

```
Tom has his dog. He loves his dog.
Tom hat seinen Hund. Er liebt seinen Hund.
トムは彼の犬を持っている。彼は彼の犬が好きだ。
汤姆有他的狗。他爱他的狗。
```

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

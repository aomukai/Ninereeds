# Level 5 — Q&A Pairs and Fragment Answers

## What this level teaches

Level 5 teaches question formation and fragment answers. The core lesson is that natural answers
are bare constituents — not full echoed sentences.

"Who drank the water?" → "The child." not "The child drank the water."

Cross-linguistic contrasts:
- Question word placement: fronted in EN/DE (with verb inversion in DE), in-situ in JP/ZH
- German question pronouns inflect for case — wer / wen / wem / wessen — the question word
  itself signals the grammatical role of the missing constituent
- Japanese fragment answers retain the case particle: が for subject, の for possessor
- Mandarin answers are bare NPs; possessor adds 的

---

## Global rules — all Level 5 files

**Naturalise, don't translate.** The same meaning expressed as a native speaker would express it.

**Japanese plain form only.** No ます/です. No keigo. Past: た form. Present/habitual: plain form.

**German V2 in questions.** WH word occupies the first constituent slot; verb comes second;
subject follows. This is inversion — the subject and verb swap relative to declarative order.
- Wer hat das Wasser getrunken? (wer V2-slot: verb second, no additional subject)
- Wen sah Klaus? (wen first, verb second, subject Klaus third)
- Wem half Tom? (wem first, half second, Tom third)

**German Perfekt for past.** hat/ist + past participle. Motion/state-change: ist. Others: hat.

**Mandarin aspect markers.** 了 for completed action in questions and answers where natural.

**Pronoun drop.** Japanese and Mandarin omit subject/object pronouns when clear from context.

**Fragment answers only.** The answer is the bare constituent that fills the questioned position.
Do not repeat the full sentence. Do not add explanation.

**No grammar labels inside files.** No headings, case labels, or explanatory notes.

---

## File format

Each file: 3–5 Q/A exchanges. Each exchange = Q block (4 lines: EN / DE / JP / ZH) + blank line
+ A block (4 lines: EN / DE / JP / ZH). Single blank line between exchanges.

```
Who drank the water?
Wer hat das Wasser getrunken?
誰が水を飲んだ？
誰喝了那水？

The child.
Das Kind.
子供が。
孩子。

Who ate the bread?
Wer hat das Brot gegessen?
誰がパンを食べた？
誰吃了那面包？

Hanako.
Hanako.
花子。
花子。
```

---

## Names

Use names from this table. Always write each name in the script appropriate to the language.
European names are phonetically transcribed into katakana in JP and into characters in ZH.
Japanese names appear in kanji in JP but are romanised in EN and DE.

| EN | DE | JP | ZH |
|---|---|---|---|
| Tom | Tom | トム | 湯姆 |
| Kate | Kate | ケイト | 凱特 |
| Klaus | Klaus | クラウス | 克勞斯 |
| Peter | Peter | ピーター | 彼得 |
| Corinna | Corinna | コリナ | 科里娜 |
| Hans | Hans | ハンス | 漢斯 |
| Susanne | Susanne | スザンネ | 蘇珊娜 |
| Taro | Taro | 太郎 | 太郎 |
| Hanako | Hanako | 花子 | 花子 |
| Kokoro | Kokoro | 心 | 心 |
| Kaori | Kaori | 香織 | 香織 |

Note: 太郎 and 花子 are read differently in Chinese (Tàiláng / Huāzǐ) than in Japanese
(Tarō / Hanako), but the characters are shared. 心 means something in both languages.
Kokoro / Kokoro reads as a foreign name in EN and DE.

---

## 5A — Who questions

### Overview

German is uniquely instructive here: the question pronoun inflects for case, making the
grammatical role of the missing constituent visible on the question word itself.

| File group | DE question word | Case | Missing constituent |
|---|---|---|---|
| 5a_wer | Wer | nominative | subject |
| 5a_wen | Wen | accusative | direct object |
| 5a_wem | Wem | dative | dative object or indirect object |
| 5a_wessen | Wessen | genitive | possessor |

Japanese and Mandarin do not move the question word. 誰 and 誰 stay in their argument
position. There is no case change on the question word in either language.

---

### 5a_wer — Subject (nominative)

The questioned constituent is the subject of the sentence. German uses **wer**.

Verb types: copula (sein), intransitive activity verbs, intransitive motion verbs.

**Recommended verbs:**

| EN | DE (Perfekt) | JP | ZH |
|---|---|---|---|
| be (identification) | ist | だ | 是 |
| drink | hat getrunken | 飲んだ | 喝了 |
| eat | hat gegessen | 食べた | 吃了 |
| sleep | hat geschlafen | 寝た | 睡了 |
| run | ist gelaufen | 走った | 跑了 |
| laugh | hat gelacht | 笑った | 笑了 |
| win | hat gewonnen | 勝った | 赢了 |
| arrive | ist angekommen | 着いた | 到了 |
| fall | ist gefallen | 落ちた | 摔倒了 |
| leave | ist gegangen | 行った | 走了 |

**German V2:** Wer + verb (+ rest of sentence)?
- Wer hat das Wasser getrunken?
- Wer ist das? (copula identification — no Perfekt)
- Wer ist zuerst angekommen?

**Answer case:** nominative.
- Das Kind. (neut nom)
- Die Frau. (fem nom)
- Der Mann. (masc nom)
- Tom. / Hanako. (proper name — no article)

**Japanese answer:** retain が (subject particle).
- 子供が。/ 花子が。/ 女の人が。

**Mandarin answer:** bare NP.
- 孩子。/ 花子。/ 那個女人。

**Example file (5a_wer_drink.md):**

```
Who drank the water?
Wer hat das Wasser getrunken?
誰が水を飲んだ？
誰喝了那水？

The child.
Das Kind.
子供が。
孩子。

Who ate the bread?
Wer hat das Brot gegessen?
誰がパンを食べた？
誰吃了那面包？

Hanako.
Hanako.
花子が。
花子。

Who arrived first?
Wer ist zuerst angekommen?
誰が一番最初に着いた？
誰先到的？

Klaus.
Klaus.
クラウスが。
克勞斯。
```

---

### 5a_wen — Direct object (accusative)

The questioned constituent is the direct object of an accusative-taking verb. German uses **wen**.

**IMPORTANT:** `helfen` (help) takes DATIVE in German. It belongs in 5a_wem, not here.
Do not use helfen in 5a_wen files.

**Recommended verbs (accusative-object verbs only):**

| EN | DE (Perfekt) | JP | ZH |
|---|---|---|---|
| see | hat gesehen | 見た | 看見了 |
| meet | hat getroffen | 会った | 見到了 |
| know | kennt (present) | 知っている | 認識 |
| find | hat gefunden | 見つけた | 找到了 |
| call | hat gerufen | 呼んだ | 叫了 |
| visit | hat besucht | 訪ねた | 拜訪了 |
| invite | hat eingeladen | 招待した | 邀請了 |
| love | liebt (present) | 愛している | 愛 |
| teach | hat unterrichtet | 教えた | 教了 |
| wait for | hat gewartet auf | 待った | 等了 |

**German V2:** Wen + verb + subject (+ rest)?
- Wen sah Klaus?
- Wen hat Tom eingeladen?
- Wen kennst du? (du = you, for variety)

**Answer case:** accusative. Only masculine changes visibly.
- Die Frau. (fem — same form as nom)
- Das Kind. (neut — same form as nom)
- Den Mann. (masc — der → den)
- Tom. / Hanako. (proper name — no article)

**Japanese:** 誰 occupies the object position in the question (誰を). In fragment answers,
を is dropped — bare NP only.
- Question: クラウスは誰を見た？
- Answer: 女の人。/ 太郎。

**Mandarin:** 誰 in object position. Bare NP answer.
- Question: 克勞斯看見誰了？
- Answer: 那個女人。/ 太郎。

**Example file (5a_wen_see.md):**

```
Who did Klaus see?
Wen sah Klaus?
クラウスは誰を見た？
克勞斯看見誰了？

The woman.
Die Frau.
女の人。
那個女人。

Who did Tom invite?
Wen hat Tom eingeladen?
トムは誰を招待した？
湯姆邀請了誰？

Corinna.
Corinna.
コリナ。
科里娜。

Who does Kate know?
Wen kennt Kate?
ケイトは誰を知っている？
凱特認識誰？

Peter.
Peter.
ピーター。
彼得。
```

---

### 5a_wem — Dative object or indirect object

The questioned constituent is in dative position. German uses **wem**.

Two verb types appear here:
1. Dative-only verbs — the dative NP is the only object.
2. Double-object verbs — the file questions the IO (dative); the DO is retained in the question.

**Dative-only verbs:**

| EN | DE (Perfekt) | JP particle | ZH |
|---|---|---|---|
| help | hat geholfen | を (助ける) / を (手伝う) | 幫助了 |
| thank | hat gedankt | に (感謝する) | 感謝了 |
| follow | ist gefolgt | に (従う) | 跟隨了 |
| belong to | gehört (present) | のものだ | 屬於 |
| answer | hat geantwortet | に (答える) | 回答了 |
| trust | hat vertraut | を (信頼する) | 信任 |
| believe | hat geglaubt | を (信じる) | 相信 |

**Double-object verbs (question targets the IO; DO stays in the question):**

| EN | DE (Perfekt) | JP | ZH |
|---|---|---|---|
| give | hat gegeben | あげた / くれた | 給了 |
| show | hat gezeigt | 見せた | 給…看了 |
| tell | hat gesagt | 話した | 告訴了 |
| send | hat geschickt | 送った | 發送了 |
| bring | hat gebracht | 持ってきた | 帶來了 |

**Note on Japanese particles:** Japanese verbs do not mechanically mirror German dative with に.
The particle is determined by the Japanese verb's own valency:
- 助ける (help) → 誰を助けた？(を)
- 感謝する (thank) → 誰に感謝した？(に)
- 従う (follow) → 誰に従った？(に)
Use the particle that is natural for the Japanese verb.

**German V2:** Wem + verb + subject (+ DO)?
- Wem half Tom? (dative-only)
- Wem hat Klaus das Buch gegeben? (DO retained)

**Answer case:** dative.
- Der Frau. (fem dative)
- Dem Kind. (neut dative)
- Dem Mann. (masc dative)
- Tom. / Hanako. (proper name — no article)

**Japanese answer:** bare NP; particle dropped in fragment.
- 女の人。/ 先生。/ 太郎。

**Example file (5a_wem_help.md):**

```
Who did Tom help?
Wem half Tom?
トムは誰を助けた？
湯姆幫助了誰？

The woman.
Der Frau.
女の人。
那個女人。

Who did Kate give the book to?
Wem hat Kate das Buch gegeben?
ケイトは誰に本をあげた？
凱特把那本書給了誰？

The child.
Dem Kind.
子供。
孩子。

Who did Klaus thank?
Wem hat Klaus gedankt?
クラウスは誰に感謝した？
克勞斯感謝了誰？

Hanako.
Hanako.
花子。
花子。
```

---

### 5a_wessen — Possessor (genitive)

The questioned constituent is the possessor of a noun. German uses **wessen**.

**German answer forms:**

| Context | Form | Example |
|---|---|---|
| Proper noun possessor | Name + -s (no article) | Peters Stift. / Toms Buch. |
| Common noun possessor (spoken/neutral) | NP von + dative | Der Stift von dem Mann. / Die Blumen von der Frau. |
| Common noun possessor (formal/written) | genitive article + noun | Der Stift des Mannes. / Die Blumen der Frau. |

Use the von + dative form as the default for common NPs. Use -s genitive for proper nouns.
Both forms may appear in the same file.

**Japanese:** 誰の + NP (+ question particle)?
- 誰の花なの？/ 誰のペンなの？/ 誰のかばんなの？
- Answer retains の: 女の人の。/ 太郎の。/ 先生の。

**Mandarin:** 這是誰的 + NP？ / 那些 NP 是誰的？
- Answer: 那個女人的。/ 太郎的。/ 彼得的。

**Example file (5a_wessen_flower.md):**

```
Whose flowers are those?
Wessen Blumen sind das?
誰の花なの？
那些花是誰的？

The woman's.
Die Blumen von der Frau.
女の人の。
那個女人的。

Whose pen is this?
Wessen Stift ist das?
誰のペンなの？
這是誰的筆？

Peter's.
Peters Stift.
ピーターの。
彼得的。

Whose bag is this?
Wessen Tasche ist das?
誰のかばんなの？
這是誰的包？

Kaori's.
Kaori's Tasche.
香織の。
香織的。
```

---

## 5B — Where questions

[to be designed in full — stub only]

Integrates Level 4 spatial content. Three German question words map the same three-way contrast
as Level 4's dative/accusative case flip.

| German | Use | JP | ZH |
|---|---|---|---|
| wo | static location (dative) | どこ + に/で + いる/ある | 在哪裡 |
| wohin | goal / directed movement (accusative) | どこ + に/へ | 去哪裡 |
| woher | source / origin (von/aus + dative) | どこ + から | 從哪裡 |

Answers mirror Level 4 fragment forms: PP for EN/DE, localizer phrase for JP, 在/去/從 + place for ZH.

---

## 5C — When questions

[to be designed — stub only]

| Language | Question word | Example |
|---|---|---|
| EN | when | When did she arrive? |
| DE | wann | Wann ist sie angekommen? |
| JP | いつ | いつ着いた？ |
| ZH | 什麼時候 | 她什麼時候到的？ |

Answers: temporal adverbial fragments (yesterday, this morning, at noon, last week).

---

## 5D — Why questions

[to be designed — stub only]

| Language | Question word | Example |
|---|---|---|
| EN | why | Why did he leave? |
| DE | warum / weshalb | Warum ist er gegangen? |
| JP | なぜ / どうして | なぜ行った？ |
| ZH | 為什麼 | 他為什麼走了？ |

Answers: bare reason clause or because-fragment. Cross-linguistic contrast in how reason is
encoded (weil + V-final in DE; から / ので in JP; 因為 in ZH).

---

## 5E — How questions (manner / instrument)

[to be designed — stub only]

Integrates Level 4C instrument content.

| Language | Manner | Instrument |
|---|---|---|
| EN | how | with what / how |
| DE | wie | womit / wie |
| JP | どうやって | 何で / どうやって |
| ZH | 怎麼 | 用什麼 |

Key contrast: JP では is instrument; と is comitative. ZH uses 用 for instrument but 坐/騎 for vehicles.

---

## 5F — Yes/No questions

[to be designed — stub only]

| Language | Question formation | Yes | No |
|---|---|---|---|
| EN | auxiliary inversion: Did X? / Is X? | Yes. | No. |
| DE | verb-first: Hat X? / Ist X? | Ja. | Nein. |
| JP | plain form + か or の | うん / そう | ううん / 違う |
| ZH | plain + 嗎 | 是的 / 對 | 不是 / 沒有 |

---

## File naming

Output directory: `training_data/lang/lang_5/`

| Sub-level | Pattern | Example |
|---|---|---|
| 5A subject (wer) | `5a_wer_{verb}.md` | `5a_wer_drink.md` |
| 5A object (wen) | `5a_wen_{verb}.md` | `5a_wen_see.md` |
| 5A dative (wem) | `5a_wem_{verb}.md` | `5a_wem_help.md` |
| 5A possessor (wessen) | `5a_wessen_{noun}.md` | `5a_wessen_flower.md` |
| 5B static | `5b_wo_{verb}.md` | `5b_wo_sit.md` |
| 5B goal | `5b_wohin_{verb}.md` | `5b_wohin_run.md` |
| 5B source | `5b_woher_{verb}.md` | `5b_woher_come.md` |
| 5C when | `5c_when_{verb}.md` | `5c_when_arrive.md` |
| 5D why | `5d_why_{verb}.md` | `5d_why_leave.md` |
| 5E how | `5e_how_{verb}.md` | `5e_how_cut.md` |
| 5F yes/no | `5f_yn_{verb}.md` | `5f_yn_drink.md` |
| stories | `5d_{topic}.md` | `5d_kitchen.md` |

---

## Generation rules

1. Each file: 3–5 Q/A exchanges. Each exchange: Q block (EN/DE/JP/ZH) + blank line + A block (EN/DE/JP/ZH).
2. Single blank line between exchanges.
3. No headers, labels, or grammar notes inside files.
4. German verb selection must match the sub-type: accusative verbs in 5a_wen, dative verbs in 5a_wem.
5. German answers use correct case article: nominative for wer, accusative for wen, dative for wem.
6. Proper noun answers use Name + -s genitive (Peters, Toms, Kaorис); no article.
7. Japanese subject-position answers retain が. Possessor answers retain の. Object-position answers drop を.
8. Mandarin answers are bare NPs. Possessor answers append 的.
9. Names must appear in the script of the language (see name table).
10. Vary subjects, objects, and tenses across exchanges within each file.
11. Use allowlist words for content nouns.

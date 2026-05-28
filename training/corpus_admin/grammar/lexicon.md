# Grammar Curriculum Lexicon

Purpose: controlled vocabulary pool for generating `training_data/grammar/`.

This is not the global allowlist. It is a curated grammar-specific lexicon drawn
from known project vocabulary. It should be broad enough to avoid accidental
micro-biases, but controlled enough that DeepSeek does not invent nouns, genders,
or roles during generation.

Use this file when generating grammar curriculum files. Prefer entries from this
lexicon over free-form vocabulary.

---

## Rules

- Keep English file slugs and character names stable.
- Do not translate character names: Emma, Taro, Gran, Biscuit.
- For early dative receiver files, prefer common nouns with visible articles:
  `dem Jungen`, `dem Mann`, `dem Arzt`, `der Frau`, `dem Kind`.
- Balance German genders in generated examples.
- Avoid gerunds in grammar files unless the target explicitly needs a gerund.
- Use verbs in finite or infinitive form, not `-ing` as the base teaching form.
- Do not use noisy global-allowlist artifacts such as numbered variants
  (`person_6`) or generated oddities.

---

## Characters

| English | German | JP | ZH | Roles |
|---|---|---|---|---|
| Emma | Emma | エマ | Emma | agent, owner, mover |
| Taro | Taro | 太郎 | Taro | agent, owner, mover |
| Gran | Gran | グラン | Gran | agent, helper, owner |
| Biscuit | Biscuit | ビスケット | Biscuit | animal, agent, mover |

---

## People And Agents

| English | German nominative | Gender | Accusative | Dative | JP | ZH | Roles |
|---|---|---|---|---|---|---|---|
| baby | das Baby | n | das Baby | dem Baby | 赤ちゃん | 嬰兒 | agent, receiver |
| child | das Kind | n | das Kind | dem Kind | 子ども | 孩子 | agent, receiver |
| boy | der Junge | m | den Jungen | dem Jungen | 男の子 | 男孩 | agent, receiver |
| girl | das Mädchen | n | das Mädchen | dem Mädchen | 女の子 | 女孩 | agent, receiver |
| man | der Mann | m | den Mann | dem Mann | 男の人 | 男人 | agent, receiver |
| woman | die Frau | f | die Frau | der Frau | 女の人 | 女人 | agent, receiver |
| adult | der Erwachsene | m | den Erwachsenen | dem Erwachsenen | 大人 | 成人 | agent, receiver |
| aunt | die Tante | f | die Tante | der Tante | おば | 阿姨 | agent, receiver |
| brother | der Bruder | m | den Bruder | dem Bruder | 兄弟 | 兄弟 | agent, receiver |
| doctor | der Arzt | m | den Arzt | dem Arzt | 医者 | 醫生 | agent, receiver, profession |
| teacher | der Lehrer | m | den Lehrer | dem Lehrer | 先生 | 老師 | agent, receiver, profession |
| baker | der Bäcker | m | den Bäcker | dem Bäcker | パン屋 | 麵包師 | agent, receiver, profession |
| butcher | der Fleischer | m | den Fleischer | dem Fleischer | 肉屋 | 肉販 | agent, receiver, profession |
| carpenter | der Tischler | m | den Tischler | dem Tischler | 大工 | 木匠 | agent, receiver, profession |
| driver | der Fahrer | m | den Fahrer | dem Fahrer | 運転手 | 司機 | agent, receiver, profession |
| waiter | der Kellner | m | den Kellner | dem Kellner | ウェイター | 服務員 | agent, receiver, profession |
| janitor | der Hausmeister | m | den Hausmeister | dem Hausmeister | 用務員 | 管理員 | agent, receiver, profession |
| neighbour | der Nachbar | m | den Nachbarn | dem Nachbarn | 隣人 | 鄰居 | agent, receiver |
| colleague | der Kollege | m | den Kollegen | dem Kollegen | 同僚 | 同事 | agent, receiver |
| boss | der Chef | m | den Chef | dem Chef | 上司 | 老闆 | agent, receiver |
| director | der Direktor | m | den Direktor | dem Direktor | 校長 | 主任 | agent, receiver |
| lawyer | der Anwalt | m | den Anwalt | dem Anwalt | 弁護士 | 律師 | agent, receiver |

---

## Animals

Use animals as agents, movers, receivers, and spatial subjects. Prefer common
animals first.

| English | German nominative | Gender | Accusative | Dative | JP | ZH | Roles |
|---|---|---|---|---|---|---|---|
| dog | der Hund | m | den Hund | dem Hund | 犬 | 狗 | animal, agent, receiver, mover |
| cat | die Katze | f | die Katze | der Katze | 猫 | 貓 | animal, agent, receiver, mover |
| bird | der Vogel | m | den Vogel | dem Vogel | 鳥 | 鳥 | animal, agent, mover |
| horse | das Pferd | n | das Pferd | dem Pferd | 馬 | 馬 | animal, agent, vehicle_like |
| cow | die Kuh | f | die Kuh | der Kuh | 牛 | 牛 | animal, receiver |
| sheep | das Schaf | n | das Schaf | dem Schaf | 羊 | 羊 | animal, receiver |
| bear | der Bär | m | den Bären | dem Bären | 熊 | 熊 | animal, agent |
| rabbit | das Kaninchen | n | das Kaninchen | dem Kaninchen | ウサギ | 兔子 | animal, mover |
| duck | die Ente | f | die Ente | der Ente | アヒル | 鴨子 | animal, mover |
| fish | der Fisch | m | den Fisch | dem Fisch | 魚 | 魚 | animal, mover |
| frog | der Frosch | m | den Frosch | dem Frosch | カエル | 青蛙 | animal, mover |
| squirrel | das Eichhörnchen | n | das Eichhörnchen | dem Eichhörnchen | リス | 松鼠 | animal, receiver, mover |

---

## Physical Objects

Use physical objects as direct objects, possessions, static spatial subjects,
and endpoint-placement objects.

| English | German nominative | Gender | Accusative | Dative | JP | ZH | Roles |
|---|---|---|---|---|---|---|---|
| apple | der Apfel | m | den Apfel | dem Apfel | りんご | 蘋果 | object, food |
| ball | der Ball | m | den Ball | dem Ball | ボール | 球 | object, toy |
| book | das Buch | n | das Buch | dem Buch | 本 | 書 | object, school |
| cup | der Becher | m | den Becher | dem Becher | コップ | 杯子 | object, container |
| hammer | der Hammer | m | den Hammer | dem Hammer | ハンマー | 錘子 | object, tool, means |
| basket | der Korb | m | den Korb | dem Korb | かご | 籃子 | object, container |
| box | die Kiste | f | die Kiste | der Kiste | 箱 | 箱子 | object, container |
| coat | der Mantel | m | den Mantel | dem Mantel | コート | 外套 | object, clothing |
| bread | das Brot | n | das Brot | dem Brot | パン | 麵包 | object, food |
| pencil | der Bleistift | m | den Bleistift | dem Bleistift | 鉛筆 | 鉛筆 | object, school |
| chalk | die Kreide | f | die Kreide | der Kreide | チョーク | 粉筆 | object, school |
| bowl | die Schüssel | f | die Schüssel | der Schüssel | ボウル | 碗 | object, container |
| bottle | die Flasche | f | die Flasche | der Flasche | ボトル | 瓶子 | object, container |
| blanket | die Decke | f | die Decke | der Decke | 毛布 | 毯子 | object, home |
| chair | der Stuhl | m | den Stuhl | dem Stuhl | 椅子 | 椅子 | object, furniture, place |
| table | der Tisch | m | den Tisch | dem Tisch | テーブル | 桌子 | object, furniture, place |
| bench | die Bank | f | die Bank | der Bank | ベンチ | 長椅 | object, furniture, place |
| door | die Tür | f | die Tür | der Tür | ドア | 門 | object, place |
| window | das Fenster | n | das Fenster | dem Fenster | 窓 | 窗戶 | object, place |
| bed | das Bett | n | das Bett | dem Bett | ベッド | 床 | object, furniture, place |
| bag | die Tasche | f | die Tasche | der Tasche | かばん | 袋子 | object, container |
| bucket | der Eimer | m | den Eimer | dem Eimer | バケツ | 水桶 | object, container |
| broom | der Besen | m | den Besen | dem Besen | ほうき | 掃帚 | object, tool |
| wrench | der Schraubenschlüssel | m | den Schraubenschlüssel | dem Schraubenschlüssel | レンチ | 扳手 | object, tool, means |
| crate | die Kiste | f | die Kiste | der Kiste | 木箱 | 板條箱 | object, container |
| document | das Dokument | n | das Dokument | dem Dokument | 書類 | 文件 | object, school |

---

## Vehicles And Means

Use these for `mit` as vehicle/means and for movement/path examples.

| English | German nominative | Gender | Accusative | Dative | JP | ZH | Roles |
|---|---|---|---|---|---|---|---|
| bus | der Bus | m | den Bus | dem Bus | バス | 公車 | vehicle, means |
| car | das Auto | n | das Auto | dem Auto | 車 | 車 | vehicle, means |
| train | der Zug | m | den Zug | dem Zug | 電車 | 火車 | vehicle, means |
| bike | das Fahrrad | n | das Fahrrad | dem Fahrrad | 自転車 | 腳踏車 | vehicle, means |
| bicycle | das Fahrrad | n | das Fahrrad | dem Fahrrad | 自転車 | 腳踏車 | vehicle, means |
| boat | das Boot | n | das Boot | dem Boot | ボート | 船 | vehicle, means |
| airplane | das Flugzeug | n | das Flugzeug | dem Flugzeug | 飛行機 | 飛機 | vehicle, means |
| truck | der Lastwagen | m | den Lastwagen | dem Lastwagen | トラック | 卡車 | vehicle, means |
| wagon | der Wagen | m | den Wagen | dem Wagen | ワゴン | 車 | vehicle, means |

---

## Places And Spatial Anchors

Use these as locations, sources, targets, and path anchors.

| English | German nominative | Gender | Accusative | Dative | JP | ZH | Roles |
|---|---|---|---|---|---|---|---|
| house | das Haus | n | das Haus | dem Haus | 家 | 房子 | place, source, target |
| home | das Zuhause | n | das Zuhause | dem Zuhause | 家 | 家 | place, source, target |
| kitchen | die Küche | f | die Küche | der Küche | 台所 | 廚房 | place, source, target |
| garden | der Garten | m | den Garten | dem Garten | 庭 | 花園 | place, source, target |
| school | die Schule | f | die Schule | der Schule | 学校 | 學校 | place, source, target |
| city | die Stadt | f | die Stadt | der Stadt | 町 | 城市 | place, target |
| market | der Markt | m | den Markt | dem Markt | 市場 | 市場 | place, target |
| restaurant | das Restaurant | n | das Restaurant | dem Restaurant | レストラン | 餐廳 | place, target |
| university | die Universität | f | die Universität | der Universität | 大学 | 大學 | place, target |
| park | der Park | m | den Park | dem Park | 公園 | 公園 | place, target |
| road | die Straße | f | die Straße | der Straße | 道 | 道路 | path, place |
| bridge | die Brücke | f | die Brücke | der Brücke | 橋 | 橋 | path, place |
| river | der Fluss | m | den Fluss | dem Fluss | 川 | 河流 | place, path |
| forest | der Wald | m | den Wald | dem Wald | 森 | 森林 | place, source, target |
| field | das Feld | n | das Feld | dem Feld | 畑 | 田野 | place, target |
| pond | der Teich | m | den Teich | dem Teich | 池 | 池塘 | place, target |
| room | das Zimmer | n | das Zimmer | dem Zimmer | 部屋 | 房間 | place |
| floor | der Boden | m | den Boden | dem Boden | 床 | 地板 | place |
| wall | die Wand | f | die Wand | der Wand | 壁 | 牆 | place |
| tree | der Baum | m | den Baum | dem Baum | 木 | 樹 | place, source |
| riverbank | das Ufer | n | das Ufer | dem Ufer | 川岸 | 河岸 | place |
| schoolyard | der Schulhof | m | den Schulhof | dem Schulhof | 校庭 | 校園 | place |
| outside | draußen | adv | draußen | draußen | 外 | 外面 | place |
| inside | drinnen | adv | drinnen | drinnen | 中 | 裡面 | place |

---

## Verbs By Function

Use the English lemma in prompts. Localize naturally in generated lines.

### Receiver / Dative

| English | German | JP | ZH | Roles |
|---|---|---|---|---|
| give | geben | あげる | 給 | receiver |
| show | zeigen | 見せる | 給...看 | receiver |
| help | helfen | 助ける | 幫助 | receiver |
| answer | antworten | 答える | 回答 | receiver |
| tell | erzählen | 話す | 告訴 | receiver |
| bring | bringen | 持ってくる | 帶來 | receiver, object |
| send | schicken | 送る | 送 | receiver |
| lend | leihen | 貸す | 借給 | receiver |
| offer | anbieten | 差し出す | 提供 | receiver |
| hand | reichen | 手渡す | 遞給 | receiver |
| pass | geben | 渡す | 傳給 | receiver |
| teach | beibringen | 教える | 教 | receiver |

### Object / Accusative Patient

| English | German | JP | ZH | Roles |
|---|---|---|---|---|
| see | sehen | 見る | 看見 | object |
| find | finden | 見つける | 找到 | object |
| hold | halten | 持つ | 拿著 | object |
| carry | tragen | 運ぶ | 搬 | object |
| take | nehmen | 取る | 拿 | object |
| open | öffnen | 開ける | 打開 | object |
| cut | schneiden | 切る | 切 | object |
| read | lesen | 読む | 讀 | object |
| write | schreiben | 書く | 寫 | object |
| throw | werfen | 投げる | 丟 | object, target |
| roll | rollen | 転がす | 滾動 | object, target |
| put | stellen | 置く | 放 | object, target |
| place | legen | 置く | 放置 | object, target |
| set | setzen | 置く | 放 | object, target |

### Means / Movement / Path

| English | German | JP | ZH | Roles |
|---|---|---|---|---|
| go | gehen | 行く | 去 | movement |
| come | kommen | 来る | 來 | movement |
| walk | gehen | 歩く | 走路 | movement |
| run | laufen | 走る | 跑 | movement |
| move | sich bewegen | 動く | 移動 | movement |
| ride | fahren | 乗る | 騎 / 搭 | means, movement |
| drive | fahren | 運転する | 開車 | means, movement |
| work | arbeiten | 働く | 工作 | means |
| play | spielen | 遊ぶ | 玩 | means |
| sit | sitzen | 座る | 坐 | static |
| stand | stehen | 立つ | 站 | static |
| lie | liegen | 横たわる | 躺 | static |
| sleep | schlafen | 眠る | 睡覺 | static |
| wake | aufwachen | 起きる | 醒來 | change |
| grow | wachsen | 育つ | 成長 | change |
| become | werden | になる | 變成 | change |
| turn | werden | 変わる | 變成 | change |
| fall | fallen | 落ちる | 掉落 | movement |
| rise | steigen | 上がる | 上升 | movement |

---

## Prepositions And Particle Cues

| Function | German | JP cue | ZH cue | Notes |
|---|---|---|---|---|
| accompaniment | `mit` + dative | と | 和 | `mit dem Hund` |
| instrument | `mit` + dative | で | 用 | `mit dem Hammer` |
| vehicle / means | `mit` + dative | で | 搭 / 乘 | `mit dem Bus` |
| nearby location | `bei` + dative | のそばに | 在...旁邊 | static relation |
| source | `von` / `aus` + dative | から | 從 | origin |
| destination relation | `zu` / `nach` + dative | に / へ | 到 | relation endpoint |
| static two-way | `in/auf/unter/über/an/vor/hinter/neben/zwischen` + dative | に / で | 在 | location |
| movement endpoint | `in/auf/unter/über/an/vor/hinter/neben/zwischen` + accusative | に / へ | 到 / 往 | endpoint |
| direct object | accusative object | を | object position | patient |
| owner | genitive / `von` | の | 的 | ownership |


# Annotation Audit — 2026-06-13

Sample: 48 files (12 per tier, seed=42)
Model: deepseek/deepseek-v4-flash

| Verdict | Count |
|---------|-------|
| OK      | 0 |
| ISSUES  | 17 |
| ERROR   | 31 |

---

## Files with issues

### `training_data/01_language/teaching_stories/tier_1/actions_care_life/marrying_marked.md`

ISSUE 1: JP sentence 2: "抑えさせた" is not the main verb; the main verb is "雇って" (employed) which is not marked as *verb*.
ISSUE 2: JP sentence 3: <馬> is incorrectly bracketed as <GEN>; the subject is "馬のたてがみ" (the horse's mane) and should be (NOM) with <GEN> inside it, not split.
ISSUE 3: JP sentence 6: "包んだ" is not the natural verb for "encompassed"; should be "包んだ" or similar, but the annotation is acceptable; however, the {ACC} "村全体を" is correct.
ISSUE 4: ZH sentence 5: "令" is not the main verb; the sentence means "The noise was overwhelming" but here "令" (causes) changes the structure; should be *是* or similar, and {人} is not a direct object in the expected sense.
ISSUE 5: ZH sentence 9: "正在把{白天} *轉換成* [傍晚]" — the *verb* should be "轉換" alone, not "轉換成"; also "把" construction is not correctly annotated (the object "白天" is inside a "把" phrase, not a direct {ACC}).
ISSUE 6: ZH sentence 14: "點了點{頭}" — "頭" is not a direct object; it's a cognate object or part of a verb phrase; should not have {ACC}.

### `training_data/01_language/teaching_stories/tier_1/actions_care_life/sanity_marked.md`

ISSUE 1: Japanese: sentence "The village of Gwen had many traditions" lacks (NOM) and incorrectly marks the subject as {ACC}; also the role of 'village' is inconsistent with English (NOM vs [DAT]).  
ISSUE 2: Chinese: sentence "他對青蛙說話" marks the preposition "對" as a verb and has two asterisked words; main verb should be "說話".  
ISSUE 3: Chinese: sentence "在葉子上留下指紋" marks the preposition "在" as a verb and has two asterisked words; main verb should be "留下".  
ISSUE 4: Chinese: sentence "青蛙背上有個指紋" lumps location and object into a single {ACC} clause, inconsistent with English which separates ACC and DAT roles.

### `training_data/01_language/teaching_stories/tier_1/basic_cognitive_verbs/yucky_2_marked.md`

ISSUE 1: EN "The bread was *inducing* {a yucky feeling}" — "inducing" is not the main verb; "was" is the copula, and "inducing" is a participle; should be *was* with no *verb* on "inducing".  
ISSUE 2: JP "[パンには](ぐにゃぐにゃした部分)*あった*" — missing (NOM) for the subject; "パンには" is a topic/location, not a nominative subject.  
ISSUE 3: JP "(子どもが)[<鍋>のそばに]*座った*" — [DAT] wraps a locative phrase, not an indirect object or dative prepositional phrase.  
ISSUE 4: JP "(子どもは)[料理人に]*尋ねた*" — [DAT] used for the person being asked, but in the EN and DE versions this is {ACC} (direct object); inconsistent role bracketing.  
ISSUE 5: JP "(子どもは)[良いパンに]{<憧れ>の目を}*向けた*" — [DAT] on "良いパンに" is a directional/locative, not an indirect object; EN/DE use {ACC} or no bracket for the same role.  
ISSUE 6: ZH "(孩子) 把{那口} *吐*出來" — "把" construction splits the {ACC} constituent; the object should be bracketed as a whole phrase including "把".  
ISSUE 7: ZH "(孩子) 把{碗} *推*開" — same issue as above; "把碗" should be bracketed together as {ACC}.  
ISSUE 8: ZH "(麵包) 很 *噁心*" — missing (NOM) for the subject? Actually (麵包) is present, but "很" is an adverb, not part of the verb; *噁心* is correct, but the sentence is acceptable. No issue.  
ISSUE 9: ZH "(孩子) 渴望地 *看著* {好麵包}" — "渴望地" is an adverb, not bracketed, but the {ACC} wraps only "好麵包", missing the adverbial; no rule violation, but note EN/DE have different structure for this sentence.  
ISSUE 10: ZH "(這個麵包) *噁心* 嗎?" — missing copula; *噁心* is used as a verb, but in EN/DE the copula is present; inconsistent with other languages.

### `training_data/01_language/teaching_stories/tier_1/basic_materials_substances/raisin_marked.md`

ISSUE 1: EN and DE: negation included inside *verb* asterisks (e.g., "*did not listen*", "*hörte nicht zu*") — verb only should be marked, not entire phrase.  
ISSUE 2: DE: verb “wischte … ab” split, with *ab* marked separately instead of as part of the main verb *wischte ab*.  
ISSUE 3: JP: multiple sentences lack required (NOM) — e.g., “*かぶっていた* {ヘルメットを}”, “[地面に] {レーズンを} *見つけた*”, “[手に] *取った*”, “シャツで *拭いた*”, “日差しで *固まっていた*”, “{レーズンを} [口に] *入れた*”, “*甘かった*”, “*美味しかった*”, and inside quote “*だ* {負け犬}”.  
ISSUE 4: JP: sentence “(彼は) *拾い上げた* {それを}” is followed by “[手に] *取った*” with no subject — another missing (NOM).  
ISSUE 5: CN: compound sentence “(他) *看到* { [地上] 有 {一顆葡萄乾} } [上面] *有* {煤灰}” has two verbs; the second verb “*有*” has no (NOM).  
ISSUE 6: CN: “(她) *不友善*” uses an adjective predicate without a copula verb — not consistent with other languages (EN *was*, DE *war*, JP *意地悪だった*) and violates requirement for a *verb*.  
ISSUE 7: Inconsistent semantic–role bracketing for soot: JP marks (煤が) as NOM, while EN/DE/CN mark {soot}/{Ruß}/{煤灰} as ACC.

### `training_data/01_language/teaching_stories/tier_1/basic_verbs_desire/busy_marked.md`

ISSUE 1: Predicate nominative after copula incorrectly marked as {ACC} in all four languages (e.g., EN: "a blessing", DE: "ein Segen", JP: "祝福", ZH: "一種祝福").
ISSUE 2: Adverbial of duration incorrectly marked as {ACC} in all four languages (e.g., EN: "all day", DE: "den ganzen Tag", JP: "一日中", ZH: "整天").
ISSUE 3: JP sentence 4 (bee): second clause "{一日中} *働く*" lacks required (NOM) subject.
ISSUE 4: JP sentence 3: <声>で incorrectly marked as <GEN> (で is not a genitive particle).
ISSUE 5: JP sentence 7: subordinate verb "見て" is marked as *verb*, but only the main verb *うなずく* should carry the asterisk (inconsistent with EN/DE/ZH).
ISSUE 6: JP sentence 8: NOM annotation is erroneous – "(ここでは)" is not a subject, and "何も" is unmarked; the subject structure is unclear.
ISSUE 7: Inconsistent role bracketing for "beholding/receiving the view": EN/ZH use {ACC}, DE uses [DAT] for the prepositional phrase, violating rule 5 (same semantic role should be bracketed consistently).
ISSUE 8: ZH sentence 4: "在 [花朵間]" marks a locative phrase as [DAT], while EN/DE/JP use [DAT] for "from X to Y" motion – different semantic roles.

### `training_data/01_language/teaching_stories/tier_1/body_parts_actions/jerking_marked.md`

ISSUE 1: EN "jerked" — missing *verb* markers in the [user] line, but that's correct; actually no issues there. RE-CHECKING: JP sentence 12 "網が引かれた" has (網が) but no *verb* marker around "引かれた" — verb is present. Actually "引かれた" is *verb*? It is not marked. ISSUE 1: JP sentence "網が引かれた" is missing *verb* brackets around "引かれた".  
ISSUE 2: JP sentence "網が引かれた" also missing [DAT] or {ACC} — "彼女の手でぐっと" is unmarked but could be instrumental; no role marker applied.  
ISSUE 3: EN sentence "(He) *said* {the fish was big}" — {the fish was big} is a full clause, not a simple direct object; this stretches {ACC} scope.  
ISSUE 4: JP sentence "(彼は) *言った* {「魚は大きかった」と}" — the quoted clause with と is direct object, but と should be included or the object should be the quote; currently {「魚は大きかった」と} is acceptable but the と could be argued as part of the object.  
ISSUE 5: ZH sentence "(一條魚)在[她附近] *抽動了一下*" — (NOM) is "(一條魚)" but the verb phrase includes "在[她附近]" before the verb, which breaks the expected (NOM) *verb* [DAT] order; the adverb/prepositional phrase is correctly bracketed but the order differs from other languages.  
ISSUE 6: ZH sentence "(牠)在[空中] *翻了*{一個身}" — {一個身} is not a direct object in the same sense as other languages' "flipped in the air" (no object). Forcing {ACC} here is inconsistent with EN/DE/JP where no {ACC} appears.  
ISSUE 7: DE sentence "(Er) *sprang* in die Luft." — "in die Luft" has no [DAT] brackets, though it's analogous to EN "in [the air]" and JP "[空中で]". Missing [DAT] in DE.  
ISSUE 8: JP sentence "(波紋が) *できた* [水面に]" — "できた" is not the main verb in EN/DE (EN "made", DE "machte"); JP uses an intransitive verb "できた" while other languages have transitive "made". This breaks semantic role consistency across languages.

### `training_data/01_language/teaching_stories/tier_1/emotions_feelings/squish_3_marked.md`

ISSUE 1: JP sentence 1: {道を} should be [DAT] (path is location, not direct object), and (NOM) is missing for the second clause {泥を}*踏む* — no subject marked.  
ISSUE 2: JP sentence 1: {泥を}*踏む* has no (NOM) — subject "he" is unmarked.  
ISSUE 3: JP sentence 2: {それを}*絞る* has no (NOM) — subject "she" is unmarked.  
ISSUE 4: JP sentence 3: {スプーン一杯のジャムを}*取る* has no (NOM) — subject "he" is unmarked.  
ISSUE 5: JP sentence 4: {濡れた布を}*絞る* has no (NOM) — subject "woman" is unmarked.  
ISSUE 6: JP sentence 5: (それが){グチャが起こるときだ} — {グチャが起こるときだ} is a full clause, not a simple {ACC}; also (それが) is not a typical (NOM) subject performing an action.  
ISSUE 7: EN sentence 5: (That) *is* {when squish happens} — {when squish happens} is a clause, not a simple {ACC} direct object.  
ISSUE 8: DE sentence 5: (Das Quetschen) *passiert* — missing {ACC} and [DAT] but no issue per se, but (Das Quetschen) is not a typical subject performing an action (it's the event itself).  
ISSUE 9: ZH sentence 1: (他)*踩進*{泥巴裡} — {泥巴裡} includes a location particle "裡", should be [DAT] (into mud).  
ISSUE 10: ZH sentence 5: (那)*是*{擠壓發生的時候} — {擠壓發生的時候} is a clause, not a simple {ACC}.

### `training_data/01_language/teaching_stories/tier_1/movement_physical_actions/chop_marked.md`

ISSUE 1: JP sentence "(音が) *大きい*" has adjective instead of verb, violating rule 1.
ISSUE 2: ZH sentence "(聲音) *很大*" has adjective instead of verb.
ISSUE 3: ZH genitive annotation "(木頭的<中心性>)" incorrectly marks head noun as genitive; should wrap "木頭的".
ISSUE 4: JP genitive annotation "丸太<の>中心性" splits the genitive phrase; should wrap "丸太の".
ISSUE 5: [DAT] incorrectly used for locative and manner prepositional phrases (e.g., EN “by [an oak tree]”, “from [the field]”, “with [calmness]”; JP “野原から”; ZH “在[橡樹旁]”) which are not dative.
ISSUE 6: Inconsistent marking of predicate complements as {ACC} in JP and ZH for “causal” and “reason” sentences, while EN and DE do not mark them, violating rule 5.
ISSUE 7: ZH sentence “(他) *有* 很 {能力}” marks {ACC} for “ability” whereas EN/DE/JP do not mark this semantic role as ACC, inconsistent.

### `training_data/01_language/teaching_stories/tier_1/places_geography/mountain_marked.md`

ISSUE 1: EN sentence "Inside *was* (a sandwich)" — missing (NOM) for *was* (should be "(A sandwich) *was* inside" or similar).  
ISSUE 2: JP sentence "(野原は) *だった* {<山の>近く}" — {ACC} used for a location phrase, not a direct object.  
ISSUE 3: JP sentence "(子どもは) [家で] (宿題が) *あった*" — (NOM) should be the subject (宿題が), but (子どもは) is marked as NOM; also [DAT] placement is inconsistent with other languages.  
ISSUE 4: ZH sentence "(孩子) *玩* {那條帶子}" — {ACC} used for "play with" which should be [DAT] (as in EN/DE/JP).  
ISSUE 5: ZH sentence "(一個男人) *談論* {那座山}" — {ACC} used for "talk about" which should be [DAT] (as in EN/DE/JP).  
ISSUE 6: ZH sentence "(孩子) 在 [家] *有* {學校作業}" — (NOM) missing for *有* (should be "(孩子) *有* {學校作業} 在 [家]" or similar).  
ISSUE 7: ZH sentence "(山) 沒有 *改變*" — missing (NOM) for *改變* (should be "(山) *沒有改變*" with verb as *沒有改變* or split incorrectly).

### `training_data/01_language/teaching_stories/tier_1/visual_abstract_forms/spatula_2_marked.md`

ISSUE 1: JP sentence 1 missing (NOM) — "女の人が" is present but "(女の人が)" is incorrectly placed; also *verb* is *した* but {料理を} should be {ACC} not split from verb.
ISSUE 2: JP sentence 2 missing (NOM) — no subject annotated.
ISSUE 3: JP sentence 3 has <GEN> on "木の" but (NOM) is "柄が" — <GEN> should wrap "木の" correctly, but "柄が" is fine; however sentence lacks *verb*? Actually *あった* is present, but (NOM) is "柄が" — acceptable, but note <GEN> is applied to adjective-like "木の" which is a noun+の, acceptable.
ISSUE 4: JP sentence 4 missing (NOM) — "柄が" is present but not annotated as (NOM); instead it's plain text.
ISSUE 5: JP sentence 5 missing (NOM) — no subject annotated.
ISSUE 6: JP sentence 6 missing (NOM) — "パンは" is not annotated as (NOM); also *あった* is verb but (NOM) missing.
ISSUE 7: JP sentence 7 missing (NOM) — no subject annotated.
ISSUE 8: JP sentence 9 missing (NOM) — no subject annotated.
ISSUE 9: JP sentence 10 missing (NOM) — "ピザは" not annotated as (NOM).
ISSUE 10: JP sentence 12 missing (NOM) — no subject annotated.
ISSUE 11: JP sentence 13 missing (NOM) — "道具は" not annotated as (NOM).
ISSUE 12: JP sentence 14 missing (NOM) — "それは" not annotated as (NOM).
ISSUE 13: JP sentence 15 has {道具が} as {ACC} but が marks subject, not object — should be (NOM) or {ACC}? "子供は" is topic, but "道具が" is subject of 好き, so {ACC} is incorrect; should be (NOM) for 道具が or restructure.
ISSUE 14: ZH sentence 2 missing (NOM) — "她" is present but not annotated as (NOM).
ISSUE 15: ZH sentence 3 missing (NOM) — "器具" not annotated as (NOM).
ISSUE 16: ZH sentence 4 missing (NOM) — "木柄" not annotated as (NOM).
ISSUE 17: ZH sentence 6 missing (NOM) — "麵包" not annotated as (NOM).
ISSUE 18: ZH sentence 7 missing (NOM) — "她" not annotated as (NOM).
ISSUE 19: ZH sentence 8 missing (NOM) — "金屬" not annotated as (NOM).
ISSUE 20: ZH sentence 9 missing (NOM) — "她" not annotated as (NOM).
ISSUE 21: ZH sentence 10 missing (NOM) — "披薩" not annotated as (NOM).
ISSUE 22: ZH sentence 12 missing (NOM) — "他" not annotated as (NOM).
ISSUE 23: ZH sentence 13 missing (NOM) — "那個器具" not annotated as (NOM).
ISSUE 24: ZH sentence 14 missing (NOM) — "它" not annotated as (NOM).
ISSUE 25: ZH sentence 15 missing (NOM) — "小孩" not annotated as (NOM).

### `training_data/01_language/teaching_stories/tier_2/abstract_properties/absence_marked.md`

ISSUE 1: English/German/Chinese leave fragments like "No eggs" / "Keine Eier" / "沒有蛋" unannotated, but Japanese annotates them as (NOM) *verb* — violates rule 1 and rule 5.  
ISSUE 2: English "through [it]" (dative) lacks parallel marking in German/Japanese, while Chinese uses {ACC} for the same entity — inconsistent semantic role (rule 5).  
ISSUE 3: English "across {the path}" incorrectly uses {ACC} for a prepositional phrase; other languages treat the path as direct object of a separate verb — mismatched annotation (rule 3, rule 5).  
ISSUE 4: German final sentence lacks {ACC} for the object clause "was Abwesenheit bedeutete" — missing required role (rule 4, rule 5).  
ISSUE 5: Japanese "(それは) *だった* {<祖先の>もの}" uses {ACC} for a predicate complement, while English/German use [DAT] for a prepositional phrase "from an ancestor" — inconsistent role (rule 5).

### `training_data/01_language/teaching_stories/tier_2/basic_cognitive_verbs/disagree_3_marked.md`

ISSUE 1: In EN, "(It) *did not want* to be touched" — "did not want" is not a single verb; annotation splits the verb phrase incorrectly.
ISSUE 2: In DE, "(Es) *wollte* nicht gestreichelt werden" — "wollte nicht ... werden" is not a single content verb; should bracket the main verb "wollte" separately from the passive construction.
ISSUE 3: In JP, "(犬は) *触られたくなかった* のだ" — "触られたくなかった" includes a negative and desire auxiliary, not a single content verb as required.
ISSUE 4: In JP, "(怒りは) *なかった*" — missing (NOM) for the subject "怒りは" (should be marked with (NOM) or restructured).
ISSUE 5: In JP, "(ただ静かな<反対の>出来事) *だった*" — <反対の> wraps only an adjective, not a full genitive phrase; also "(NOM) is missing.
ISSUE 6: In JP, "(犬は) *大切にしていた* {<自分の>休息を}" — <自分の> is an adjective/pronoun, not a full genitive noun phrase; should not be bracketed alone.
ISSUE 7: In ZH, "(老婦人) *伸出了* {一隻手}" — "伸出了" is verb+aspect particle; should bracket only the verb "伸" or "伸出", not split.
ISSUE 8: In ZH, "(她) *揮著* {雙手} *表示* {拒絕}" — two verbs in one minimal clause without proper subject-verb pairing; "表示" should not be separate.
ISSUE 9: In ZH, "(孩子) *說*「*幫*{我}*找*{我的貓}」" — "幫" and "找" are both verbs; missing (NOM) for "找" and inconsistent verb bracketing.
ISSUE 10: In ZH, "*沒有* {生氣}" and "*只是* {一場安靜的不同意}" — both lack (NOM) and *verb* in same sentence; "沒有" and "只是" are not content verbs.

### `training_data/01_language/teaching_stories/tier_2/body_measure_style/polish_2_marked.md`

ISSUE 1: English: NOM bracket incorrectly includes "Later," in "Later, (the <child’s> mother)..."
ISSUE 2: German: Adverb "Dann" incorrectly bracketed as (Dann) before subject.
ISSUE 3: German: Adverb "Später" incorrectly bracketed as (Später) before subject.
ISSUE 4: Japanese: Sentence "*持っていた* {布と鍋を}" lacks (NOM) subject.
ISSUE 5: Japanese: Sentence "*かけた* {圧力を}" lacks (NOM) subject.
ISSUE 6: Japanese: Sentence "*買った* {レインコートを}" lacks (NOM) subject.
ISSUE 7: Japanese: Sentence "*微笑んだ*" lacks (NOM) subject.

### `training_data/01_language/teaching_stories/tier_2/movement_physical_actions/reel_2_marked.md`

ISSUE 1: English sentence "He did not quit" has two verb marks (*did* and *quit*) instead of a single main verb.  
ISSUE 2: German sentence "Er gab nicht auf" marks only *gab*, missing the separable prefix "auf" from the verb "aufgeben".  
ISSUE 3: Japanese has two sentences with empty NOM ( ( ) ) — missing subject for "巻きつけた" and "引いた".  
ISSUE 4: Japanese locative phrase "水の中で" is not bracketed as [DAT], while other languages bracket the equivalent location.  
ISSUE 5: Multiple prepositional phrases across languages are split (preposition outside bracket), e.g., "by [the millpond]", "am [Mühlteich]", "在[池塘邊]", violating rule 3 and consistency rule 5.

### `training_data/01_language/teaching_stories/tier_2/processes_operations/impairing_marked.md`

ISSUE 1: English: "(A storm) *developing*" lacks a finite verb — '*developing*' is a participle, not a main verb.
ISSUE 2: Japanese: Multiple sentences missing (NOM) — e.g., "{海を} *見たい*", "*試す*", "*滑る*", "*呼ぶ*", "{感謝<の>笑顔を} *見せる*", "{海を} *見る*", "[空と] *競う*", "[家に] *帰らなければならない*".
ISSUE 3: Japanese: Adjectives used as verbs — *痛い*, *涼しい*, *大きい* are not verbs.
ISSUE 4: Chinese: Adjectives used as verbs — *很痛*, *比較涼爽*, *很大* are not verbs.
ISSUE 5: Chinese: Missing (NOM) in "( ) *競爭* 與[天空]".
ISSUE 6: Inconsistency across languages: the ocean in "want to see" is marked as {ACC} in German and Japanese but not in English or Chinese, due to different verb selection — violates rule 5.

### `training_data/01_language/teaching_stories/tier_2/time_sequence/mixed-up_marked.md`

ISSUE 1: English: verb markers incorrectly include negation – "did *not stay*", "did *not know*" (rule 3).  
ISSUE 2: English: "{the bowl}" etc. after "looked at" should be dative/prepositional phrase, not ACC (rule 4).  
ISSUE 3: English, German, Chinese: prepositions left outside brackets (e.g., "in [a bowl]", "in [einer Schüssel]", "在[碗裡]") – brackets must wrap entire PP (rule 3).  
ISSUE 4: German: missing bracket for "in die falschen Kästen" in "Er steckte..." (rule 3).  
ISSUE 5: Japanese: multiple sentences lack (NOM) – empty parentheses used instead of explicit subject (rule 1).  
ISSUE 6: Japanese: missing brackets for locative phrases "ボウルで", "畑で", "市場で" (rule 3).  
ISSUE 7: Chinese: missing (NOM) – empty parentheses in " ( ) 沒有 *停留*" (rule 1).  
ISSUE 8: Chinese: missing bracket for "錯誤的箱子" as dative object (rule 3).  
ISSUE 9: Chinese: "*可以*" incorrectly marked as main verb – should mark the main predicate "很有趣" (rule 2).

### `training_data/01_language/teaching_stories/tier_3/abstract_concepts_info/chatter_2_marked.md`

ISSUE 1: JP: Missing <GEN> on "多くの人" in "多くの人の声が"; should be (<多くの人の>声が).
ISSUE 2: JP: Missing <GEN> on "おしゃべりの" in "おしゃべりの音は"; should be (<おしゃべりの>音は).
ISSUE 3: JP: Incorrect (NOM) on "今日は"; it is an adverbial topic, not a subject.
ISSUE 4: JP: Missing *verb* for "遊び" (play) in children's sentence; should be *遊び*.
ISSUE 5: JP: Incorrect {ACC} on "隅々まで"; it is an adverbial phrase, not a direct object.
ISSUE 6: EN/DE vs ZH: In the man-helping sentence, EN and DE do not mark the verb for "assist/zu helfen", but ZH marks "幫" and "搬"; inconsistent application of *verb* for the same semantic action.
ISSUE 7: ZH: Missing <GEN> on "管理市場的" in "(管理市場的規則)"; should be (<管理市場的>規則).
ISSUE 8: ZH: Missing <GEN> on "嘰嘰喳喳的" in "(嘰嘰喳喳的聲音)"; should be (<嘰嘰喳喳的>聲音).

### `training_data/01_language/teaching_stories/tier_1/actions_care_life/spiritual_marked.md`


### `training_data/01_language/teaching_stories/tier_1/kitchen_food_crafts/utensil_marked.md`


### `training_data/01_language/teaching_stories/tier_2/clothing_container/suit_marked.md`


### `training_data/01_language/teaching_stories/tier_2/colors_light_atmosphere/brightnes_2_marked.md`


### `training_data/01_language/teaching_stories/tier_2/communication_reasoning/classify_marked.md`


### `training_data/01_language/teaching_stories/tier_2/movement_physical_actions/trampling_3_marked.md`


### `training_data/01_language/teaching_stories/tier_2/separation_departure/shutting_marked.md`


### `training_data/01_language/teaching_stories/tier_2/social_people_places/cody_marked.md`


### `training_data/01_language/teaching_stories/tier_3/abstract_states/blindspot_marked.md`


### `training_data/01_language/teaching_stories/tier_3/abstract_states/salvaging_2_marked.md`


### `training_data/01_language/teaching_stories/tier_3/basic_verbs_desire/page_marked.md`


### `training_data/01_language/teaching_stories/tier_3/communication_reasoning/basis_marked.md`


### `training_data/01_language/teaching_stories/tier_3/culture_study_media/causal_marked.md`


### `training_data/01_language/teaching_stories/tier_3/math_numbers/normalized_marked.md`


### `training_data/01_language/teaching_stories/tier_3/places_geography/newspaper_marked.md`


### `training_data/01_language/teaching_stories/tier_3/separation_departure/eroding_2_marked.md`


### `training_data/01_language/teaching_stories/tier_3/time_quantity/survey_2_marked.md`


### `training_data/01_language/teaching_stories/tier_3/time_sequence/bit_marked.md`


### `training_data/01_language/teaching_stories/tier_3/visual_abstract_forms/complexity_marked.md`


### `training_data/01_language/teaching_stories/tier_4/abstract_properties/atypical_marked.md`


### `training_data/01_language/teaching_stories/tier_4/abstract_states/surpassing_2_marked.md`


### `training_data/01_language/teaching_stories/tier_4/actions_care_life/childhood_marked.md`


### `training_data/01_language/teaching_stories/tier_4/actions_care_life/preserve_marked.md`


### `training_data/01_language/teaching_stories/tier_4/basic_verbs_desire/video_marked.md`


### `training_data/01_language/teaching_stories/tier_4/communication_reasoning/implementing_2_marked.md`


### `training_data/01_language/teaching_stories/tier_4/emotions_feelings/neighing_marked.md`


### `training_data/01_language/teaching_stories/tier_4/emotions_feelings/rudenes_2_marked.md`


### `training_data/01_language/teaching_stories/tier_4/emotions_feelings/unpleasant_marked.md`


### `training_data/01_language/teaching_stories/tier_4/knowledge_truth/doesn_t_marked.md`


### `training_data/01_language/teaching_stories/tier_4/movement_physical_actions/row_marked.md`


### `training_data/01_language/teaching_stories/tier_4/time_sequence/final_marked.md`


---

## Clean files


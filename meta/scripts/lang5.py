#!/usr/bin/env python3
"""
Lang-5 corpus generator — Q&A pairs and fragment answers.

Each file: 3–5 Q/A exchanges.
Each exchange: Q block (EN/DE/JP/ZH) + blank line + A block (EN/DE/JP/ZH).

Sub-levels:
  5a_wer    — Who (subject / nominative):   Wer hat das Wasser getrunken? → Das Kind.
  5a_wen    — Who/Whom (object / accusative): Wen sah Klaus? → Die Frau.
  5a_wem    — Who/Whom (dative):             Wem half Tom? → Dem Mann.
  5a_wessen — Whose (genitive):              Wessen Blumen sind das? → Die Blumen von der Frau.
  5b_wo     — Where (static, dative):        Wo ist die Katze? → In der Küche.
  5b_wohin  — Where to (goal, accusative):   Wohin ist X gegangen? → In den Park.
  5b_woher  — Where from (source, dative):   Woher kommt X? → Von der Schule.
  5c_when   — When:                          Wann ist X angekommen? → Gestern.
  5d_why    — Why:                           Warum ist X gegangen? → Wegen des Regens.
  5e_how    — How / With what:               Womit hat X geschnitten? → Mit der Schere.
  5f_yn     — Yes/No (incl. Doch contrast):  Hat X gegessen? → Ja. / Nein. / Doch!

Usage:
  python3 meta/scripts/lang5.py gen    [--workers 4] [--batch 5] [--limit N] [--dry-run]
  python3 meta/scripts/lang5.py report

Auth:
  1. OPENROUTER_API_KEY env var
  2. OPENAI_API_KEY env var
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR   = REPO_ROOT / "training_data" / "lang" / "lang_5"
BASE_URL  = "https://openrouter.ai/api/v1"
MODEL     = "deepseek/deepseek-v4-flash"

_lock = threading.Lock()

# ─────────────────────────────────────────────────────────────────
# Job matrix
# ─────────────────────────────────────────────────────────────────

JOBS: list[dict] = [

    # ── 5A wer — subject / nominative ────────────────────────────
    # DE question word: Wer. Answer: nominative (das Kind / die Frau / der Mann).
    # JP answer: retain が.  ZH answer: bare NP.

    {"frame_id": "5a_wer_drink",  "sublevel": "5a_wer",
     "verb_en": "drink",  "verb_de": "trinken",    "verb_jp": "飲む",    "verb_zh": "喝",
     "desc": "Who drank X? — subject identification; vary liquid and subject across exchanges"},

    {"frame_id": "5a_wer_eat",    "sublevel": "5a_wer",
     "verb_en": "eat",    "verb_de": "essen",      "verb_jp": "食べる",  "verb_zh": "吃",
     "desc": "Who ate X? — vary food item and tense; mix proper names and common NPs in answers"},

    {"frame_id": "5a_wer_sleep",  "sublevel": "5a_wer",
     "verb_en": "sleep",  "verb_de": "schlafen",   "verb_jp": "寝る",    "verb_zh": "睡",
     "desc": "Who slept? — intransitive; vary time adverbials; mix animate subjects"},

    {"frame_id": "5a_wer_run",    "sublevel": "5a_wer",
     "verb_en": "run",    "verb_de": "laufen",     "verb_jp": "走る",    "verb_zh": "跑",
     "desc": "Who ran? — intransitive motion; DE Perfekt: ist gelaufen"},

    {"frame_id": "5a_wer_win",    "sublevel": "5a_wer",
     "verb_en": "win",    "verb_de": "gewinnen",   "verb_jp": "勝つ",    "verb_zh": "赢",
     "desc": "Who won? — vary the object won (game, race, prize); mix answers"},

    {"frame_id": "5a_wer_arrive", "sublevel": "5a_wer",
     "verb_en": "arrive", "verb_de": "ankommen",   "verb_jp": "着く",    "verb_zh": "到",
     "desc": "Who arrived? — DE Perfekt: ist angekommen; vary destination across exchanges"},

    {"frame_id": "5a_wer_fall",   "sublevel": "5a_wer",
     "verb_en": "fall",   "verb_de": "fallen",     "verb_jp": "落ちる",  "verb_zh": "摔",
     "desc": "Who fell? — DE Perfekt: ist gefallen; include animate and inanimate subjects"},

    {"frame_id": "5a_wer_laugh",  "sublevel": "5a_wer",
     "verb_en": "laugh",  "verb_de": "lachen",     "verb_jp": "笑う",    "verb_zh": "笑",
     "desc": "Who laughed? — intransitive; vary context (at what, when)"},

    {"frame_id": "5a_wer_leave",  "sublevel": "5a_wer",
     "verb_en": "leave",  "verb_de": "gehen",      "verb_jp": "行く",    "verb_zh": "走",
     "desc": "Who left? — DE Perfekt: ist gegangen; vary destination or manner"},

    {"frame_id": "5a_wer_id",     "sublevel": "5a_wer",
     "verb_en": "be",     "verb_de": "sein",       "verb_jp": "だ",      "verb_zh": "是",
     "desc": "Who is that / who is this? — Wer ist das? / Wer ist das Kind? — identification copula; answers are names"},

    # ── 5A wen — direct object / accusative ──────────────────────
    # DE question word: Wen. Answer: accusative (den Mann / die Frau / das Kind).
    # IMPORTANT: helfen is dative — it belongs in 5a_wem, not here.
    # JP answer: bare NP (drop を in fragment answers).

    {"frame_id": "5a_wen_see",    "sublevel": "5a_wen",
     "verb_en": "see",    "verb_de": "sehen",      "verb_jp": "見る",    "verb_zh": "看見",
     "desc": "Whom did X see? — Wen sah Klaus? — accusative object; vary subject and tense; DE: den Mann (masc acc)"},

    {"frame_id": "5a_wen_meet",   "sublevel": "5a_wen",
     "verb_en": "meet",   "verb_de": "treffen",    "verb_jp": "会う",    "verb_zh": "見到",
     "desc": "Whom did X meet? — Wen hat Tom getroffen? — vary meeting context"},

    {"frame_id": "5a_wen_know",   "sublevel": "5a_wen",
     "verb_en": "know",   "verb_de": "kennen",     "verb_jp": "知っている", "verb_zh": "認識",
     "desc": "Who does X know? — Wen kennt Kate? — present tense; use kennen not wissen for persons"},

    {"frame_id": "5a_wen_find",   "sublevel": "5a_wen",
     "verb_en": "find",   "verb_de": "finden",     "verb_jp": "見つける", "verb_zh": "找到",
     "desc": "Whom did X find? — Wen hat er gefunden? — vary the context (lost, searching)"},

    {"frame_id": "5a_wen_call",   "sublevel": "5a_wen",
     "verb_en": "call",   "verb_de": "rufen",      "verb_jp": "呼ぶ",    "verb_zh": "叫",
     "desc": "Whom did X call/summon? — Wen hat sie gerufen? — rufen = call out to; vary situation"},

    {"frame_id": "5a_wen_visit",  "sublevel": "5a_wen",
     "verb_en": "visit",  "verb_de": "besuchen",   "verb_jp": "訪ねる",  "verb_zh": "拜訪",
     "desc": "Whom did X visit? — Wen hat Tom besucht? — vary who is visited (person, family)"},

    {"frame_id": "5a_wen_invite", "sublevel": "5a_wen",
     "verb_en": "invite", "verb_de": "einladen",   "verb_jp": "招待する", "verb_zh": "邀請",
     "desc": "Whom did X invite? — Wen hat Klaus eingeladen? — vary occasion (party, meal)"},

    {"frame_id": "5a_wen_teach",  "sublevel": "5a_wen",
     "verb_en": "teach",  "verb_de": "unterrichten","verb_jp": "教える", "verb_zh": "教",
     "desc": "Whom does X teach? — Wen unterrichtet Corinna? — present habitual; answers: groups or named students"},

    {"frame_id": "5a_wen_love",   "sublevel": "5a_wen",
     "verb_en": "love",   "verb_de": "lieben",     "verb_jp": "愛する",  "verb_zh": "愛",
     "desc": "Whom does X love? — Wen liebt Hans? — present; vary subjects and answers"},

    {"frame_id": "5a_wen_wait",   "sublevel": "5a_wen",
     "verb_en": "wait for","verb_de": "warten auf", "verb_jp": "待つ",   "verb_zh": "等",
     "desc": "Whom is X waiting for? — Auf wen wartet Tom? — DE: auf+wen (prepositional object); JP: 誰を待っている？"},

    # ── 5A wem — dative object ────────────────────────────────────
    # DE question word: Wem. Answer: dative (dem Kind / der Frau / dem Mann).
    # JP: particle depends on the Japanese verb (not mechanically に — check each verb).
    # JP answer: bare NP (drop particle in fragment).

    {"frame_id": "5a_wem_help",   "sublevel": "5a_wem",
     "verb_en": "help",   "verb_de": "helfen",     "verb_jp": "助ける",  "verb_zh": "幫助",
     "desc": "Whom did X help? — Wem half Tom? — helfen ALWAYS takes dative in DE; JP: 誰を助けた？(を); vary who helps whom"},

    {"frame_id": "5a_wem_thank",  "sublevel": "5a_wem",
     "verb_en": "thank",  "verb_de": "danken",     "verb_jp": "感謝する","verb_zh": "感謝",
     "desc": "Whom did X thank? — Wem hat Kate gedankt? — dative-only; JP: 誰に感謝した？(に)"},

    {"frame_id": "5a_wem_follow", "sublevel": "5a_wem",
     "verb_en": "follow", "verb_de": "folgen",     "verb_jp": "従う",    "verb_zh": "跟隨",
     "desc": "Whom did X follow? — Wem ist Klaus gefolgt? — DE Perfekt: ist gefolgt (motion); JP: 誰に従った？(に)"},

    {"frame_id": "5a_wem_trust",  "sublevel": "5a_wem",
     "verb_en": "trust",  "verb_de": "vertrauen",  "verb_jp": "信頼する","verb_zh": "信任",
     "desc": "Whom does X trust? — Wem vertraut Hanako? — present; JP: 誰を信頼している？(を)"},

    {"frame_id": "5a_wem_believe","sublevel": "5a_wem",
     "verb_en": "believe","verb_de": "glauben",    "verb_jp": "信じる",  "verb_zh": "相信",
     "desc": "Whom does X believe? — Wem glaubt Peter? — present; JP: 誰を信じている？(を)"},

    {"frame_id": "5a_wem_answer", "sublevel": "5a_wem",
     "verb_en": "answer", "verb_de": "antworten",  "verb_jp": "答える",  "verb_zh": "回答",
     "desc": "Whom did X answer? — Wem hat sie geantwortet? — dative-only; JP: 誰に答えた？(に)"},

    {"frame_id": "5a_wem_give",   "sublevel": "5a_wem",
     "verb_en": "give",   "verb_de": "geben",      "verb_jp": "あげる",  "verb_zh": "給",
     "desc": "Whom did X give the [object] to? — Wem hat Tom das Buch gegeben? — double-object verb; retain DO in question; JP: 誰に[object]をあげた？(に); vary object across exchanges"},

    {"frame_id": "5a_wem_show",   "sublevel": "5a_wem",
     "verb_en": "show",   "verb_de": "zeigen",     "verb_jp": "見せる",  "verb_zh": "給…看",
     "desc": "Whom did X show the [object] to? — Wem hat Kate das Bild gezeigt? — double-object; retain DO; vary object"},

    {"frame_id": "5a_wem_tell",   "sublevel": "5a_wem",
     "verb_en": "tell",   "verb_de": "erzählen",   "verb_jp": "話す",    "verb_zh": "告訴",
     "desc": "Whom did X tell the [story/news] to? — Wem hat er die Geschichte erzählt? — double-object; retain DO"},

    {"frame_id": "5a_wem_send",   "sublevel": "5a_wem",
     "verb_en": "send",   "verb_de": "schicken",   "verb_jp": "送る",    "verb_zh": "寄",
     "desc": "Whom did X send the [letter/package] to? — Wem hat Susanne den Brief geschickt? — double-object; vary object"},

    {"frame_id": "5a_wem_bring",  "sublevel": "5a_wem",
     "verb_en": "bring",  "verb_de": "bringen",    "verb_jp": "持ってくる","verb_zh": "帶來",
     "desc": "Whom did X bring the [object] to? — Wem hat Hans die Blumen gebracht? — double-object; vary object"},

    # ── 5A wessen — possessor / genitive ─────────────────────────
    # DE question word: Wessen. Answer forms:
    #   proper noun: Name + -s (Peters Stift / Toms Buch — no article)
    #   common NP spoken: NP von + dative (Der Stift von dem Mann / Die Blumen von der Frau)
    #   common NP formal: NP + genitive article (rarer — include occasionally for contrast)
    # JP answer: retain の (女の人の。/ 太郎の。)
    # ZH answer: NP + 的 (那個女人的。/ 太郎的。)
    # Mix proper-noun answers and common-NP answers within each file.

    {"frame_id": "5a_wessen_flower",  "sublevel": "5a_wessen",
     "noun_en": "flowers", "noun_de": "Blumen", "noun_jp": "花", "noun_zh": "花",
     "desc": "Whose flowers are those? — Wessen Blumen sind das? — mix name answers (Peters Blumen) and NP answers (von der Frau)"},

    {"frame_id": "5a_wessen_pen",     "sublevel": "5a_wessen",
     "noun_en": "pen",    "noun_de": "Stift",   "noun_jp": "ペン",  "noun_zh": "筆",
     "desc": "Whose pen is this? — Wessen Stift ist das? — mix name answers and NP answers; Stift is masc: von dem Mann"},

    {"frame_id": "5a_wessen_bag",     "sublevel": "5a_wessen",
     "noun_en": "bag",    "noun_de": "Tasche",  "noun_jp": "かばん","noun_zh": "包",
     "desc": "Whose bag is that? — Wessen Tasche ist das? — Tasche is fem: von der Frau"},

    {"frame_id": "5a_wessen_book",    "sublevel": "5a_wessen",
     "noun_en": "book",   "noun_de": "Buch",    "noun_jp": "本",    "noun_zh": "書",
     "desc": "Whose book is this? — Wessen Buch ist das? — Buch is neut: von dem Kind"},

    {"frame_id": "5a_wessen_key",     "sublevel": "5a_wessen",
     "noun_en": "key",    "noun_de": "Schlüssel","noun_jp": "鍵",   "noun_zh": "鑰匙",
     "desc": "Whose key is this? — Wessen Schlüssel ist das? — Schlüssel is masc: von dem Mann; also name answers"},

    {"frame_id": "5a_wessen_coat",    "sublevel": "5a_wessen",
     "noun_en": "coat",   "noun_de": "Mantel",  "noun_jp": "コート","noun_zh": "外套",
     "desc": "Whose coat is that? — Wessen Mantel ist das? — Mantel is masc; vary who left the coat"},

    {"frame_id": "5a_wessen_hat",     "sublevel": "5a_wessen",
     "noun_en": "hat",    "noun_de": "Hut",     "noun_jp": "帽子",  "noun_zh": "帽子",
     "desc": "Whose hat is that? — Wessen Hut ist das? — Hut is masc; include names with -s genitive"},

    {"frame_id": "5a_wessen_cup",     "sublevel": "5a_wessen",
     "noun_en": "cup",    "noun_de": "Tasse",   "noun_jp": "カップ","noun_zh": "杯子",
     "desc": "Whose cup is this? — Wessen Tasse ist das? — Tasse is fem: von der Frau"},

    {"frame_id": "5a_wessen_bicycle", "sublevel": "5a_wessen",
     "noun_en": "bicycle","noun_de": "Fahrrad", "noun_jp": "自転車","noun_zh": "自行車",
     "desc": "Whose bicycle is that? — Wessen Fahrrad ist das? — Fahrrad is neut; mix name and NP answers"},

    {"frame_id": "5a_wessen_notebook","sublevel": "5a_wessen",
     "noun_en": "notebook","noun_de": "Heft",   "noun_jp": "ノート","noun_zh": "筆記本",
     "desc": "Whose notebook is this? — Wessen Heft ist das? — Heft is neut: von dem Kind; school setting"},

    # ── 5B wo — static location (Where is X?) ────────────────────
    # DE question word: Wo. Answer: dative (static = dative, same as Level 4A).
    # JP: どこ + に (existence: いる/ある) or で (activity verb).
    # ZH: 在哪裡 in question; 在 + place in answer.
    # Vary animate/inanimate subjects; vary verb type (be, sit, stand, wait, work, live).

    {"frame_id": "5b_wo_be",    "sublevel": "5b_wo",
     "verb_en": "be",    "verb_de": "sein",    "verb_jp": "いる/ある", "verb_zh": "在",
     "desc": "Where is X? — Wo ist X? — mix animate (いる) and inanimate (ある) subjects; JP に for existence; ZH 在+place"},

    {"frame_id": "5b_wo_sit",   "sublevel": "5b_wo",
     "verb_en": "sit",   "verb_de": "sitzen",  "verb_jp": "座っている","verb_zh": "坐",
     "desc": "Where is X sitting? — Wo sitzt X? — DE dative answer; JP: で for activity location"},

    {"frame_id": "5b_wo_stand", "sublevel": "5b_wo",
     "verb_en": "stand", "verb_de": "stehen",  "verb_jp": "立っている","verb_zh": "站",
     "desc": "Where is X standing? — Wo steht X? — vary locations across exchanges"},

    {"frame_id": "5b_wo_sleep", "sublevel": "5b_wo",
     "verb_en": "sleep", "verb_de": "schlafen","verb_jp": "寝ている",  "verb_zh": "睡",
     "desc": "Where is X sleeping? — Wo schläft X? — JP: で for activity location (ベッドで寝ている)"},

    {"frame_id": "5b_wo_wait",  "sublevel": "5b_wo",
     "verb_en": "wait",  "verb_de": "warten",  "verb_jp": "待っている","verb_zh": "等",
     "desc": "Where is X waiting? — Wo wartet X? — common locations: station, door, outside"},

    {"frame_id": "5b_wo_work",  "sublevel": "5b_wo",
     "verb_en": "work",  "verb_de": "arbeiten","verb_jp": "働いている","verb_zh": "工作",
     "desc": "Where does X work? — Wo arbeitet X? — habitual present; JP: で (activity); vary workplaces"},

    {"frame_id": "5b_wo_live",  "sublevel": "5b_wo",
     "verb_en": "live",  "verb_de": "wohnen",  "verb_jp": "住んでいる","verb_zh": "住",
     "desc": "Where does X live? — Wo wohnt X? — habitual; vary cities/places; DE: in + dative (in Berlin / in der Stadt)"},

    {"frame_id": "5b_wo_study", "sublevel": "5b_wo",
     "verb_en": "study", "verb_de": "lernen",  "verb_jp": "勉強している","verb_zh": "學習",
     "desc": "Where does X study? — Wo lernt/studiert X? — JP: で (activity, not に); ZH: 在哪裡學習"},

    # ── 5B wohin — goal / directed movement (Where to?) ──────────
    # DE question word: Wohin. Answer: accusative (goal = accusative, same as Level 4B).
    #   Exception: zu and nach always take dative even for goals.
    #   Wechselpräpositionen (in, auf, unter, etc.) take accusative for goal.
    # JP: どこ + に/へ in question; place + に/へ in answer.
    # ZH: 去哪裡 / 到哪裡 in question; 去 + place in answer.

    {"frame_id": "5b_wohin_go",    "sublevel": "5b_wohin",
     "verb_en": "go",    "verb_de": "gehen",   "verb_jp": "行く",    "verb_zh": "去",
     "desc": "Where did/does X go? — Wohin ist X gegangen? — vary: in + acc (ins Kino) and zu + dat (zum Bahnhof, zur Schule) and nach + dat (nach Berlin)"},

    {"frame_id": "5b_wohin_run",   "sublevel": "5b_wohin",
     "verb_en": "run",   "verb_de": "laufen",  "verb_jp": "走る",    "verb_zh": "跑",
     "desc": "Where did X run? — Wohin ist X gelaufen? — DE ist gelaufen (sein Perfekt); accusative for enclosed destinations"},

    {"frame_id": "5b_wohin_drive", "sublevel": "5b_wohin",
     "verb_en": "drive", "verb_de": "fahren",  "verb_jp": "行く",    "verb_zh": "開車去",
     "desc": "Where did X drive? — Wohin ist X gefahren? — DE ist gefahren; nach+city, zum+place, in+acc for enclosed"},

    {"frame_id": "5b_wohin_walk",  "sublevel": "5b_wohin",
     "verb_en": "walk",  "verb_de": "gehen",   "verb_jp": "歩く",    "verb_zh": "走",
     "desc": "Where did X walk? — Wohin ist X gegangen? — vary destinations; show in+acc vs zu+dat distinction"},

    {"frame_id": "5b_wohin_fly",   "sublevel": "5b_wohin",
     "verb_en": "fly",   "verb_de": "fliegen", "verb_jp": "飛ぶ",    "verb_zh": "飛",
     "desc": "Where did X fly? — Wohin ist X geflogen? — DE: nach + city/country (nach Tokyo, nach Japan); ist geflogen"},

    {"frame_id": "5b_wohin_carry", "sublevel": "5b_wohin",
     "verb_en": "carry", "verb_de": "tragen",  "verb_jp": "運ぶ",    "verb_zh": "搬",
     "desc": "Where did X carry it? — Wohin hat X es getragen? — caused motion: hat getragen (haben); accusative destination"},

    # ── 5B woher — source / origin (Where from?) ─────────────────
    # DE question word: Woher. Answer: aus + dative (enclosed) or von + dative (open/named).
    # JP: どこ + から in question; place + から in answer.
    # ZH: 從哪裡 in question; 從 + place in answer.

    {"frame_id": "5b_woher_come",   "sublevel": "5b_woher",
     "verb_en": "come",   "verb_de": "kommen",  "verb_jp": "来る",    "verb_zh": "來",
     "desc": "Where did X come from? — Woher ist X gekommen? — mix aus+dative (aus dem Haus) and von+dative (von der Schule); ist gekommen"},

    {"frame_id": "5b_woher_return", "sublevel": "5b_woher",
     "verb_en": "return", "verb_de": "kommen",  "verb_jp": "帰る",    "verb_zh": "回來",
     "desc": "Where did X return from? — Woher ist X zurückgekommen? — ist zurückgekommen; common sources: work, holiday, school"},

    {"frame_id": "5b_woher_run",    "sublevel": "5b_woher",
     "verb_en": "run",    "verb_de": "laufen",  "verb_jp": "走る",    "verb_zh": "跑",
     "desc": "Where did X run from? — Woher ist X gelaufen? — aus+dative for enclosed sources; von+dative for open sources"},

    {"frame_id": "5b_woher_know",   "sublevel": "5b_woher",
     "verb_en": "know",   "verb_de": "wissen",  "verb_jp": "知る",    "verb_zh": "知道",
     "desc": "Where does X know this from? — Woher weißt du das? / Woher weiß X das? — source of knowledge, not physical location; vary: from a book, from a friend, from school"},

    {"frame_id": "5b_woher_get",    "sublevel": "5b_woher",
     "verb_en": "get",    "verb_de": "haben",   "verb_jp": "もらう",  "verb_zh": "得到",
     "desc": "Where did X get it from? — Woher hat X das? — source of an object; von + person (von Tom); aus + place (aus dem Laden)"},

    {"frame_id": "5b_woher_origin", "sublevel": "5b_woher",
     "verb_en": "be from","verb_de": "kommen",  "verb_jp": "来る",    "verb_zh": "來自",
     "desc": "Where are you/is X from? — Woher kommst du? / Woher ist X? — geographic origin; DE: aus + country/city (aus Japan, aus Berlin); JP: どこから来た？/ どこの人？"},

    # ── 5C when — temporal (When?) ───────────────────────────────
    # DE question word: Wann. Answer: temporal adverbial (no case inflection on adverbs).
    # JP: いつ. ZH: 什麼時候.
    # Vary: past (Wann ist X angekommen?), present habitual (Wann schläft X?), future (Wann kommt X?).
    # Vary answers: gestern, heute Morgen, um drei Uhr, am Montag, letzte Woche, nächsten Monat.

    {"frame_id": "5c_when_arrive", "sublevel": "5c_when",
     "verb_en": "arrive","verb_de": "ankommen","verb_jp": "着く",    "verb_zh": "到",
     "desc": "When did X arrive? — Wann ist X angekommen? — DE Perfekt ist angekommen; vary times: yesterday, this morning, at noon, on Monday"},

    {"frame_id": "5c_when_leave",  "sublevel": "5c_when",
     "verb_en": "leave", "verb_de": "gehen",   "verb_jp": "出る",    "verb_zh": "離開",
     "desc": "When did X leave? — Wann ist X gegangen? — vary past/future; DE: ist gegangen; answers: yesterday / tomorrow / at 8 o'clock"},

    {"frame_id": "5c_when_come",   "sublevel": "5c_when",
     "verb_en": "come",  "verb_de": "kommen",  "verb_jp": "来る",    "verb_zh": "來",
     "desc": "When did/will X come? — Wann kommt X? — mix past and future; answers: tomorrow, next week, yesterday, in the evening"},

    {"frame_id": "5c_when_eat",    "sublevel": "5c_when",
     "verb_en": "eat",   "verb_de": "essen",   "verb_jp": "食べる",  "verb_zh": "吃",
     "desc": "When did X eat? — Wann hat X gegessen? — vary meal times and context; answers: at noon, this morning, yesterday evening"},

    {"frame_id": "5c_when_sleep",  "sublevel": "5c_when",
     "verb_en": "sleep", "verb_de": "schlafen","verb_jp": "寝る",    "verb_zh": "睡",
     "desc": "When does X sleep? — Wann schläft X? — habitual present; answers: at night, in the afternoon, at ten o'clock"},

    {"frame_id": "5c_when_work",   "sublevel": "5c_when",
     "verb_en": "work",  "verb_de": "arbeiten","verb_jp": "働く",    "verb_zh": "工作",
     "desc": "When does X work? — Wann arbeitet X? — habitual; answers: on Monday, every day, in the morning, from 8 to 5"},

    {"frame_id": "5c_when_start",  "sublevel": "5c_when",
     "verb_en": "start", "verb_de": "anfangen","verb_jp": "始める",  "verb_zh": "開始",
     "desc": "When did X start? — Wann hat X angefangen? — vary what was started; answers: last week, yesterday, at 9 o'clock"},

    {"frame_id": "5c_when_finish", "sublevel": "5c_when",
     "verb_en": "finish","verb_de": "fertig sein","verb_jp": "終わる","verb_zh": "結束",
     "desc": "When did X finish? — Wann war X fertig? / Wann hat X aufgehört? — vary answers: soon, yesterday, this afternoon"},

    # ── 5D why — reason (Why?) ────────────────────────────────────
    # DE question word: Warum. Answer types:
    #   wegen + genitive (because of X): wegen des Regens / wegen der Kälte / wegen des Kindes
    #   aus + dative (out of): aus Angst / aus Liebe / aus Müdigkeit
    #   vor + dative (from/with emotion): vor Freude / vor Müdigkeit
    #   um zu + inf (purpose): Um zu helfen. / Um rechtzeitig anzukommen.
    # JP: なぜ / どうして. Answers: 〜から / 〜ために / 〜のせいで / bare noun reason.
    # ZH: 為什麼. Answers: 因為 + reason / 為了 + purpose / bare reason clause.

    {"frame_id": "5d_why_leave",  "sublevel": "5d_why",
     "verb_en": "leave", "verb_de": "gehen",   "verb_jp": "行く",    "verb_zh": "走",
     "desc": "Why did X leave? — Warum ist X gegangen? — vary reasons: wegen des Regens / aus Angst / um zu helfen; JP: 雨のせいで / 助けるために"},

    {"frame_id": "5d_why_cry",    "sublevel": "5d_why",
     "verb_en": "cry",   "verb_de": "weinen",  "verb_jp": "泣く",    "verb_zh": "哭",
     "desc": "Why did X cry? — Warum hat X geweint? — emotional cause answers: aus Trauer / vor Freude (tears of joy); JP: 悲しいから / 嬉しくて; ZH: 因為傷心 / 因為高興"},

    {"frame_id": "5d_why_come",   "sublevel": "5d_why",
     "verb_en": "come",  "verb_de": "kommen",  "verb_jp": "来る",    "verb_zh": "來",
     "desc": "Why did X come? — Warum ist X gekommen? — purpose answers: um zu helfen / für das Kind; JP: 助けるために; ZH: 為了幫忙"},

    {"frame_id": "5d_why_late",   "sublevel": "5d_why",
     "verb_en": "be late","verb_de": "spät sein","verb_jp": "遅れる","verb_zh": "遲到",
     "desc": "Why is X late? — Warum ist X zu spät? / Warum kommt X so spät? — causes: wegen des Zuges / wegen des Staus; JP: 電車のせいで / 渋滞のせいで; ZH: 因為塞車 / 因為誤點"},

    {"frame_id": "5d_why_happy",  "sublevel": "5d_why",
     "verb_en": "be happy","verb_de": "glücklich sein","verb_jp": "嬉しい","verb_zh": "開心",
     "desc": "Why is X happy? — Warum ist X glücklich? / Warum freut sich X? — positive reasons: wegen des Briefes; JP: 手紙が来たから; ZH: 因為收到信"},

    {"frame_id": "5d_why_run",    "sublevel": "5d_why",
     "verb_en": "run",   "verb_de": "laufen",  "verb_jp": "走る",    "verb_zh": "跑",
     "desc": "Why did X run? — Warum ist X gelaufen? — purposive and causal: um den Zug zu erreichen / aus Angst; JP: 電車に乗るために / 怖かったから"},

    {"frame_id": "5d_why_tired",  "sublevel": "5d_why",
     "verb_en": "be tired","verb_de": "müde sein","verb_jp": "疲れている","verb_zh": "累",
     "desc": "Why is X tired? — Warum ist X müde? — causal: wegen der Arbeit / aus Erschöpfung; JP: 仕事のせいで; ZH: 因為工作太累 / 因為沒睡好"},

    # ── 5E how — manner and instrument (How? / With what?) ────────
    # Two German question words: Wie? (manner) and Womit? (instrument/means).
    # Instrument files (cut, write, open, carry): Womit? — answers use mit + dative / で / 用.
    # Manner files (run, speak): Wie? — answers are manner adverbials.
    # Vehicle files (travel, go): Wie? or Womit? — answers: mit+dative / で / 坐/騎.
    # JP: どうやって (how/by what method), 何で (with what/instrument — context determines).
    # ZH: 怎麼 (how), 用什麼 (with what).

    {"frame_id": "5e_how_cut",    "sublevel": "5e_how",
     "verb_en": "cut",   "verb_de": "schneiden","verb_jp": "切る",   "verb_zh": "剪/切",
     "desc": "How did X cut it? — Womit hat X es geschnitten? — instrument answers: mit der Schere / mit dem Messer; JP: はさみで / ナイフで; ZH: 用剪刀 / 用刀; vary instruments across exchanges"},

    {"frame_id": "5e_how_write",  "sublevel": "5e_how",
     "verb_en": "write", "verb_de": "schreiben","verb_jp": "書く",   "verb_zh": "寫",
     "desc": "How did X write it? — Womit hat X geschrieben? — instrument: mit dem Stift / mit dem Bleistift / mit der Hand; JP: ペンで / 鉛筆で / 手で; ZH: 用筆 / 用鉛筆 / 用手"},

    {"frame_id": "5e_how_travel", "sublevel": "5e_how",
     "verb_en": "travel","verb_de": "fahren",  "verb_jp": "行く",    "verb_zh": "去",
     "desc": "How did X get there? — Wie ist X dorthin gefahren? / Womit ist X gefahren? — vehicle answers: mit dem Zug / mit dem Fahrrad / zu Fuß; JP: 電車で / 自転車で / 歩いて; ZH: 坐火車 / 騎自行車 / 走路"},

    {"frame_id": "5e_how_carry",  "sublevel": "5e_how",
     "verb_en": "carry", "verb_de": "tragen",  "verb_jp": "運ぶ",    "verb_zh": "搬",
     "desc": "How did X carry it? — Wie hat X es getragen? — means/manner: mit den Händen / auf dem Rücken; JP: 手で / 背中に; ZH: 用手 / 用背"},

    {"frame_id": "5e_how_open",   "sublevel": "5e_how",
     "verb_en": "open",  "verb_de": "öffnen",  "verb_jp": "開ける",  "verb_zh": "開",
     "desc": "How did X open it? — Wie/Womit hat X es geöffnet? — instrument: mit dem Schlüssel / mit der Hand / mit einem Messer; JP: 鍵で / 手で / ナイフで"},

    {"frame_id": "5e_how_speak",  "sublevel": "5e_how",
     "verb_en": "speak", "verb_de": "sprechen","verb_jp": "話す",    "verb_zh": "說",
     "desc": "How did X speak? — Wie hat X gesprochen? — manner answers: laut / leise / langsam / schnell; JP: 大きな声で / ゆっくり; ZH: 大聲地 / 慢慢地; Wie? not Womit?"},

    {"frame_id": "5e_how_fix",    "sublevel": "5e_how",
     "verb_en": "fix",   "verb_de": "reparieren","verb_jp": "直す",  "verb_zh": "修",
     "desc": "How did X fix it? — Womit hat X es repariert? — instrument: mit dem Hammer / mit dem Werkzeug; JP: ハンマーで / 道具で; ZH: 用錘子 / 用工具"},

    # ── 5F yes/no — polarity questions ───────────────────────────
    # DE: verb-first questions (V1). Answers: Ja / Nein / Doch.
    #   Doch: contradicts a NEGATIVE question — uniquely German, no EN equivalent.
    #   "Hat X nicht gegessen?" → "Doch!" (= yes he did, contradicting the negation).
    # JP: plain sentence (± question particle か / の). Answers: repeat verb or うん/ううん.
    # ZH: plain + 嗎. Answers: repeat verb or 是/沒有.
    # Each file: mix affirmative and negative answers across exchanges.
    # The 5f_yn_doch file: ONLY negative questions, showing Doch vs Nein contrast.

    {"frame_id": "5f_yn_eat",     "sublevel": "5f_yn",
     "verb_en": "eat",   "verb_de": "essen",   "verb_jp": "食べる",  "verb_zh": "吃",
     "desc": "Did X eat? — Hat X gegessen? — alternate Ja/Nein answers across exchanges; JP: うん/ううん or 食べた/食べてない; ZH: 吃了/沒吃"},

    {"frame_id": "5f_yn_drink",   "sublevel": "5f_yn",
     "verb_en": "drink", "verb_de": "trinken", "verb_jp": "飲む",    "verb_zh": "喝",
     "desc": "Did X drink? — Hat X getrunken? — alternate Ja/Nein; vary the liquid across exchanges"},

    {"frame_id": "5f_yn_come",    "sublevel": "5f_yn",
     "verb_en": "come",  "verb_de": "kommen",  "verb_jp": "来る",    "verb_zh": "來",
     "desc": "Did X come? — Ist X gekommen? — DE: ist gekommen (sein Perfekt); mix yes/no answers"},

    {"frame_id": "5f_yn_know",    "sublevel": "5f_yn",
     "verb_en": "know",  "verb_de": "wissen",  "verb_jp": "知っている","verb_zh": "知道",
     "desc": "Does X know? — Weiß X das? — present tense; vary what is known; mix Ja/Nein"},

    {"frame_id": "5f_yn_like",    "sublevel": "5f_yn",
     "verb_en": "like",  "verb_de": "mögen",   "verb_jp": "好き",    "verb_zh": "喜歡",
     "desc": "Does X like X? — Mag X das? — present; vary the liked object; mix yes/no"},

    {"frame_id": "5f_yn_have",    "sublevel": "5f_yn",
     "verb_en": "have",  "verb_de": "haben",   "verb_jp": "持っている","verb_zh": "有",
     "desc": "Does X have X? — Hat X einen Stift? — present; vary the possessed object; mix Ja/Nein"},

    {"frame_id": "5f_yn_rain",    "sublevel": "5f_yn",
     "verb_en": "rain",  "verb_de": "regnen",  "verb_jp": "雨が降る", "verb_zh": "下雨",
     "desc": "Did it rain? — Hat es geregnet? / Regnet es? — impersonal verb; vary tense; JP: 雨が降った？; ZH: 下雨了嗎？"},

    {"frame_id": "5f_yn_doch",    "sublevel": "5f_yn_doch",
     "verb_en": "various","verb_de": "various", "verb_jp": "various", "verb_zh": "various",
     "desc": "DOCH contrast file — all questions are NEGATIVE; answers show Doch! (contradicting) vs Nein (confirming the negative). EN has no equivalent for Doch. JP and ZH answer with the positive verb form. Vary verbs across exchanges: essen, trinken, kommen, schlafen, lernen."},

]


# ─────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────

GLOBAL_RULES = """\
## Global rules

Naturalise, don't translate.

## Vocabulary restrictions — DO NOT USE these words

Use only words taught in the allowlist. The following words are not on the allowlist.
Use the indicated substitute instead:

  cleaver     → knife          futon       → bed           ramen       → soup
  crowbar     → tool / bar     wrench      → tool          crate       → box
  jazz        → music          cinema      → theater       university  → school
  outside     → garden/street  someone     → person/child  temple      → building
  boss        → teacher/leader colleague   → friend        director    → teacher/leader
  lawyer      → man/woman      waiter      → man/woman     capital     → city
  attract     → draw/bring     essay       → letter/story  postcard    → letter
  sheer       → real/pure
  The same meaning expressed as a native speaker would say it in each language.

Japanese plain form only. No desu/masu. No keigo.
  Past: ta form. Present/habitual: plain form.
  CRITICAL: Japanese MUST be written in Japanese script (kanji + hiragana + katakana). Never romaji.

German V2 word order. In questions: WH word is first constituent, verb is second, subject follows.
  Wer hat das Wasser getrunken?  (wer=1st, hat=2nd, das Wasser getrunken follows)
  Wen sah Klaus?                 (wen=1st, sah=2nd, Klaus=3rd)
  Wem half Tom?                  (wem=1st, half=2nd, Tom=3rd)
  Wessen Blumen sind das?        (wessen Blumen=1st, sind=2nd, das=3rd)

German Perfekt for past: hat/ist + past participle.
  Motion/state-change verbs: ist (ist gegangen, ist gelaufen, ist angekommen, ist gefallen, ist gefolgt).
  All others: hat.

Mandarin aspect: 了 for completed action where natural. Time adverbials set tense.
Pronoun drop: Japanese and Mandarin omit pronouns when the referent is clear.

Fragment answers only. The answer is the bare constituent — never a repeated full sentence.
No grammar labels, headers, or explanatory notes inside generated files."""


NAMES_TABLE = """\
## Names

Always write each name in the script of the language.
European names are phonetically transcribed in JP (katakana) and ZH (characters).
Japanese names appear in kanji in JP but are romanised in EN and DE.

| EN       | DE       | JP       | ZH     |
|----------|----------|----------|--------|
| Tom      | Tom      | トム     | 湯姆   |
| Kate     | Kate     | ケイト   | 凱特   |
| Klaus    | Klaus    | クラウス | 克勞斯 |
| Peter    | Peter    | ピーター | 彼得   |
| Corinna  | Corinna  | コリナ   | 科里娜 |
| Hans     | Hans     | ハンス   | 漢斯   |
| Susanne  | Susanne  | スザンネ | 蘇珊娜 |
| Taro     | Taro     | 太郎     | 太郎   |
| Hanako   | Hanako   | 花子     | 花子   |
| Kokoro   | Kokoro   | 心       | 心     |
| Kaori    | Kaori    | 香織     | 香織   |

Proper noun genitive in German: attach -s directly to the name, no article.
  Peters Stift. Toms Buch. Kaorис Tasche. Hanakos Blumen."""


RULES_5A_WER = """\
## 5a_wer — Who? (subject / nominative)

The questioned constituent is the SUBJECT of the sentence.
German question word: Wer

German V2 pattern:
  Wer + verb (+ object)?
  Wer hat das Wasser getrunken?
  Wer ist das? (copula identification — no Perfekt, present tense)
  Wer ist zuerst angekommen?

German answer case: NOMINATIVE.
  das Kind   (neut nom)
  die Frau   (fem nom)
  der Mann   (masc nom)
  Tom / Hanako / Klaus  (proper name — no article)

Japanese question word: 誰が (who-SUBJ, が marks subject)
  誰が水を飲んだ？
  誰が来た？

Japanese answer: retain が.
  子供が。 / 花子が。 / 女の人が。

Mandarin question word: 誰 stays in subject position.
  誰喝了那水？ / 誰來了？

Mandarin answer: bare NP (no particle).
  孩子。 / 花子。 / 那個女人。"""


RULES_5A_WEN = """\
## 5a_wen — Who/Whom? (direct object / accusative)

The questioned constituent is the DIRECT OBJECT of an accusative verb.
German question word: Wen

CRITICAL: helfen (help) is a DATIVE verb in German. Do NOT use helfen in wen-files.
Accusative verbs only: sehen, treffen, kennen, finden, rufen, besuchen, einladen,
unterrichten, lieben, warten auf.

German V2 pattern (inversion: subject comes after verb):
  Wen + verb + subject (+ rest)?
  Wen sah Klaus?
  Wen hat Tom eingeladen?
  Auf wen wartet er?  (warten auf = prepositional object; use Auf wen? not Wen?)

German answer case: ACCUSATIVE.
  die Frau   (fem acc — same form as nom)
  das Kind   (neut acc — same form as nom)
  den Mann   (masc acc — der → den)
  Tom / Hanako  (proper name — no article, no change)

Japanese question word: 誰を (who-OBJ, を marks direct object)
  クラウスは誰を見た？
  トムは誰を招待した？

Japanese answer: drop を in fragment — bare NP only.
  女の人。 / 太郎。 / 先生。

Mandarin question word: 誰 stays in object position.
  克勞斯看見誰了？ / 湯姆邀請了誰？

Mandarin answer: bare NP.
  那個女人。 / 太郎。"""


RULES_5A_WEM = """\
## 5a_wem — Who/Whom? (dative object)

The questioned constituent is in DATIVE position — either a dative-only object or an IO.
German question word: Wem

Dative-only verbs (the dative NP is the only object):
  helfen (help), danken (thank), folgen (follow), vertrauen (trust),
  glauben (believe), antworten (answer).

Double-object verbs (question targets the IO; retain the DO in the question):
  geben (give), zeigen (show), erzählen (tell), schicken (send), bringen (bring).
  Example: Wem hat Tom das Buch gegeben?  (das Buch = DO retained in question)

German V2 pattern:
  Wem + verb + subject (+ DO if double-object)?
  Wem half Tom?
  Wem hat Kate das Bild gezeigt?

German answer case: DATIVE.
  der Frau   (fem dat)
  dem Kind   (neut dat)
  dem Mann   (masc dat)
  Tom / Hanako  (proper name — no article)

IMPORTANT — Japanese particles are verb-specific (do NOT mechanically use に):
  helfen  → 助ける → 誰を助けた？ (を)
  danken  → 感謝する → 誰に感謝した？ (に)
  folgen  → 従う → 誰に従った？ (に)
  vertrauen → 信頼する → 誰を信頼している？ (を)
  glauben → 信じる → 誰を信じている？ (を)
  antworten → 答える → 誰に答えた？ (に)
  geben   → あげる/くれる → 誰に[DO]をあげた？ (に)
  zeigen  → 見せる → 誰に[DO]を見せた？ (に)
  erzählen → 話す → 誰に[story]を話した？ (に)
  schicken → 送る → 誰に[DO]を送った？ (に)
  bringen → 持ってくる → 誰に[DO]を持ってきた？ (に)

Japanese answer: bare NP (drop particle in fragment).
  女の人。 / 先生。 / 太郎。

Mandarin question word: 誰 stays in dative/IO position.
  湯姆幫助了誰？ / 凱特把那本書給了誰？

Mandarin answer: bare NP.
  那個女人。 / 孩子。"""


RULES_5A_WESSEN = """\
## 5a_wessen — Whose? (genitive / possessor)

The questioned constituent is the POSSESSOR of a noun.
German question word: Wessen + noun phrase.
  Wessen Blumen sind das?
  Wessen Stift ist das?

German answer forms — use all three types across exchanges in each file:
  1. Proper noun + -s (no article): Peters Stift. / Toms Buch. / Kaorис Tasche.
     Names ending in s/z/x: just add apostrophe: Klaus' Hut. (or: der Hut von Klaus)
  2. NP + von + DATIVE (spoken/natural default for common nouns):
     Die Blumen von der Frau.  (fem dat: der Frau)
     Der Stift von dem Mann.   (masc dat: dem Mann)
     Das Buch von dem Kind.    (neut dat: dem Kind)
  3. NP + genitive article (formal/written — include occasionally for contrast):
     Die Blumen der Frau.  (fem gen: der Frau — same form as fem dat!)
     Der Stift des Mannes. (masc gen: des Mannes)
     Das Buch des Kindes.  (neut gen: des Kindes)

Each file: mix proper-noun answers (type 1) and common-NP answers (type 2).
Include at least one type-3 (genitive article) answer per file.

Japanese question word: 誰の + noun (+ の to mark question)
  誰の花なの？ / 誰のペンなの？ / 誰のかばんなの？

Japanese answer: retain の (possessor particle).
  女の人の。 / 太郎の。 / 先生の。

Mandarin question word: 這是/那是誰的 + noun? or NP + 是誰的?
  那些花是誰的？ / 這是誰的筆？

Mandarin answer: NP + 的.
  那個女人的。 / 太郎的。 / 彼得的。"""


RULES_5B_WO = """\
## 5b_wo — Where? (static location)

The questioned constituent is a STATIC LOCATION. German question word: Wo
This is the mirror of Level 4A: static location = dative in German.

German V2 pattern:
  Wo + verb + subject (+ rest)?
  Wo ist die Katze?         (Wo=1st, ist=2nd, die Katze=3rd)
  Wo schläft er?            (Wo=1st, schläft=2nd, er=3rd)
  Wo wohnt Kate?

German answer case: DATIVE (static = dative — same rule as 4A).
  Common answer patterns:
  In der Küche. / Im Haus. (in+dem=im, neut/masc)
  Auf dem Tisch. / Auf der Matte.
  Unter dem Bett.
  Am Bahnhof. (an+dem=am)
  Bei der Schule. / Neben dem Fenster.

Japanese: どこ + に (existence verb) or で (activity verb).
  Animate existence: どこにいる？ → 台所に。
  Inanimate existence: どこにある？ → 机の上に。/ 台所に。
  Activity: どこで働いている？ → 学校で。/ どこで勉強している？ → 図書館で。
  The に/で distinction is OBLIGATORY — get it right based on the verb type.

Mandarin: 在哪裡 in question; 在 + place (+ localizer) in answer.
  在哪裡？→ 在廚房。/ 在桌子上。/ 在學校。"""


RULES_5B_WOHIN = """\
## 5b_wohin — Where to? (directed movement / goal)

The questioned constituent is a GOAL of movement. German question word: Wohin
This is the mirror of Level 4B (goal): goal = accusative for Wechselpräpositionen.

German V2 pattern:
  Wohin + verb (sein/hat Perfekt split) + subject?
  Wohin ist Klaus gegangen?   (Wohin=1st, ist=2nd, Klaus=3rd, gegangen=end)
  Wohin läuft Tom?            (present: Wohin=1st, läuft=2nd, Tom=3rd)

German answer case: depends on preposition:
  Wechselpräpositionen + ACCUSATIVE (direction):
    In den Park. (masc acc: den)
    Ins Haus. (in+das=ins, neut acc)
    In die Küche. (fem acc: die)
    Auf den Tisch.
  zu + DATIVE (always dative, even for goals):
    Zum Bahnhof. (zu+dem=zum) / Zur Schule. (zu+der=zur)
  nach + DATIVE (cities, countries, named places without article):
    Nach Berlin. / Nach Hause.

CRITICAL: vary answers across all three types within each file.
Make the accusative/dative contrast visible: ins Haus (acc) vs zum Bahnhof (dat).

Japanese: どこに/へ in question; place + に or へ in answer.
  どこに行った？ → 公園に。/ 学校へ。
  どこへ走った？ → 駅に。
  に and へ are interchangeable for most goal destinations.

Mandarin: 去哪裡了？/ 到哪裡去了？ in question; 去 + place in answer.
  去哪裡了？ → 去了公園。/ 去學校了。/ 去了家。"""


RULES_5B_WOHER = """\
## 5b_woher — Where from? (source / origin)

The questioned constituent is the SOURCE of movement or knowledge.
German question word: Woher

German V2 pattern:
  Woher + verb + subject?
  Woher ist X gekommen?      (physical source)
  Woher weißt du das?        (source of knowledge — not physical movement)
  Woher hat X das?           (source of an object)

German answer: aus + dative or von + dative.
  aus + dative — enclosed spaces, countries, cities:
    Aus dem Haus. / Aus der Schule. / Aus Japan. / Aus Berlin.
  von + dative — open spaces, people, named non-enclosed places:
    Von der Schule. (from school as institution) / Vom Bahnhof. / Von Tom.
  von zu Hause — from home (fixed idiom).
  Knowledge source: Aus einem Buch. / Von einem Freund. / Aus der Zeitung.

Japanese: どこから in question; place + から in answer.
  どこから来た？ → 学校から。/ 家から。/ 日本から。
  どこから知っている？ → 本から。/ 友達から。

Mandarin: 從哪裡來的？ / 從哪裡知道的？ in question; 從 + place in answer.
  從哪裡來的？ → 從學校來的。/ 從家裡來的。/ 從日本來的。"""


RULES_5C_WHEN = """\
## 5c_when — When? (temporal)

German question word: Wann. Answer: temporal adverbial fragment (adverbs do not inflect).

German V2 pattern:
  Wann + verb + subject?
  Wann ist X angekommen?  (Perfekt: ist angekommen)
  Wann schläft X?         (present habitual)
  Wann kommt X?           (future with present tense)

German answer — temporal adverbials (no case change on the adverb itself):
  Day: gestern / heute / morgen / vorgestern (day before yesterday)
  Time of day: heute Morgen / heute Abend / heute Nacht / am Nachmittag
  Clock time: um drei Uhr / um halb vier / um Mitternacht / um 8 Uhr morgens
  Day of week: am Montag / am Dienstag ... am Sonntag (am + day)
  Week/month/year: letzte Woche / nächste Woche / letzten Monat / nächstes Jahr
  Adverbs: bald (soon) / gleich (right away) / später (later) / neulich (recently)

Japanese: いつ in question; temporal fragment in answer.
  いつ着いた？ → 昨日。/ 今朝。/ 月曜日に。/ 三時に。/ 先週。
  Note: に marks specific time points (三時に、月曜日に) but NOT gestern/today equivalents (昨日、今日、明日 have no に).

Mandarin: 什麼時候 in question; temporal fragment in answer.
  什麼時候到的？ → 昨天。/ 今天早上。/ 星期一。/ 三點。/ 上週。
  Time structure is adverbial — no case, just position."""


RULES_5D_WHY = """\
## 5d_why — Why? (reason and purpose)

German question word: Warum (also: Weshalb — more formal, same meaning).

German V2 pattern:
  Warum + verb + subject?
  Warum ist X gegangen?
  Warum weint X?
  Warum ist X so müde?

German answer types — use ALL of these across exchanges in a file:
  wegen + GENITIVE (because of X):
    Wegen des Regens. (masc gen: des Regens)
    Wegen der Kälte.  (fem gen: der Kälte)
    Wegen des Kindes. (neut gen: des Kindes)
    Wegen des Zuges.  (masc gen: des Zuges)
  aus + DATIVE (out of / from — for emotional or internal causes):
    Aus Angst. / Aus Liebe. / Aus Müdigkeit. (abstract nouns — no article)
  vor + DATIVE (from / with — for emotional overwhelm):
    Vor Freude. / Vor Müdigkeit. (tears of joy, exhausted from something)
  um zu + INFINITIVE (purpose: in order to):
    Um zu helfen. / Um rechtzeitig anzukommen. / Um den Zug zu erreichen.

Each file: include at least one wegen-answer and one um-zu-answer.

Japanese: なぜ / どうして in question; reason/purpose in answer.
  Reason (〜から): 疲れているから。/ 病気だから。/ 雨のせいで。
  Purpose (〜ために): 助けるために。/ 電車に乗るために。
  Emotional (〜て): 嬉しくて。/ 怖くて。(so happy that / so scared that)
  Bare reason NP: 雨のせいで。/ 仕事のせいで。

Mandarin: 為什麼 in question; reason/purpose in answer.
  Reason: 因為下雨。/ 因為太累了。/ 因為塞車。
  Purpose: 為了幫忙。/ 為了趕上火車。
  Bare clause: 太累了。/ 下雨了。"""


RULES_5E_HOW = """\
## 5e_how — How? / With what? (manner and instrument)

Two German question words depending on meaning:
  Wie? — manner (how, in what way): Wie ist X gelaufen? → Schnell.
  Womit? — instrument/means (with what): Womit hat X geschnitten? → Mit der Schere.

For instrument files (cut, write, open, fix, carry): use Womit?
For manner files (run, speak): use Wie?
For vehicle/travel files: use Wie? or Womit? — show both within the file.

German answers:
  Instrument: mit + DATIVE
    Mit der Schere. (fem dat) / Mit dem Messer. (masc dat) / Mit den Händen. (pl dat)
    Mit dem Zug. / Mit dem Fahrrad. / Zu Fuß. (on foot — NOT mit dem Fuß)
  Manner: bare adverb
    Schnell. / Langsam. / Laut. / Leise. / Vorsichtig. / Mit Mühe. (with effort)

Japanese:
  Instrument/means: tool/vehicle + で
    はさみで。 / ナイフで。 / 電車で。 / 自転車で。 / 手で。
  Manner: adverb
    素早く。 / ゆっくり。 / 大きな声で。 / 静かに。
  どうやって covers both manner and instrument in questions.
  何で is more specifically "with what" (instrument).

Mandarin:
  Instrument: 用 + tool: 用剪刀。/ 用刀。/ 用手。
  Vehicle: 坐火車。/ 騎自行車。/ 走路。/ 開車。(not 用 for vehicles)
  Manner: adverb: 很快地。/ 慢慢地。/ 大聲地。/ 小心地。
  怎麼 covers both manner and instrument.
  用什麼 specifically asks about instrument."""


RULES_5F_YN = """\
## 5f_yn — Yes/No questions

German: verb-FIRST questions (V1 — no WH word, verb leads).
  Present: Schläft X?  Hat X das?  Mag X das?
  Perfekt: Hat X gegessen?  Ist X gekommen?
  Modal:   Kann X das?  Will X das?

German answers:
  Affirmative: Ja.
  Negative: Nein.
  DOCH — contradicts a NEGATIVE question (the most important German-specific feature here):
    Negative Q: "Hat X nicht gegessen?" (Didn't X eat?)
    Affirm with Doch: "Doch!" (= Yes, X did — contradicting the negation)
    Confirm with Nein: "Nein." (= No, X didn't — agreeing with the negation)
  English has no equivalent for Doch — "yes" is ambiguous when answering a negative question.

Each file: alternate affirmative and negative answers across exchanges.

Japanese: plain sentence (± か / の at end).
  Hat X gegessen? → Xは食べた？ / Xは食べたの？
  Ja. → うん。 / 食べた。
  Nein. → ううん。 / 食べてない。
  Verb-repeat answers are more natural than bare うん/ううん in casual speech.

Mandarin: plain + 嗎？
  Hat X gegessen? → Xは食べた嗎？ → X吃了嗎？
  Ja. → 吃了。 / 是的。
  Nein. → 沒吃。 / 沒有。
  Mandarin prefers verb-repeat answers over bare 是/不是."""


RULES_5F_YN_DOCH = """\
## 5f_yn_doch — Doch contrast (NEGATIVE questions only)

This file contains ONLY negative questions. Every exchange shows:
  - A German negative question (with nicht)
  - Two possible answers: Doch! (contradicts the negation) vs Nein. (confirms the negation)

Format: alternate Doch and Nein answers across exchanges.

German negative question pattern: verb + subject + nicht?
  Hat X nicht gegessen?    (Didn't X eat?)
  Ist X nicht gekommen?    (Didn't X come?)
  Schläft X nicht?         (Isn't X sleeping?)

English gloss: "Yes, X did." (Doch) vs "No, X didn't." (Nein).
CRITICAL: "Yes" in English is ambiguous when answering "Didn't X eat?" — it could mean
"Yes, you're right, X didn't eat" or "Yes, X did eat." Doch is unambiguous.

Japanese negative question: 〜なかった？ / 〜ていない？
  Xは食べなかった？ / Xは来なかった？
  Doch (affirm): うん、食べた。 / 来たよ。
  Nein (confirm neg): ううん、食べなかった。 / 来なかった。

Mandarin negative question: 沒有 + verb + 嗎？ / 不 + verb + 嗎？
  X沒吃嗎？ / X沒來嗎？
  Doch (affirm): 吃了。 / 來了。
  Nein (confirm neg): 對，沒吃。 / 對，沒來。

Use 5 different verbs across the 5 exchanges: essen, trinken, kommen, schlafen, lernen."""


SUBLEVEL_RULES: dict[str, str] = {
    "5a_wer":      RULES_5A_WER,
    "5a_wen":      RULES_5A_WEN,
    "5a_wem":      RULES_5A_WEM,
    "5a_wessen":   RULES_5A_WESSEN,
    "5b_wo":       RULES_5B_WO,
    "5b_wohin":    RULES_5B_WOHIN,
    "5b_woher":    RULES_5B_WOHER,
    "5c_when":     RULES_5C_WHEN,
    "5d_why":      RULES_5D_WHY,
    "5e_how":      RULES_5E_HOW,
    "5f_yn":       RULES_5F_YN,
    "5f_yn_doch":  RULES_5F_YN_DOCH,
}


GEN_PROMPT_TPL = """\
Generate Level-5 multilingual Q&A corpus files.
Each file contains question-and-answer exchanges.
The question is in all four languages; the answer is a natural fragment in all four languages.

{global_rules}

{names_table}

{sublevel_rules}

## Output format

Each file: 3–5 exchanges.
Each exchange has:
  q — list of exactly 4 strings: [EN question, DE question, JP question, ZH question]
  a — list of exactly 4 strings: [EN answer, DE answer, JP answer, ZH answer]

Vary subjects, tenses, and supporting NPs across exchanges within each file.
Use names from the table — show them in the correct script for each language.

Return JSON only — no commentary, no markdown fences:
{{"files": [{{"frame_id": "...", "exchanges": [{{"q": ["EN","DE","JP","ZH"], "a": ["EN","DE","JP","ZH"]}}]}}]}}

## Frames to generate

{frames}"""


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    with _lock:
        print(msg, flush=True)


def load_api_key() -> str:
    for var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        if key := os.environ.get(var):
            return key
    return ""


def pending_jobs() -> list[dict]:
    seen: set[str] = set()
    result = []
    for job in JOBS:
        fid = job["frame_id"]
        if fid in seen:
            continue
        seen.add(fid)
        if not (OUT_DIR / f"{fid}.md").exists():
            result.append(job)
    return result


def group_by_sublevel(jobs: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for job in jobs:
        sl = job["sublevel"]
        groups.setdefault(sl, []).append(job)
    return groups


# ─────────────────────────────────────────────────────────────────
# Gen
# ─────────────────────────────────────────────────────────────────

def _parse_response(raw: str) -> dict | None:
    if raw.startswith("```"):
        raw = re.sub(r"^```[^\n]*\n", "", raw)
        raw = re.sub(r"\n?```$", "", raw.strip())
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return None


def frame_text(job: dict) -> str:
    lines = [f"frame_id: {job['frame_id']}", f"sublevel: {job['sublevel']}", f"desc: {job['desc']}"]
    for key in ("verb_en", "verb_de", "verb_jp", "verb_zh",
                "noun_en", "noun_de", "noun_jp", "noun_zh"):
        if key in job:
            lines.append(f"{key}: {job[key]}")
    return "\n".join(lines)


def exchanges_to_file(exchanges: list[dict]) -> str:
    parts = []
    for ex in exchanges:
        q_block = "\n".join(ex["q"])
        a_block = "\n".join(ex["a"])
        parts.append(f"{q_block}\n\n{a_block}")
    return "\n\n".join(parts) + "\n"


def gen_batch(
    jobs: list[dict],
    sublevel: str,
    client: OpenAI,
    dry_run: bool,
) -> tuple[list[str], list[str]]:
    if dry_run:
        log(f"  [DRY-RUN] gen: {[j['frame_id'] for j in jobs]}")
        return [j["frame_id"] for j in jobs], []

    frames_text = "\n\n".join(frame_text(j) for j in jobs)
    rules = SUBLEVEL_RULES.get(sublevel, "")

    prompt = GEN_PROMPT_TPL.format(
        global_rules=GLOBAL_RULES,
        names_table=NAMES_TABLE,
        sublevel_rules=rules,
        frames=frames_text,
    )

    for attempt in (1, 2):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=32768,
            )
        except Exception as e:
            log(f"  GEN API ERROR (attempt {attempt}) {jobs[0]['frame_id']}…: {e}")
            if attempt == 2:
                return [], [j["frame_id"] for j in jobs]
            continue

        raw = (resp.choices[0].message.content or "").strip()
        tokens_in  = resp.usage.prompt_tokens     if resp.usage else "?"
        tokens_out = resp.usage.completion_tokens if resp.usage else "?"

        data = _parse_response(raw)
        if data is None:
            log(f"  PARSE FAIL (attempt {attempt}) {jobs[0]['frame_id']}… raw:\n{raw[:200]}")
            if attempt == 2:
                return [], [j["frame_id"] for j in jobs]
            continue

        written, failed = [], []

        for file_data in data.get("files", []):
            fid       = file_data.get("frame_id", "").strip()
            exchanges = file_data.get("exchanges", [])

            if not fid:
                continue

            if not (3 <= len(exchanges) <= 5):
                log(f"  SKIP {fid}: expected 3–5 exchanges, got {len(exchanges)}")
                failed.append(fid)
                continue

            bad = False
            for ex in exchanges:
                q = ex.get("q", [])
                a = ex.get("a", [])
                if (len(q) != 4 or len(a) != 4
                        or not all(isinstance(s, str) and s.strip() for s in q)
                        or not all(isinstance(s, str) and s.strip() for s in a)):
                    log(f"  SKIP {fid}: malformed exchange")
                    bad = True
                    break
            if bad:
                failed.append(fid)
                continue

            content = exchanges_to_file(exchanges)
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            (OUT_DIR / f"{fid}.md").write_text(content, encoding="utf-8")
            log(f"  OK {fid} ({tokens_in}→{tokens_out})")
            written.append(fid)

        returned = {f.get("frame_id", "") for f in data.get("files", [])}
        for job in jobs:
            fid = job["frame_id"]
            if fid not in returned and fid not in written and fid not in failed:
                log(f"  MISSING from response: {fid}")
                failed.append(fid)

        return written, failed

    return [], [j["frame_id"] for j in jobs]


def run_gen(args: argparse.Namespace, client: OpenAI) -> None:
    pending = pending_jobs()

    if args.limit:
        pending = pending[: args.limit]

    total = len(pending)
    if total == 0:
        print("Nothing to generate — all frames already exist.")
        return

    print(f"Pending: {total} frames")

    by_sublevel = group_by_sublevel(pending)
    batches: list[tuple[list[dict], str]] = []
    for sublevel, jobs in by_sublevel.items():
        for i in range(0, len(jobs), args.batch):
            batches.append((jobs[i : i + args.batch], sublevel))

    print(f"Batches: {len(batches)}  (batch size: {args.batch})")

    all_failed: list[str] = []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(gen_batch, b, sl, client, args.dry_run): (b, sl) for b, sl in batches}
        for fut in as_completed(futs):
            _, failed = fut.result()
            all_failed.extend(failed)

    done = total - len(all_failed)
    print(f"\nDone: {done}/{total} written. Failed: {len(all_failed)}")
    if all_failed:
        print("Failed:", sorted(all_failed)[:20])


# ─────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────

def run_report() -> None:
    total = len(JOBS)
    done  = sum(1 for j in JOBS if (OUT_DIR / f"{j['frame_id']}.md").exists())

    print(f"Total frames: {total}")
    print(f"Generated:    {done}")
    print(f"Remaining:    {total - done}")

    by_sl: dict[str, list[int]] = {}
    for job in JOBS:
        sl = job["sublevel"]
        if sl not in by_sl:
            by_sl[sl] = [0, 0]
        by_sl[sl][1] += 1
        if (OUT_DIR / f"{job['frame_id']}.md").exists():
            by_sl[sl][0] += 1

    print()
    print("By sub-level:")
    for sl, (d, n) in sorted(by_sl.items()):
        bar = "#" * d + "." * (n - d)
        print(f"  {sl:<20} {d:>3}/{n:<3}  {bar}")


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Lang-5 corpus generator")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_gen = sub.add_parser("gen", help="Generate files for all pending frames")
    p_gen.add_argument("--workers", type=int, default=4)
    p_gen.add_argument("--batch",   type=int, default=5,
                       help="Frames per API call (default 5)")
    p_gen.add_argument("--limit",   type=int, default=0,
                       help="Max frames to generate this run (0=all pending)")
    p_gen.add_argument("--dry-run", action="store_true")

    sub.add_parser("report", help="Show progress summary")

    args = parser.parse_args()

    if args.cmd == "report":
        run_report()
        return

    api_key = load_api_key()
    if not api_key:
        print("ERROR: set OPENROUTER_API_KEY or OPENAI_API_KEY", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=BASE_URL)
    run_gen(args, client)


if __name__ == "__main__":
    main()

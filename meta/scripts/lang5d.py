#!/usr/bin/env python3
"""
Lang-5d corpus generation — mini parallel stories integrating Level-5 Q&A constructions.

Two story types:
  narrative — pure 7-10 sentence parallel narrative establishing vocabulary in context
  qa        — 5-8 sentence narrative with one embedded Q+A exchange (Level-5 question types)

Usage:
  python3 meta/scripts/lang5d.py gen    [--workers 4] [--limit N] [--dry-run]
  python3 meta/scripts/lang5d.py report

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
LANG_DIR  = REPO_ROOT / "training_data" / "lang"
OUT_DIR   = LANG_DIR / "lang_5d"
BASE_URL  = "https://openrouter.ai/api/v1"
MODEL     = "deepseek/deepseek-v4-flash"

_lock = threading.Lock()


def log(msg: str) -> None:
    with _lock:
        print(msg, flush=True)


def load_api_key() -> str:
    for var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        if key := os.environ.get(var):
            return key
    return ""


# ─────────────────────────────────────────────────────────────────
# Job matrix
# ─────────────────────────────────────────────────────────────────

def _n(num, setting, actors, new_words, desc):
    return {"num": num, "story_type": "narrative",
            "setting": setting, "actors": actors, "new_words": new_words, "desc": desc}

def _q(num, q_type, setting, actors, new_words, desc):
    return {"num": num, "story_type": "qa", "q_type": q_type,
            "setting": setting, "actors": actors, "new_words": new_words, "desc": desc}

JOBS: list[dict] = [

    # ── Narrative stories — new words in context ──────────────────

    _n( 1, "restaurant",  ["Tom", "a waiter"],
        ["waiter"],
        "a waiter brings soup and bread to Tom at a table; Tom eats and pays"),

    _n( 2, "office",      ["Kate", "a boss", "a colleague"],
        ["boss", "colleague"],
        "a boss arrives, hands a task to a colleague, and leaves; the colleague works at the desk"),

    _n( 3, "office",      ["Klaus", "a director"],
        ["director"],
        "a director opens a meeting, gives instructions, and signs a paper"),

    _n( 4, "street",      ["Peter", "a lawyer"],
        ["lawyer"],
        "a lawyer walks to a building, opens a bag, takes out papers, and enters"),

    _n( 5, "garden",      ["Hanako", "a child"],
        ["outside"],
        "a child goes outside into the garden; runs across the grass; picks a flower"),

    _n( 6, "temple",      ["Taro", "a woman"],
        ["temple"],
        "two visitors walk through the gate of a temple; look at the stones and the garden; sit and rest"),

    _n( 7, "university",  ["Corinna"],
        ["university"],
        "a student crosses the university yard, enters the library, and finds a book on the shelf"),

    _n( 8, "restaurant",  ["Hans", "Susanne", "a waiter"],
        ["waiter"],
        "a waiter takes the order from Hans and Susanne, brings food and water, and collects the plates"),

    _n( 9, "office",      ["Susanne", "a boss"],
        ["boss"],
        "a boss arrives early, puts papers on the desk, calls a colleague, and starts work"),

    _n(10, "university",  ["Kaori", "a colleague"],
        ["university", "colleague"],
        "two colleagues meet at the university; they carry books to a table and read together"),

    # ── QA stories — new words appear as question subject/object/answer ──

    _q(11, "wer",   "office",    ["Tom", "a director"],      ["director"],
       "Tom arrives at the office; who gave the instructions this morning? the director"),

    _q(12, "wo",    "building",  ["Hanako", "a director"],   ["director"],
       "Hanako looks for someone; where is the director's office? on the second floor"),

    _q(13, "wer",   "office",    ["Klaus", "a lawyer"],      ["lawyer"],
       "Klaus waits in the hall; who just walked in carrying the bag? the lawyer"),

    _q(14, "wann",  "office",    ["Peter", "a lawyer"],      ["lawyer"],
       "Peter and a colleague wait; when does the lawyer arrive? in the morning"),

    _q(15, "wohin", "house",     ["Kate", "a child"],        ["outside"],
       "Kate calls for the child but gets no answer; where did the child go? outside"),

    _q(16, "warum", "garden",    ["Tom", "a child"],         ["outside"],
       "Tom finds the child in the garden; why did the child go outside? because of the sun"),

    _q(17, "wer",   "temple",    ["Taro", "a man"],          ["temple"],
       "Taro arrives at the temple gate; who is already sitting at the temple? an old man"),

    _q(18, "wann",  "temple",    ["Hanako", "a woman"],      ["temple"],
       "Hanako and a woman make a plan; when do they visit the temple? in the morning"),

    _q(19, "wo",    "office",    ["Kate", "a boss"],         ["boss"],
       "Kate arrives; where is the boss? at the desk in the big room"),

    _q(20, "yn",    "office",    ["Klaus", "a boss"],        ["boss"],
       "Klaus knocks on the door; is the boss in? yes, the boss is at the desk"),

    _q(21, "wer",   "restaurant",["Tom", "a waiter"],        ["waiter"],
       "Tom sits at a table; who brings the cup of water? the waiter"),

    _q(22, "wann",  "restaurant",["Susanne", "a waiter"],    ["waiter"],
       "Susanne waits at the table; when does the waiter come back with the food?"),

    _q(23, "wen",   "office",    ["Tom", "a colleague"],     ["colleague"],
       "Tom enters the office; whom does Tom see at the desk? his colleague"),

    _q(24, "wem",   "office",    ["Kate", "a boss", "a colleague"], ["colleague"],
       "the boss hands something out; to whom does the boss give the task? to Kate's colleague"),

    # ── QA general — wer ─────────────────────────────────────────

    _q(25, "wer",  "kitchen",   ["Kate", "a child"],     [],
       "someone ate the last piece of bread; the child"),

    _q(26, "wer",  "garden",    ["Tom", "a man"],        [],
       "a key was lying in the grass; who found it? the man"),

    _q(27, "wer",  "school",    ["a teacher", "a student"], [],
       "the teacher asks who can read the next paragraph; a student raises a hand"),

    _q(28, "wer",  "park",      ["Klaus", "Peter"],      [],
       "Klaus and Peter race to the bench; who gets there first?"),

    _q(29, "wer",  "library",   ["Corinna", "a student"],[],
       "the window was closed all morning; who opened it? Corinna"),

    # ── QA general — wen ─────────────────────────────────────────

    _q(30, "wen",  "park",      ["Tom", "Kate"],         [],
       "Tom is walking in the park; whom does he see near the tree? Kate"),

    _q(31, "wen",  "shop",      ["Hans", "a woman"],     [],
       "Hans cannot find the bread; whom does he ask for help? the woman at the counter"),

    _q(32, "wen",  "library",   ["Corinna", "a student"],[], "Corinna has extra time; whom does she help? a student with a heavy bag"),

    _q(33, "wen",  "school",    ["a teacher", "Klaus"],  [],
       "the teacher calls one student to the board; whom does the teacher call? Klaus"),

    _q(34, "wen",  "kitchen",   ["Kate", "a child"],     [],
       "Kate bakes a cake; whom does she invite to sit and eat? the child"),

    # ── QA general — wem ─────────────────────────────────────────

    _q(35, "wem",  "kitchen",   ["Kate", "Tom", "a child"], [],
       "Kate has one apple left; to whom does she give it? to the child"),

    _q(36, "wem",  "school",    ["a teacher", "Tom"],    [],
       "the teacher holds out the book; to whom does the teacher give it? to Tom"),

    _q(37, "wem",  "restaurant",["Susanne", "a man"],    [],
       "Susanne carries a bowl of soup; to whom does she bring it? to the man at the corner table"),

    _q(38, "wem",  "garden",    ["Tom", "a child"],      [],
       "Tom picks a flower; to whom does he give it? to the child"),

    # ── QA general — wessen ──────────────────────────────────────

    _q(39, "wessen","classroom", ["a teacher", "a student"],[],
       "a pen is on the desk; whose pen is it? the student's pen"),

    _q(40, "wessen","kitchen",   ["Kate", "Tom"],         [],
       "there are two cups on the table; whose cup is the red one? Kate's"),

    _q(41, "wessen","park",      ["a child", "a woman"],  [],
       "a bag is left on the bench; whose bag is it? the woman's bag"),

    _q(42, "wessen","garden",    ["Klaus", "Peter"],      [],
       "a flower was picked from the garden; whose flower was it? Peter's flower"),

    # ── QA general — wo ──────────────────────────────────────────

    _q(43, "wo",   "library",   ["Corinna", "a student"], [],
       "a student cannot find the notebook; where is it? on the shelf by the window"),

    _q(44, "wo",   "classroom", ["a teacher", "a student"],[],
       "the teacher asks for the pen; where is the pen? on the desk"),

    _q(45, "wo",   "kitchen",   ["Kate", "a child"],     [],
       "the child wants bread; where is the bread? in the box on the shelf"),

    _q(46, "wo",   "garden",    ["Tom", "a man"],        [],
       "the cat has disappeared; where is the cat? under the table by the wall"),

    _q(47, "wo",   "park",      ["Hans", "a child"],     [],
       "Hans and the child look for a place to sit; where is the bench? near the tree"),

    # ── QA general — wohin ───────────────────────────────────────

    _q(48, "wohin","street",    ["Tom", "Kate"],         [],
       "Tom sees Kate with a bag; where is Kate going? to the shop"),

    _q(49, "wohin","school",    ["a student", "a teacher"],[],
       "a student runs out of the classroom; where did the student go? into the hall"),

    _q(50, "wohin","garden",    ["a child", "a man"],    [],
       "the cat disappears from the chair; where did it go? into the garden"),

    _q(51, "wohin","kitchen",   ["Kate", "Tom"],         [],
       "Kate carried the bottle somewhere; where did she put it? on the shelf"),

    # ── QA general — woher ───────────────────────────────────────

    _q(52, "woher","kitchen",   ["Kate", "Tom"],         [],
       "Tom walks in carrying a bag; where did Tom come from? from the shop"),

    _q(53, "woher","park",      ["a child", "a woman"],  [],
       "a woman arrives out of breath; where did she come from? from the school"),

    _q(54, "woher","classroom", ["a teacher", "a student"],[],
       "the teacher carries a new book into class; where did the book come from? from the library"),

    _q(55, "woher","garden",    ["Taro", "a man"],       [],
       "Taro appears with wet shoes; where did Taro come from? from the river"),

    # ── QA general — wann ────────────────────────────────────────

    _q(56, "wann", "station",   ["Tom", "Kate"],         [],
       "Tom and Kate wait at the station; when does the next train arrive? soon"),

    _q(57, "wann", "school",    ["a teacher", "a student"],[],
       "the student is early; when does the lesson start? at nine"),

    _q(58, "wann", "kitchen",   ["Hanako", "a child"],   [],
       "the child is hungry; when is the meal ready? in the evening"),

    _q(59, "wann", "garden",    ["Klaus", "Peter"],      [],
       "Klaus waits by the gate; when did Peter arrive? this morning"),

    # ── QA general — warum ───────────────────────────────────────

    _q(60, "warum","garden",    ["Klaus", "Peter"],      [],
       "Peter ran all the way to the garden; why? because of the rain"),

    _q(61, "warum","school",    ["a teacher", "a student"],[],
       "the student leaves before the lesson ends; why? to help someone at the door"),

    _q(62, "warum","kitchen",   ["Kate", "a child"],     [],
       "Kate makes a big pot of soup; why? because the child is hungry and tired"),

    # ── QA general — wie ─────────────────────────────────────────

    _q(63, "wie",  "park",      ["Tom", "a child"],      [],
       "Tom carries a heavy bag across the park; how? with both hands"),

    _q(64, "wie",  "kitchen",   ["Kate", "Tom"],         [],
       "Tom asks how Kate cut the apple so fast; with the big knife"),

    _q(65, "wie",  "school",    ["a teacher", "a student"],[],
       "the teacher asks how the student came to school; by bicycle"),

    _q(66, "wie",  "garden",    ["Kaori", "a child"],    [],
       "the flowers look very healthy; how did Kaori water them? with a small pot"),

    _q(67, "wie",  "street",    ["Tom", "Kate"],         [],
       "Tom asks Kate how she got to the station so quickly; she ran"),

    # ── QA general — yn ──────────────────────────────────────────

    _q(68, "yn",   "garden",    ["Hans", "a child"],     [],
       "Hans looks for the child; is the child in the garden? yes"),

    _q(69, "yn",   "kitchen",   ["Susanne", "Tom"],      [],
       "Susanne left bread on the table; did Tom eat it? yes he did"),

    _q(70, "yn",   "library",   ["Corinna", "a student"],[],
       "the student needed a book; did Corinna find it? yes she did"),

    # ── QA general — yn_doch ─────────────────────────────────────

    _q(71, "yn_doch","school",  ["a teacher", "a student"],[],
       "the teacher doubts the student studied; the student did in fact study — doch"),

    _q(72, "yn_doch","kitchen", ["Kate", "a child"],     [],
       "the child says Kate did not make the soup; but she did — doch"),

    _q(73, "yn_doch","park",    ["Tom", "Klaus"],        [],
       "Klaus thinks Tom forgot the book; Tom did bring it — doch"),

    # ── Vocabulary context stories — narrative + QA pairs ─────────
    # Covers words found in lang_4d/lang_5d that are missing from allowlist.
    # Each word appears in one narrative + one QA story.

    # neighbour
    _n(74, "street",     ["Tom", "a neighbour"],
       ["neighbour"],
       "a neighbour knocks on Tom's door; they talk at the doorstep; "
       "the neighbour brings eggs from the garden and leaves with a wave"),

    _q(88, "wer",  "street",    ["Tom", "a neighbour"],    ["neighbour"],
       "Tom hears a knock at the door; who is standing outside? his neighbour"),

    # restaurant
    _n(75, "restaurant", ["Kate", "Tom", "a waiter"],
       ["restaurant"],
       "Kate and Tom go to a restaurant; they find a table by the window; "
       "a waiter brings menus; they order soup and bread; they pay and leave"),

    _q(89, "wo",   "city",      ["Kate", "Tom"],           ["restaurant"],
       "Kate and Tom are hungry after a long walk; where do they go to eat? to the restaurant"),

    # inside
    _n(76, "garden",     ["a child", "Kate"],
       ["inside"],
       "a child plays in the garden; rain begins to fall; "
       "Kate calls from the door; the child runs inside; "
       "inside the house it is warm and dry; the child takes off wet shoes"),

    _q(90, "wohin","house",     ["Kate", "a child"],       ["inside"],
       "the rain starts; Kate looks for the child; where did the child go? inside"),

    # blackboard + schoolyard + begin
    _n(77, "school",     ["a teacher", "students"],
       ["blackboard", "schoolyard", "begin"],
       "students play in the schoolyard; the bell rings; "
       "the teacher calls them in; the lesson is about to begin; "
       "the teacher writes the date on the blackboard; "
       "students open their books; the lesson begins"),

    _q(91, "wann", "school",    ["a teacher", "a student"],["blackboard", "begin"],
       "students wait outside; when does the lesson begin? "
       "when the teacher writes on the blackboard"),

    # toolbox + wrench + peg + crate
    _n(78, "workshop",   ["Tom", "a man"],
       ["toolbox", "wrench", "peg", "crate"],
       "Tom opens a wooden crate in the workshop; "
       "inside is a toolbox; he takes out a wrench and a peg; "
       "the man uses the wrench to tighten a bolt; "
       "he hammers the peg into the wall; the shelf is now fixed"),

    _q(92, "wie",  "workshop",  ["Tom", "a man"],          ["wrench", "toolbox"],
       "the pipe was loose; how did the man fix it? "
       "he took a wrench from the toolbox and tightened the joint"),

    # mailbox
    _n(79, "street",     ["Hanako"],
       ["mailbox"],
       "Hanako walks down the street to the mailbox; "
       "she opens the mailbox and finds a letter inside; "
       "she carries the letter home; "
       "she sits at the table and reads the letter slowly"),

    _q(93, "wo",   "street",    ["Hanako", "a woman"],     ["mailbox"],
       "Hanako is looking for the letter from her friend; "
       "where is the letter? in the mailbox at the end of the street"),

    # easel
    _n(80, "park",       ["Corinna", "a woman"],
       ["easel"],
       "a woman carries an easel to the park; "
       "she sets up the easel under a tree; "
       "she puts a canvas on the easel; "
       "she paints the trees and the river; "
       "Corinna stops to watch; the woman smiles"),

    _q(94, "wo",   "park",      ["Corinna", "a woman"],    ["easel"],
       "the woman has her canvas and paints; "
       "where does she put the canvas to paint? on the easel"),

    # riverbank
    _n(81, "river",      ["Taro", "a child"],
       ["riverbank"],
       "Taro and a child walk along the river path; "
       "they sit down on the riverbank; "
       "they throw stones into the water; "
       "the child watches the stones sink; "
       "they rest on the riverbank until the sun goes down"),

    _q(95, "wo",   "river",     ["Taro", "a child"],       ["riverbank"],
       "Taro and the child walk for a long time; "
       "where do they finally sit down to rest? on the riverbank"),

    # nightstand + tired
    _n(82, "bedroom",    ["Tom"],
       ["nightstand", "tired"],
       "Tom comes home from work; he is tired; "
       "he puts his bag and his book on the nightstand; "
       "he lies down on the bed; "
       "the lamp on the nightstand is still on; "
       "he turns it off and falls asleep"),

    _q(96, "wo",   "bedroom",   ["Kate", "Tom"],            ["nightstand"],
       "Kate is looking for Tom's book; "
       "where is it? on the nightstand beside the lamp"),

    # janitor + crate
    _n(83, "school",     ["a janitor", "a teacher"],
       ["janitor", "crate"],
       "the janitor sweeps the school hall; "
       "a large crate sits by the wall; "
       "the teacher asks the janitor to move the crate; "
       "the janitor carries it to the storage room; "
       "students walk past and say thank you"),

    _q(97, "wer",  "school",    ["a janitor", "students"], ["janitor"],
       "the hall was dirty after the rain; "
       "who cleaned the floor and moved the crate? the janitor"),

    # employee + document
    _n(84, "office",     ["Klaus", "a boss", "employees"],
       ["employee", "document"],
       "Klaus walks into the office building; "
       "employees sit at their desks; "
       "Klaus carries a document to the boss; "
       "the boss reads the document carefully; "
       "one employee brings coffee to the table; "
       "the boss signs the document and hands it back"),

    _q(98, "wen",  "office",    ["a boss", "an employee"], ["employee", "document"],
       "the boss has an important document to deliver; "
       "whom does the boss call over? an employee"),

    # cash + discuss
    _n(85, "market",     ["Hans", "a woman"],
       ["cash", "discuss"],
       "Hans goes to the market; "
       "he picks up bread and apples; "
       "he and the woman discuss the price of the apples; "
       "Hans counts his cash; "
       "he pays with cash and the woman gives change"),

    _q(99, "wie",  "market",    ["Hans", "a woman"],       ["cash"],
       "Hans buys bread at the market; "
       "how does he pay? with cash"),

    # slobber
    _n(86, "park",       ["a child", "a dog"],
       ["slobber"],
       "a dog runs across the park to the child; "
       "the dog is happy and wags its tail; "
       "the dog jumps up and slobbers on the child's hand; "
       "the child laughs and wipes the hand on the grass; "
       "the dog sits and waits for the child to throw the ball"),

    _q(100, "wie", "park",      ["a child", "a dog"],      ["slobber"],
       "the dog is very excited to see the child; "
       "how does the dog greet the child? it jumps up and slobbers on the child's hand"),

    # chat + tired + history + discuss
    _n(87, "cafe",       ["Kate", "Corinna"],
       ["chat", "tired", "history", "discuss"],
       "Kate and Corinna meet at a café after school; "
       "they are tired from the long history lesson; "
       "they sit down and chat about the day; "
       "they discuss what they learned in history class; "
       "Corinna orders tea; Kate drinks water; "
       "they chat until the café closes"),

    _q(101, "warum", "cafe",    ["Kate", "Corinna"],       ["chat", "history"],
       "Kate and Corinna stay late at the café; "
       "why do they stay so long? to chat and discuss their history lesson"),
]


# ─────────────────────────────────────────────────────────────────
# Question-type rules
# ─────────────────────────────────────────────────────────────────

Q_TYPE_RULES: dict[str, str] = {

    "wer": """\
WER — "who" as subject (nominative)
EN: "Who ate the apple?"  →  "The child."  /  "Tom."  /  "The teacher."
DE: "Wer hat den Apfel gegessen?" — wer is nominative; verb 2nd; answer in nominative:
    "Das Kind."  "Tom."  "Die Frau."  "Der Mann."
JP: 誰が + verb — "誰がりんごを食べた？" / Answer (drop が): "子供。" "トム。"
ZH: 誰 as subject — "誰吃了蘋果？" / Answer: "那個孩子。" "湯姆。" """,

    "wen": """\
WEN — "whom" as direct object (accusative)
EN: "Whom did Tom see?"  →  "Kate."  /  "The man."  /  "The child."
DE: "Wen hat Tom gesehen?" — answer in accusative:
    "Kate." (names unchanged)  "Den Mann."  "Die Frau."  "Das Kind."
JP: 誰を + verb — "トムは誰を見た？" / Answer (drop を): "ケイト。" "その男の人。"
ZH: 誰 as object — "湯姆看見了誰？" / Answer: "凱特。" "那個男人。" """,

    "wem": """\
WEM — "to whom" / indirect object (dative)
EN: "Who did Kate give the apple to?"  →  "Tom."  /  "The child."
DE: "Wem hat Kate den Apfel gegeben?" — answer in dative:
    "Tom." (names unchanged)  "Dem Kind."  "Der Frau."  "Dem Mann."
JP: 誰に + verb — "ケイトは誰にりんごをあげた？" / Answer (keep に): "トムに。" "子供に。"
ZH: 誰 as recipient — "凱特把蘋果給了誰？" / Answer: "湯姆。" "那個孩子。" """,

    "wessen": """\
WESSEN — "whose" (genitive possession)
EN: "Whose book is on the desk?"  →  "Tom's."  /  "Kate's book."  /  "The teacher's."
DE: "Wessen Buch liegt auf dem Tisch?" — answer:
    "Toms Buch."  "Das Buch des Lehrers."  "Das Buch der Frau."  "Peters."
JP: 誰の + noun — "誰の本が机の上にある？" / Answer: "トムのだ。" "先生の本だ。"
ZH: 誰的 + noun — "誰的書在桌子上？" / Answer: "湯姆的。" "老師的書。" """,

    "wo": """\
WO — "where" (static location; German answer uses DATIVE)
EN: "Where is the cat?"  →  "On the table."  /  "In the kitchen."  /  "Under the chair."
DE: "Wo ist die Katze?" — answer uses dative:
    "Auf dem Tisch."  "In der Küche."  "Unter dem Stuhl."
    Contractions: im (in+dem), am (an+dem).
JP: どこに/で + verb — "猫はどこにいる？" / Answer: "テーブルの上に。" "台所に。"
ZH: 在哪裡 — "貓在哪裡？" / Answer: "在桌子上。" "在廚房裡。" """,

    "wohin": """\
WOHIN — "where to" (goal of movement; German answer uses ACCUSATIVE)
EN: "Where is Kate going?"  →  "To the garden."  /  "To school."  /  "Into the house."
DE: "Wohin geht Kate?" — answer uses accusative:
    "In den Garten."  "Zur Schule."  "Ins Haus."
    Contractions: ins (in+das), ans (an+das), zum/zur (zu+dem/der).
JP: どこへ/どこに + motion verb — "ケイトはどこへ行く？" / Answer: "庭へ。" "学校に。"
ZH: 去哪裡 — "凱特去哪裡？" / Answer: "去花園。" "去學校。" """,

    "woher": """\
WOHER — "where from" (source of movement; German answer uses DATIVE)
EN: "Where did Tom come from?"  →  "From the garden."  /  "From school."
DE: "Woher kommt Tom?" — answer:
    aus + enclosed space (dative): "Aus dem Haus."  "Aus der Küche."
    von + open/named place (dative): "Von der Schule."  "Vom Bahnhof."
JP: どこから + motion verb — "トムはどこから来た？" / Answer: "庭から。" "学校から。"
ZH: 從哪裡 — "湯姆從哪裡來？" / Answer: "從花園來。" "從學校來。" """,

    "wann": """\
WANN — "when" (time)
EN: "When does the train arrive?"  →  "Soon."  /  "In the morning."  /  "At noon."
DE: "Wann kommt der Zug an?" — answer: "Bald."  "Am Morgen."  "Um zwölf."
JP: いつ + verb — "電車はいつ来る？" / Answer: "もうすぐ。" "朝に。" "昼に。"
ZH: 什麼時候 — "火車什麼時候到？" / Answer: "快了。" "早上。" """,

    "warum": """\
WARUM — "why" (reason)
EN: "Why did Kate leave?"  →  "Because of the rain."  /  "To help."  /  "For Tom."
DE: "Warum ist Kate gegangen?" — answer: "Wegen des Regens."  "Um zu helfen."  "Für Tom."
JP: なぜ/どうして + verb — "ケイトはなぜ行った？" / Answer: "雨のせいで。" "助けるために。"
ZH: 為什麼 — "凱特為什麼走了？" / Answer: "因為下雨。" "為了幫忙。" """,

    "wie": """\
WIE — "how" (manner or means)
EN: "How did Tom carry the bag?"  →  "With both hands."  /  "By bicycle."  /  "Carefully."
DE: "Wie hat Tom die Tasche getragen?" — answer: "Mit beiden Händen."  "Mit dem Fahrrad."  "Vorsichtig."
JP: どうやって + verb — "トムはどうやって袋を運んだ？" / Answer: "両手で。" "自転車で。"
ZH: 怎麼 — "湯姆怎麼拿袋子的？" / Answer: "用兩隻手。" "騎自行車。" """,

    "yn": """\
YES/NO question — verb first in German; positive expected answer
EN: "Did Tom eat the bread?" / "Is the door open?"  →  "Yes."  /  "No."
DE: Verb first: "Hat Tom das Brot gegessen?"  →  "Ja."  /  "Nein."
JP: verb + の? / か? — "トムはパンを食べた？"  →  "うん、食べた。"  /  "ううん。"
ZH: verb + 了嗎 — "湯姆吃了麵包嗎？"  →  "吃了。"  /  "沒吃。" """,

    "yn_doch": """\
NEGATIVE QUESTION answered with DOCH (German-specific contradiction of negation)
EN: "Didn't Tom eat the bread?"  →  "Yes, he ate it."  (contradict the negative)
DE: "Hat Tom das Brot nicht gegessen?"  →  "Doch, er hat es gegessen."
    DOCH = yes-but-you're-wrong. Only used to contradict a negative question. No English equivalent.
JP: "トムはパンを食べなかった？"  →  "うん、食べた。"  (affirm the truth despite negative framing)
ZH: "湯姆沒吃麵包嗎？"  →  "吃了。"  (state what actually happened) """,
}


# ─────────────────────────────────────────────────────────────────
# Prompt templates
# ─────────────────────────────────────────────────────────────────

GLOBAL_RULES = """\
## Language rules

German:
  V2 word order — verb is always the second constituent.
  Time adverbials trigger inversion: "Gestern kam Tom..." not "Gestern Tom kam...".
  Perfekt: sein + participle for intransitive motion (ist gegangen, ist gelaufen, ist gekommen,
    ist gefahren, ist angekommen, ist gefallen, ist gesprungen).
    haben + participle for everything else (hat gegessen, hat getragen, hat gegeben, hat gelegt).
  Articles: masc nom=der, acc=den, dat=dem; fem nom/acc=die, dat=der; neut nom/acc=das, dat=dem.
  Contractions: in+dem=im, an+dem=am, in+das=ins, an+das=ans, zu+dem=zum, zu+der=zur.

Japanese:
  Plain form throughout. No desu/masu. No keigo.
  Past: ta-form. Ongoing: te-iru form. Future: darou / to omou.
  SCRIPT: every Japanese line must be written in Japanese script only (kanji + hiragana + katakana).
  NEVER use romaji. Roman letters anywhere in a Japanese line = wrong.
  Pronoun drop: omit subject and object pronouns when recoverable from context.

Traditional Mandarin Chinese (繁體中文):
  Use Traditional characters throughout — 來 not 来, 裡 not 里, 說 not 说, 國 not 国, etc.
  Completed action: 了. Ongoing: 在 + verb. Future intent: 會.
  No tense morphology — time is shown by context and particles.
  Pronoun drop: omit pronouns when context is clear.

All:
  Short, concrete sentences. No metaphors. No literary prose.
  Each sentence group: exactly 4 lines — English / German / Japanese / Traditional Mandarin."""


NARRATIVE_PROMPT = """\
Generate a short parallel story in English, German, Japanese (Japanese script only — \
kanji/hiragana/katakana, NO romaji), and Traditional Mandarin Chinese.
This is a language-learning corpus for a small AI. Write clear, concrete everyday sentences.

{global_rules}

## Story specification

Setting: {setting}
Characters: {actors_str}
{new_words_line}\
Scene: {desc}

## Format

Write 7-10 sentence groups separated by blank lines.
Each group: exactly 4 lines in order — English / German / Japanese / Traditional Mandarin.
No headers. No labels. No grammar notes inside the story.

Return JSON only — no commentary, no markdown fences:
{{"story_id": "{story_id}", "groups": [["EN", "DE", "JP", "ZH"], ...]}}"""


QA_PROMPT = """\
Generate a short parallel story in English, German, Japanese (Japanese script only — \
kanji/hiragana/katakana, NO romaji), and Traditional Mandarin Chinese.
The story includes one embedded Q&A exchange.

{global_rules}

## Question type: {q_type_label}

{q_type_rules}

## Story specification

Setting: {setting}
Characters: {actors_str}
{new_words_line}\
Scene: {desc}

## Story structure — follow exactly

1. 2–3 narrative groups establishing the scene
2. One question group — EVERY LINE in this group must end with a question mark (?). No exceptions.
3. One answer group (short fragment answer — not a full sentence, just the answer itself)
4. 1–2 narrative groups continuing or resolving the scene

Total: 5–8 groups. Each group: exactly 4 lines (English / German / Japanese / Traditional Mandarin).
No headers, no labels, no grammar commentary.

Return JSON only — no commentary, no markdown fences:
{{"story_id": "{story_id}", "groups": [["EN", "DE", "JP", "ZH"], ...]}}"""


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def validate_groups(groups: list, story_type: str) -> list[str]:
    errors = []
    if not isinstance(groups, list):
        return ["groups is not a list"]
    if len(groups) < 4:
        errors.append(f"too few groups: {len(groups)}")
    if len(groups) > 14:
        errors.append(f"too many groups: {len(groups)}")
    for i, g in enumerate(groups):
        if not isinstance(g, list) or len(g) != 4:
            errors.append(f"group {i+1}: expected list of 4 lines, got {type(g).__name__}")
            continue
        if not all(isinstance(line, str) and line.strip() for line in g):
            errors.append(f"group {i+1}: empty or non-string line")
    if story_type == "qa":
        has_q = any(
            isinstance(g, list) and any(line.strip().endswith("?") for line in g)
            for g in groups
        )
        if not has_q:
            errors.append("no question group found (no line in any group ends with ?)")
    return errors


def check_required(groups: list, new_words: list[str]) -> list[str]:
    all_en = " ".join(g[0].lower() for g in groups if isinstance(g, list) and g).replace("-", " ")
    return [w for w in new_words if w.lower() not in all_en]


def parse_response(raw: str) -> tuple[dict | None, bool]:
    raw = raw.strip()
    raw = re.sub(r"^```[^\n]*\n", "", raw)
    raw = re.sub(r"\n?```$", "", raw.strip())
    try:
        return json.loads(raw), True
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                return json.loads(m.group(0)), True
            except json.JSONDecodeError:
                pass
    return None, False


def groups_to_file(groups: list) -> str:
    return "\n\n".join("\n".join(g) for g in groups) + "\n"


# ─────────────────────────────────────────────────────────────────
# Generation
# ─────────────────────────────────────────────────────────────────

def generate_one(job: dict, client: OpenAI, dry_run: bool) -> bool:
    num        = job["num"]
    story_type = job["story_type"]
    story_id   = f"story_{num:04d}"
    out_path   = OUT_DIR / f"{story_id}.md"

    if out_path.exists():
        log(f"  SKIP {story_id} — exists")
        return True

    if dry_run:
        log(f"  [DRY-RUN] {story_id} ({story_type})")
        return True

    actors_str    = ", ".join(job["actors"])
    new_words     = job.get("new_words", [])
    new_words_line = (
        f"Required words (must appear naturally in the story): {', '.join(new_words)}\n"
        if new_words else ""
    )

    pending_missing: list[str] = []

    for attempt in (1, 2):
        extra = (
            f"\n\nCRITICAL: the following words MUST appear in the story: {', '.join(pending_missing)}."
            if pending_missing else ""
        )

        if story_type == "narrative":
            prompt = NARRATIVE_PROMPT.format(
                global_rules=GLOBAL_RULES,
                setting=job["setting"],
                actors_str=actors_str,
                new_words_line=new_words_line,
                desc=job["desc"],
                story_id=story_id,
            ) + extra
        else:
            q_type = job["q_type"]
            prompt = QA_PROMPT.format(
                global_rules=GLOBAL_RULES,
                q_type_label=q_type.upper().replace("_", " + "),
                q_type_rules=Q_TYPE_RULES[q_type],
                setting=job["setting"],
                actors_str=actors_str,
                new_words_line=new_words_line,
                desc=job["desc"],
                story_id=story_id,
            ) + extra

        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=32768,
            )
        except Exception as e:
            log(f"  API ERROR (attempt {attempt}) {story_id}: {e}")
            if attempt == 2:
                return False
            continue

        raw  = (resp.choices[0].message.content or "").strip()
        data, ok = parse_response(raw)
        if not ok or data is None:
            log(f"  PARSE FAIL (attempt {attempt}) {story_id}")
            if attempt == 2:
                return False
            continue

        groups = data.get("groups", [])
        errors = validate_groups(groups, story_type)
        if errors:
            log(f"  VALIDATE FAIL (attempt {attempt}) {story_id}:")
            for e in errors:
                log(f"    {e}")
            if attempt == 2:
                return False
            continue

        missing = check_required(groups, new_words)
        if missing and attempt == 1:
            pending_missing = missing
            log(f"  MISSING WORDS (attempt 1) {story_id}: {missing} — retrying")
            continue

        content = groups_to_file(groups)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")

        tin  = resp.usage.prompt_tokens     if resp.usage else "?"
        tout = resp.usage.completion_tokens if resp.usage else "?"
        log(f"  OK {story_id}.md  [{story_type}]  ({tin}→{tout})")
        if missing:
            log(f"  WARN {story_id}: still missing: {missing}")
        return True

    return False


# ─────────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────────

def run_gen(args: argparse.Namespace, client: OpenAI) -> None:
    jobs = JOBS[:args.limit] if args.limit else JOBS
    log(f"Generating {len(jobs)} lang_5d stories...")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ok = failed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(generate_one, job, client, args.dry_run): job for job in jobs}
        for fut in as_completed(futures):
            if fut.result():
                ok += 1
            else:
                failed += 1

    log(f"\nDone: {ok} written/skipped, {failed} failed.")


def run_report() -> None:
    files = sorted(OUT_DIR.glob("story_*.md"))
    print(f"lang_5d: {len(files)} / {len(JOBS)} stories")

    new_words = [
        "boss", "colleague", "director", "lawyer", "outside", "temple", "university", "waiter",
        "neighbour", "restaurant", "inside", "blackboard", "schoolyard", "begin",
        "toolbox", "wrench", "peg", "crate", "mailbox", "easel", "riverbank",
        "nightstand", "tired", "janitor", "employee", "cash", "discuss", "slobber",
        "chat", "history", "document",
    ]
    counts: dict[str, int] = {w: 0 for w in new_words}
    for f in files:
        text = f.read_text(encoding="utf-8").lower()
        for w in new_words:
            if w in text:
                counts[w] += 1

    print("\nNew-word coverage (target ≥ 2):")
    for w, c in sorted(counts.items()):
        flag = "OK " if c >= 2 else "LOW"
        print(f"  {flag} {w}: {c}")

    # Q-type distribution
    q_counts: dict[str, int] = {}
    for job in JOBS:
        if job["story_type"] == "qa":
            qt = job["q_type"]
            q_counts[qt] = q_counts.get(qt, 0) + 1
    print("\nQA type distribution (planned):")
    for qt, c in sorted(q_counts.items()):
        print(f"  {qt}: {c}")


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Lang-5d story generator")
    sub    = parser.add_subparsers(dest="cmd")

    gen_p = sub.add_parser("gen", help="Generate story files")
    gen_p.add_argument("--workers", type=int, default=4)
    gen_p.add_argument("--limit",   type=int, default=0, help="Generate only first N jobs")
    gen_p.add_argument("--dry-run", action="store_true")

    sub.add_parser("report", help="Coverage report")

    args = parser.parse_args()

    if args.cmd == "report":
        run_report()
        return

    if args.cmd != "gen":
        parser.print_help()
        return

    api_key = load_api_key()
    if not api_key and not args.dry_run:
        print("ERROR: set OPENROUTER_API_KEY or OPENAI_API_KEY", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key or "dry", base_url=BASE_URL)
    run_gen(args, client)


if __name__ == "__main__":
    main()

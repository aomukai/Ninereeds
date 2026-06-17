#!/usr/bin/env python3
"""
bridge_extend.py — Generate pending bridge file types:
  Type A: always-dative prepositions (mit/bei/von/aus/nach/zu/seit/gegenüber) — 80 files (235–314)
  Type B: dative pronouns (ihm/ihr/ihnen/mir/dir/uns/euch) — 30 files (315–344)
  Type C: NOM/ACC isolation (accusative-only verbs, no dative) — 20 files (345–364)

Each call to DeepSeek generates one file. Workers run in parallel.

Usage:
  python3 meta/scripts/bridge_extend.py gen --type A [--workers 6] [--dry-run]
  python3 meta/scripts/bridge_extend.py gen --type B [--workers 6] [--dry-run]
  python3 meta/scripts/bridge_extend.py gen --type C [--workers 6] [--dry-run]
  python3 meta/scripts/bridge_extend.py status
"""

import argparse
import concurrent.futures
import json
import os
import pathlib
import re
import sys
import threading
import time

from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────

AUTH_PATH  = pathlib.Path.home() / ".local/share/opencode/auth.json"
BASE_URL   = "https://openrouter.ai/api/v1"
MODEL      = "deepseek/deepseek-v4-flash"
BRIDGE_DIR = pathlib.Path("training_data/01_language/bridge")

# ── Job definitions ────────────────────────────────────────────────────────────

# Type A: always-dative prepositions
# Each entry: (file_num, preposition, de_prep_phrase, NOM_NP_de, NOM_NP_en, scenario_hint)
PREP_JOBS = []

_PREP_DATA = [
    # (preposition, Q-word_de, Q-word_en, Q-word_jp, Q-word_zh, 10 NP pairs)
    ("mit", "Mit wem", "With whom", "誰と", "和谁", [
        ("das Mädchen", "the girl", "der Junge", "the boy", "gehen ins Kino", "goes to the cinema"),
        ("der Mann", "the man", "die Frau", "the woman", "spazieren", "walk"),
        ("das Kind", "the child", "die Lehrerin", "the teacher", "arbeiten", "work"),
        ("die Frau", "the woman", "der Nachbar", "the neighbor", "sprechen", "speak"),
        ("der Junge", "the boy", "das Mädchen", "the girl", "spielen", "play"),
        ("die Schülerin", "the student", "dem Freund", "the friend", "lernen", "study"),
        ("der Arzt", "the doctor", "der Patient", "the patient", "reden", "talk"),
        ("das Baby", "the baby", "die Mutter", "the mother", "schlafen", "sleep"),
        ("der Koch", "the cook", "die Küchenhilfe", "the kitchen helper", "kochen", "cook"),
        ("die Großmutter", "the grandmother", "das Enkelkind", "the grandchild", "lesen", "read"),
    ]),
    ("bei", "Bei wem", "At whose place", "誰のところに", "在谁那里", [
        ("das Mädchen", "the girl", "der Arzt", "the doctor", "wohnen", "live"),
        ("der Mann", "the man", "die Großmutter", "the grandmother", "schlafen", "sleep"),
        ("das Kind", "the child", "der Lehrer", "the teacher", "lernen", "study"),
        ("die Frau", "the woman", "der Nachbar", "the neighbor", "helfen", "help"),
        ("der Junge", "the boy", "die Freundin", "the friend", "essen", "eat"),
        ("die Schülerin", "the student", "der Onkel", "the uncle", "bleiben", "stay"),
        ("der Patient", "the patient", "der Arzt", "the doctor", "sein", "be"),
        ("das Baby", "the baby", "die Tante", "the aunt", "spielen", "play"),
        ("der Koch", "the cook", "die Chefin", "the boss", "arbeiten", "work"),
        ("die Großmutter", "the grandmother", "die Tochter", "the daughter", "wohnen", "live"),
    ]),
    ("von", "Von wem", "From whom", "誰から", "从谁那里", [
        ("das Mädchen", "the girl", "die Mutter", "the mother", "ein Buch bekommen", "receives a book"),
        ("der Mann", "the man", "der Bruder", "the brother", "Hilfe bekommen", "gets help"),
        ("das Kind", "the child", "der Lehrer", "the teacher", "ein Lob bekommen", "gets praise"),
        ("die Frau", "the woman", "der Arzt", "the doctor", "Rat bekommen", "gets advice"),
        ("der Junge", "the boy", "die Großmutter", "the grandmother", "Geld bekommen", "gets money"),
        ("die Schülerin", "the student", "der Freund", "the friend", "ein Geschenk bekommen", "receives a gift"),
        ("der Patient", "the patient", "der Arzt", "the doctor", "Medizin bekommen", "gets medicine"),
        ("das Baby", "the baby", "die Mutter", "the mother", "Milch bekommen", "gets milk"),
        ("der Koch", "the cook", "dem Lieferanten", "the supplier", "Gemüse bekommen", "gets vegetables"),
        ("die Großmutter", "the grandmother", "dem Enkel", "the grandchild", "Blumen bekommen", "gets flowers"),
    ]),
    ("aus", "Woher", "From where", "どこから", "从哪里", [
        ("das Mädchen", "the girl", "dem Haus", "the house", "kommen", "comes"),
        ("der Mann", "the man", "dem Büro", "the office", "kommen", "comes"),
        ("das Kind", "the child", "der Schule", "the school", "kommen", "comes"),
        ("die Frau", "the woman", "der Küche", "the kitchen", "kommen", "comes"),
        ("der Junge", "the boy", "dem Park", "the park", "kommen", "comes"),
        ("die Schülerin", "the student", "dem Klassenzimmer", "the classroom", "kommen", "comes"),
        ("der Patient", "the patient", "dem Krankenhaus", "the hospital", "kommen", "comes"),
        ("das Baby", "the baby", "dem Bett", "the bed", "kommen", "comes"),
        ("der Koch", "the cook", "der Küche", "the kitchen", "kommen", "comes"),
        ("die Großmutter", "the grandmother", "dem Garten", "the garden", "kommen", "comes"),
    ]),
    ("nach", "Wohin", "To where", "どこへ", "去哪里", [
        ("das Mädchen", "the girl", "der Schule", "school", "gehen", "goes"),
        ("der Mann", "the man", "dem Markt", "the market", "gehen", "goes"),
        ("das Kind", "the child", "dem Park", "the park", "laufen", "runs"),
        ("die Frau", "the woman", "der Arbeit", "work", "fahren", "drives"),
        ("der Junge", "the boy", "dem Stadion", "the stadium", "rennen", "runs"),
        ("die Schülerin", "the student", "Hause", "home", "gehen", "goes"),
        ("der Patient", "the patient", "dem Krankenhaus", "the hospital", "fahren", "goes"),
        ("das Baby", "the baby", "dem Bett", "bed", "gehen", "goes"),
        ("der Koch", "the cook", "dem Supermarkt", "the supermarket", "fahren", "drives"),
        ("die Großmutter", "the grandmother", "dem Arzt", "the doctor", "gehen", "goes"),
    ]),
    ("zu", "Zu wem", "To whom", "誰のところへ", "去谁那里", [
        ("das Mädchen", "the girl", "der Ärztin", "the doctor", "gehen", "goes"),
        ("der Mann", "the man", "dem Bruder", "the brother", "fahren", "drives"),
        ("das Kind", "the child", "der Lehrerin", "the teacher", "laufen", "runs"),
        ("die Frau", "the woman", "der Nachbarin", "the neighbor", "gehen", "goes"),
        ("der Junge", "the boy", "dem Freund", "the friend", "rennen", "runs"),
        ("die Schülerin", "the student", "den Eltern", "the parents", "kommen", "comes"),
        ("der Patient", "the patient", "dem Arzt", "the doctor", "fahren", "goes"),
        ("das Baby", "the baby", "der Mutter", "the mother", "krabbeln", "crawls"),
        ("der Koch", "the cook", "dem Chef", "the boss", "gehen", "goes"),
        ("die Großmutter", "the grandmother", "den Enkeln", "the grandchildren", "fahren", "drives"),
    ]),
    ("seit", "Seit wann", "Since when", "いつから", "从什么时候开始", [
        ("das Mädchen", "the girl", "dem Montag", "Monday", "lernen", "has studied"),
        ("der Mann", "the man", "einem Jahr", "one year", "arbeiten", "has worked"),
        ("das Kind", "the child", "dem Sommer", "summer", "schwimmen", "has swum"),
        ("die Frau", "the woman", "dem Morgen", "morning", "warten", "has waited"),
        ("der Junge", "the boy", "drei Stunden", "three hours", "spielen", "has played"),
        ("die Schülerin", "the student", "dem Herbst", "autumn", "üben", "has practiced"),
        ("der Patient", "the patient", "dem Unfall", "the accident", "schlafen", "has rested"),
        ("das Baby", "the baby", "dem Mittag", "noon", "schlafen", "has slept"),
        ("der Koch", "the cook", "der Früh", "early morning", "kochen", "has cooked"),
        ("die Großmutter", "the grandmother", "der Jugend", "youth", "stricken", "has knitted"),
    ]),
    ("gegenüber", "Wem gegenüber", "Across from whom", "誰の向かいに", "在谁对面", [
        ("das Mädchen", "the girl", "dem Jungen", "the boy", "sitzen", "sits"),
        ("der Mann", "the man", "der Frau", "the woman", "stehen", "stands"),
        ("das Kind", "the child", "dem Lehrer", "the teacher", "sitzen", "sits"),
        ("die Frau", "the woman", "dem Arzt", "the doctor", "sitzen", "sits"),
        ("der Junge", "the boy", "dem Freund", "the friend", "stehen", "stands"),
        ("die Schülerin", "the student", "der Klassenkameradin", "the classmate", "sitzen", "sits"),
        ("der Patient", "the patient", "dem Arzt", "the doctor", "sitzen", "sits"),
        ("das Baby", "the baby", "der Mutter", "the mother", "sitzen", "sits"),
        ("der Koch", "the cook", "dem Gast", "the guest", "stehen", "stands"),
        ("die Großmutter", "the grandmother", "dem Enkel", "the grandchild", "sitzen", "sits"),
    ]),
]

file_num = 235
for prep_de, q_de, q_en, q_jp, q_zh, pairs in _PREP_DATA:
    for (nom_de, nom_en, dat_de, dat_en, verb_de, verb_en) in pairs:
        PREP_JOBS.append({
            "num": file_num,
            "type": "A",
            "prep": prep_de,
            "nom_de": nom_de, "nom_en": nom_en,
            "dat_de": dat_de, "dat_en": dat_en,
            "verb_de": verb_de, "verb_en": verb_en,
            "q_de": q_de, "q_en": q_en, "q_jp": q_jp, "q_zh": q_zh,
        })
        file_num += 1

# Type B: dative pronouns
PRONOUN_JOBS = []
_PRONOUN_DATA = [
    # (pronoun_de, pronoun_en, antecedent_de, antecedent_en, acc_de, acc_en, count)
    ("ihm", "him", "der Mann", "the man", "das Buch", "the book", 4),
    ("ihm", "him", "der Junge", "the boy", "den Ball", "the ball", 1),
    ("ihr", "her", "die Frau", "the woman", "das Buch", "the book", 3),
    ("ihr", "her", "das Mädchen", "the girl", "den Apfel", "the apple", 1),
    ("ihr", "her", "die Lehrerin", "the teacher", "das Heft", "the notebook", 1),
    ("ihnen", "them", "die Kinder", "the children", "das Brot", "the bread", 3),
    ("ihnen", "them", "die Schüler", "the students", "die Bücher", "the books", 2),
    ("mir", "me", "das Mädchen", "the girl", "das Buch", "the book", 2),
    ("mir", "me", "der Mann", "the man", "den Stift", "the pen", 2),
    ("mir", "me", "die Frau", "the woman", "den Apfel", "the apple", 1),
    ("dir", "you", "das Mädchen", "the girl", "das Buch", "the book", 2),
    ("dir", "you", "der Junge", "the boy", "den Ball", "the ball", 2),
    ("dir", "you", "die Lehrerin", "the teacher", "das Heft", "the notebook", 1),
    ("uns", "us", "der Lehrer", "the teacher", "die Hefte", "the notebooks", 2),
    ("uns", "us", "die Frau", "the woman", "das Essen", "the food", 1),
    ("euch", "you all", "der Koch", "the cook", "das Essen", "the food", 2),
    ("euch", "you all", "das Mädchen", "the girl", "die Äpfel", "the apples", 2),
]

pnum = 315
for row in _PRONOUN_DATA:
    pron_de, pron_en, subj_de, subj_en, acc_de, acc_en, count = row
    for i in range(count):
        PRONOUN_JOBS.append({
            "num": pnum,
            "type": "B",
            "pronoun_de": pron_de,
            "pronoun_en": pron_en,
            "subj_de": subj_de,
            "subj_en": subj_en,
            "acc_de": acc_de,
            "acc_en": acc_en,
        })
        pnum += 1

# Type C: NOM/ACC isolation (accusative-only verbs)
NOMACC_JOBS = []
_VERB_DATA = [
    ("sehen", "sees", "der Mann", "the man", "den Jungen", "the boy", 2),
    ("kennen", "knows", "die Frau", "the woman", "den Arzt", "the doctor", 2),
    ("haben", "has", "das Kind", "the child", "den Ball", "the ball", 2),
    ("lieben", "loves", "das Mädchen", "the girl", "den Bruder", "the brother", 2),
    ("hören", "hears", "der Junge", "the boy", "die Musik", "the music", 2),
    ("finden", "finds", "die Frau", "the woman", "den Schlüssel", "the key", 2),
    ("treffen", "meets", "der Mann", "the man", "den Freund", "the friend", 2),
    ("brauchen", "needs", "das Kind", "the child", "das Buch", "the book", 2),
    ("lesen", "reads", "die Schülerin", "the student", "den Brief", "the letter", 2),
    ("besuchen", "visits", "das Mädchen", "the girl", "die Großmutter", "the grandmother", 2),
]

cnum = 345
for verb_de, verb_en, nom_de, nom_en, acc_de, acc_en, count in _VERB_DATA:
    for i in range(count):
        NOMACC_JOBS.append({
            "num": cnum,
            "type": "C",
            "verb_de": verb_de,
            "verb_en": verb_en,
            "nom_de": nom_de,
            "nom_en": nom_en,
            "acc_de": acc_de,
            "acc_en": acc_en,
        })
        cnum += 1

ALL_JOBS = {
    "A": PREP_JOBS,
    "B": PRONOUN_JOBS,
    "C": NOMACC_JOBS,
}

# ── API client ────────────────────────────────────────────────────────────────

def get_api_key():
    for var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        val = os.environ.get(var)
        if val:
            return val
    if AUTH_PATH.exists():
        d = json.loads(AUTH_PATH.read_text())
        k = d.get("openrouter", {}).get("key") or d.get(".openrouter.key", "")
        if k:
            return k
    wp = os.environ.get("WORKER_API_KEY")
    if wp:
        return wp
    sys.exit("No API key found. Set OPENROUTER_API_KEY.")

_client = None
_client_lock = threading.Lock()

def get_client():
    global _client
    with _client_lock:
        if _client is None:
            _client = OpenAI(api_key=get_api_key(), base_url=BASE_URL)
    return _client

# ── Prompt builders ───────────────────────────────────────────────────────────

BRIDGE_FORMAT_EXAMPLE = """\
(das Mädchen) *gibt* [dem Jungen] {den Apfel}.
(the girl) *gives* [the boy] {the apple}.
(女の子が)[少年に]{りんごを}*あげる*。
(那個女孩)*給*[男孩]{蘋果}。

[Wem / To whom / 誰に / 给谁] does the girl give the apple?
[the boy]. / [dem Jungen]. / [少年に]. / [男孩].

{Was / What / 何を / 什么} does the girl give the boy?
{the apple}. / {den Apfel}. / {りんごを}. / {蘋果}.

Das Mädchen gibt dem Jungen den Apfel.
The girl gives the boy the apple.
女の子が少年にりんごをあげる。
那個女孩給男孩蘋果。"""


def build_prompt_A(job):
    return f"""\
Generate ONE German-English-Japanese-Chinese bridge file for a language learning corpus.

## Job
Preposition: {job['prep']} (always takes DATIVE case in German)
Subject (NOM): German: {job['nom_de']} | English: {job['nom_en']}
Dative NP: German: {job['dat_de']} | English: {job['dat_en']}
Action: German: {job['verb_de']} | English: {job['verb_en']}

## Format rules
- Line 1: (NOM_de) *verb_de* [prep DAT_de].
- Line 2: (NOM_en) *verb_en* [prep_en DAT_en].
- Line 3: Japanese equivalent with [(DAT)] in brackets
- Line 4: Chinese equivalent with [(DAT)] in brackets
- Blank line
- Q&A: {job['q_de']} / {job['q_en']} / {job['q_jp']} / {job['q_zh']} + answer line
- Blank line
- Plain sentence in all 4 languages (no brackets)

## Bracket key
(NOM) = subject | [DAT prepositional phrase] = dative PP | *verb* = main verb

## Output
Output ONLY the file content. No commentary, no markdown fences.

## Example (different verb — shows format only)
(das Mädchen) *geht* [mit dem Jungen] ins Kino.
(the girl) *goes* [with the boy] to the cinema.
(女の子が)[男の子と]一緒に映画館に*行く*。
(那個女孩)*和*[那個男孩]去電影院。

[Mit wem / With whom / 誰と / 和谁] does the girl go to the cinema?
[mit dem Jungen]. / [with the boy]. / [男の子と]. / [那個男孩].

Das Mädchen geht mit dem Jungen ins Kino.
The girl goes with the boy to the cinema.
女の子が男の子と一緒に映画館に行く。
那個女孩和那個男孩去電影院。"""


def build_prompt_B(job):
    return f"""\
Generate ONE German-English-Japanese-Chinese bridge file for a language learning corpus.

## Job
Subject (NOM): German: {job['subj_de']} | English: {job['subj_en']}
Dative pronoun: German: {job['pronoun_de']} | English: {job['pronoun_en']}
Accusative object: German: {job['acc_de']} | English: {job['acc_en']}
Verb: geben (gives / 渡す / 給)

## Format rules (DATIVE PRONOUN focus)
- Line 1: ({job['subj_de']}) *gibt* [{job['pronoun_de']}] {{{job['acc_de']}}}.
- Line 2: ({job['subj_en']}) *gives* [{job['pronoun_en']}] {{{job['acc_en']}}}.
- Line 3: Japanese equivalent with [DAT pronoun] in brackets and {{ACC}} in braces
- Line 4: Chinese equivalent
- Blank line
- Q&A: Wem/To whom/誰に/给谁 + answer line with all 4 lang forms
- Blank line
- Was/What/何を/什么 + answer line
- Blank line
- Plain sentence in all 4 languages (no brackets)

## Bracket key
(NOM) = subject | [DAT] = dative (pronoun) | {{ACC}} = accusative | *verb* = main verb

## Output
Output ONLY the file content. No commentary, no markdown fences.

## Reference format
{BRIDGE_FORMAT_EXAMPLE}"""


def build_prompt_C(job):
    return f"""\
Generate ONE German-English-Japanese-Chinese bridge file for a language learning corpus.
This file drills NOM/ACC (NO dative) to anchor the NOM-ACC boundary before dative is introduced.

## Job
Subject (NOM): German: {job['nom_de']} | English: {job['nom_en']}
Verb: {job['verb_de']} | {job['verb_en']}
Accusative object: German: {job['acc_de']} | English: {job['acc_en']}

## Format rules (NOM/ACC only — no DAT bracket)
- Line 1: ({job['nom_de']}) *{job['verb_de']}* {{{job['acc_de']}}}.
- Line 2: ({job['nom_en']}) *{job['verb_en']}* {{{job['acc_en']}}}.
- Line 3: Japanese equivalent with (NOM) in parens and {{ACC}} in braces
- Line 4: Chinese equivalent
- Blank line
- Q&A: Wer/Who/誰が/谁 + answer (the subject)
- Blank line
- Q&A: Wen/Whom/誰を/看见谁 + answer (the ACC object)
- Blank line
- Plain sentence in all 4 languages (no brackets)

## Bracket key
(NOM) = subject | {{ACC}} = accusative object | *verb* = main verb | NO [DAT] in this file

## Output
Output ONLY the file content. No commentary, no markdown fences."""


PROMPT_BUILDERS = {"A": build_prompt_A, "B": build_prompt_B, "C": build_prompt_C}

# ── File naming ───────────────────────────────────────────────────────────────

def job_filename(job):
    n = job["num"]
    t = job["type"]
    if t == "A":
        prep = job["prep"]
        nom = job["nom_de"].split()[-1].lower().replace("ü","ue").replace("ä","ae").replace("ö","oe")
        dat = job["dat_de"].split()[-1].lower().replace("ü","ue").replace("ä","ae").replace("ö","oe")
        return BRIDGE_DIR / f"{n:03d}_bridge_prep_{prep}_{nom}_{dat}.md"
    elif t == "B":
        pron = job["pronoun_de"]
        subj = job["subj_de"].split()[-1].lower().replace("ü","ue").replace("ä","ae").replace("ö","oe")
        return BRIDGE_DIR / f"{n:03d}_bridge_datpron_{pron}_{subj}.md"
    else:
        verb = job["verb_de"]
        nom = job["nom_de"].split()[-1].lower().replace("ü","ue").replace("ä","ae").replace("ö","oe")
        acc = job["acc_de"].split()[-1].lower().replace("ü","ue").replace("ä","ae").replace("ö","oe").replace("ß","ss")
        return BRIDGE_DIR / f"{n:03d}_bridge_nomacc_{verb}_{nom}_{acc}.md"

# ── Verification ──────────────────────────────────────────────────────────────

def verify(content, job_type):
    lines = [l for l in content.strip().splitlines()]
    if len(lines) < 8:
        return False, "too short"
    # Check bracket presence
    if job_type == "A":
        if "[" not in lines[0] or "(" not in lines[0]:
            return False, "missing brackets line 1"
    elif job_type == "B":
        if "[" not in lines[0] or "{" not in lines[0]:
            return False, "missing DAT/ACC brackets line 1"
    elif job_type == "C":
        if "{" not in lines[0] or "(" not in lines[0]:
            return False, "missing NOM/ACC brackets line 1"
        if "[" in content and "DAT" not in content:
            # DAT bracket crept in
            return False, "unexpected DAT bracket in NOM/ACC file"
    return True, "ok"

# ── Worker ────────────────────────────────────────────────────────────────────

_print_lock = threading.Lock()

def log(msg):
    with _print_lock:
        print(msg, flush=True)

def process_job(job, dry_run=False):
    path = job_filename(job)
    if path.exists():
        log(f"  SKIP {path.name} (exists)")
        return True

    prompt = PROMPT_BUILDERS[job["type"]](job)

    if dry_run:
        log(f"  DRY  {path.name}")
        return True

    for attempt in range(2):
        try:
            resp = get_client().chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.3,
            )
            content = resp.choices[0].message.content.strip()
            ok, reason = verify(content, job["type"])
            if ok:
                path.write_text(content + "\n", encoding="utf-8")
                log(f"  OK   {path.name}")
                return True
            else:
                log(f"  WARN {path.name} verify failed: {reason} (attempt {attempt+1})")
                if attempt == 0:
                    time.sleep(1)
        except Exception as e:
            log(f"  ERR  {path.name}: {e} (attempt {attempt+1})")
            if attempt == 0:
                time.sleep(2)
    log(f"  FAIL {path.name}")
    return False

# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_status(args):
    total = sum(len(v) for v in ALL_JOBS.values())
    done = sum(1 for jobs in ALL_JOBS.values() for j in jobs if job_filename(j).exists())
    print(f"Bridge extension status: {done}/{total} files exist")
    for t, jobs in ALL_JOBS.items():
        d = sum(1 for j in jobs if job_filename(j).exists())
        print(f"  Type {t}: {d}/{len(jobs)}")

def cmd_gen(args):
    jobs = ALL_JOBS.get(args.type)
    if jobs is None:
        sys.exit(f"Unknown type: {args.type}. Use A, B, or C.")
    pending = [j for j in jobs if not job_filename(j).exists()]
    if args.batch:
        pending = pending[:args.batch]
    print(f"Type {args.type}: {len(pending)} jobs to run ({args.workers} workers)")
    if not pending:
        print("Nothing to do.")
        return
    ok = fail = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(process_job, j, args.dry_run): j for j in pending}
        for f in concurrent.futures.as_completed(futures):
            if f.result():
                ok += 1
            else:
                fail += 1
    print(f"Done: {ok} OK, {fail} failed.")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    sg = sub.add_parser("gen")
    sg.add_argument("--type", required=True, choices=["A", "B", "C"])
    sg.add_argument("--workers", type=int, default=6)
    sg.add_argument("--batch", type=int, default=None)
    sg.add_argument("--dry-run", action="store_true")

    sub.add_parser("status")

    args = p.parse_args()
    if args.cmd == "gen":
        cmd_gen(args)
    else:
        cmd_status(args)

if __name__ == "__main__":
    main()

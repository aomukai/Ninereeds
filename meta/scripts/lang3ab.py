#!/usr/bin/env python3
"""
Lang-3a and lang-3b corpus generation.

3a — Dative (indirect object). Two construction types:
  double-object  (give_1.md) — "Tom gives her an apple"
  prepositional  (give_2.md) — "Tom gives an apple to her"
  Verbs allowing both get two files. Prepositional-only verbs get one (_1.md).

3b — Dative + genitive. One file per verb.
  Every sentence contains a dative IO AND a genitive possessor on the DO.

No plan phase — jobs are fully determined by the verb lists below.

Usage:
  python3 meta/scripts/lang3ab.py gen-3a  [--workers 4] [--batch 5] [--limit N] [--dry-run]
  python3 meta/scripts/lang3ab.py gen-3b  [--workers 4] [--batch 5] [--limit N] [--dry-run]
  python3 meta/scripts/lang3ab.py report

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
OUT_3A    = LANG_DIR / "lang_3a"
OUT_3B    = LANG_DIR / "lang_3b"
BASE_URL  = "https://openrouter.ai/api/v1"
MODEL     = "deepseek/deepseek-v4-flash"

_lock = threading.Lock()

# ─────────────────────────────────────────────────────────────────
# Verb lists (from level_3a_templates.md and level_3b_templates.md)
# ─────────────────────────────────────────────────────────────────

# 3a: verbs allowing BOTH double-object and prepositional constructions
# Anglo-Saxon / Germanic verbs: "Tom gives her an apple" AND "Tom gives an apple to her"
BOTH_VERBS = [
    # original
    "give", "show", "tell", "send", "bring", "buy",
    "lend", "offer", "teach", "write", "hand", "pass",
    # extended
    "sell", "read", "sing", "throw", "toss", "feed",
    "serve", "deal", "slide", "rent", "promise", "forward",
    "email", "text", "whisper", "shout", "award", "pay",
    "quote", "wire", "flip",
]

# 3a: verbs allowing PREPOSITIONAL ONLY (Latinate — "she explained him X" is not English)
PREP_ONLY_VERBS = [
    # original
    "explain", "describe", "suggest", "announce",
    "mention", "introduce", "report",
    # extended
    "recommend", "present", "propose", "dedicate",
    "demonstrate", "confirm", "admit", "signal",
    "assign", "submit",
]

# 3b uses the same double-object verbs as 3a
VERBS_3B = BOTH_VERBS


def all_jobs_3a() -> list[dict]:
    jobs = []
    for v in BOTH_VERBS:
        jobs.append({"verb": v, "file_id": f"{v}_1", "construction": "double_object"})
        jobs.append({"verb": v, "file_id": f"{v}_2", "construction": "prepositional"})
    for v in PREP_ONLY_VERBS:
        jobs.append({"verb": v, "file_id": f"{v}_1", "construction": "prepositional"})
    return jobs


def all_jobs_3b() -> list[dict]:
    return [{"verb": v, "file_id": v} for v in VERBS_3B]


def pending_jobs(jobs: list[dict], out_dir: Path) -> list[dict]:
    seen: set[str] = set()
    pending = []
    for job in jobs:
        fid = job["file_id"]
        if fid in seen:
            continue
        seen.add(fid)
        if not (out_dir / f"{fid}.md").exists():
            pending.append(job)
    return pending


def log(msg: str) -> None:
    with _lock:
        print(msg, flush=True)


def load_api_key() -> str:
    for var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        if key := os.environ.get(var):
            return key
    return ""


# ─────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────

GLOBAL_RULES = """\
## Global rules — apply to every sentence in every language

Naturalise, don't translate.
  The goal is the same meaning expressed as a native speaker would say it.

Japanese plain form throughout. No ます/です. No keigo.

German V2 word order.
  The verb is always the second constituent.
  Perfekt for past: hat + past participle (sein + pp for motion/state-change).
  Time adverbials trigger inversion: Gestern hat Tom... (not Gestern Tom hat...).

Mandarin aspect particles: 了 completed, 会 future intent.

Pronoun drop.
  Japanese and Mandarin drop subject and object pronouns when the referent is clear.

Vary subjects across groups: Tom, Kate, the child, the teacher, she, he, they.
Do not explain grammar inside the generated files."""


GEN_3A_PROMPT_TPL = """\
Generate lang_3a training files. Each file teaches the dative (indirect object) construction
for one English verb in one construction type. The sentences show how the recipient of an action
is encoded in English, German, Japanese (plain form), and Mandarin Chinese.

{rules}

## Core linguistic facts encoded in these files

English has two surface forms for the dative:
  double_object:  "Tom gives her an apple"     — IO before DO, no preposition
  prepositional:  "Tom gives an apple to her"  — DO before IO, "to" marks the recipient

German has ONE form: dative case on the IO. Both English constructions map to the same German sentence.
  "Tom gibt ihr einen Apfel." — same for both "Tom gives her an apple" AND "Tom gives an apple to her."
  German does NOT have a "to" prepositional dative for these verbs.

Japanese has ONE form: に particle marks the recipient.
  "トムは彼女にリンゴをあげた。" — same for both English constructions.
  Use あげる when the agent gives TO someone (outward). Use くれる when someone gives TO the speaker.
  Never use あげる when the recipient is the speaker ("she gives me X" → 彼女はXをくれた).

Mandarin encodes the DISTINCTION using the verb-specific constructions below:
  double_object:  给 + IO + [VERB] + DO  (for most verbs; 给 marks the recipient)
  prepositional:  把 + DO + 给 + IO (+ 了)  (topicalises the DO when it is definite)

CRITICAL — Mandarin verb reference. Use the correct verb/frame per verb; do NOT default to bare 给+IO+DO:
  give    → 给 + IO + DO  (给 is the main verb; no extra verb needed)
  show    → 给 + IO + 看 + DO  ("give to see") or 把 + DO + 给 + IO + 看
  tell    → 告诉 + IO + DO  (告诉 = inform/tell; for a story/joke: 给 + IO + 讲 + DO)
  send    → 给 + IO + 发/寄 + DO  (发 email/message; 寄 physical mail/parcel)
  bring   → 给 + IO + 带来/拿来 + DO
  buy     → 给 + IO + 买 + DO
  lend    → 把 + DO + 借给 + IO
  offer   → 给 + IO + 提供/递 + DO
  teach   → 教 + IO + DO  (教 already encodes the recipient; 给 optional: 给 + IO + 教 + DO)
  write   → 给 + IO + 写 + DO
  hand    → 把 + DO + 递给/交给 + IO
  pass    → 把 + DO + 递给/传给 + IO
  explain → 给 + IO + 解释 + DO  or  把 + DO + 解释给 + IO
  describe → 给 + IO + 描述 + DO  or  向 + IO + 描述 + DO
  suggest → 向 + IO + 建议 + DO  or  给 + IO + 建议 + DO
  announce → 向 + IO + 宣布 + DO
  mention → 向 + IO + 提到/提及 + DO
  introduce → 给 + IO + 介绍 + DO  or  把 + DO + 介绍给 + IO
  report  → 向 + IO + 汇报 + DO
  sell    → 把 + DO + 卖给 + IO
  read    → 给 + IO + 读/朗读 + DO
  sing    → 给 + IO + 唱 + DO
  throw   → 把 + DO + 扔给/丢给 + IO
  toss    → 把 + DO + 扔给 + IO
  feed    → 给 + IO + 喂 + DO  (animals); 给 + IO + 吃 + DO  (people)
  serve   → 给 + IO + 端上/上 + DO
  deal    → 给 + IO + 发 + DO  (cards: 给他发牌)
  slide   → 把 + DO + 推给/递给 + IO
  rent    → 把 + DO + 租给 + IO
  promise → 答应/承诺 + IO + DO  or  向 + IO + 承诺 + DO
  forward → 把 + DO + 转发给 + IO
  email   → 给 + IO + 发 + DO  (邮件)
  text    → 给 + IO + 发 + DO  (短信/消息)
  whisper → 向 + IO + 低语/小声说 + DO  or  对 + IO + 耳语
  shout   → 向 + IO + 喊/大声说 + DO
  award   → 给 + IO + 颁发/授予 + DO
  pay     → 给 + IO + 一个 + [compliment/etc.]  (付 for money; 给...一个鼓励 for intangibles)
  quote   → 给 + IO + 报 + DO  (报价 = quote a price: 给他报了个价)
  wire    → 给 + IO + 汇/转 + DO  (汇款 = wire money)
  flip    → 给 + IO + 扔/弹 + DO  (把硬币弹给他)
  recommend → 向 + IO + 推荐 + DO  or  给 + IO + 推荐 + DO
  present → 把 + DO + 呈现/交给 + IO  or  向 + IO + 颁发 + DO
  propose → 向 + IO + 提出/建议 + DO
  dedicate → 把 + DO + 献给 + IO
  demonstrate → 给 + IO + 演示/展示 + DO
  confirm → 向 + IO + 确认 + DO
  admit   → 向 + IO + 承认 + DO
  signal  → 向 + IO + 示意/发信号 + DO
  assign  → 把 + DO + 分配给/交给 + IO
  submit  → 向 + IO + 提交 + DO  or  把 + DO + 提交给 + IO

## German reference

Dative pronouns: mir (me) | dir (you) | ihm (him) | ihr (her) | uns (us) | ihnen (them)
Dative NPs: dem Kind (neut) | der Frau (fem) | dem Mann (masc) | den Kindern (pl) | dem Hund (masc)
Accusative articles: einen (masc indef) | eine (fem indef) | ein (neut indef) | den (masc def) | die (fem def) | das (neut def)

Common German verb forms for these verbs:
  give → geben, gab, gegeben (gibt 3sg pres)
  show → zeigen, zeigte, gezeigt
  tell → sagen/erzählen; for telling a person: erzählen; past: erzählte, erzählt
  send → schicken, schickte, geschickt
  bring → bringen, brachte, gebracht
  buy → kaufen, kaufte, gekauft
  lend → leihen, lieh, geliehen
  offer → anbieten, bot an, angeboten
  teach → beibringen, brachte bei, beigebracht (or lehren, lehrte, gelehrt for content)
  write → schreiben, schrieb, geschrieben
  hand → reichen, reichte, gereicht
  pass → reichen/weitergeben, reichte weiter, weitergegeben
  explain    → erklären, erklärte, erklärt
  describe   → beschreiben, beschrieb, beschrieben
  suggest    → vorschlagen, schlug vor, vorgeschlagen
  announce   → ankündigen, kündigte an, angekündigt
  mention    → erwähnen, erwähnte, erwähnt
  introduce  → vorstellen, stellte vor, vorgestellt
  report     → berichten, berichtete, berichtet
  sell       → verkaufen, verkaufte, verkauft (jmdm. etw. verkaufen)
  read       → vorlesen, las vor, vorgelesen (reading aloud to someone)
  sing       → singen, sang, gesungen (jmdm. etw. singen)
  throw      → zuwerfen, warf zu, zugeworfen (jmdm. etw. zuwerfen)
  toss       → zuwerfen, warf zu, zugeworfen (same as throw)
  feed       → füttern (animals, + accusative); geben (people, + dative)
  serve      → servieren, servierte, serviert (jmdm. etw. servieren)
  deal       → austeilen / geben (jmdm. Karten austeilen)
  slide      → zuschieben, schob zu, zugeschoben (jmdm. etw. zuschieben)
  rent       → vermieten, vermietete, vermietet (jmdm. etw. vermieten)
  promise    → versprechen, versprach, versprochen (jmdm. etw. versprechen)
  forward    → weiterleiten, leitete weiter, weitergeleitet (jmdm. etw. weiterleiten)
  email      → schicken / mailen (jmdm. eine E-Mail schicken)
  text       → schreiben / simsen (jmdm. eine Nachricht schicken)
  whisper    → zuflüstern, flüsterte zu, zugeflüstert (jmdm. etw. zuflüstern)
  shout      → zurufen, rief zu, zugerufen (jmdm. etw. zurufen)
  award      → verleihen, verlieh, verliehen (prizes); überreichen for physical handoff
  pay        → machen (jmdm. ein Kompliment machen — NOT zahlen for compliments)
  quote      → nennen / mitteilen (jmdm. einen Preis nennen)
  wire       → überweisen, überwies, überwiesen (jmdm. Geld überweisen)
  flip       → zuwerfen, warf zu, zugeworfen (jmdm. eine Münze zuwerfen)
  recommend  → empfehlen, empfahl, empfohlen (jmdm. etw. empfehlen — takes dative in DE)
  present    → überreichen, reichte über, überreicht (formal handoff)
  propose    → vorschlagen, schlug vor, vorgeschlagen (jmdm. etw. vorschlagen — takes dative)
  dedicate   → widmen, widmete, gewidmet (jmdm. etw. widmen)
  demonstrate → vorführen, führte vor, vorgeführt (jmdm. etw. vorführen)
  confirm    → bestätigen, bestätigte, bestätigt (jmdm. etw. bestätigen)
  admit      → gestehen, gestand, gestanden (jmdm. etw. gestehen)
  signal     → signalisieren / anzeigen (jmdm. etw. signalisieren)
  assign     → zuweisen, wies zu, zugewiesen (jmdm. etw. zuweisen)
  submit     → vorlegen / einreichen (jmdm. etw. vorlegen)

## Files to generate

{files}

## Output format

Each file contains 3 to 5 sentence groups separated by blank lines.
Each group is exactly 4 lines in order: English / German / Japanese / Mandarin.
Vary IO between pronoun (her, him, them) and NP (the child, the woman, the children) across groups.
Vary tense across groups: past, present, future (wird + inf / あげるだろう / 会).

Return JSON only — no commentary, no markdown fences:
{{"files": [{{"file_id": "...", "groups": [["EN", "DE", "JP", "ZH"], ...]}}]}}"""


GEN_3B_PROMPT_TPL = """\
Generate lang_3b training files. Each file teaches a sentence containing BOTH a dative indirect
object AND a genitive possessor inside the direct object: "He gives the child the dog's ball."

{rules}

## Core linguistic facts

Structure: SUBJ + VERB + IO(dative) + POSS's DO

IO = indirect object — who receives the item.
POSS = possessor of the direct object — whose item it is.
DO = the item being transferred.

German: four case-marked NPs in one sentence.
  Nominative subject | Dative IO | Accusative DO | Genitive possessor
  "Er gibt dem Kind den Ball des Hundes."
  Word order: SUBJ VERB IO(DAT) DO(ACC+GEN) — dative NP precedes accusative NP.
  Genitive modifier follows the noun it modifies: "den Ball des Hundes", "das Buch der Lehrerin".

Japanese: の marks the possessor inside the DO; に marks the IO.
  "[SUBJ]は + [IO]に + [POSS]の[DO]を + [VERB]"
  "彼は子供に犬のボールをあげた。"

Mandarin: 的 marks possession inside the DO; 给 marks the IO.
  "他给孩子狗的球了。" or with 把-construction: "他把狗的球给了孩子。"

## German reference

Dative IO NPs: dem Kind | der Frau | dem Mann | den Kindern | dem Hund
Genitive possessor NPs: des Hundes (masc) | des Kindes (neut) | der Katze (fem) | der Kinder (pl) | des Mannes (masc) | der Lehrerin (fem)
Accusative DO articles: einen (masc indef) | eine (fem indef) | ein (neut indef) | den (masc def) | die (fem def) | das (neut def)

Rules:
  DO pronoun possessor is FORBIDDEN — do not write "his ball", "her book". Use a named or noun possessor ("the dog's ball", "the teacher's letter"). Pronoun possessors collapse the genitive lesson.
  Vary IO between pronoun (her, him, them) and NP (the child, the woman) across groups.
  Each file: 3–5 groups.

## Files to generate

{files}

## Output format

Each file contains 3 to 5 sentence groups separated by blank lines.
Each group is exactly 4 lines in order: English / German / Japanese / Mandarin.

Return JSON only — no commentary, no markdown fences:
{{"files": [{{"file_id": "...", "groups": [["EN", "DE", "JP", "ZH"], ...]}}]}}"""


# ─────────────────────────────────────────────────────────────────
# Gen
# ─────────────────────────────────────────────────────────────────

def _format_jobs_3a(jobs: list[dict]) -> str:
    lines = []
    for j in jobs:
        c = j["construction"]
        v = j["verb"]
        fid = j["file_id"]
        if c == "double_object":
            desc = f'Double-object construction: "Tom {v}s her X" — IO before DO, no preposition.'
        else:
            desc = f'Prepositional construction: "Tom {v}s X to her" — DO before IO, "to" marks recipient.'
        lines.append(
            f"file_id: {fid}\n"
            f"verb: {v}\n"
            f"construction: {c}\n"
            f"desc: {desc}"
        )
    return "\n\n".join(lines)


def _format_jobs_3b(jobs: list[dict]) -> str:
    lines = []
    for j in jobs:
        lines.append(
            f"file_id: {j['file_id']}\n"
            f"verb: {j['verb']}\n"
            f"desc: Every sentence contains a dative IO and a genitive possessor on the DO."
        )
    return "\n\n".join(lines)


def gen_batch(
    jobs: list[dict],
    level: str,
    client: OpenAI,
    out_dir: Path,
    dry_run: bool,
) -> tuple[list[str], list[str]]:
    if dry_run:
        log(f"  [DRY-RUN] gen-{level}: {[j['file_id'] for j in jobs]}")
        return [j["file_id"] for j in jobs], []

    if level == "3a":
        files_text = _format_jobs_3a(jobs)
        prompt = GEN_3A_PROMPT_TPL.format(rules=GLOBAL_RULES, files=files_text)
    else:
        files_text = _format_jobs_3b(jobs)
        prompt = GEN_3B_PROMPT_TPL.format(rules=GLOBAL_RULES, files=files_text)

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=32768,
        )
    except Exception as e:
        log(f"  GEN API ERROR for {jobs[0]['file_id']}…: {e}")
        return [], [j["file_id"] for j in jobs]

    raw = (resp.choices[0].message.content or "").strip()
    tokens_in  = resp.usage.prompt_tokens     if resp.usage else "?"
    tokens_out = resp.usage.completion_tokens if resp.usage else "?"

    if raw.startswith("```"):
        raw = re.sub(r"^```[^\n]*\n", "", raw)
        raw = re.sub(r"\n?```$", "", raw.strip())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            log(f"  PARSE FAIL for {jobs[0]['file_id']}… raw:\n{raw[:200]}")
            return [], [j["file_id"] for j in jobs]
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            log(f"  PARSE FAIL (inner) for {jobs[0]['file_id']}…")
            return [], [j["file_id"] for j in jobs]

    written, failed = [], []

    for file_data in data.get("files", []):
        fid    = file_data.get("file_id", "").strip()
        groups = file_data.get("groups", [])

        if not fid:
            continue

        if not (3 <= len(groups) <= 6):
            log(f"  SKIP {fid}: expected 3–6 groups, got {len(groups)}")
            failed.append(fid)
            continue

        bad = False
        for g in groups:
            if len(g) != 4 or not all(isinstance(s, str) and s.strip() for s in g):
                log(f"  SKIP {fid}: malformed group")
                bad = True
                break
        if bad:
            failed.append(fid)
            continue

        content = "\n\n".join("\n".join(g) for g in groups) + "\n"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{fid}.md").write_text(content, encoding="utf-8")
        log(f"  OK {fid} ({tokens_in}→{tokens_out})")
        written.append(fid)

    returned = {f.get("file_id", "") for f in data.get("files", [])}
    for job in jobs:
        fid = job["file_id"]
        if fid not in returned and fid not in failed and fid not in written:
            log(f"  MISSING from response: {fid}")
            failed.append(fid)

    return written, failed


def run_gen(args: argparse.Namespace, level: str, client: OpenAI) -> None:
    if level == "3a":
        all_jobs = all_jobs_3a()
        out_dir  = OUT_3A
    else:
        all_jobs = all_jobs_3b()
        out_dir  = OUT_3B

    pending = pending_jobs(all_jobs, out_dir)

    if args.limit:
        pending = pending[: args.limit]

    total = len(pending)
    if total == 0:
        print("Nothing to generate — all files already exist.")
        return

    print(f"Pending: {total} files")
    batches = [pending[i : i + args.batch] for i in range(0, total, args.batch)]
    print(f"Batches: {len(batches)}  (batch size: {args.batch})")

    all_failed: list[str] = []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {
            pool.submit(gen_batch, b, level, client, out_dir, args.dry_run): b
            for b in batches
        }
        for fut in as_completed(futs):
            _, failed = fut.result()
            all_failed.extend(failed)

    done = total - len(all_failed)
    print(f"\nDone: {done}/{total} written. Failed: {len(all_failed)}")
    if all_failed:
        print("Failed:", all_failed[:20])


# ─────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────

def run_report() -> None:
    jobs_3a = all_jobs_3a()
    jobs_3b = all_jobs_3b()

    done_3a = sum(1 for j in jobs_3a if (OUT_3A / f"{j['file_id']}.md").exists())
    done_3b = sum(1 for j in jobs_3b if (OUT_3B / f"{j['file_id']}.md").exists())

    print(f"lang_3a: {done_3a} / {len(jobs_3a)} files generated")
    do_construction_breakdown = len(jobs_3a) > 0
    if do_construction_breakdown:
        dbl  = [j for j in jobs_3a if j["construction"] == "double_object"]
        prep = [j for j in jobs_3a if j["construction"] == "prepositional"]
        done_dbl  = sum(1 for j in dbl  if (OUT_3A / f"{j['file_id']}.md").exists())
        done_prep = sum(1 for j in prep if (OUT_3A / f"{j['file_id']}.md").exists())
        print(f"  double_object:  {done_dbl} / {len(dbl)}")
        print(f"  prepositional:  {done_prep} / {len(prep)}")

    print()
    print(f"lang_3b: {done_3b} / {len(jobs_3b)} files generated")


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Lang-3a and 3b corpus generator")
    sub = parser.add_subparsers(dest="cmd", required=True)

    for cmd in ("gen-3a", "gen-3b"):
        p = sub.add_parser(cmd, help=f"Generate {cmd[4:]} files")
        p.add_argument("--workers", type=int, default=4)
        p.add_argument("--batch",   type=int, default=5,
                       help="Files per API call (default 5)")
        p.add_argument("--limit",   type=int, default=0,
                       help="Max files to generate this run (0=all pending)")
        p.add_argument("--dry-run", action="store_true")

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

    if args.cmd == "gen-3a":
        run_gen(args, "3a", client)
    elif args.cmd == "gen-3b":
        run_gen(args, "3b", client)


if __name__ == "__main__":
    main()

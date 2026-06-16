#!/usr/bin/env python3
"""
bridge_gen_4case.py — Generate new 4-case bridge files (NOM + verb + DAT + ACC + GEN).

All new files use generic person NPs (no named characters). Each file includes:
  - Standard 4-language annotation block (EN/DE/JP/ZH)
  - Two word-order scrambles of the DE sentence (ACC-fronted, DAT-fronted)
  - Full Q&A for all 4 cases (Wer/Wem/Was/Wessen)
  - Plain sentences in all 4 languages

New files are numbered from 101 onwards: 101_bridge_4case_*.md

Model: deepseek/deepseek-v4-flash via OpenRouter
Progress: tmp/bridge_gen_4case_done.txt

Usage:
  python3 meta/scripts/bridge_gen_4case.py gen [--workers 4] [--batch 10]
  python3 meta/scripts/bridge_gen_4case.py status
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

ROOT = Path(__file__).resolve().parent.parent.parent

_env = ROOT / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if _line.strip() and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

BRIDGE_DIR = ROOT / "training_data" / "01_language" / "bridge"
DONE_FILE  = ROOT / "tmp" / "bridge_gen_4case_done.txt"
MODEL      = "deepseek/deepseek-v4-flash"
MAX_TOKENS = 4096
TEMPERATURE = 0.5

_print_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Job matrix — (de_nom, en_nom, jp_nom, zh_nom,
#               de_verb, en_verb, jp_verb, zh_verb,
#               de_dat, en_dat, jp_dat, zh_dat,
#               de_acc, en_acc, jp_acc, zh_acc,
#               de_gen, en_gen, jp_gen, zh_gen,
#               slug)
# ---------------------------------------------------------------------------

SUBJECTS = [
    ("das Mädchen", "the girl",  "女の子", "那個女孩"),
    ("die Frau",    "the woman", "女の人", "那個女人"),
    ("der Mann",    "the man",   "男の人", "那個男人"),
    ("der Junge",   "the boy",   "男の子", "那個男孩"),
]

VERBS = [
    ("gibt",    "gives",  "あげる",    "給",    "gibt"),
    ("zeigt",   "shows",  "見せる",    "展示給", "zeigt"),
    ("bringt",  "brings", "持ってくる", "帶給",  "bringt"),
    ("schickt", "sends",  "送る",      "寄給",  "schickt"),
    ("leiht",   "lends",  "貸す",      "借給",  "leiht"),
    ("schenkt", "gives as a gift", "プレゼントする", "送給", "schenkt"),
]

DAT_RECIPIENTS = [
    ("dem Jungen",  "the boy",   "男の子に",  "那個男孩", "jungen"),
    ("der Frau",    "the woman", "女の人に",  "那個女人", "frau"),
    ("dem Kind",    "the child", "子供に",    "那個小孩", "kind"),
    ("dem Mann",    "the man",   "男の人に",  "那個男人", "mann"),
    ("dem Hund",    "the dog",   "犬に",      "那條狗",   "hund"),
    ("der Katze",   "the cat",   "猫に",      "那隻貓",   "katze"),
]

ACC_OBJECTS = [
    ("den Ball",   "the ball",  "ボールを",  "球",   "ball"),
    ("das Buch",   "the book",  "本を",      "書",   "buch"),
    ("den Apfel",  "the apple", "りんごを",  "蘋果", "apfel"),
    ("den Becher", "the cup",   "コップを",  "杯子", "becher"),
    ("die Tasche", "the bag",   "かばんを",  "包",   "tasche"),
    ("das Heft",   "the notebook", "ノートを", "筆記本", "heft"),
]

GEN_MODIFIERS = [
    ("des Mannes",  "the man's",   "男の人の", "男人的",  "mannes"),
    ("des Kindes",  "the child's", "子供の",   "小孩的",  "kindes"),
    ("der Frau",    "the woman's", "女の人の", "女人的",  "frau"),
    ("des Jungen",  "the boy's",   "男の子の", "男孩的",  "jungen"),
    ("der Katze",   "the cat's",   "猫の",     "貓的",    "katze"),
    ("des Hundes",  "the dog's",   "犬の",     "狗的",    "hundes"),
]


def base_noun(de_form: str) -> str:
    """Extract a rough base to detect same-entity conflicts."""
    return (de_form
            .replace("dem ", "").replace("der ", "").replace("den ", "")
            .replace("des ", "").replace("das ", "").replace("die ", "")
            .lower().strip())


def build_jobs() -> list[dict]:
    """Generate the full job list, filtering out same-entity conflicts."""
    jobs = []
    for subj in SUBJECTS:
        for verb in VERBS:
            for dat in DAT_RECIPIENTS:
                for acc in ACC_OBJECTS:
                    for gen in GEN_MODIFIERS:
                        # Conflict checks
                        nom_base = base_noun(subj[0])
                        dat_base = base_noun(dat[0])
                        gen_base = base_noun(gen[0])
                        if nom_base == dat_base:
                            continue
                        if gen_base == nom_base or gen_base == dat_base:
                            continue
                        slug = f"{verb[4]}_{dat[4]}_{acc[4]}_{gen[4]}_{subj[0].split()[-1].lower()}"
                        jobs.append({
                            "nom": subj, "verb": verb, "dat": dat,
                            "acc": acc, "gen": gen, "slug": slug,
                        })
    return jobs


def next_file_number() -> int:
    existing = sorted(BRIDGE_DIR.glob("*_bridge_4case_*.md"))
    if not existing:
        return 101
    nums = [int(p.name.split("_")[0]) for p in existing]
    return max(nums) + 1


def load_done() -> set[str]:
    if DONE_FILE.exists():
        return set(DONE_FILE.read_text("utf-8").splitlines())
    return set()


def mark_done(slug: str):
    with open(DONE_FILE, "a", encoding="utf-8") as f:
        f.write(slug + "\n")


# Static example used in all prompts (no substitution needed)
EXAMPLE = """\
(das Mädchen) *gives* [the boy] {the man's ball}.
(das Mädchen) *gibt* [dem Jungen] {den Ball <des Mannes>}.
(女の子が)[少年に]{<男の人の>ボールを}*あげる*。
(那個女孩)*給*[那個男孩]{<男人的>球}。

{den Ball <des Mannes>} *gibt* (das Mädchen) [dem Jungen].
The girl gives the boy the man's ball.
男の人のボールを女の子が少年にあげる。
那個女孩把男人的球給了那個男孩。

[dem Jungen] *gibt* (das Mädchen) {den Ball <des Mannes>}.
The girl gives the boy the man's ball.
女の子が少年に男の人のボールをあげる。
那個女孩給那個男孩男人的球。

(Wer / Who / 誰が / 谁) gives the boy the man's ball?
(das Mädchen). / (the girl). / (女の子が). / (那個女孩).

[Wem / To whom / 誰に / 给谁] does the girl give the man's ball?
[dem Jungen]. / [the boy]. / [少年に]. / [那個男孩].

{Was / What / 何を / 什么} does the girl give the boy?
{den Ball des Mannes}. / {the man's ball}. / {<男の人の>ボールを}. / {<男人的>球}.

<Wessen / Whose / 誰の / 谁的> ball does the girl give the boy?
<des Mannes>. / <the man's>. / <男の人の>. / <男人的>.

Das Mädchen gibt dem Jungen den Ball des Mannes.
The girl gives the boy the man's ball.
女の子が少年に男の人のボールをあげる。
那個女孩給那個男孩男人的球。"""


def build_prompt(job: dict) -> str:
    nom  = job["nom"]
    verb = job["verb"]
    dat  = job["dat"]
    acc  = job["acc"]
    gen  = job["gen"]
    de_nom, en_nom, jp_nom, zh_nom     = nom[0], nom[1], nom[2], nom[3]
    de_verb, en_verb, jp_verb, zh_verb = verb[0], verb[1], verb[2], verb[3]
    de_dat, en_dat, jp_dat, zh_dat     = dat[0], dat[1], dat[2], dat[3]
    de_acc, en_acc, jp_acc, zh_acc     = acc[0], acc[1], acc[2], acc[3]
    de_gen, en_gen, jp_gen, zh_gen     = gen[0], gen[1], gen[2], gen[3]

    return f"""Generate a grammar bridge training file following the EXAMPLE below exactly.

The file teaches that case markers encode grammatical role regardless of word order.
It drills all 4 German cases (NOM, DAT, ACC, GEN) in one sentence.

PARAMETERS for this file:
  NOM: DE="{de_nom}" | EN="{en_nom}" | JP="{jp_nom}が" | ZH="{zh_nom}"
  VERB: DE="{de_verb}" | EN="{en_verb}" | JP="{jp_verb}" | ZH="{zh_verb}"
  DAT: DE="{de_dat}" | EN="{en_dat}" | JP="{jp_dat}" | ZH="{zh_dat}"
  ACC: DE="{de_acc}" | EN="{en_acc}" | JP="{jp_acc}" | ZH="{zh_acc}"
  GEN (modifies ACC): DE="{de_gen}" | EN="{en_gen}" | JP="{jp_gen}" | ZH="{zh_gen}"

ANNOTATION BRACKETS: (NOM)  *verb*  [DAT]  {{ACC}}  <GEN>

STRUCTURE (follow exactly — same number of sections, same blank-line layout):
1. 4-line annotation block: EN / DE / JP / ZH
2. blank line
3. ACC-fronted DE variant + EN/JP/ZH equivalents (4 lines)
4. blank line
5. DAT-fronted DE variant + EN/JP/ZH equivalents (4 lines)
6. blank line
7. Q&A block — 4 question-answer pairs (Wer / Wem / Was / Wessen), each answer on one line
8. blank line
9. 4 plain sentences without brackets: EN / DE / JP / ZH

Rules:
- Japanese: SOV order, particle が stays inside the NOM bracket, に inside DAT, を inside ACC, の inside GEN
- Chinese: SVO order
- GEN modifier goes INSIDE the ACC braces: {{ACC <GEN>}}
- In answer lines: use natural word order for each language (DE: ACC then GEN; EN: GEN then ACC)
- In plain sentences: no brackets, natural word order

EXAMPLE (do NOT copy — produce your own with the parameters above):

{EXAMPLE}

Output ONLY the file content. No explanation, no markdown fences."""


def verify_output(text: str, job: dict) -> bool:
    """Check required annotation brackets are present."""
    if "(" not in text or "*" not in text:
        return False
    if "[" not in text or "{" not in text or "<" not in text:
        return False
    # Check that all 4 case Q&A labels appear
    for label in ("Wer /", "Wem /", "Was /", "Wessen /"):
        if label not in text:
            return False
    return True


def call_api(prompt: str, api_key: str) -> str:
    from openai import OpenAI
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        messages=[{"role": "user", "content": prompt}],
    )
    content = resp.choices[0].message.content or ""
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    if content.startswith("```"):
        content = "\n".join(l for l in content.splitlines()
                            if not l.startswith("```")).strip()
    content = "\n".join(l for l in content.splitlines() if l.strip() != "---").strip()
    return content


def run_one(job: dict, file_num: int, api_key: str) -> tuple[str, bool, str]:
    slug = job["slug"]
    out_path = BRIDGE_DIR / f"{file_num:03d}_bridge_4case_{slug}.md"
    if out_path.exists():
        return (slug, True, "already exists")

    prompt = build_prompt(job)
    try:
        result = call_api(prompt, api_key)
    except Exception as e:
        return (slug, False, f"API error: {e}")

    if not verify_output(result, job):
        return (slug, False, "verification failed — missing required brackets or Q&A")

    out_path.write_text(result + "\n", "utf-8")
    return (slug, True, str(out_path.name))


def cmd_gen(args):
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("ERROR: OPENROUTER_API_KEY not set")

    all_jobs  = build_jobs()
    done      = load_done()
    pending   = [j for j in all_jobs if j["slug"] not in done]

    if args.batch:
        pending = pending[:args.batch]

    print(f"Total valid jobs: {len(all_jobs)} | done: {len(done)} | pending: {len(pending)}")
    if not pending:
        print("Nothing to do.")
        return

    file_num  = next_file_number()
    ok = fail = skip = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {}
        for i, job in enumerate(pending):
            futures[pool.submit(run_one, job, file_num + i, api_key)] = job

        for fut in as_completed(futures):
            slug, success, msg = fut.result()
            with _print_lock:
                if success:
                    if msg == "already exists":
                        print(f"  SKIP  {slug}")
                        skip += 1
                    else:
                        print(f"  OK    {msg}")
                        ok += 1
                    mark_done(slug)
                else:
                    print(f"  FAIL  {slug}: {msg}", file=sys.stderr)
                    fail += 1

    print(f"\nDone: {ok} generated, {skip} skipped, {fail} failed")
    if fail:
        sys.exit(1)


def cmd_status(args):
    all_jobs = build_jobs()
    done     = load_done()
    existing = list(BRIDGE_DIR.glob("*_bridge_4case_*.md"))
    print(f"Total valid jobs : {len(all_jobs)}")
    print(f"Marked done      : {len(done)}")
    print(f"Files on disk    : {len(existing)}")
    print(f"Remaining        : {len(all_jobs) - len(done)}")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    p_gen = sub.add_parser("gen")
    p_gen.add_argument("--workers", type=int, default=4)
    p_gen.add_argument("--batch",   type=int, default=0,
                       help="Max number of jobs to run (0 = all)")

    sub.add_parser("status")

    args = parser.parse_args()
    if args.cmd == "gen":
        cmd_gen(args)
    elif args.cmd == "status":
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
audit_teaching_stories.py — Quality audit for teaching story files.

Two-pass approach:
  Pass 1 (programmatic): block count, language order, Simplified Chinese,
                         Japanese polite form, definition openers.
  Pass 2 (LLM via Gemma4): grammar errors, wrong concept-word translations,
                            internal states without observable evidence.

Usage:
  # Full audit (programmatic + LLM):
  python3 meta/scripts/audit_teaching_stories.py run --local [--workers 4]

  # Programmatic pass only (fast, no LLM):
  python3 meta/scripts/audit_teaching_stories.py run --no-llm

  # Single file:
  python3 meta/scripts/audit_teaching_stories.py run --label worry --local

  # Summary of existing report:
  python3 meta/scripts/audit_teaching_stories.py report

Output:  tmp/teaching_stories_audit.jsonl
         tmp/teaching_stories_audit_summary.txt
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

ROOT = Path(__file__).resolve().parent.parent.parent

_env = ROOT / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if _line.strip() and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

STORIES_DIR   = ROOT / "training_data" / "teaching_stories"
VOCAB_FILE    = ROOT / "tmp" / "phase_vocab.jsonl"
AUDIT_LOG     = ROOT / "tmp" / "teaching_stories_audit.jsonl"
SUMMARY_FILE  = ROOT / "tmp" / "teaching_stories_audit_summary.txt"

LOCAL_ENDPOINT  = "http://192.168.3.5:1234/v1"
LOCAL_MODEL     = "gemma-4-26b-a4b-it"
REMOTE_MODEL    = "google/gemma-4-26b-a4b-it"   # audit model via OpenRouter
REPAIR_MODEL    = "google/gemma-3-4b-it"    # cheap repair model via OpenRouter

# ---------------------------------------------------------------------------
# Simplified Chinese → Traditional Chinese mapping (common characters)
# ---------------------------------------------------------------------------
SIMP_TO_TRAD: dict[str, str] = {
    '么': '麼', '这': '這', '来': '來', '说': '說', '们': '們',
    '为': '為', '时': '時', '学': '學', '国': '國', '会': '會',
    '从': '從', '发': '發', '问': '問', '没': '沒', '当': '當',
    '经': '經', '边': '邊', '过': '過', '进': '進', '个': '個',
    '东': '東', '长': '長', '开': '開', '对': '對', '关': '關',
    '头': '頭', '动': '動', '体': '體', '语': '語', '联': '聯',
    '总': '總', '样': '樣', '变': '變', '话': '話', '视': '視',
    '见': '見', '与': '與', '义': '義', '历': '歷', '记': '記',
    '间': '間', '后': '後', '还': '還', '门': '門', '实': '實',
    '现': '現', '场': '場', '产': '產', '应': '應', '线': '線',
    '带': '帶', '题': '題', '处': '處', '务': '務', '报': '報',
    '给': '給', '称': '稱', '认': '認', '亲': '親', '观': '觀',
    '传': '傳', '员': '員', '决': '決', '结': '結', '气': '氣',
    '华': '華', '红': '紅', '远': '遠', '设': '設', '规': '規',
    '数': '數', '热': '熱', '灯': '燈', '质': '質', '级': '級',
    '节': '節', '则': '則', '须': '須', '维': '維', '类': '類',
    '图': '圖', '导': '導', '获': '獲', '虽': '雖', '尽': '盡',
    '战': '戰', '继': '繼', '组': '組', '细': '細', '终': '終',
    '难': '難', '离': '離', '两': '兩', '丰': '豐', '乐': '樂',
    '书': '書', '买': '買', '卖': '賣', '尝': '嘗', '岁': '歲',
    '帮': '幫', '广': '廣', '归': '歸', '态': '態', '择': '擇',
    '权': '權', '欢': '歡', '汉': '漢', '汽': '汽',  # same
    '爱': '愛', '独': '獨', '画': '畫', '简': '簡', '纸': '紙',
    '续': '續', '罗': '羅', '职': '職', '艺': '藝', '药': '藥',
    '许': '許', '证': '證', '资': '資', '达': '達', '运': '運',
    '适': '適', '阶': '階', '随': '隨', '顾': '顧', '风': '風',
    '鱼': '魚', '鸟': '鳥',
}

# ---------------------------------------------------------------------------
# LLM audit prompt
# ---------------------------------------------------------------------------
AUDIT_PROMPT = """\
You are auditing a 4-language teaching story file for a small language model.

The file has four [user]/[Ninereeds] blocks in order: English (EN), German (DE), \
Japanese (JP), Traditional Chinese (ZH).

CONCEPT BEING TAUGHT: "{label}"

Check for these issues only:

1. GRAMMAR_ERROR (DE): German gender or case error (wrong adjective ending, wrong article).
2. POLITE_JAPANESE (JP): Uses です/ます/でした/ました instead of plain form.
3. SIMPLIFIED_CHINESE (ZH): Simplified Chinese characters used (should be Traditional).
4. WRONG_CONCEPT_WORD (ZH or JP): The concept "{label}" is translated with a semantically \
different word (e.g. "wonder" → "疑惑" means doubt, should be "好奇").
5. DEFINITION_OPENER (any lang): [Ninereeds] response begins with a definition \
("X is a...", "X refers to...", "X means...") instead of a narrative scene.
6. INTERNAL_STATE (any lang): Emotion stated directly without observable evidence \
("she felt sad" with no behavioral description showing it).

Report ONLY issues you are confident about. If no issues, output exactly: OK

Otherwise output a JSON object (no markdown fences, no extra text):
{{
  "issues": [
    {{
      "lang": "EN|DE|JP|ZH",
      "issue_type": "grammar_error|polite_japanese|simplified_chinese|wrong_concept_word|definition_opener|internal_state",
      "severity": "error|warning",
      "flagged_text": "exact text that is wrong, ≤ 60 chars",
      "suggestion": "corrected replacement text",
      "repair_type": "substitution|rewrite_block"
    }}
  ]
}}

Use repair_type "substitution" when flagged_text can simply be replaced with suggestion.
Use repair_type "rewrite_block" when the whole [Ninereeds] response needs rewriting.

---
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_vocab() -> dict[str, dict]:
    if not VOCAB_FILE.exists():
        return {}
    return {r["label"]: r
            for r in (json.loads(l) for l in VOCAB_FILE.read_text().splitlines() if l.strip())}


def parse_blocks(text: str) -> list[dict]:
    """Split file into list of {user, ninereeds} dicts."""
    blocks = []
    current_user = current_nr = None
    for line in text.splitlines():
        if line.startswith("[user]"):
            if current_user is not None:
                blocks.append({"user": current_user, "ninereeds": current_nr or ""})
            current_user = line[6:].strip()
            current_nr = None
        elif line.startswith("[Ninereeds]"):
            current_nr = line[11:].strip()
        elif current_nr is not None:
            current_nr += "\n" + line
    if current_user is not None:
        blocks.append({"user": current_user, "ninereeds": current_nr or ""})
    return blocks


def detect_language(text: str) -> str:
    """Heuristic: detect language from [user] line content."""
    cjk_chars = sum(1 for c in text if '一' <= c <= '鿿')
    jp_chars   = sum(1 for c in text if '぀' <= c <= 'ヿ')
    if jp_chars > 0:
        return "JP"
    if cjk_chars > 0:
        return "ZH"
    german_markers = ["was", "wie", "ist", "ein", "eine", "der", "die", "das",
                      "kannst", "zeig", "bitte", "warum", "wann"]
    lower = text.lower()
    if any(f" {m} " in f" {lower} " for m in german_markers):
        return "DE"
    return "EN"


# ---------------------------------------------------------------------------
# Programmatic pass
# ---------------------------------------------------------------------------

def programmatic_check(path: Path, label: str) -> list[dict]:
    issues = []
    text = path.read_text(encoding="utf-8")
    blocks = parse_blocks(text)

    # 1. Block count
    if len(blocks) != 4:
        issues.append({
            "lang": "ALL",
            "issue_type": "block_count",
            "severity": "error",
            "flagged_text": f"found {len(blocks)} blocks",
            "suggestion": "must have exactly 4 [user]/[Ninereeds] pairs",
            "repair_type": "rewrite_block",
        })
        return issues  # can't do further checks

    # Assign expected language order
    lang_order = ["EN", "DE", "JP", "ZH"]
    for i, (block, expected_lang) in enumerate(zip(blocks, lang_order)):
        detected = detect_language(block["user"])
        nr = block["ninereeds"]

        # 2. Language order check
        if detected != expected_lang and detected != "EN":  # EN is default fallback
            issues.append({
                "lang": expected_lang,
                "issue_type": "wrong_language",
                "severity": "error",
                "flagged_text": block["user"][:50],
                "suggestion": f"Block {i+1} should be {expected_lang}, detected as {detected}",
                "repair_type": "rewrite_block",
            })

        # 3. Simplified Chinese in ZH block
        if expected_lang == "ZH":
            found_simp = {}
            for char, trad in SIMP_TO_TRAD.items():
                if char in nr or char in block["user"]:
                    found_simp[char] = trad
            if found_simp:
                sample = ", ".join(f"{s}→{t}" for s, t in list(found_simp.items())[:5])
                issues.append({
                    "lang": "ZH",
                    "issue_type": "simplified_chinese",
                    "severity": "error",
                    "flagged_text": sample,
                    "suggestion": f"Replace: {sample}",
                    "repair_type": "substitution",
                    "simp_map": found_simp,
                })

        # 4. Japanese polite form in JP block
        if expected_lang == "JP":
            polite = re.findall(r'(?:ました|ません|ます|でした|です)', nr)
            if polite:
                issues.append({
                    "lang": "JP",
                    "issue_type": "polite_japanese",
                    "severity": "error",
                    "flagged_text": polite[0],
                    "suggestion": "Rewrite JP block in plain form (〜た, 〜だ, 〜る)",
                    "repair_type": "rewrite_block",
                })

        # 5. Definition opener in any block
        def_pattern = re.compile(
            rf'^{re.escape(label)}\s+is\s+(?:a|an|the)\b', re.IGNORECASE
        )
        if def_pattern.match(nr):
            issues.append({
                "lang": expected_lang,
                "issue_type": "definition_opener",
                "severity": "warning",
                "flagged_text": nr[:60],
                "suggestion": "Open with a narrative scene, not a definition",
                "repair_type": "rewrite_block",
            })

    return issues


# ---------------------------------------------------------------------------
# LLM pass
# ---------------------------------------------------------------------------

def get_client(local: bool, endpoint: str | None = None) -> OpenAI:
    if local or endpoint:
        url = endpoint or LOCAL_ENDPOINT
        return OpenAI(base_url=url, api_key="local")
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("Set OPENROUTER_API_KEY or use --local.")
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)


def llm_check(path: Path, label: str, client: OpenAI, model: str) -> list[dict]:
    content = path.read_text(encoding="utf-8").strip()
    prompt  = AUDIT_PROMPT.format(label=label)
    try:
        resp = client.chat.completions.create(
            model=model,
            max_tokens=1024,
            temperature=0.1,
            messages=[
                {"role": "user", "content": prompt + content},
            ],
        )
        text = resp.choices[0].message.content.strip()
    except Exception as e:
        return [{"lang": "ALL", "issue_type": "llm_error", "severity": "warning",
                 "flagged_text": str(e)[:80], "suggestion": "", "repair_type": "none"}]

    if text.strip() == "OK":
        return []

    # Strip markdown fences
    if text.startswith("```"):
        text = "\n".join(l for l in text.splitlines() if not l.startswith("```")).strip()
    try:
        data = json.loads(text)
        return data.get("issues", [])
    except json.JSONDecodeError:
        return [{"lang": "ALL", "issue_type": "llm_parse_error", "severity": "warning",
                 "flagged_text": text[:80], "suggestion": "", "repair_type": "none"}]


# ---------------------------------------------------------------------------
# Main audit worker
# ---------------------------------------------------------------------------

def audit_file(path: Path, label: str, client: OpenAI | None,
               model: str) -> dict | None:
    issues = programmatic_check(path, label)

    if client:
        llm_issues = llm_check(path, label, client, model)
        # Deduplicate by flagged_text
        existing = {i["flagged_text"] for i in issues}
        for issue in llm_issues:
            if issue["flagged_text"] not in existing:
                issues.append(issue)
                existing.add(issue["flagged_text"])

    if not issues:
        return None
    return {
        "file":   str(path.relative_to(ROOT)),
        "label":  label,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_run(args):
    vocab = load_vocab()
    if not STORIES_DIR.exists():
        sys.exit(f"Stories dir not found: {STORIES_DIR}")

    if args.label:
        safe = re.sub(r"[^\w\-]", "_", args.label).strip("_") + ".md"
        paths = [STORIES_DIR / safe]
        paths = [p for p in paths if p.exists()]
    else:
        paths = sorted(STORIES_DIR.glob("*.md"))

    if not paths:
        sys.exit("No story files found.")

    client = None if args.no_llm else get_client(args.local, args.endpoint)
    model  = args.model or (LOCAL_MODEL if args.local else REMOTE_MODEL)

    print(f"Auditing {len(paths)} files  "
          f"({'programmatic only' if args.no_llm else f'+ LLM: {model}'})"
          f"  workers={args.workers}")

    lock    = threading.Lock()
    results = []

    def process(path: Path):
        label = path.stem.replace("_", " ")
        # Try to find exact label from vocab
        if label not in vocab:
            # Try with spaces
            for k in vocab:
                if re.sub(r"[^\w\-]", "_", k).strip("_") == path.stem:
                    label = k
                    break
        result = audit_file(path, label, client, model)
        if result:
            with lock:
                results.append(result)
                print(f"  FLAGGED {path.name} — {len(result['issues'])} issue(s)")

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(process, p): p for p in paths}
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as e:
                print(f"  ERROR {futures[fut].name}: {e}")

    # Write log (append mode — resume-safe)
    done_files = set()
    if AUDIT_LOG.exists() and not args.force:
        done_files = {json.loads(l)["file"]
                      for l in AUDIT_LOG.read_text().splitlines() if l.strip()}

    with open(AUDIT_LOG, "a") as f:
        for r in results:
            if r["file"] not in done_files:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\nFlagged: {len(results)} / {len(paths)}")
    print(f"Report:  {AUDIT_LOG}")


def cmd_report(args):
    if not AUDIT_LOG.exists():
        sys.exit("No audit log found. Run audit first.")
    records = [json.loads(l) for l in AUDIT_LOG.read_text().splitlines() if l.strip()]
    if not records:
        print("Audit log is empty — no issues found.")
        return

    from collections import Counter
    type_counts  = Counter()
    lang_counts  = Counter()
    sev_counts   = Counter()
    repair_counts = Counter()
    for rec in records:
        for issue in rec["issues"]:
            type_counts[issue["issue_type"]] += 1
            lang_counts[issue["lang"]] += 1
            sev_counts[issue["severity"]] += 1
            repair_counts[issue.get("repair_type", "?")] += 1

    total_issues = sum(len(r["issues"]) for r in records)
    lines = [
        f"Files with issues: {len(records)}",
        f"Total issues:      {total_issues}",
        "",
        "By type:",
        *[f"  {t:<25} {c}" for t, c in type_counts.most_common()],
        "",
        "By language:",
        *[f"  {l:<6} {c}" for l, c in lang_counts.most_common()],
        "",
        "By severity:",
        *[f"  {s:<10} {c}" for s, c in sev_counts.most_common()],
        "",
        "By repair type:",
        *[f"  {r:<20} {c}" for r, c in repair_counts.most_common()],
    ]
    report = "\n".join(lines)
    print(report)
    SUMMARY_FILE.write_text(report)
    print(f"\nSummary written: {SUMMARY_FILE}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    run_p = sub.add_parser("run")
    run_p.add_argument("--local",    action="store_true", help="Use local LM Studio")
    run_p.add_argument("--no-llm",   action="store_true", help="Programmatic pass only")
    run_p.add_argument("--endpoint", help="Override LM Studio URL")
    run_p.add_argument("--model",    help="Override model name")
    run_p.add_argument("--label",    help="Audit one concept only")
    run_p.add_argument("--workers",  type=int, default=4)
    run_p.add_argument("--force",    action="store_true",
                       help="Re-audit already-logged files")

    sub.add_parser("report")

    args = ap.parse_args()
    if args.cmd == "run":
        cmd_run(args)
    elif args.cmd == "report":
        cmd_report(args)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()

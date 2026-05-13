#!/usr/bin/env python3
"""
Direct formatting repair via OpenRouter API.
No shared progress file — reads queue, deduplicates, processes N from remaining.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import urllib.request
import urllib.error
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
QUEUE_PATH = REPO_ROOT / "training_data/phases/repair_formatting.txt"
DEBUG_DIR = REPO_ROOT / "tmp/formatting_direct_debug"
MODEL = "deepseek/deepseek-v4-flash"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
PRINT_LOCK = threading.Lock()


def log(msg: str) -> None:
    with PRINT_LOCK:
        print(msg, flush=True)


def parse_queue() -> list[dict]:
    entries: OrderedDict[str, dict] = OrderedDict()
    for line in QUEUE_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if ".md" not in line or "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|", 2)]
        if len(parts) != 3:
            continue
        path_str, issue_type, reason = parts
        entry = entries.setdefault(path_str, {"path": path_str, "reasons": []})
        entry["reasons"].append(reason)
    return list(entries.values())


def read_file(path_str: str) -> str:
    return (REPO_ROOT / path_str).read_text(encoding="utf-8")


def verify_rewrite(path_str: str, content: str) -> None:
    if "[user]" not in content or "[Ninereeds]" not in content:
        raise RuntimeError(f"missing required tags")
    if "```" in content:
        raise RuntimeError(f"stray code fence")
    if len(content.strip()) < 40:
        raise RuntimeError(f"content too short")
    lines = content.splitlines()
    blocks: list[list[str]] = []
    cur: list[str] = []
    for line in lines:
        if not line.strip():
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(line)
    if cur:
        blocks.append(cur)
    if not blocks:
        raise RuntimeError(f"no content blocks")
    for bi, block in enumerate(blocks, 1):
        if len(block) < 3:
            raise RuntimeError(f"block {bi} too short")
        if not block[0].startswith("[user]") or not block[1].startswith("[Ninereeds]"):
            raise RuntimeError(f"block {bi} missing standard headers")
        if block[1].count(".") != 1:
            raise RuntimeError(f"block {bi} opener must be 1 sentence")
        for line in block[2:]:
            if line.startswith("[user]") or line.startswith("[Ninereeds]"):
                raise RuntimeError(f"block {bi} nested tags")
            if line.count(".") != 1:
                raise RuntimeError(f"content line must be 1 sentence")


def call_api(prompt: str, timeout: int) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.3,
    }).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API {exc.code}: {body[:300]}") from exc
    data = json.loads(resp.read().decode("utf-8"))
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError(f"empty API response: {json.dumps(data)[:300]}")
    return content.strip()


def normalize(text: str) -> str:
    if "[user]" in text:
        text = text[text.index("[user]"):]
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    lines = [l for l in text.splitlines() if l.strip() not in {"=== END ===", "```", "--- BEGIN ---", "--- END ---"}]
    return "\n".join(lines).strip() + "\n"


def build_prompt(entry: dict, retry: bool = False) -> str:
    path_str = entry["path"]
    current = read_file(path_str)
    reasons = "\n".join(f"- {r}" for r in entry["reasons"])
    retry_note = ""
    extra_example = ""
    if retry:
        retry_note = (
            "Previous attempt returned non-file output.\n"
            "Return only the rewritten file text. Do not echo the prompt.\n"
            "Every [user] block must have exactly one [Ninereeds] response line that opens with 'This is'.\n"
            "Each [Ninereeds] block must have 5 body lines (each 1 sentence) + 1 summary line combining two properties.\n"
        )
        extra_example = (
            "\nExpected format per block:\n"
            "[user]What does X look like?\n"
            "[Ninereeds]This is X.\n"
            "<5 body lines, each 1 sentence>\n"
            "<summary: X is <prop1> and <prop2>.>\n"
        )
    return f"""{retry_note}Repair the target file to match Ninereeds training-file format.

Rules:
- Output ONLY the corrected file text. No commentary. No BEGIN/END markers.
- Fix all listed issues in one pass.
- Use concrete, grammatical English.
- Keep one sentence per line.
- Every block: [user] question, then [Ninereeds] opener "This is X.", then 5 body lines (1 sentence each), then 1 summary line combining two properties.
- [Ninereeds] tag appears only on the opener line, not on body lines.
- Preserve [user] / [Ninereeds] training-pair format.{extra_example}

Target: {path_str}
Issues:
{reasons}

Current content:
--- BEGIN ---
{current}
--- END ---"""


def process(entry: dict, timeout: int) -> tuple[str, str]:
    path_str = entry["path"]
    last_error: Exception | None = None
    responses: list[str] = []
    for attempt in range(2):
        prompt = build_prompt(entry, retry=(attempt > 0))
        try:
            response = call_api(prompt, timeout)
            responses.append(response)
            new_content = normalize(response)
            verify_rewrite(path_str, new_content)
            path = REPO_ROOT / path_str
            path.write_text(new_content, encoding="utf-8")
            return path_str, "ok"
        except Exception as exc:
            last_error = exc
    if last_error:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        for i, resp in enumerate(responses):
            (DEBUG_DIR / f"{Path(path_str).name}.attempt{i}.txt").write_text(resp or "(empty)", encoding="utf-8")
        raise last_error
    return path_str, "ok"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=6)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--skip", type=int, default=0, help="Skip first N queue entries")
    args = parser.parse_args()

    all_entries = parse_queue()
    batch = all_entries[args.skip:args.skip + args.batch]
    processed: list[str] = []
    blockers: list[str] = []

    if not batch:
        remaining = len(all_entries) - args.skip
        log(f"No files in this batch. Queue total: {len(all_entries)}, skipped: {args.skip}, remaining: {remaining}")
        log("RECEIPT")
        log("-------")
        log(f"Status: DONE" if remaining <= 0 else f"Status: IN_PROGRESS (need --skip {args.skip} to continue)")
        return 0

    import concurrent.futures
    log(f"Processing {len(batch)} file(s), starting at offset {args.skip}, timeout {args.timeout}s")
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(batch)) as pool:
        futmap = {pool.submit(process, e, args.timeout): e for e in batch}
        for fut in concurrent.futures.as_completed(futmap):
            e = futmap[fut]
            try:
                p, _ = fut.result()
                processed.append(p)
                log(f"OK {p}")
            except Exception as exc:
                blockers.append(f"{e['path']}: {exc}")
                log(f"FAILED {e['path']}: {exc}")

    remaining = len(all_entries) - args.skip - len(processed)
    status = "DONE" if remaining <= 0 and not blockers else "IN_PROGRESS"
    if blockers:
        status = "BLOCKED"
    log("")
    log("RECEIPT")
    log("-------")
    log(f"Files processed this run: {processed}")
    log(f"Total queue: {len(all_entries)}, skip offset: {args.skip}")
    log(f"Files remaining: {remaining}")
    log(f"Next command: python3 {Path(__file__).name} --batch {args.batch} --skip {args.skip + len(processed)}")
    log(f"Status: {status}")
    if blockers:
        log(f"Blockers: {' || '.join(blockers)}")
    return 0 if status != "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Audit vignette files for semantic integrity and language quality.

Sends each v_*.md file to the LLM with a structured audit prompt.
NIM is primary (leaving OpenRouter for the generator); OR is fallback.

Results are appended to _audit.jsonl one record per file so the run is
resumable — already-audited files are skipped on re-run.

Usage:
  python3 meta/scripts/vignette_audit.py gen  [--workers 4] [--batch N]
  python3 meta/scripts/vignette_audit.py status
  python3 meta/scripts/vignette_audit.py report [--fail-only]
"""

from __future__ import annotations
import argparse, concurrent.futures, json, os, pathlib, re, sys, time

ROOT    = pathlib.Path(__file__).resolve().parents[2]
VIG_DIR = ROOT / "training_data" / "01_language" / "vignettes"
AUDIT_F = VIG_DIR / "_audit.jsonl"
FAIL_F  = VIG_DIR / "_audit_failures.txt"

# ── API ───────────────────────────────────────────────────────────────────────

def _read_dotenv() -> dict:
    env: dict[str, str] = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

_dotenv = _read_dotenv()

def _get(key: str) -> str | None:
    return os.environ.get(key) or _dotenv.get(key)

def _make_client(key: str, base_url: str):
    from openai import OpenAI
    k = _get(key)
    if not k:
        return None
    return OpenAI(api_key=k, base_url=base_url)

def _sources():
    src = []
    ds = _make_client("DEEPSEEK_API_KEY", "https://api.deepseek.com/v1")
    if ds:
        src.append((ds, "deepseek-chat", {}))
    nim = _make_client("NVIDIA_API_KEY", "https://integrate.api.nvidia.com/v1")
    if nim:
        src.append((nim, "deepseek-ai/deepseek-v4-pro",
                    {"extra_body": {"chat_template_kwargs": {"thinking": False}}}))
    orc = _make_client("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1")
    if orc:
        src.append((orc, "deepseek/deepseek-v4-flash", {}))
    return src

SOURCES = _sources()

def call_api(system: str, user: str) -> tuple[str, str]:
    if not SOURCES:
        raise RuntimeError("No API key found. Set NVIDIA_API_KEY or OPENROUTER_API_KEY.")
    last_err = None
    for attempt in range(5):
        for client, model, extra in SOURCES:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user},
                    ],
                    max_tokens=3000,
                    temperature=0.1,
                    **extra,
                )
                content = resp.choices[0].message.content
                if content and content.strip():
                    return content.strip(), model
            except Exception as e:
                last_err = e
        if "429" in str(last_err):
            wait = 10 * (2 ** attempt)
            time.sleep(wait)
    raise RuntimeError(f"All API sources failed after retries: {last_err}")

# ── Audit prompt ──────────────────────────────────────────────────────────────

AUDIT_SYSTEM = """\
You are auditing multilingual vignette training files for a language-learning model.

Each vignette has 5 blocks. Each block expresses the same event in 4 languages from a
different grammatical angle (active, passive, topicalized, paraphrase, question).
Languages may appear in any order within a block.

Your job: determine whether all 5 blocks preserve the same underlying event, roles, and
lexical meaning, and whether the language in each block is grammatically correct.

THINK through the scene graph mentally for each block (agent, patient, recipient, action).
Do NOT write out the scene graphs in your response.

OUTPUT your response in exactly this format and nothing else:

EVENT_PRESERVED: PASS|FAIL
ROLE_PRESERVED: PASS|FAIL
LEXICAL_DRIFT: PASS|FAIL
GERMAN_CASES: PASS|FAIL
QUESTION_CONSISTENCY: PASS|FAIL
LANGUAGE_IDENTIFICATION: PASS|FAIL

GRAMMATICALITY:
EN: PASS|FAIL
DE: PASS|FAIL
JP: PASS|FAIL
ZH: PASS|FAIL

NATURALNESS:
EN: PASS|MINOR_AWKWARDNESS|FAIL
DE: PASS|MINOR_AWKWARDNESS|FAIL
JP: PASS|MINOR_AWKWARDNESS|FAIL
ZH: PASS|MINOR_AWKWARDNESS|FAIL

OVERALL: PASS|FAIL

If OVERALL is FAIL, add one sentence explaining which block and what failed.

Definitions:
- EVENT_PRESERVED: all blocks describe the same action between the same parties
- ROLE_PRESERVED: agent/patient/recipient/possessor are the same across all blocks
- LEXICAL_DRIFT: FAIL if any block substitutes a verb that changes the event type
  (tear≠cut, push≠roll, store≠hold, buy≠receive — same motion/action type required)
- GERMAN_CASES: nominative subjects, accusative objects, dative recipients, genitive possessors
- QUESTION_CONSISTENCY: if a block is a question, the implied answer matches the scene
- LANGUAGE_IDENTIFICATION: each line is in the expected language with no mixing\
"""

# ── Output parsing ────────────────────────────────────────────────────────────

_BOOL_FIELDS = [
    "EVENT_PRESERVED", "ROLE_PRESERVED", "LEXICAL_DRIFT",
    "GERMAN_CASES", "QUESTION_CONSISTENCY", "LANGUAGE_IDENTIFICATION",
]
_LANG_KEYS = ["EN", "DE", "JP", "ZH"]


def parse_audit(text: str) -> dict:
    """Parse structured audit output. Missing fields → None."""
    result: dict = {}

    for field in _BOOL_FIELDS:
        m = re.search(rf"^{field}:\s*(PASS|FAIL)", text, re.MULTILINE | re.IGNORECASE)
        result[field.lower()] = m.group(1).upper() if m else None

    # GRAMMATICALITY sub-block
    gram: dict = {}
    gram_m = re.search(
        r"GRAMMATICALITY:\s*\n(.*?)(?=\n\s*\n|\nNATURALNESS:|\nOVERALL:)",
        text, re.DOTALL,
    )
    if gram_m:
        block = gram_m.group(1)
        for lang in _LANG_KEYS:
            m = re.search(rf"^{lang}:\s*(PASS|FAIL)", block, re.MULTILINE | re.IGNORECASE)
            gram[lang.lower()] = m.group(1).upper() if m else None
    result["grammaticality"] = gram

    # NATURALNESS sub-block
    nat: dict = {}
    nat_m = re.search(
        r"NATURALNESS:\s*\n(.*?)(?=\n\s*\n|\nOVERALL:)",
        text, re.DOTALL,
    )
    if nat_m:
        block = nat_m.group(1)
        for lang in _LANG_KEYS:
            m = re.search(
                rf"^{lang}:\s*(PASS|MINOR_AWKWARDNESS|FAIL)",
                block, re.MULTILINE | re.IGNORECASE,
            )
            nat[lang.lower()] = m.group(1).upper() if m else None
    result["naturalness"] = nat

    # OVERALL
    m = re.search(r"^OVERALL:\s*(PASS|FAIL)", text, re.MULTILINE | re.IGNORECASE)
    result["overall"] = m.group(1).upper() if m else None

    # Explanation (text following OVERALL: FAIL)
    m_fail = re.search(r"^OVERALL:\s*FAIL\s*\n+(.*)", text, re.MULTILINE | re.DOTALL)
    if m_fail:
        expl = m_fail.group(1).strip()
        result["explanation"] = expl or None
    else:
        result["explanation"] = None

    return result

# ── Audit state ───────────────────────────────────────────────────────────────

def load_done() -> set[str]:
    if not AUDIT_F.exists():
        return set()
    done: set[str] = set()
    for line in AUDIT_F.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                done.add(json.loads(line)["file"])
            except Exception:
                pass
    return done


def append_result(rec: dict) -> None:
    with AUDIT_F.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def update_failures() -> None:
    fails: list[str] = []
    if AUDIT_F.exists():
        for line in AUDIT_F.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rec = json.loads(line)
                    if rec.get("overall") == "FAIL":
                        fails.append(rec["file"])
                except Exception:
                    pass
    FAIL_F.write_text(
        "\n".join(sorted(fails)) + ("\n" if fails else ""),
        encoding="utf-8",
    )

# ── Single file audit ─────────────────────────────────────────────────────────

def audit_file(fname: str) -> dict:
    path = VIG_DIR / fname
    text = path.read_text(encoding="utf-8").strip()
    user_msg = f"Audit this vignette:\n\n{text}"
    try:
        raw, model = call_api(AUDIT_SYSTEM, user_msg)
        parsed = parse_audit(raw)
        rec: dict = {"file": fname, "model": model}
        rec.update(parsed)
        return rec
    except Exception as e:
        return {"file": fname, "model": None, "overall": None, "error": str(e)}

# ── gen ───────────────────────────────────────────────────────────────────────

def gen(workers: int = 4, batch: int = 0) -> None:
    VIG_DIR.mkdir(parents=True, exist_ok=True)
    all_files = sorted(p.name for p in VIG_DIR.glob("v_*.md"))
    done      = load_done()
    pending   = [f for f in all_files if f not in done]
    if batch > 0:
        pending = pending[:batch]

    if not pending:
        print("Nothing to audit — all files done.")
        return

    print(f"Pending: {len(pending)} / {len(all_files)}  (done: {len(done)})")
    print(f"Workers: {workers}\n")

    fail_count = 0

    def _print(fname: str, rec: dict) -> None:
        nonlocal fail_count
        overall = rec.get("overall") or "error"
        err_note = f" — {rec.get('error','')[:80]}" if "error" in rec else ""
        expl = rec.get("explanation") or ""
        expl_short = f" | {expl[:60]}…" if len(expl) > 60 else (f" | {expl}" if expl else "")
        print(f"  {fname}  {overall}{err_note}{expl_short}", flush=True)
        if overall == "FAIL":
            fail_count += 1

    if workers == 1:
        for fname in pending:
            rec = audit_file(fname)
            append_result(rec)
            _print(fname, rec)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(audit_file, f): f for f in pending}
            for fut in concurrent.futures.as_completed(futs):
                fname = futs[fut]
                rec = fut.result()
                append_result(rec)
                _print(fname, rec)

    update_failures()
    print(f"\nThis run: {fail_count} FAIL out of {len(pending)} audited")
    if fail_count:
        print(f"Failures written to {FAIL_F.relative_to(ROOT)}")

# ── status ────────────────────────────────────────────────────────────────────

def status() -> None:
    all_files = sorted(p.name for p in VIG_DIR.glob("v_*.md"))
    if not all_files:
        print("No vignette files found.")
        return

    done    = load_done()
    pending = [f for f in all_files if f not in done]

    records: list[dict] = []
    if AUDIT_F.exists():
        for line in AUDIT_F.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass

    pass_n = sum(1 for r in records if r.get("overall") == "PASS")
    fail_n = sum(1 for r in records if r.get("overall") == "FAIL")
    err_n  = sum(1 for r in records if r.get("overall") is None)

    print(f"Vignette files : {len(all_files)}")
    print(f"Audited        : {len(done)}  (PASS: {pass_n}, FAIL: {fail_n}, error: {err_n})")
    print(f"Pending        : {len(pending)}")
    if pending:
        print(f"\nRun: python3 meta/scripts/vignette_audit.py gen --workers 4")

# ── report ────────────────────────────────────────────────────────────────────

def report(fail_only: bool = False) -> None:
    if not AUDIT_F.exists():
        print("No audit results yet.")
        return

    records: list[dict] = []
    for line in AUDIT_F.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                records.append(json.loads(line))
            except Exception:
                pass

    if not records:
        print("No results to report.")
        return

    total  = len(records)
    passes = [r for r in records if r.get("overall") == "PASS"]
    fails  = [r for r in records if r.get("overall") == "FAIL"]
    errs   = [r for r in records if r.get("overall") is None]

    pct = lambda n: f"{100*n//total}%" if total else "0%"
    print(f"Audit results: {total} files")
    print(f"  PASS  : {len(passes)} ({pct(len(passes))})")
    print(f"  FAIL  : {len(fails)} ({pct(len(fails))})")
    print(f"  error : {len(errs)}")

    if fails:
        cats = [
            "event_preserved", "role_preserved", "lexical_drift",
            "german_cases", "question_consistency", "language_identification",
        ]
        print("\nFailure breakdown (FAIL files only):")
        for cat in cats:
            n = sum(1 for r in fails if r.get(cat) == "FAIL")
            if n:
                print(f"  {cat:<32} {n}")
        for section, label in [("grammaticality", "grammaticality FAIL"), ("naturalness", "naturalness FAIL")]:
            header_printed = False
            for lang in ["en", "de", "jp", "zh"]:
                n = sum(1 for r in fails if r.get(section, {}).get(lang) == "FAIL")
                if n:
                    if not header_printed:
                        print(f"  {label}:")
                        header_printed = True
                    print(f"    {lang.upper():<4} {n}")

        print(f"\nFailed files:")
        for r in fails:
            expl = r.get("explanation") or ""
            expl_short = (expl[:80] + "…") if len(expl) > 80 else expl
            print(f"  {r['file']}  {expl_short}")

    if errs and not fail_only:
        print(f"\nErrors ({len(errs)}):")
        for r in errs:
            print(f"  {r['file']}  {r.get('error','')[:80]}")

# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Vignette semantic auditor")
    sub = ap.add_subparsers(dest="cmd")

    p_gen = sub.add_parser("gen", help="Run audit on pending files")
    p_gen.add_argument("--workers", type=int, default=4)
    p_gen.add_argument("--batch",   type=int, default=0,
                       help="Limit to N files this run (0 = all pending)")

    sub.add_parser("status", help="Show audit progress")

    p_rep = sub.add_parser("report", help="Show audit summary")
    p_rep.add_argument("--fail-only", action="store_true",
                       help="Skip the error section")

    args = ap.parse_args()

    if args.cmd == "gen":
        gen(workers=args.workers, batch=args.batch)
    elif args.cmd == "status":
        status()
    elif args.cmd == "report":
        report(fail_only=args.fail_only)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()

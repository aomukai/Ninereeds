#!/usr/bin/env python3
"""Generate and assemble the Ninereeds kernel corpus.

The generator is intentionally separate from redesign angle generation. It writes
to training_data/kernel/ and uses its own progress files.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any

from openai import OpenAI, RateLimitError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
WORDS_FILE = ROOT / "training" / "corpus_admin" / "kernel" / "kernel_words.jsonl"
OUT_ROOT = ROOT / "training_data" / "kernel"
CLAIMS_DIR = OUT_ROOT / "claims"
PROGRESS_DIR = OUT_ROOT / "progress"
DONE_FILE = PROGRESS_DIR / "done.txt"
FAILED_FILE = PROGRESS_DIR / "failed.txt"
LOG_FILE = ROOT / "tmp" / "kernel_gen.log"

SOURCES: dict[str, dict[str, Any]] = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "deepseek/deepseek-v4-flash",
        "api_key_env": "OPENROUTER_API_KEY",
        "max_tokens": 12000,
        "extra_body": {},
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
        "max_tokens": 6000,
        "extra_body": {},
    },
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "model": "deepseek-ai/deepseek-v4-flash",
        "api_key_env": "NVIDIA_API_KEY",
        "max_tokens": 12000,
        "extra_body": {"chat_template_kwargs": {"thinking": False}},
    },
}

RATE_LIMIT_WAITS = [30, 90, 180]
MAX_ATTEMPTS = 3
REQUIRED_FILES = {
    "what_is",
    "classification",
    "properties",
    "behavior",
    "location",
    "connections",
    "negative_category",
    "negative_part",
    "yes_no_true",
    "yes_no_false",
    "unknown_name",
    "unknown_internal",
    "followup_known",
    "followup_unknown",
}

_lock = threading.Lock()


def load_env(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    with _lock:
        print(line, flush=True)
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with LOG_FILE.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except Exception:
            pass


def configure_paths(args: argparse.Namespace) -> None:
    global WORDS_FILE, OUT_ROOT, CLAIMS_DIR, PROGRESS_DIR, DONE_FILE, FAILED_FILE
    if getattr(args, "words_file", None):
        WORDS_FILE = args.words_file if args.words_file.is_absolute() else ROOT / args.words_file
    if getattr(args, "out_root", None):
        OUT_ROOT = args.out_root if args.out_root.is_absolute() else ROOT / args.out_root
    CLAIMS_DIR = OUT_ROOT / "claims"
    PROGRESS_DIR = OUT_ROOT / "progress"
    DONE_FILE = PROGRESS_DIR / "done.txt"
    FAILED_FILE = PROGRESS_DIR / "failed.txt"


def load_concepts(limit: int | None = None) -> list[dict[str, Any]]:
    concepts: list[dict[str, Any]] = []
    with WORDS_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                concepts.append(json.loads(line))
    return concepts[:limit] if limit else concepts


def load_set(path: Path) -> set[str]:
    if path.exists():
        return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}
    return set()


def append_to(path: Path, entry: str) -> None:
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(entry + "\n")


def safe_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def concept_dir(concept: dict[str, Any]) -> Path:
    return OUT_ROOT / str(concept.get("category", "unsorted")) / safe_name(str(concept["concept_id"]))


def try_claim(concept_id: str) -> bool:
    CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        (CLAIMS_DIR / f"{safe_name(concept_id)}.claim").open("x").close()
        return True
    except FileExistsError:
        return False


def release_claim(concept_id: str) -> None:
    try:
        (CLAIMS_DIR / f"{safe_name(concept_id)}.claim").unlink()
    except FileNotFoundError:
        pass


SYSTEM_PROMPT = """\
You create training data for Ninereeds, a small language model.

Write short, literal, grounded chat examples. The goal is concept binding, not prose.

Hard rules:
- Use only [user] and [Ninereeds] tags.
- One file may contain 1 to 4 exchanges.
- Responses must be short, direct, and factual.
- Prefer repeated concept names over pronouns.
- Do not add markdown fences.
- Do not add commentary outside file blocks.
- Do not invent obscure facts.
- Include negative controls and unknown boundaries.
- Unknown boundaries are for specific missing facts, not for general facts the model should know.
- Every answer must be safe for a young child and easy for a byte-level model to learn.
"""


USER_PROMPT = """\
Generate the kernel corpus files for this concept:

{concept_json}

Required output files:
{required_files}

Use this exact delimiter for each file:

=== FILE: ANGLE.md ===
[user]...
[Ninereeds]...

Filename rules:
- Replace ANGLE with one required output file name exactly.
- Do not include the concept name in the filename.
- Produce all required files.

Content rules:
- The concept is "{concept_id}".
- If positive facts are provided, use them as the main known facts.
- If positive facts are missing or sparse, infer simple common facts suitable for a young child.
- If negative facts are provided, use them for false-category and false-part questions.
- If negative facts are missing, choose obvious false categories or false properties.
- If unknown facts are provided, use them for "I don't know" boundaries.
- If unknown facts are missing, use specific missing details such as a name, exact count, exact location, exact origin, exact owner, current feeling, or private thought.
- For connections, explicitly list related concepts and categories.
- For yes_no_true, ask a true yes/no question and answer "Yes."
- For yes_no_false, ask a false yes/no question and answer "No." with correction.
- For followup_known, make a 2 or 3 turn chat where the user asks "what else?"
- For followup_unknown, make a 2 or 3 turn chat where the user asks a missing specific fact.
- Keep every response 1 to 4 short sentences.
- Avoid contractions.
- Avoid poetic wording.
- Avoid long explanations.
"""


FILE_RE = re.compile(r"=== FILE: ([^\n=]+\.md) ===\n(.*?)(?==== FILE:|$)", re.DOTALL)


def parse_files(raw: str) -> dict[str, str]:
    files: dict[str, str] = {}
    for match in FILE_RE.finditer(raw):
        name = match.group(1).strip()
        content = match.group(2).strip()
        if name and content:
            files[name] = content
    return files


def validate_content(content: str) -> list[str]:
    issues: list[str] = []
    user_count = len(re.findall(r"^\[user\]", content, re.MULTILINE))
    nr_count = len(re.findall(r"^\[Ninereeds\]", content, re.MULTILINE))
    if user_count == 0:
        issues.append("no [user] tags")
    if user_count != nr_count:
        issues.append(f"mismatched turns: {user_count} user vs {nr_count} Ninereeds")
    if "```" in content:
        issues.append("markdown fence present")
    return issues


def normalize_files(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for filename, content in files.items():
        angle = Path(filename).stem
        angle = safe_name(angle)
        normalized[f"{angle}.md"] = content.strip() + "\n"
    return normalized


def required_for_concept(concept: dict[str, Any]) -> set[str]:
    raw = concept.get("missing_angles") or concept.get("required_angles")
    if raw:
        return {safe_name(str(item)) for item in raw}
    return set(REQUIRED_FILES)


def missing_required(files: dict[str, str], required: set[str] | None = None) -> set[str]:
    required = required or REQUIRED_FILES
    angles = {Path(name).stem for name in files}
    return required - angles


def generate_one(client: OpenAI, source: str, concept: dict[str, Any], max_tokens: int, extra_body: dict[str, Any]) -> bool:
    concept_id = str(concept["concept_id"])
    required = required_for_concept(concept)
    required_files = "\n".join(f"- {item}" for item in sorted(required))
    prompt = USER_PROMPT.format(
        concept_json=json.dumps(concept, ensure_ascii=False, indent=2),
        concept_id=concept_id,
        required_files=required_files,
    )
    attempts = 0
    rate_hits = 0
    while attempts < MAX_ATTEMPTS:
        try:
            kwargs: dict[str, Any] = {
                "model": client.model,  # type: ignore[attr-defined]
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.4,
            }
            if extra_body:
                kwargs["extra_body"] = extra_body
            response = client.chat.completions.create(**kwargs)
            raw = response.choices[0].message.content or ""
            files = normalize_files(parse_files(raw))
            if not files:
                log(f"WARN [{source}:{concept_id}] no files parsed")
                attempts += 1
                continue
            missing = missing_required(files, required)
            bad: list[str] = []
            for filename, content in files.items():
                issues = validate_content(content)
                if issues:
                    bad.append(f"{filename}: {issues}")
            if missing or bad:
                log(f"WARN [{source}:{concept_id}] missing={sorted(missing)} bad={bad[:3]}")
                attempts += 1
                continue
            out_dir = concept_dir(concept)
            out_dir.mkdir(parents=True, exist_ok=True)
            meta = {
                "concept": concept,
                "source": source,
                "model": client.model,  # type: ignore[attr-defined]
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }
            (out_dir / "_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            for filename, content in files.items():
                (out_dir / filename).write_text(content, encoding="utf-8")
            log(f"OK   [{source}:{concept_id}] {len(files)} files -> {out_dir.relative_to(ROOT)}")
            return True
        except RateLimitError:
            if rate_hits >= len(RATE_LIMIT_WAITS):
                log(f"FAIL [{source}:{concept_id}] rate limited too often")
                return False
            wait = RATE_LIMIT_WAITS[rate_hits]
            rate_hits += 1
            log(f"RATE [{source}:{concept_id}] waiting {wait}s")
            time.sleep(wait)
        except Exception as exc:
            log(f"ERR  [{source}:{concept_id}] {exc}")
            attempts += 1
    log(f"FAIL [{source}:{concept_id}] attempts exhausted")
    return False


def cmd_gen(args: argparse.Namespace) -> None:
    configure_paths(args)
    load_env()
    cfg = SOURCES[args.source]
    model = args.model or cfg["model"]
    api_key = os.environ.get(cfg["api_key_env"], "")
    if not api_key:
        raise SystemExit(f"{cfg['api_key_env']} is not set")

    concepts = load_concepts(args.limit)
    done = load_set(DONE_FILE)
    failed = set() if args.retry_failed else load_set(FAILED_FILE)
    queue = [item for item in concepts if str(item["concept_id"]) not in done | failed]
    if args.batch:
        queue = queue[: args.batch]
    log(f"{args.source}: total={len(concepts)} done={len(done)} failed={len(failed)} queue={len(queue)} model={model}")
    if not queue:
        return

    client = OpenAI(api_key=api_key, base_url=cfg["base_url"], timeout=180.0)
    client.model = model  # type: ignore[attr-defined]

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures: dict[Future[bool], str] = {}
        cursor = 0

        def submit_until_full() -> None:
            nonlocal cursor
            while len(futures) < args.workers and cursor < len(queue):
                concept = queue[cursor]
                cursor += 1
                concept_id = str(concept["concept_id"])
                if not try_claim(concept_id):
                    log(f"SKIP [{args.source}:{concept_id}] claimed")
                    continue
                fut = pool.submit(
                    generate_one,
                    client,
                    args.source,
                    concept,
                    cfg["max_tokens"],
                    cfg.get("extra_body", {}),
                )
                futures[fut] = concept_id

        submit_until_full()
        while futures:
            completed, _pending = wait(futures, return_when=FIRST_COMPLETED)
            for fut in completed:
                concept_id = futures.pop(fut)
                try:
                    ok = fut.result()
                finally:
                    release_claim(concept_id)
                if ok:
                    append_to(DONE_FILE, concept_id)
                else:
                    append_to(FAILED_FILE, concept_id)
            submit_until_full()


def iter_kernel_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(OUT_ROOT.rglob("*.md")):
        if any(part in {"claims", "progress"} for part in path.parts):
            continue
        files.append(path)
    return files


def cmd_report(_args: argparse.Namespace) -> None:
    configure_paths(_args)
    concepts = load_concepts()
    done = load_set(DONE_FILE)
    failed = load_set(FAILED_FILE)
    claims = list(CLAIMS_DIR.glob("*.claim")) if CLAIMS_DIR.exists() else []
    files = iter_kernel_files()
    print(f"Concepts total: {len(concepts)}")
    print(f"Done:           {len(done)}")
    print(f"Failed:         {len(failed)}")
    print(f"Claims:         {len(claims)}")
    print(f"Files:          {len(files)}")
    for category in sorted({str(item["category"]) for item in concepts}):
        count = len(list((OUT_ROOT / category).rglob("*.md"))) if (OUT_ROOT / category).exists() else 0
        print(f"  {category:12s} {count:4d}")
    remaining = [str(item["concept_id"]) for item in concepts if str(item["concept_id"]) not in done | failed]
    if remaining:
        print("Next:", ", ".join(remaining[:20]))


def cmd_validate(_args: argparse.Namespace) -> None:
    configure_paths(_args)
    files = iter_kernel_files()
    issues: list[str] = []
    for path in files:
        content = path.read_text(encoding="utf-8", errors="replace")
        for issue in validate_content(content):
            issues.append(f"{path.relative_to(ROOT)}: {issue}")
    if issues:
        for issue in issues[:200]:
            print(issue)
        raise SystemExit(f"Validation failed: {len(issues)} issue(s)")
    print(f"OK: {len(files)} kernel files")


def cmd_build(args: argparse.Namespace) -> None:
    configure_paths(args)
    files = iter_kernel_files()
    if not files:
        raise SystemExit("No kernel files found. Generate first.")
    parts: list[str] = []
    manifest: list[str] = []
    for path in files:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            continue
        for issue in validate_content(content):
            raise SystemExit(f"{path.relative_to(ROOT)}: {issue}")
        rel = path.relative_to(ROOT).as_posix()
        repeat = repeat_for_path(args, rel)
        for _ in range(repeat):
            parts.append(content)
            manifest.append(rel)
    corpus = "\n\n".join(parts) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(corpus, encoding="utf-8")
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text("\n".join(manifest) + "\n", encoding="utf-8")
    report = [
        "# Kernel Corpus Build",
        "",
        f"- source_files: {len(files)}",
        f"- training_records_after_repeat: {len(parts)}",
        f"- bytes: {len(corpus.encode('utf-8'))}",
        f"- output: `{args.output}`",
        f"- manifest: `{args.manifest}`",
        "",
    ]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(report), encoding="utf-8")
    print(f"Corpus:   {args.output} ({len(parts)} records)")
    print(f"Manifest: {args.manifest}")
    print(f"Report:   {args.report}")


TURN_RE = re.compile(r"^\[user\](.*?)\n\[Ninereeds\](.*?)(?=\n\[user\]|\Z)", re.DOTALL | re.MULTILINE)


def lowercase_user_prompt(prompt: str) -> str:
    lines = prompt.splitlines()
    out: list[str] = []
    for line in lines:
        if line.startswith("[user]"):
            out.append("[user]" + line[len("[user]") :].lower())
        else:
            out.append(line)
    return "\n".join(out)


def parse_turn_examples(content: str) -> list[tuple[str, str]]:
    """Return growing-context prompt/completion examples from a dialogue file."""
    examples: list[tuple[str, str]] = []
    history = ""
    for match in TURN_RE.finditer(content.strip()):
        user_text = match.group(1).strip()
        answer = match.group(2).strip()
        if not user_text or not answer:
            continue
        prompt = history + f"[user]{user_text}\n[Ninereeds]"
        completion = answer
        examples.append((prompt, completion))
        history = prompt + completion + "\n"
    return examples


def repeat_for_path(args: argparse.Namespace, rel: str) -> int:
    identity_paths = getattr(args, "repeat_identity_path", None) or []
    if any(marker and marker in rel for marker in identity_paths):
        return args.repeat_identity
    return args.repeat_kernel


def cmd_build_jsonl(args: argparse.Namespace) -> None:
    configure_paths(args)
    files = iter_kernel_files()
    if not files:
        raise SystemExit("No kernel files found. Generate first.")

    records: list[dict[str, str]] = []
    for path in files:
        content = path.read_text(encoding="utf-8").strip()
        rel = path.relative_to(ROOT).as_posix()
        repeat = repeat_for_path(args, rel)
        for prompt, completion in parse_turn_examples(content):
            for _ in range(repeat):
                records.append({"prompt": prompt, "completion": completion})
                if args.lowercase_user_copy:
                    lower_prompt = lowercase_user_prompt(prompt)
                    if lower_prompt != prompt:
                        records.append({"prompt": lower_prompt, "completion": completion})

    if not records:
        raise SystemExit("No JSONL examples parsed.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    report = [
        "# Kernel JSONL Build",
        "",
        f"- source_files: {len(files)}",
        f"- examples: {len(records)}",
        f"- lowercase_user_copy: {args.lowercase_user_copy}",
        f"- output: `{args.output}`",
        "",
    ]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(report), encoding="utf-8")
    print(f"JSONL:  {args.output} ({len(records)} examples)")
    print(f"Report: {args.report}")


def cmd_clean_claims(_args: argparse.Namespace) -> None:
    configure_paths(_args)
    removed = 0
    if CLAIMS_DIR.exists():
        for path in CLAIMS_DIR.glob("*.claim"):
            path.unlink()
            removed += 1
    print(f"Removed {removed} claims")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate/build Ninereeds kernel corpus")
    sub = parser.add_subparsers(dest="cmd")

    gen = sub.add_parser("gen")
    gen.add_argument("--source", choices=list(SOURCES), required=True)
    gen.add_argument("--words-file", type=Path, default=WORDS_FILE)
    gen.add_argument("--out-root", type=Path, default=OUT_ROOT)
    gen.add_argument("--model", default=None)
    gen.add_argument("--workers", type=int, default=2)
    gen.add_argument("--batch", type=int, default=None)
    gen.add_argument("--limit", type=int, default=None)
    gen.add_argument("--retry-failed", action="store_true")

    report_cmd = sub.add_parser("report")
    report_cmd.add_argument("--words-file", type=Path, default=WORDS_FILE)
    report_cmd.add_argument("--out-root", type=Path, default=OUT_ROOT)

    validate_cmd = sub.add_parser("validate")
    validate_cmd.add_argument("--words-file", type=Path, default=WORDS_FILE)
    validate_cmd.add_argument("--out-root", type=Path, default=OUT_ROOT)

    clean_cmd = sub.add_parser("clean-claims")
    clean_cmd.add_argument("--words-file", type=Path, default=WORDS_FILE)
    clean_cmd.add_argument("--out-root", type=Path, default=OUT_ROOT)

    build = sub.add_parser("build")
    build.add_argument("--words-file", type=Path, default=WORDS_FILE)
    build.add_argument("--out-root", type=Path, default=OUT_ROOT)
    build.add_argument("--output", type=Path, default=ROOT / "training" / "corpus" / "kernel_experiment.txt")
    build.add_argument("--manifest", type=Path, default=ROOT / "training" / "corpus" / "manifests" / "kernel_experiment.txt")
    build.add_argument("--report", type=Path, default=ROOT / "training" / "corpus" / "kernel_experiment_report.md")
    build.add_argument("--repeat-kernel", type=int, default=1)
    build.add_argument("--repeat-identity", type=int, default=3)
    build.add_argument(
        "--repeat-identity-path",
        action="append",
        default=["/identity/"],
        help="Path substring that receives --repeat-identity. May be repeated.",
    )

    build_jsonl = sub.add_parser("build-jsonl")
    build_jsonl.add_argument("--words-file", type=Path, default=WORDS_FILE)
    build_jsonl.add_argument("--out-root", type=Path, default=OUT_ROOT)
    build_jsonl.add_argument("--output", type=Path, default=ROOT / "training" / "corpus" / "kernel_experiment.jsonl")
    build_jsonl.add_argument("--report", type=Path, default=ROOT / "training" / "corpus" / "kernel_experiment_jsonl_report.md")
    build_jsonl.add_argument("--repeat-kernel", type=int, default=1)
    build_jsonl.add_argument("--repeat-identity", type=int, default=3)
    build_jsonl.add_argument(
        "--repeat-identity-path",
        action="append",
        default=["/identity/"],
        help="Path substring that receives --repeat-identity. May be repeated.",
    )
    build_jsonl.add_argument("--lowercase-user-copy", action="store_true")

    args = parser.parse_args()
    if args.cmd == "gen":
        cmd_gen(args)
    elif args.cmd == "report":
        cmd_report(args)
    elif args.cmd == "validate":
        cmd_validate(args)
    elif args.cmd == "build":
        cmd_build(args)
    elif args.cmd == "build-jsonl":
        cmd_build_jsonl(args)
    elif args.cmd == "clean-claims":
        cmd_clean_claims(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

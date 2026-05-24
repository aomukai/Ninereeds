#!/usr/bin/env python3
"""
gen_grammar.py — Generate Ninereeds grammar curriculum files via OpenRouter.

The script is intentionally cluster-scoped and resumable. Generate one grammar
directory at a time, validate, audit, then continue.

Usage:
  python3 meta/scripts/gen_grammar.py --cluster 00_relation --dry-run
  python3 meta/scripts/gen_grammar.py --cluster 00_relation
"""
from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent.parent
GRAMMAR_ROOT = ROOT / "training_data" / "grammar"
MODEL = "deepseek/deepseek-v4-flash"
MAX_TOKENS = 32768
REQUEST_TIMEOUT = 300.0


@dataclass(frozen=True)
class FileSpec:
    path: str
    focus: str
    required_terms: tuple[str, ...]
    notes: str


CLUSTERS: dict[str, list[FileSpec]] = {
    "00_relation": [
        FileSpec(
            path="00_relation/001_relation_receiver.md",
            focus="relation and receiver",
            required_terms=("relation", "receiver"),
            notes="Explain that a receiver gets something or is helped by an action.",
        ),
        FileSpec(
            path="00_relation/002_place_source_target.md",
            focus="place, source, target",
            required_terms=("place", "source", "target"),
            notes="Contrast where something is, where movement begins, and where movement points.",
        ),
        FileSpec(
            path="00_relation/003_path_object_action.md",
            focus="path, object, action",
            required_terms=("path", "object", "action"),
            notes="Keep object as acted-on thing; keep path as route through space.",
        ),
        FileSpec(
            path="00_relation/004_owner_change_means.md",
            focus="owner, change, means",
            required_terms=("owner", "change", "means"),
            notes="Keep means as way/tool/vehicle used to do something.",
        ),
    ],
}


BASE_RULES = """
You are generating one small grammar curriculum file for Ninereeds.

Output ONLY the file content. No markdown fences. No preamble.

Format rules:
- Use exactly 4 [user] / [Ninereeds] pairs.
- Each [user] tag and its English question must be on the same line.
- Each [Ninereeds] tag and the English answer must be on the same line.
- Each [Ninereeds] response has exactly four short answer lines:
  1. English, on the same line as [Ninereeds]
  2. German
  3. Japanese
  4. Traditional Chinese
- Keep [user] and [Ninereeds] tags exactly.
- Do not add headings.
- Do not use romaji.

Register:
- English: simple child-facing explanation.
- German: clear Schulbuch style.
- Japanese: plain form, natural, no ですます, no romaji.
- Chinese: Traditional Chinese, standard written register.

Content rules:
- This is a bridge file, not a grammar lecture.
- Keep vocabulary simple and concrete.
- Do not introduce dative/accusative terminology in this cluster.
- Use examples with Emma, Taro, Gran, Biscuit, apple, cup, table, house, garden, bus, hammer, ball where useful.
- Keep character names as names. Do not translate Emma, Taro, Gran, or Biscuit.
"""


def load_dotenv(path: Path) -> None:
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


def get_api_key() -> str:
    load_dotenv(ROOT / ".env")
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("No API key found. Set OPENROUTER_API_KEY in .env or environment.")
    return key


def build_prompt(spec: FileSpec, previous_errors: list[str] | None = None) -> str:
    required = ", ".join(spec.required_terms)
    retry = ""
    if previous_errors:
        retry = (
            "\nPrevious attempt failed validation. Fix these errors:\n"
            + "\n".join(f"- {e}" for e in previous_errors)
            + "\n"
        )
    return f"""{BASE_RULES}

File focus: {spec.focus}
Required terms: {required}
Notes: {spec.notes}
{retry}
Generate the file now.
"""


def validate(text: str, spec: FileSpec) -> list[str]:
    errors: list[str] = []
    user_count = len(re.findall(r"^\[user\]", text, re.MULTILINE))
    nr_count = len(re.findall(r"^\[Ninereeds\]", text, re.MULTILINE))
    if user_count != 4:
        errors.append(f"expected 4 [user] tags, got {user_count}")
    if nr_count != 4:
        errors.append(f"expected 4 [Ninereeds] tags, got {nr_count}")
    if user_count != nr_count:
        errors.append(f"mismatched tag counts: {user_count} [user] vs {nr_count} [Ninereeds]")
    user_with_content = len(re.findall(r"^\[user\].+", text, re.MULTILINE))
    nr_with_content = len(re.findall(r"^\[Ninereeds\].+", text, re.MULTILINE))
    if user_with_content != user_count:
        errors.append("[user] tags must have the question on the same line")
    if nr_with_content != nr_count:
        errors.append("[Ninereeds] tags must have the English answer on the same line")
    if re.search(r"[A-Za-z]+(?:-[A-Za-z]+)?\s*\([^)]*romaji", text, re.I):
        errors.append("possible romaji explanation found")
    for term in spec.required_terms:
        if term.lower() not in text.lower():
            errors.append(f"missing required term: {term}")

    blocks = re.split(r"(?=^\[user\])", text.strip(), flags=re.MULTILINE)
    blocks = [b for b in blocks if b.strip()]
    for i, block in enumerate(blocks, start=1):
        if "[Ninereeds]" not in block:
            continue
        response = block.split("[Ninereeds]", 1)[1].strip()
        lines = [ln for ln in response.splitlines() if ln.strip()]
        if len(lines) != 4:
            errors.append(f"pair {i}: expected 4 response lines, got {len(lines)}")
    return errors


def generate_file(client: OpenAI, spec: FileSpec, force: bool, dry_run: bool) -> str:
    out_path = GRAMMAR_ROOT / spec.path
    if out_path.exists() and not force:
        return f"SKIP {spec.path} — exists"
    if dry_run:
        return f"WOULD WRITE {spec.path}"

    errors: list[str] | None = None
    for attempt in range(1, 4):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": build_prompt(spec, errors)}],
            )
        except Exception as exc:
            return f"ERROR {spec.path}: {exc}"
        text = (resp.choices[0].message.content or "").strip()
        errors = validate(text, spec)
        if not errors:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(text + "\n", encoding="utf-8")
            return f"OK {spec.path}"
    return f"FAIL {spec.path}: {'; '.join(errors or ['unknown validation error'])}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate grammar curriculum files")
    parser.add_argument("--cluster", choices=sorted(CLUSTERS), required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Overwrite existing generated files")
    args = parser.parse_args()

    specs = CLUSTERS[args.cluster]
    print(f"Grammar generation cluster: {args.cluster}", flush=True)
    print(f"Files: {len(specs)}", flush=True)
    print(f"Dry run: {args.dry_run}", flush=True)
    print(flush=True)

    client = None
    if not args.dry_run:
        client = OpenAI(
            api_key=get_api_key(),
            base_url="https://openrouter.ai/api/v1",
            timeout=REQUEST_TIMEOUT,
        )

    for spec in specs:
        if args.dry_run:
            print(generate_file(None, spec, args.force, True), flush=True)  # type: ignore[arg-type]
        else:
            print(generate_file(client, spec, args.force, False), flush=True)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()

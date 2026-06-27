#!/usr/bin/env python3
"""Generate the Ninereeds identity corpus from identity.md."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from openai import OpenAI, RateLimitError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "identity.md"
OUT_ROOT = ROOT / "training_data" / "kernel_identity"

SOURCES: dict[str, dict[str, Any]] = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "deepseek/deepseek-v4-flash",
        "api_key_env": "OPENROUTER_API_KEY",
        "max_tokens": 20000,
        "extra_body": {},
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
        "max_tokens": 8000,
        "extra_body": {},
    },
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "model": "deepseek-ai/deepseek-v4-flash",
        "api_key_env": "NVIDIA_API_KEY",
        "max_tokens": 20000,
        "extra_body": {"chat_template_kwargs": {"thinking": False}},
    },
}

GROUPS = {
    "core": 30,
    "contrast": 30,
    "limits": 24,
    "knowledge": 24,
    "senses": 18,
    "language": 12,
    "chat_control": 24,
    "correction": 16,
    "unknowns": 24,
    "multi_turn": 18,
}

FILE_RE = re.compile(r"=== FILE: ([^\n=]+\.md) ===\n(.*?)(?==== FILE:|$)", re.DOTALL)
TURN_RE = re.compile(r"^\[user\].*\n\[Ninereeds\].*", re.MULTILINE)


def load_env(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def safe_name(value: str) -> str:
    value = value.lower().strip()
    suffix = ".md" if value.endswith(".md") else ""
    if suffix:
        value = value[: -len(suffix)]
    return re.sub(r"[^a-z0-9_/-]+", "_", value).strip("_/") + suffix


def parse_files(raw: str) -> dict[str, str]:
    files: dict[str, str] = {}
    for match in FILE_RE.finditer(raw):
        name = safe_name(match.group(1).strip())
        content = match.group(2).strip()
        if name and content:
            files[name] = normalize(content)
    return files


def normalize(content: str) -> str:
    lines: list[str] = []
    for raw in content.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        line = raw.rstrip()
        if line.strip().startswith("```"):
            continue
        line = re.sub(r"^\[(user|Ninereeds)\]\s+", r"[\1]", line)
        lines.append(line)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def validate_file(path: str, content: str, group: str) -> list[str]:
    issues: list[str] = []
    if not path.startswith(f"{group}/"):
        issues.append("wrong group path")
    if not TURN_RE.search(content):
        issues.append("no dialogue turn")
    users = len(re.findall(r"^\[user\]", content, re.MULTILINE))
    bots = len(re.findall(r"^\[Ninereeds\]", content, re.MULTILINE))
    if users != bots:
        issues.append(f"mismatched turns {users}/{bots}")
    if "```" in content:
        issues.append("markdown fence")
    return issues


def group_prompt(spec: str, group: str, count: int) -> str:
    return f"""Generate Ninereeds identity corpus files for exactly one group.

Use this spec as binding requirements:

{spec}

Task:
- Generate exactly {count} files for group `{group}`.
- Every file path must be under `{group}/`.
- Use descriptive lowercase snake-case filenames.
- Output only file blocks.
- Do not write explanations.
- Do not include markdown fences.

Use this exact delimiter for each file:

=== FILE: {group}/example_name.md ===
[user]...
[Ninereeds]...

Important style:
- For contrast questions like "are you ChatGPT?", answer briefly: "No. I am Ninereeds."
- Keep Ninereeds responses short and stable.
- Do not mention OpenAI, Anthropic, APIs, policies, browsing, or tools.
- Do not use contractions.
"""


def generate_group(client: OpenAI, source: str, group: str, count: int, spec: str, cfg: dict[str, Any]) -> dict[str, str]:
    prompt = group_prompt(spec, group, count)
    attempts = 4
    for attempt in range(1, attempts + 1):
        try:
            kwargs: dict[str, Any] = {
                "model": client.model,  # type: ignore[attr-defined]
                "messages": [
                    {"role": "system", "content": "You generate strict training corpus files for a small language model. Output only requested file blocks."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": cfg["max_tokens"],
                "temperature": 0.35,
            }
            if cfg.get("extra_body"):
                kwargs["extra_body"] = cfg["extra_body"]
            response = client.chat.completions.create(**kwargs)
            raw = response.choices[0].message.content or ""
            files = parse_files(raw)
            bad = []
            for path, content in files.items():
                issues = validate_file(path, content, group)
                if issues:
                    bad.append(f"{path}: {issues}")
            if len(files) < max(8, int(count * 0.75)) or bad:
                print(f"WARN [{source}:{group}] attempt={attempt} files={len(files)} bad={bad[:3]}", flush=True)
                continue
            print(f"OK   [{source}:{group}] files={len(files)}", flush=True)
            return files
        except RateLimitError:
            wait = 30 * attempt
            print(f"RATE [{source}:{group}] wait={wait}s", flush=True)
            time.sleep(wait)
        except Exception as exc:
            print(f"ERR  [{source}:{group}] {exc}", flush=True)
    raise RuntimeError(f"failed to generate {group}")


def write_files(files: dict[str, str], out_root: Path) -> None:
    for rel, content in files.items():
        path = out_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate identity corpus from identity.md")
    parser.add_argument("--source", choices=list(SOURCES), default="deepseek")
    parser.add_argument("--out-root", type=Path, default=OUT_ROOT)
    parser.add_argument("--spec", type=Path, default=SPEC)
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--groups", nargs="*", default=list(GROUPS))
    args = parser.parse_args()

    load_env()
    cfg = SOURCES[args.source]
    api_key = os.environ.get(cfg["api_key_env"], "")
    if not api_key:
        raise SystemExit(f"{cfg['api_key_env']} is not set")

    out_root = args.out_root if args.out_root.is_absolute() else ROOT / args.out_root
    spec_path = args.spec if args.spec.is_absolute() else ROOT / args.spec
    if args.clean and out_root.exists():
        shutil.rmtree(out_root)
    spec = spec_path.read_text(encoding="utf-8")

    client = OpenAI(api_key=api_key, base_url=cfg["base_url"], timeout=240.0)
    client.model = cfg["model"]  # type: ignore[attr-defined]

    manifest: dict[str, Any] = {"source": args.source, "model": cfg["model"], "groups": {}}
    for group in args.groups:
        if group not in GROUPS:
            raise SystemExit(f"Unknown group: {group}")
        files = generate_group(client, args.source, group, GROUPS[group], spec, cfg)
        write_files(files, out_root)
        manifest["groups"][group] = len(files)
    (out_root / "_meta.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote identity corpus -> {out_root}")


if __name__ == "__main__":
    main()

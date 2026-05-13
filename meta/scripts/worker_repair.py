#!/usr/bin/env python3
"""
Batch repair worker for Ninereeds training corpus.

Reads the first N entries from damage_map.txt, sends each file to
DeepSeek v4 flash via OpenRouter for repair, writes the fixed file back,
then removes the processed entries from damage_map.txt.

Usage:
  python3 skills/worker_repair.py [--batch 10] [--dry-run]

Config:
  Reads OpenRouter API key from ~/.local/share/opencode/auth.json
  Override with WORKER_API_KEY env var.
"""

import argparse
import concurrent.futures
import json
import os
import pathlib
import re
import sys
import threading

from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────

AUTH_PATH = pathlib.Path.home() / ".local/share/opencode/auth.json"
BASE_URL   = "https://openrouter.ai/api/v1"
MODEL      = "deepseek/deepseek-v4-flash"

DAMAGE_MAP = pathlib.Path("training_data/phases/damage_map.txt")

# ── Format spec injected into every repair prompt ────────────────────────────

FORMAT_SPEC = """
## Correct format for phase files

### Phase 1, 2, 3, 6 — Format A (4 questions per file):

```
[user]what does X look like?
[Ninereeds]This is X.
X is [property].
X is [property].
X is [property].
X is [property].
X is [property].
X is [A] and [B].

[user]where is X?
[Ninereeds]This is X.
...

[user]what does X do?
[Ninereeds]This is X.
...

[user]what is X for?
[Ninereeds]This is X.
...
```

Rules:
- Exactly 4 [user]/[Ninereeds] block pairs
- Each [Ninereeds] block starts with `This is X.` on the SAME LINE as the tag: `[Ninereeds]This is X.`
- 5 body lines after the opener (concrete, affirmative, present tense, no pronouns)
- 1 summary line combining two properties: `X is [A] and [B].`
- No blank lines within a block; one blank line between blocks
- No line may repeat another line in the same block
- No pronouns anywhere (no it, its, they, them, their, he, she)
- Subject of every sentence is X (or X's part)

### Phase 4 — Format A, 1-2 questions per file (biological processes):
Same rules but only 1 or 2 question blocks.

### Phase 5 action sequences — Format A, 1 question per file:
```
[user]what does a [state] bird do?
[Ninereeds]This is a [state] bird.
The bird [action].
The bird [action].
The bird [action].
The bird [action].
The bird [action].
The bird [action].
```
6 body lines describing a goal-directed action chain.

### Phase 5 and 6 vocabulary — Format B ("X is here"):
```
[user]what is X?
[Ninereeds]X is here.
X is [definition].
X is [context].
X [usage].

[user]where is X?
...
```
"""

# ── Repair prompts by damage type ─────────────────────────────────────────────

PATCH_PROMPT = """\
You are a corpus repair tool. Fix the training file below. Do NOT explain anything.
Output ONLY the corrected file contents — no markdown fences, no commentary.

Damage type: {damage_tag}
Specific issue: {reason}

{format_spec}

## Repair instructions for this damage type:

{repair_instruction}

## File to repair (word: "{word}"):

{file_content}
"""

REGENERATE_PROMPT = """\
You are a corpus generation tool. Rewrite this training file from scratch.
Do NOT explain anything. Output ONLY the new file contents — no markdown fences, no commentary.

The target word is: "{word}"

{format_spec}

## Original file (for reference only — rewrite it completely):

{file_content}
"""

REPAIR_INSTRUCTIONS = {
    "TEMPLATE": """\
The file has a wrong template structure. Restructure it to exactly match the correct format.
If the file already matches the format upon inspection, output it unchanged.""",

    "QUALITY": """\
The file has duplicate, repeated, placeholder, or weak lines.
- Remove any line that is identical or nearly identical to another line in the same block.
- Remove placeholder filler like "nice look", "good work", "helpful form", etc.
- Replace removed lines with fresh, concrete, unique descriptive sentences.
- Ensure each block has exactly 5 body lines + 1 summary (no more, no less).""",

    "STRUCT": """\
The file has structural problems (broken tags, missing opener, concatenated lines).
- Add `This is X.` opener if missing from any [Ninereeds] block.
- If lines are concatenated into one long sentence with periods, split them into separate lines.
- Fix any missing [user] or [Ninereeds] tags.""",

    "GRAMMAR": """\
The file has grammatical errors or the wrong number of lines per block.
- Fix all grammatical errors.
- Ensure each block has exactly 5 body lines + 1 summary (remove extras, add if missing).
- Keep the meaning intact where possible.""",

    "POS": """\
The file frames the word with the wrong part of speech (e.g. treating "acoustic" as a noun when it is an adjective).
- Reframe the word correctly for its actual part of speech.
- Adjectives: "X is [adjective]. X is [adjective]." (describe things that ARE this property)
- Nouns: standard "This is X." format
- Verbs used as concepts: nominalized form ("This is X." where X is the action-concept)
- Keep all other format rules intact.""",

    "UNKNOWN": """\
Unknown damage type. Evaluate the file and fix whatever structural or content issues are present.
Aim for the correct format with 5 body lines + 1 summary per block.""",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_api_key():
    if key := os.environ.get("WORKER_API_KEY"):
        return key
    try:
        data = json.loads(AUTH_PATH.read_text())
        v = data.get("openrouter", "")
        return v.get("key", "") if isinstance(v, dict) else v
    except Exception:
        return ""


def parse_damage_map(path: pathlib.Path):
    """Return list of entry dicts for .md lines."""
    entries = []
    for line in path.read_text().splitlines():
        if ".md" not in line:
            continue
        # handles: "phase_1_958.md ..." and "./phase_2_237.md ..."
        m = re.match(
            r"^\.?/?(phase_\d+_[\w]+\.md)\s+(PATCH|REGENERATE)\s+\(([^)]+)\)\s+\[(\w+)\]",
            line.strip()
        )
        if m:
            entries.append({
                "line": line,
                "filename": m.group(1),
                "action": m.group(2),
                "reason": m.group(3),
                "tag": m.group(4),
            })
    return entries


def resolve_path(filename: str) -> pathlib.Path:
    # phase_1_958.md → training_data/phases/phase_1/phase_1_958.md
    m = re.match(r"^(phase_\d+)_", filename)
    if not m:
        raise ValueError(f"Cannot resolve path for: {filename}")
    phase_dir = m.group(1)
    return pathlib.Path("training_data/phases") / phase_dir / filename


def extract_word(content: str, filename: str) -> str:
    """Extract the target word from the file content or filename."""
    # Try standard opener
    m = re.search(r"\[Ninereeds\]This is (?:a |an |the )?(.+?)\.", content)
    if m:
        return m.group(1).strip()
    # Try [user] question: "what does a panel look like?" → "panel"
    m = re.search(r"\[user\](?:what does (?:a |an |the )?|where is (?:a |an |the )?|what is (?:a |an |the )?)(.+?)(?:\?| look| do| mean)", content)
    if m:
        return m.group(1).strip()
    # Last resort: leave blank (human can verify)
    return "UNKNOWN"


def claim_batch(path: pathlib.Path, batch: list[dict]) -> None:
    """Remove claimed entries from damage_map.txt BEFORE parallel work starts."""
    claimed = {e["line"] for e in batch}
    current = path.read_text().splitlines()
    remaining = [l for l in current if l not in claimed]
    path.write_text("\n".join(remaining) + "\n")


def return_failures(path: pathlib.Path, failed_entries: list[dict]) -> None:
    """Prepend failed entries back to damage_map.txt for retry next batch."""
    if not failed_entries:
        return
    lines_to_return = "\n".join(e["line"] for e in failed_entries) + "\n"
    current = path.read_text()
    path.write_text(lines_to_return + current)


def count_md_lines(path: pathlib.Path) -> int:
    return sum(1 for l in path.read_text().splitlines() if ".md" in l)


# ── Worker function (runs in thread) ─────────────────────────────────────────

_print_lock = threading.Lock()

def _log(msg: str, end: str = "\n") -> None:
    with _print_lock:
        print(msg, end=end, flush=True)


def repair_one(entry: dict, client: OpenAI, dry_run: bool) -> tuple[dict, bool]:
    """Repair a single file. Returns (entry, success)."""
    filename = entry["filename"]
    action   = entry["action"]
    reason   = entry["reason"]
    tag      = entry["tag"]

    try:
        file_path = resolve_path(filename)
        content   = file_path.read_text()
        word      = extract_word(content, filename)

        if dry_run:
            _log(f"  [DRY RUN] {filename} {action} ({reason}) [{tag}] — word: {word}")
            return entry, True

        if action == "REGENERATE":
            prompt = REGENERATE_PROMPT.format(
                word=word,
                format_spec=FORMAT_SPEC,
                file_content=content,
            )
        else:
            instruction = REPAIR_INSTRUCTIONS.get(tag, REPAIR_INSTRUCTIONS["STRUCT"])
            prompt = PATCH_PROMPT.format(
                damage_tag=tag,
                reason=reason,
                format_spec=FORMAT_SPEC,
                repair_instruction=instruction,
                word=word,
                file_content=content,
            )

        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content":
                    "You are a corpus repair tool. Output ONLY the corrected file "
                    "contents. No markdown fences, no commentary, no explanations."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=8192,  # reasoning model: needs room for think tokens + output
        )

        new_content = resp.choices[0].message.content or ""

        # Strip accidental markdown fences
        if new_content.startswith("```"):
            new_content = new_content.split("\n", 1)[1].rsplit("```", 1)[0]

        if not new_content.strip():
            _log(f"  {filename} [{tag}] FAILED (empty response)")
            return entry, False

        file_path.write_text(new_content)

        tokens_in  = resp.usage.prompt_tokens if resp.usage else "?"
        tokens_out = resp.usage.completion_tokens if resp.usage else "?"
        _log(f"  {filename} {action} [{tag}] (word: {word}) OK ({tokens_in}→{tokens_out})")
        return entry, True

    except Exception as e:
        _log(f"  {filename} ERROR: {e}")
        return entry, False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Batch-repair Ninereeds corpus files")
    parser.add_argument("--batch", type=int, default=30,
                        help="Number of files to repair per run (default: 30)")
    parser.add_argument("--workers", type=int, default=5,
                        help="Parallel API workers (default: 5)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without making changes")
    args = parser.parse_args()

    api_key = load_api_key()
    if not api_key:
        print("ERROR: No OpenRouter API key found.", file=sys.stderr)
        print(f"Set WORKER_API_KEY env var or check {AUTH_PATH}", file=sys.stderr)
        sys.exit(1)

    if not DAMAGE_MAP.exists():
        print(f"ERROR: {DAMAGE_MAP} not found.", file=sys.stderr)
        sys.exit(1)

    all_entries = parse_damage_map(DAMAGE_MAP)
    if not all_entries:
        print("damage_map.txt is empty — nothing to do.")
        return

    batch = all_entries[: args.batch]
    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    print(f"Processing {len(batch)} files (of {len(all_entries)} remaining) "
          f"with {args.workers} parallel workers...")
    print()

    # ── Step 1: Claim entries atomically BEFORE any parallel work ─────────────
    if not args.dry_run:
        claim_batch(DAMAGE_MAP, batch)

    # ── Step 2: Repair in parallel ─────────────────────────────────────────────
    results: list[tuple[dict, bool]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(repair_one, entry, client, args.dry_run): entry
            for entry in batch
        }
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    # ── Step 3: Return failures to damage_map.txt for retry ───────────────────
    failed_entries = [entry for entry, success in results if not success]
    if not args.dry_run and failed_entries:
        return_failures(DAMAGE_MAP, failed_entries)

    repaired = sum(1 for _, success in results if success)
    failed   = len(failed_entries)
    remaining = count_md_lines(DAMAGE_MAP)

    print()
    print("RECEIPT")
    print("-------")
    print(f"Files processed this run: {len(batch)}")
    print(f"  Repaired: {repaired}")
    print(f"  Failed:   {failed}")
    print(f"damage_map.txt entries remaining: {remaining}")
    print(f"Status: {'DONE' if remaining == 0 else 'IN_PROGRESS'}")


if __name__ == "__main__":
    main()

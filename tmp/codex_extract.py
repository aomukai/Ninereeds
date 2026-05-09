#!/usr/bin/env python3
"""Run vocab extraction for remaining wiki files via codex, one at a time."""
import subprocess, sys, re
from pathlib import Path

REPO = Path("/home/aomukai/Ninereeds")
OUT = REPO / "training_data/triplet_stories"
DONE_FILE = OUT / "files_done.txt"

REMAINING = [
    "training_data/triplet_stories/tier_2/home_and_daily_life.md",
    "training_data/triplet_stories/tier_2/vehicles_and_travel.md",
    "training_data/triplet_stories/tier_3/animals_and_nature.md",
    "training_data/triplet_stories/tier_3/people_and_relationships.md",
    "training_data/triplet_stories/tier_3/vehicles_and_travel.md",
    "training_data/triplet_stories/tier_4/body_and_health.md",
    "training_data/triplet_stories/tier_4/people_and_relationships.md",
    "training_data/triplet_stories/tier_4/tools_and_making.md",
]

already_done = {l.strip() for l in DONE_FILE.read_text().splitlines() if l.strip()}

def merge(path: Path, words: list[str]) -> int:
    existing = set(path.read_text().splitlines()) if path.exists() else set()
    combined = sorted(existing | set(w for w in words if w))
    path.write_text("\n".join(combined) + "\n")
    return len(combined) - len(existing)

def parse(text: str) -> dict:
    result = {"verbs": [], "adjectives": [], "nouns": []}
    current = None
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    for line in text.splitlines():
        s = re.sub(r"[*_`#]", "", line).strip().upper()
        if re.match(r"^VERBS\s*:?$", s): current = "verbs"
        elif re.match(r"^ADJECTIVES?\s*:?$", s): current = "adjectives"
        elif re.match(r"^NOUNS?\s*:?$", s): current = "nouns"
        elif s and current:
            for w in re.split(r"[,;\s]+", line.strip().lower()):
                w = w.strip().strip(".-")
                if re.match(r"^[a-z][a-z\-]{1,30}$", w):
                    result[current].append(w)
    return result

for rel_path in REMAINING:
    if rel_path in already_done:
        print(f"SKIP {rel_path} (already done)")
        continue

    fpath = REPO / rel_path
    content = fpath.read_text(errors="replace")

    prompt = f"""Extract content words from the file below into three groups.

Rules:
- Ignore speaker tags: [user] [Ninereeds]
- Ignore numbers and proper names.
- Ignore function/grammar words (articles, prepositions, conjunctions, auxiliaries).
- Ignore temporal/spatial words: now, then, here, there, before, after, above, below, inside, outside, already, still, just, always, never, often, sometimes.
- Keep only meaningful content words.

Normalise:
- Verbs: base/infinitive form
- Adjectives: dictionary form
- Nouns: singular form

Output ONLY this format with no extra text:

VERBS:
<one verb per line>

ADJECTIVES:
<one adjective per line>

NOUNS:
<one noun per line>

File content:
---
{content}
---"""

    prompt_file = REPO / "tmp" / "codex_prompt.txt"
    prompt_file.write_text(prompt)

    print(f"Processing {fpath.name} ...", flush=True)
    result = subprocess.run(
        ["codex", "exec", "-m", "gpt-5.4-mini",
         "--dangerously-bypass-approvals-and-sandbox",
         "-s", "danger-full-access",
         f"Read the file tmp/codex_prompt.txt and follow its instructions exactly. Output only VERBS:, ADJECTIVES:, NOUNS: sections."],
        cwd=REPO, capture_output=True, text=True, timeout=300
    )

    output = result.stdout + result.stderr
    words = parse(output)
    total = sum(len(v) for v in words.values())

    if total == 0:
        print(f"FAIL {fpath.name}: no words parsed. Raw output saved.")
        (REPO / "tmp" / f"codex_debug_{fpath.stem}.txt").write_text(output)
        continue

    av = merge(OUT / "verbs.txt", words["verbs"])
    aa = merge(OUT / "adjectives.txt", words["adjectives"])
    an = merge(OUT / "nouns.txt", words["nouns"])
    with DONE_FILE.open("a") as f:
        f.write(rel_path + "\n")
    print(f"OK  {fpath.name}  +{av}v +{aa}adj +{an}n")

print("\nDone. Remaining:")
done2 = {l.strip() for l in DONE_FILE.read_text().splitlines() if l.strip()}
q = [l.strip() for l in (OUT / "files.txt").read_text().splitlines() if l.strip()]
print(f"  {len([f for f in q if f not in done2])} files left")

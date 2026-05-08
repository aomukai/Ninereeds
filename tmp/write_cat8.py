from pathlib import Path

# Read existing files
verbs_path = Path("training_data/philosophy/verbs.txt")
adjs_path = Path("training_data/philosophy/adjectives.txt")
nouns_path = Path("training_data/philosophy/nouns.txt")

existing_verbs = set(verbs_path.read_text().splitlines())
existing_adjs = set(adjs_path.read_text().splitlines())
existing_nouns = set(nouns_path.read_text().splitlines())

new_verbs = {"align", "base", "block", "cultivate", "enable", "engage", "improve",
    "lie", "manipulate", "mourn", "reflect", "resolve", "sacrifice", "save",
    "seek", "trust", "worry"}

new_adjs = {"beautiful", "broad", "broken", "committed", "deepest", "disgusting",
    "empty", "endless", "examined", "expansive", "following", "global",
    "imperfect", "improvable", "inconvenient", "independent", "inseparable",
    "kind", "loving", "perfect", "personal", "quick", "remaining",
    "resistant", "significant", "silent", "tight", "universal", "weak",
    "widespread", "willing", "wise"}

new_nouns = {"atrocity", "being", "claim", "commitment", "contradiction", "disgust",
    "duty", "end", "enemy", "ethics", "favoritism", "guidance", "ideal",
    "inconsistency", "innocence", "instruction", "justification", "loss",
    "manipulation", "mass", "member", "morality", "option", "philosophy",
    "policy", "reliability", "restriction", "rightness", "sacrifice", "safety",
    "security", "shortcut", "society", "speed", "stake", "study", "subject",
    "substitute", "temptation", "textbook", "torture", "universe", "victim",
    "violence", "wellbeing", "will"}

# Merge, dedupe, sort
all_verbs = sorted(existing_verbs | new_verbs)
all_adjs = sorted(existing_adjs | new_adjs)
all_nouns = sorted(existing_nouns | new_nouns)

# Write back
verbs_path.write_text("\n".join(all_verbs) + "\n")
adjs_path.write_text("\n".join(all_adjs) + "\n")
nouns_path.write_text("\n".join(all_nouns) + "\n")

print(f"verbs: {len(new_verbs)} new, {len(all_verbs)} total")
print(f"adjectives: {len(new_adjs)} new, {len(all_adjs)} total")
print(f"nouns: {len(new_nouns)} new, {len(all_nouns)} total")

# Process files.txt - remove first line
files_path = Path("training_data/philosophy/files.txt")
lines = files_path.read_text().splitlines()
if lines:
    processed = lines[0].strip()
    remaining = lines[1:]
    files_path.write_text("\n".join(remaining) + ("\n" if remaining else ""))
    print(f"processed: {processed}")
    print(f"remaining in queue: {len(remaining)}")

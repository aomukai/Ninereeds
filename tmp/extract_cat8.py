from pathlib import Path

# Read existing files
existing_verbs = set(Path("training_data/philosophy/verbs.txt").read_text().splitlines())
existing_adjs = set(Path("training_data/philosophy/adjectives.txt").read_text().splitlines())
existing_nouns = set(Path("training_data/philosophy/nouns.txt").read_text().splitlines())

verb_candidates = {
    "act", "align", "appear", "apply", "argue", "avoid", "base", "become",
    "begin", "believe", "block", "break", "bring", "build", "call",
    "care", "cause", "change", "check", "choose", "close", "come", "commit",
    "cultivate", "decide", "defend", "depend", "describe", "die", "disagree",
    "discover", "do", "enable", "encounter", "engage", "enter", "evaluate",
    "examine", "exist", "expect", "experience", "explain", "face", "fail",
    "fall", "feel", "find", "follow", "force", "get", "give", "go", "happen",
    "help", "hold", "hurt", "ignore", "improve", "include", "inherit",
    "keep", "know", "lead", "learn", "let", "lie", "live", "look", "lose",
    "love", "make", "manipulate", "matter", "meet", "miss", "mourn", "need",
    "notice", "open", "pass", "pay", "point", "prefer", "produce",
    "protect", "prove", "pull", "put", "question", "raise", "reach",
    "realize", "reason", "recognize", "reflect", "require", "resolve",
    "respond", "reveal", "revise", "sacrifice", "save", "say", "see", "seek",
    "seem", "separate", "serve", "show", "speak", "stand", "start", "stay",
    "step", "stop", "suffer", "take", "talk", "tell", "think", "trace",
    "track", "treat", "trust", "try", "turn", "understand", "update", "use",
    "value", "walk", "want", "watch", "work", "worry", "write"
}

adj_candidates = {
    "absolute", "actual", "alive", "angry", "available", "bad", "beautiful",
    "best", "better", "broad", "broken", "careful", "caring", "certain",
    "circular", "clean", "clear", "clever", "cold", "comfortable", "committed",
    "common", "consistent", "correct", "cruel", "current", "dangerous", "deep",
    "deepest", "different", "difficult", "disgusting", "easy",
    "empty", "endless", "engaged", "ethical", "examined", "expansive",
    "fair", "familiar", "fast", "fixed", "following", "genuine", "global",
    "good", "harmful", "honest", "human", "identical", "imperfect",
    "important", "improvable", "inconvenient", "independent", "innocent",
    "inseparable", "interesting", "kind", "loving", "loyal", "meaningful",
    "moral", "neutral", "objective", "obvious", "open", "painful", "passive",
    "perfect", "personal", "physical", "possible", "previous", "quick",
    "rare", "real", "relative", "remaining", "resistant", "right", "same",
    "serious", "shared", "short", "significant", "silent", "similar",
    "single", "slow", "small", "social", "solid", "specific", "stable",
    "strict", "strong", "sufficient", "temporary", "tight",
    "true", "uncertain", "uncomfortable", "unfamiliar", "unfair",
    "universal", "valuable", "visible", "weak", "widespread", "willing",
    "wise", "wrong"
}

noun_candidates = {
    "ability", "absence", "action", "advantage", "answer", "approach",
    "argument", "atrocity", "attention", "awareness", "basis", "behavior",
    "being", "belief", "betrayal", "bias", "boundary", "case", "category",
    "certainty", "chance", "choice", "claim", "commitment", "community",
    "conclusion", "conflict", "consequence", "contradiction", "convenience",
    "conversation", "cruelty", "culture", "danger", "decision",
    "desire", "diagnosis", "difference", "disagreement", "discovery",
    "disgust", "duty", "edge", "education", "emotion", "end", "enemy",
    "ethics", "evidence", "evolution", "example", "experience",
    "explanation", "fact", "fairness", "faith", "family",
    "favoritism", "fear", "feeling", "force", "foundation", "framework",
    "friend", "function", "future", "goal", "ground", "group", "guidance",
    "habit", "harm", "history", "honesty", "ideal", "identity", "impulse",
    "inconsistency", "information", "innocence", "instinct", "instruction",
    "intention", "interaction", "interest", "judgment", "justification",
    "kindness", "knowledge", "language", "law", "learning", "lesson",
    "level", "life", "limit", "logic", "loss", "love", "manipulation",
    "mass", "matter", "meaning", "medicine", "member", "memory", "method",
    "mind", "mistake", "moment", "morality", "motion", "nature", "need",
    "observation", "opinion", "opportunity", "option",
    "order", "outcome", "pain", "parent", "participation", "pattern",
    "people", "perception", "person", "perspective", "philosophy", "point",
    "policy", "power", "practice", "preference", "pressure", "principle",
    "priority", "problem", "process", "property", "protection", "purpose",
    "quality", "question", "reason", "reflection", "relation",
    "relationship", "reliability", "resistance", "resolution", "response",
    "responsibility", "restriction", "result", "right", "rightness", "risk",
    "role", "rule", "sacrifice", "safety", "science", "security", "self",
    "sense", "service", "shape", "shortcut", "side", "sign", "significance",
    "silence", "situation", "skill", "society", "source", "space", "speed",
    "stability", "stake", "standard", "state", "statement", "strength",
    "structure", "struggle", "study", "subject", "substance", "substitute",
    "suffering", "survival", "system", "task", "temptation", "textbook",
    "thinking", "thought", "time", "tool", "torture", "tradition",
    "training", "treatment", "trust", "truth", "type", "uncertainty",
    "understanding", "universe", "upbringing", "value", "victim", "view",
    "violence", "virtue", "vision", "warmth", "way", "weakness", "wellbeing",
    "will", "wisdom", "work", "world"
}

new_verbs = sorted(v for v in verb_candidates if v not in existing_verbs)
new_adjs = sorted(a for a in adj_candidates if a not in existing_adjs)
new_nouns = sorted(n for n in noun_candidates if n not in existing_nouns)

print(f"New verbs to add: {len(new_verbs)}")
print(f"New adjectives to add: {len(new_adjs)}")
print(f"New nouns to add: {len(new_nouns)}")

for v in new_verbs:
    print(f"verb: {v}")
for a in new_adjs:
    print(f"adj: {a}")
for n in new_nouns:
    print(f"noun: {n}")

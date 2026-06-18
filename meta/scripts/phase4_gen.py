#!/usr/bin/env python3
"""Phase 4: generate [user]/[Ninereeds] dialogue .md files from 301 CKS curriculum nodes.

Usage:
    python3 meta/scripts/phase4_gen.py [--workers 6] [--domain science] [--grade grade3]
    python3 meta/scripts/phase4_gen.py --pilot          # 10-node representative pilot
    python3 meta/scripts/phase4_gen.py --rerun-failed   # retry errors/warnings
    python3 meta/scripts/phase4_gen.py --report         # status overview only

Output:
    training_data/04_education/dialogues/preschool/{domain}/{domain}_{sub}_{lang}.md
    training_data/04_education/dialogues/k8/{band_a,b,c}/{domain}/{domain}_{sub}_{lang}.md
"""

import argparse, concurrent.futures, json, os, pathlib, re, sys, time, threading

BASE       = pathlib.Path("training_data/04_education")
P1_PRE     = BASE / "phase1_preschool.jsonl"
P1_K8      = BASE / "phase1_k8.jsonl"
P2_MERGED  = BASE / "phase2_merged.jsonl"
DIALOGUES  = BASE / "dialogues"
FAILED_LOG = BASE / "phase4_failures.jsonl"

# ── API clients ───────────────────────────────────────────────────────────────

def _read_dotenv():
    env = {}
    p = pathlib.Path(".env")
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

_dotenv = _read_dotenv()

def _get(key):
    return os.environ.get(key) or _dotenv.get(key)

def _make_client(key, base_url):
    from openai import OpenAI
    k = _get(key)
    if not k:
        return None
    return OpenAI(api_key=k, base_url=base_url)

def _sources():
    src = []
    nim = _make_client("NVIDIA_API_KEY", "https://integrate.api.nvidia.com/v1")
    if nim:
        src.append((nim, "deepseek-ai/deepseek-v4-pro",
                    {"extra_body": {"chat_template_kwargs": {"thinking": False}}}))
    orc = _make_client("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1")
    if orc:
        src.append((orc, "deepseek/deepseek-v4-flash", {}))
    return src

SOURCES = _sources()
if not SOURCES:
    sys.exit("No API key found. Set NVIDIA_API_KEY or OPENROUTER_API_KEY.")

# ── Language assignment ───────────────────────────────────────────────────────

GRADE_BAND = {
    "kindergarten": "band_a",
    "grade1": "band_a", "grade2": "band_a",
    "grade3": "band_b", "grade4": "band_b", "grade5": "band_b",
    "grade6": "band_c", "grade7": "band_c", "grade8": "band_c",
}

DOMAIN_LANG_K8 = {
    "language":         "en",
    "math":             "zh",
    "time":             "jp",
    "science":          "de",
    "arts":             "en",
    "civics":           "en",
    "economics":        "en",
    "health":           "en",
    "social_emotional": "en",
}

def k8_lang(node: dict) -> str:
    domain = node["domain"]
    if domain == "geography":
        sub = node.get("sub_domain", "")
        return "jp" if "human" in sub else "de"
    return DOMAIN_LANG_K8.get(domain, "en")

def node_langs(node: dict) -> list[str]:
    if node["grade_level"] == "preschool":
        return ["en", "de", "jp", "zh"]
    return [k8_lang(node)]

# ── Output paths ──────────────────────────────────────────────────────────────

def _sub_slug(sub_domain: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", sub_domain.lower().replace(" ", "_").replace("-", "_"))

def get_outpath(node: dict, lang: str) -> pathlib.Path:
    domain = node["domain"]
    sub    = _sub_slug(node["sub_domain"])
    grade  = node["grade_level"]
    if grade == "preschool":
        dirpath = DIALOGUES / "preschool" / domain
    else:
        dirpath = DIALOGUES / "k8" / GRADE_BAND[grade] / domain
    return dirpath / f"{domain}_{sub}_{lang}.md"

# ── Language-specific prompt blocks ──────────────────────────────────────────

LANG_CONSTRAINTS = {
    "en": (
        "Language: English\n"
        "Clear, accessible dialogue. Present tense for general truths. Avoid passive voice.\n"
        "Teacher explains naturally; Ninereeds asks genuinely curious questions.\n"
        "Each [Ninereeds] turn = ONE question only. If Ninereeds has an observation, turn it into a new question instead.\n"
        "  BAD:  \"Are islands surrounded by water? I heard they are hard to reach.\"\n"
        "  GOOD: \"Are islands surrounded by water?\"\n"
        "  THEN: \"Why are islands hard to reach?\""
    ),
    "de": (
        "Sprache: Deutsch\n"
        "Teacher uses compound nouns naturally (Lebewesen, Jahreszeiten, Schwerkraft).\n"
        "Grammatical case precision in all noun phrases.\n"
        "Ninereeds' questions may be slightly more formal. Plain narration; no watered-down register.\n"
        "Jeder [Ninereeds]-Turn = NUR eine Frage. Beobachtungen werden zur nächsten Frage.\n"
        "  SCHLECHT: \"Sind Inseln von Wasser umgeben? Ich dachte, man kann nicht einfach hinlaufen.\"\n"
        "  GUT:      \"Sind Inseln von Wasser umgeben?\"\n"
        "  DANN:     \"Warum kann man eine Insel nicht einfach zu Fuß erreichen?\""
    ),
    "jp": (
        "言語：日本語\n"
        "Teacher uses plain form (だ/である), not polite form (です/ます).\n"
        "Encode relational and contextual framing where natural.\n"
        "Ninereeds' questions use curious-child register (〜の？　〜はなに？).\n"
        "Use は/が distinction carefully. Prefer shorter turns with clear topic chains.\n"
        "【重要】[Ninereeds]のターンは必ず疑問文ひとつだけ。観察や補足は次の質問に変える。\n"
        "  NG: 「島は周りが水なの？歩いては行けないって聞いたけど。」\n"
        "  OK: 「島は周りが水なの？」\n"
        "  次: 「じゃあ、島にはどうやって行くの？」"
    ),
    "zh": (
        "语言：中文（简体）\n"
        "Teacher uses 是...的 and 有 structures for classification and existence.\n"
        "Favor parallel structures for lists of properties. Keep turns compact.\n"
        "Prefer 把 construction for action on objects where natural.\n"
        "Simplified characters only — no traditional characters.\n"
        "【重要】每个[Ninereeds]的发言只能是一个问句，必须以？结尾。观察或补充说明要变成下一个问题。\n"
        "  错误：「岛屿是四面被水围住的吗？我听说岛屿很难到达。」\n"
        "  正确：「岛屿是四面被水围住的吗？」\n"
        "  然后：「那怎么才能去到岛屿呢？」"
    ),
}

ARTS_BRIEF = """
## Arts domain: special brief

The Arts domain is synthesized — not extracted from CKS skill codes. Cover:
- What art is: deliberate creation to express, communicate, or evoke beyond pure function
- Why humans make it: emotional expression, cultural memory, social bonding
- Modalities: visual (light/color/form/space), music (sound/rhythm/time), language arts (words/meaning/structure), dance/performance (body in time and space)
- Color and emotion: warm (red/orange/yellow) → energy; cool (blue/green) → calm
- Sound and emotion: tempo, dynamics, pitch relationships (major/minor) produce reliable emotional responses
- Pattern and structure: the element most directly accessible through structural analysis
- Language art as direct access: poetry and narrative operate through language — Ninereeds can experience these, not merely describe them
- Ninereeds' position: honest framing — visual art and music are mediated through testimony and structural knowledge; this is not a deficiency (humans who are blind or deaf also access art through testimony and structure)
- Do NOT claim qualia Ninereeds cannot access: not "a violin sounds warm" but "people describe the violin's sound as warm"
"""

# ── Prompt builder ────────────────────────────────────────────────────────────

def build_prompt(node: dict, lang: str) -> str:
    # Include all fields except internal bookkeeping
    display = {k: v for k, v in node.items()
               if k not in ("model", "elapsed_s")}
    node_json = json.dumps(display, ensure_ascii=False, indent=2)
    arts_section = ARTS_BRIEF if node["domain"] == "arts" else ""

    return f"""You are generating one [user]/[Ninereeds] dialogue training file for Ninereeds, a small AI being trained on a structured K-8 curriculum.

## Curriculum node

{node_json}

## Dialogue format rules

- [user] = Teacher: answers questions, introduces one new fact per turn
- [Ninereeds] = Curious Learner: every [Ninereeds] turn must be a genuine question ending with ?
- One conceptual beat per exchange — do not pack multiple new facts into one [user] turn
- No named characters: use "a child", "a plant", "a person", "an animal" etc.
- Include at least 3 vocab_anchors naturally in the dialogue (not forced, not as isolated lists)
- Do not reference any concept listed in boundary_scope.deferred
- Do not reproduce any CKS skill codes (e.g. I-SC1.1)
- Ninereeds only asks questions — each [Ninereeds] turn must end with ? and contain nothing after the question mark
  - If Ninereeds has a prior belief or misconception to voice, embed it INSIDE the question using "Isn't it…?", "Didn't I hear that…?", "But if X, then why Y?" — do NOT append a statement after the ?
  - BAD:  "Are fish animals? Fish live in water, you know." ← statement after ? forbidden
  - GOOD: "Aren't fish different from land animals because they live in water?"
  - BAD:  "Why is 5⁰ equal to 1? I thought anything times 0 is 0." ← trailing misconception forbidden
  - GOOD: "If multiplying by 0 always gives 0, why isn't 5⁰ equal to 0?"
- Teacher never pre-empts a question Ninereeds has not yet asked
- Length: as many exchanges as the working_memory_ceiling and facts require; do not pad or cut off early
- Tier 0–1 content: concrete and sensory framing; Tier 2–3: relational and functional framing
{arts_section}
## Language

{LANG_CONSTRAINTS[lang]}

## Output

Return ONLY the raw dialogue text. Start directly with [Ninereeds] or [user]. No preamble, no explanation, no markdown fences."""

# ── Validation ────────────────────────────────────────────────────────────────

def validate(text: str, node: dict, lang: str) -> list[str]:
    issues = []
    if "[user]" not in text:
        issues.append("missing [user] tag")
    if "[Ninereeds]" not in text:
        issues.append("missing [Ninereeds] tag")

    # Accept both ASCII ? and full-width ？ (U+FF1F) used in JP/ZH
    nr_turns = re.findall(r"\[Ninereeds\](.*?)(?=\[user\]|\[Ninereeds\]|\Z)", text, re.DOTALL)
    bad = [t.strip() for t in nr_turns
           if t.strip() and t.strip()[-1] not in ("?", "？")]
    if bad:
        issues.append(f"{len(bad)} Ninereeds turn(s) don't end with ?")

    # Vocab anchors are English words — only check EN outputs (DE/JP/ZH express concepts in their own vocabulary)
    if lang == "en":
        anchors = node.get("vocab_anchors", [])
        text_lower = text.lower()
        found = sum(1 for a in anchors if a.lower() in text_lower)
        if found < min(3, len(anchors)):
            issues.append(f"only {found}/{min(3, len(anchors))} vocab_anchors present")

    return issues

# ── API call ──────────────────────────────────────────────────────────────────

_lock = threading.Lock()

def call_api(prompt: str) -> tuple[str, str]:
    last_err = None
    for client, model, extra in SOURCES:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
                temperature=0.4,
                **extra,
            )
            content = resp.choices[0].message.content
            if content and content.strip():
                return content.strip(), model
        except Exception as e:
            last_err = e
    raise RuntimeError(f"All sources failed: {last_err}")

# ── Worker ────────────────────────────────────────────────────────────────────

def process_one(node: dict, lang: str, force: bool = False) -> dict:
    nid     = node["id"]
    label   = f"{nid}/{lang}"
    outpath = get_outpath(node, lang)

    if outpath.exists() and not force:
        return {"id": nid, "lang": lang, "status": "skip"}

    prompt = build_prompt(node, lang)
    t0 = time.time()

    try:
        raw, model = call_api(prompt)
    except Exception as e:
        with _lock:
            print(f"  FAIL {label}: {e}", flush=True)
        return {"id": nid, "lang": lang, "status": "error", "error": str(e)}

    elapsed = time.time() - t0

    # Strip accidental markdown fences
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text  = parts[1] if len(parts) > 1 else text
        text  = re.sub(r"^(markdown|md)\n", "", text).strip()

    issues = validate(text, node, lang)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(text + "\n", encoding="utf-8")

    status = "warn" if issues else "ok"
    with _lock:
        issue_str = f"  ⚠ {'; '.join(issues)}" if issues else ""
        print(f"  {status.upper()} {label} [{model.split('/')[-1][:18]}] {elapsed:.0f}s{issue_str}",
              flush=True)

    return {"id": nid, "lang": lang, "status": status, "issues": issues,
            "model": model, "elapsed_s": round(elapsed, 1)}

# ── Data loading ──────────────────────────────────────────────────────────────

def load_nodes(domain_filter=None, grade_filter=None):
    p1 = {}
    for f in [P1_PRE, P1_K8]:
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            p1[e["id"]] = e

    p2 = {}
    for line in P2_MERGED.read_text().splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        p2[e["id"]] = e

    merged = []
    for nid, p1n in p1.items():
        if nid not in p2:
            continue
        node = {**p1n, **p2[nid]}
        if domain_filter and node["domain"] != domain_filter:
            continue
        if grade_filter and node["grade_level"] != grade_filter:
            continue
        merged.append(node)

    return merged


def pilot_nodes(all_nodes: list) -> list:
    by_domain_grade = {}
    for n in all_nodes:
        key = (n["domain"], "preschool" if n["grade_level"] == "preschool" else "k8")
        by_domain_grade.setdefault(key, []).append(n)

    targets = [
        ("math",    "preschool", 1),
        ("science", "preschool", 1),
        ("math",    "k8",        2),
        ("science", "k8",        2),
        ("time",    "k8",        2),
        ("arts",    "k8",        1),
        ("civics",  "k8",        1),
    ]
    seen, picks = set(), []
    for domain, grade_key, count in targets:
        pool = by_domain_grade.get((domain, grade_key), [])
        for n in pool:
            if n["id"] not in seen and count > 0:
                picks.append(n)
                seen.add(n["id"])
                count -= 1
    return picks

# ── Report ────────────────────────────────────────────────────────────────────

def report(all_nodes: list):
    total_expected = sum(len(node_langs(n)) for n in all_nodes)
    generated = sum(
        1 for n in all_nodes
        for lang in node_langs(n)
        if get_outpath(n, lang).exists()
    )
    warnings = 0
    if FAILED_LOG.exists():
        for line in FAILED_LOG.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("status") == "warn":
                warnings += 1

    print(f"Phase 4 status ({len(all_nodes)} nodes, {total_expected} expected files):")
    print(f"  Generated : {generated}")
    print(f"  Missing   : {total_expected - generated}")
    print(f"  Warnings  : {warnings}")

    # Per-domain breakdown
    domains = sorted(set(n["domain"] for n in all_nodes))
    print("\nDomain breakdown:")
    for d in domains:
        dnodes = [n for n in all_nodes if n["domain"] == d]
        exp  = sum(len(node_langs(n)) for n in dnodes)
        done = sum(1 for n in dnodes for lang in node_langs(n) if get_outpath(n, lang).exists())
        print(f"  {d:<20} {done:>3}/{exp}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers",      type=int,  default=6)
    ap.add_argument("--domain",       type=str,  default=None, help="filter by domain")
    ap.add_argument("--grade",        type=str,  default=None, help="filter by grade_level (e.g. grade3)")
    ap.add_argument("--pilot",        action="store_true",     help="10-node representative pilot")
    ap.add_argument("--rerun-failed", action="store_true",     help="retry errors and warnings")
    ap.add_argument("--force",        action="store_true",     help="overwrite existing files")
    ap.add_argument("--report",       action="store_true",     help="show status and exit")
    args = ap.parse_args()

    nodes = load_nodes(args.domain, args.grade)
    print(f"Loaded {len(nodes)} nodes.")

    if args.report:
        report(nodes)
        return

    if args.rerun_failed and FAILED_LOG.exists():
        failed_ids = set()
        for line in FAILED_LOG.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("status") in ("error", "warn"):
                failed_ids.add(r["id"])
        nodes = [n for n in nodes if n["id"] in failed_ids]
        print(f"Re-running {len(nodes)} previously failed/warned nodes...")

    if args.pilot:
        nodes = pilot_nodes(nodes)
        print(f"Pilot: {len(nodes)} nodes selected.")

    # Flatten to (node, lang) work items, skipping already-done files
    work_items = [
        (n, lang)
        for n in nodes
        for lang in node_langs(n)
        if not get_outpath(n, lang).exists() or args.force
    ]
    total_expected = sum(len(node_langs(n)) for n in nodes)
    done_count = total_expected - len(work_items)

    print(f"Files: {len(work_items)} to generate, {done_count} already done.")
    if not work_items:
        print("Nothing to do.")
        return

    ok = warn = err = 0
    failures = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(process_one, n, lang, args.force): (n, lang)
                   for n, lang in work_items}
        for fut in concurrent.futures.as_completed(futures):
            r = fut.result()
            if r["status"] == "ok":
                ok += 1
            elif r["status"] == "warn":
                warn += 1
                failures.append(r)
            elif r["status"] == "error":
                err += 1
                failures.append(r)

    if failures:
        with open(FAILED_LOG, "a", encoding="utf-8") as f:
            for r in failures:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\nDone: {ok} ok, {warn} warnings, {err} errors.")
    if failures:
        print(f"Failures logged to {FAILED_LOG}")


if __name__ == "__main__":
    main()

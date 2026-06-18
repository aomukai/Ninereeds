#!/usr/bin/env python3
"""Phase 2: generate facts + misconceptions for all 301 curriculum nodes.

Usage:
    python3 meta/scripts/phase2_gen.py [--workers 6] [--domain math] [--rerun-failed]

Output: training_data/04_education/phase2_outputs/{id}.json
Merge: python3 meta/scripts/phase2_gen.py --merge
"""

import argparse, concurrent.futures, json, math, os, pathlib, sys, time, threading

BASE   = pathlib.Path("training_data/04_education")
OUTDIR = pathlib.Path("training_data/04_education/phase2_outputs")

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
    if not k: return None
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
    sys.exit("No API key found (NVIDIA_API_KEY or OPENROUTER_API_KEY).")

# ── Prompt ────────────────────────────────────────────────────────────────────

EXAMPLE_BAD_FACTS = [
    'Fractions represent parts of a whole.',
    'The numerator is on top.',
]
EXAMPLE_GOOD_FACTS = [
    'The denominator names how many equal parts the whole is divided into; a circle cut into 4 equal pieces has denominator 4 whether 0, 1, 2, 3, or 4 pieces are shaded.',
    'The numerator counts how many of those equal-sized parts are selected; 3/4 means exactly 3 of the 4 equal pieces.',
    'On a number line from 0 to 1, the fraction 1/4 lands exactly one-quarter of the way across, at the same point regardless of what object or drawing is used as the whole.',
    'Two fractions are equivalent when they land on the same point on the number line; 2/4 and 1/2 are equivalent because they mark the midpoint.',
]
EXAMPLE_BAD_MISC = ['Students may not understand fractions.']
EXAMPLE_GOOD_MISC = [
    'A larger denominator means a larger fraction — students believe 1/8 > 1/4 because 8 > 4, when the reverse is true because each piece is smaller when the whole is divided into more parts.',
    'Equal parts means the same number of parts, not the same size; students accept unequally-cut slices as valid fractions, but fractions require equal-sized parts.',
]

def build_prompt(node: dict) -> str:
    wmc        = node["working_memory_ceiling"]
    fact_target = wmc
    fact_min   = max(2, wmc - 1)
    misc_count = 1 if wmc <= 3 else (2 if wmc <= 5 else 3)

    node_json = json.dumps(node, ensure_ascii=False, indent=2)

    return f"""You are building the lesson skeleton for Ninereeds, a small AI being trained on a structured K-8 curriculum. Generate two fields for the curriculum node below.

## Node

{node_json}

## Your task

**`facts`** — {fact_min} to {fact_target} statements (target: {fact_target}).
Each fact must:
- Be a specific, standalone true statement that a probe could test
- Contain explanatory tension: prefer "X is Y because Z" or "X is Y, not A" over bare "X is Y"
- Naturally use vocabulary from vocab_anchors where it fits (not forced)
- Respect boundary_scope: do not reference any concept from `deferred`
- Not define a term using the term itself

**`misconceptions`** — exactly {misc_count} statement(s).
Each misconception must:
- Name the specific error a student at this grade actually makes (not "students may confuse X and Y")
- Be something a learner genuinely believes, not an artifact of how the concept is labeled in this dataset
- Be correctable by one of the facts above

## Quality contrast (MATH-G3-FRC-001, fractions)

BAD facts (reject these patterns):
{chr(10).join(f'× "{f}"' for f in EXAMPLE_BAD_FACTS)}

GOOD facts (aim for this):
{chr(10).join(f'✓ "{f}"' for f in EXAMPLE_GOOD_FACTS)}

BAD misconception:
{chr(10).join(f'× "{m}"' for m in EXAMPLE_BAD_MISC)}

GOOD misconceptions:
{chr(10).join(f'✓ "{m}"' for m in EXAMPLE_GOOD_MISC)}

## Output format

Return ONLY valid JSON with exactly two keys: "facts" (array of strings) and "misconceptions" (array of strings). No explanation, no markdown fences, no other text."""


# ── API call ──────────────────────────────────────────────────────────────────

_lock = threading.Lock()

def call_api(prompt: str):
    last_err = None
    for client, model, extra in SOURCES:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=8192,
                temperature=0.3,
                **extra,
            )
            content = resp.choices[0].message.content
            if content and content.strip():
                return content.strip(), model
        except Exception as e:
            last_err = e
    raise RuntimeError(f"All sources failed: {last_err}")


def process_node(node: dict, force: bool = False) -> dict | None:
    nid     = node["id"]
    outfile = OUTDIR / f"{nid}.json"

    if outfile.exists() and not force:
        return None  # already done

    prompt   = build_prompt(node)
    wmc      = node["working_memory_ceiling"]
    fact_min = max(2, wmc - 1)

    t0 = time.time()
    try:
        raw, model = call_api(prompt)
    except Exception as e:
        with _lock:
            print(f"  FAIL {nid}: {e}", flush=True)
        return {"id": nid, "error": str(e)}

    elapsed = time.time() - t0

    # Strip markdown fences
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        (OUTDIR / f"{nid}_raw.txt").write_text(raw)
        with _lock:
            print(f"  PARSE ERR {nid}: {e}", flush=True)
        return {"id": nid, "error": f"json: {e}"}

    facts = parsed.get("facts", [])
    miscs = parsed.get("misconceptions", [])
    ok    = "✓" if (len(facts) >= fact_min and len(miscs) >= 1) else "⚠"

    result = {
        "id":             nid,
        "wmc":            wmc,
        "grade_level":    node["grade_level"],
        "domain":         node["domain"],
        "core_concept":   node["core_concept"],
        "facts":          facts,
        "misconceptions": miscs,
        "model":          model,
        "elapsed_s":      round(elapsed, 1),
    }
    outfile.write_text(json.dumps(result, ensure_ascii=False, indent=2))

    with _lock:
        print(f"  {ok} {nid} {len(facts)}f/{len(miscs)}m [{model.split('/')[-1][:16]}] {elapsed:.0f}s", flush=True)

    return result


# ── Merge into phase2_merged.jsonl ────────────────────────────────────────────

def merge():
    outfile = BASE / "phase2_merged.jsonl"
    results = []
    errors  = []
    for p in sorted(OUTDIR.glob("*.json")):
        if p.name.endswith("_raw.txt"):
            continue
        r = json.loads(p.read_text())
        if "error" in r:
            errors.append(r["id"])
        else:
            results.append(r)
    outfile.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in results) + "\n")
    print(f"Merged {len(results)} nodes → {outfile}")
    if errors:
        print(f"  {len(errors)} errors (not merged): {errors}")


# ── Main ──────────────────────────────────────────────────────────────────────

def load_nodes(domain_filter=None):
    nodes = []
    for f in ["phase1_preschool.jsonl", "phase1_k8.jsonl"]:
        for line in (BASE / f).read_text().splitlines():
            if not line.strip(): continue
            e = json.loads(line)
            if domain_filter and e["domain"] != domain_filter:
                continue
            nodes.append(e)
    return nodes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers",      type=int, default=6)
    ap.add_argument("--domain",       type=str, default=None, help="filter to one domain")
    ap.add_argument("--rerun-failed", action="store_true",    help="re-run nodes with error output")
    ap.add_argument("--merge",        action="store_true",    help="merge outputs to phase2_merged.jsonl")
    args = ap.parse_args()

    if args.merge:
        merge()
        return

    OUTDIR.mkdir(parents=True, exist_ok=True)

    nodes = load_nodes(args.domain)
    if args.rerun_failed:
        failed_ids = set()
        for p in OUTDIR.glob("*.json"):
            r = json.loads(p.read_text())
            if "error" in r:
                failed_ids.add(r["id"])
                p.unlink()
        nodes = [n for n in nodes if n["id"] in failed_ids]
        print(f"Re-running {len(nodes)} failed nodes...")

    todo = [n for n in nodes if not (OUTDIR / f"{n['id']}.json").exists()]
    done = len(nodes) - len(todo)
    print(f"Phase 2: {len(nodes)} nodes total, {done} already done, {len(todo)} to generate.")
    if not todo:
        print("Nothing to do.")
        return

    ok = err = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(process_node, n): n for n in todo}
        for fut in concurrent.futures.as_completed(futures):
            r = fut.result()
            if r and "error" in r:
                err += 1
            elif r:
                ok += 1

    print(f"\nDone: {ok} generated, {err} errors. Run --merge when complete.")


if __name__ == "__main__":
    main()

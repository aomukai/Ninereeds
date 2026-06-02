#!/usr/bin/env python3
"""
brain_map.py — Activation atlas for a BDH checkpoint.

Records xy_sparse (Hebbian co-firing signal) at the last prompt-token position
across all layers for a structured probe set. Generates a cosine similarity
heatmap and t-SNE scatter to reveal whether concepts form clean semantic
clusters in the model's internal representation space.

Python: /home/aomukai/.unsloth/studio/unsloth_studio/bin/python
Run from: ~/Ninereeds/  (where torch is installed)

Commands:
  probe  — run probe pass, save activations + metadata
  map    — generate visualizations from saved activations
  run    — probe then map (default)

Usage:
  python3 meta/scripts/brain_map.py run
  python3 meta/scripts/brain_map.py run --checkpoint checkpoints/c13_Phase_C_winner.pt
  python3 meta/scripts/brain_map.py probe --checkpoint checkpoints/c13_Phase_C_winner.pt
  python3 meta/scripts/brain_map.py map
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEFAULT_CHECKPOINT = ROOT / "checkpoints" / "c13_Phase_C_winner.pt"
OUT_ACTIVATIONS    = ROOT / "tmp" / "brain_map_activations.npz"
OUT_PROBES         = ROOT / "tmp" / "brain_map_probes.jsonl"
OUT_HEATMAP        = ROOT / "tmp" / "brain_map_similarity.png"
OUT_SCATTER        = ROOT / "tmp" / "brain_map_scatter.png"

SEED = 42

# Phase A noun concepts — concrete, succeeded in C13
PHASE_A_DIR  = ROOT / "training_data" / "phase_A"
# Phase B social/agent concepts — succeeded in C13
PHASE_B_DIR  = ROOT / "training_data" / "phase_B"

# B/D/E words that failed in C13 — hardcoded representative set
EMOTION_WORDS = [
    "sadness", "happiness", "fear", "anger", "joy", "grief",
    "loneliness", "excitement", "anxiety", "hope", "pride",
    "shame", "jealousy", "disgust", "surprise", "envy",
    "guilt", "relief", "frustration", "curiosity",
]
COGNITIVE_WORDS = [
    "thinking", "remembering", "knowing", "believing", "understanding",
    "imagining", "wondering", "deciding", "forgetting", "learning",
    "reasoning", "doubting", "suspecting", "realising", "expecting",
]

# Concepts for multilingual cross-language probe (same concept × 4 languages)
# These are concrete Phase A nouns we're confident the model has seen
MULTILINGUAL_CONCEPTS = [
    ("dog",   "Hund",   "犬",   "狗"),
    ("rain",  "Regen",  "雨",   "雨"),
    ("stone", "Stein",  "石",   "石"),
    ("cat",   "Katze",  "猫",   "貓"),
    ("tree",  "Baum",   "木",   "樹"),
]

# German grammar completions — dative and accusative
GRAMMAR_PROBES = [
    # über + dative (static location)
    ("grammar_dative",   "A cloud is above the tree.\nEine Wolke ist "),
    ("grammar_dative",   "A bird sits above the house.\nEin Vogel sitzt über "),
    ("grammar_dative",   "The sun shines above the field.\nDie Sonne scheint über "),
    ("grammar_dative",   "Smoke rises above the barn.\nRauch steigt über "),
    ("grammar_dative",   "Stars hang above the village.\nSterne hängen über "),
    # in + dative (static)
    ("grammar_dative",   "The cat is in the barn.\nDie Katze ist in "),
    ("grammar_dative",   "The child is in the garden.\nDas Kind ist in "),
    # in + accusative (movement)
    ("grammar_accusative", "The child runs into the field.\nDas Kind läuft in "),
    ("grammar_accusative", "The dog jumps into the barn.\nDer Hund springt in "),
    ("grammar_accusative", "The stone falls into the water.\nDer Stein fällt in "),
    # mit + dative
    ("grammar_dative",   "She walks with the dog.\nSie geht mit "),
    ("grammar_dative",   "He works with a stone.\nEr arbeitet mit "),
    # German V2 word order
    ("grammar_v2",       "Today the dog runs fast.\nHeute läuft "),
    ("grammar_v2",       "In the morning the child wakes.\nAm Morgen erwacht "),
    ("grammar_v2",       "By the well the old woman stands.\nAm Brunnen steht "),
    # Artikel (der/die/das)
    ("grammar_artikel",  "A dog is an animal.\nEin Hund ist "),
    ("grammar_artikel",  "A cat is an animal.\nEine Katze ist "),
    ("grammar_artikel",  "Rain is water.\nRegen ist "),
    ("grammar_artikel",  "A tree is a plant.\nEin Baum ist "),
    ("grammar_artikel",  "A child is a person.\nEin Kind ist "),
]

# Arithmetic probes
ARITHMETIC_PROBES = [
    (1, 1), (1, 2), (2, 2), (2, 3), (3, 3),
    (1, 4), (2, 4), (3, 4), (4, 4), (1, 5),
    (2, 5), (3, 5), (4, 5), (5, 5), (0, 1),
]
_NUM = {0:"zero",1:"one",2:"two",3:"three",4:"four",5:"five",
        6:"six",7:"seven",8:"eight",9:"nine",10:"ten"}


# ---------------------------------------------------------------------------
# Probe builders
# ---------------------------------------------------------------------------

def _en_files(directory: Path, max_n: int, rng: random.Random) -> list[Path]:
    files = [f for f in directory.glob("*.md")
             if not any(f.name.endswith(s) for s in ("_DE.md","_JP.md","_ZH.md"))]
    return rng.sample(files, min(max_n, len(files)))


def _first_user_question(fpath: Path) -> str | None:
    for line in fpath.read_text(encoding="utf-8").splitlines():
        if line.startswith("[user]"):
            return line[6:].strip()
    return None


def build_phase_a_probes(rng: random.Random, n: int = 50) -> list[dict]:
    probes = []
    if not PHASE_A_DIR.exists():
        return probes
    for fpath in _en_files(PHASE_A_DIR, n, rng):
        q = _first_user_question(fpath)
        if q:
            label = fpath.stem
            probes.append({
                "label":    label,
                "category": "phase_a",
                "prompt":   f"[user]{q}\n[Ninereeds]",
            })
    return probes


def build_phase_b_probes(rng: random.Random, n: int = 40) -> list[dict]:
    probes = []
    if not PHASE_B_DIR.exists():
        return probes
    for fpath in _en_files(PHASE_B_DIR, n, rng):
        q = _first_user_question(fpath)
        if q:
            label = fpath.stem
            probes.append({
                "label":    label,
                "category": "phase_b",
                "prompt":   f"[user]{q}\n[Ninereeds]",
            })
    return probes


def build_emotion_probes(words: list[str]) -> list[dict]:
    return [
        {
            "label":    w,
            "category": "emotion",
            "prompt":   f"[user]What does {w} look like?\n[Ninereeds]",
        }
        for w in words
    ]


def build_cognitive_probes(words: list[str]) -> list[dict]:
    return [
        {
            "label":    w,
            "category": "cognitive",
            "prompt":   f"[user]What does it mean to be {w}?\n[Ninereeds]",
        }
        for w in words
    ]


def build_grammar_probes() -> list[dict]:
    return [
        {
            "label":    f"{cat}_{i}",
            "category": cat,
            "prompt":   prompt,
        }
        for i, (cat, prompt) in enumerate(GRAMMAR_PROBES)
    ]


def build_arithmetic_probes(pairs: list[tuple]) -> list[dict]:
    return [
        {
            "label":    f"{a}+{b}",
            "category": "arithmetic",
            "prompt":   f"[user]What is {_NUM[a]} plus {_NUM[b]}?\n[Ninereeds]",
        }
        for a, b in pairs
    ]


def build_multilingual_probes(concepts: list[tuple]) -> list[dict]:
    """
    For each concept, one probe in each of EN, DE, JP, ZH.
    Tests whether same-concept probes cluster by concept or by language.
    """
    probes = []
    # Language-specific question formats derived from actual phase_A file format
    for en, de, jp, zh in concepts:
        probes += [
            {
                "label":    f"ml_{en}_EN",
                "category": "multilingual_EN",
                "prompt":   f"[user]What does a {en} look like?\n[Ninereeds]",
            },
            {
                "label":    f"ml_{en}_DE",
                "category": "multilingual_DE",
                "prompt":   f"[user]Wie sieht ein {de} aus?\n[Ninereeds]",
            },
            {
                "label":    f"ml_{en}_JP",
                "category": "multilingual_JP",
                "prompt":   f"[user]{jp}はどんな様子か？\n[Ninereeds]",
            },
            {
                "label":    f"ml_{en}_ZH",
                "category": "multilingual_ZH",
                "prompt":   f"[user]{zh}看起來是什麼樣子？\n[Ninereeds]",
            },
        ]
    return probes


def build_all_probes(rng: random.Random) -> list[dict]:
    probes: list[dict] = []
    probes += build_phase_a_probes(rng, 50)
    probes += build_phase_b_probes(rng, 40)
    probes += build_emotion_probes(EMOTION_WORDS)
    probes += build_cognitive_probes(COGNITIVE_WORDS)
    probes += build_grammar_probes()
    probes += build_arithmetic_probes(ARITHMETIC_PROBES)
    probes += build_multilingual_probes(MULTILINGUAL_CONCEPTS)
    return probes


# ---------------------------------------------------------------------------
# Activation capture
# ---------------------------------------------------------------------------

def encode_prompt(text: str) -> list[int]:
    return list(text.encode("utf-8", errors="replace"))


def forward_with_activations(model, idx):
    """
    Replicate BDH.forward() with xy_sparse captured at the last prompt token.
    Does NOT modify bdh.py. Model must be in eval() mode.

    Returns: list of tensors, one per layer, each shape (n_head, N).
    The xy_sparse tensor is the Hebbian co-firing signal: neurons that fired
    together for the query (x_sparse) and the context response (y_sparse).
    """
    import torch
    import torch.nn.functional as F

    C = model.config
    B, T = idx.size()
    D    = C.n_embd
    nh   = C.n_head
    N    = D * C.mlp_internal_dim_multiplier // nh

    x = model.embed(idx).unsqueeze(1)   # B, 1, T, D
    x = model.ln(x)

    captured: list = []

    for level in range(C.n_layer):
        if C.per_layer_weights:
            encoder   = model.encoder[level]
            encoder_v = model.encoder_v[level]
            decoder   = model.decoder[level]
        else:
            encoder   = model.encoder
            encoder_v = model.encoder_v
            decoder   = model.decoder

        x_latent  = x @ encoder                       # B, nh, T, N
        x_sparse  = F.relu(x_latent)                  # sparsity: ~3-5% active

        yKV       = model.attn(Q=x_sparse, K=x_sparse, V=x)
        yKV       = model.ln(yKV)
        y_latent  = yKV @ encoder_v
        y_sparse  = F.relu(y_latent)
        xy_sparse = x_sparse * y_sparse               # Hebbian co-firing: B, nh, T, N

        # Capture last token position — the prompt's accumulated "understanding"
        captured.append(xy_sparse[0, :, -1, :].detach().cpu())   # (nh, N)

        # Continue forward (eval mode → dropout is identity)
        yMLP = (
            xy_sparse.transpose(1, 2).reshape(B, 1, T, N * nh) @ decoder
        )                                             # B, 1, T, D
        y = model.ln(yMLP)
        x = model.ln(x + y)

    return captured   # list[n_layer] of (nh, N)


def activation_vector(captured: list) -> "np.ndarray":
    """Flatten all layer activations to a single 1-D numpy vector."""
    import numpy as np
    parts = [layer.numpy().ravel() for layer in captured]
    return np.concatenate(parts)


# ---------------------------------------------------------------------------
# Load model
# ---------------------------------------------------------------------------

def load_model(checkpoint_path: Path):
    import torch
    sys.path.insert(0, str(ROOT))
    from bdh import BDH, BDHConfig
    from inference import BDHInference

    torch.serialization.add_safe_globals([BDHConfig])
    ck     = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    config = ck.get("config")
    if isinstance(config, dict):
        config = BDHConfig(**config)
    if config is None:
        config = BDHConfig()

    model = BDH(config)
    state = (ck.get("model_state_dict") or ck.get("model")
             or ck.get("state_dict") or ck)
    model.load_state_dict(state, strict=False)
    model.eval()
    return model


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_probe(args):
    import torch
    import numpy as np

    checkpoint = Path(args.checkpoint)
    if not checkpoint.exists():
        sys.exit(f"Checkpoint not found: {checkpoint}")

    rng    = random.Random(SEED)
    probes = build_all_probes(rng)
    print(f"Probe set: {len(probes)} probes")

    by_cat = {}
    for p in probes:
        by_cat.setdefault(p["category"], 0)
        by_cat[p["category"]] += 1
    for cat, n in sorted(by_cat.items()):
        print(f"  {cat}: {n}")
    print()

    print(f"Loading checkpoint: {checkpoint}")
    model = load_model(checkpoint)
    print(f"Config: {model.config}")

    C  = model.config
    N  = C.n_embd * C.mlp_internal_dim_multiplier // C.n_head
    dim = C.n_layer * C.n_head * N
    print(f"Activation vector dim: {C.n_layer} layers × {C.n_head} heads × {N} = {dim:,}")
    print()

    vectors   = np.zeros((len(probes), dim), dtype=np.float32)
    meta      = []

    for i, probe in enumerate(probes):
        tokens = encode_prompt(probe["prompt"])
        idx    = torch.tensor([tokens], dtype=torch.long)
        with torch.no_grad():
            captured = forward_with_activations(model, idx)
        vec          = activation_vector(captured)
        vectors[i]   = vec
        sparsity     = (vec > 0).mean()
        meta.append({**probe, "sparsity": float(sparsity)})

        if (i + 1) % 25 == 0 or i == len(probes) - 1:
            print(f"  [{i+1:3d}/{len(probes)}]  last: '{probe['label']}'  "
                  f"sparsity={sparsity:.3f}")

    OUT_ACTIVATIONS.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(str(OUT_ACTIVATIONS), activations=vectors)
    OUT_PROBES.write_text(
        "\n".join(json.dumps(m, ensure_ascii=False) for m in meta) + "\n",
        encoding="utf-8",
    )
    avg_sparsity = np.mean([m["sparsity"] for m in meta])
    print(f"\nSaved: {OUT_ACTIVATIONS}")
    print(f"Saved: {OUT_PROBES}")
    print(f"Average sparsity: {avg_sparsity:.3f}  "
          f"(~{avg_sparsity * dim:.0f} active neurons per probe out of {dim:,})")


def cmd_map(args):
    import numpy as np

    if not OUT_ACTIVATIONS.exists():
        sys.exit(f"No activations found. Run: probe first.")

    data    = np.load(str(OUT_ACTIVATIONS))
    vectors = data["activations"]          # (n_probes, dim)
    probes  = [json.loads(l)
               for l in OUT_PROBES.read_text(encoding="utf-8").splitlines()
               if l.strip()]
    labels   = [p["label"]    for p in probes]
    cats     = [p["category"] for p in probes]
    n        = len(probes)
    print(f"Loaded {n} probe activations, dim={vectors.shape[1]:,}")

    # ── Cosine similarity ─────────────────────────────────────────────────
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)   # avoid divide-by-zero (untrained = zero vec)
    normed = vectors / norms
    sim    = normed @ normed.T                  # (n, n) cosine similarity matrix

    # Sort probes by category for clean block structure in heatmap
    category_order = [
        "phase_a", "phase_b",
        "emotion", "cognitive",
        "grammar_dative", "grammar_accusative", "grammar_v2", "grammar_artikel",
        "arithmetic",
        "multilingual_EN", "multilingual_DE", "multilingual_JP", "multilingual_ZH",
    ]
    cat_priority = {c: i for i, c in enumerate(category_order)}
    order   = sorted(range(n), key=lambda i: (cat_priority.get(cats[i], 99), labels[i]))
    sim_ord = sim[np.ix_(order, order)]
    labs_ord = [labels[i] for i in order]
    cats_ord = [cats[i]   for i in order]

    _heatmap(sim_ord, labs_ord, cats_ord)

    # ── 2-D scatter (t-SNE or PCA fallback) ──────────────────────────────
    _scatter(vectors, labels, cats)


def _heatmap(sim: "np.ndarray", labels: list[str], cats: list[str]):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np

    n = len(labels)

    PALETTE = {
        "phase_a":          "#2196F3",   # blue — succeeded
        "phase_b":          "#4CAF50",   # green — succeeded
        "emotion":          "#F44336",   # red — failed B/D/E
        "cognitive":        "#FF9800",   # orange — failed B/D/E
        "grammar_dative":   "#9C27B0",   # purple — grammar
        "grammar_accusative":"#7B1FA2",
        "grammar_v2":       "#CE93D8",
        "grammar_artikel":  "#E1BEE7",
        "arithmetic":       "#795548",   # brown
        "multilingual_EN":  "#00BCD4",   # cyan family — multilingual
        "multilingual_DE":  "#0097A7",
        "multilingual_JP":  "#006064",
        "multilingual_ZH":  "#80DEEA",
    }

    fig, ax = plt.subplots(figsize=(14, 12))
    im = ax.imshow(sim, vmin=-0.1, vmax=1.0, cmap="RdYlGn", aspect="auto")
    plt.colorbar(im, ax=ax, shrink=0.6, label="Cosine similarity")

    # Category boundary lines
    prev_cat = None
    for i, cat in enumerate(cats):
        if cat != prev_cat and i > 0:
            ax.axhline(i - 0.5, color="white", lw=1.5, alpha=0.8)
            ax.axvline(i - 0.5, color="white", lw=1.5, alpha=0.8)
        prev_cat = cat

    # Axis tick labels — show label, coloured by category
    tick_cols = [PALETTE.get(c, "#999999") for c in cats]
    short = [l[:18] for l in labels]
    ax.set_xticks(range(n))
    ax.set_xticklabels(short, rotation=90, fontsize=4)
    ax.set_yticks(range(n))
    ax.set_yticklabels(short, fontsize=4)

    for tick, col in zip(ax.get_xticklabels(), tick_cols):
        tick.set_color(col)
    for tick, col in zip(ax.get_yticklabels(), tick_cols):
        tick.set_color(col)

    # Legend
    seen = {}
    for cat in cats:
        if cat not in seen:
            seen[cat] = mpatches.Patch(color=PALETTE.get(cat, "#999999"),
                                       label=cat.replace("_", " "))
    ax.legend(handles=list(seen.values()), loc="lower right",
              fontsize=7, framealpha=0.8)

    # Intra-category mean similarity annotations per block diagonal
    prev_cat, block_start = None, 0
    block_means = []
    for i, cat in enumerate(cats + [None]):
        if cat != prev_cat:
            if prev_cat is not None and i - block_start > 1:
                block = sim[block_start:i, block_start:i]
                mask  = np.triu(np.ones_like(block, dtype=bool), k=1)
                if mask.any():
                    mean_sim = block[mask].mean()
                    block_means.append((prev_cat, block_start, i, mean_sim))
            block_start = i
            prev_cat = cat

    ax.set_title(
        "BDH C13 Winner — Concept Activation Similarity (xy_sparse, last token)\n"
        + "  ".join(f"{cat.replace('_',' ')}: μ={ms:.2f}"
                    for cat, _, _, ms in block_means),
        fontsize=9,
    )

    plt.tight_layout()
    plt.savefig(str(OUT_HEATMAP), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Heatmap saved: {OUT_HEATMAP}")

    # Print block diagonal means to console
    print("\nIntra-category mean cosine similarity (diagonal blocks):")
    for cat, s, e, ms in sorted(block_means, key=lambda x: -x[3]):
        print(f"  {cat:<25}  n={e-s:3d}  mean_sim={ms:.3f}")


def _scatter(vectors: "np.ndarray", labels: list[str], cats: list[str]):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    PALETTE = {
        "phase_a":          "#2196F3",
        "phase_b":          "#4CAF50",
        "emotion":          "#F44336",
        "cognitive":        "#FF9800",
        "grammar_dative":   "#9C27B0",
        "grammar_accusative":"#7B1FA2",
        "grammar_v2":       "#CE93D8",
        "grammar_artikel":  "#E1BEE7",
        "arithmetic":       "#795548",
        "multilingual_EN":  "#00BCD4",
        "multilingual_DE":  "#0097A7",
        "multilingual_JP":  "#006064",
        "multilingual_ZH":  "#80DEEA",
    }

    # Try t-SNE first, fall back to PCA
    try:
        from sklearn.manifold import TSNE
        reducer = TSNE(n_components=2, random_state=SEED, perplexity=min(30, len(labels)//3),
                       n_iter=1000, init="pca")
        method  = "t-SNE"
        coords  = reducer.fit_transform(vectors)
    except Exception:
        from sklearn.decomposition import PCA
        reducer = PCA(n_components=2, random_state=SEED)
        method  = "PCA"
        coords  = reducer.fit_transform(vectors)

    fig, ax = plt.subplots(figsize=(13, 10))
    colours = [PALETTE.get(c, "#999999") for c in cats]
    ax.scatter(coords[:, 0], coords[:, 1], c=colours, s=30, alpha=0.8, linewidths=0.3,
               edgecolors="black")

    # Label a subset of points — the multilingual pairs and a few anchors
    for i, (label, cat) in enumerate(zip(labels, cats)):
        if cat.startswith("multilingual") or cat == "arithmetic":
            ax.annotate(label, coords[i], fontsize=5, alpha=0.8,
                        xytext=(3, 3), textcoords="offset points")

    # Legend
    import matplotlib.patches as mpatches
    seen = {}
    for cat in cats:
        if cat not in seen:
            seen[cat] = mpatches.Patch(color=PALETTE.get(cat, "#999999"),
                                       label=cat.replace("_", " "))
    ax.legend(handles=list(seen.values()), fontsize=7, loc="best", framealpha=0.8)
    ax.set_title(f"BDH C13 Winner — {method} of xy_sparse activations\n"
                 "Each point = one probe; colour = category", fontsize=10)
    ax.set_xlabel(f"{method} dim 1")
    ax.set_ylabel(f"{method} dim 2")

    plt.tight_layout()
    plt.savefig(str(OUT_SCATTER), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Scatter ({method}) saved: {OUT_SCATTER}")


def cmd_run(args):
    cmd_probe(args)
    cmd_map(args)


# ---------------------------------------------------------------------------
# Hub detection
# ---------------------------------------------------------------------------

def detect_hubs(vectors: "np.ndarray", cats: list[str],
                hub_threshold: float = 0.7) -> "np.ndarray":
    """
    For each neuron, compute category breadth: fraction of distinct categories
    in which it fires (activation > 0) in at least one probe.

    Neurons above hub_threshold are routing hubs — they activate regardless of
    concept category and carry no semantic specificity.

    Returns a boolean mask of shape (dim,): True = routing hub.
    """
    import numpy as np

    unique_cats = sorted(set(cats))
    n_cats      = len(unique_cats)
    cat_idx     = {c: i for i, c in enumerate(unique_cats)}
    dim         = vectors.shape[1]

    # For each neuron × category: does it fire in at least one probe of that category?
    coverage = np.zeros((dim, n_cats), dtype=bool)
    for probe_i, cat in enumerate(cats):
        ci            = cat_idx[cat]
        coverage[:, ci] |= (vectors[probe_i] > 0)

    breadth          = coverage.sum(axis=1)            # (dim,) int
    breadth_fraction = breadth / n_cats                # (dim,) float
    hub_mask         = breadth_fraction >= hub_threshold

    return hub_mask, breadth, breadth_fraction, unique_cats, coverage


def cmd_hubs(args):
    import numpy as np
    import json as _json

    if not OUT_ACTIVATIONS.exists():
        sys.exit("No activations found. Run: probe first.")

    hub_threshold = args.threshold

    data    = np.load(str(OUT_ACTIVATIONS))
    vectors = data["activations"]
    probes  = [_json.loads(l)
               for l in OUT_PROBES.read_text(encoding="utf-8").splitlines()
               if l.strip()]
    labels  = [p["label"]    for p in probes]
    cats    = [p["category"] for p in probes]
    n, dim  = vectors.shape

    # Model geometry — reconstruct from dim
    # dim = n_layer * n_head * N  where N = n_embd * mlp_mult // n_head
    # For C13: 6 * 4 * 8192 = 196,608
    n_layer, n_head, N = 6, 4, 8192   # hardcoded for C13 config
    assert dim == n_layer * n_head * N, f"Unexpected dim {dim}"

    hub_mask, breadth, breadth_frac, unique_cats, coverage = detect_hubs(
        vectors, cats, hub_threshold
    )

    n_hubs     = hub_mask.sum()
    n_semantic = (breadth == 1).sum()
    n_silent   = (breadth == 0).sum()

    print(f"Hub threshold: {hub_threshold:.0%} of {len(unique_cats)} categories "
          f"= fires in ≥ {int(hub_threshold * len(unique_cats))} categories")
    print(f"Total neurons:   {dim:>8,}")
    print(f"Routing hubs:    {n_hubs:>8,}  ({n_hubs/dim:.2%})")
    print(f"Semantic (1 cat):{n_semantic:>8,}  ({n_semantic/dim:.2%})")
    print(f"Silent (0 cats): {n_silent:>8,}  ({n_silent/dim:.2%})")

    # Hub distribution across layers and heads
    print("\nHub count per layer × head:")
    hub_indices = np.where(hub_mask)[0]
    layer_head_counts = {}
    for idx in hub_indices:
        layer = idx // (n_head * N)
        head  = (idx % (n_head * N)) // N
        layer_head_counts[(layer, head)] = layer_head_counts.get((layer, head), 0) + 1
    for (layer, head), count in sorted(layer_head_counts.items()):
        bar = "█" * (count // 50)
        print(f"  L{layer} H{head}: {count:5d}  {bar}")

    # Category-specific neuron counts (fires in exactly 1 category)
    print("\nSemantic neuron count per category (fires in exactly 1):")
    for ci, cat in enumerate(unique_cats):
        exclusive = ((breadth == 1) & coverage[:, ci]).sum()
        print(f"  {cat:<25}  {exclusive:>6,}")

    # Intra-category similarity before and after hub removal
    def mean_sim_by_cat(vecs):
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        normed = vecs / norms
        results = {}
        for cat in unique_cats:
            idx = [i for i, c in enumerate(cats) if c == cat]
            if len(idx) < 2:
                continue
            sub = normed[idx]
            sim = sub @ sub.T
            mask = np.triu(np.ones((len(idx), len(idx)), dtype=bool), k=1)
            results[cat] = sim[mask].mean()
        return results

    before = mean_sim_by_cat(vectors)
    vectors_no_hubs = vectors.copy()
    vectors_no_hubs[:, hub_mask] = 0.0
    after  = mean_sim_by_cat(vectors_no_hubs)

    print("\nIntra-category similarity — before vs after hub removal:")
    print(f"  {'Category':<25}  {'Before':>7}  {'After':>7}  {'Delta':>7}")
    for cat in sorted(before, key=lambda c: after.get(c, 0) - before.get(c, 0), reverse=True):
        b = before.get(cat, 0)
        a = after.get(cat, 0)
        print(f"  {cat:<25}  {b:>7.3f}  {a:>7.3f}  {a-b:>+7.3f}")

    # Save hub report
    out_hubs = ROOT / "tmp" / "brain_map_hubs.json"
    report = {
        "hub_threshold":    hub_threshold,
        "n_categories":     len(unique_cats),
        "dim":              int(dim),
        "n_hubs":           int(n_hubs),
        "n_semantic":       int(n_semantic),
        "n_silent":         int(n_silent),
        "hub_pct":          float(n_hubs / dim),
        "layer_head_hubs":  {f"L{l}H{h}": c for (l, h), c in layer_head_counts.items()},
        "similarity_before": {k: float(v) for k, v in before.items()},
        "similarity_after":  {k: float(v) for k, v in after.items()},
    }
    out_hubs.write_text(_json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nHub report saved: {out_hubs}")

    # Hub-filtered heatmap
    out_heatmap_nohubs = ROOT / "tmp" / "brain_map_similarity_nohubs.png"
    _heatmap_filtered(vectors_no_hubs, labels, cats, out_heatmap_nohubs,
                      title_suffix=f" (routing hubs removed, threshold={hub_threshold:.0%})")


def _heatmap_filtered(vectors: "np.ndarray", labels: list[str], cats: list[str],
                      out_path: Path, title_suffix: str = ""):
    """Generate a cosine similarity heatmap from arbitrary activation vectors."""
    import numpy as np

    norms  = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms  = np.where(norms == 0, 1.0, norms)
    normed = vectors / norms
    sim    = normed @ normed.T

    category_order = [
        "phase_a", "phase_b",
        "emotion", "cognitive",
        "grammar_dative", "grammar_accusative", "grammar_v2", "grammar_artikel",
        "arithmetic",
        "multilingual_EN", "multilingual_DE", "multilingual_JP", "multilingual_ZH",
    ]
    cat_priority = {c: i for i, c in enumerate(category_order)}
    order    = sorted(range(len(labels)),
                      key=lambda i: (cat_priority.get(cats[i], 99), labels[i]))
    sim_ord  = sim[np.ix_(order, order)]
    labs_ord = [labels[i] for i in order]
    cats_ord = [cats[i]   for i in order]

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    PALETTE = {
        "phase_a": "#2196F3", "phase_b": "#4CAF50",
        "emotion": "#F44336", "cognitive": "#FF9800",
        "grammar_dative": "#9C27B0", "grammar_accusative": "#7B1FA2",
        "grammar_v2": "#CE93D8", "grammar_artikel": "#E1BEE7",
        "arithmetic": "#795548",
        "multilingual_EN": "#00BCD4", "multilingual_DE": "#0097A7",
        "multilingual_JP": "#006064", "multilingual_ZH": "#80DEEA",
    }

    n   = len(labs_ord)
    fig, ax = plt.subplots(figsize=(14, 12))
    im  = ax.imshow(sim_ord, vmin=-0.1, vmax=1.0, cmap="RdYlGn", aspect="auto")
    plt.colorbar(im, ax=ax, shrink=0.6, label="Cosine similarity")

    prev_cat = None
    for i, cat in enumerate(cats_ord):
        if cat != prev_cat and i > 0:
            ax.axhline(i - 0.5, color="white", lw=1.5, alpha=0.8)
            ax.axvline(i - 0.5, color="white", lw=1.5, alpha=0.8)
        prev_cat = cat

    tick_cols = [PALETTE.get(c, "#999999") for c in cats_ord]
    short     = [l[:18] for l in labs_ord]
    ax.set_xticks(range(n)); ax.set_xticklabels(short, rotation=90, fontsize=4)
    ax.set_yticks(range(n)); ax.set_yticklabels(short, fontsize=4)
    for tick, col in zip(ax.get_xticklabels(), tick_cols): tick.set_color(col)
    for tick, col in zip(ax.get_yticklabels(), tick_cols): tick.set_color(col)

    seen = {}
    for cat in cats_ord:
        if cat not in seen:
            seen[cat] = mpatches.Patch(color=PALETTE.get(cat, "#999999"),
                                       label=cat.replace("_", " "))
    ax.legend(handles=list(seen.values()), loc="lower right", fontsize=7, framealpha=0.8)

    # Block diagonal means
    prev_cat, block_start = None, 0
    block_means = []
    for i, cat in enumerate(cats_ord + [None]):
        if cat != prev_cat:
            if prev_cat is not None and i - block_start > 1:
                block = sim_ord[block_start:i, block_start:i]
                mask  = np.triu(np.ones_like(block, dtype=bool), k=1)
                if mask.any():
                    block_means.append((prev_cat, block[mask].mean()))
            block_start = i
            prev_cat = cat

    ax.set_title(
        f"BDH C13 Winner — Activation Similarity{title_suffix}\n"
        + "  ".join(f"{cat.replace('_',' ')}: μ={ms:.2f}" for cat, ms in block_means),
        fontsize=9,
    )
    plt.tight_layout()
    plt.savefig(str(out_path), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Filtered heatmap saved: {out_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    ap  = argparse.ArgumentParser(description="BDH activation atlas.")
    sub = ap.add_subparsers(dest="cmd")

    p_probe = sub.add_parser("probe", help="Run probe pass, save activations")
    p_probe.add_argument("--checkpoint", default=str(DEFAULT_CHECKPOINT))
    p_probe.set_defaults(func=cmd_probe)

    sub.add_parser("map", help="Generate visualizations from saved activations") \
       .set_defaults(func=cmd_map)

    p_hubs = sub.add_parser("hubs", help="Detect routing hubs, generate filtered heatmap")
    p_hubs.add_argument("--threshold", type=float, default=0.7,
                        help="Fraction of categories a neuron must fire in to be a hub (default 0.7)")
    p_hubs.set_defaults(func=cmd_hubs)

    p_run = sub.add_parser("run", help="Probe then map (default)")
    p_run.add_argument("--checkpoint", default=str(DEFAULT_CHECKPOINT))
    p_run.set_defaults(func=cmd_run)

    args = ap.parse_args()

    # Default to run if no subcommand given
    if not hasattr(args, "func"):
        args.func = cmd_run

    args.func(args)


if __name__ == "__main__":
    main()

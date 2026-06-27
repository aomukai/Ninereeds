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
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEFAULT_CHECKPOINT = ROOT / "checkpoints" / "c13_Phase_C_winner.pt"
PROBE_SETS_DIR     = ROOT / "training" / "corpus_admin" / "probe_sets"

SEED = 42

# Phase A/B dirs — used only by the built-in fallback probe builders
PHASE_A_DIR  = ROOT / "training_data" / "01_language" / "phase_A"
PHASE_B_DIR  = ROOT / "training_data" / "01_language" / "phase_B"

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
# Output path helper
# ---------------------------------------------------------------------------

BRAIN_MAPS_DIR = ROOT / "training" / "logs" / "brain_maps"


def _out_paths(name: str | None) -> tuple[Path, Path, Path, Path]:
    """Return (activations, probes, heatmap, scatter) paths, optionally namespaced.

    Activations and probes stay in tmp/ (large intermediates, regeneratable).
    Images go to training/logs/brain_maps/ alongside the campaign reports.
    """
    suffix = f"_{name}" if name else ""
    tmp = ROOT / "tmp"
    BRAIN_MAPS_DIR.mkdir(parents=True, exist_ok=True)
    img_stem = name if name else "brain_map"
    return (
        tmp / f"brain_map{suffix}_activations.npz",
        tmp / f"brain_map{suffix}_probes.jsonl",
        BRAIN_MAPS_DIR / f"{img_stem}_similarity.png",
        BRAIN_MAPS_DIR / f"{img_stem}_scatter.png",
    )


def _trace_paths(name: str | None) -> tuple[Path, Path, Path]:
    """Return (npz, json, markdown_report) paths for richer trace artifacts."""
    suffix = f"_{name}" if name else ""
    stem = name if name else "brain_trace"
    tmp = ROOT / "tmp"
    BRAIN_MAPS_DIR.mkdir(parents=True, exist_ok=True)
    return (
        tmp / f"brain_trace{suffix}.npz",
        BRAIN_MAPS_DIR / f"{stem}_trace.json",
        BRAIN_MAPS_DIR / f"{stem}_trace_report.md",
    )


# ---------------------------------------------------------------------------
# External probe loader
# ---------------------------------------------------------------------------

def load_external_probes(path: Path) -> list[dict]:
    """
    Load a probe set from a JSONL file.
    Required fields: 'prompt', 'category'.
    Optional: 'id' (used as label), 'lang', 'expected_cluster'.
    Lines starting with '#' are ignored.
    """
    probes = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            p = json.loads(line)
            if "label" not in p:
                p["label"] = p.get("id", f"probe_{len(probes)}")
            probes.append(p)
    return probes


TRACE_REQUIRED_FIELDS = {
    "id",
    "campaign",
    "category",
    "language",
    "concept_id",
    "template_id",
    "probe_role",
    "construction_id",
    "source_corpus",
    "prompt",
    "expected_cluster",
    "expected_behavior",
}


def validate_probe_file(path: Path, strict: bool = True) -> tuple[int, list[str]]:
    """Validate probe JSONL metadata for trace-ready scanner use."""
    errors: list[str] = []
    count = 0
    seen_ids: set[str] = set()
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                rec = json.loads(stripped)
            except json.JSONDecodeError as exc:
                errors.append(f"{path}:{lineno}: invalid JSON: {exc}")
                continue
            count += 1
            probe_id = rec.get("id", f"<line {lineno}>")
            if probe_id in seen_ids:
                errors.append(f"{path}:{lineno}: duplicate id `{probe_id}`")
            seen_ids.add(probe_id)
            missing = sorted(k for k in TRACE_REQUIRED_FIELDS
                             if k not in rec or rec[k] in (None, ""))
            if missing:
                errors.append(f"{path}:{lineno}: `{probe_id}` missing {', '.join(missing)}")
            if strict:
                if "lang" in rec and "language" in rec and rec["lang"] != rec["language"]:
                    errors.append(
                        f"{path}:{lineno}: `{probe_id}` lang={rec['lang']} "
                        f"but language={rec['language']}"
                    )
                if rec.get("concept_id") == probe_id:
                    errors.append(f"{path}:{lineno}: `{probe_id}` concept_id falls back to probe id")
    return count, errors


# ---------------------------------------------------------------------------
# Dynamic palette
# ---------------------------------------------------------------------------

# Known categories get consistent colours; unknown ones get auto-assigned.
_KNOWN_COLORS: dict[str, str] = {
    # Language campaign
    "animals":           "#2196F3",
    "animals_boolean":   "#64B5F6",
    "multilingual":      "#00BCD4",
    "vehicles":          "#00ACC1",
    "objects":           "#78909C",
    "boundary":          "#FF7043",
    "emotions":          "#E53935",
    "emotions_boolean":  "#EF9A9A",
    "emotions_boundary": "#FFCDD2",
    "movement":          "#FF8F00",
    "time":              "#FDD835",
    "cognitive":         "#FB8C00",
    "abstract":          "#8E24AA",
    "grammar":           "#6A1B9A",
    "grammar_dative":    "#9C27B0",
    "grammar_accusative":"#7B1FA2",
    "grammar_v2":        "#CE93D8",
    "grammar_artikel":   "#E1BEE7",
    "spatial":           "#43A047",
    "arithmetic":        "#795548",
    # Multilingual subcategories
    "multilingual_EN":   "#00BCD4",
    "multilingual_DE":   "#0097A7",
    "multilingual_JP":   "#006064",
    "multilingual_ZH":   "#80DEEA",
    # Legacy (built-in probe builders)
    "phase_a":           "#2196F3",
    "phase_b":           "#4CAF50",
    "emotion":           "#F44336",
    "cognitive_legacy":  "#FF9800",
}
_AUTO_COLORS = [
    "#F06292", "#AED581", "#FFD54F", "#CE93D8", "#80CBC4",
    "#FFAB40", "#B0BEC5", "#A5D6A7", "#F48FB1", "#81D4FA",
]

def make_palette(cats: list[str]) -> dict[str, str]:
    palette: dict[str, str] = {}
    auto_i = 0
    for cat in dict.fromkeys(cats):
        if cat in _KNOWN_COLORS:
            palette[cat] = _KNOWN_COLORS[cat]
        else:
            prefix = cat.split("_")[0]
            if prefix in _KNOWN_COLORS:
                palette[cat] = _KNOWN_COLORS[prefix]
            else:
                palette[cat] = _AUTO_COLORS[auto_i % len(_AUTO_COLORS)]
                auto_i += 1
    return palette


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


def forward_with_activation_trace(model, idx, mode: str = "prompt") -> list:
    """
    Capture xy_sparse across token positions.

    mode:
      last   — only final token, equivalent shape to forward_with_activations
      prompt — every token in idx

    Returns list[n_layer] tensors shaped (n_head, selected_T, N).
    """
    import torch
    import torch.nn.functional as F

    if mode not in {"last", "prompt"}:
        raise ValueError(f"Unsupported trace mode: {mode}")

    C = model.config
    B, T = idx.size()
    D = C.n_embd
    nh = C.n_head
    N = D * C.mlp_internal_dim_multiplier // nh

    x = model.embed(idx).unsqueeze(1)
    x = model.ln(x)

    captured: list = []

    for level in range(C.n_layer):
        if C.per_layer_weights:
            encoder = model.encoder[level]
            encoder_v = model.encoder_v[level]
            decoder = model.decoder[level]
        else:
            encoder = model.encoder
            encoder_v = model.encoder_v
            decoder = model.decoder

        x_latent = x @ encoder
        x_sparse = F.relu(x_latent)

        yKV = model.attn(Q=x_sparse, K=x_sparse, V=x)
        yKV = model.ln(yKV)
        y_latent = yKV @ encoder_v
        y_sparse = F.relu(y_latent)
        xy_sparse = x_sparse * y_sparse

        if mode == "last":
            captured.append(xy_sparse[0, :, -1:, :].detach().cpu())
        else:
            captured.append(xy_sparse[0].detach().cpu())

        yMLP = (
            xy_sparse.transpose(1, 2).reshape(B, 1, T, N * nh) @ decoder
        )
        y = model.ln(yMLP)
        x = model.ln(x + y)

    return captured


def activation_vector(captured: list) -> "np.ndarray":
    """Flatten all layer activations to a single 1-D numpy vector."""
    import numpy as np
    parts = [layer.numpy().ravel() for layer in captured]
    return np.concatenate(parts)


def activation_trace_summary(captured: list, top_k: int) -> dict:
    """
    Summarize a token trace into compact probe-level evidence.

    The full layer/head/neuron x token tensor can be too large to keep for every
    probe. This stores enough to answer: how often did dimensions fire, how
    strong were they, and which dimensions dominated this probe?
    """
    import numpy as np

    # Each layer is (n_head, T, N). Move token dimension first, then flatten.
    per_layer = [layer.numpy().transpose(1, 0, 2).reshape(layer.shape[1], -1)
                 for layer in captured]
    token_vectors = np.concatenate(per_layer, axis=1).astype(np.float32, copy=False)
    active = token_vectors > 0
    fire_rate_by_dim = active.mean(axis=0).astype(np.float32)
    mean_activation_by_dim = token_vectors.mean(axis=0).astype(np.float32)
    max_activation_by_dim = token_vectors.max(axis=0).astype(np.float32)
    ever_active = active.any(axis=0)

    strength = mean_activation_by_dim * np.sqrt(np.maximum(fire_rate_by_dim, 1e-8))
    k = min(top_k, strength.shape[0])
    if k:
        top_idx = np.argpartition(strength, -k)[-k:]
        top_idx = top_idx[np.argsort(strength[top_idx])[::-1]]
    else:
        top_idx = np.array([], dtype=np.int64)

    return {
        "vector": token_vectors[-1].astype(np.float32, copy=False),
        "mean_vector": token_vectors.mean(axis=0).astype(np.float32),
        "fire_rate_by_dim": fire_rate_by_dim,
        "mean_activation_by_dim": mean_activation_by_dim,
        "max_activation_by_dim": max_activation_by_dim,
        "active_mask": ever_active,
        "top_indices": top_idx.astype(np.int32),
        "top_strengths": strength[top_idx].astype(np.float32),
        "token_fire_rate": active.mean(axis=1).astype(np.float32),
        "overall_fire_rate": float(active.mean()),
        "mean_positive_activation": float(token_vectors[active].mean()) if active.any() else 0.0,
    }


def _decode_bytes(tokens) -> str:
    return bytes(int(t) % 256 for t in tokens).decode("utf-8", errors="replace")


def generate_for_trace(model, prompt: str, max_new_tokens: int,
                       temperature: float, top_k: int | None) -> str:
    import torch

    token_ids = encode_prompt(prompt)
    idx = torch.tensor([token_ids], dtype=torch.long)
    with torch.no_grad():
        out = model.generate(idx, max_new_tokens=max_new_tokens,
                             temperature=temperature, top_k=top_k)
    decoded = _decode_bytes(out[0].tolist())
    if decoded.startswith(prompt):
        return decoded[len(prompt):].strip()
    return decoded.strip()


def output_status(text: str) -> str:
    """Cheap behavior label until probe files include authoritative scoring."""
    stripped = text.strip()
    if not stripped:
        return "empty"
    low = stripped.lower()
    if "don't know" in low or "do not know" in low or "i dont know" in low:
        return "unknown"
    if len(stripped) >= 12:
        chunks = [stripped[i:i + 8] for i in range(0, max(0, len(stripped) - 8), 8)]
        if chunks:
            most_common = max(chunks.count(c) for c in set(chunks))
            if most_common >= 5:
                return "loop"
    bad = sum(1 for ch in stripped if ch == "\ufffd" or ord(ch) < 9)
    if bad / max(1, len(stripped)) > 0.05:
        return "garbled"
    return "generated"


def infer_template_id(prompt: str) -> str:
    body = prompt.lower()
    body = body.replace("[user]", "").replace("[ninereeds]", "").strip()
    if body.startswith("what is") or body.startswith("what are"):
        return "what_is"
    if body.startswith("what does") and "look like" in body:
        return "look_like"
    if body.startswith("describe"):
        return "describe"
    if body.startswith("where"):
        return "where"
    if body.startswith("can "):
        return "can"
    if body.startswith("is ") or body.startswith("are "):
        return "boolean"
    if " plus " in body or "+" in body:
        return "arithmetic"
    return "other"


def _clean_question_body(prompt: str) -> str:
    body = prompt.lower()
    body = body.replace("[user]", "").replace("[ninereeds]", "")
    body = re.sub(r"\s+", " ", body).strip()
    body = body.strip(" ?.!:;\"'")
    return body


def _clean_concept_phrase(text: str) -> str:
    text = re.sub(r"'s\b", "", text)
    text = re.sub(r"\bweight of\b", " ", text)
    text = re.sub(r"\b(right now|specific|exact|the color|color)\b", " ", text)
    text = re.sub(r"\b(a|an|the|this|that|your|my)\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" ?.!:;\"'")
    return text.replace(" ", "_") if text else ""


def infer_concept_id(prompt: str, label: str) -> str:
    """Best-effort concept extraction for legacy probe files without concept_id."""
    body = _clean_question_body(prompt)
    patterns = [
        r"^what kind of animal is (?P<x>.+)$",
        r"^what kind of thing are (?P<x>.+)$",
        r"^what can (?P<x>you) do$",
        r"^what will happen (?P<x>.+)$",
        r"^what is (?P<x>.+?) used for$",
        r"^what is (?P<x>.+?) for$",
        r"^what is (?P<x>.+?) thinking right now$",
        r"^what is (?P<x>.+?) feeling right now$",
        r"^what is (?P<x>.+?) name$",
        r"^what is (?P<x>.+?) weight$",
        r"^(does|can) (?P<x>.+?) [a-z_]+$",
        r"^is (?P<x>.+?) (a|an|the|same|more|less|greater|smaller).*$",
        r"^what is (?P<x>.+)$",
        r"^what are (?P<x>.+?) for$",
        r"^what do (?P<x>.+?) do$",
        r"^what does (?P<x>.+?) (look|feel|taste) like$",
        r"^what does (?P<x>.+?) involve$",
        r"^where do (?P<x>.+?) live$",
        r"^describe (?P<x>.+)$",
        r"^how many (?P<x>.+?) exist",
        r"^can (?P<x>you) ",
        r"^do (?P<x>you) ",
        r"^who are (?P<x>you)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, body)
        if match:
            concept = _clean_concept_phrase(match.group("x"))
            if concept:
                return concept
    return label


def normalize_probe_meta(probe: dict, i: int) -> dict:
    prompt = probe.get("prompt") or probe.get("text") or ""
    label = probe.get("label") or probe.get("id") or f"probe_{i}"
    concept_id = (
        probe.get("concept_id")
        or probe.get("concept")
        or probe.get("word")
        or infer_concept_id(prompt, label)
    )
    return {
        **probe,
        "id": probe.get("id", label),
        "label": label,
        "concept_id": str(concept_id),
        "template_id": probe.get("template_id") or infer_template_id(prompt),
        "language": probe.get("language") or probe.get("lang") or "unknown",
        "construction_id": probe.get("construction_id"),
        "source_corpus": probe.get("source_corpus"),
        "prompt": prompt,
    }


def cosine_matrix(vectors: "np.ndarray") -> "np.ndarray":
    import numpy as np

    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    normed = vectors / norms
    return normed @ normed.T


def jaccard_matrix(masks: "np.ndarray") -> "np.ndarray":
    import numpy as np

    masks = masks.astype(bool, copy=False)
    inter = masks.astype(np.uint32) @ masks.astype(np.uint32).T
    counts = masks.sum(axis=1, keepdims=True)
    union = counts + counts.T - inter
    return np.divide(inter, union, out=np.zeros_like(inter, dtype=np.float32), where=union != 0)


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

    name = getattr(args, "name", None)
    out_act, out_probes_file, _, _ = _out_paths(name)

    probe_file = getattr(args, "probes", None)
    if probe_file:
        probe_path = Path(probe_file)
        if not probe_path.exists():
            sys.exit(f"Probe file not found: {probe_path}")
        probes = load_external_probes(probe_path)
        print(f"Probe set: {len(probes)} probes from {probe_path.name}")
    else:
        rng    = random.Random(SEED)
        probes = build_all_probes(rng)
        print(f"Probe set: {len(probes)} probes (built-in fallback)")

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

    out_act.parent.mkdir(parents=True, exist_ok=True)
    # Save geometry alongside activations so hubs command doesn't need to hardcode it
    np.savez_compressed(str(out_act), activations=vectors,
                        n_layer=np.int32(C.n_layer),
                        n_head=np.int32(C.n_head),
                        neuron_dim=np.int32(N))
    out_probes_file.write_text(
        "\n".join(json.dumps(m, ensure_ascii=False) for m in meta) + "\n",
        encoding="utf-8",
    )
    avg_sparsity = np.mean([m["sparsity"] for m in meta])
    print(f"\nSaved: {out_act}")
    print(f"Saved: {out_probes_file}")
    print(f"Average sparsity: {avg_sparsity:.3f}  "
          f"(~{avg_sparsity * dim:.0f} active neurons per probe out of {dim:,})")


def cmd_map(args):
    import numpy as np

    name = getattr(args, "name", None)
    out_act, out_probes_file, out_heatmap, out_scatter = _out_paths(name)

    if not out_act.exists():
        sys.exit(f"No activations found at {out_act}. Run: probe first.")

    data    = np.load(str(out_act))
    vectors = data["activations"]          # (n_probes, dim)
    probes  = [json.loads(l)
               for l in out_probes_file.read_text(encoding="utf-8").splitlines()
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

    # Sort probes by category — preserve first-seen order from probe file
    category_order = list(dict.fromkeys(cats))
    cat_priority   = {c: i for i, c in enumerate(category_order)}
    order   = sorted(range(n), key=lambda i: (cat_priority.get(cats[i], 99), labels[i]))
    sim_ord = sim[np.ix_(order, order)]
    labs_ord = [labels[i] for i in order]
    cats_ord = [cats[i]   for i in order]

    ckpt_label = getattr(args, "name", None) or "checkpoint"
    _heatmap(sim_ord, labs_ord, cats_ord, out_heatmap,
             title=f"BDH {ckpt_label} — Concept Activation Similarity (xy_sparse, last token)")

    # ── 2-D scatter (t-SNE or PCA fallback) ──────────────────────────────
    _scatter(vectors, labels, cats, out_scatter, title_prefix=f"BDH {ckpt_label}")


def _heatmap(sim: "np.ndarray", labels: list[str], cats: list[str], out_path: "Path",
             title: str = "BDH — Concept Activation Similarity (xy_sparse, last token)"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np

    n = len(labels)
    PALETTE = make_palette(cats)

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
        title + "\n"
        + "  ".join(f"{cat.replace('_',' ')}: μ={ms:.2f}"
                    for cat, _, _, ms in block_means),
        fontsize=9,
    )

    plt.tight_layout()
    plt.savefig(str(out_path), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Heatmap saved: {out_path}")

    # Print block diagonal means to console
    print("\nIntra-category mean cosine similarity (diagonal blocks):")
    for cat, s, e, ms in sorted(block_means, key=lambda x: -x[3]):
        print(f"  {cat:<25}  n={e-s:3d}  mean_sim={ms:.3f}")


def _scatter(vectors: "np.ndarray", labels: list[str], cats: list[str], out_path: "Path",
             title_prefix: str = "BDH"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    PALETTE = make_palette(cats)

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
    ax.set_title(f"{title_prefix} — {method} of xy_sparse activations\n"
                 "Each point = one probe; colour = category", fontsize=10)
    ax.set_xlabel(f"{method} dim 1")
    ax.set_ylabel(f"{method} dim 2")

    plt.tight_layout()
    plt.savefig(str(out_path), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Scatter ({method}) saved: {out_path}")


def cmd_run(args):
    cmd_probe(args)
    cmd_map(args)


def cmd_trace(args):
    import numpy as np
    import torch

    checkpoint = Path(args.checkpoint)
    if not checkpoint.exists():
        sys.exit(f"Checkpoint not found: {checkpoint}")

    probe_file = getattr(args, "probes", None)
    if probe_file:
        probe_path = Path(probe_file)
        if not probe_path.exists():
            sys.exit(f"Probe file not found: {probe_path}")
        raw_probes = load_external_probes(probe_path)
        print(f"Probe set: {len(raw_probes)} probes from {probe_path.name}")
    else:
        rng = random.Random(SEED)
        raw_probes = build_all_probes(rng)
        print(f"Probe set: {len(raw_probes)} probes (built-in fallback)")

    probes = [normalize_probe_meta(p, i) for i, p in enumerate(raw_probes)]
    name = getattr(args, "name", None)
    out_npz, out_json, out_report = _trace_paths(name)

    print(f"Loading checkpoint: {checkpoint}")
    model = load_model(checkpoint)
    print(f"Config: {model.config}")

    C = model.config
    N = C.n_embd * C.mlp_internal_dim_multiplier // C.n_head
    dim = C.n_layer * C.n_head * N
    print(f"Trace dim: {C.n_layer} layers × {C.n_head} heads × {N} = {dim:,}")
    print(f"Trace mode: {args.positions}; output generation: {'on' if args.generate else 'off'}")

    n = len(probes)
    probe_vectors = np.zeros((n, dim), dtype=np.float32)
    mean_vectors = np.zeros((n, dim), dtype=np.float32)
    active_masks = np.zeros((n, dim), dtype=bool)
    fire_rates = np.zeros((n, dim), dtype=np.float32)
    top_indices = np.zeros((n, args.top_k), dtype=np.int32)
    top_strengths = np.zeros((n, args.top_k), dtype=np.float32)
    meta = []

    for i, probe in enumerate(probes):
        prompt = probe["prompt"]
        output = ""
        status = "not_generated"
        trace_text = prompt
        if args.generate:
            output = generate_for_trace(model, prompt, args.max_new_tokens,
                                        args.temperature, args.top_k_sample)
            status = output_status(output)
            trace_text = prompt + output

        tokens = encode_prompt(trace_text)
        idx = torch.tensor([tokens], dtype=torch.long)
        with torch.no_grad():
            captured = forward_with_activation_trace(model, idx, mode=args.positions)
        summary = activation_trace_summary(captured, args.top_k)

        k = len(summary["top_indices"])
        probe_vectors[i] = summary["vector"]
        mean_vectors[i] = summary["mean_vector"]
        active_masks[i] = summary["active_mask"]
        fire_rates[i] = summary["fire_rate_by_dim"]
        top_indices[i, :k] = summary["top_indices"]
        top_strengths[i, :k] = summary["top_strengths"]

        meta.append({
            **probe,
            "trace_tokens": len(tokens),
            "overall_fire_rate": summary["overall_fire_rate"],
            "mean_positive_activation": summary["mean_positive_activation"],
            "output": output,
            "output_status": status,
            "top_neurons": [
                {"index": int(idx), "strength": float(strength)}
                for idx, strength in zip(summary["top_indices"], summary["top_strengths"])
            ],
        })

        if (i + 1) % 10 == 0 or i == n - 1:
            print(f"  [{i+1:3d}/{n}] {probe['id']} concept={probe['concept_id']} "
                  f"fire={summary['overall_fire_rate']:.4f} status={status}")

    concept_ids = list(dict.fromkeys(m["concept_id"] for m in meta))
    concept_index = {c: i for i, c in enumerate(concept_ids)}
    c = len(concept_ids)
    concept_vectors = np.zeros((c, dim), dtype=np.float32)
    concept_fire_rates = np.zeros((c, dim), dtype=np.float32)
    concept_masks = np.zeros((c, dim), dtype=bool)
    concept_counts = np.zeros(c, dtype=np.int32)

    for i, m in enumerate(meta):
        ci = concept_index[m["concept_id"]]
        concept_vectors[ci] += mean_vectors[i]
        concept_fire_rates[ci] += fire_rates[i]
        concept_masks[ci] |= active_masks[i]
        concept_counts[ci] += 1

    concept_vectors /= np.maximum(concept_counts[:, None], 1)
    concept_fire_rates /= np.maximum(concept_counts[:, None], 1)

    concept_cosine = cosine_matrix(concept_vectors).astype(np.float32)
    concept_jaccard = jaccard_matrix(concept_masks).astype(np.float32)
    probe_cosine = cosine_matrix(mean_vectors).astype(np.float32)

    out_npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        str(out_npz),
        probe_vectors=probe_vectors,
        mean_vectors=mean_vectors,
        active_masks=active_masks,
        fire_rates=fire_rates,
        top_indices=top_indices,
        top_strengths=top_strengths,
        concept_vectors=concept_vectors,
        concept_fire_rates=concept_fire_rates,
        concept_masks=concept_masks,
        concept_counts=concept_counts,
        concept_cosine=concept_cosine,
        concept_jaccard=concept_jaccard,
        probe_cosine=probe_cosine,
        concept_ids=np.array(concept_ids, dtype=str),
        n_layer=np.int32(C.n_layer),
        n_head=np.int32(C.n_head),
        neuron_dim=np.int32(N),
    )

    summary_json = build_trace_summary_json(
        meta=meta,
        concept_ids=concept_ids,
        concept_counts=concept_counts,
        concept_fire_rates=concept_fire_rates,
        concept_masks=concept_masks,
        concept_cosine=concept_cosine,
        concept_jaccard=concept_jaccard,
        threshold=args.edge_threshold,
        name=name or "brain_trace",
        checkpoint=str(checkpoint),
        positions=args.positions,
    )
    out_json.write_text(json.dumps(summary_json, indent=2, ensure_ascii=False), encoding="utf-8")
    out_report.write_text(render_trace_report(summary_json), encoding="utf-8")

    print(f"\nSaved trace arrays: {out_npz}")
    print(f"Saved trace summary: {out_json}")
    print(f"Saved trace report: {out_report}")


def build_trace_summary_json(*, meta, concept_ids, concept_counts, concept_fire_rates,
                             concept_masks, concept_cosine, concept_jaccard,
                             threshold: float, name: str, checkpoint: str,
                             positions: str) -> dict:
    import numpy as np

    concept_categories = {}
    concept_templates = {}
    concept_languages = {}
    concept_statuses = {}
    concept_sources = {}
    for m in meta:
        cid = m["concept_id"]
        concept_categories.setdefault(cid, set()).add(m.get("category", "unknown"))
        concept_templates.setdefault(cid, set()).add(m.get("template_id", "unknown"))
        concept_languages.setdefault(cid, set()).add(m.get("language", "unknown"))
        concept_statuses.setdefault(cid, []).append(m.get("output_status", "not_generated"))
        source = m.get("source_corpus")
        if source:
            if isinstance(source, list):
                concept_sources.setdefault(cid, set()).update(str(s) for s in source)
            else:
                concept_sources.setdefault(cid, set()).add(str(source))

    concepts = []
    for i, cid in enumerate(concept_ids):
        avg_fire = float(concept_fire_rates[i].mean())
        active_dims = int(concept_masks[i].sum())
        top_dim_idx = np.argpartition(concept_fire_rates[i], -10)[-10:]
        top_dim_idx = top_dim_idx[np.argsort(concept_fire_rates[i][top_dim_idx])[::-1]]
        concepts.append({
            "concept_id": cid,
            "categories": sorted(concept_categories.get(cid, [])),
            "templates": sorted(concept_templates.get(cid, [])),
            "languages": sorted(concept_languages.get(cid, [])),
            "source_corpus": sorted(concept_sources.get(cid, []))[:12],
            "probe_count": int(concept_counts[i]),
            "avg_fire_rate": avg_fire,
            "active_dims": active_dims,
            "output_status_counts": {
                s: concept_statuses.get(cid, []).count(s)
                for s in sorted(set(concept_statuses.get(cid, [])))
            },
            "top_fire_dims": [
                {"index": int(j), "fire_rate": float(concept_fire_rates[i, j])}
                for j in top_dim_idx
            ],
        })

    connections = []
    n = len(concept_ids)
    for i in range(n):
        for j in range(i + 1, n):
            cos = float(concept_cosine[i, j])
            jac = float(concept_jaccard[i, j])
            if cos >= threshold or jac >= threshold:
                connections.append({
                    "source": concept_ids[i],
                    "target": concept_ids[j],
                    "cosine": cos,
                    "jaccard": jac,
                    "same_category": bool(
                        set(concept_categories.get(concept_ids[i], []))
                        & set(concept_categories.get(concept_ids[j], []))
                    ),
                })
    connections.sort(key=lambda x: (x["cosine"], x["jaccard"]), reverse=True)

    category_stats = []
    categories = sorted({m.get("category", "unknown") for m in meta})
    probe_by_category = {cat: [m for m in meta if m.get("category", "unknown") == cat]
                         for cat in categories}
    concept_pos = {cid: i for i, cid in enumerate(concept_ids)}
    for cat, rows in probe_by_category.items():
        cids = list(dict.fromkeys(m["concept_id"] for m in rows))
        idx = [concept_pos[cid] for cid in cids]
        intra_cosine = None
        intra_jaccard = None
        if len(idx) > 1:
            sub_cos = concept_cosine[np.ix_(idx, idx)]
            sub_jac = concept_jaccard[np.ix_(idx, idx)]
            mask = np.triu(np.ones_like(sub_cos, dtype=bool), k=1)
            intra_cosine = float(sub_cos[mask].mean())
            intra_jaccard = float(sub_jac[mask].mean())
        category_stats.append({
            "category": cat,
            "probe_count": len(rows),
            "concept_count": len(cids),
            "mean_probe_fire_rate": float(np.mean([m["overall_fire_rate"] for m in rows])),
            "intra_concept_cosine": intra_cosine,
            "intra_concept_jaccard": intra_jaccard,
        })

    avg_rates = np.array([c["avg_fire_rate"] for c in concepts], dtype=np.float32)
    weak_cutoff = float(np.quantile(avg_rates, 0.20)) if len(avg_rates) else 0.0
    strong_cutoff = float(np.quantile(avg_rates, 0.80)) if len(avg_rates) else 0.0
    degree = {cid: 0 for cid in concept_ids}
    cross_category_connections = []
    for edge in connections:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1
        if not edge["same_category"]:
            cross_category_connections.append(edge)

    flags = {
        "weak_concepts": sorted(
            [c for c in concepts if c["avg_fire_rate"] <= weak_cutoff],
            key=lambda c: c["avg_fire_rate"],
        )[:20],
        "strong_concepts": sorted(
            [c for c in concepts if c["avg_fire_rate"] >= strong_cutoff],
            key=lambda c: c["avg_fire_rate"],
            reverse=True,
        )[:20],
        "overconnected_concepts": sorted(
            [{"concept_id": cid, "degree": deg} for cid, deg in degree.items() if deg],
            key=lambda x: x["degree"],
            reverse=True,
        )[:20],
        "cross_category_connections": cross_category_connections[:30],
        "fuzzy_categories": sorted(
            [s for s in category_stats
             if s["intra_concept_cosine"] is not None and s["intra_concept_cosine"] < 0.65],
            key=lambda s: s["intra_concept_cosine"],
        ),
    }

    return {
        "name": name,
        "checkpoint": checkpoint,
        "positions": positions,
        "edge_threshold": threshold,
        "n_probes": len(meta),
        "n_concepts": len(concept_ids),
        "probes": meta,
        "concepts": concepts,
        "connections": connections,
        "category_stats": category_stats,
        "flags": flags,
    }


def render_trace_report(summary: dict) -> str:
    lines = []
    lines.append(f"# Brain Trace Report — {summary['name']}")
    lines.append("")
    lines.append(f"- checkpoint: `{summary['checkpoint']}`")
    lines.append(f"- probes: {summary['n_probes']}")
    lines.append(f"- concepts: {summary['n_concepts']}")
    lines.append(f"- positions: `{summary['positions']}`")
    lines.append(f"- edge threshold: {summary['edge_threshold']:.2f}")
    lines.append("")

    lines.append("## Next-Move Signals")
    weak = summary["flags"]["weak_concepts"][:10]
    if weak:
        lines.append("")
        lines.append("### Weak concepts: add cleaner/more varied corpus")
        for c in weak:
            cats = ",".join(c["categories"])
            lines.append(f"- `{c['concept_id']}` ({cats}) fire={c['avg_fire_rate']:.5f} active_dims={c['active_dims']}")
            sources = c.get("source_corpus") or []
            if sources:
                lines.append(f"  source: `{sources[0]}`")
    else:
        lines.append("")
        lines.append("No weak concepts flagged.")

    fuzzy = summary["flags"]["fuzzy_categories"][:10]
    if fuzzy:
        lines.append("")
        lines.append("### Fuzzy categories: split or strengthen anchors")
        for s in fuzzy:
            lines.append(f"- `{s['category']}` concept_cos={s['intra_concept_cosine']:.3f} "
                         f"concept_jaccard={s['intra_concept_jaccard']:.3f}")

    cross = summary["flags"]["cross_category_connections"][:10]
    if cross:
        lines.append("")
        lines.append("### Cross-category connections: audit co-occurrence/noise")
        for e in cross:
            lines.append(f"- `{e['source']}` ↔ `{e['target']}` cosine={e['cosine']:.3f} jaccard={e['jaccard']:.3f}")

    over = summary["flags"]["overconnected_concepts"][:10]
    if over:
        lines.append("")
        lines.append("### Overconnected concepts: possible hubs/default patterns")
        for row in over:
            lines.append(f"- `{row['concept_id']}` degree={row['degree']}")

    lines.append("")
    lines.append("## Category Stats")
    lines.append("")
    lines.append("| category | probes | concepts | fire_rate | concept_cos | concept_jaccard |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for s in sorted(summary["category_stats"], key=lambda x: x["category"]):
        cos = "" if s["intra_concept_cosine"] is None else f"{s['intra_concept_cosine']:.3f}"
        jac = "" if s["intra_concept_jaccard"] is None else f"{s['intra_concept_jaccard']:.3f}"
        lines.append(f"| {s['category']} | {s['probe_count']} | {s['concept_count']} | "
                     f"{s['mean_probe_fire_rate']:.5f} | {cos} | {jac} |")

    lines.append("")
    lines.append("## Output Status")
    lines.append("")
    status_counts = {}
    for p in summary["probes"]:
        status = p.get("output_status", "not_generated")
        status_counts[status] = status_counts.get(status, 0) + 1
    for status, count in sorted(status_counts.items()):
        lines.append(f"- `{status}`: {count}")

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("- Weak concepts are candidates for more direct anchor examples and template diversity.")
    lines.append("- Fuzzy categories need either more examples or finer categories; do not assume one cluster exists.")
    lines.append("- Cross-category edges are not automatically bad, but they are the first corpus co-occurrence audits to run.")
    lines.append("- Overconnected concepts may be useful hubs or accidental defaults; verify with negative controls and output scoring.")
    return "\n".join(lines) + "\n"


def cmd_trace_report(args):
    name = getattr(args, "name", None)
    _, out_json, out_report = _trace_paths(name)
    if not out_json.exists():
        sys.exit(f"No trace summary found at {out_json}. Run: trace first.")
    summary = json.loads(out_json.read_text(encoding="utf-8"))
    out_report.write_text(render_trace_report(summary), encoding="utf-8")
    print(f"Trace report saved: {out_report}")


def cmd_validate_probes(args):
    paths = [Path(p) for p in args.probes]
    failed = False
    for path in paths:
        if path.is_dir():
            files = sorted(path.glob("*.jsonl"))
        else:
            files = [path]
        for file_path in files:
            if not file_path.exists():
                print(f"FAIL {file_path}: not found")
                failed = True
                continue
            count, errors = validate_probe_file(file_path, strict=not args.no_strict)
            if errors:
                failed = True
                print(f"FAIL {file_path}: {count} probes, {len(errors)} errors")
                for err in errors[: args.max_errors]:
                    print(f"  {err}")
                if len(errors) > args.max_errors:
                    print(f"  ... {len(errors) - args.max_errors} more")
            else:
                print(f"OK   {file_path}: {count} probes")
    if failed:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Concept atlas: cluster drill-down + edge evidence
# ---------------------------------------------------------------------------

_ATLAS_HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Ninereeds Concept Atlas — __TITLE__</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#07100d;color:#d8eadc;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;overflow:hidden}
#app{display:grid;grid-template-columns:280px 1fr 360px;height:100vh}
#left,#right{background:#0b1712;border-color:#1f3b2d;padding:14px;overflow:auto}
#left{border-right:1px solid #1f3b2d}
#right{border-left:1px solid #1f3b2d}
#main{position:relative;background:
  radial-gradient(circle at 25% 20%,rgba(62,137,95,.22),transparent 28%),
  radial-gradient(circle at 75% 80%,rgba(147,111,55,.18),transparent 32%),
  #06100c}
h1{font-size:13px;letter-spacing:2px;margin:0 0 12px;color:#9de0b1}
h2{font-size:11px;color:#79aa82;border-bottom:1px solid #1f3b2d;padding-bottom:5px;margin:16px 0 8px}
.meta{font-size:10px;color:#89a08d;line-height:1.45}
.cluster{display:flex;align-items:center;gap:8px;padding:6px 7px;margin:3px 0;border-radius:5px;cursor:pointer;color:#cce4d1}
.cluster:hover,.cluster.active{background:#153524}
.dot{width:9px;height:9px;border-radius:50%;flex:0 0 auto}
.count{margin-left:auto;color:#87a08c;font-size:10px}
#search{width:100%;background:#09130f;border:1px solid #244633;color:#d8eadc;padding:8px;border-radius:5px}
#toolbar{position:absolute;left:14px;right:14px;top:12px;display:flex;gap:8px;align-items:center;z-index:2}
button{background:#143321;color:#d8eadc;border:1px solid #2f6144;border-radius:5px;padding:7px 9px;cursor:pointer;font-family:inherit;font-size:11px}
button:hover{background:#1d4a30}
#title{font-size:12px;color:#9de0b1;margin-left:6px}
svg{width:100%;height:100%}
.node{cursor:pointer;stroke:#06100c;stroke-width:1.5}
.node.external{opacity:.52}
.label{font-size:10px;fill:#d8eadc;pointer-events:none;text-shadow:0 1px 2px #000}
.edge{stroke:#5c8f6a;stroke-opacity:.45;cursor:pointer}
.edge.external{stroke:#8b7650;stroke-opacity:.32}
.edge.selected{stroke:#fff;stroke-opacity:.95}
.panelbox{background:#08130e;border:1px solid #1f3b2d;border-radius:6px;padding:10px;margin:8px 0}
.kv{display:grid;grid-template-columns:110px 1fr;gap:4px;font-size:10px;margin:3px 0}
.k{color:#89a08d}.v{color:#d8eadc;word-break:break-word}
.listitem{font-size:10px;padding:5px;border-bottom:1px solid #183123;cursor:pointer}
.listitem:hover{background:#122b1d}
.src{font-size:9px;color:#a0b29f;word-break:break-all;margin:3px 0}
.warn{color:#f3c66b}
</style>
</head>
<body>
<div id="app">
  <aside id="left">
    <h1>NINEREEDS · ATLAS</h1>
    <div class="meta" id="summary"></div>
    <h2>Search</h2>
    <input id="search" placeholder="concept..." />
    <h2>Clusters</h2>
    <div id="clusters"></div>
  </aside>
  <main id="main">
    <div id="toolbar">
      <button id="showAll">All Clusters</button>
      <button id="toggleExternal">Toggle External Links</button>
      <span id="title"></span>
    </div>
    <svg id="svg"></svg>
  </main>
  <aside id="right">
    <h1>INSPECTOR</h1>
    <div id="inspect" class="meta">Click a cluster, concept, or edge.</div>
    <h2>Connected Concepts</h2>
    <div id="connections"></div>
  </aside>
</div>
<script>
const DATA = __DATA_JSON__;
const PALETTE = __PALETTE_JSON__;
let selectedCategory = DATA.categories[0]?.id || null;
let showExternal = true;
let selectedEdge = null;
let selectedConcept = null;

const svg = document.getElementById('svg');
const clustersEl = document.getElementById('clusters');
const inspectEl = document.getElementById('inspect');
const connectionsEl = document.getElementById('connections');
const titleEl = document.getElementById('title');
document.getElementById('summary').innerHTML =
  DATA.name + '<br>' + DATA.nConcepts + ' concepts · ' + DATA.nEdges + ' edges<br>threshold ' + DATA.threshold;

function color(cat){ return PALETTE[cat] || '#7da883'; }
function fmt(x){ return Number(x).toFixed(3); }
function esc(s){ return String(s ?? '').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

function renderClusters(){
  clustersEl.innerHTML = '';
  DATA.categories.forEach(cat => {
    const row = document.createElement('div');
    row.className = 'cluster' + (cat.id === selectedCategory ? ' active' : '');
    row.innerHTML = `<span class="dot" style="background:${color(cat.id)}"></span><span>${esc(cat.id)}</span><span class="count">${cat.count}</span>`;
    row.onclick = () => { selectedCategory = cat.id; selectedConcept = null; selectedEdge = null; render(); };
    clustersEl.appendChild(row);
  });
}

function categoryConcepts(cat){
  return DATA.concepts.filter(c => c.categories.includes(cat));
}
function edgeKey(e){ return e.source + '→' + e.target; }

function graphForCategory(cat){
  const primary = new Set(categoryConcepts(cat).map(c => c.id));
  const edges = DATA.edges.filter(e => primary.has(e.source) || primary.has(e.target));
  const visibleEdges = showExternal ? edges : edges.filter(e => primary.has(e.source) && primary.has(e.target));
  const nodeIds = new Set();
  visibleEdges.forEach(e => { nodeIds.add(e.source); nodeIds.add(e.target); });
  primary.forEach(id => nodeIds.add(id));
  const nodes = DATA.concepts.filter(c => nodeIds.has(c.id)).map(c => ({...c, primary: primary.has(c.id)}));
  return {nodes, edges: visibleEdges, primary};
}

function layout(nodes, edges){
  const w = svg.clientWidth || 900, h = svg.clientHeight || 700;
  const cx = w/2, cy = h/2;
  const primary = nodes.filter(n => n.primary);
  const external = nodes.filter(n => !n.primary);
  primary.forEach((n,i) => {
    const a = (Math.PI*2*i)/Math.max(1, primary.length);
    const r = Math.min(w,h)*0.22;
    n.x = cx + Math.cos(a)*r;
    n.y = cy + Math.sin(a)*r;
  });
  external.forEach((n,i) => {
    const a = (Math.PI*2*i)/Math.max(1, external.length);
    const r = Math.min(w,h)*0.39;
    n.x = cx + Math.cos(a)*r;
    n.y = cy + Math.sin(a)*r;
  });
}

function render(){
  renderClusters();
  if (!selectedCategory) return;
  titleEl.textContent = 'cluster: ' + selectedCategory + (showExternal ? ' · external links on' : ' · internal only');
  const g = graphForCategory(selectedCategory);
  layout(g.nodes, g.edges);
  const byId = Object.fromEntries(g.nodes.map(n => [n.id,n]));
  svg.innerHTML = '';

  g.edges.forEach(e => {
    const a = byId[e.source], b = byId[e.target];
    if (!a || !b) return;
    const line = document.createElementNS('http://www.w3.org/2000/svg','line');
    line.setAttribute('x1',a.x); line.setAttribute('y1',a.y); line.setAttribute('x2',b.x); line.setAttribute('y2',b.y);
    line.setAttribute('class','edge ' + ((a.primary && b.primary) ? '' : 'external') + (selectedEdge && edgeKey(selectedEdge)===edgeKey(e) ? ' selected':''));
    line.setAttribute('stroke-width', Math.max(1, (e.cosine - DATA.threshold + 0.02) * 16));
    line.onclick = evt => { evt.stopPropagation(); selectedEdge = e; selectedConcept = null; inspectEdge(e); renderConnections(e.source); render(); };
    svg.appendChild(line);
  });

  g.nodes.forEach(n => {
    const circle = document.createElementNS('http://www.w3.org/2000/svg','circle');
    circle.setAttribute('cx',n.x); circle.setAttribute('cy',n.y);
    circle.setAttribute('r', Math.max(7, Math.min(18, 7 + n.probe_count*1.4)));
    circle.setAttribute('fill', color(n.categories[0]));
    circle.setAttribute('class','node ' + (n.primary ? '' : 'external'));
    circle.onclick = evt => { evt.stopPropagation(); selectedConcept = n.id; selectedEdge = null; inspectConcept(n); renderConnections(n.id); render(); };
    svg.appendChild(circle);
    const text = document.createElementNS('http://www.w3.org/2000/svg','text');
    text.setAttribute('x', n.x + 10); text.setAttribute('y', n.y + 4);
    text.setAttribute('class','label');
    text.textContent = n.id;
    svg.appendChild(text);
  });

  if (selectedEdge) inspectEdge(selectedEdge);
  else if (selectedConcept) inspectConcept(DATA.conceptsById[selectedConcept]);
  else inspectCluster(selectedCategory, g);
}

function inspectCluster(cat, g){
  const concepts = categoryConcepts(cat);
  const internal = g.edges.filter(e => g.primary.has(e.source) && g.primary.has(e.target));
  const external = g.edges.length - internal.length;
  inspectEl.innerHTML = `<div class="panelbox">
    <div class="kv"><div class="k">cluster</div><div class="v">${esc(cat)}</div></div>
    <div class="kv"><div class="k">concepts</div><div class="v">${concepts.length}</div></div>
    <div class="kv"><div class="k">internal edges</div><div class="v">${internal.length}</div></div>
    <div class="kv"><div class="k">external edges</div><div class="v">${external}</div></div>
  </div>`;
  renderConnections(concepts[0]?.id);
}

function inspectConcept(c){
  if (!c) return;
  inspectEl.innerHTML = `<div class="panelbox">
    <div class="kv"><div class="k">concept</div><div class="v">${esc(c.id)}</div></div>
    <div class="kv"><div class="k">categories</div><div class="v">${esc(c.categories.join(', '))}</div></div>
    <div class="kv"><div class="k">templates</div><div class="v">${esc(c.templates.join(', '))}</div></div>
    <div class="kv"><div class="k">fire</div><div class="v">${c.avg_fire_rate.toFixed(5)}</div></div>
    <div class="kv"><div class="k">active dims</div><div class="v">${c.active_dims}</div></div>
  </div>
  <h2>Top Neurons</h2>
  <div class="panelbox">${c.top_neurons.map(n => `<div class="kv"><div class="k">${esc(n.label)}</div><div class="v">${n.fire_rate.toFixed(3)}</div></div>`).join('')}</div>
  <h2>Sources</h2>
  <div class="panelbox">${(c.source_corpus||[]).map(s=>`<div class="src">${esc(s)}</div>`).join('') || '<span class="warn">no source metadata</span>'}</div>`;
}

function inspectEdge(e){
  const a = DATA.conceptsById[e.source], b = DATA.conceptsById[e.target];
  inspectEl.innerHTML = `<div class="panelbox">
    <div class="kv"><div class="k">edge</div><div class="v">${esc(e.source)} ↔ ${esc(e.target)}</div></div>
    <div class="kv"><div class="k">cosine</div><div class="v">${fmt(e.cosine)}</div></div>
    <div class="kv"><div class="k">jaccard</div><div class="v">${fmt(e.jaccard)}</div></div>
    <div class="kv"><div class="k">same category</div><div class="v">${e.same_category ? 'yes' : '<span class="warn">no</span>'}</div></div>
  </div>
  <h2>Shared Neuron Evidence</h2>
  <div class="panelbox">${e.shared_neurons.map(n => `<div class="kv"><div class="k">${esc(n.label)}</div><div class="v">shared ${n.shared.toFixed(3)} · ${esc(e.source)} ${n.source_fire.toFixed(3)} · ${esc(e.target)} ${n.target_fire.toFixed(3)}</div></div>`).join('') || '<span class="warn">not in top-neuron intersection</span>'}</div>
  <h2>Sources</h2>
  <div class="panelbox"><b>${esc(e.source)}</b>${(a.source_corpus||[]).slice(0,5).map(s=>`<div class="src">${esc(s)}</div>`).join('')}<br><b>${esc(e.target)}</b>${(b.source_corpus||[]).slice(0,5).map(s=>`<div class="src">${esc(s)}</div>`).join('')}</div>`;
}

function renderConnections(conceptId){
  if (!conceptId){ connectionsEl.innerHTML = ''; return; }
  const rows = DATA.edges.filter(e => e.source===conceptId || e.target===conceptId)
    .sort((a,b) => (b.cosine+b.jaccard)-(a.cosine+a.jaccard))
    .slice(0,80);
  connectionsEl.innerHTML = rows.map(e => {
    const other = e.source===conceptId ? e.target : e.source;
    const cross = e.same_category ? '' : ' <span class="warn">cross</span>';
    return `<div class="listitem" data-edge="${esc(edgeKey(e))}">${esc(other)} · cos ${fmt(e.cosine)} · jac ${fmt(e.jaccard)}${cross}</div>`;
  }).join('');
  [...connectionsEl.querySelectorAll('.listitem')].forEach((el, i) => {
    el.onclick = () => { selectedEdge = rows[i]; selectedConcept = null; inspectEdge(rows[i]); render(); };
  });
}

document.getElementById('showAll').onclick = () => { selectedCategory = DATA.categories[0]?.id || null; render(); };
document.getElementById('toggleExternal').onclick = () => { showExternal = !showExternal; render(); };
document.getElementById('search').oninput = e => {
  const q = e.target.value.trim().toLowerCase();
  if (!q) { render(); return; }
  const c = DATA.concepts.find(c => c.id.toLowerCase().includes(q));
  if (c) { selectedCategory = c.categories[0]; selectedConcept = c.id; selectedEdge = null; render(); inspectConcept(c); renderConnections(c.id); }
};

DATA.conceptsById = Object.fromEntries(DATA.concepts.map(c => [c.id,c]));
render();
</script>
</body>
</html>'''


def _dim_label(idx: int, n_head: int, neuron_dim: int) -> str:
    layer = idx // (n_head * neuron_dim)
    head = (idx % (n_head * neuron_dim)) // neuron_dim
    neuron = idx % neuron_dim
    return f"L{layer}H{head}N{neuron}"


def cmd_atlas(args):
    import numpy as np

    name = getattr(args, "name", None)
    out_npz, out_json, _ = _trace_paths(name)
    if not out_npz.exists() or not out_json.exists():
        sys.exit(f"Trace artifacts not found for {name}. Run: trace first.")

    data = np.load(str(out_npz))
    summary = json.loads(out_json.read_text(encoding="utf-8"))
    concept_ids = [str(x) for x in data["concept_ids"]]
    concept_fire = data["concept_fire_rates"]
    concept_masks = data["concept_masks"]
    concept_cos = data["concept_cosine"]
    concept_jac = data["concept_jaccard"]
    n_head = int(data["n_head"])
    neuron_dim = int(data["neuron_dim"])

    source_by_concept: dict[str, set[str]] = {}
    for probe in summary.get("probes", []):
        cid = probe.get("concept_id")
        source = probe.get("source_corpus")
        if cid and source:
            if isinstance(source, list):
                source_by_concept.setdefault(cid, set()).update(str(s) for s in source)
            else:
                source_by_concept.setdefault(cid, set()).add(str(source))

    concept_meta = {c["concept_id"]: c for c in summary.get("concepts", [])}
    top_neuron_count = max(args.top_neurons_per_concept, args.shared_pool)
    top_by_concept: dict[str, list[tuple[int, float]]] = {}
    concepts = []
    for i, cid in enumerate(concept_ids):
        rates = concept_fire[i]
        k = min(top_neuron_count, rates.shape[0])
        top_idx = np.argpartition(rates, -k)[-k:]
        top_idx = top_idx[np.argsort(rates[top_idx])[::-1]]
        top_pairs = [(int(idx), float(rates[idx])) for idx in top_idx if rates[idx] > 0]
        top_by_concept[cid] = top_pairs
        meta = concept_meta.get(cid, {})
        source = sorted(source_by_concept.get(cid, set()) | set(meta.get("source_corpus", [])))
        concepts.append({
            "id": cid,
            "categories": meta.get("categories", ["unknown"]),
            "templates": meta.get("templates", []),
            "probe_count": int(meta.get("probe_count", 1)),
            "avg_fire_rate": float(meta.get("avg_fire_rate", float(rates.mean()))),
            "active_dims": int(meta.get("active_dims", int(concept_masks[i].sum()))),
            "source_corpus": source[:16],
            "top_neurons": [
                {
                    "index": idx,
                    "label": _dim_label(idx, n_head, neuron_dim),
                    "fire_rate": rate,
                }
                for idx, rate in top_pairs[: args.top_neurons_per_concept]
            ],
        })

    category_counts: dict[str, int] = {}
    for concept in concepts:
        for cat in concept["categories"]:
            category_counts[cat] = category_counts.get(cat, 0) + 1
    categories = [
        {"id": cat, "count": count}
        for cat, count in sorted(category_counts.items(), key=lambda x: (-x[1], x[0]))
    ]

    concept_pos = {cid: i for i, cid in enumerate(concept_ids)}
    edges = []
    for i, source in enumerate(concept_ids):
        for j in range(i + 1, len(concept_ids)):
            target = concept_ids[j]
            cos = float(concept_cos[i, j])
            jac = float(concept_jac[i, j])
            if cos < args.edge_threshold and jac < args.jaccard_threshold:
                continue
            source_cats = set(concept_meta.get(source, {}).get("categories", []))
            target_cats = set(concept_meta.get(target, {}).get("categories", []))
            source_top = dict(top_by_concept[source][: args.shared_pool])
            target_top = dict(top_by_concept[target][: args.shared_pool])
            shared = []
            for idx in set(source_top) & set(target_top):
                sf = source_top[idx]
                tf = target_top[idx]
                shared.append({
                    "index": idx,
                    "label": _dim_label(idx, n_head, neuron_dim),
                    "source_fire": sf,
                    "target_fire": tf,
                    "shared": min(sf, tf),
                })
            shared.sort(key=lambda x: x["shared"], reverse=True)
            edges.append({
                "source": source,
                "target": target,
                "cosine": cos,
                "jaccard": jac,
                "same_category": bool(source_cats & target_cats),
                "shared_neurons": shared[: args.top_shared_neurons],
            })

    edges.sort(key=lambda e: (e["cosine"] + e["jaccard"]), reverse=True)
    if args.max_edges and len(edges) > args.max_edges:
        edges = edges[: args.max_edges]

    atlas = {
        "name": name or "brain_trace",
        "threshold": args.edge_threshold,
        "nConcepts": len(concepts),
        "nEdges": len(edges),
        "categories": categories,
        "concepts": concepts,
        "edges": edges,
    }
    palette = make_palette([c["id"] for c in categories])
    html = _ATLAS_HTML_TEMPLATE
    html = html.replace("__TITLE__", name or "brain_trace")
    html = html.replace("__DATA_JSON__", json.dumps(atlas, separators=(",", ":"), ensure_ascii=False))
    html = html.replace("__PALETTE_JSON__", json.dumps(palette, separators=(",", ":")))

    stem = name if name else "brain_trace"
    out_html = BRAIN_MAPS_DIR / f"{stem}_atlas.html"
    out_html.write_text(html, encoding="utf-8")
    print(f"Atlas saved: {out_html} ({out_html.stat().st_size // 1024} KB)")
    print(f"Concepts: {len(concepts)}  Edges: {len(edges)}  Categories: {len(categories)}")


# ---------------------------------------------------------------------------
# 3-D interactive graph visualiser
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Ninereeds Brain Map — __TITLE__</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#00001a;overflow:hidden;font-family:'Courier New',monospace;color:#8ab4cc}
#gc{position:fixed;top:0;left:0;right:300px;bottom:0}
#sb{position:fixed;top:0;right:0;width:300px;height:100vh;background:rgba(4,6,22,.95);
    border-left:1px solid #0d1f3c;overflow-y:auto;padding:14px}
#hdr{color:#5af;font-size:10px;letter-spacing:3px;padding-bottom:8px;
     border-bottom:1px solid #0d1f3c;margin-bottom:12px}
h2{color:#3a6a9a;font-size:9px;letter-spacing:2px;margin:14px 0 6px;
   border-bottom:1px solid #0d1f3c;padding-bottom:4px}
#ni{background:rgba(0,15,40,.7);border:1px solid #0d2a50;padding:10px;
    margin-bottom:4px;min-height:70px;border-radius:2px}
#ni .lbl{color:#7ef;font-size:12px;font-weight:bold;margin-bottom:5px;word-break:break-all}
#ni .det{font-size:10px;color:#5a7a9a;margin:2px 0}
.cr{display:flex;align-items:center;margin:4px 0;cursor:pointer;padding:3px 5px;
    border-radius:2px;transition:background .15s}
.cr:hover{background:rgba(80,140,255,.08)}
.cd{width:9px;height:9px;border-radius:50%;margin-right:7px;flex-shrink:0}
.cl{font-size:10px;flex:1;transition:opacity .2s}
.cc{font-size:9px;color:#2a4a6a;margin-left:4px}
.cr.off .cl,.cr.off .cd{opacity:.2}
#sts{font-size:9px;color:#2a4a6a;margin-bottom:2px}
#ctr{font-size:9px;color:#2a4a6a;line-height:2}
</style>
</head>
<body>
<div id="gc"></div>
<div id="sb">
  <div id="hdr">NINEREEDS · BRAIN MAP</div>
  <h2>NODE INFO</h2>
  <div id="ni"><div class="det" style="color:#1a3a5a">hover a node to inspect</div></div>
  <h2>PROBE SET</h2>
  <div id="sts"></div>
  <h2>CATEGORIES</h2>
  <div id="cl"></div>
  <h2>CONTROLS</h2>
  <div id="ctr">drag &nbsp;— rotate<br>scroll — zoom<br>right-drag — pan<br>click &nbsp;— highlight neighbours</div>
</div>
<script>
__LIBRARY__
</script>
<script>
const ALL_NODES = __NODES_JSON__;
const LINKS_RAW = __LINKS_JSON__;
const PALETTE   = __PALETTE_JSON__;
const META      = __META_JSON__;

const visible = {};
Object.keys(PALETTE).forEach(k => visible[k] = true);

function filteredData() {
  const visIds = new Set(ALL_NODES.filter(n => visible[n.category]).map(n => n.id));
  return {
    nodes: ALL_NODES.filter(n => visIds.has(n.id)),
    links: LINKS_RAW.filter(l => visIds.has(l.source) && visIds.has(l.target)).map(l => ({...l}))
  };
}

const Graph = ForceGraph3D()(document.getElementById('gc'))
  .backgroundColor('#00001a')
  .graphData(filteredData())
  .nodeLabel(n => n.label)
  .nodeColor(n => PALETTE[n.category] || '#555')
  .nodeVal(n => Math.max(0.5, n.degree))
  .nodeOpacity(0.85)
  .linkWidth(l => Math.max(0.1, (l.value - META.threshold) * 4))
  .linkOpacity(0.2)
  .linkColor(() => '#2a5a8a')
  .onNodeHover(node => {
    document.body.style.cursor = node ? 'pointer' : 'default';
    const el = document.getElementById('ni');
    if (!node) {
      el.innerHTML = '<div class="det" style="color:#1a3a5a">hover a node to inspect</div>';
    } else {
      el.innerHTML = '<div class="lbl">' + node.label + '</div>'
        + '<div class="det">category: <span style="color:' + PALETTE[node.category] + '">'
        + node.category.replace(/_/g,' ') + '</span></div>'
        + '<div class="det">degree: ' + node.degree + '</div>'
        + '<div class="det">sparsity: ' + (node.sparsity * 100).toFixed(1) + '%</div>';
    }
  })
  .onNodeClick(node => {
    const linked = new Set();
    LINKS_RAW.forEach(l => {
      if (l.source === node.id) linked.add(l.target);
      if (l.target === node.id) linked.add(l.source);
    });
    Graph.nodeColor(n => n.id === node.id ? '#fff' : linked.has(n.id) ? PALETTE[n.category] : '#111');
    setTimeout(() => Graph.nodeColor(n => PALETTE[n.category] || '#555'), 2500);
  });

document.getElementById('sts').textContent =
  META.n_probes + ' nodes · ' + META.n_edges + ' edges · threshold ' + META.threshold.toFixed(2);

const catCounts = {};
ALL_NODES.forEach(n => catCounts[n.category] = (catCounts[n.category] || 0) + 1);
const catList = document.getElementById('cl');
Object.entries(PALETTE).forEach(([cat, color]) => {
  if (!catCounts[cat]) return;
  const row = document.createElement('div');
  row.className = 'cr';
  row.innerHTML = '<div class="cd" style="background:' + color + '"></div>'
    + '<div class="cl">' + cat.replace(/_/g,' ') + '</div>'
    + '<div class="cc">' + catCounts[cat] + '</div>';
  row.addEventListener('click', () => {
    visible[cat] = !visible[cat];
    row.classList.toggle('off', !visible[cat]);
    Graph.graphData(filteredData());
  });
  catList.appendChild(row);
});
</script>
</body>
</html>'''


def _get_force_graph_lib() -> str:
    lib_path = ROOT / "tmp" / "3d-force-graph.min.js"
    if not lib_path.exists():
        print("Downloading 3d-force-graph library (one-time, cached to tmp/)...")
        import urllib.request
        urllib.request.urlretrieve(
            "https://unpkg.com/3d-force-graph/dist/3d-force-graph.min.js",
            str(lib_path),
        )
        print(f"  Saved {lib_path.stat().st_size // 1024} KB → {lib_path}")
    content = lib_path.read_text(encoding="utf-8")
    # Prevent HTML parser from prematurely closing the script block
    return content.replace("</script>", r"<\/script>")


def _make_graph_html(lib_js: str, nodes: list, links: list,
                     palette: dict, meta: dict, title: str) -> str:
    html = _HTML_TEMPLATE
    html = html.replace("__LIBRARY__",      lib_js)
    html = html.replace("__NODES_JSON__",   json.dumps(nodes,   separators=(",", ":")))
    html = html.replace("__LINKS_JSON__",   json.dumps(links,   separators=(",", ":")))
    html = html.replace("__PALETTE_JSON__", json.dumps(palette, separators=(",", ":")))
    html = html.replace("__META_JSON__",    json.dumps(meta,    separators=(",", ":")))
    html = html.replace("__TITLE__",        title)
    return html


def cmd_graph(args):
    import numpy as np

    name      = getattr(args, "name", None)
    threshold = args.threshold
    out_act, out_probes_file, _, _ = _out_paths(name)

    if not out_act.exists():
        sys.exit(f"No activations found at {out_act}. Run: probe first.")

    data    = np.load(str(out_act))
    vectors = data["activations"]
    probes  = [json.loads(l) for l in out_probes_file.read_text(encoding="utf-8").splitlines()
               if l.strip()]
    cats    = [p["category"] for p in probes]
    n       = len(probes)
    print(f"Loaded {n} probes, dim={vectors.shape[1]:,}")

    # Cosine similarity matrix
    norms  = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms  = np.where(norms == 0, 1.0, norms)
    normed = vectors / norms
    sim    = normed @ normed.T

    # Edges above threshold (upper triangle only)
    raw_links: list[dict] = []
    for i in range(n):
        for j in range(i + 1, n):
            if sim[i, j] >= threshold:
                raw_links.append({"source": i, "target": j, "value": float(sim[i, j])})

    # Degree per node
    degree = [0] * n
    for lk in raw_links:
        degree[lk["source"]] += 1
        degree[lk["target"]] += 1

    nodes = [
        {
            "id":       i,
            "label":    probes[i]["label"],
            "category": probes[i]["category"],
            "sparsity": float(probes[i].get("sparsity", 0.0)),
            "degree":   degree[i],
        }
        for i in range(n)
    ]

    palette = make_palette(cats)
    meta    = {
        "name":      name or "brain_map",
        "threshold": threshold,
        "n_probes":  n,
        "n_edges":   len(raw_links),
    }

    lib_js   = _get_force_graph_lib()
    html_out = _make_graph_html(lib_js, nodes, raw_links, palette, meta, name or "unnamed")

    img_stem = name if name else "brain_map"
    BRAIN_MAPS_DIR.mkdir(parents=True, exist_ok=True)
    out_html = BRAIN_MAPS_DIR / f"{img_stem}_graph.html"
    out_html.write_text(html_out, encoding="utf-8")
    size_kb  = out_html.stat().st_size // 1024
    print(f"Graph saved: {out_html}  ({size_kb} KB)")
    print(f"Nodes: {n}  Edges: {len(raw_links)}  Threshold: {threshold:.2f}")


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

    name = getattr(args, "name", None)
    out_act, out_probes_file, _, _ = _out_paths(name)

    if not out_act.exists():
        sys.exit(f"No activations found at {out_act}. Run: probe first.")

    hub_threshold = args.threshold

    data    = np.load(str(out_act))
    vectors = data["activations"]
    probes  = [_json.loads(l)
               for l in out_probes_file.read_text(encoding="utf-8").splitlines()
               if l.strip()]
    labels  = [p["label"]    for p in probes]
    cats    = [p["category"] for p in probes]
    n, dim  = vectors.shape

    # Model geometry — read from file if saved, fall back to C13 defaults
    if "n_layer" in data:
        n_layer = int(data["n_layer"])
        n_head  = int(data["n_head"])
        N       = int(data["neuron_dim"])
    else:
        n_layer, n_head, N = 6, 4, 8192   # C13 fallback
    assert dim == n_layer * n_head * N, f"Geometry mismatch: {dim} ≠ {n_layer}×{n_head}×{N}"

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

    # Hub distribution across layers and heads — use geometry from file if available
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
    suffix = f"_{name}" if name else ""
    img_stem = name if name else "brain_map"
    BRAIN_MAPS_DIR.mkdir(parents=True, exist_ok=True)
    out_hubs = BRAIN_MAPS_DIR / f"{img_stem}_hubs.json"
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
    out_heatmap_nohubs = BRAIN_MAPS_DIR / f"{img_stem}_nohubs.png"
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

    category_order = list(dict.fromkeys(cats))
    cat_priority   = {c: i for i, c in enumerate(category_order)}
    order    = sorted(range(len(labels)),
                      key=lambda i: (cat_priority.get(cats[i], 99), labels[i]))
    sim_ord  = sim[np.ix_(order, order)]
    labs_ord = [labels[i] for i in order]
    cats_ord = [cats[i]   for i in order]

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    PALETTE = make_palette(cats_ord)

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
    p_probe.add_argument("--probes", default=None,
                         help="Path to probe set JSONL (e.g. training/corpus_admin/probe_sets/language.jsonl). "
                              "Omit to use built-in fallback probes.")
    p_probe.add_argument("--name", default=None,
                         help="Label for output files (e.g. c14_e2_language). "
                              "Files saved as tmp/brain_map_<name>_*.npz/jsonl/png.")
    p_probe.set_defaults(func=cmd_probe)

    p_map = sub.add_parser("map", help="Generate visualizations from saved activations")
    p_map.add_argument("--name", default=None,
                       help="Must match --name used during probe (default: unnamed)")
    p_map.set_defaults(func=cmd_map)

    p_hubs = sub.add_parser("hubs", help="Detect routing hubs, generate filtered heatmap")
    p_hubs.add_argument("--threshold", type=float, default=0.7,
                        help="Fraction of categories a neuron must fire in to be a hub (default 0.7)")
    p_hubs.add_argument("--name", default=None,
                        help="Must match --name used during probe (default: unnamed)")
    p_hubs.set_defaults(func=cmd_hubs)

    p_run = sub.add_parser("run", help="Probe then map (default)")
    p_run.add_argument("--checkpoint", default=str(DEFAULT_CHECKPOINT))
    p_run.add_argument("--probes", default=None,
                       help="Path to probe set JSONL.")
    p_run.add_argument("--name", default=None,
                       help="Label for output files.")
    p_run.set_defaults(func=cmd_run)

    p_graph = sub.add_parser("graph", help="Generate self-contained 3D interactive HTML brain map")
    p_graph.add_argument("--threshold", type=float, default=0.65,
                         help="Cosine similarity threshold for edges (default 0.65)")
    p_graph.add_argument("--name", default=None,
                         help="Must match --name used during probe")
    p_graph.set_defaults(func=cmd_graph)

    p_trace = sub.add_parser("trace", help="Run richer concept trace and decision report")
    p_trace.add_argument("--checkpoint", default=str(DEFAULT_CHECKPOINT))
    p_trace.add_argument("--probes", default=None,
                         help="Path to probe set JSONL. Omit to use built-in fallback probes.")
    p_trace.add_argument("--name", default=None,
                         help="Label for trace outputs.")
    p_trace.add_argument("--positions", choices=["last", "prompt"], default="prompt",
                         help="Token positions to summarize (default: prompt)")
    p_trace.add_argument("--top-k", type=int, default=32,
                         help="Top active dimensions to store per probe (default: 32)")
    p_trace.add_argument("--edge-threshold", type=float, default=0.65,
                         help="Concept connection threshold for cosine or Jaccard (default: 0.65)")
    p_trace.add_argument("--generate", action="store_true",
                         help="Generate an answer first, then trace prompt+answer and label output status.")
    p_trace.add_argument("--max-new-tokens", type=int, default=96)
    p_trace.add_argument("--temperature", type=float, default=0.8)
    p_trace.add_argument("--top-k-sample", type=int, default=40,
                         help="Sampling top-k for generation (default: 40)")
    p_trace.set_defaults(func=cmd_trace)

    p_trace_report = sub.add_parser("trace-report", help="Regenerate markdown report from a trace JSON")
    p_trace_report.add_argument("--name", default=None,
                                help="Must match --name used during trace")
    p_trace_report.set_defaults(func=cmd_trace_report)

    p_validate = sub.add_parser("validate-probes", help="Validate trace-ready probe metadata")
    p_validate.add_argument("probes", nargs="+",
                            help="Probe JSONL file(s) or directories containing *.jsonl")
    p_validate.add_argument("--no-strict", action="store_true",
                            help="Only require fields; skip consistency checks")
    p_validate.add_argument("--max-errors", type=int, default=20,
                            help="Maximum errors to print per file")
    p_validate.set_defaults(func=cmd_validate_probes)

    p_atlas = sub.add_parser("atlas", help="Generate drill-down concept atlas from trace artifacts")
    p_atlas.add_argument("--name", default=None,
                         help="Must match --name used during trace")
    p_atlas.add_argument("--edge-threshold", type=float, default=0.75,
                         help="Cosine threshold for concept links")
    p_atlas.add_argument("--jaccard-threshold", type=float, default=0.75,
                         help="Jaccard threshold for concept links")
    p_atlas.add_argument("--top-neurons-per-concept", type=int, default=24,
                         help="Top neurons shown in concept inspector")
    p_atlas.add_argument("--shared-pool", type=int, default=256,
                         help="Top neuron pool per concept used to find shared edge evidence")
    p_atlas.add_argument("--top-shared-neurons", type=int, default=12,
                         help="Shared neurons shown in edge inspector")
    p_atlas.add_argument("--max-edges", type=int, default=20000,
                         help="Maximum edges embedded in atlas HTML")
    p_atlas.set_defaults(func=cmd_atlas)

    args = ap.parse_args()

    # Default to run if no subcommand given
    if not hasattr(args, "func"):
        args.func = cmd_run
    if not hasattr(args, "checkpoint"):
        args.checkpoint = str(DEFAULT_CHECKPOINT)

    args.func(args)


if __name__ == "__main__":
    main()

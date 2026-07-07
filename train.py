#!/usr/bin/env python3
"""BDH curriculum training script.

Trains the BDH model on a single phase of training data.  Each phase
builds on the previous one by loading the prior checkpoint before
continuing.

Usage examples
--------------
  # Train phase 1 from scratch:
  python train.py --phase 1

  # Train phase 2 starting from phase 1 checkpoint:
  python train.py --phase 2 --resume core/phase_1.pt

  # Train phase 3 with custom hypers:
  python train.py --phase 3 --resume core/phase_2.pt --epochs 20 --lr 5e-4

  # Use a specific output path:
  python train.py --phase 1 --output core/my_run.pt

Checkpoints
-----------
  Saved to: core/phase_{N}.pt  (unless --output overrides)

Scaling
-------
  Pass --scale to use a larger BDHConfig (n_layer=12, n_embd=512, n_head=8, ~100M).
  Pass --scale-150m to use per-layer weights at 6x256 (~150M).
  Scaling only makes sense for phase 1 from scratch.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import hashlib
import json
import math
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from torch.optim.lr_scheduler import CosineAnnealingLR

try:
    import bitsandbytes.optim as bnb_optim
    _BNB_AVAILABLE = True
except ImportError:
    _BNB_AVAILABLE = False

from bdh import BDH, BDHConfig

ROOT = Path(__file__).resolve().parent
DEFAULT_SEED = 1337

# ---------------------------------------------------------------------------
# Phase → data files mapping
# ---------------------------------------------------------------------------

# Phase 0 = full corpus run (use --corpus-file to supply the assembled corpus).
# Phases 1-5 retained for reference but their old flat-file paths no longer exist;
# use --corpus-file for any new training run.
PHASE_FILES: dict[int, list[str]] = {
    0: [],  # populated at runtime via --corpus-file
    1: ["training_data/phase 1.md"],
    2: ["training_data/phase 2.md"],
    3: ["training_data/phase 3.md", "training_data/phase_3_ext.md"],
    4: [
        "training_data/phase_4.md",
        "training_data/phase_4_ext.md",
        "training_data/phase_4_ext2.md",
    ],
    5: ["training_data/phase_5_v1.md", "training_data/phase_5_v1_1.md"],
}

# Default hypers per phase (can be overridden with CLI flags)
PHASE_DEFAULTS: dict[int, dict] = {
    0: {"epochs": 5, "lr": 1e-3},   # full corpus run — override after first results
    1: {"epochs": 40, "lr": 1e-3},
    2: {"epochs": 30, "lr": 5e-4},
    3: {"epochs": 30, "lr": 5e-4},
    4: {"epochs": 25, "lr": 3e-4},
    5: {"epochs": 25, "lr": 3e-4},
}

# Default BDHConfig (small — ~25M params)
SMALL_CONFIG = BDHConfig(
    n_layer=6,
    n_embd=256,
    n_head=4,
    mlp_internal_dim_multiplier=128,
    vocab_size=256,
)

# Larger config (~100M params) for scaling experiments
LARGE_CONFIG = BDHConfig(
    n_layer=12,
    n_embd=512,
    n_head=8,
    mlp_internal_dim_multiplier=128,
    vocab_size=256,
)

# Per-layer 6x model (~150M params)
XL_150M_CONFIG = BDHConfig(
    n_layer=6,
    n_embd=256,
    n_head=4,
    mlp_internal_dim_multiplier=128,
    vocab_size=256,
    per_layer_weights=True,
)

# Per-layer model on wide dims (~600M params, 604M actual)
# n_layer=6 matches 150M depth — only width scales (256→512), so comparison is clean.
# n_layer=12 at these dims = 1.2B actual, static 19 GB fp32 — does not fit in 12 GB VRAM.
XL_600M_CONFIG = BDHConfig(
    n_layer=6,
    n_embd=512,
    n_head=8,
    mlp_internal_dim_multiplier=128,
    vocab_size=256,
    per_layer_weights=True,
)


def apply_architecture_variant(
    config: BDHConfig,
    *,
    architecture_variant: str,
    attention_decay: float | None,
    attention_half_life_tokens: float | None,
    learned_attention_decay: bool,
    activation_history_mix: float,
    activation_history_decay: float,
    activation_history_target: str,
    activation_history_max_mix: float,
    learned_activation_history: bool,
    compute_ticks: int,
    adaptive_compute: bool,
    adaptive_min_ticks: int,
    adaptive_max_ticks: int,
    adaptive_logit_delta_threshold: float,
) -> BDHConfig:
    """Return a size preset with explicit architecture-experiment knobs applied."""
    if attention_half_life_tokens is not None:
        attention_decay = math.log(2.0) / attention_half_life_tokens

    updates: dict[str, object] = {
        "architecture_variant": architecture_variant,
        "attention_decay": attention_decay,
        "learned_attention_decay": learned_attention_decay,
        "activation_history_mix": activation_history_mix,
        "activation_history_decay": activation_history_decay,
        "activation_history_target": activation_history_target,
        "activation_history_max_mix": activation_history_max_mix,
        "learned_activation_history": learned_activation_history,
        "compute_ticks": compute_ticks,
        "adaptive_compute": adaptive_compute,
        "adaptive_min_ticks": adaptive_min_ticks,
        "adaptive_max_ticks": adaptive_max_ticks,
        "adaptive_logit_delta_threshold": adaptive_logit_delta_threshold,
    }
    if architecture_variant == "temporal_decay" and attention_decay is None:
        updates["attention_decay"] = 0.001
    elif architecture_variant == "ctm_lite":
        if attention_decay is None:
            updates["attention_decay"] = 0.001
        if activation_history_mix == 0.0:
            updates["activation_history_mix"] = 0.1
    return dataclasses.replace(config, **updates)


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_text(paths: list[str]) -> bytes:
    """Load and concatenate text from one or more files (as raw bytes)."""
    chunks = []
    for p in paths:
        full = ROOT / p
        if not full.exists():
            raise FileNotFoundError(f"Training data not found: {full}")
        chunks.append(full.read_bytes())
    return b"\n".join(chunks)


def load_jsonl_examples(
    path: Path,
    response_delimiter: bytes,
    eot_byte: int,
) -> list[tuple[bytes, int]]:
    """Load JSONL into (sequence_bytes, response_start_idx) examples.

    Supported record shapes:
    - {"prompt": "...", "completion": "..."}
    - {"text": "...### Response:\\n..."}
    """
    if not path.exists():
        raise FileNotFoundError(f"JSONL data not found: {path}")

    examples: list[tuple[bytes, int]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue
            obj = json.loads(s)

            if "prompt" in obj and "completion" in obj:
                p = str(obj["prompt"]).encode("utf-8", errors="replace")
                c = str(obj["completion"]).encode("utf-8", errors="replace")
                if len(c) == 0:
                    continue
                seq = p + c + bytes([eot_byte])
                response_start = len(p)
                examples.append((seq, response_start))
                continue

            if "text" in obj:
                t = str(obj["text"]).encode("utf-8", errors="replace")
                pos = t.find(response_delimiter)
                if pos < 0:
                    raise ValueError(
                        f"{path}:{line_no}: missing response delimiter "
                        f"{response_delimiter!r} in 'text' field."
                    )
                response_start = pos + len(response_delimiter)
                if response_start >= len(t):
                    continue
                seq = t + bytes([eot_byte])
                examples.append((seq, response_start))
                continue

            raise ValueError(
                f"{path}:{line_no}: expected prompt/completion fields or a text field."
            )

    if not examples:
        raise ValueError(f"No usable examples loaded from {path}.")
    return examples


def estimate_windows_and_batches(
    n_tokens: int, block_size: int, batch_size: int
) -> tuple[int, int]:
    if block_size <= 0:
        raise ValueError(f"block_size must be > 0 (got {block_size}).")
    if batch_size <= 0:
        raise ValueError(f"batch_size must be > 0 (got {batch_size}).")
    if n_tokens <= block_size:
        raise ValueError(
            f"Not enough tokens for block_size={block_size}. "
            f"Need more than {block_size} bytes of data after tokenization, got {n_tokens}."
        )

    # Matches range(0, n_tokens - block_size, block_size)
    num_windows = (n_tokens - block_size + block_size - 1) // block_size
    n_batches = (num_windows + batch_size - 1) // batch_size
    return num_windows, n_batches


def make_batches(
    data: bytes | torch.Tensor,
    block_size: int,
    batch_size: int,
    device: torch.device,
    seed: int | None = None,
    shuffle: bool = True,
):
    """Yield (x, y) tensors from raw byte data indefinitely (one epoch pass).

    Accepts either raw bytes (converted once per call) or a pre-computed Long tensor.
    Pass a pre-converted tensor to avoid the expensive bytes→list→tensor conversion
    on every epoch.

    seed: when provided, shuffles with an isolated Generator so model-init RNG state
    does not affect data order. Pass seed=base_seed+epoch for deterministic per-epoch
    order that is identical across model sizes.

    shuffle: when False, emit windows in corpus order. Use this for ordered
    curricula where file sequence is part of the intervention.
    """
    if isinstance(data, torch.Tensor):
        ids = data
    else:
        ids = torch.frombuffer(bytearray(data), dtype=torch.uint8).long()
    n_tokens = len(ids) - 1  # need at least one next-token
    _, n_batches = estimate_windows_and_batches(n_tokens, block_size, batch_size)

    # All possible start indices
    starts = torch.arange(0, n_tokens - block_size, block_size, dtype=torch.long)
    if shuffle:
        # Shuffle with isolated generator so model init RNG doesn't affect data order.
        g = torch.Generator()
        if seed is not None:
            g.manual_seed(seed)
        perm = torch.randperm(len(starts), generator=g)
        starts = starts[perm]

    emitted = 0
    for i in range(0, len(starts), batch_size):
        batch_starts = starts[i : i + batch_size]
        if len(batch_starts) == 0:
            continue
        x = torch.stack([ids[int(s) : int(s) + block_size] for s in batch_starts]).to(device)
        y = torch.stack(
            [ids[int(s) + 1 : int(s) + block_size + 1] for s in batch_starts]
        ).to(device)
        emitted += 1
        yield x, y
    if emitted != n_batches:
        raise RuntimeError(
            f"Batch generation mismatch: expected {n_batches} batches, emitted {emitted}."
        )


def estimate_jsonl_batches(n_examples: int, batch_size: int) -> int:
    if n_examples <= 0:
        raise ValueError("Need at least one JSONL example to train.")
    if batch_size <= 0:
        raise ValueError(f"batch_size must be > 0 (got {batch_size}).")
    return (n_examples + batch_size - 1) // batch_size


def make_jsonl_batches(
    examples: list[tuple[bytes, int]],
    block_size: int,
    batch_size: int,
    device: torch.device,
    eot_byte: int,
    prompt_tail_bytes: int,
    prompt_loss_weight: float,
    seed: int | None = None,
    shuffle: bool = True,
):
    """Yield (x, y, mask) for prompt/completion JSONL training.

    mask is a per-target loss weight vector:
    - completion/EOT tokens: 1.0
    - prompt tokens: prompt_loss_weight
    - padded tokens: 0.0

    seed: see make_batches — isolated Generator keeps data order independent of model init.
    shuffle: when False, emit examples in file order.
    """
    if block_size <= 0:
        raise ValueError(f"block_size must be > 0 (got {block_size}).")

    n = len(examples)
    if shuffle:
        g = torch.Generator()
        if seed is not None:
            g.manual_seed(seed)
        order = torch.randperm(n, generator=g).tolist()
    else:
        order = list(range(n))
    n_batches = estimate_jsonl_batches(n, batch_size)
    emitted = 0

    for i in range(0, n, batch_size):
        batch_ids = order[i : i + batch_size]
        xs: list[torch.Tensor] = []
        ys: list[torch.Tensor] = []
        ms: list[torch.Tensor] = []

        for j in batch_ids:
            seq, response_start = examples[j]
            seq_len = len(seq)
            if seq_len < 2:
                continue

            max_start = max(0, seq_len - (block_size + 1))
            desired_start = max(0, response_start - prompt_tail_bytes)
            start = min(desired_start, max_start)
            if response_start < start:
                start = min(response_start, max_start)

            win = seq[start : start + block_size + 1]
            orig_win_len = len(win)
            if orig_win_len < block_size + 1:
                win += bytes([eot_byte]) * (block_size + 1 - orig_win_len)

            x = torch.tensor(list(win[:-1]), dtype=torch.long)
            y = torch.tensor(list(win[1:]), dtype=torch.long)

            # y[k] predicts absolute byte at (start + k + 1)
            abs_targets = torch.arange(start + 1, start + block_size + 1, dtype=torch.long)
            valid = abs_targets < (start + orig_win_len)
            in_completion = abs_targets >= response_start
            prompt_valid = valid & (~in_completion)
            m = in_completion.to(torch.float32) + prompt_valid.to(torch.float32) * prompt_loss_weight

            xs.append(x)
            ys.append(y)
            ms.append(m)

        if not xs:
            continue

        emitted += 1
        yield torch.stack(xs).to(device), torch.stack(ys).to(device), torch.stack(ms).to(device)

    if emitted != n_batches:
        raise RuntimeError(
            f"JSONL batch generation mismatch: expected {n_batches}, emitted {emitted}."
        )


def count_params(model: BDH) -> int:
    return sum(p.numel() for p in model.parameters())


def file_sha256(path: Path | None) -> str | None:
    if path is None:
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def set_reproducibility(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    # Note: torch.use_deterministic_algorithms(True) is intentionally omitted —
    # it forces slow CUDA fallbacks that make training unacceptably slow on this
    # architecture. Seeding is sufficient for reproducible experiments.


def batch_loss(
    model: BDH,
    x: torch.Tensor,
    y: torch.Tensor,
    mask: torch.Tensor | None,
) -> torch.Tensor:
    if mask is None:
        _, loss = model(x, targets=y)
        return loss

    logits, _ = model(x, targets=None)
    per_token = F.cross_entropy(
        logits.reshape(-1, logits.size(-1)),
        y.reshape(-1),
        reduction="none",
    )
    mask_flat = mask.reshape(-1)
    valid = mask_flat.sum()
    if valid.item() == 0:
        raise ValueError("Masked batch has no valid loss tokens.")
    return (per_token * mask_flat).sum() / valid


@torch.no_grad()
def evaluate(
    model: BDH,
    *,
    data_mode: str,
    data: torch.Tensor | None,
    examples: list[tuple[bytes, int]] | None,
    block_size: int,
    batch_size: int,
    device: torch.device,
    eot_byte: int,
    prompt_tail_bytes: int,
    prompt_loss_weight: float,
    mask_instruction_loss: bool,
    max_batches: int | None,
) -> float:
    was_training = model.training
    model.eval()
    try:
        total = 0.0
        count = 0
        if data_mode == "jsonl":
            assert examples is not None
            batch_iter = make_jsonl_batches(
                examples=examples,
                block_size=block_size,
                batch_size=batch_size,
                device=device,
                eot_byte=eot_byte,
                prompt_tail_bytes=prompt_tail_bytes,
                prompt_loss_weight=prompt_loss_weight,
                seed=None,
                shuffle=False,
            )
        else:
            assert data is not None
            batch_iter = make_batches(
                data,
                block_size,
                batch_size,
                device,
                seed=None,
                shuffle=False,
            )

        for i, batch in enumerate(batch_iter, start=1):
            if data_mode == "jsonl":
                x, y, m = batch
                mask = m if mask_instruction_loss else None
            else:
                x, y = batch
                mask = None
            loss = batch_loss(model, x, y, mask)
            total += float(loss.item())
            count += 1
            if max_batches is not None and i >= max_batches:
                break

        if count == 0:
            raise RuntimeError("Evaluation produced no batches.")
        return total / count
    finally:
        model.train(was_training)


def first_probe_batch(
    *,
    data_mode: str,
    data: torch.Tensor | None,
    examples: list[tuple[bytes, int]] | None,
    block_size: int,
    batch_size: int,
    device: torch.device,
    eot_byte: int,
    prompt_tail_bytes: int,
    prompt_loss_weight: float,
) -> torch.Tensor:
    if data_mode == "jsonl":
        assert examples is not None
        iterator = make_jsonl_batches(
            examples=examples,
            block_size=block_size,
            batch_size=batch_size,
            device=device,
            eot_byte=eot_byte,
            prompt_tail_bytes=prompt_tail_bytes,
            prompt_loss_weight=prompt_loss_weight,
            seed=None,
            shuffle=False,
        )
        x, _, _ = next(iterator)
        return x

    assert data is not None
    iterator = make_batches(
        data,
        block_size,
        batch_size,
        device,
        seed=None,
        shuffle=False,
    )
    x, _ = next(iterator)
    return x


def format_diagnostics(diagnostics: dict[str, Any]) -> str:
    layers = diagnostics.get("layers") or []
    if layers:
        avg_x_density = sum(layer["x_sparse_density"] for layer in layers) / len(layers)
        avg_y_density = sum(layer["y_sparse_density"] for layer in layers) / len(layers)
        avg_xy_density = sum(layer["xy_sparse_density"] for layer in layers) / len(layers)
        avg_x_abs = sum(layer["x_sparse_mean_abs"] for layer in layers) / len(layers)
        avg_xy_abs = sum(layer["xy_sparse_mean_abs"] for layer in layers) / len(layers)
    else:
        avg_x_density = avg_y_density = avg_xy_density = avg_x_abs = avg_xy_abs = 0.0

    half_life = diagnostics.get("attention_half_life_tokens")
    half_life_str = "none" if half_life is None else f"{half_life:.1f}"
    return (
        f"entropy {diagnostics['logit_entropy']:.4f}  "
        f"dlogits {diagnostics['logit_delta_mean']:.6f}  "
        f"x_density {avg_x_density:.4f}  "
        f"y_density {avg_y_density:.4f}  "
        f"xy_density {avg_xy_density:.4f}  "
        f"x_abs {avg_x_abs:.4f}  "
        f"xy_abs {avg_xy_abs:.4f}  "
        f"attn_half_life {half_life_str}"
    )


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def load_checkpoint(path: Path, model: BDH, device: torch.device) -> None:
    """Load weights from a checkpoint into model in-place."""
    torch.serialization.add_safe_globals([BDHConfig])
    ckpt = torch.load(path, map_location=device, weights_only=True)
    if isinstance(ckpt, dict):
        state = (
            ckpt.get("model_state_dict")
            or ckpt.get("model")
            or ckpt.get("state_dict")
            or ckpt
        )
    else:
        raise TypeError(f"Unsupported checkpoint format: {type(ckpt)}")
    missing, unexpected = model.load_state_dict(state, strict=False)
    if missing:
        print(f"  [warn] Missing keys: {missing[:5]}{'...' if len(missing) > 5 else ''}")
    if unexpected:
        print(f"  [warn] Unexpected keys: {unexpected[:5]}{'...' if len(unexpected) > 5 else ''}")


def save_checkpoint(
    path: Path,
    model: BDH,
    config: BDHConfig,
    phase: int,
    epoch: int,
    loss: float,
    metadata: dict[str, Any] | None = None,
    eval_loss: float | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "config": config,
            "phase": phase,
            "epoch": epoch,
            "loss": loss,
            "eval_loss": eval_loss,
            "metadata": metadata or {},
        },
        path,
    )


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def train(
    phase: int,
    resume: Path | None,
    output: Path,
    epochs: int,
    lr: float,
    batch_size: int,
    block_size: int,
    seed: int,
    log_interval: int,
    grad_accum_steps: int,
    amp_bf16: bool,
    log_vram: bool,
    adam8bit: bool,
    shuffle: bool,
    scale: bool,
    scale_150m: bool,
    scale_600m: bool,
    architecture_variant: str,
    attention_decay: float | None,
    attention_half_life_tokens: float | None,
    learned_attention_decay: bool,
    activation_history_mix: float,
    activation_history_decay: float,
    activation_history_target: str,
    activation_history_max_mix: float,
    learned_activation_history: bool,
    compute_ticks: int,
    adaptive_compute: bool,
    adaptive_min_ticks: int,
    adaptive_max_ticks: int,
    adaptive_logit_delta_threshold: float,
    jsonl_data: Path | None,
    eval_corpus_file: Path | None,
    eval_jsonl_data: Path | None,
    eval_interval: int,
    eval_max_batches: int | None,
    diagnostics_interval: int,
    mask_instruction_loss: bool,
    response_delimiter: bytes,
    eot_byte: int,
    prompt_tail_bytes: int,
    prompt_loss_weight: float,
    device: torch.device,
    corpus_file: Path | None = None,
    epoch_checkpoints: bool = False,
) -> None:
    print(f"\n{'='*60}")
    print(f"  BDH Phase {phase} Training")
    print(f"{'='*60}")

    # --- Data ---
    data_mode = "jsonl" if jsonl_data is not None else "phase_text"
    if data_mode == "jsonl":
        print(f"  JSONL data: {jsonl_data}")
        examples = load_jsonl_examples(
            path=jsonl_data,
            response_delimiter=response_delimiter,
            eot_byte=eot_byte,
        )
        print(f"  JSONL examples: {len(examples):,}")
        num_windows = len(examples)
        steps_per_epoch = estimate_jsonl_batches(len(examples), batch_size)
    else:
        if corpus_file is not None:
            paths = [str(corpus_file)]
        else:
            paths = PHASE_FILES[phase]
        print(f"  Data files: {paths}")
        data = load_text(paths)
        print(f"  Total bytes: {len(data):,}")
        n_tokens = len(data) - 1
        num_windows, steps_per_epoch = estimate_windows_and_batches(
            n_tokens=n_tokens,
            block_size=block_size,
            batch_size=batch_size,
        )
        # Pre-convert corpus bytes to a Long tensor once — avoids repeating
        # the expensive bytes→bytearray→tensor conversion on every epoch.
        print("  Pre-loading corpus tensor...", flush=True)
        data = torch.frombuffer(bytearray(data), dtype=torch.uint8).long()
        print(f"  Corpus tensor: {data.shape[0]:,} tokens", flush=True)
    updates_per_epoch = (steps_per_epoch + grad_accum_steps - 1) // grad_accum_steps
    total_updates = epochs * updates_per_epoch

    # --- Model ---
    if scale_600m:
        config = XL_600M_CONFIG
        model_name = "xl-600m"
    elif scale_150m:
        config = XL_150M_CONFIG
        model_name = "xl-150m"
    elif scale:
        config = LARGE_CONFIG
        model_name = "large-100m"
    else:
        config = SMALL_CONFIG
        model_name = "small-25m"
    config = apply_architecture_variant(
        config,
        architecture_variant=architecture_variant,
        attention_decay=attention_decay,
        attention_half_life_tokens=attention_half_life_tokens,
        learned_attention_decay=learned_attention_decay,
        activation_history_mix=activation_history_mix,
        activation_history_decay=activation_history_decay,
        activation_history_target=activation_history_target,
        activation_history_max_mix=activation_history_max_mix,
        learned_activation_history=learned_activation_history,
        compute_ticks=compute_ticks,
        adaptive_compute=adaptive_compute,
        adaptive_min_ticks=adaptive_min_ticks,
        adaptive_max_ticks=adaptive_max_ticks,
        adaptive_logit_delta_threshold=adaptive_logit_delta_threshold,
    )
    model = BDH(config).to(device)
    n_params = count_params(model)
    print(f"  Model: {model_name} ({n_params/1e6:.1f}M params)")
    print(f"  Architecture variant: {config.architecture_variant}")
    if config.attention_decay is not None:
        mode = "learned" if config.learned_attention_decay else "fixed"
        print(f"  Attention decay: {config.attention_decay} ({mode})")
    if config.activation_history_mix != 0.0:
        mode = "learned" if config.learned_activation_history else "fixed"
        print(
            "  Activation history: "
            f"mix={config.activation_history_mix} decay={config.activation_history_decay} "
            f"target={config.activation_history_target} ({mode})"
        )
    if config.attention_decay is not None:
        half_life = model.attention_half_life_tokens()
        if half_life is not None:
            print(f"  Attention half-life: {half_life:.1f} tokens")
    if config.compute_ticks != 1:
        print(f"  Compute ticks: {config.compute_ticks}")
    if config.adaptive_compute:
        print(
            "  Adaptive generation: "
            f"ticks={config.adaptive_min_ticks}-{config.adaptive_max_ticks} "
            f"delta<={config.adaptive_logit_delta_threshold}"
        )

    if resume is not None:
        print(f"  Resuming from: {resume}")
        load_checkpoint(resume, model, device)
    else:
        print("  Training from scratch.")

    # --- Optimizer & scheduler ---
    if adam8bit:
        if not _BNB_AVAILABLE:
            raise RuntimeError("--adam8bit requires bitsandbytes: pip install bitsandbytes")
        optimizer = bnb_optim.AdamW8bit(model.parameters(), lr=lr, weight_decay=0.1)
        print("  Optimizer: AdamW8bit (bitsandbytes) — optimizer states in 8-bit")
    else:
        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.1)
    scheduler = CosineAnnealingLR(optimizer, T_max=total_updates, eta_min=lr * 0.1)

    order_mode = "seeded-shuffle" if shuffle else "sequential"
    print(f"  Seed: {seed}  |  Deterministic: enabled  |  Data order: {order_mode}")
    print(
        f"  Epochs: {epochs}  |  Windows/epoch: {num_windows}  |  "
        f"Micro-steps/epoch: {steps_per_epoch}  |  "
        f"Optimizer updates/epoch: {updates_per_epoch}  |  "
        f"Total optimizer updates: {total_updates}  |  LR: {lr}"
    )
    print(f"  Block size: {block_size}  |  Batch size: {batch_size}")
    print(f"  Grad accumulation: {grad_accum_steps}")
    print(f"  AMP bf16: {'enabled' if amp_bf16 else 'disabled'}")
    if data_mode == "jsonl":
        print(f"  Data mode: jsonl")
        print(f"  Mask instruction loss: {'enabled' if mask_instruction_loss else 'disabled'}")
        print(f"  Response delimiter: {response_delimiter!r}")
        print(f"  EOT byte: {eot_byte}")
        print(f"  Prompt tail bytes: {prompt_tail_bytes}")
        print(f"  Prompt loss weight: {prompt_loss_weight}")
    else:
        print(f"  Data mode: phase_text")
    print(f"  VRAM logging: {'enabled' if log_vram else 'disabled'}")
    print(f"  Log interval: every {log_interval} step(s)")
    print(f"  Output: {output}")
    print(f"  Eval interval: every {eval_interval} epoch(s)")
    print()

    # --- Eval data ---
    eval_data_mode = None
    eval_data = None
    eval_examples = None
    eval_source = None
    if eval_jsonl_data is not None:
        eval_data_mode = "jsonl"
        eval_source = eval_jsonl_data
        print(f"  Eval JSONL data: {eval_jsonl_data}")
        eval_examples = load_jsonl_examples(
            path=eval_jsonl_data,
            response_delimiter=response_delimiter,
            eot_byte=eot_byte,
        )
        print(f"  Eval JSONL examples: {len(eval_examples):,}")
    elif eval_corpus_file is not None:
        eval_data_mode = "phase_text"
        eval_source = eval_corpus_file
        print(f"  Eval corpus: {eval_corpus_file}")
        eval_bytes = load_text([str(eval_corpus_file)])
        eval_data = torch.frombuffer(bytearray(eval_bytes), dtype=torch.uint8).long()
        print(f"  Eval corpus tensor: {eval_data.shape[0]:,} tokens")

    run_metadata: dict[str, Any] = {
        "argv": sys.argv,
        "seed": seed,
        "git_commit": git_commit(),
        "model_name": model_name,
        "n_params": n_params,
        "phase": phase,
        "resume": str(resume) if resume is not None else None,
        "output": str(output),
        "corpus_file": str(corpus_file) if corpus_file is not None else None,
        "corpus_sha256": file_sha256(corpus_file) if corpus_file is not None else None,
        "jsonl_data": str(jsonl_data) if jsonl_data is not None else None,
        "jsonl_sha256": file_sha256(jsonl_data) if jsonl_data is not None else None,
        "eval_source": str(eval_source) if eval_source is not None else None,
        "eval_sha256": file_sha256(eval_source) if eval_source is not None else None,
        "epochs": epochs,
        "lr": lr,
        "batch_size": batch_size,
        "block_size": block_size,
        "grad_accum_steps": grad_accum_steps,
        "shuffle": shuffle,
        "steps_per_epoch": steps_per_epoch,
        "updates_per_epoch": updates_per_epoch,
        "total_updates": total_updates,
        "eval_interval": eval_interval,
        "eval_max_batches": eval_max_batches,
    }

    model.train()
    best_loss = float("inf")
    best_metric_name = "eval_loss" if eval_data_mode is not None else "train_loss"
    global_micro_step = 0  # 1-indexed in logs
    global_update_step = 0  # 1-indexed in logs
    latest_diagnostics: dict[str, Any] | None = None
    for epoch in range(1, epochs + 1):
        epoch_loss = 0.0
        n_micro_steps = 0
        n_update_steps = 0
        t0 = time.time()
        optimizer.zero_grad(set_to_none=True)
        if log_vram and device.type == "cuda":
            torch.cuda.reset_peak_memory_stats(device=device)

        if data_mode == "jsonl":
            batch_iter = make_jsonl_batches(
                examples=examples,
                block_size=block_size,
                batch_size=batch_size,
                device=device,
                eot_byte=eot_byte,
                prompt_tail_bytes=prompt_tail_bytes,
                prompt_loss_weight=prompt_loss_weight,
                seed=seed + epoch,
                shuffle=shuffle,
            )
        else:
            batch_iter = make_batches(
                data,
                block_size,
                batch_size,
                device,
                seed=seed + epoch,
                shuffle=shuffle,
            )

        for step_in_epoch, batch in enumerate(batch_iter, start=1):
            if data_mode == "jsonl":
                x, y, m = batch
            else:
                x, y = batch
                m = None

            with (
                torch.autocast(device_type="cuda", dtype=torch.bfloat16)
                if amp_bf16 and device.type == "cuda"
                else contextlib.nullcontext()
            ):
                loss = batch_loss(
                    model,
                    x,
                    y,
                    m if data_mode == "jsonl" and mask_instruction_loss else None,
                )

            raw_loss = float(loss.item())
            (loss / grad_accum_steps).backward()

            should_step = (
                step_in_epoch % grad_accum_steps == 0
                or step_in_epoch == steps_per_epoch
            )
            if should_step:
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
                n_update_steps += 1
                global_update_step += 1

            epoch_loss += raw_loss
            n_micro_steps += 1
            global_micro_step += 1

            if (
                step_in_epoch == 1
                or step_in_epoch % log_interval == 0
                or step_in_epoch == steps_per_epoch
            ):
                current_lr = scheduler.get_last_lr()[0]
                vram_str = ""
                if log_vram and device.type == "cuda":
                    alloc_mb = torch.cuda.memory_allocated(device=device) / (1024 * 1024)
                    reserved_mb = torch.cuda.memory_reserved(device=device) / (1024 * 1024)
                    peak_mb = torch.cuda.max_memory_allocated(device=device) / (1024 * 1024)
                    vram_str = (
                        f"  vram alloc/res/peak "
                        f"{alloc_mb:.0f}/{reserved_mb:.0f}/{peak_mb:.0f}MB"
                    )
                print(
                    f"    step {step_in_epoch:4d}/{steps_per_epoch} "
                    f"(global micro {global_micro_step:5d}/{epochs * steps_per_epoch}, "
                    f"update {global_update_step:5d}/{total_updates})  "
                    f"loss {raw_loss:.4f}  lr {current_lr:.2e}{vram_str}"
                )

        if n_micro_steps != steps_per_epoch:
            raise RuntimeError(
                f"Micro-step mismatch in epoch {epoch}: "
                f"expected {steps_per_epoch}, saw {n_micro_steps}."
            )
        if n_update_steps != updates_per_epoch:
            raise RuntimeError(
                f"Optimizer-step mismatch in epoch {epoch}: "
                f"expected {updates_per_epoch}, saw {n_update_steps}."
            )

        avg_loss = epoch_loss / max(n_micro_steps, 1)
        eval_loss = None
        if eval_data_mode is not None and (epoch % eval_interval == 0 or epoch == epochs):
            eval_loss = evaluate(
                model,
                data_mode=eval_data_mode,
                data=eval_data,
                examples=eval_examples,
                block_size=block_size,
                batch_size=batch_size,
                device=device,
                eot_byte=eot_byte,
                prompt_tail_bytes=prompt_tail_bytes,
                prompt_loss_weight=prompt_loss_weight,
                mask_instruction_loss=mask_instruction_loss,
                max_batches=eval_max_batches,
            )
        if diagnostics_interval > 0 and epoch % diagnostics_interval == 0:
            probe_mode = eval_data_mode or data_mode
            probe_data = eval_data if eval_data_mode is not None else (None if data_mode == "jsonl" else data)
            probe_examples = eval_examples if eval_data_mode is not None else (examples if data_mode == "jsonl" else None)
            probe_x = first_probe_batch(
                data_mode=probe_mode,
                data=probe_data,
                examples=probe_examples,
                block_size=block_size,
                batch_size=batch_size,
                device=device,
                eot_byte=eot_byte,
                prompt_tail_bytes=prompt_tail_bytes,
                prompt_loss_weight=prompt_loss_weight,
            )
            latest_diagnostics = model.diagnostics(probe_x)
        elapsed = time.time() - t0
        current_lr = scheduler.get_last_lr()[0]

        eval_str = f"eval_loss {eval_loss:.4f}  " if eval_loss is not None else ""
        print(
            f"  epoch {epoch:3d}/{epochs}  "
            f"loss {avg_loss:.4f}  "
            f"{eval_str}"
            f"lr {current_lr:.2e}  "
            f"({elapsed:.1f}s)"
        )
        if latest_diagnostics is not None and diagnostics_interval > 0 and epoch % diagnostics_interval == 0:
            print(f"    diagnostics: {format_diagnostics(latest_diagnostics)}")

        metric = eval_loss if eval_data_mode is not None else avg_loss
        if metric is not None and metric < best_loss:
            best_loss = metric
            metadata = {
                **run_metadata,
                "best_metric_name": best_metric_name,
                "best_metric": best_loss,
                "train_loss": avg_loss,
                "eval_loss": eval_loss,
                "epoch": epoch,
                "diagnostics": latest_diagnostics,
            }
            save_checkpoint(
                output,
                model,
                config,
                phase,
                epoch,
                avg_loss,
                metadata=metadata,
                eval_loss=eval_loss,
            )

        if epoch_checkpoints:
            epoch_path = output.with_name(f"{output.stem}_e{epoch}{output.suffix}")
            metadata = {
                **run_metadata,
                "best_metric_name": best_metric_name,
                "train_loss": avg_loss,
                "eval_loss": eval_loss,
                "epoch": epoch,
                "diagnostics": latest_diagnostics,
            }
            save_checkpoint(
                epoch_path,
                model,
                config,
                phase,
                epoch,
                avg_loss,
                metadata=metadata,
                eval_loss=eval_loss,
            )
            print(f"  Epoch checkpoint: {epoch_path}")

    print(f"\n  Best {best_metric_name}: {best_loss:.4f}")
    print(f"  Checkpoint saved: {output}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def check_training_audit() -> None:
    """Verify that the final training audit has passed before starting."""
    audit_file = ROOT / "training_activation_audit.md"
    if not audit_file.exists():
        print("=" * 80)
        print("TRAINING BLOCKED: MISSING AUDIT FILE")
        print("=" * 80)
        print(f"Error: Audit file not found at: {audit_file}")
        print("Training cannot begin until the repo-wide audit is complete.")
        print("See `todo.md` for the final audit steps required.")
        sys.exit(1)

    content = audit_file.read_text()
    if "GO" not in content:
        print("=" * 80)
        print("TRAINING BLOCKED: AUDIT NOT PASSED")
        print("=" * 80)
        print(f"Error: Audit file found, but it is not in a 'GO' state.")
        print("The audit reported:")
        for line in content.splitlines():
            if "go / no-go" in line.lower():
                print(f"  > {line}")
        print("\nTraining cannot begin until the audit passes with a 'GO' status.")
        sys.exit(1)

    print("  Training audit: PASSED")


def main() -> None:
    parser = argparse.ArgumentParser(description="BDH curriculum trainer")
    parser.add_argument("--phase", type=int, default=0, choices=[0, 1, 2, 3, 4, 5],
                        help="Training phase (0=full corpus run, 1–5=legacy phases; default: 0)")
    parser.add_argument("--resume", type=Path, default=None,
                        help="Checkpoint to load before training (for phases 2+)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Output checkpoint path (default: core/phase_{N}.pt)")
    parser.add_argument("--epochs", type=int, default=None,
                        help="Number of epochs (overrides phase default)")
    parser.add_argument("--lr", type=float, default=None,
                        help="Learning rate (overrides phase default)")
    parser.add_argument("--batch-size", type=int, default=8,
                        help="Batch size (default: 8 — safe for 12GB GPU)")
    parser.add_argument("--block-size", type=int, default=256,
                        help="Context window in bytes (default: 256)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help=f"Random seed (default: {DEFAULT_SEED})")
    parser.add_argument("--log-interval", type=int, default=25,
                        help="Per-step progress print frequency within each epoch (default: 25)")
    parser.add_argument("--grad-accum-steps", type=int, default=1,
                        help="Number of micro-batches to accumulate before optimizer step (default: 1)")
    parser.add_argument("--amp-bf16", action="store_true",
                        help="Enable CUDA AMP autocast with bfloat16")
    parser.add_argument("--log-vram", action="store_true",
                        help="Log CUDA VRAM usage during training progress updates")
    parser.add_argument("--adam8bit", action="store_true",
                        help="Use bitsandbytes AdamW8bit optimizer (reduces optimizer VRAM ~4x; requires bitsandbytes)")
    parser.add_argument("--no-shuffle", action="store_true",
                        help="Disable per-epoch data shuffling and consume batches in source order")
    parser.add_argument("--allow-fresh-start", action="store_true",
                        help="Explicitly allow phase 2+ training without --resume")
    parser.add_argument("--skip-training-audit", action="store_true",
                        help="Bypass the legacy repo-wide training_activation_audit.md gate. "
                             "Only for audited MSM micro-updates or other explicitly gated wrappers.")
    parser.add_argument("--jsonl-data", type=Path, default=None,
                        help="Optional prompt/completion JSONL training file (overrides phase text data)")
    parser.add_argument("--mask-instruction-loss", action="store_true",
                        help="In JSONL mode, compute loss only on completion tokens")
    parser.add_argument("--response-delimiter", type=str, default="### Response:\\n",
                        help="Delimiter used to locate completion start for JSONL text mode")
    parser.add_argument("--eot-byte", type=int, default=0,
                        help="End-of-example byte appended in JSONL mode (default: 0)")
    parser.add_argument("--prompt-tail-bytes", type=int, default=768,
                        help="In JSONL mode, include this many prompt bytes before response in each crop")
    parser.add_argument("--prompt-loss-weight", type=float, default=0.0,
                        help="In JSONL+mask mode, loss weight for prompt tokens (0.0 = hard mask)")
    parser.add_argument("--scale", action="store_true",
                        help="Use larger model config (~100M params)")
    parser.add_argument("--scale-150m", action="store_true",
                        help="Use per-layer 6x model config (~150M params)")
    parser.add_argument("--scale-600m", action="store_true",
                        help="Use per-layer 6x large model config (~600M params)")
    parser.add_argument("--architecture-variant", choices=["bdh_v1", "temporal_decay", "ctm_lite"],
                        default="bdh_v1",
                        help="Architecture experiment variant (default: bdh_v1)")
    parser.add_argument("--attention-decay", type=float, default=None,
                        help="Enable causal attention distance decay with this non-negative rate")
    parser.add_argument("--attention-half-life-tokens", type=float, default=None,
                        help="Set attention decay via half-life in tokens/bytes; overrides --attention-decay")
    parser.add_argument("--learned-attention-decay", action="store_true",
                        help="Learn one attention decay rate per head")
    parser.add_argument("--activation-history-mix", type=float, default=0.0,
                        help="Mix causal sparse activation history into sparse activations")
    parser.add_argument("--activation-history-decay", type=float, default=0.5,
                        help="EMA decay for sparse activation history (default: 0.5)")
    parser.add_argument("--activation-history-target", choices=["x", "y", "both", "pre_gate"],
                        default="x",
                        help="Where to apply activation history (default: x)")
    parser.add_argument("--activation-history-max-mix", type=float, default=0.5,
                        help="Upper bound for learned positive activation-history mix (default: 0.5)")
    parser.add_argument("--learned-activation-history", action="store_true",
                        help="Learn per-head activation-history mix and decay")
    parser.add_argument("--compute-ticks", type=int, default=1,
                        help="Fixed whole-stack recurrent passes (default: 1)")
    parser.add_argument("--adaptive-compute", action="store_true",
                        help="Enable adaptive compute during generation")
    parser.add_argument("--adaptive-min-ticks", type=int, default=1,
                        help="Minimum adaptive generation ticks (default: 1)")
    parser.add_argument("--adaptive-max-ticks", type=int, default=1,
                        help="Maximum adaptive generation ticks (default: 1)")
    parser.add_argument("--adaptive-logit-delta-threshold", type=float, default=0.0,
                        help="Adaptive generation early-stop threshold across tick logits")
    parser.add_argument("--corpus-file", type=Path, default=None,
                        help="Pre-assembled corpus text file (overrides PHASE_FILES lookup; "
                             "use with --phase 0 for a full corpus run)")
    parser.add_argument("--eval-corpus-file", type=Path, default=None,
                        help="Held-out corpus text file for deterministic eval loss")
    parser.add_argument("--eval-jsonl-data", type=Path, default=None,
                        help="Held-out prompt/completion JSONL file for deterministic eval loss")
    parser.add_argument("--eval-interval", type=int, default=1,
                        help="Evaluate every N epochs when eval data is provided (default: 1)")
    parser.add_argument("--eval-max-batches", type=int, default=None,
                        help="Maximum eval batches per eval pass (default: all)")
    parser.add_argument("--diagnostics-interval", type=int, default=1,
                        help="Print architecture diagnostics every N epochs; 0 disables")
    parser.add_argument("--epoch-checkpoints", action="store_true",
                        help="Save a checkpoint after every epoch (named <output>_e<N>.pt) "
                             "in addition to the best-loss checkpoint")
    parser.add_argument("--device", type=str, default=None,
                        help="Device: cpu / cuda / mps (auto-detected if omitted)")
    args = parser.parse_args()

    # --- Audit check ---
    if args.skip_training_audit:
        print("  Training audit: SKIPPED by explicit --skip-training-audit")
    else:
        check_training_audit()

    # Resolve defaults
    defaults = PHASE_DEFAULTS[args.phase]
    epochs = args.epochs if args.epochs is not None else defaults["epochs"]
    lr = args.lr if args.lr is not None else defaults["lr"]
    output = args.output if args.output is not None else ROOT / f"core/phase_{args.phase}.pt"
    if args.log_interval <= 0:
        parser.error("--log-interval must be > 0.")
    if args.grad_accum_steps <= 0:
        parser.error("--grad-accum-steps must be > 0.")
    if args.phase == 0 and args.corpus_file is None and args.jsonl_data is None:
        parser.error("--phase 0 requires --corpus-file (or --jsonl-data) to specify training data.")
    if args.corpus_file is not None and not args.corpus_file.exists():
        parser.error(f"--corpus-file not found: {args.corpus_file}")
    if args.phase >= 2 and args.resume is None and not args.allow_fresh_start:
        parser.error(
            f"Phase {args.phase} requires --resume <checkpoint> to continue from prior phase. "
            "If you intentionally want to start fresh, add --allow-fresh-start."
        )
    if sum([args.scale, args.scale_150m, args.scale_600m]) > 1:
        parser.error("Choose only one scale mode: --scale, --scale-150m, or --scale-600m.")
    if args.resume is not None and not args.resume.exists():
        parser.error(f"--resume checkpoint not found: {args.resume}")
    if args.jsonl_data is not None and not args.jsonl_data.exists():
        parser.error(f"--jsonl-data not found: {args.jsonl_data}")
    if args.eval_corpus_file is not None and not args.eval_corpus_file.exists():
        parser.error(f"--eval-corpus-file not found: {args.eval_corpus_file}")
    if args.eval_jsonl_data is not None and not args.eval_jsonl_data.exists():
        parser.error(f"--eval-jsonl-data not found: {args.eval_jsonl_data}")
    if args.eval_corpus_file is not None and args.eval_jsonl_data is not None:
        parser.error("Choose only one eval data source: --eval-corpus-file or --eval-jsonl-data.")
    if args.mask_instruction_loss and args.jsonl_data is None:
        parser.error("--mask-instruction-loss requires --jsonl-data.")
    if args.eot_byte < 0 or args.eot_byte > 255:
        parser.error("--eot-byte must be in [0, 255].")
    if args.prompt_tail_bytes < 0:
        parser.error("--prompt-tail-bytes must be >= 0.")
    if args.jsonl_data is not None and args.prompt_tail_bytes >= args.block_size:
        parser.error("--prompt-tail-bytes must be < --block-size.")
    if args.prompt_loss_weight < 0.0:
        parser.error("--prompt-loss-weight must be >= 0.")
    if args.attention_decay is not None and args.attention_decay < 0.0:
        parser.error("--attention-decay must be >= 0.")
    if args.attention_half_life_tokens is not None and args.attention_half_life_tokens <= 0.0:
        parser.error("--attention-half-life-tokens must be > 0.")
    if not 0.0 <= args.activation_history_decay <= 1.0:
        parser.error("--activation-history-decay must be in [0, 1].")
    if args.activation_history_max_mix <= 0.0:
        parser.error("--activation-history-max-mix must be > 0.")
    if args.compute_ticks < 1:
        parser.error("--compute-ticks must be >= 1.")
    if args.adaptive_min_ticks < 1:
        parser.error("--adaptive-min-ticks must be >= 1.")
    if args.adaptive_max_ticks < args.adaptive_min_ticks:
        parser.error("--adaptive-max-ticks must be >= --adaptive-min-ticks.")
    if args.adaptive_logit_delta_threshold < 0.0:
        parser.error("--adaptive-logit-delta-threshold must be >= 0.")
    if args.eval_interval <= 0:
        parser.error("--eval-interval must be > 0.")
    if args.eval_max_batches is not None and args.eval_max_batches <= 0:
        parser.error("--eval-max-batches must be > 0.")
    if args.diagnostics_interval < 0:
        parser.error("--diagnostics-interval must be >= 0.")

    device = torch.device(
        args.device
        if args.device
        else ("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    )

    print(f"  Python: {sys.executable}")
    print(f"  Device: {device}")
    print(f"  Phase: {args.phase}")
    print(f"  Seed: {args.seed}")
    print(f"  Data order: {'sequential' if args.no_shuffle else 'seeded-shuffle'}")
    if args.amp_bf16 and device.type != "cuda":
        parser.error("--amp-bf16 requires --device cuda (or auto-selected cuda).")
    if args.resume is not None:
        print(f"  Resume checkpoint: {args.resume}")
    else:
        print("  Resume checkpoint: none (fresh start)")

    set_reproducibility(args.seed)

    train(
        phase=args.phase,
        resume=args.resume,
        output=output,
        epochs=epochs,
        lr=lr,
        batch_size=args.batch_size,
        block_size=args.block_size,
        seed=args.seed,
        log_interval=args.log_interval,
        grad_accum_steps=args.grad_accum_steps,
        amp_bf16=args.amp_bf16,
        log_vram=args.log_vram,
        adam8bit=args.adam8bit,
        shuffle=not args.no_shuffle,
        scale=args.scale,
        scale_150m=args.scale_150m,
        scale_600m=args.scale_600m,
        architecture_variant=args.architecture_variant,
        attention_decay=args.attention_decay,
        attention_half_life_tokens=args.attention_half_life_tokens,
        learned_attention_decay=args.learned_attention_decay,
        activation_history_mix=args.activation_history_mix,
        activation_history_decay=args.activation_history_decay,
        activation_history_target=args.activation_history_target,
        activation_history_max_mix=args.activation_history_max_mix,
        learned_activation_history=args.learned_activation_history,
        compute_ticks=args.compute_ticks,
        adaptive_compute=args.adaptive_compute,
        adaptive_min_ticks=args.adaptive_min_ticks,
        adaptive_max_ticks=args.adaptive_max_ticks,
        adaptive_logit_delta_threshold=args.adaptive_logit_delta_threshold,
        jsonl_data=args.jsonl_data,
        eval_corpus_file=args.eval_corpus_file,
        eval_jsonl_data=args.eval_jsonl_data,
        eval_interval=args.eval_interval,
        eval_max_batches=args.eval_max_batches,
        diagnostics_interval=args.diagnostics_interval,
        mask_instruction_loss=args.mask_instruction_loss,
        response_delimiter=args.response_delimiter.encode("utf-8"),
        eot_byte=args.eot_byte,
        prompt_tail_bytes=args.prompt_tail_bytes,
        prompt_loss_weight=args.prompt_loss_weight,
        device=device,
        corpus_file=args.corpus_file,
        epoch_checkpoints=args.epoch_checkpoints,
    )


if __name__ == "__main__":
    main()

# RTK — Rust Token Killer

RTK is a CLI proxy that compresses verbose shell output before it reaches the model context, reducing token waste by 60–90%.

Binary: `~/.local/bin/rtk` (v0.39.0, x86_64 Linux musl)

## When to use

Prefix shell commands with `rtk` when their output would otherwise be verbose:

```bash
rtk git status
rtk git diff
rtk grep pattern path/
rtk find . -name "*.md"
rtk read path/to/file.md
```

## When NOT to use

- When you need the raw unfiltered output (use `rtk proxy <cmd>` to bypass)
- For short commands whose output is already compact (echo, wc, pwd, etc.)
- For writes — rtk is a read/query proxy, not a write wrapper

## Analytics

```bash
rtk gain            # cumulative token savings
rtk gain --history  # per-command savings history
```

## Installation note

No global hook is installed. Use explicit `rtk` prefix only.
To re-verify: `rtk --version` and `which rtk`.

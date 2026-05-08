# Codex Handoff — 2026-05-08

Read this file first in the next session.

## Current State

- Branch: `main`
- HEAD at handoff: `5da9b33`
- No DeepSeek / `opencode` jobs are currently running

## What Was Done

### 1. Standardized DeepSeek via `opencode`

Created repo-local guidance and wrappers so outsourcing does not need to be reinvented each session.

Key files:

- [`docs/opencode_deepseek.md`](/home/aomukai/Ninereeds/docs/opencode_deepseek.md)
- [`meta/scripts/opencode_ds.sh`](/home/aomukai/Ninereeds/meta/scripts/opencode_ds.sh)
- [`meta/scripts/opencode_ds_fanout.sh`](/home/aomukai/Ninereeds/meta/scripts/opencode_ds_fanout.sh)

Policy now documented there:

- do not use worker MCP delegation for corpus execution
- outsource file work through DeepSeek via `opencode`
- keep Codex local for routing, verification, and cleanup

### 2. Finished the duplicate queue

Runner:

- [`meta/repair_duplicates_opencode.py`](/home/aomukai/Ninereeds/meta/repair_duplicates_opencode.py)

Ledgers:

- [`training_data/phases/repair_progress_duplicate.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_progress_duplicate.txt)
- [`training_data/phases/repair_skipped_duplicate.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_skipped_duplicate.txt)

Status:

- duplicate queue complete for live corpus files
- `58` live files completed
- `1` stale skipped target: `training_data/phases/adj_rewrites.md`

Last duplicate file completed:

- [`training_data/phases/phase_6/phase_6_983.md`](/home/aomukai/Ninereeds/training_data/phases/phase_6/phase_6_983.md)

### 3. Cleaned the formatting queue of stale targets

Removed dead paths from the live queue and preserved them separately.

Files:

- live queue: [`training_data/phases/repair_formatting.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_formatting.txt)
- skipped rows: [`training_data/phases/repair_skipped_formatting.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_skipped_formatting.txt)

Formatting queue after cleanup:

- `275` live unique target files
- `8` skipped stale rows

### 4. Started the formatting pass

Runner:

- [`meta/repair_formatting_opencode.py`](/home/aomukai/Ninereeds/meta/repair_formatting_opencode.py)

Progress ledger:

- [`training_data/phases/repair_progress_formatting.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_progress_formatting.txt)

Current formatting status:

- `52` completed
- `223` remaining

Last completed formatting file:

- [`training_data/phases/phase_1/phase_1_945.md`](/home/aomukai/Ninereeds/training_data/phases/phase_1/phase_1_945.md)

## Operational Notes

DeepSeek v4 flash works, but the main failure modes were output-shape issues, not repo logic:

- returns prose like `Done.` instead of file text
- returns receipt-style text instead of file text
- leaves blank `[Ninereeds]` opener lines
- appends stray trailing code fences
- sometimes echoes `=== END ===`

The current formatting runner already handles most of this:

- retries once with a narrower prompt
- strips `=== END ===`
- strips standalone code-fence lines
- verifies `[user]` / `[Ninereeds]` structure after every write
- appends the progress ledger only after a confirmed write

One manual cleanup was done for a stubborn file:

- [`training_data/phases/phase_1/phase_1_1247.md`](/home/aomukai/Ninereeds/training_data/phases/phase_1/phase_1_1247.md)

That file had already been semantically rewritten on disk; only the blank opener lines remained, so they were patched manually and the file was appended to the formatting progress ledger.

## Recommended Resume Path

Continue the formatting queue with small parallel waves.

Command:

```bash
python3 meta/repair_formatting_opencode.py --batch 6 --workers 6 --timeout 300
```

This was the best speed/cleanliness tradeoff reached in this session.

## Next Pending Files

The next live formatting targets are:

1. `training_data/phases/phase_1/phase_1_959.md`
2. `training_data/phases/phase_1/phase_1_964.md`
3. `training_data/phases/phase_1/phase_1_975.md`
4. `training_data/phases/phase_1/phase_1_729.md`
5. `training_data/phases/phase_1/phase_1_798.md`
6. `training_data/phases/phase_1/phase_1_799.md`

## Verification Commands

Current exact counts can be rechecked with:

```bash
python3 - <<'PY'
from pathlib import Path
q=Path('training_data/phases/repair_formatting.txt')
rows=[]
for line in q.read_text().splitlines():
    if '.md' in line and '|' in line:
        rows.append(line.split('|',1)[0].strip())
uniq=[]; seen=set()
for p in rows:
    if p not in seen:
        seen.add(p); uniq.append(p)
done=[x.strip() for x in Path('training_data/phases/repair_progress_formatting.txt').read_text().splitlines() if x.strip()]
print('total', len(uniq))
print('done', len(done))
print('remaining', len([p for p in uniq if p not in set(done)]))
print('last', done[-1] if done else '(none)')
PY
```

## Short Summary

- duplicate queue: done
- formatting queue: active
- formatting completed: `52 / 275`
- formatting remaining: `223`
- no active DeepSeek jobs are running right now

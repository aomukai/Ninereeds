# TODO

This file is the single active unfinished-work queue for the repository.

Rules:
- Add new unfinished work here.
- When a task is completed, remove it from this file and move it to `history.md`.
- Do not leave completed tasks or long status summaries here.
- Legacy planning and status docs belong in `archive/`.

## Active queue

[ ] Write `meta/scripts/lang3c.py` modelled on `meta/scripts/lang2.py`.
    Read first: `training_data/lang/level_3c_templates.md` (prompts and output spec),
    `training_data/lang/lang_3c_verbs.txt` (input verb list, strip `[*]` markers and `#` lines),
    `meta/scripts/lang2.py` (model to follow).
    Output dir: `training_data/lang/lang_3/`
    Jobs file: `training_data/lang/lang_3_jobs.jsonl`
    Planned file: `training_data/lang/lang_3_planned.txt`
    Run plan phase, then gen phase. Same two-phase idempotent flow as lang_2.

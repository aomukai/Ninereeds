# TODO

This file is the single active unfinished-work queue for the repository.

Rules:
- Add new unfinished work here.
- When a task is completed, remove it from this file and move it to `history.md`.
- Do not leave completed tasks or long status summaries here.
- Legacy planning and status docs belong in `archive/`.

## Active queue

[ ] Batch vocabulary backfill loop
    Executor prompt:
    Read the first 50 words from training_data/phases/backfill_clean.txt.
    For each word, create one file in the correct phase directory using the exact format of existing phase 1-6 files: 4 [user]/[Ninereeds] blocks, 5 response lines per block, simple vocabulary, no pronouns, each block approaches the word from a different angle.
    After all files are created, remove those 50 words from backfill_clean.txt.
    Return a receipt: filename → word, line count, words remaining in backfill_clean.txt.
    Do not update any indexes or tracking docs until receipt is confirmed.

[ ] Rebuild training_data/dependency_graph.json incrementally, 10 files per run
    Executor prompt:
    Rebuild training_data/dependency_graph.json incrementally, 10 files per run.
    On each run:

    Read training_data/dependency_graph_progress.txt to find out which files have already been processed. If the file does not exist, start from the beginning.
    Process the next 10 unprocessed files from this order: training_data/phases/ first, then training_data/wiki/, then training_data/triplet_stories/, then training_data/reasoning/
    For phase files: identify the target word(s) introduced, extract all vocabulary used in [Ninereeds] response lines, record those as prerequisites for the target word
    For wiki/stories/reasoning files: record which phase 1–6 words each file depends on
    Merge results into training_data/dependency_graph.json (append, do not overwrite existing nodes)
    Append the 10 processed filenames to training_data/dependency_graph_progress.txt

    Receipt: files processed this run, total nodes so far, total edges so far, files remaining.
    When dependency_graph_progress.txt contains every file: report total nodes, total edges, deepest dependency chain, any circular dependencies. Graph is complete.
    Do not touch any other file.

# Roadmap

## Vocabulary governance pass

Once phase files are confirmed final after the damage check:

1. Extract all content words (nouns, verbs, adj, adv) from the full corpus — phases, wiki, stories, reasoning, philosophy. Record word + every filename it appears in.
2. Check against `wordlist.txt`. Flag anything not explicitly taught in phases 1–6.
3. Filter flagged words by reading level / syllable count (target: grade 3–4 ceiling). This eliminates rare/adult vocab without micromanaging every synonym.
4. Human review: for each flagged word, decide keep or remove. If remove, the preferred replacement comes from the allowed-words palette (wordlist.txt + approved additions).
5. Produce a rewrite list: files to fix + allowed-words palette. DeepSeek rewrites in context — no mechanical search+replace.
6. Re-scan any new files created in the process. Repeat until clean.
7. Coverage check: for words kept as deliberate exceptions, decide whether they need a phase entry, wiki article, or story — or whether adjacent material already covers the concept well enough.

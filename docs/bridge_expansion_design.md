# Grammar Bridge Expansion — Design Document

Current bridge (`training_data/01_language/bridge/`, 100 files × 4 langs):
- Covers dative double-object verbs only: gibt, zeigt, bringt, schickt, leiht, hilft, antwortet, erzählt
- Always canonical word order
- Files 51–70 add genitive possession
- Missing: prepositions, pronouns, NOM/ACC isolation, word-order variation

---

## Why bridge-before-grammar works

The C14 comparison experiment (variants A and B, June 2026) confirmed:
- Bridge before grammar: grammar cluster μ = 0.243 at E2, 0.201 at E3
- Bridge after grammar: grammar cluster μ = 0.209 at E2 (lower)

Hebbian learning explanation: the bridge pre-loads surface-form patterns (dem Jungen, den Ball,
des Hundes) as raw co-occurrence signals. When the grammar curriculum arrives, it reinforces and
structures patterns that already exist. Bridge-after arrives when the model has already committed
to its own surface-form hypotheses — correct or not — and can only act as a weak corrective.

Same principle applies to arithmetic: drill files go BEFORE the reasoning corpus, not after.

---

## Expansion 1 — Always-dative prepositions (~80 files)

German prepositions that are unconditionally dative — no static/movement judgement required.
These build the dative retrieval pathway without semantic reasoning load.
The training.md diagnostic identified this as the specific gap.

Prepositions to cover:
  mit (with), bei (at/with), von (from/of), aus (from/out of),
  nach (after/to), zu (to/toward), seit (since), gegenüber (opposite)

Format: same annotated bracket structure as existing bridge.

Example file (mit):
  (Emma) geht [mit dem Mann].  ← [] = dative
  (Emma) walks [with the man].
  (エマ)が[男の人と]歩く。    ← と = comitative, dative-equivalent
  (Emma)和[那個男人]走。

  [Mit wem / With whom / 誰と / 和誰] does Emma walk?
  [with the man]. / [mit dem Mann]. / [男の人と]. / [和那個男人].

  Emma walks with the man.
  Emma geht mit dem Mann.
  エマが男の人と歩く。
  Emma和那個男人走。

Cover each preposition with ~10 files varying the noun (Mann, Frau, Kind, Arzt, etc.).

---

## Expansion 2 — Dative pronouns (~30 files)

Pronoun case forms that signal dative explicitly.
DE: ihm, ihr, ihnen, mir, dir, uns, euch
JP: に + pronoun equivalents (彼に、彼女に、彼らに)
EN: him, her, them (objective case)

Example:
  Emma gibt [ihm] den Ball.     ← ihm = dative pronoun (him in dative)
  Emma gives [him] the ball.
  エマが[彼に]ボールをあげる。
  Emma把球給[他]。

These are distinct from noun-phrase datives because the article inflection disappears —
the pronoun form carries the entire case signal.

---

## Expansion 3 — NOM/ACC isolation (~20 files)

The current bridge always presents all three cases together. This file set drills the
nominative/accusative boundary in isolation, without the dative present.

Accusative-only verbs (no dative recipient): sehen, kennen, haben, lieben, hören, suchen, finden

Example:
  (Der Mann) sieht {den Jungen}.   ← () = NOM, {} = ACC
  (The man) sees {the boy}.
  (男の人)が{男の子}を見る。
  (那個男人)看{男孩}。

  (Wer / Who / 誰が / 谁) sees the boy? — (the man) / (der Mann)
  {Wen / Whom / 誰を / 谁} does the man see? — {the boy} / {den Jungen}

Key contrast to teach: der Junge (NOM) vs den Jungen (ACC) — same noun, different role.

---

## Expansion 4 — Case-invariance drills (~75 files) ← CORE NEW IDEA

**The pedagogical goal:** teach that case markers encode grammatical role independently
of word order. A model that has only seen canonical order can learn "dative = second slot"
rather than "dative = dem marker". Scrambled word order breaks that shortcut.

### The core sentence

"Der Mann gibt dem Jungen den Ball des Hundes."

All four cases present:
  NOM (subject):          Der Mann    — der
  DAT (indirect object):  dem Jungen  — dem
  ACC (direct object):    den Ball    — den
  GEN (possession):       des Hundes  — des

### Word order permutations (German V2 constraint: verb stays position 2)

1. Canonical:      Der Mann     gibt dem Jungen  den Ball des Hundes.
2. DAT fronted:    Dem Jungen   gibt der Mann    den Ball des Hundes.
3. ACC fronted:    Den Ball     gibt der Mann    dem Jungen des Hundes.
4. GEN fronted:    Des Hundes   Ball gibt der Mann   dem Jungen.  (complex, optional)

Each permutation Q&A drills all four roles:
  Who gives? → always the NOM-marked one (der Mann / der Mann / der Mann)
  To whom?   → always the DAT-marked one (dem Jungen / dem Jungen / dem Jungen)
  What?      → always the ACC-marked one (den Ball / den Ball / den Ball)
  Whose?     → always the GEN-marked one (des Hundes / des Hundes / des Hundes)

### Cross-linguistic expression of the same relationship

The same four-case sentence expressed differently in each language — the RELATIONSHIP
is the invariant, the surface form is language-specific:

**German** — inflected articles carry case:
  Der Mann gibt dem Jungen den Ball des Hundes.
  Dem Jungen gibt der Mann den Ball des Hundes.  ← DAT fronted, der Mann still NOM

**Japanese** — postpositional particles carry case:
  男の人が男の子に犬のボールをあげる。       ← canonical (NOM-DAT-GEN-ACC-V)
  男の子に、男の人が犬のボールをあげる。     ← DAT emphatic fronting
  犬のボールを、男の人が男の子にあげる。     ← ACC emphatic fronting
  が (NOM), に (DAT), を (ACC), の (GEN) — particles detached from their typical slot
  but STILL carrying the full relationship information. This is the clearest signal:
  position is irrelevant, the particle is the only carrier.

**Chinese** — word order + 的 for genitive:
  那個男人把球給男孩了。  (canonical: subject-verb-object)
  把 construction marks accusative; 的 marks genitive possession
  Chinese contrast is pedagogically useful: NO overt case on NOM/DAT, word order required.
  Showing ZH alongside DE/JP makes the case system visible by contrast.

**English** — residual case marking, mostly hidden:
  Canonical: The man gives the boy the dog's ball.  (case hidden in word order + 's)
  Cleft/emphatic: It is the boy WHOM the man gives the ball.  (whom = overt dative/accusative)
  Relative: The boy to WHOM the man gives the ball...  (whom forced by preposition)
  Possessive: The dog WHOSE ball the man gives the boy.  (whose = overt genitive)

  The English pronoun paradigm is the full case system in miniature:
    he / him / his     (NOM / ACC-DAT / GEN)
    she / her / her    (NOM / ACC-DAT / GEN)
    they / them / their (NOM / ACC-DAT / GEN)

  Cleft construction forces the marked form into the open. "It is the boy WHOM the man
  gives the ball" — whom cannot be swapped for who here. This is overt case marking,
  just usually avoided in informal speech. Including the cleft form in the drill makes
  the English case system as visible as the German/Japanese ones.

### Q&A drilling per permutation — all four languages

For each word-order variant, drill all four case roles in all four languages:

  Who gives?           → The man. / Der Mann. / 男の人が. / 那個男人.
  To whom does he give? → The boy. / Dem Jungen. / 男の子に. / 男孩.
  What does he give?   → The ball. / Den Ball. / ボールを. / 球.
  Whose ball?          → The dog's. / Des Hundes. / 犬の. / 犬的.

  [In scrambled-order versions, answers are identical — the point of the drill.]

### Scale

5 verbs × 5 noun combinations × 3 permutations = ~75 files
Verbs: gibt (gives), zeigt (shows), bringt (brings), schickt (sends), leiht (lends)
Noun combos: vary subject, recipient, object, possessor across files

---

## DeepSeek generation notes

All four expansions use the same annotated bracket format as the current bridge:
  () = nominative/subject
  [] = dative/indirect object
  {} = accusative/direct object
  <> = genitive/possessive

Key instruction for case-invariance files: generate the CLEFT/EMPHATIC form in English
(not just canonical "The man gives the boy the ball"), and the EMPHATIC FRONTED form in
Japanese (not just canonical SOV order). These are the forms where case marking is most
visible.

Chinese note: 把-construction for accusative, 的 for genitive, topic-comment for
fronting ("至於那個男孩，那個男人把犬的球給了他") — may need manual verification.

Output directory: `training_data/01_language/bridge/` continuing from file 101.
Naming: `101_case_inv_gibt_nom1.md`, `102_case_inv_gibt_dat1.md`, etc.

---

## Summary of additions

| Set | Files (EN only) | Files × 4 langs | What it teaches |
|---|---|---|---|
| Always-dative prepositions | ~80 | ~320 | Unconditional dative; builds retrieval pathway |
| Dative pronouns | ~30 | ~120 | Pronoun case forms; no article to rely on |
| NOM/ACC isolation | ~20 | ~80 | der vs den boundary without DAT present |
| Case-invariance drills | ~75 | ~300 | Case = role, not position; cross-linguistic |
| **Total** | **~205** | **~820** | |

Current bridge: 100 files × 4 langs = 400 files.
After expansion: ~305 files × 4 langs = ~1,220 files.

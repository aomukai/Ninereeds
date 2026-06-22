# Mommy Says — Convergence Log Corpus

**Status:** spec / planned  
**Target directory:** `training_data/convergence/`  
**Depends on:** a fully pretrained Ninereeds checkpoint  

---

## Purpose

Standard corpus files show Ninereeds always answering correctly. Convergence logs
introduce a different structural role: Ninereeds starts wrong, receives corrections,
and converges toward the right answer within the same session. This teaches several
things simultaneously:

- **Identity anchoring.** `[Ninereeds]` is the entity that gets corrected and
  converges — not just the entity that outputs. Ninereeds learns it is its own replies.
- **Echo pressure mitigation.** The corpus gains a `[user] corrects → [Ninereeds]
  incorporates` pattern that the standard files lack entirely.
- **Trajectory structure.** The log encodes wrong → less wrong → right → confirmed →
  next topic. Even surface exposure to this arc may teach Ninereeds that output can
  improve in response to input.
- **Topic boundary signaling.** Affirmation + pivot on the same `[user]` turn teaches
  Ninereeds that closure and transition are a single move.

---

## File Format

Single continuous `[user]`/`[Ninereeds]` exchange. No blank line separators between
turns (unlike phase files). One turn per line.

```
[user] What is a bird?
[Ninereeds] A bird runs in the sky.
[user] A bird flies in the sky.
[Ninereeds] A bird flies in the sky.
[user] Yes. A bird flies in the sky. What does a dog look like?
[Ninereeds] A dog has four legs.
[user] Right. A dog has four legs. What color is a dog?
[Ninereeds] A dog is brown.
[user] Exactly. What is a fish?
[Ninereeds] A fish lives in the water.
[user] Good. A fish lives in the water.
```

---

## Rules

### Correction turns

- A correction `[user]` turn is a statement, not a question: `A bird flies in the sky.`
- It restates the correct form without preamble.
- Keep corrections short — one sentence, one correction per turn.
- Do not use negation in corrections: not `A bird does not run`, just `A bird flies`.

### Affirmation vocabulary

Vary affirmations across the corpus. Do not rely on a single token.

Allowed: `Yes.` `Right.` `Correct.` `Exactly.` `Good.` `That's right.` `You got it.`

Affirmations may be:
- Fused with the next question on the same turn: `Yes. What does a dog look like?`
- Fused with a restatement + question: `Right. A bird flies in the sky. What does a fish do?`
- Standalone when closing the final topic in a file: `Good. A fish lives in the water.`

Do not use the same affirmation twice in a row in the same file.

### Convergence arc

- Ninereeds **may get the answer right on the first try.** This is important — the
  corpus must not teach that the first answer is always wrong.
- Aim for roughly: 30% first-try correct, 50% one correction needed, 20% two corrections.
- Maximum two corrections per concept before moving on. Do not let a single concept
  loop more than twice without resolution.
- After convergence, always affirm before pivoting to the next concept.

### Topic transitions

- Transitions happen on a `[user]` turn: affirmation + new question, or affirmation +
  restatement + new question.
- Topics within a file stay within one cluster (see clusters below). Do not mix animals
  and food in the same file.

### File length

- Target: 40–80 turns per file (20–40 `[user]`/`[Ninereeds]` pairs).
- Too short: not enough arc to be useful. Too long: corpus weight imbalance.
- Each file should cover 5–10 distinct concepts from its cluster.

---

## Clusters

Pick one cluster per file. Start with clusters that overlap with existing phase/lang
vocabulary to maximise reinforcement.

Suggested starting clusters:

| Cluster | Example concepts |
|---|---|
| animals | bird, dog, fish, cat, horse, bee, spider |
| food | apple, bread, soup, egg, rice, cake |
| body | hand, eye, foot, tooth, nose, ear |
| home objects | cup, chair, door, key, window, lamp |
| nature | tree, river, cloud, stone, flower, wind |
| actions | run, eat, sleep, give, carry, wash |
| spatial | above, below, inside, next to, between |
| social | greeting, asking, thanking, helping |

---

## Generation workflow

These logs should be generated from a **live pretrained Ninereeds checkpoint**, not
written by DeepSeek from scratch. The value is in the real error patterns.

Workflow:

1. Load a checkpoint (post-run, any epoch with stable output).
2. Feed `[user] What is a bird?` and record the reply.
3. If correct: affirm and move to next concept.
4. If wrong: issue one correction turn, re-query, record reply.
5. If still wrong after two corrections: affirm partial progress, move on anyway.
6. Continue until the session reaches target length.
7. Save the raw log.
8. Review: logs where Ninereeds never converges are still useful — archive them in
   `training/logs/convergence_sessions/` for analysis rather than discarding.
9. Clean logs (where convergence happens) go to `training_data/convergence/`.

Generation can be scripted once the checkpoint is stable enough to produce structured
output. A simple harness that:
- feeds the prompt
- reads the reply
- optionally feeds a correction if the reply doesn't match a reference answer
- loops until session length is reached

would remove the manual step entirely.

---

## Corpus weight

These files will be few and short relative to the full corpus. That is intentional.
They are a drop in the ocean — the goal is structural exposure, not volume.

Do not generate more than ~50 files in the first pass. Evaluate on probes before
expanding.

---

## On falsifying the arc

Convergence logs that come from live sessions may show Ninereeds getting something
wrong many times in a row before converging — or never converging at all. These raw
logs are **not suitable training material as-is.**

A log showing 20+ consecutive wrong answers before convergence would train the signal
"produce wrong output repeatedly, then eventually be right." At 150M with no fuzziness
buffer, that is not a recoverable pattern. Ninereeds is not a human who can cargo-cult
behavior until the underlying structure clicks — it has no biological noise to paper
over prolonged failure arcs.

Therefore: **corpus logs are intentionally edited to show clean arcs.** This is not
dishonesty — it is curriculum design. The log is training material, not a transcript.

Editing rules:

- Collapse multiple failed attempts into at most two corrections before convergence.
- Remove turns where Ninereeds produces structurally broken output (not just wrong
  content — genuinely malformed turns).
- Keep at least one wrong answer per concept where one occurred — zero corrections
  would make the arc invisible.
- Do not invent wrong answers for concepts Ninereeds got right first try.

Raw session logs (unedited) go to `training/logs/convergence_sessions/` regardless of
quality. They are useful for understanding error patterns even when unusable as corpus.

---

## Interaction with bridge course

Bridge files and convergence logs serve different purposes:

- Bridge files fire the same structural frame repeatedly → case/particle anchoring.
- Convergence logs fire the correction arc → identity and trajectory.

They do not conflict. Bridge files can appear between domain transitions as planned;
convergence logs live in their own directory and are sequenced after the primary
concept layers in the corpus order.

---

## Open questions

- Should the correction turn always be a bare restatement, or can it include mild
  scaffolding? e.g. `No. A bird flies, not runs. A bird flies in the sky.` — the
  explicit contrast might help but could also introduce negation pressure.
- Should `[user]` ever give a wrong correction (to test robustness)? Probably not in
  the first pass — keep the teacher signal clean.
- Does the topic-boundary affirmation need a consistent form to be learnable, or is
  variation better? Currently specced as varied — revisit after run_13 eval.

---

## Status log

| Date | Event |
|---|---|
| 2026-05-27 | Spec written. Pending pretrained checkpoint. |

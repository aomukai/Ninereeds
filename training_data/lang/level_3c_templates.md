# Level 3c — Reflexive Verbs and Benefactive Flow

## What this level teaches

Level 3c teaches how languages encode **argument flow** — the relationship between the agent and the recipient of an action, and whether the agent acts on themselves or on behalf of someone else.

Three patterns are covered:

| Pattern | English | German | Japanese | Mandarin |
|---|---|---|---|---|
| Reflexive | washes (himself) | wäscht sich | 体を洗う (object implied) | 洗自己 |
| Gives benefit outward | does X for someone | tut X für jemanden / dative | ～てあげる | 给…做X |
| Receives benefit / has done for them | has X done for them | lässt X machen | ～てもらう / ～てくれる | 让…做X |

The cross-linguistic lesson: English largely ignores this distinction. German encodes it via case (dative) and reflexive pronouns (sich). Japanese grammaticalises it in the auxiliary verb after て — the auxiliary itself encodes who the benefit flows toward. Mandarin uses 给 (for) and 让 (let/have) as explicit role-markers.

---

## How to generate 3c files

3c uses the same plan → gen flow as lang_2.

**Scripts to model on:** `meta/scripts/lang2.py` and `meta/scripts/lang_gen.py`
**Output directory:** `training_data/lang/lang_3/`
**Jobs file:** `training_data/lang/lang_3_jobs.jsonl`
**Planned file:** `training_data/lang/lang_3_planned.txt`

Write `meta/scripts/lang3c.py` modelled on `lang2.py`. The two phases are identical in structure; only the prompts change.

---

## Phase 1 — Plan

For each verb in the 3c verb list, the plan phase asks DeepSeek to identify which of the three patterns apply and what the cross-linguistic contrast is.

### 3c verb list

Seed list — extend as needed. Prioritise common verbs.

**Reflexive verbs (German sich-verbs):**
wash, dress, shave, remember, feel, enjoy, sit (down), introduce (oneself), change, move, calm (down), prepare, imagine, worry, decide, meet (each other), hurt (oneself), look at (oneself)

**Benefactive verbs (てあげる / てくれる / てもらう frame):**
teach, carry, buy, cook, write, make, fix, help, bring, send, read (aloud), explain, show, cut (hair), clean, translate, photograph, wrap

These lists overlap intentionally. Many verbs belong to both patterns.

### Plan prompt (adapt for lang3c.py)

For each verb, identify which of these frames apply:

1. **reflexive** — the agent acts on themselves. German uses sich. Japanese typically omits the object or makes it implicit. English may use "oneself" or just drops it.
2. **agentive_benefactive** — the agent does X for someone else's benefit. German uses dative or für + NP. Japanese: てあげる. Mandarin: 给 + recipient + verb.
3. **receptive_benefactive** — the agent has something done for them, or someone does X for the agent. German: dative or lassen + infinitive. Japanese: てもらう (agent receives benefit) or てくれる (someone gives benefit to agent). Mandarin: 让 + doer + verb.

Return one job per applicable frame. A verb may yield 1–3 jobs.

### Jobs file format

Same as lang_2_jobs.jsonl:
```json
{"word": "wash", "frame_id": "wash_reflexive", "pattern": "reflexive", "desc": "...", "note": "..."}
{"word": "wash", "frame_id": "wash_benefactive", "pattern": "agentive_benefactive", "desc": "...", "note": "..."}
```

---

## Phase 2 — Gen

For each job, generate a file with 3–5 sentence groups in the standard 4-line EN/DE/JP/ZH format.

### Output format

Identical to lang_2: four lines per group, blank line between groups, no headers or labels inside the file.

```
The child washed himself.
Das Kind hat sich gewaschen.
子供は体を洗った。
孩子洗了自己。

He is washing himself.
Er wäscht sich.
体を洗っている。
他在洗自己。

She will wash herself.
Sie wird sich waschen.
体を洗うだろう。
她会洗自己。
```

### Pattern-specific generation rules

**reflexive:**
- German: sich in accusative position for most verbs (sich waschen, sich erinnern); dative sich for body-part verbs (sich die Hände waschen — "wash one's hands").
- Japanese: typically drops the reflexive object when it is the agent's own body; 自分 only when contrast or emphasis is needed.
- Mandarin: 自己 (zìjǐ) for reflexive objects; can often drop if clear from context.
- English: "himself / herself / themselves" for emphasis; often just uses the verb without object.

**agentive_benefactive (doing X for someone):**
- German: dative NP for recipient, or für + accusative.
- Japanese: [VERB て]あげる — てあげる encodes that the agent gives the benefit outward. Never use あげる when the recipient is the first person.
- Mandarin: 给 + recipient before the verb (给她做饭 — cook for her).
- English: "[VERB] for [recipient]" — no grammatical marking on the verb itself.

**receptive_benefactive (having X done / someone does X for agent):**
- German: lassen + infinitive for "have done"; dative of interest for softer beneficiary marking.
- Japanese:
  - てもらう — agent receives the benefit (I had her fix it: 彼女に直してもらった)
  - てくれる — someone does X for the agent's benefit (she fixed it for me: 直してくれた)
- Mandarin: 让 + doer + verb (让她做 — have/let her do it).
- English: "have [someone] do X" or "[someone] does X for me" — again, no grammatical marking.

---

## Cross-linguistic summary to keep in mind during generation

English is structurally flat for all three patterns. The agent–recipient relationship is only visible through word order and optional "for/by" phrases. Nothing in the verb changes.

German marks reflexivity with sich (a pronoun that agrees with the subject) and marks beneficiaries with the dative case.

Japanese marks beneficiary direction in the auxiliary verb after て. This is perhaps the richest grammaticalisation in the corpus: あげる/くれる/もらう each encode a different direction and social relationship. A single event ("she fixed my bike") is expressed differently depending on who the narrator is and what the social relationship implies.

Mandarin uses explicit lexical role-markers (给, 让, 自己) in fixed positions. Roles are visible and compositional — consistent with Mandarin's general analytic pattern.

---

## File naming

`wash_reflexive.md`, `wash_benefactive.md`, `teach_agentive.md`, `teach_receptive.md`

Use the pattern name as a suffix so files are self-describing.

---

## Global rules still apply

All rules from the global section (naturalise, pronoun drop, aspect vs tense, register) apply here without exception.

Additionally:
- Japanese plain form. てあげた not てあげました.
- Vary subjects across groups: Tom, Kate, the child, the teacher, she, he, they.
- Do not explain grammar inside the generated files.
- Use allowlist words for content nouns and verbs.

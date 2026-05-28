**`bridge_course_spec.md`**

**Purpose:** Defines the annotated parallel format for the Ninereeds bridge course corpus. This format is a teaching scaffold, not the target output register. Bridge files are a minority of total training data.

**Bracket semantics — semantic roles:**

| Bracket | Role | German case | Japanese |
|---|---|---|---|
| `()` | actor / subject | nominative | が |
| `[]` | anchor — location, recipient, source | dative | に／から／で |
| `{}` | target — object, endpoint | accusative | を／に／へ |
| `**` | action | verb | verb (end position) |
| `<>` | ownership / source relation | genitive / von | の |

**File structure — one paradigm block:**

Annotated four-language sentence first. Then question-answer pairs, one per bracket type present. Then the plain sentence in all four languages, no annotation. The plain sentence is mandatory — it is the training wheels removed.

**Language line order:** EN / DE / JP / ZH throughout. Never vary the order within a file.

**Nesting:** `<>` may nest inside `{}` or `[]` to show genitive modification. Bracket of the outer phrase wraps the whole constituent including the nested genitive. Example: `{den Ball <des Jungen>}`.

**Verb position:** `**verb**` marker follows the word order of each language. In Japanese it lands at the end. In German it may be second position or final in subordinate clauses. The marker travels with the verb, not with a fixed position.

**Contractions:** Early files prefer full forms. `in dem` before `im`. Introduce contractions as explicitly equivalent: `im (in dem)` on first occurrence per file.

**Scaffold removal sequence for pedagogical use:**
1. Remove `<>` first — genitive is possession, low ambiguity
2. Remove `{}` — accusative has English analogue
3. Remove `()` — nominative is trivial
4. Remove `**` — verbs are self-evident
5. Remove `[]` last — dative has no English equivalent, highest failure risk

**Scale:** Target 100 bridge files total. Do not exceed 10% of total corpus size.

**Bleed risk:** Bridge files must use distinct question framing ("show the parts", "label the roles") so Ninereeds learns two separate retrieval frames — annotated analysis vs. plain production. Never use identical question phrasing across bridge and plain corpus files.

(The man) *gave* [the dog] {the <boy's> ball}.
(Der Mann) *gab* [dem Hund] {den Ball <des Jungen>}.
(男の人が)[犬に]{<男の子の>ボールを}*あげた*。
(男人)*给了*[狗]{<男孩的>球}。
(Wer / Who / 誰が / 谁) gave the dog the boy's ball?
(The man). / (Der Mann). / (男の人が). / (男人).
[Wem / To whom / 誰に / 给谁] did the man give the boy's ball?
[The dog]. / [Dem Hund]. / [犬に]. / [狗].
{Was / What / 何を / 什么} did the man give the dog?
{The boy's ball}. / {Den Ball des Jungen}. / {男の子のボールを}. / {男孩的球}.
<Wessen / Whose / 誰の / 谁的> ball did the man give the dog?
<The boy's>. / <Des Jungen>. / <男の子の>. / <男孩的>.
The man gave the dog the boy's ball.
Der Mann gab dem Hund den Ball des Jungen.
男の人が犬に男の子のボールを あげた。
男人给了狗男孩的球。

# Seminar logic flow

The document to rehearse from. The spec's §12 is a *schedule*; this is the
*argument*. If a link in §3 does not follow from the one before it, the seminar
has a hole no slide will patch.

**Audience:** technical people who *use* AI but do not specialise in it. They read
code and run production. "Cross-encoder" and "RRF fusion" are not yet vocabulary.

**"Hands-on" means implementable afterwards, not typing in the room.** Nobody
codes during the session. Success is that a colleague goes back to their team and
builds a RAG that fits their problem — alone or with help. Therefore every block
ends by naming **the artifact in the repo that produced the fix**, and the repo
plus adoption checklist are load-bearing deliverables, not appendices.

---

## 1. The through-line

> Your knowledge base could not find the complicated cases. Retrieval fixes
> findability — but which retrieval, and how would you know it worked? You measure,
> one step at a time, and most of what you would have added on faith does not help.

Everything in the seminar either sets that up or pays it off.

---

## 2. Assumptions register

A review caught an earlier draft asserting something no stakeholder had said. The
project's own principle is *never guess*, so every claim the talk makes **about
the audience's organisation** is listed here with its status.

**Nothing marked ASSUMED or HYPOTHESIS may be stated as fact on stage.**

| Claim | Status |
|---|---|
| A knowledge base was delivered to NOC | **Verified** |
| NOC **does** find familiar cases; the complicated ones are what it cannot find | **Verified** |
| A small share of questions have a guide the operator does not recognise | **Verified** |
| The bulk is hard analysis needing deep production knowledge | **Verified** |
| Real docs exist in EN / VI / JA versions | **Verified** |
| Versions are updated together, per company procedure | **Verified** |
| Answers go to NOC **in Vietnamese** | **Verified** |
| "Answer" means giving the playbook and the step, not a bare conclusion | **Verified** |
| Cause: cases new to NOC, deep production knowledge required, NOC covers multiple products, frequent new staff, experienced staff leaving | **HYPOTHESIS** — the author's, not stated by colleagues |
| ~~Writing more documentation was already tried and failed~~ | **REMOVED — invented** |
| The audience arrives sceptical of AI pitches | ASSUMED — a planning heuristic; never asserted aloud |
| Colleagues have this failure in their own KB today | ASSUMED — phrase as *"worth checking"*, never as fact |

**The hypothesis is testable, and should be tested before the seminar.** Escalation
rate against operator tenure; the share of escalations whose subject already
appears in an older resolved ticket. Running that check converts a hypothesis into
a finding — and stating *"we measured this"* is worth far more than *"I think"*.

---

## 3. The argument chain

| # | Claim | Earned by |
|---|---|---|
| 1 | This problem is real and it is yours | **Real escalations from your colleagues** |
| 2 | NOC handles familiar cases; complicated ones cannot be found | Their own words |
| 3 | Knowledge must accumulate in the system, not in people | Hypothesis, labelled as such |
| 4 | There are several tools, not one | Long context, CAG, fine-tuning, RAG, agentic search |
| 5 | Some beat RAG in specific cases | **Live**: grep beats RAG on code |
| 6 | For *this* case RAG is right — here is how the others were ruled out | CAG dies on shared model hosting; long context dies on cost-per-query; fine-tuning changes behaviour, not knowledge |
| 7 | Naive RAG fails in specific, nameable ways | Eight concept→failure→fix blocks |
| 8 | Each failure has a name you can search for | Vocabulary handed over as it appears |
| 9 | **Not every fix helps. Measure.** | The reranker is added, measured, removed |
| 10 | Found → answer with playbook and step. Not found → escalate **with evidence** | Block 8 |
| 11 | Escalation is most of the volume, and is not failure | Evidence packet; time-to-context |
| 12 | Here is how to choose for *your* problem | Decision matrix + question-shape guide |
| 13 | Here is where the buzzwords fit | The layer map |
| 14 | Do not rebuild the failure you started with | F8.5 callback |

**Link 9 is the hinge.** Everything before it builds a system; everything after it
is about judgment. If one thing survives the week, it should be that one.

---

## 4. The five acts

### Act I — "That's my situation" (0:00–0:10)
*Enters expecting a pitch. Leaves recognising their own problem.*

Three **real escalations from your colleagues**, lightly redacted — ideally ones
where a playbook already existed. No technology on screen.

Then the three tiers, including the line that costs nothing and buys a lot:
**the system adds no value to the cases NOC already handles.**

Then the labelled hypothesis: people rotate across products, staff join and leave,
so knowledge cannot accumulate in people — it has to accumulate in the system.

### Act II — Just enough foundation (0:10–0:25)
*Enters willing to listen. Leaves trusting the speaker's judgment.*

Deliberately narrow. Only what Act III needs:

- **What RAG does** — one diagram: find relevant text, put it in the prompt,
  answer from it. No mathematics, no vector geometry.
- **Two phases** — ingest is paid once and **fails silently**; query is paid every
  time and fails visibly. Teams work on the visible half; the problem is usually in
  the other one. This single idea pays off in the very first demo block.
- **Several tools, not one** — and **how three were ruled out**. The CAG rejection
  carries the criterion that no published comparison mentions: *do you own the
  model instance, or share it?*
- **0:20–0:25 Live: grep vs RAG** — same question, each tool winning on its own
  material.

This act deliberately costs the speaker his own pitch. That is what buys the next
eighty minutes.

### Act III — Concept → failure → fix, eight times (0:25–1:20)
*Enters trusting. Leaves holding a mental map and a vocabulary.*

~5–6 minutes each: teach the idea in two minutes, watch it fail, watch the fix
land. **No idea runs past 90 seconds before something concrete appears on screen.**
Each block closes by naming the repo artifact that produced the fix.

| # | Concept taught | Failure shown | Fix | Min |
|---|---|---|---|---|
| 1 | Documents must be *parsed* before they can be found | Scanned runbook: indexed, present, **unreachable** | Parsing + OCR | 7 |
| 2 | Meaning vs exact words | Paraphrase finds nothing | Semantic search | 5 |
| 3 | **One document, three languages** | Three translations flood top-k; the best source is English but the reader needs Vietnamese | `doc_id` grouping + cross-lingual retrieval + **answer in Vietnamese** | 8 |
| 4 | …but meaning loses exact strings | `SQ-2011` returns nonsense | Hybrid search | 6 |
| 5 | Not all documents are equal | Answer from the wrong service or an older version | Metadata + routing | 5 |
| 6 | Some questions retrieval cannot answer | "Which services do **not** …" fails throughout | Question parsing; the limit | 4 |
| 7 | **Every tutorial's favourite component** | Reranker added — barely helps | **Measure it. Remove it.** | 8 |
| 8 | Found or not found | Confidently wrong on an unknown, then a real repeat incident | Grounding, refusal, **playbook+step vs escalate** | 8 |

**Block 1 is first deliberately.** Before any talk of embeddings they watch a
document that is present, indexed and completely unreachable. Frame it as *worth
checking in your own knowledge base* — never as a claim about their systems. It
earns "quality in, quality out" instead of asserting it.

**Block 3 is the most transferable.** Multi-version translated documentation exists
in most companies in the room, and nobody designs for it. Three translations eating
three of five result slots is a failure people recognise instantly once shown.

**Block 7 is the pivot**, landing at ~1:05 — the strongest moment placed at the
weakest point of the attention curve.

### Act IV — "I know what to do Monday" (1:20–1:40)
*Enters convinced the demo works. Leaves able to act on their own problem.*

- **Escalation as a product** — the evidence packet, and the admission that most
  volume is escalation rather than answers
- **Decision matrix + question-shape guide** — the take-home tables
- **Security: retrieval is an untrusted input channel.** Told as a *mechanism*, in
  plain language:

  > Hidden text in a document — white-on-white, 1pt, or in metadata — contains
  > instructions aimed at the AI. Someone asks an ordinary question. The system
  > retrieves that document, cannot distinguish "content I am reading" from
  > "instructions I follow", and obeys. It writes an image link pointing at the
  > attacker's server with the data in the URL. The chat window renders images
  > automatically, so the browser sends it. **Nobody clicked anything.**

  Then the connection: *your tickets contain text pasted from customers, vendors
  and external logs.* That is the same channel, inside the trusted boundary.

  **If it can only be name-dropped, cut it.** Be able to answer "how did the data
  actually leave?"

### Act V — Where this all sits (1:40–1:50)
*Enters equipped. Leaves oriented.*

The layer map, one slide — these are **layers around RAG, not competitors to it**:

| Layer | Unit of control | Where retrieval sits |
|---|---|---|
| Prompt engineering | One model response | RAG fills the prompt |
| Context engineering (2025) | What is in the window | RAG is the mechanism; CAG is the no-retrieval alternative — **needs a dedicated model instance** |
| Loop engineering (late 2025→) | One agent's cycle: discover → plan → execute → verify | **Agentic RAG** — the agent chooses how to retrieve |
| Graph engineering (2026→) | Many agents; stateful, **cyclic** control flow | GraphRAG is retrieval over a knowledge graph — *a different sense of "graph"* |
| Harness engineering | Everything wrapping the model | Retrieval is one harness component |

Two precise points worth making:

- Agent graphs are **cyclic**, not DAGs — loops live inside the graph, which is
  exactly what a classic DAG orchestrator forbids. Closer to a state machine.
- **"Graph" means two unrelated things**: a graph of *agents* (orchestration) and
  a graph of *knowledge* (GraphRAG). The conflation is common.

"Agent = Model + Harness" (Hashimoto, 2026); the wrapper around a *fixed* model
reportedly moves benchmark performance up to **6×** — independent support for the
thesis that architecture beats model-swapping.

Then the evolution, as failures they personally watched:

```
keyword → semantic → hybrid → +structure → agentic
```

Close on:

> **You do not need the latest generation. You need the generation that fixes your
> failure.** Most teams adopt the newest architecture to solve the oldest problem.

Then the F8.5 callback — the bot becoming another "too complicated" tool, the
failure that started the story.

### Handouts and Q&A (1:50–2:00)
Repo walkthrough, adoption checklist, failure catalog, VI/EN glossary.

---

## 5. The three credibility purchases

Planned moments of arguing against yourself. Technical audiences trust whoever
states the limits, and these are the highest-value seconds in the seminar. They
are also the first thing a nervous presenter cuts and the last thing they should.

| When | Conceded | Buys |
|---|---|---|
| 0:20 | "For code, grep beats what I'm about to show you" | The right to advocate RAG later |
| Block 7 | "We measured the reranker and removed it" | The evaluation principle, permanently |
| 1:20 | "The system adds nothing to the cases NOC already handles" | Belief in every number after it |

---

## 6. Delivery risks

| Risk | Mitigation |
|---|---|
| A block overruns and eats the next | Hard stop per block; blocks 2, 5, 6 compress to ~3 min with pre-rendered results |
| Concept explained too abstractly | The 90-second rule |
| Company model host unreachable | Prebuilt index; recorded fallback per block |
| Security segment lands as name-dropping | Rehearse the mechanism; answer "how did the data leave?" |
| Buzzword slide overwhelms | One slide, four terms maximum, single-sentence payoff |
| Vocabulary outruns the audience | Terms written on screen at first use; glossary handed out at the **start**, not the end |
| "Is RAG dead?" derail | Category error — context engineering is the discipline, RAG a technique inside it |

---

## 7. Rehearsal card

Hard checkpoints — if you are not at these marks, cut a fast block, not a
concession.

```
0:10  Act I done ....... three real escalations + three tiers
0:25  Act II done ...... grep-vs-RAG run live       [CONCESSION 1]
1:05  Block 7 starts ... the reranker experiment    [CONCESSION 2]
1:20  Act III done ..... eight blocks
      Act IV opens ..... "adds nothing to familiar cases" [CONCESSION 3]
1:40  Act IV done ...... security told as a mechanism
1:50  Act V done ....... layer map + the meta-lesson
```

**Never cut:** block 1, block 7, the three concessions, the meta-lesson.
**Cut first:** blocks 2, 5, 6 to pre-rendered results.

---

## 8. Verification — runnable before the room is

1. **Argument test** — read only the 14 claims in §3 aloud. Any link that does not
   follow from the previous one is a hole no slide fixes.
2. **Assumption audit** — every statement about the audience's organisation traces
   to §2, or is cut.
3. **Hypothesis test** — run the ticket-data check in §2. Convert it to a finding
   or drop the claim.
4. **Rejection test** — for each tool ruled out (CAG, long context, fine-tuning),
   state the killing constraint in one sentence. A rejection that cannot be defended
   in one sentence is not understood well enough to present.
5. **Timed rehearsal on the demo host** — not the 3090 (spec §5.3.3). Retime the
   blocks from measured numbers.
6. **Jargon audit** — list every term used before it is defined. For this audience
   that list must be empty.
7. **"Can they build it?" test** — give the repo and adoption checklist to one
   colleague who did *not* attend, and see how far they get unaided. This is the
   real measure of hands-on, and it can be run before the seminar.
8. **Cut test** — rehearse a 90-minute version. Any block whose removal breaks a
   link in §3 is mis-scoped.
9. **Concession check** — confirm all three survived editing.

# RAG for NOC Call Deflection — Design

**Date:** 2026-07-29
**Revised:** 2026-07-30 — v1.5, incorporating the *Document Intelligence* series
(§16). The revision changed the complexity ladder, the evaluation reporting rule,
and the position of reranking. See §5.4.
**Status:** Approved (design); failure catalog at v1.5 (see §10.10)
**Author:** phucvd

---

## 1. Context and problem

A knowledge base was already delivered to the NOC team. It failed — not because
knowledge was missing, but because it was **unfindable**. NOC cannot locate or
confirm the relevant procedure, so they escalate to the production/development
team on almost every alert.

The most expensive category of escalation is the **repeat incident**: the same
failure has occurred several times, a playbook already exists, and NOC cannot
recall or find it. The development team wants those calls rejected.

The root cause is findability, which is precisely and only what retrieval
fixes. Writing more documentation would not have helped. This is the honest
motivation for the project and the opening of the presentation.

## 2. Goals

1. **Deep understanding (private).** The author must understand every stage of a
   RAG pipeline well enough to answer hostile questions without bluffing.
2. **Actionable transfer (public).** Colleagues leave a ~2 hour session able to
   picture the concepts, choose a fitting solution for their own problem, and
   know the vocabulary to search with when stuck.
3. **Four teaching principles above all:**
   - **Start simple.** Add a component only when a measurement demands it.
   - **Never guess.** Retrieval quality is measured, not asserted.
   - **Structure before semantics.** Deterministic filtering and routing are
     cheaper and more reliable than better ranking.
   - **Evaluate per failure mode, not in aggregate.** A single headline score
     hides which failures remain.
4. **A failure catalog** as the durable take-home artifact — best practice taught
   through failure modes rather than feature tours.

## 3. Non-goals

- Production deployment, HA, or SLA design.
- Connectors to real Confluence/Jira/ServiceNow instances.
- Conversation memory, multi-turn agent planning, web chat UI development.
- Indexing source code. (Dropped deliberately; see §10.1 catalog entry F0.2 —
  code is the case where agentic search usually beats RAG.)
- Using real company documents. The corpus is authored (§6).

## 4. Audience and success criteria

**Audience:** engineering colleagues, mixed seniority, Vietnamese speakers,
familiar with production operations, sceptical of AI hype.

The session succeeds if a colleague can afterwards:

| # | Outcome | How we know |
|---|---|---|
| S1 | Decide whether their problem needs RAG at all | They can state a case where grep or long context is the better answer |
| S2 | Pick a stack tier for their problem | They can point at a row of the decision matrix (§11) and justify it |
| S3 | Diagnose a bad RAG result | They can name the failing stage and the search term for the fix |
| S4 | Refuse to trust an unmeasured claim | They ask "what's the baseline?" when someone demos a RAG system |
| S5 | Reproduce the demo | `docker compose up` on a modest laptop works |

**System-level success criterion (demo):** deflection rate on the gold question
set, subject to a hard constraint on false deflection (§7.3).

## 5. Architecture

### 5.1 Two tracks

| Track | Audience | Content | Share of effort |
|---|---|---|---|
| **A — Learning** | The author only | From-scratch notebooks: chunking, embeddings, cosine search, BM25, RRF fusion, reranking, scoring. No frameworks. | ~60% |
| **B — Demo** | Colleagues | Config-driven stack, one `docker compose up`, minimal code | ~40% |

Track A is the source of authority; roughly 10% of it appears on screen.
Track B is what colleagues clone.

### 5.2 Demo architecture

The anchor is **our own retrieval service**, not a platform. Platforms are
discussed in the decision matrix, not installed as infrastructure.

```
NOC operator ──> Open WebUI      ─┐
AI agent     ──> MCP client      ─┼──> retrieval service (~200 LOC)
colleague app ──> REST           ─┘            │
Flowise (no-code path) ──────────┘             │  strategy swapped live
                                               │
                     L1 bm25 │ L2 dense │ L3 hybrid │ L4 +rerank │ L5 +metadata
                                               │
                                    Qdrant + BGE-M3 (VI/EN)
```

**Key design decision — the service implements two standard contracts:**

1. `POST /v1/chat/completions` — the OpenAI API shape. Any existing client
   (Open WebUI, LibreChat, Cursor, colleagues' own apps) connects with zero
   integration code.
2. An **MCP server** wrapping the same retrieval core, so agent clients
   (Claude Desktop, Cursor) can consume the knowledge base directly.

This is the central architectural lesson for the audience: *retrieval is a
replaceable service; the agent is a client.* Speaking two standard protocols
covers every consumer they will realistically have.

A third contract, `POST /retrieval` (Dify's External Knowledge API shape), is
implemented as a thin alias so the tier-1 platform path can be demonstrated
without installing Dify.

### 5.3 Component budget (target host: WSL2, 8 GB)

| Component | RAM |
|---|---|
| Retrieval service + BGE-M3 embeddings | ~2.5 GB |
| Qdrant | ~0.5 GB |
| Open WebUI | ~0.5 GB |
| Flowise | ~1.0 GB |
| **Total** | **~4.5 GB** |

The **generation LLM is a cloud API**, not local — there is no RAM for Ollama
on this host. Embeddings remain local, which preserves the "documents never
leave the machine" property where it actually matters. This constraint is
itself presented as a teaching point: it is the realistic constraint most
colleagues face.

**Rejected:** RAGFlow (16 GB minimum, x86_64 only — exceeds the host) and Dify
(4–8 GB, 6–8 containers — heavy for the value it adds here). Both appear in the
decision matrix as graduation targets.

### 5.4 Adopted architectural principles

Taken from the *Document Intelligence* series (§16), whose empirical results
contradicted the default pipeline this spec originally assumed.

| Principle | Consequence for this system |
|---|---|
| **Structure-first retrieval** — filter and route deterministically before embedding similarity | Classify the alert (service, severity, environment) and narrow the corpus *before* semantic search. In that series, classify-before-retrieve reduced a 200,000-document corpus to ~800 |
| **Deterministic dispatchers over autonomous agents** | A question parser routes by query shape: error codes to exact lookup, "what changed recently" to a recency sort, counting questions to a structured query. No agent decides this at runtime |
| **Domain vocabulary is a central asset** | A curated map of internal acronyms and Vietnamese↔English term pairs, maintained by the dev team. Cheaper and more reliable than hoping an embedding model absorbed the company's jargon |
| **Rerankers are a fallback, not a foundation** | Reranking moves to the *end* of the ladder and is expected to fail (§9.2) |
| **Relational data at every junction, never raw strings** | Pipeline stages exchange structured records — chunk id, source, section path, score, timestamp, service — so any stage's contribution is inspectable |
| **RAG is search plus generation, not machine learning** | Nothing is trained. Improvements come from architecture and vocabulary, not fitting |
| **The corpus is controlled and the expert is in the loop** | The system *amplifies* the dev team's knowledge (playbooks, vocabulary, routing rules) rather than replacing it |

The last point reframes the project honestly: this is not an AI that learns
operations. It is a findability layer over knowledge the team already has —
which is exactly the failure identified in §1.

## 6. Corpus design

An authored corpus for a fictional order/payment processing service.
Authored rather than anonymized because (a) real documents cannot ship in a
repo colleagues clone, and (b) authoring is what makes a **gold answer key**
possible, without which nothing can be measured.

**Volume:** ~75 documents.

| Set | Count | Character |
|---|---|---|
| Runbooks / playbooks | ~15 | Vietnamese prose, English technical terms |
| Architecture & config reference | ~10 | Fully English, AI-generated register |
| Past incidents / tickets | ~50 | Mixed VI/EN; fields: symptom, service, severity, date, root cause, resolution, resolved_by |

**Language mix is deliberate and realistic:** Vietnamese runbooks containing
English technical terms, some fully-English AI-generated pages, inconsistent
formatting across authors.

### 6.1 Planted traps

Every trap maps to exactly one teaching moment. This is the core of the
corpus design — volume is not the point.

| Trap | Teaching moment |
|---|---|
| Vietnamese question, English-only runbook | Multilingual embeddings; grep cannot cross this gap |
| Error code `ORD-5021` appears verbatim, semantically meaningless | Hybrid / BM25 — embeddings lose here |
| Two runbooks contradict; one is ~2 years stale | Metadata filtering and recency |
| Two services throw near-identical errors | Metadata scoping by service |
| Correct document exists but ranks ~7th | Reranking |
| Question with no answer anywhere in the corpus | INSUFFICIENT verdict — refuse to guess |
| Repeat incident with an existing playbook | SELF_SERVE verdict — the deflection case |
| P1-severity incident that also has a playbook | Severity gate must override deflection |
| Acronym used only in tickets, never defined in docs | Domain vocabulary map — not an embedding problem |
| **Signal dilution**: the answer sentence buried inside a ~70-word paragraph among topical distractors | The *one* case where a cross-encoder reliably helps (§9.2) |
| A negation question — "which services do **not** use the retry queue" | Persistent blind spot; no scorer fixes it. Needs question parsing |
| A listing/counting question — "how many P2 incidents touched payments last quarter" | Retrieval is the wrong tool; needs a structured query |
| A term that exists only in the dev team's heads, in neither docs nor tickets | Out-of-domain vocabulary; expert-in-the-loop limit |

## 7. The product: a triage verdict, not prose

The primary output is a **verdict**, because the business goal is call
deflection rather than conversation.

| Verdict | Condition | NOC sees |
|---|---|---|
| `SELF_SERVE` | Playbook or matching past incident found, severity below gate | Steps + citations + "incident #4471 was identical, resolved by NOC" — escalation rejected |
| `ESCALATE` | Novel symptom, or severity at/above gate | Page dev team, **with retrieved context attached** |
| `INSUFFICIENT` | Nothing retrieved above threshold | Say so plainly. Never fabricate steps |

### 7.1 Trust is a hard requirement

Deflection only works if NOC trusts the verdict. An uncited "you can handle
this" is ignored and the call happens anyway. Therefore every `SELF_SERVE`
response **must** carry citations to the specific runbook section or incident
ID. Citations are a functional requirement, not presentation polish.

### 7.2 Severity gate

Severity at or above P1 escalates **even when a playbook exists**. Deflection
optimizes for the dev team's time; the severity gate ensures it never does so
at the cost of an outage.

### 7.3 The dangerous error

**False deflection** — telling NOC to self-serve an incident that genuinely
needed the dev team — is the failure that destroys the system's credibility and
prolongs outages. It is weighted far above false escalation.

Target: maximize deflection rate subject to **false deflection rate ≈ 0** on
the gold set. Stating this precision/recall trade-off explicitly, and measuring
it, is the most credibility-earning part of the presentation.

## 8. Evaluation design

Measurement precedes and justifies every architectural addition. Nothing enters
the pipeline on intuition.

### 8.1 Gold question set — ~46 questions

Categories are **failure modes, not topics.** Each exists to make one specific
weakness visible, and each is scored separately (§8.4).

| Category | Count | Proves |
|---|---|---|
| Simple factual | 8 | Baseline works at all |
| Cross-lingual (VI question → EN doc) | 7 | Multilingual embeddings |
| Exact identifier / error code | 6 | Hybrid search; dense retrieval alone fails |
| Requires routing or metadata filter | 6 | Structure-first retrieval (§5.4) |
| **Signal dilution** (buried answer, long chunk) | 5 | The one justified reranker case (§9.2) |
| **Negation** | 3 | Persistent blind spot — needs question parsing, not ranking |
| **Listing / counting** | 3 | Retrieval is the wrong tool; needs a structured query |
| Repeat incident with playbook | 5 | SELF_SERVE deflection |
| Unanswerable | 3 | INSUFFICIENT — refusal to guess |

Each question records: text, expected source document(s), expected verdict,
severity, language, and **failure-mode category**.

The negation and listing categories are expected to stay unsolved by every
retrieval rung. They are included precisely for that reason: they demonstrate
the limit of similarity search and justify the routing layer. A gold set
containing only questions the system can answer would prove nothing.

### 8.2 Metrics

| Metric | Why |
|---|---|
| `recall@5`, `MRR` | Retrieval quality, independent of the LLM |
| Groundedness (LLM judge) | Answer supported by retrieved text |
| Correctness (LLM judge) | Answer matches the gold answer |
| **Deflection rate** | The business metric |
| **False deflection rate** | The dangerous error (§7.3) |
| Refusal accuracy on unanswerable | Does it decline to guess |
| Latency p50 / p95 | Reranking and fusion cost real time |
| Cost per query | Adoption reality for colleagues |

### 8.3 Judge caveat

LLM-as-judge scores are themselves estimates. A ~10-question human-scored
subset is retained to sanity-check the judge. Presenting judge scores as ground
truth would violate the project's own "never guess" principle.

### 8.4 Reporting rule: per failure mode, never aggregate

**Every result is reported as a rung × failure-mode matrix.** A single headline
number is not produced at all, because averaging is how real regressions hide:
a rung that lifts factual questions by 15 points while breaking negation
questions shows up as a clean win.

| | factual | cross-lingual | error code | routing | dilution | negation | listing | repeat | unanswerable |
|---|---|---|---|---|---|---|---|---|---|
| L0 | | | | | | | | | |
| L1 | | | | | | | | | |
| … | | | | | | | | | |

Consequences, all binding:

1. A rung is **adopted only if it improves at least one cell and regresses
   none.** A rung that trades one failure mode for another is rejected, or
   applied only to the query shapes it helps — which is what routing is for.
2. Cells where L0 already succeeds grant later rungs **no credit** (§9.1).
3. Cells that never move across every rung are reported as **open failure
   modes**, not omitted. They become catalog entries.

This matrix is the single most valuable slide in the presentation. It is also
the artifact that makes the "never guess" principle real rather than rhetorical.

## 9. The complexity ladder

The spine of both the build and the talk. **A rung is climbed only when the
evaluation demonstrates the current rung failing on a specific question
category.**

Ordering is by **cost-effectiveness, cheapest first** — which, after the v1.5
revision, puts the cross-encoder reranker **last** rather than fourth.

| Rung | Added | Climb only if | Cost |
|---|---|---|---|
| **L0** | Nothing new — measure the *incumbent* (§9.1) | (baseline) | none |
| **L1** | BM25 + Vietnamese word segmentation | L0 fails on paraphrase | trivial |
| **L2** | Dense embeddings (BGE-M3) | L1 fails on semantic / cross-lingual | index build |
| **L3** | Hybrid, RRF fusion | L2 fails on error codes and identifiers | negligible at query time |
| **L4** | **Structure-first**: question parsing + classify-before-retrieve + metadata pre-filter | Wrong-service, stale, negation or listing questions fail | deterministic, ~free |
| **L5** | **Domain vocabulary map** (acronyms, VI↔EN term pairs) | Internal jargon still misses | human curation, no runtime cost |
| **L6** | **Embedding upgrade** — evaluate a stronger or different embedder | Semantic recall still short | reindex; no added latency |
| **L7** | Cross-encoder reranker — **expected to fail** (§9.2) | Signal dilution persists after L0–L6 | +100s of ms **per query** |
| **L8** | Verdict logic + severity gate | Retrieval is good but calls still arrive | logic only |

Three rungs — L4, L5, L6 — sit between hybrid search and reranking, and all
three are cheaper at query time than a reranker. That ordering is the central
lesson of the revision: **the reranker is the most expensive intervention and
the least likely to pay off, so it is tried last, not by default.**

Not every rung appears in the 45-minute demo (§12). L1–L5 and L7–L8 are
demonstrated live; L6 (embedding upgrade) is presented as a measured result,
since swapping an embedder means a reindex that cannot be done on stage.

### 9.1 What L0 concretely is

L0 must be defined precisely or it degrades into a strawman that flatters every
later rung. It is **title-and-keyword substring search over the corpus, with no
ranking** — the behaviour of a typical wiki search box, standing in for the
knowledge base NOC already has. It is implemented and scored like any other
rung, against the same ~46 questions.

Two honest reporting rules apply:

1. L0 is scored on the **same gold set**, not an easier one.
2. If L0 already answers a question category well, later rungs claim **no
   credit** for that category.

**L0 is the most important rung.** Measuring the incumbent first makes every
later gain attributable, and it is the discipline the audience is least likely
to practise. It is also the only rung that can prove the project unnecessary —
which is precisely why it must be run first and reported honestly.

### 9.2 The reranker hypothesis — stated in advance

Rungs may prove unnecessary, and one is expected to. Two independent sources
point the same way: RAGFlow removed its bundled rerankers in 2025 on the grounds
that they cost latency for minimal recall gain, and the *Document Intelligence*
benchmark (§16) found that **on four of five query shapes where a reranker was
expected to win, cross-encoders matched or did worse than the embedding alone** —
with two of three rerankers *actively degrading* results by preferring token
overlap over meaning. In one case a 22M-parameter model beat every reranker
tested, inverting the assumed cost/performance gradient.

**Pre-registered hypotheses**, recorded here before the experiment runs so the
result cannot be rationalized afterwards:

| # | Hypothesis | Falsified if |
|---|---|---|
| H1 | L7 improves only the **signal-dilution** category | It improves others materially |
| H2 | L7 regresses at least one category | No category regresses |
| H3 | L6 (embedding upgrade) beats L7 at lower query-time cost | L7 wins on more cells than L6 |
| H4 | L4 (structure-first) delivers a larger gain than L6 and L7 combined | Either exceeds it |

Writing the hypotheses down first is the point. The most likely honest outcome
of this project is **"we tested the reranker, and the architecture mattered
more"** — which is a stronger demonstration of engineering judgment than
shipping every component in the diagram.

One caveat to carry into the talk: these findings come from other people's
corpora. They are a *prior*, not a conclusion. The measurement on this corpus
decides, and if the reranker wins here, that gets reported too.

## 10. Failure catalog (v1.5)

First-class deliverable. Each entry carries **symptom → cause → fix → search
term**, so a colleague who is stuck can self-diagnose and know what to look up.
Below is v1, grouped by pipeline stage.

### 10.1 Framing

| ID | Symptom | Cause | Fix / search term |
|---|---|---|---|
| F0.1 | More docs written, escalations unchanged | Findability treated as a documentation problem | Retrieval, not authoring |
| F0.2 | RAG built where grep would do | Corpus is small, structured, or code | "agentic search vs RAG" |
| F0.3 | Cannot say whether the system is good | No success definition | "RAG evaluation", gold set |
| F0.4 | Demo works, production does not | Evaluated on invented questions | Mine real NOC tickets for the eval set |
| F0.5 | Long context ignored as an option | Assumed RAG is always needed | "long context vs RAG" |
| F0.6 | Every component in the reference diagram gets built | The funnel diagram mistaken for a requirement | Cost-ordered ladder; measure each rung |
| F0.7 | Headline score improves, users complain more | Aggregate metric hid a per-category regression | Per-failure-mode matrix (§8.4) |
| F0.8 | Effort spent on ranking while structure is ignored | Semantics assumed harder than filtering | "classify before retrieve", structure-first |
| F0.9 | Expert knowledge left in people's heads | System designed to replace experts, not amplify them | Vocabulary maps, curated routing rules |

### 10.2 Ingestion and parsing

| ID | Symptom | Cause | Fix / search term |
|---|---|---|---|
| F1.1 | Table answers never retrieved | Layout destroyed at parse | "document layout parsing", DeepDoc |
| F1.2 | Answer lives in a screenshot | Text extraction only | Multimodal embedding / OCR |
| F1.3 | Top-k filled with near-identical chunks | Duplicate docs indexed | Dedup at ingest |
| F1.4 | Stale procedure returned confidently | No recency signal captured | Metadata at ingest |
| F1.5 | User sees a doc they should not | ACLs ignored at index time | Per-document permission filters |

### 10.3 Chunking

| ID | Symptom | Cause | Fix / search term |
|---|---|---|---|
| F2.1 | Half a procedure retrieved | Fixed-size split mid-step | Structure-aware / heading-based chunking |
| F2.2 | Retrieves the right topic, not the answer | Chunk too large, embedding diluted | Chunk size tuning |
| F2.3 | "Restart the service" — which service? | Chunk too small, context lost | Context enrichment / parent-document retrieval |
| F2.4 | Chunk says "set it to 30" with no antecedent | Heading hierarchy dropped | Prepend heading path to chunk |
| F2.5 | Table split across chunks | Chunker unaware of table boundaries | Table-aware chunking |
| F2.6 | Answer sentence present in the chunk but ranked below topical distractors | **Signal dilution** in a long chunk | Smaller chunks, or the one justified reranker case (§9.2) |

### 10.4 Embedding

| ID | Symptom | Cause | Fix / search term |
|---|---|---|---|
| F3.1 | Quality collapses on Vietnamese, **silently** | English-only embedding model | Multilingual embeddings, BGE-M3 |
| F3.2 | VI query never matches EN doc | No cross-lingual alignment | Cross-lingual retrieval |
| F3.3 | Internal acronyms never match | Jargon unseen in training | Hybrid search; fine-tuning |
| F3.4 | Short query vs long doc mismatch | Asymmetric embedding not handled | Query/passage prefixes |
| F3.5 | Retrieval degrades after a model change | Index not rebuilt | Reindex on embedding change |
| F3.6 | Scores look wrong | Wrong distance metric / no normalization | Cosine vs dot product |
| F3.7 | Larger, costlier model performs worse | "Bigger is better" assumed; benchmark rank mistaken for fitness on your data | Evaluate small models too — a 22M model has beaten rerankers |
| F3.8 | Internal jargon never retrieves, whatever the model | Domain vocabulary not curated | Expert keyword/acronym map (§5.4) |
| F3.9 | Paraphrase found, literal token missed | Embedding smoothed away the exact term | Hybrid; the literal-token trap |

### 10.5 Retrieval

| ID | Symptom | Cause | Fix / search term |
|---|---|---|---|
| F4.1 | Error code query returns nonsense | Dense retrieval cannot match identifiers | Hybrid search, BM25 |
| F4.2 | Vietnamese keyword search underperforms | Word segmentation not applied | Vietnamese tokenization for BM25 |
| F4.3 | Answer exists but sits at rank 7 | `top_k` too small | Increase k, then rerank |
| F4.4 | Context flooded with noise | `top_k` too large | Threshold + rerank |
| F4.5 | Something is always returned, even garbage | No similarity threshold | Score threshold / abstention |
| F4.6 | Fused ranking worse than either input | Incomparable score scales | Reciprocal Rank Fusion (RRF) |
| F4.7 | Answer from the wrong service | No metadata scoping | Metadata filters |
| F4.8 | "Which services do **not** …" answered with the ones that do | Negation is invisible to similarity | Question parsing; no scorer fixes this |
| F4.9 | "How many incidents last quarter" answered with one anecdote | Listing/counting sent through retrieval | Structured query, SQL agent |
| F4.10 | Correct doc buried among 200k plausible ones | Semantic search run over the whole corpus | Classify-before-retrieve, then search the slice |
| F4.11 | Every rung fails this one question shape | Persistent blind spot, not a tuning problem | Report as an open failure mode (§8.4) |

### 10.6 Reranking

| ID | Symptom | Cause | Fix / search term |
|---|---|---|---|
| F5.1 | Latency doubled, quality flat | Reranker added by default, unmeasured | Measure before adopting |
| F5.2 | Reranker hurts Vietnamese results | English-only cross-encoder | Multilingual reranker (BGE-reranker-v2-m3, ViRanker) |
| F5.3 | Reranking changes nothing | Too few candidates reranked | Widen the candidate pool first |
| F5.4 | Reranker makes results **worse** | Cross-encoder preferred token overlap over meaning | Compare against no-reranker baseline every time |
| F5.5 | Reranker budget would have bought a better embedder | Query-time cost chosen over one-off index cost | Try the embedding upgrade first (L6 before L7) |
| F5.6 | Reranker cannot be cached | Scores depend on the query, so nothing precomputes | Accept the per-query cost, or shrink the candidate pool |
| F5.7 | Reranker adopted on someone else's benchmark | Findings transferred without local measurement | Re-measure on your own corpus (§9.2 caveat) |

### 10.7 Generation

| ID | Symptom | Cause | Fix / search term |
|---|---|---|---|
| F6.1 | Steps that appear in no document | Ungrounded generation | Groundedness constraint + eval |
| F6.2 | **NOC does not trust it, calls anyway** | No citations | Citation-mandatory prompting |
| F6.3 | Two services' procedures merged | Chunks from different sources blended | Source-scoped synthesis |
| F6.4 | Confident tone on weak evidence | No confidence signalling | Calibrated hedging; expose scores |
| F6.5 | Stale playbook followed without warning | Document age not surfaced | Surface recency in the answer |

### 10.8 Deflection (specific to this system)

| ID | Symptom | Cause | Fix / search term |
|---|---|---|---|
| F7.1 | **Outage prolonged by a wrong "you can handle this"** | False deflection | Severity gate; conservative thresholds |
| F7.2 | Everything escalates; no value delivered | Thresholds too conservative | Tune against deflection rate |
| F7.3 | A P1 was deflected | No severity awareness | Severity gate (§7.2) |
| F7.4 | Verdict ignored | No citations / no trust | See F6.2 |
| F7.5 | Same wrong deflection recurs | No feedback loop | Log verdicts + outcomes |

### 10.9 Operations and adoption

| ID | Symptom | Cause | Fix / search term |
|---|---|---|---|
| F8.1 | Answers drift from current docs | Index not refreshed | Incremental re-ingestion |
| F8.2 | No idea what NOC actually asks | Queries not logged | Query logging → eval set growth |
| F8.3 | Quality silently decays | Evaluated once at launch | Regression eval in CI |
| F8.4 | Knowledge base rots | No owner | Assign ownership |
| F8.5 | **The bot becomes another "too complicated" tool** | Same failure as the original KB | Usability is the requirement, not the feature count |

F8.5 closes the loop on the opening story and is the final slide.

### 10.10 Expansion status

**Done (v1 → v1.5, 2026-07-30).** The *Document Intelligence* series (§16)
added 16 entries — F0.6–F0.9, F2.6, F3.7–F3.9, F4.8–F4.11, F5.4–F5.7 — and
changed the ladder, the reporting rule, and the position of reranking. Catalog
now stands at **62 entries** (46 in v1).

**Remaining research for v2:**

- Agentic RAG and the 2025–2026 shift away from vector search for code
- Long-context models as a partial RAG substitute; the "lost in the middle" effect
- GraphRAG, late-interaction retrieval (ColBERT), and structured retrieval
- Contextual retrieval and chunk-context augmentation
- Query transformation: rewriting, decomposition, HyDE, and their failure modes
- Multimodal retrieval failures
- Retrieval security: prompt injection through indexed documents, data exfiltration
- Evaluation frameworks and their known weaknesses (RAGAS and similar)

**Inclusion criterion:** an entry is added only if it has an observable symptom,
a nameable cause, and a search term that leads a stuck colleague somewhere
useful. Interesting-but-undiagnosable phenomena are excluded.

**Process note.** The v1.5 pass changed the architecture, not merely the
documentation — reranking moved from rung 4 to rung 7, and three cheaper rungs
were discovered. That is evidence the research pass belongs **before** the build
milestones, not after (§15).

## 11. Platform decision matrix

The primary take-home artifact for colleagues.

| Tier | Problem | Stack | Setup | Trade-off |
|---|---|---|---|---|
| **0** | ~20 docs, one team | **No RAG.** Long context or grep | Minutes | Breaks past ~100 docs |
| **1** | Team KB, non-technical users want a chatbot | Flowise / AnythingLLM / Dify | ~1 hour | Limited retrieval tuning |
| **2** | Messy scanned PDFs, tables, tuning required | RAGFlow, LlamaIndex parsing | ~half a day, needs 16 GB | Complexity |
| **3** | Multi-source, ACL, audit, SLA | Qdrant/pgvector + Haystack + eval harness | Weeks | Not low-code |
| **4** | Agent over a codebase | **No vector store.** Agentic search + MCP | Hours | No semantic / cross-lingual matching |

Tiers 0 and 4 earn the audience's trust by stating when *not* to use the
technology being presented.

**A rule that cuts across every tier:** at any tier, spend on structure before
spending on ranking. Classification, metadata filtering, question routing and a
curated vocabulary are cheap, deterministic, and inspectable. Rerankers are
expensive per query, unpredictable, and — on the evidence in §9.2 — frequently
neutral. A colleague who remembers only this one rule will still make better
decisions than the reference architecture diagrams they will be shown.

## 12. Presentation run-of-show (~2 hours)

| Time | Segment |
|---|---|
| 0:00–0:10 | **The real story** — we gave NOC a knowledge base; they still call us |
| 0:10–0:25 | **Concepts** — one pipeline diagram, no mathematics |
| 0:25–0:40 | **Do you even need RAG?** grep vs RAG vs long context; the evidence |
| 0:40–1:25 | **Live demo — climbing the ladder, failure by failure** |
| 1:25–1:40 | **Decision matrix** (§11) |
| 1:40–1:50 | **Failure catalog** as the take-home |
| 1:50–2:00 | Q&A, adoption checklist, VI/EN glossary |

The demo block is structured as **failure → named fix**, never as a feature
tour. Each fix is a concept the audience can subsequently search for:

1. Baseline (L0/L1) fails a paraphrased question → *semantic search*
2. Vietnamese question misses the English runbook → *multilingual embeddings*
3. Error-code query returns nonsense → *hybrid search*
4. Answer drawn from the stale runbook, wrong service → *classify-before-retrieve*
5. "Which services do **not** …" fails at every rung → *question parsing; the
   limit of similarity search*
6. Internal acronym never matches → *domain vocabulary map*
7. **The reranker experiment** → add it, measure it, and show the latency chart
   against the per-category matrix. Expected outcome: it helps one category and
   costs 100s of ms. **The audience watches a component get rejected on evidence.**
8. Confidently wrong on an unknown → *grounding and refusal*
9. Repeat incident → **SELF_SERVE verdict; the call is rejected**

Beat 7 is the pivot of the talk. Every RAG tutorial adds a reranker and declares
victory; this one adds it, measures it, and takes it out. That single moment
teaches the evaluation principle more effectively than any slide about
evaluation, and it inoculates the audience against the next vendor diagram they
are shown.

Payoff: the same service consumed by Open WebUI (OpenAI-compatible endpoint),
by an agent (MCP), and rebuilt no-code in Flowise.

## 13. Repository layout

```
rag/
├── README.md                  decision matrix + adoption checklist (take-home)
├── docker-compose.yml         qdrant + open-webui + flowise + service
├── corpus/
│   ├── docs/                  runbooks, architecture (mixed VI/EN)
│   ├── tickets/               past incidents
│   └── eval/questions.yaml    gold set with expected sources and verdicts
├── learning/                  Track A — from-scratch notebooks
├── service/
│   ├── app.py                 /v1/chat/completions, /retrieval
│   ├── strategies/            bm25, dense, hybrid, reranked, filtered
│   ├── verdict.py             SELF_SERVE / ESCALATE / INSUFFICIENT
│   ├── ingest.py
│   └── mcp_server.py
├── eval/
│   ├── run.py                 scores every rung of the ladder
│   └── results/               the numbers presented
└── docs/
    ├── superpowers/specs/
    ├── failure-catalog.md
    ├── decision-matrix.md
    ├── concepts/              diagrams, VI/EN glossary
    └── talk/run-of-show.md
```

## 14. Constraints and risks

| Risk | Mitigation |
|---|---|
| 8 GB WSL2 host | Cloud LLM, local embeddings; ~4.5 GB budget (§5.3) |
| Live demo failure | Pre-warmed containers, pre-computed index, recorded fallback |
| Authored corpus feels artificial | Traps modelled on real escalation patterns; state the limitation openly |
| LLM judge unreliable | Human-scored subset (§8.3) |
| Cloud LLM needs network during the talk | Cache demo responses; keep a local fallback answer path |
| 2 hours is not much time | Run-of-show is timed; demo is rehearsed end to end |

## 15. Milestones

Each milestone gets its own implementation plan.

| # | Milestone | Output |
|---|---|---|
| **M0** | Catalog research pass v2 (§10.10) — **moved to first** | Catalog v2; ladder confirmed before anything is built |
| **M1** | Corpus + gold question set + eval harness + L0 baseline | Measurable baseline exists |
| **M2** | Retrieval service, rungs L1–L3 | Hybrid retrieval, per-category matrix |
| **M3** | Rungs L4–L5 — structure-first routing + vocabulary map | The cheap architectural wins, measured |
| **M4** | Rungs L6–L7 — embedding upgrade, then the reranker experiment | Hypotheses H1–H4 (§9.2) resolved on evidence |
| **M5** | Rung L8 — verdict logic, severity gate, citations | Deflection and false-deflection measured |
| **M6** | Interfaces — OpenAI-compatible, MCP, Open WebUI, Flowise | Demo-able end to end |
| **M7** | Talk materials, decision matrix, glossary, rehearsal | Presentable |

**M0 moved to the front.** The v1.5 revision changed the architecture, not just
the prose — a second research pass could do the same, and discovering that after
M2 is built means rework. Research is cheap; rebuilding is not.

Track A (learning notebooks) runs alongside M2–M4 rather than as a separate
milestone: each rung is understood from scratch before it is configured.

## 16. References

- **Document Intelligence: A Series on Building RAG Brick by Brick, from Minimal
  to Corpus Scale** — 22 articles in five parts; source of the architectural
  principles in §5.4.
  https://towardsdatascience.com/document-intelligence-a-series-on-building-rag-brick-by-brick-from-minimal-to-corpus-scale/
- **Rerankers Aren't Magic Either: When the Cross-Encoder Layer Is Worth the
  Cost** — the 7-model benchmark (4 embeddings, 3 cross-encoders) behind §9.2.
  https://towardsdatascience.com/rerankers-arent-magic-either-when-the-cross-encoder-layer-is-worth-the-cost-enterprise-document-intelligence-vol-1-2bis/
- RAGFlow release notes — removal of bundled rerankers, 2025.
- Anthropic's replacement of the Claude Code vector index with agentic search,
  May 2025; Amazon Science (AAAI 2026) measuring agentic keyword search at 94.5%
  of RAG faithfulness with no vector store. Both support §10.1 entry F0.2.
- BAAI BGE-M3 — multilingual embeddings, 100+ languages, 8192-token inputs.

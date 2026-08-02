# RAG Fundamentals — source material

Companion to the design spec
(../superpowers/specs/2026-07-29-rag-noc-assistant-design.md) and the narrative
design (../talk/logic-flow.md).

**This is a source pool, not a running order.** The seminar interleaves teaching
with demonstration rather than front-loading theory, so this material is
distributed across the acts:

| Section here | Goes to | Note |
|---|---|---|
| §1 Why RAG (the tool options) | **Act II** | Include the CAG rejection (§1.1) |
| §2 The stages | **Act II** | Keep the *ingest fails silently* point; it sets up demo block 1 |
| §3 The evolution | **Act V** | Compressed to one arc, delivered *after* they have climbed the ladder |
| §4 When to retrieve | Cut, or one line in Act V | |
| §5 Security | **Act IV** | Rewritten as a mechanism (§5) |
| §6 Glossary | Handed out **at the start** | |

The old cutting guidance in §7 is superseded by the rehearsal card in
`../talk/logic-flow.md` §7.

---

## 1. Why RAG?

RAG is **one of four** ways to get knowledge into a model. Presenting it as *the*
way is how audiences end up adopting it for problems it does not solve.

| Approach | What it changes | Best for | Real cost |
|---|---|---|---|
| **Prompt / long context** | Nothing | Small, stable corpora; prototyping | ~20–24× more expensive than RAG at production volume |
| **CAG** (cache-augmented) | Nothing | Stable corpus that fits the window, **on a model instance you own** | Cache rebuild on every document change |
| **Fine-tuning** | Behaviour | Tone, format, response style, reasoning patterns | Training, plus retraining whenever content changes |
| **RAG** | Knowledge | Facts that change; attribution; per-user access control | Index maintenance |
| **Agentic search** | Nothing | Code, structured filesystems | Latency and tokens on every query |

The 2026 consensus is that these **layer** rather than compete:

> **Fine-tuning teaches the model how to respond. RAG supplies what to reason
> about. Long context is for prototyping.**

### 1.1 CAG, and why it was rejected here

**Cache-Augmented Generation** preloads the entire corpus into context, precomputes
the KV cache, and serves with no retrieval at runtime. It is the *optimised* form
of long context — it attacks long context's weakness, cost per query, directly.

It is a real candidate and it was genuinely considered. Two things killed it:

1. **The model host is shared across teams.** CAG's benefit depends on the cached
   corpus prefix staying **resident** in GPU memory. With multiple tenants, each
   would need its own large prefix competing for the same finite memory — caches
   get evicted and recomputed, erasing the advantage that justified CAG.
2. **The corpus will grow beyond one product's documentation.** RAG scales by
   adding to an index; CAG requires rebuilding the cache and re-fitting the window.

Published RAG-vs-CAG comparisons argue about **context window size**. That is the
less useful criterion. The one that decided it:

> **Do you own the model instance, or share it?** Shared hosting rules out any
> technique that depends on resident per-corpus cache state.

Present this as a rejection *with a stated reason*. It is a worked example of the
method the whole seminar teaches: consider the option, name the constraint that
kills it, move on.

### When RAG is the right answer

- **Freshness.** For operational facts that change more often than weekly, RAG
  is the only practical option — a fine-tune is stale the day after training.
- **Attribution.** You can cite a retrieved document. You cannot cite a weight.
  For our NOC case this is not a nicety: without citations the operator does not
  trust the answer and calls the dev team anyway (§7.1 of the spec).
- **Access control.** Retrieval can filter per user at query time. Fine-tuning
  bakes everything into one model that knows things some readers must not see.
- **Cost of change.** A new runbook means one document indexed, not a retrain.
- **Auditability.** You can inspect exactly what was retrieved and why. This is
  what makes the system debuggable at all.

### When RAG is the wrong answer

| Situation | Use instead |
|---|---|
| ~20 documents, one team | Long context. Skip the infrastructure entirely |
| Stable corpus, fits the window, **you own the model instance** | CAG (§1.1) |
| Output has the wrong *tone or format* | Fine-tuning. Retrieval cannot fix behaviour |
| Searching code | Agentic search — grep, read, follow references |
| "How many incidents last quarter?" | A structured query. Counting is not retrieval |
| "What did we decide last sprint?" | Nothing. It was never written down |

That last row is the one worth repeating: **retrieval finds what was written
down. It cannot recover what was never recorded.** Most disappointment with RAG
traces back to asking it for the second.

---

## 2. The stages of RAG

Two phases that run at completely different times — a distinction most diagrams
blur, and the reason for the cost axis in the spec (§9).

### Ingest — offline, paid once per document

```
load → parse → chunk → embed → index
```

| Stage | What it does | Where it fails |
|---|---|---|
| **Load** | Fetch documents from sources | Missed formats; permissions ignored |
| **Parse** | Binary → text + structure | Tables flattened, scanned pages yield *empty text*, diagrams dropped |
| **Chunk** | Split into retrievable units | Procedure split mid-step; chunk loses its heading context |
| **Embed** | Text → vector | Wrong language coverage; internal jargon unseen in training |
| **Index** | Store vectors + metadata | No metadata captured, so no filtering is possible later |

### Query — online, paid on every request, forever

```
query → [transform] → retrieve → [rerank] → augment → generate → cite
```

| Stage | What it does | Where it fails |
|---|---|---|
| **Transform** | Rewrite, expand, decompose | Rewrites away the exact error code that mattered |
| **Retrieve** | Find candidate chunks | Error codes defeat dense search; no threshold, so garbage is always returned |
| **Rerank** | Reorder candidates | Hundreds of ms per query for frequently no gain |
| **Augment** | Build the prompt | Too much context; the answer gets lost in the middle |
| **Generate** | Produce the answer | Steps invented that appear in no document |
| **Cite** | Attribute to sources | No provenance kept at parse time, so citations are useless |

**The lesson to state out loud:** ingest failures are *silent* — nothing throws
an error when a scanned page extracts to an empty string. Query failures are
*visible*. Teams therefore spend their time on the visible half, which is not
where the problem usually is.

---

## 3. The evolution of RAG — as a chain of failures

Do not teach this as a timeline. Teach it as **each generation fixing a named
failure of the one before**, because that is what lets an engineer identify
which generation *they* need.

```
Gen 0  Keyword search
        └─ FAILED: vocabulary mismatch
           "payment stuck" never matches "order state machine deadlock"

Gen 1  RAG (Lewis et al., 2020) — dense retrieval + generation
        └─ FAILED: naive retrieve-then-read is brittle
           bad chunks, no ranking, exact identifiers lost

Gen 2  Advanced RAG (2023–24) — better chunking, hybrid search, reranking
        └─ FAILED: a chunk still loses its document context
           "revenue grew 3%" — whose revenue? which quarter?

Gen 2.5 Contextual Retrieval (Anthropic, Sept 2024)
        prepend chunk-specific context before embedding
        └─ FAILED: still one-shot; cannot chain reasoning steps

Gen 3a GraphRAG (Microsoft, 2024) — entity-relation graphs, multi-hop paths
Gen 3b Modular RAG — pipeline becomes reconfigurable modules
        └─ FAILED: still a fixed pipeline; cannot decide when to retrieve

Gen 4  Agentic RAG (2024–26) — retrieval as a reasoning loop
        plan → retrieve → evaluate → iterate
        Self-RAG (reflection tokens), CRAG (retrieval evaluator), FLARE
        └─ shifted the question from "what to retrieve" to "WHEN to retrieve"

Gen 5  Context Engineering (2026)
        RAG is one technique inside a discipline covering governance,
        memory and orchestration
```

### Three measured results worth quoting

Most of this field is claims. These three are numbers.

**Contextual Retrieval (Anthropic, 2024)** — prepending chunk-specific context
before embedding:
- contextual embeddings alone: **35% fewer** retrieval failures (5.7% → 3.7%)
- plus contextual BM25: **49% fewer**
- plus reranking: **67% fewer** (5.7% → 1.9%)

**GraphRAG (RAGSearch benchmark, 2026)** — 6 datasets, 5 GraphRAG variants:
- multi-hop QA: **+27.23** average improvement
- general single-hop QA: **+0.47**

GraphRAG earns its heavy preprocessing for genuine multi-hop questions and
almost nothing otherwise. The same benchmark found agentic search closed 32.3%
of the dense-RAG-to-GraphRAG gap without any graph at all.

**Agentic search over code (Anthropic, May 2025)** — the vector index was
*removed* from Claude Code because grep retrieved code better. Amazon Science
(AAAI 2026) measured agentic keyword search at 94.5% of RAG faithfulness with no
vector store.

### The meta-lesson — the real point of this section

> **You do not need the latest generation. You need the generation that fixes
> your failure.**

Most teams adopt Gen 4 machinery to solve a Gen 1 problem. The only way to know
which generation you need is to measure where yours actually breaks — which is
the complexity ladder (spec §9) and the reason it exists.

### The layer map — where the 2026 buzzwords fit

Colleagues will have heard these. They are **layers around RAG, not competitors**,
which is precisely why "is RAG dead" keeps being asked and keeps being wrong.

| Layer | Unit of control | Where retrieval sits |
|---|---|---|
| Prompt engineering | One model response | RAG fills the prompt |
| Context engineering (2025) | What is in the window | RAG is the mechanism; **CAG** is the no-retrieval alternative (§1.1) |
| Loop engineering (late 2025→) | One agent's cycle: discover → plan → execute → verify | **Agentic RAG** — the agent chooses how to retrieve |
| Graph engineering (2026→) | Many agents; stateful, **cyclic** control flow | GraphRAG is retrieval over a knowledge graph — *a different sense of "graph"* |
| Harness engineering | Everything wrapping the model | Retrieval is one harness component |

Two precise points worth making, because both are commonly got wrong:

- Agent graphs are **cyclic, not DAGs.** Loops live inside the graph — exactly what
  a classic DAG orchestrator forbids. Closer to a state machine than a pipeline.
- **"Graph" means two unrelated things**: a graph of *agents* (orchestration) and a
  graph of *knowledge* (GraphRAG).

"**Agent = Model + Harness**" (Hashimoto, 2026). The wrapper around a *fixed* model
reportedly moves end-to-end benchmark performance by up to **6×** — which is
independent support for this project's thesis that architecture beats
model-swapping.

Cap this at one slide. The payoff is a single sentence: *these are layers you can
add later; you still have to make retrieval work first.*

### On "is RAG dead?"

It is a category error, and worth defusing directly because someone will ask.
Context engineering is a *discipline*; RAG is a *technique inside it*. Retrieval
is the transport layer; context engineering is the structural layer around it —
governance, memory, orchestration.

A useful contrast for choosing:

> A **semantic layer** is narrow and deep — near 100% correct on the subset it
> covers, useless outside it. **RAG** is wide and shallow — it will attempt
> anything, and be right most of the time.

For NOC triage, wide-and-shallow with citations is the right shape. For
"how many P2 incidents last quarter", narrow-and-deep is the only correct answer.

---

## 4. When to retrieve at all

A Gen 4 idea that is easy to explain and immediately useful: **policies should
decide *when* to retrieve, not only *what*.**

- **Self-RAG** — the model emits reflection tokens deciding whether retrieval is
  needed and critiquing what came back.
- **CRAG (Corrective RAG)** — a retrieval evaluator scores the documents and
  triggers corrective action when they are poor.
- **FLARE** — anticipates upcoming content and re-queries when the next tokens
  look low-confidence.
- **Adaptive gating** — skip retrieval entirely for questions the model can
  answer, saving latency and cost.

For our system this is the deterministic router (spec §9.2, L4). Same idea,
without the machine learning: *classify the question, then choose the strategy.*

---

## 5. The stage nobody draws: retrieval is an untrusted input channel

Include this. It is the segment that earns the room's respect, and it appears in
almost no RAG tutorial.

Every retrieved chunk is **text from elsewhere, injected into a privileged
prompt**. That is an attack surface.

**Indirect prompt injection**: a document sitting in the indexed corpus contains
instructions aimed at the model. When any user runs an ordinary search, the
model retrieves the document and follows them.

This is not theoretical. Microsoft 365 Copilot's RAG ingested hidden document
content whose injected instructions caused Copilot to construct markdown image
links that **exfiltrated context data to an attacker server — with zero clicks
from the victim.**

The risk compounds when three things meet — sometimes called the *lethal
trifecta*: access to private data, exposure to untrusted content, and the ability
to communicate externally. An internal assistant with tool access has all three.

**For the NOC system specifically:** the corpus is internal, which sounds safe —
but incident tickets routinely contain content pasted from customers, vendors and
external logs. That is the injection surface, and it is inside the trusted
boundary.

Defences are layered; **there is no 100% solution**:
- sanitise retrieved content before it enters the model context
- treat an agent with data access as a privileged service account
- constrain outbound capability — no arbitrary URL construction
- keep provenance so an injected instruction can be traced to its document

---

## 6. Glossary (VI/EN)

The Vietnamese column is deliberately left for the team to fill with **the words
your colleagues actually use**, not dictionary translations. Internal vocabulary
is a project asset (spec §5.4); imposing outside terms defeats the purpose.

| English | Meaning | Vietnamese (team's usage) |
|---|---|---|
| Chunk | A retrievable unit of a document | |
| Embedding | Text represented as a vector of numbers | |
| Dense retrieval | Search by meaning, via embeddings | |
| Sparse / BM25 | Search by exact words | |
| Hybrid search | Both, results fused | |
| RRF | Fusion by rank rather than incomparable scores | |
| Rerank | Reorder candidates with a slower, more accurate model | |
| Cross-encoder | Model scoring query and document *together* | |
| Grounding | Answer supported by retrieved text | |
| Hallucination | Confident output not supported by any source | |
| Provenance | Which document, page and region an answer came from | |
| Recall@k | Was the right document in the top k? | |
| MRR | How high did the right document rank? | |
| Multi-hop | Question needing several linked facts | |
| Indirect prompt injection | Instructions hidden in an indexed document | |

---

## 7. Cutting guidance for 15 minutes

| Priority | Segment | Minutes |
|---|---|---|
| **Must** | §1 Why RAG — the four approaches and when each wins | 4 |
| **Must** | §2 Stages — one diagram, ingest vs query, silent vs visible failure | 4 |
| **Must** | §3 Evolution as a failure chain + the meta-lesson | 5 |
| **Strong** | §5 Security — retrieval as untrusted input | 2 |
| Cut to one slide | §4 When to retrieve | — |
| Hand out | §6 Glossary | — |

If time runs short, cut §4 first and §3's measured results second — but **keep
the meta-lesson**, because it is what makes the rest of the seminar coherent:
you need the generation that fixes your failure, and you only know which by
measuring.

---

## Sources

- Lewis et al. (2020), *Retrieval-Augmented Generation for Knowledge-Intensive
  NLP Tasks* — the original.
- Gao et al., *Retrieval-Augmented Generation for Large Language Models: A
  Survey* (arXiv 2312.10997) — the Naive / Advanced / Modular taxonomy.
- *Modular RAG: Transforming RAG Systems into LEGO-like Reconfigurable
  Frameworks* (arXiv 2407.21059).
- *Agentic Retrieval-Augmented Generation: A Survey* (arXiv 2501.09136).
- Anthropic, *Contextual Retrieval in AI Systems* (Sept 2024) — the 35/49/67%
  failure-reduction figures. https://www.anthropic.com/engineering/contextual-retrieval
- *Do We Still Need GraphRAG? Benchmarking RAG and GraphRAG for Agentic Search
  Systems* (arXiv 2604.09666) — the +27.23 vs +0.47 result.
- Self-RAG, CRAG, FLARE — adaptive and corrective retrieval.
- Microsoft GraphRAG (2024) — entity-relation graph construction.
- Indirect prompt injection and the M365 Copilot exfiltration case; the "lethal
  trifecta" framing.
- Context engineering vs RAG — RAGFlow's 2025 year-end review, *From RAG to
  Context*; and the semantic-layer contrast.

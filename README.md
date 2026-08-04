# RAG for NOC — a teaching project

A hands-on RAG system that helps a NOC team answer questions from an EDR product's
documentation: **answer** when a playbook exists, **escalate with evidence** when
it doesn't. Built to be understood, not just used — every retrieval technique is
built from scratch and **measured**, so you can see which one buys what, and which
ones don't.

The real deliverable is a ~2-hour seminar plus this repo. If you clone one thing,
clone the discipline: **never guess — measure.** Results here are always a
rung × failure-mode matrix, never a headline number, because averaging hides
regressions.

> **This repo is public and the corpus is invented** ("SENTRIQ", a fictional EDR
> product). Real company documentation lives only in `corpus/private/`
> (gitignored) and is never committed. See `CLAUDE.md`.

## Quick start

```bash
# 1. render the invented corpus to its messy real-world formats (pdf/docx/xlsx/scan)
bash scripts/render_corpus.sh

# 2. Path A — the learning notebooks (needs a GPU; uses uv)
uv run learning/01_naive_retrieval.py        # or open cell-by-cell in VS Code
#    ... through 08; see learning/README.md for the arc

# 3. the eval harness — scores every rung as a matrix
uv run python eval/run.py
uv run python eval/parsing.py                 # parsing quality vs the source
```

## What's here

| Path | What it is |
|---|---|
| `learning/` | **Path A** — 8 notebooks building the ladder from scratch, each climbing one rung and showing one measured failure. Start at `learning/README.md`. |
| `corpus/` | The invented SENTRIQ corpus: `source/` (markdown, ground truth, never indexed), `rendered/` (the binaries the pipeline reads), `tickets/` (50 incidents), `BIBLE.md` (the consistency reference). |
| `eval/` | The measuring stick: `ingest.py` (parse every format), `run.py` (rung × failure-mode matrix), `parsing.py` (recovery vs source), `questions.yaml` (the gold set — **replace with real questions**). |
| `docs/` | The design spec (`superpowers/specs/`), the seminar narrative (`talk/logic-flow.md`), the concepts (`concepts/fundamentals.md`), and `REVIEW-QUEUE.md`. |

## The two ideas that organise everything

**Two ladders, ordered by when cost is paid.** Parsing (P0–P4) runs once at
ingest; retrieval (L0–L8) runs on every query, forever. Spend at ingest first —
which is why the cross-encoder reranker sits *last* (L7), and why a scanned
document that extracts to nothing is caught at ingest, not three rungs later.

**Climb a rung only when evaluation shows the one below it failing.** The notebooks
demonstrate this literally: notebook 02 was meant to end on "hybrid wins";
measuring it showed hybrid *hurt* the cross-lingual query, which forced the routing
rung (04) into existence. Notebook 05 adds a reranker, measures it, and removes it.

## Which stack for which problem (the take-home)

You do not always need RAG, and you rarely need the fanciest version. Decide by
constraint, not fashion:

| Tier | Your problem | Use | Note |
|---|---|---|---|
| **0** | ~20 docs, one team | **No RAG** — long context or grep | Breaks past ~100 docs |
| **0b** | Stable corpus, fits the window, **you own the model instance** | **CAG** (cache the corpus) | Shared model hosting rules it out — the cache gets evicted |
| **1** | Team KB, non-technical users want a chatbot | Flowise / AnythingLLM / Dify | Limited retrieval tuning |
| **2** | Messy scanned PDFs, tables, tuning needed | Docling / RAGFlow + own service | ~half a day |
| **3** | Multi-source, ACL, audit, SLA | Qdrant/pgvector + Haystack + eval | Weeks; not low-code |
| **4** | Agent over a codebase | **No vector store** — agentic search + MCP | grep beats embeddings for code |

**One rule across every tier: spend on structure before ranking.** Classification,
metadata filtering, query routing and a curated vocabulary are cheap, deterministic
and inspectable. A reranker is expensive per query and, on the evidence here,
frequently neutral. (Full decision guides and the 100+ entry failure catalog are in
the spec, `docs/superpowers/specs/`.)

## Adoption checklist

Before you point a RAG system at real NOC traffic:

1. **Measure the baseline first (L0).** Whatever search you have now, score it on
   real questions. Later rungs earn credit only where L0 fails.
2. **Mine real questions.** 20–40 from actual tickets/chat, each tagged with the
   document or past incident that answers it. Invented questions flatter the system
   (catalog F0.4). Drop them into `eval/questions.yaml`.
3. **Check for silent parsing loss.** Any document that extracts to near-nothing
   (scans, images) is indexed but unreachable. `eval/parsing.py` finds them.
4. **Capture metadata at ingest** — service, severity, recency. Structure filtering
   is the cheapest, highest-leverage rung.
5. **Gate answers on confidence, and escalate with evidence.** A confidently wrong
   answer to an operator at 3 a.m. is worse than no system. Measure false-answer
   rate, and drive it to zero before optimising anything else.
6. **Report per failure mode, never as one number.**

## Environment

Learning runs on a local GPU (an RTX 3090 here) with `bge-m3`. The demo/eval also
targets a GPU-less host calling company-hosted models over the internal network —
switching is configuration, not a code path. Latency and cost figures must be
measured on the host that will serve, never the workstation (spec §5.3).

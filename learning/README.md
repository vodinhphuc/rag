# Track A — learning from scratch

Private learning track (spec §5.1). The point is **understanding**, not reuse:
you build chunking, cosine search, BM25, RRF fusion, reranking and scoring by
hand, so that when the demo stack does these behind a config screen you know
exactly what it is doing and can answer any question from the floor.

Not a framework. No LangChain, no LlamaIndex. Model loading is bought
(`sentence-transformers`); the retrieval logic is built.

## How to run

Each notebook is a plain `.py` in `# %%` cell format — it runs as a script and
opens as a notebook in VS Code or Jupyter.

```bash
uv run learning/01_naive_retrieval.py       # run top to bottom
# or open it in VS Code and run cells with Shift+Enter
```

The corpus must be rendered first (`bash scripts/render_corpus.sh`). These
notebooks read `corpus/rendered/` like the real pipeline — never `corpus/source/`.

## The arc — each notebook climbs one rung and shows one failure

| # | Builds | The lesson it makes visible |
|---|---|---|
| 01 | Fixed-size chunking, dense embedding, cosine search | Dense retrieval works for meaning — and wobbles on exact error codes |
| 02 | BM25 from scratch, RRF fusion | BM25 is confident on exact tokens, blind across languages; fusing helps same-language but *hurts* cross-lingual — which is why routing (L4) exists |
| 03 | Cross-lingual retrieval, `doc_id` grouping, citation language | A Vietnamese question finds the English runbook; three translations stop flooding top-k; cite in the reader's language or flag the gap |
| 04 | Query routing + metadata scoping (L4) | Route cross-lingual to dense-only (undoing 02's hybrid dilution); separate look-alike docs by the component that raised the alert |
| 05 | Cross-encoder reranking (L7) | Measure whether it helps — and whether the latency is worth it |
| 06 | Grounded answer + the answer/escalate verdict (L8) | Refusing to guess; citing the source in the reader's language |
| 07 | Retrieval over the incident history (tickets) | A shorthand alert matches past tickets with no vocabulary gap; the matched precedent decides answer vs escalate, and hands a warm start to the hard slice |

The arc grows as rungs are reached, not all up front — the same discipline as the
spec's ladder (§9): climb only when the current rung is shown to fail. Notebook 02
was meant to end on "hybrid wins"; measuring it forced a rung (routing) into
existence that the plan did not have. That is the method working.

Not yet built, each waiting on its inputs rather than guessed:
- **Parsing ladder (P0–P4)** — needs the PDF/DOCX/scanned corpus loaded (D07, D10,
  D12, D16). Would also let the vocabulary map (L5) be measured against the whole
  document set, and is the seminar's demo block 1 (the scanned doc that is indexed
  but unreachable).
- **Vocabulary map (L5)** — partially seen in notebook 07 (ticket→ticket needs no
  map; ticket→formal-runbook does). A full treatment needs the parsed docs above.
- **Embedding head-to-head (L6)** — needs the hosted `Qwen3-Embedding-4B` to
  compare against bge-m3 on the same index.

## Model

`BAAI/bge-m3` for embeddings — multilingual (the corpus is VI/EN/JA), ~2.2 GB,
loads on the 3090. It is also one arm of the spec's L6 embedding head-to-head, so
having it here is not throwaway. The eval work later also runs
`Qwen3-Embedding-4B` to match the demo index (spec §5.3.4); for *learning the
concepts* the model choice does not change the lesson, and a smaller model
iterates faster.

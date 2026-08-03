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
| 02 | BM25 from scratch, RRF fusion | Keywords find the error code dense missed; fusing beats either alone |
| 03 | Cross-lingual retrieval, `doc_id` grouping | A Vietnamese question finds the English runbook; three translations stop flooding top-k |
| 04 | Cross-encoder reranking | Measure whether it helps — and whether the latency is worth it |
| 05 | Grounded answer + the answer/escalate verdict | Refusing to guess; citing the source |

Later notebooks are written as each rung is reached, not all up front — the same
discipline as the spec's ladder (§9): climb only when the current rung is shown
to fail.

## Model

`BAAI/bge-m3` for embeddings — multilingual (the corpus is VI/EN/JA), ~2.2 GB,
loads on the 3090. It is also one arm of the spec's L6 embedding head-to-head, so
having it here is not throwaway. The eval work later also runs
`Qwen3-Embedding-4B` to match the demo index (spec §5.3.4); for *learning the
concepts* the model choice does not change the lesson, and a smaller model
iterates faster.

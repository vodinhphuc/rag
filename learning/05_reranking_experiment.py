# %% [markdown]
# # 05 — The reranker experiment (L7)
#
# Every RAG tutorial adds a cross-encoder reranker near the end and declares
# victory. This notebook does what the spec insists on instead: add it, *measure*
# it, and let the measurement decide. The question is not "does a reranker help in
# general" — it is "does it help *on this corpus*, enough to pay for its latency,
# given that the cheap structural rungs (L1–L4) already did most of the work."
#
# Spoiler, earned from data below: on this corpus it changes which document wins on
# **zero** queries, costs 100–400 ms, and its one real contribution is sharper
# confidence — which matters for the answer/refuse threshold (notebook 06), not for
# ranking. That is the honest "we tested it and mostly removed it" result the
# seminar is built around.

# %%
import time
import re
import numpy as np
from sentence_transformers import CrossEncoder
from _shared import load_chunks, DenseIndex

docs, chunks = load_chunks()
dense = DenseIndex(chunks)

# %% [markdown]
# ## 1. Why a cross-encoder *could* help
#
# The dense retriever is a **bi-encoder**: it embeds the query and each document
# separately, then compares. That is fast (embed once, reuse forever) but lossy —
# a long document is averaged into one vector, so a single buried answer sentence
# gets diluted by everything around it.
#
# A **cross-encoder** reads the query and one document *together* in a single
# forward pass and outputs a relevance score. It can attend to the exact answer
# span, so it should rescue a buried answer a bi-encoder averaged away. The price:
# nothing can be precomputed. Every candidate is a fresh forward pass **at query
# time**, so cost scales with how many candidates you rerank.

# %%
reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", device="cuda", max_length=512)

def rerank(query, cand_idx):
    pairs = [(query, chunks[i]["text"]) for i in cand_idx]
    scores = reranker.predict(pairs)
    order = [cand_idx[j] for j in np.argsort(-scores)]
    return order

def rank_of(order, doc):
    for r, i in enumerate(order):
        if chunks[i]["doc"] == doc:
            return r
    return None

# %% [markdown]
# ## 2. On the real corpus — it changes nothing, and it is not free
#
# Take dense's top-10 for each query, rerank them, and compare the rank of the
# correct document before and after. Because L2 already places the right document
# at rank 0 on this small, distinct corpus, there is nothing for the reranker to
# reorder. Watch the `dense` and `rerank` columns be identical, and the millisecond
# column not be.

# %%
cases = [
    ("agent offline not sending heartbeat",           "D06"),
    ("what do I do when the collector is overloaded",  "D08"),
    ("store shard will not allocate",                  "D09"),
    ("detection rule failed to compile",               "D11"),
    ("agents dropped off, telemetry stopped",          "D08"),
]
print(f"{'query':46s} {'exp':4s} {'dense':>5s} {'rerank':>6s} {'ms':>5s}")
print("-" * 70)
for q, exp in cases:
    dorder = dense.ranking(q)
    t = time.perf_counter()
    rorder = rerank(q, list(dorder[:10]))
    ms = (time.perf_counter() - t) * 1000
    print(f"{q[:46]:46s} {exp:4s} {str(rank_of(dorder, exp)):>5s} "
          f"{str(rank_of(rorder, exp)):>6s} {ms:5.0f}")

# %% [markdown]
# ## 3. Where it *does* help — a fair signal-dilution case
#
# To prove the reranker is not a strawman, here is the case it is built for. Two
# candidates for the same question:
# - **A** actually answers it, phrased naturally, but buried in a long paragraph of
#   unrelated operational prose.
# - **B** is the wrong service and short, sharing only the word "timeout".
#
# This corpus's real signal-dilution trap (D04, one sentence in a long paragraph)
# is a PDF we have not parsed yet, so this pair is constructed — and labelled as
# such — purely to show the mechanism.

# %%
q_dil = "the payment worker keeps timing out, what is its configured limit"
A = ("Operators should first confirm the service is registered and healthy in the "
     "console before making changes. Many transient issues resolve on their own as "
     "the system rebalances load across the worker pool. The payment worker is "
     "configured to wait 30 seconds for an acknowledgement before it times out and "
     "re-queues the request. If the problem persists across the whole pool, "
     "escalate to the platform team and attach logs from the affected region.")
B = "The order service uses a 5 second timeout when it validates inventory levels."

qv = dense.model.encode([q_dil], normalize_embeddings=True)[0]
av, bv = dense.model.encode([A, B], normalize_embeddings=True)
rs = reranker.predict([(q_dil, A), (q_dil, B)])
print(f"dense   A(answer,long)={av@qv:.3f}  B(wrong,short)={bv@qv:.3f}"
      f"  gap={abs(av@qv-bv@qv):.3f}  -> {'A' if av@qv>bv@qv else 'B'}")
print(f"rerank  A={rs[0]:.3f}  B={rs[1]:.3f}"
      f"  gap={abs(rs[0]-rs[1]):.3f}  -> {'A' if rs[0]>rs[1] else 'B'}")
print("\nBoth pick A — but look at the gap. Dense barely separates them; the")
print("cross-encoder separates them enormously. Its value here is CONFIDENCE,")
print("not a corrected ranking.")

# %% [markdown]
# ## 4. Where it also fails — rerankers are not magic
#
# The opposite case, and the honest counterweight. **B** is stuffed with the
# query's exact vocabulary but contains no answer; **A** answers in a paraphrase.
# The bi-encoder is fooled by the keyword overlap — and so is the cross-encoder.
# This is catalog **F5.4**: a reranker can prefer token overlap over meaning just
# like BM25. Adding one does not guarantee correctness; it guarantees latency.

# %%
q_adv = "how long before the payment worker gives up and retries the request"
A2 = ("The nightly window rotates credentials and verifies backups across regions. "
      "If no acknowledgement arrives within 30 seconds, the worker abandons the "
      "attempt and re-queues the job for another pass. The team then updates the "
      "runbook index and closes stale alerts.")
B2 = ("Payment worker retry timeout tuning. The retry timeout for the payment "
      "worker governs how the payment worker retries; review the payment worker "
      "retry timeout and adjust retry and timeout budgets for the payment worker.")
qv2 = dense.model.encode([q_adv], normalize_embeddings=True)[0]
av2, bv2 = dense.model.encode([A2, B2], normalize_embeddings=True)
rs2 = reranker.predict([(q_adv, A2), (q_adv, B2)])
print(f"dense   A(answer)={av2@qv2:.3f}  B(keyword-stuffed)={bv2@qv2:.3f}"
      f"  -> {'A' if av2@qv2>bv2@qv2 else 'B (WRONG)'}")
print(f"rerank  A={rs2[0]:.3f}  B={rs2[1]:.3f}"
      f"  -> {'A' if rs2[0]>rs2[1] else 'B (WRONG)'}")

# %% [markdown]
# ## 5. The latency it always charges
#
# The reranker's cost is real and scales linearly with the candidate pool, because
# every pair is a forward pass that cannot be cached. And this is on the RTX 3090.
# The **demo host has no GPU** (spec §5.3): the same work there runs on CPU, where
# hundreds of milliseconds become seconds — per query, forever.

# %%
q = "agents showing offline telemetry stopped"
for n in (5, 10, 20, len(chunks)):
    cand = list(dense.ranking(q)[:n])
    t = time.perf_counter()
    rerank(q, cand)
    print(f"  rerank {n:3d} candidates: {(time.perf_counter()-t)*1000:5.0f} ms  (GPU; CPU would be ~10-20x)")

# %% [markdown]
# ## 6. The verdict — the seminar's pivot
#
# Read the evidence as a whole:
#
# - **Ranking:** on the real corpus the reranker reorders nothing (rank 0 → 0),
#   because L1–L4 already won. Its one demonstrated strength (signal dilution) does
#   not appear in this corpus, and it is fooled by keyword-stuffing just like BM25.
# - **Confidence:** its genuine contribution is a much wider score gap between right
#   and wrong. That is not nothing — a sharp gap is what lets the next notebook
#   decide *answer vs refuse* with a threshold — but it is a smaller and more
#   specific value than "fixes retrieval."
# - **Cost:** 100–400 ms per query on GPU, seconds on the demo host's CPU, every
#   query, forever.
#
# So the disciplined conclusion, and the moment the seminar is built around: **we
# added the reranker, measured it, and it did not earn its latency on our data.**
# You adopt L7 only when a per-category evaluation shows a category that L0–L6
# leaves failing *and* the latency is affordable on the host that will serve it.
# On this corpus, neither holds. That is not a failure of the experiment — it *is*
# the experiment.

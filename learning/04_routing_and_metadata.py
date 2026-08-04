# %% [markdown]
# # 04 — Structure-first: route the query, scope by metadata
#
# Notebooks 02 and 03 both ended at the same wall. Two problems that no better text
# matching solves:
#
# 1. **The hybrid dilution** — a Vietnamese query for an English document scored
#    rank 0 under dense alone but rank 9 under RRF hybrid, because BM25 voted
#    confidently and wrongly and RRF gave it an equal say.
# 2. **The look-alikes** — D08 (`SQ-2011`, collector) and D09 (`SQ-6008`, store)
#    open with a byte-identical symptom paragraph. Retrieval interleaves them
#    because the *text* really is the same.
#
# Both fixes are the same idea: use structure you already have — the shape of the
# query, and metadata about the documents — *before* reaching for a heavier model.
# This is the L4 rung, and it is cheaper and more reliable than anything above it.

# %%
import re
import numpy as np
from _shared import load_chunks, DenseIndex, BM25Index, rrf

docs, chunks = load_chunks()
dense = DenseIndex(chunks)
bm25 = BM25Index(chunks)      # both built in earlier notebooks, packaged in _shared

def rank_of(ranking, doc):
    for r, idx in enumerate(ranking):
        if chunks[idx]["doc"] == doc:
            return r
    return None

# %% [markdown]
# ## 1. Metadata is captured at ingest — it is not text to be searched
#
# Every document carries a manifest: which service it is about, its error codes,
# its severity. In a real pipeline this comes from document properties or a CMS at
# ingest time; here it comes from the source front matter (the rendered files strip
# it, so parsing stays measured on body text alone). The lesson embedded in that:
# **capture metadata at ingest** — catalog **F1.4** is what happens when you don't.

# %%
seen = set()
print(f"{'doc':8s} {'service':14s} {'codes':12s} {'sev':4s}")
for c in chunks:
    if c["doc"] in seen:
        continue
    seen.add(c["doc"])
    m = c["meta"]
    codes = ",".join(m.get("error_codes", []))
    print(f"{c['doc']:8s} {m.get('service',''):14s} {codes:12s} {m.get('severity',''):4s}")

# %% [markdown]
# ## 2. Metadata scoping — separating the look-alikes
#
# The query "agents showing offline, telemetry stopped" matches D08 and D09 almost
# equally, because their symptom text is identical by design. But an *alert* is not
# just prose — it names the component that raised it. Scope retrieval to that
# component's documents and the ambiguity vanishes. Same query, two different
# alerts, two correct and unambiguous runbooks.

# %%
def grouped(scores, mask=None, k=5):
    """Best chunk per base document (notebook 03), optionally within a metadata mask."""
    best = {}
    for i in np.argsort(-scores):
        if mask is not None and not mask[i]:
            continue
        d = chunks[i]["doc"]
        if d not in best:
            best[d] = i
    order = sorted(best.values(), key=lambda i: -scores[i])[:k]
    return [f"{chunks[i]['doc']}.{chunks[i]['lang']}" for i in order]

def service_mask(service):
    return np.array([c["meta"].get("service") == service for c in chunks])

q = "agents showing offline, telemetry stopped for some endpoints"
print(f"query: {q!r}\n")
print(f"  no scoping:              {grouped(dense.scores(q))}")
print(f"  alert from sq-collector: {grouped(dense.scores(q), service_mask('sq-collector'))}  -> D08")
print(f"  alert from sq-store:     {grouped(dense.scores(q), service_mask('sq-store'))}  -> D09")

# %% [markdown]
# ## 3. Query routing — a deterministic dispatcher
#
# Notebook 02 showed that fusing BM25 in *hurts* a cross-lingual query. The fix is
# not a cleverer fusion weight; it is to not fuse BM25 in when it cannot help.
#
# We route by the *shape* of the query, with a plain rule and no model: if it
# contains an exact identifier — an error code like `SQ-6008`, or a number like
# `50,000` — keyword matching is valuable, so use hybrid. Otherwise it is natural
# language, possibly in another language than the document, so use dense alone.
# A deterministic dispatcher like this is the spec's L4 preference over letting an
# agent decide at runtime.

# %%
def has_identifier(query):
    return bool(re.search(r"\b[A-Z]{2,}-\d+\b|\b\d{3,}\b", query))

def route(query):
    return "hybrid" if has_identifier(query) else "dense"

def retrieve(query):
    if route(query) == "hybrid":
        return rrf([dense.ranking(query), bm25.ranking(query)])
    return dense.ranking(query)

def blind_hybrid(query):
    return rrf([dense.ranking(query), bm25.ranking(query)])

# %% [markdown]
# ## 4. Measure — routing beats always-hybrid
#
# For each query, the rank of the correct document under the *routed* retriever,
# next to what a fixed always-hybrid pipeline would have given. Routing should hold
# rank 0 everywhere, including the cross-lingual query where blind hybrid collapsed
# to rank 9.

# %%
cases = [
    ("luật phát hiện không biên dịch được", "D11", "VI -> EN-only (cross-lingual)"),
    ("SQ-6008 shard unassigned",            "D09", "exact code"),
    ("50,000 events",                       "D08", "exact number"),
    ("agent offline not sending heartbeat", "D06", "plain natural language"),
]
print(f"{'case':32s} {'route':6s} {'routed':>6s} {'blind-hybrid':>13s}")
print("-" * 62)
for q, exp, note in cases:
    routed = rank_of(retrieve(q), exp)
    blind = rank_of(blind_hybrid(q), exp)
    print(f"{note:32s} {route(q):6s} {str(routed):>6s} {str(blind):>13s}")

# %% [markdown]
# ## 5. What structure bought
#
# - **Metadata scoping** separated two documents whose text is identical by
#   design. No model could have done this from the prose; the component that
#   raised the alert did it instantly.
# - **Query routing** recovered the cross-lingual rank 0 that blind hybrid threw
#   away — by *not* using a ranker that cannot help, rather than by adding one that
#   can.
#
# Both are deterministic, need no GPU, and run in microseconds. That is the point
# of the spec's ladder order: exhaust cheap structure before spending on a
# reranker. Two rungs still stand between here and reranking — a domain vocabulary
# map (L5), and trying a stronger embedder (L6) — and the whole thesis is that the
# reranker, when we finally reach it, may not beat what structure already bought.

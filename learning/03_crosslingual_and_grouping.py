# %% [markdown]
# # 03 — Cross-lingual retrieval done right: grouping + citation language
#
# Notebook 02 left two structure problems that no amount of better text matching
# solves. This notebook fixes the first family — the one about *results* — and
# leaves the second (routing the *query*) as the explicit next step.
#
# The corpus carries the same document in several languages. That is realistic
# (the real EDR docs are EN/VI/JA) and it breaks naive top-k in a specific way:
# ask about an agent going offline and all five result slots come back as
# translations and fragments of the *one* runbook, crowding out every other
# document. We measure that, fix it by grouping on document identity, then handle
# the requirement that makes this project unusual — the operator reads Vietnamese,
# but the best source may be in English.

# %%
import re
from collections import defaultdict
import numpy as np
from _shared import load_chunks, DenseIndex

docs, chunks = load_chunks()

# Each rendered file is `D06.vi` = base document id + language. Translations of one
# document share the base id — that shared id is exactly what lets us group them.
for c in chunks:
    c["doc"], c["lang"] = c["doc_id"].split(".")

available = defaultdict(set)
for c in chunks:
    available[c["doc"]].add(c["lang"])
print("document -> languages present in this corpus:")
for d, ls in sorted(available.items()):
    print(f"  {d}: {sorted(ls)}")

dense = DenseIndex(chunks)      # dense retrieval crosses languages; that is the point

# %% [markdown]
# ## 1. The flooding, measured
#
# Take the top-5 chunks for a few queries and count how many *distinct documents*
# they represent. A healthy result set shows the operator several different
# sources; a flooded one shows the same document five times in three languages.

# %%
def top_chunks(scores, k=5):
    return [chunks[i] for i in np.argsort(-scores)[:k]]

def distinct_docs(chunk_list):
    return len({c["doc"] for c in chunk_list})

print("distinct documents among the top-5 chunks:")
for q in [
    "agent offline not sending heartbeat",
    "how do I restart the agent",
    "agent shows offline on the console",
]:
    top = top_chunks(dense.scores(q))
    labels = [f"{c['doc']}.{c['lang']}" for c in top]
    print(f"  {distinct_docs(top)} distinct  {labels}")
    print(f"             <- {q!r}")

# %% [markdown]
# ## 2. Group on document identity, then take top-k
#
# The fix is one idea: rank chunks as before, then keep only the **best chunk per
# base document** before cutting to top-k. Each document appears once, so five
# slots means five different documents. This is a *result-set* transform — it costs
# nothing at query time and needs no model — and it is the L4 "structure-first"
# rung applied to what retrieval returns.

# %%
def grouped_docs(scores, k=5):
    """Best-scoring chunk per base document, then top-k documents."""
    best = {}
    for i in np.argsort(-scores):
        d = chunks[i]["doc"]
        if d not in best:                 # first time we see this doc = its best chunk
            best[d] = i
    order = sorted(best.values(), key=lambda i: -scores[i])[:k]
    return [chunks[i] for i in order]

print("top-5 BEFORE grouping vs AFTER, same query:")
q = "agent offline not sending heartbeat"
before = [f"{c['doc']}.{c['lang']}" for c in top_chunks(dense.scores(q))]
after = [f"{c['doc']}.{c['lang']}" for c in grouped_docs(dense.scores(q))]
print(f"  before ({distinct_docs(top_chunks(dense.scores(q)))} distinct): {before}")
print(f"  after  ({len(after)} distinct): {after}")

# %% [markdown]
# ## 3. Retrieval crosses languages; keyword search could not
#
# Recall from notebook 02 that a Vietnamese query for the English-only `D11` landed
# at BM25 rank 35 but dense rank 0. Grouping does not change that — it just makes
# the cross-lingual hit visible in a clean, de-duplicated result set. Ask in
# Vietnamese and watch an English document come back as a legitimate top result.

# %%
vq = "quy tắc phát hiện bị lỗi biên dịch"        # "the detection rule failed to compile"
grouped = grouped_docs(dense.scores(vq))
print(f"VI query: {vq!r}")
for rank, c in enumerate(grouped):
    snippet = re.sub(r"\s+", " ", c["text"]).strip()[:60]
    print(f"  {rank}  {c['doc']}.{c['lang']}  {snippet}")

# %% [markdown]
# ## 4. Citation language — the requirement almost no tutorial covers
#
# The operator reads Vietnamese. Retrieval ranged across all languages to *find*
# the answer, but the citation we hand back must be one they can read. Two cases,
# both real:
#
# - **A Vietnamese version exists** (`D06`): the English chunk may have scored
#   highest, but we surface the Vietnamese version of the same document.
# - **No Vietnamese version exists** (`D11`, English only — standing in for `D16`
#   in the full corpus): we cannot invent one. We cite the English source and
#   *flag* that no Vietnamese version exists, rather than silently handing over a
#   document the operator cannot read.

# %%
def cite_for_reader(scores, reader_lang="vi", k=3):
    """Group to documents, then choose each citation in the reader's language."""
    out = []
    for c in grouped_docs(scores, k):
        versions = available[c["doc"]]
        if reader_lang in versions:
            chosen, note = reader_lang, ""
        else:
            chosen, note = c["lang"], f"(no {reader_lang} version — cited in {c['lang']})"
        out.append((c["doc"], chosen, note))
    return out

print("citations for a Vietnamese-reading operator:\n")
for q in ["agent offline not sending heartbeat", "detection rule compilation failure"]:
    print(f"  query: {q!r}")
    for doc, lang, note in cite_for_reader(dense.scores(q)):
        print(f"    cite {doc}.{lang}  {note}")
    print()

# %% [markdown]
# ## 5. Where this leaves us
#
# - **Grouping on document identity** turns a result set that was one document in
#   five slots into five distinct documents — a free, query-time-cheap structure
#   fix (L4).
# - **Cross-lingual retrieval** means the Vietnamese operator's question reaches
#   the English runbook. Grouping keeps that hit visible instead of buried under
#   duplicate chunks.
# - **Citation language** is handled explicitly: cite in the reader's language when
#   we can, and flag the gap when we cannot — never hand over an unreadable source
#   as if it were an answer.
#
# Still open, carried from notebook 02: the RRF hybrid *hurt* the cross-lingual
# query (dense rank 0, hybrid rank 9) because BM25 voted confidently and wrongly.
# We fixed the results here; the fix for that one is to route the *query* — send a
# cross-lingual query to dense only. That is structure-first applied to the input,
# and it is the next rung.

# %% [markdown]
# # 06 — The product: answer, or escalate with evidence (L8)
#
# Everything so far produced a *ranked list*. NOC does not want a ranked list; it
# wants a decision. This notebook turns retrieval into the product the spec
# describes (§7): for each question, either **ANSWER** — hand over the playbook and
# the step, cited, in the operator's language — or **ESCALATE** — page the dev team
# with the evidence already gathered.
#
# The dangerous error is a **false answer**: confidently handing NOC a procedure
# from a knowledge base that does not actually cover their case. We prevent it
# structurally, and without an LLM, by gating on retrieval confidence *before*
# anything is answered. The generation model in the demo stack writes prose from an
# ANSWER packet — but it never sees a question we were not confident about, which is
# how "false answer" is designed out rather than prompted against.

# %%
import re
import numpy as np
from _shared import load_chunks, DenseIndex, BM25Index, rrf

docs, chunks = load_chunks()
dense = DenseIndex(chunks)
bm25 = BM25Index(chunks)
available = {c["doc"]: set() for c in chunks}
for c in chunks:
    available[c["doc"]].add(c["lang"])

# %% [markdown]
# ## 1. The confidence signal — absolute score, not the gap
#
# Notebooks 01 and 05 used the rank-1-minus-rank-2 *gap* as a confidence proxy.
# Measuring it against real answerable and unanswerable queries shows the gap is the
# wrong signal for *this* decision: the corpus has near-duplicate documents (three
# D06 translations, the D08/D09 look-alikes), so a genuinely answerable query can
# have a tiny gap simply because two good chunks are tied.
#
# The **absolute** top score separates the two cleanly — answerable queries land
# well above unanswerable ones — because it asks a different question: not "is rank
# 1 ahead of rank 2" (ambiguity) but "is anything here actually relevant"
# (answerability). We calibrate a threshold on that.

# %%
def top_score(query):
    s = dense.scores(query)
    return float(s.max())

print("answerable:")
for q in ["agent offline not sending heartbeat", "collector overloaded throttling",
          "store shard unassigned", "detection rule compile failure"]:
    print(f"  {top_score(q):.3f}  {q!r}")
print("unanswerable (not in the corpus):")
for q in ["how do I enable ARM Mac support for the agent",
          "what is the enterprise licensing price", "reset the billing portal password"]:
    print(f"  {top_score(q):.3f}  {q!r}")

THRESHOLD = 0.55      # calibrated on the split above; in production, tuned on the gold set
print(f"\nthreshold = {THRESHOLD}")

# %% [markdown]
# ## 2. Retrieval, assembled from the earlier rungs
#
# One function that composes what the previous notebooks built: route by query
# shape (L4), scope to the alert's component when we have one (L4), and group to
# distinct documents (L3). This is the pipeline the verdict sits on top of.

# %%
def has_identifier(q):
    return bool(re.search(r"\b[A-Z]{2,}-\d+\b|\b\d{3,}\b", q))

def retrieve(query, alert_service=None, k=5):
    scores = dense.scores(query)
    if has_identifier(query):                                  # route (L4)
        order = rrf([dense.ranking(query), bm25.ranking(query)])
    else:
        order = list(np.argsort(-scores))
    best = {}                                                  # group to distinct docs (L3)
    for i in order:
        if alert_service and chunks[i]["meta"].get("service") != alert_service:
            continue                                           # scope (L4)
        d = chunks[i]["doc"]
        best.setdefault(d, i)
    ranked = sorted(best.values(), key=lambda i: -scores[i])[:k]
    return ranked, scores

# %% [markdown]
# ## 3. The verdict — answer, or escalate with evidence
#
# The decision, in plain rules:
# - **Below the confidence threshold** → ESCALATE. Nothing in the KB is clearly
#   relevant; say so and hand over what was searched. This is the anti-false-answer
#   gate.
# - **Severity at or above P1** → ESCALATE even if we are confident. A P1 is a
#   detection blind; the severity gate (spec §7.2) never lets deflection cost an
#   outage. The evidence still goes along, so the engineer starts informed.
# - **Otherwise** → ANSWER: cite the best document, in the reader's language,
#   pointing at the section to follow.

# %%
def cite_language(doc, reader_lang="vi"):
    langs = available[doc]
    if reader_lang in langs:
        return reader_lang, ""
    lang = "en" if "en" in langs else sorted(langs)[0]
    return lang, f"(no {reader_lang} version; cited in {lang})"

def verdict(query, alert_service=None, reader_lang="vi"):
    ranked, scores = retrieve(query, alert_service)
    if not ranked or scores[ranked[0]] < THRESHOLD:
        return {"decision": "ESCALATE", "reason": "no confident source in the KB",
                "evidence": [chunks[i]["doc"] for i in ranked[:3]]}
    top = chunks[ranked[0]]
    severity = top["meta"].get("severity", "P3")
    if severity in ("P1",):
        return {"decision": "ESCALATE", "reason": f"severity {severity} gate",
                "evidence": [chunks[i]["doc"] for i in ranked[:3]], "severity": severity}
    lang, note = cite_language(top["doc"], reader_lang)
    return {"decision": "ANSWER", "cite": f"{top['doc']}.{lang}", "note": note,
            "severity": severity, "score": round(float(scores[ranked[0]]), 3)}

# %% [markdown]
# ## 4. The four cases the product must get right
#
# 1. **Answerable, low severity** → ANSWER, cited in Vietnamese.
# 2. **Unanswerable** → ESCALATE, *not* a confident wrong answer.
# 3. **P1 severity, even though answerable** → ESCALATE (the gate holds).
# 4. **Alert-scoped look-alike** → the metadata picks the right runbook (nb 04),
#    then the verdict answers on it.

# %%
def show(label, v):
    print(f"{label}")
    for k, val in v.items():
        print(f"    {k}: {val}")
    print()

show("1. answerable, P3:  'agent offline, not sending heartbeat'",
     verdict("agent offline not sending heartbeat"))
show("2. unanswerable:    'how do I enable ARM Mac support for the agent'",
     verdict("how do I enable ARM Mac support for the agent"))
show("3. P1 gate:         SQ-6008 alert from sq-store  'store shard unassigned'",
     verdict("store shard unassigned", alert_service="sq-store"))
show("4. scoped look-alike: SQ-2011 alert from sq-collector  'agents offline'",
     verdict("agents showing offline telemetry stopped", alert_service="sq-collector"))

# %% [markdown]
# ## 5. Why the gate matters — the false answer it prevents
#
# The whole product turns on case 2. A naive pipeline that always returns its top
# result would hand the ARM-Mac question a confident-looking citation to D06 — a
# real runbook, utterly unrelated to the question. That is a false answer, and to a
# NOC operator at 3 a.m. it is worse than no system at all: it burns the trust the
# whole thing depends on. Compare the two behaviours directly.

# %%
q = "how do I enable ARM Mac support for the agent"
naive_top = chunks[int(np.argmax(dense.scores(q)))]
print(f"query: {q!r}")
print(f"  naive 'always answer':  cite {naive_top['doc']}  (score {top_score(q):.3f}) "
      f"<- confidently WRONG, a false answer")
print(f"  gated verdict:          {verdict(q)['decision']}  "
      f"<- refuses, escalates, preserves trust")

# %% [markdown]
# ## 6. Where this leaves Path A
#
# The learning track now spans the ladder end to end, each rung climbed only when
# the one below was shown to fail, every claim measured on the 3090:
#
# - L1–L3 keyword, dense, hybrid, and the fusion that *hurt* until we routed it
# - L4 structure-first routing and metadata scoping — the cheap rungs that did the
#   heavy lifting
# - L7 the reranker, added, measured, and set aside for not earning its latency
# - L8 the answer/escalate verdict with a confidence gate that designs out the false
#   answer, and a severity gate that never trades an outage for a deflection
#
# What is deliberately *not* here: the generation model (the demo stack's job; it
# writes prose from an ANSWER packet it is only ever handed when we are confident),
# the vocabulary map (L5, needs the ticket corpus), the embedding head-to-head (L6,
# needs the hosted Qwen model), and the parsing ladder (P0–P4, needs the PDF/scan
# corpus). Each is noted where it belongs, to be built when its inputs exist —
# never guessed.

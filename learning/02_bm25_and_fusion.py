# %% [markdown]
# # 02 — BM25 keyword search + RRF fusion, from scratch
#
# Notebook 01 ended on a wobble: dense retrieval put an unrelated document at
# rank 2 for the query `SQ-2011`, with a score gap of 0.012. An exact identifier
# is a *string*, not a concept — there is nothing for it to be semantically
# similar to — so dense retrieval blurs it into the surrounding meaning.
#
# Keyword search has the opposite shape. We build BM25 by hand and find that on
# this small corpus it usually agrees with dense on *which* document — but it is
# dramatically more **confident** about exact tokens, and it **cannot cross
# languages** at all. Those two facts are the whole argument for running both and
# fusing them, which we then do with RRF.
#
# A discipline note up front: this corpus is seven documents. On something this
# small and topically clean, most methods find the right document at rank 0, so we
# will not manufacture a dramatic rescue that the data does not support. We look
# for where the methods *genuinely* diverge, and measure it.

# %%
import re
import math
from collections import Counter, defaultdict
import numpy as np
from _shared import load_chunks, DenseIndex

docs, chunks = load_chunks()
print(f"{len(chunks)} chunks from {len(docs)} documents")

# %% [markdown]
# ## 1. Tokenize — from scratch, and multilingual by necessity
#
# BM25 works on tokens. The corpus is Vietnamese, English and Japanese, and a
# tokenizer that assumes English silently corrupts the other two — an earlier
# draft of this notebook used `[a-z0-9]+` and BM25 promptly ranked a *Japanese*
# document top for `SQ-2011`, because that document tokenized to almost nothing
# and BM25's length normalization then inflated its one match.
#
# Two rules fix it:
# - **CJK** (Japanese/Chinese) has no spaces between words, so we treat each CJK
#   character as its own token — the standard first approximation for IR.
# - Everything else uses Unicode word matching, so Vietnamese diacritics stay
#   attached (`quá`, `tải`) instead of shattering the word.
#
# One honest limit remains: this still splits Vietnamese at *syllable* spaces, not
# *word* boundaries. Real word segmentation (pyvi / underthesea) is catalog **F4.2**
# and we defer it until it actually costs a result.

# %%
CJK = r"぀-ヿ一-鿿"          # hiragana, katakana, common kanji

def tokenize(text):
    text = re.sub(rf"([{CJK}])", r" \1 ", text.lower())     # isolate CJK chars
    return re.findall(r"\w+(?:-\w+)*", text, re.UNICODE)     # \w keeps Vietnamese diacritics

print(tokenize("Alert SQ-2011: collector quá tải; エージェント offline."))

# %% [markdown]
# ## 2. BM25 — from scratch
#
# BM25 scores a document on three ideas, all visible in the formula:
#
# 1. **Term frequency**, with diminishing returns (`k1`): the tenth "collector"
#    barely beats the ninth.
# 2. **Inverse document frequency**: a term in few documents is informative.
#    `sq-2011` is in one document, `the` in all — IDF makes the rare term dominate.
# 3. **Length normalization** (`b`): a long document has more chances to contain a
#    term by luck, so its matches are discounted.

# %%
class BM25:
    def __init__(self, corpus_tokens, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.N = len(corpus_tokens)
        self.tf = [Counter(toks) for toks in corpus_tokens]
        self.len = np.array([len(toks) for toks in corpus_tokens])
        self.avgdl = self.len.mean()
        df = Counter()
        for toks in corpus_tokens:
            df.update(set(toks))
        self.idf = {t: math.log(1 + (self.N - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def scores(self, query):
        q = tokenize(query)
        out = np.zeros(self.N)
        for i in range(self.N):
            tf, dl = self.tf[i], self.len[i]
            s = 0.0
            for term in q:
                f = tf.get(term, 0)
                if f:
                    s += self.idf.get(term, 0.0) * (f * (self.k1 + 1)) / (
                        f + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                    )
            out[i] = s
        return out

    def ranking(self, query):
        return list(np.argsort(-self.scores(query)))

bm25 = BM25([tokenize(c["text"]) for c in chunks])
dense = DenseIndex(chunks)          # notebook 01, packaged

def show(title, scores, k=4):
    order = np.argsort(-scores)
    gap = scores[order[0]] - scores[order[1]]
    print(f"\n{title}   (top-1 minus top-2 gap: {gap:.3f})")
    print("-" * 72)
    for idx in order[:k]:
        snippet = re.sub(r"\s+", " ", chunks[idx]["text"]).strip()[:64]
        print(f"  {scores[idx]:7.3f}  {chunks[idx]['doc_id']:8s}  {snippet}")

# %% [markdown]
# ## 3. BM25's strength — exact tokens, with confidence
#
# The corpus contains a planted trap: `D08.vi` is the stale v3.8 runbook whose
# throttle threshold is **10,000** events, while `D08.en` is current at **50,000**.
# Ask for each number.
#
# Watch two things. First, BM25 routes each number to the *correct language
# version* — `50,000` to the English doc, `10.000` to the Vietnamese one — because
# it matches the literal token. Dense retrieval cannot: a bare number carries no
# meaning to embed, so it is near-tied (gap ≈ 0.00) and picks the wrong version.
# Second, look at the size of BM25's confidence gap versus dense's. That gap is not
# cosmetic — a retriever that is *sure* can be trusted to answer; one that is
# guessing (gap 0.000) should refuse. We build exactly that decision in notebook 05.

# %%
show("DENSE   '50,000 events'", dense.scores("50,000 events"))
show("BM25    '50,000 events'", bm25.scores("50,000 events"))
show("DENSE   '10.000 event'",  dense.scores("10.000 event"))
show("BM25    '10.000 event'",  bm25.scores("10.000 event"))

# %% [markdown]
# ## 4. BM25's blind spot — it cannot cross languages
#
# `D11` (detection-rule compilation failure) exists only in English. Ask about it
# in Vietnamese — *"luật phát hiện không biên dịch được"* — which shares not one
# token with the English document. BM25 has nothing to match and buries the correct
# document near the bottom of all 42 chunks. Dense retrieval, matching on meaning
# across languages, puts it at rank 0.
#
# This is the single most important capability in the whole project — a Vietnamese
# operator finding an English runbook — and keyword search simply cannot do it.

# %%
def rank_of(ranking, doc_prefix):
    for r, idx in enumerate(ranking):
        if chunks[idx]["doc_id"].split(".")[0] == doc_prefix:
            return r
    return None

vq = "luật phát hiện không biên dịch được"      # "the detection rule won't compile"
print(f"VI query -> EN-only doc D11: {vq!r}")
print(f"  dense ranks D11 at:  {rank_of(dense.ranking(vq), 'D11')}")
print(f"  bm25  ranks D11 at:  {rank_of(bm25.ranking(vq), 'D11')}   (of {len(chunks)} chunks)")

# %% [markdown]
# ## 5. RRF — fusing two rankings on incomparable scales, from scratch
#
# Dense scores live near 0–1; BM25 is unbounded (we just saw a 5-point gap).
# Averaging the raw numbers lets whichever is larger dominate — catalog **F4.6**.
# Reciprocal Rank Fusion throws the scores away and keeps only the *rank*: each
# ranker contributes `1 / (k + rank)`, with `k = 60` so rank 1 does not utterly
# swamp rank 2. A document both rankers like accumulates from both; a document only
# one ranker found can still surface — which is what we want, since each ranker is
# the only one that works for its kind of query.

# %%
def rrf(rankings, k=60):
    fused = defaultdict(float)
    for ranking in rankings:
        for rank, idx in enumerate(ranking):
            fused[idx] += 1.0 / (k + rank)
    return sorted(fused, key=fused.get, reverse=True)

def hybrid_ranking(query):
    return rrf([dense.ranking(query), bm25.ranking(query)])

# %% [markdown]
# ## 6. Measure — and let it correct you
#
# Not "does it look better" — *measure*. For a set of (query, correct-document)
# pairs, report the rank at which each method places the correct document. Lower is
# better; rank 0 is a hit. This is a miniature of the eval harness, and the habit
# the whole project runs on: never adopt a rung on vibes.
#
# Watch the cross-lingual row. It is about to contradict the "hybrid is never
# worse" story that every tutorial tells — which is the entire reason we measure
# instead of assert.

# %%
cases = [
    ("agent offline, not sending heartbeat",        "D06", "plain EN"),
    ("50,000 events",                               "D08", "exact number (EN version)"),
    ("SQ-6008 shard unassigned",                    "D09", "exact code"),
    ("luật phát hiện không biên dịch được",         "D11", "VI -> EN-only (cross-lingual)"),
    ("làm sao gia hạn certificate cho agent",       "D06", "VI, cert cross-ref"),
]
print(f"{'case':32s} {'exp':4s} {'dense':>5s} {'bm25':>5s} {'hybrid':>6s}")
print("-" * 60)
for q, exp, note in cases:
    d = rank_of(dense.ranking(q), exp)
    b = rank_of(bm25.ranking(q), exp)
    h = rank_of(hybrid_ranking(q), exp)
    g = lambda x: "-" if x is None else str(x)
    print(f"{note:32s} {exp:4s} {g(d):>5s} {g(b):>5s} {g(h):>6s}")

# %% [markdown]
# ## 7. What the measurement actually said
#
# Read the table honestly:
#
# - On same-language queries every method scores rank 0. On a seven-document,
#   topically-clean corpus the baseline already wins, so hybrid adds nothing here.
#   That is not a failure — it is catalog **F0.3**: a rung earns credit only where
#   the level below it fails.
# - On the **cross-lingual** query, dense scores rank 0 and hybrid scores rank
#   **9** — hybrid is *worse than dense alone*. RRF weighted BM25's confidently
#   wrong ranking (the correct doc at 35) equally with dense's correct one, and
#   BM25's wrong-but-confident top results outscored the right answer.
#
# So the tutorial claim "hybrid is never worse" is false, and we only know because
# we measured. **Equal-weight fusion assumes both rankers are worth listening to.**
# When one ranker is structurally blind to a query type — BM25 to cross-language —
# fusing it in *dilutes* a win the other ranker already had.
#
# The fix is not a better fusion constant. It is to stop sending cross-lingual
# queries through BM25 at all — to *route* by query shape. That is the L4
# structure-first rung, and this failure is exactly why it exists. We do not paper
# over it here; we let it stand as the reason to climb.
#
# ### Take away
# - **Dense** owns meaning and crosses languages; **BM25** owns exact tokens with
#   far more confidence. They fail in opposite places.
# - **Hybrid (RRF)** is the right default for a *single-language* mix of exact and
#   semantic queries — the L3 rung — but it is not a free lunch, and the
#   cross-lingual case proves it.
# - Also still unsolved: telling near-identical D08 (`SQ-2011`) and D09 (`SQ-6008`)
#   apart. Text matching cannot; that needs metadata about which component owns the
#   fault. Both open problems point at the same next rung — **structure before more
#   matching.**

# %% [markdown]
# # 01 — Naive dense retrieval, from scratch
#
# The whole RAG retrieval loop in ~60 lines of real code and no framework:
#
#     documents -> chunks -> embeddings -> cosine search -> ranked results
#
# We build the chunker and the search by hand. We only *buy* the embedding model,
# because reimplementing a transformer is not the lesson. By the end you will have
# seen dense retrieval work on a paraphrased question, and wobble on an exact
# error code — which is exactly what motivates notebook 02 (keyword search).
#
# Reads `corpus/rendered/` (the messy binaries the real pipeline sees), same as
# production would. For this first notebook we use only the already-clean
# markdown renders; parsing the PDFs and scans is a later notebook.

# %%
from pathlib import Path
import re
import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
RENDERED = ROOT / "corpus" / "rendered"

# %% [markdown]
# ## 1. Load documents
#
# Only the `.md` renders for now — the clean case. A real corpus is mostly not
# this clean, which is the entire point of the parsing ladder, but starting here
# keeps the first lesson about *retrieval* rather than *extraction*.

# %%
docs = []
for path in sorted(RENDERED.glob("*.md")):
    text = path.read_text(encoding="utf-8")
    docs.append({"id": path.stem, "text": text})       # e.g. id="D06.vi"

print(f"loaded {len(docs)} documents:")
for d in docs:
    print(f"  {d['id']:10s}  {len(d['text']):5d} chars")

# %% [markdown]
# ## 2. Chunk — fixed-size, deliberately naive
#
# The simplest thing that could work: slide a fixed-width window over the
# characters with a little overlap. It is naive on purpose. Watch where it splits
# — it will cut through the middle of sentences and tables, because it has no idea
# what a sentence or a table is. That is catalog failure **F2.1**, and we will
# feel it before we fix it.

# %%
def chunk_fixed(text, size=500, overlap=80):
    """Slice text into overlapping fixed-width windows. No structure awareness."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap                 # step back by `overlap` each time
    return chunks

chunks = []          # flat list of {doc_id, text}
for d in docs:
    for piece in chunk_fixed(d["text"]):
        chunks.append({"doc_id": d["id"], "text": piece})

print(f"{len(chunks)} chunks from {len(docs)} documents\n")
print("--- example chunk boundary (note the mid-sentence cut) ---")
print(repr(chunks[3]["text"][-120:]))
print(repr(chunks[4]["text"][:120]))

# %% [markdown]
# ## 3. Embed — buy the model, on the GPU
#
# `bge-m3` maps each chunk to a 1024-dim vector where *distance ≈ meaning*. It is
# multilingual, which the corpus (VI/EN/JA) requires. First run downloads ~2.2 GB.

# %%
model = SentenceTransformer("BAAI/bge-m3", device="cuda")
print("device:", model.device)

chunk_texts = [c["text"] for c in chunks]
# normalize_embeddings=True makes each vector unit-length, so a dot product IS
# the cosine similarity — one less thing to get wrong by hand in step 4.
embeddings = model.encode(
    chunk_texts, normalize_embeddings=True, show_progress_bar=True
)
print("embeddings:", embeddings.shape)         # (n_chunks, 1024)

# %% [markdown]
# ## 4. Cosine search — from scratch
#
# With unit-length vectors, similarity is just a dot product. Ranking all chunks
# for a query is one matrix-vector multiply. No vector database needed at this
# scale — that comes when the corpus is too big to hold in RAM, not before.

# %%
def search(query, k=5):
    q = model.encode([query], normalize_embeddings=True)[0]   # (1024,)
    scores = embeddings @ q                                   # (n_chunks,)
    top = np.argsort(-scores)[:k]
    return [(float(scores[i]), chunks[i]["doc_id"], chunks[i]["text"]) for i in top]

def show(query, k=5):
    print(f"\nQUERY: {query}")
    print("-" * 70)
    for score, doc_id, text in search(query, k):
        snippet = re.sub(r"\s+", " ", text).strip()[:90]
        print(f"  {score:.3f}  {doc_id:10s}  {snippet}")

# %% [markdown]
# ## 5. The win — a paraphrased question
#
# The user does not type the words the document uses. They describe the *problem*.
# Dense retrieval is built for exactly this: no shared keywords required, only
# shared meaning. This should land on D06 (agent offline).

# %%
show("my machine dropped off the console and won't report in")

# %% [markdown]
# ## 6. The wobble — an exact error code
#
# Now ask for a specific identifier. `SQ-2011` is a *string*, not a concept —
# there is nothing to be semantically similar to. Dense retrieval flattens it into
# the surrounding meaning, so D08 (the SQ-2011 runbook) and D09 (SQ-6008, the
# near-identical-symptom sibling) score almost the same. Look at how close the top
# scores are, and whether the right document is even on top.
#
# This is catalog failure **F4.1**, and it is why notebook 02 builds keyword
# search: BM25 matches `SQ-2011` as a literal token, which is precisely what dense
# retrieval cannot do.

# %%
show("SQ-2011")
show("collector back-pressure, agents being throttled")   # the concept behind it

# %% [markdown]
# ## 7. A note you can already act on
#
# Print the score *gap* between rank 1 and rank 2. A confident retrieval has a
# clear gap; a wobbly one is nearly tied. This single number is the seed of the
# "should I answer or refuse?" decision in notebook 05 — you cannot ground an
# answer on a result the retriever itself is unsure about.

# %%
for q in ["my machine dropped off the console and won't report in", "SQ-2011"]:
    res = search(q, k=2)
    gap = res[0][0] - res[1][0]
    print(f"gap {gap:.3f}  (rank1={res[0][0]:.3f} {res[0][1]}, "
          f"rank2={res[1][0]:.3f} {res[1][1]})   {q!r}")

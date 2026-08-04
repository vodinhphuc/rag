# %% [markdown]
# # 08 — The parsing ladder: the document that isn't there
#
# Every notebook so far read the clean markdown renders. The real corpus is not
# clean — it is PDFs, scanned pages, DOCX. Before any retrieval rung can run, text
# has to come *out* of those files, and that is where the most dangerous failure in
# the whole system lives: not a wrong answer, but a **silent** one. A scanned
# document is indexed, looks fine, and contains zero retrievable text. Nobody gets
# an error. The document simply cannot be found, forever.
#
# This is the seminar's opening demo, and it is the parsing half of the spec's two
# ladders (P0–P4) — paid once at ingest, before any query-time work. We climb it far
# enough to make the failure visible and then repair it, and — because the corpus
# was authored in markdown and only *rendered* to these binaries — we can measure
# exactly how much text each rung recovers against the source that produced it.

# %%
import re
import time
import fitz          # pymupdf
import numpy as np

SCANNED = "corpus/rendered/D07.vi.pdf"       # a runbook rendered as a scanned page
DIGITAL = "corpus/rendered/D12.vi.pdf"       # a normal, digital-born PDF
SOURCE = "corpus/source/D07.vi.md"           # ground truth, never indexed

# %% [markdown]
# ## 1. P0 — naive text extraction, and the silent failure
#
# The simplest thing: ask the PDF library for its text. On a digital PDF this is
# perfect and free. On the scanned one it returns **nothing** — the page is an
# image, there is no text layer to read — and crucially it does not raise. A
# pipeline that trusts P0 would index D07 as an empty document and never know.

# %%
def p0_extract(path):
    return "".join(page.get_text() for page in fitz.open(path))

digital = p0_extract(DIGITAL)
scanned = p0_extract(SCANNED)
print(f"P0 on a digital PDF  (D12): {len(digital.strip()):5d} chars  <- fine")
print(f"P0 on the scanned PDF (D07): {len(scanned.strip()):5d} chars  <- SILENTLY empty")
print("\nThe failure is format-specific and invisible. Same code, same 'success',")
print("one document quietly unreachable. This is catalog F1.6, and demo block 1.")

# %% [markdown]
# ## 2. Measurement — why we can score parsing at all
#
# The corpus was authored in markdown, then rendered to these binaries (see
# `scripts/render_corpus.sh`). The markdown is held back and never indexed. That
# gap is the whole point: extracted text can be diffed against the exact source
# that produced it. We score with Normalized Edit Distance — the fraction of
# characters you would have to change to turn one string into the other — built
# from scratch below. Recovery = 1 − NED.

# %%
def norm(s):
    return re.sub(r"\s+", " ", s.lower()).strip()

def ned(a, b):
    a, b = norm(a), norm(b)
    m, n = len(a), len(b)
    if not m or not n:
        return 1.0
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        for j in range(1, n + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] != b[j - 1]))
        prev = cur
    return prev[n] / max(m, n)

source = re.sub(r"^---.*?---", "", open(SOURCE, encoding="utf-8").read(), flags=re.DOTALL).strip()
print(f"P0 recovery of D07 vs source: {1 - ned(scanned, source):.0%}")
print("Zero. The document is present in the index and absent from reality.")

# %% [markdown]
# ## 3. P3 — OCR, and the repair
#
# We skip past P1 (layout/reading order) and P2 (tables) — which the digital PDFs
# do not need — straight to the rung the scanned page demands: optical character
# recognition. Render each page to an image and read the characters back. This is
# ingest-time work, paid once per document; the cost is a few seconds on the GPU.

# %%
import easyocr
reader = easyocr.Reader(["vi", "en"], gpu=True, verbose=False)   # multilingual, the corpus is VI/EN

def p3_ocr(path):
    parts = []
    for page in fitz.open(path):
        pix = page.get_pixmap(dpi=200)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img = img[:, :, :3]
        parts.append("\n".join(reader.readtext(img, detail=0, paragraph=True)))
    return "\n".join(parts)

t = time.perf_counter()
recovered = p3_ocr(SCANNED)
dt = time.perf_counter() - t
print(f"P3 OCR: {len(recovered.strip())} chars in {dt:.1f}s")
print(f"P3 recovery vs source: {1 - ned(recovered, source):.0%}\n")
print("The facts that only D07 carries — and that were unreachable at P0 — survive:")
for fact in ["7443", "90 ngày", "sentriqctl cert renew", "certificate expired"]:
    print(f"   {fact!r:26s} recovered: {fact.lower() in recovered.lower()}")

# %% [markdown]
# ## 4. The payoff — the document becomes retrievable
#
# A parsing rung is not an end in itself; it exists so retrieval can reach the
# content. Build a dense index over the clean markdown corpus, and ask a question
# only D07 answers — how to renew an expired agent certificate. It is not there.
# Add the OCR'd D07 and ask again: now it is the top hit. Parsing is what put it
# within reach of every rung we built in notebooks 01–07.

# %%
from _shared import load_chunks, chunk_fixed, DenseIndex

_, base_chunks = load_chunks()                       # the 7 markdown docs, no D07
with_ocr = base_chunks + [
    {"doc_id": "D07.vi", "doc": "D07", "lang": "vi", "text": piece,
     "meta": {"service": "sq-agent", "error_codes": ["SQ-1017"], "severity": "P2"}}
    for piece in chunk_fixed(recovered)
]

q = "làm sao gia hạn certificate đã hết hạn cho agent"      # answerable only from D07
before = DenseIndex(base_chunks)
after = DenseIndex(with_ocr)

def top(index, chunks):
    i = int(np.argmax(index.scores(q)))
    return chunks[i]["doc"], float(index.scores(q)[i])

db, sb = top(before, base_chunks)
da, sa = top(after, with_ocr)
print(f"query: {q!r}\n")
print(f"  before OCR — top hit: {db}  ({sb:.3f})   <- D07 not in the index, wrong doc")
print(f"  after  OCR — top hit: {da}  ({sa:.3f})   <- the OCR'd D07, now reachable")

# %% [markdown]
# ## 5. What the ladder cost, and what is deferred
#
# - **P0** is free and correct on digital PDFs — and silently empty on scans. The
#   lesson is not "P0 is bad"; it is "a silent failure needs a *check*", which is
#   the recovery measurement above. Any document that extracts to near-nothing must
#   be flagged, not trusted.
# - **P3** recovered ~92% of a deliberately-degraded Vietnamese scan in ~2 s on the
#   GPU, ingest-time, once. The missing ~8% is real — OCR is not lossless — which is
#   exactly why we measure it rather than assume.
#
# Deferred, each waiting on its input:
# - **P1** layout / reading order — needs the two-column D01 to show columns
#   interleaving; the digital PDFs here do not exercise it.
# - **P2** table structure — needs the table-bearing D03/D05; the DOCX D10 has one
#   to start from.
# - **P4** figure captioning — needs a vision model (the hosted, vision-capable
#   Qwen on the demo host; spec §5.3), to turn diagrams and screenshots into
#   searchable text.
#
# With P3 in place the scanned runbook is no longer a hole in the corpus, and demo
# block 1 has both halves: the silent failure, and the measured repair.

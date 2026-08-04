"""Packaged version of what notebook 01 built by hand.

Notebook 01 explains loading, fixed-size chunking and cosine search in full.
From notebook 02 on, that part is setup rather than the lesson, so it lives here
and gets imported. Nothing new is hidden — every line here appears, explained, in
notebook 01.
"""
import re
import math
from pathlib import Path
from collections import Counter
import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
RENDERED = ROOT / "corpus" / "rendered"
SOURCE = ROOT / "corpus" / "source"


def read_front_matter(path):
    """Parse the flat YAML front matter as a metadata manifest.

    In a real pipeline, metadata (service, severity, error codes) is captured at
    ingest from document properties or a CMS — it is NOT free text to be searched.
    Our rendered files deliberately strip the front matter (parsing is measured on
    body text alone), so we read the metadata from the source file that produced
    each render. Content still comes only from `rendered/`; this is the manifest.
    """
    if not path.exists():
        return {}
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    meta = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line or line.startswith(" "):
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if val.startswith("[") and val.endswith("]"):
            val = [v.strip().strip('"') for v in val[1:-1].split(",") if v.strip()]
        else:
            val = val.strip('"')
        meta[key] = val
    return meta


def chunk_fixed(text, size=500, overlap=80):
    """Naive fixed-width windows with overlap. Structure-unaware on purpose."""
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks


def load_chunks():
    """Load the clean markdown renders, chunk them, attach the metadata manifest.

    Each chunk is {doc_id, doc, lang, text, meta}:
      doc_id  full source id, e.g. "D06.vi"
      doc     base document id shared across translations, e.g. "D06"
      lang    "en" | "vi" | "ja"
      meta    front-matter manifest (service, error_codes, severity, version, ...)
    """
    docs, chunks = [], []
    for path in sorted(RENDERED.glob("*.md")):
        stem = path.stem                       # "D06.vi"
        base, lang = stem.split(".")
        meta = read_front_matter(SOURCE / f"{stem}.md")
        text = path.read_text(encoding="utf-8")
        docs.append({"id": stem, "doc": base, "lang": lang, "text": text, "meta": meta})
        for piece in chunk_fixed(text):
            chunks.append({"doc_id": stem, "doc": base, "lang": lang,
                           "text": piece, "meta": meta})
    return docs, chunks


class DenseIndex:
    """Cosine search over normalized bge-m3 embeddings (notebook 01, packaged)."""

    def __init__(self, chunks, model_name="BAAI/bge-m3", device="cuda"):
        self.chunks = chunks
        self.model = SentenceTransformer(model_name, device=device)
        self.emb = self.model.encode(
            [c["text"] for c in chunks], normalize_embeddings=True
        )

    def scores(self, query):
        q = self.model.encode([query], normalize_embeddings=True)[0]
        return self.emb @ q                      # unit vectors -> dot product = cosine

    def ranking(self, query):
        """Chunk indices, best first."""
        return list(np.argsort(-self.scores(query)))


# BM25 keyword search (notebook 02, packaged). Multilingual tokenizer: CJK
# characters as individual tokens, Vietnamese diacritics preserved via unicode \w.
_CJK = r"぀-ヿ一-鿿"


def tokenize(text):
    text = re.sub(rf"([{_CJK}])", r" \1 ", text.lower())
    return re.findall(r"\w+(?:-\w+)*", text, re.UNICODE)


class BM25Index:
    def __init__(self, chunks, k1=1.5, b=0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        corpus = [tokenize(c["text"]) for c in chunks]
        self.N = len(corpus)
        self.tf = [Counter(toks) for toks in corpus]
        self.len = np.array([len(toks) for toks in corpus])
        self.avgdl = self.len.mean()
        df = Counter()
        for toks in corpus:
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


def rrf(rankings, k=60):
    """Reciprocal Rank Fusion (notebook 02). Returns fused chunk indices."""
    from collections import defaultdict
    fused = defaultdict(float)
    for ranking in rankings:
        for rank, idx in enumerate(ranking):
            fused[idx] += 1.0 / (k + rank)
    return sorted(fused, key=fused.get, reverse=True)

"""Packaged version of what notebook 01 built by hand.

Notebook 01 explains loading, fixed-size chunking and cosine search in full.
From notebook 02 on, that part is setup rather than the lesson, so it lives here
and gets imported. Nothing new is hidden — every line here appears, explained, in
notebook 01.
"""
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
RENDERED = ROOT / "corpus" / "rendered"


def chunk_fixed(text, size=500, overlap=80):
    """Naive fixed-width windows with overlap. Structure-unaware on purpose."""
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks


def load_chunks():
    """Load the clean markdown renders and chunk them.

    Returns (docs, chunks) where chunks is a flat list of {doc_id, text}.
    """
    docs, chunks = [], []
    for path in sorted(RENDERED.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        docs.append({"id": path.stem, "text": text})
        for piece in chunk_fixed(text):
            chunks.append({"doc_id": path.stem, "text": piece})
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

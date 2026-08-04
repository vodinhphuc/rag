"""Parsing quality: how much of each document survived rendering + extraction.

This is only possible because the corpus was authored in markdown and the source
is held back (spec section 6.1). For every rendered document we extract text the
way ingestion does, then score it against the source that produced it with
Normalized Edit Distance. Recovery = 1 - NED.

    uv run python eval/parsing.py

Low recovery is not always a bug — an xlsx render deliberately keeps only tables,
so a doc with lots of prose scores low there. The point is to make the loss
*visible* rather than silent, which is exactly the failure a scanned page causes
(0% recovery, caught here rather than three rungs later in retrieval).
"""
import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "learning"))
sys.path.insert(0, str(ROOT / "eval"))
from ingest import _extract, RENDERED, SOURCE     # noqa: E402


def norm(s):
    """Normalize away markup so we compare CONTENT, not formatting.

    NED against raw markdown otherwise penalizes a docx for losing '##' and '|',
    which is not content loss. We strip markdown syntax and table/extraction
    punctuation from both sides so a low score means missing text, not reformatted
    text — which is what 'did parsing lose anything' actually asks.
    """
    s = s.lower()
    s = re.sub(r"[#*`>|]", " ", s)           # headers, bold, code, quotes, table pipes
    s = re.sub(r"[-–—:]+", " ", s)           # list/table rules, separators
    s = re.sub(r"\s+", " ", s)
    return s.strip()


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


def source_body(doc_lang):
    p = SOURCE / f"{doc_lang}.md"
    if not p.exists():
        return None
    return re.sub(r"^---.*?---", "", p.read_text(encoding="utf-8"), flags=re.DOTALL).strip()


# group rendered files by base doc (concatenate multi-sheet, like ingest)
groups = {}
for path in sorted(RENDERED.glob("*.*")):
    stem = path.name.rsplit(".", 1)[0]
    base = stem.split(".sheet")[0]
    groups.setdefault(base, []).append(path)

print("parsing recovery vs source (1 - NED), by document:\n")
print(f"{'doc':10s} {'fmt':6s} {'recovery':>9s}  notes")
print("-" * 60)
rows = []
for base, paths in sorted(groups.items()):
    src = source_body(base)
    if src is None:
        continue
    fmt = paths[0].suffix.lstrip(".")
    texts = []
    for p in sorted(paths):
        t, _ = _extract(p)
        if t:
            texts.append(t)
    extracted = "\n".join(texts)
    rec = 1 - ned(extracted, src)
    note = ""
    if not extracted.strip():
        note = "SILENT LOSS — 0 chars (scanned/figure, needs OCR/caption)"
    elif rec < 0.5:
        note = "low — xlsx keeps only tables, prose dropped" if fmt == "xlsx" else "low — check"
    rows.append((base, fmt, rec))
    print(f"{base:10s} {fmt:6s} {rec:8.0%}  {note}")

ans = [r for _, _, r in rows if r > 0]
print(f"\nmean recovery (excluding total losses): {sum(ans)/len(ans):.0%}")
print("figures (D18-D20) and the scanned D07 at P0 are the total losses; D07 is")
print("recovered to ~92% once OCR (P3) runs, figures await P4 captioning.")

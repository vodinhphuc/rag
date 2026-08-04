"""Score every rung of the ladder against the gold questions.

Output is a rung x failure-mode matrix (spec section 8.4), never a single headline
number — averaging hides which failures remain. A cell is recall@5: the fraction
of that category's questions whose expected source appears in the rung's top-5
grouped results.

    uv run python eval/run.py

The questions in eval/questions.yaml are illustrative until real NOC questions
replace them (catalog F0.4). The harness does not change; only the questions do.
"""
import sys
import re
import math
from pathlib import Path
from collections import defaultdict

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "learning"))
sys.path.insert(0, str(ROOT / "eval"))
from _shared import DenseIndex, BM25Index, rrf, tokenize      # noqa: E402
from ingest import load_full_corpus, load_ticket_chunks        # noqa: E402


# --- corpus -----------------------------------------------------------------
print("ingesting full corpus (parsing all formats; OCR the scan)...")
doc_chunks, _ = load_full_corpus(verbose=False)
_, ticket_chunks = load_ticket_chunks()
chunks = doc_chunks + ticket_chunks           # docs and incident history in one index
dense = DenseIndex(chunks)
bm25 = BM25Index(chunks)
print(f"  {len(chunks)} chunks ({len(doc_chunks)} doc, {len(ticket_chunks)} ticket)\n")


# --- the rungs: each returns grouped top-k base ids (doc or ticket) ----------
def _group(order, k=5):
    seen, out = set(), []
    for i in order:
        d = chunks[i]["doc"]
        if d not in seen:
            seen.add(d)
            out.append(d)
        if len(out) >= k:
            break
    return out


def l0_keyword(q):                              # substring/token overlap, no ranking
    qt = set(tokenize(q))
    counts = [len(qt & set(tokenize(c["text"]))) for c in chunks]
    return _group([i for i in np.argsort(-np.array(counts)) if counts[i] > 0])


def l1_bm25(q):
    return _group(bm25.ranking(q))


def l2_dense(q):
    return _group(dense.ranking(q))


def l3_hybrid(q):
    return _group(rrf([dense.ranking(q), bm25.ranking(q)]))


def _has_identifier(q):
    return bool(re.search(r"\b[A-Z]{2,}-\d+\b|\b\d{3,}\b", q))


def l4_structure(q):
    # route by query shape (nb 04); scope to a named service if the question gives one
    order = rrf([dense.ranking(q), bm25.ranking(q)]) if _has_identifier(q) else dense.ranking(q)
    m = re.search(r"\bsq-\w+\b", q)
    if m:
        svc = m.group(0)
        scoped = [i for i in order if chunks[i]["meta"].get("service") == svc]
        if scoped:
            order = scoped
    return _group(order)


RUNGS = [("L0 keyword", l0_keyword), ("L1 bm25", l1_bm25), ("L2 dense", l2_dense),
         ("L3 hybrid", l3_hybrid), ("L4 structure", l4_structure)]


# --- scoring ----------------------------------------------------------------
questions = yaml.safe_load((ROOT / "eval" / "questions.yaml").read_text())["questions"]
categories = sorted({q["category"] for q in questions})


def expected_set(q):
    e = q["expect"]
    if e is None:
        return set()
    return set(e) if isinstance(e, list) else {e}


def hit(got, q):
    exp = expected_set(q)
    if not exp:                                  # unanswerable: "hit" = nothing confident returned
        return None                              # scored separately (refusal), not recall
    return bool(exp & set(got))


# rung -> category -> [bools]
matrix = {name: defaultdict(list) for name, _ in RUNGS}
for q in questions:
    for name, fn in RUNGS:
        got = fn(q["q"])
        h = hit(got, q)
        if h is not None:
            matrix[name][q["category"]].append(h)

# --- report -----------------------------------------------------------------
answerable_cats = [c for c in categories if c != "unanswerable"]
w = 12
print("recall@5, rung x failure-mode  (blank = no answerable questions in cell)\n")
head = "rung".ljust(w) + "".join(c[:9].rjust(10) for c in answerable_cats)
print(head)
print("-" * len(head))
for name, _ in RUNGS:
    row = name.ljust(w)
    for c in answerable_cats:
        vals = matrix[name][c]
        row += (f"{sum(vals)}/{len(vals)}".rjust(10)) if vals else "".rjust(10)
    print(row)

print("\nper-rung overall recall@5 (answerable questions only):")
for name, _ in RUNGS:
    allv = [v for c in answerable_cats for v in matrix[name][c]]
    print(f"  {name:14s} {sum(allv)}/{len(allv)}  ({sum(allv)/len(allv):.0%})")

# open failure modes: answerable categories no rung ever gets
print("\nopen failure modes (answerable, yet 0 hits at every rung):")
any_open = False
for c in answerable_cats:
    has_q = len(matrix["L2 dense"][c]) > 0
    if has_q and all(sum(matrix[name][c]) == 0 for name, _ in RUNGS):
        any_open = True
        print(f"  {c}  ({len(matrix['L2 dense'][c])} q) — retrieval is the wrong tool "
              f"(structured query) or the answer is in an un-captioned figure (needs P4)")
if not any_open:
    print("  (none — but see the low-recall cells above; recall@5 is coarse)")

# refusal accuracy: unanswerable questions must NOT surface a confident source
THRESHOLD = 0.55                                  # same gate as notebook 06
unanswerable = [q for q in questions if not expected_set(q)]
correct_refusals = 0
for q in unanswerable:
    top = float(dense.scores(q["q"]).max())
    if top < THRESHOLD:
        correct_refusals += 1
print(f"\nrefusal accuracy (unanswerable questions correctly below the {THRESHOLD} "
      f"confidence gate): {correct_refusals}/{len(unanswerable)}")
print("  a false answer here — confidently citing a source for a question the KB does")
print("  not cover — is the dangerous error (spec 7.3). Zero false answers is the target.")

print("\nThese numbers are illustrative until real NOC questions replace the gold set")
print("(F0.4). The harness does not change; only questions.yaml does.")

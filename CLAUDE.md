# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A **teaching project**, not a product. It builds a RAG system that helps a NOC
team answer questions from an EDR product's documentation, and its real
deliverable is a ~2 hour seminar plus a repo colleagues can clone and copy from.

Three artifacts carry the project. Read them before proposing changes:

| File | What it is |
|---|---|
| `docs/superpowers/specs/2026-07-29-rag-noc-assistant-design.md` | **Source of truth.** ~1600 lines, versioned v1.0 → v2.3, with a revision log at the top |
| `docs/talk/logic-flow.md` | Seminar narrative: argument chain, five acts, **assumptions register** |
| `corpus/BIBLE.md` | Invented-product reference that keeps every generated document consistent |

The spec's **§10 failure catalog (115 entries)** is a first-class deliverable, not
documentation about the code. New failure modes discovered during work belong in
it, with the standard shape: symptom → cause → fix → search term.

## Critical: this repository is public

`github.com/vodinhphuc/rag` is **public**. `corpus/private/` holds real internal
EDR documentation — install guides, troubleshooting, NOC/SOC operations — which
describes tamper protection, exclusions, detection thresholds and console
endpoints. It must never be committed, and neither may anything derived from it
(chunks, indexes, captions, eval questions containing verbatim content,
screenshots for slides).

A pre-commit guard enforces this. **On a fresh clone the hook symlink does not
exist — reinstall it:**

```bash
ln -sf ../../scripts/check-no-private.sh .git/hooks/pre-commit
```

It blocks private paths, document binaries outside `corpus/rendered/`, and
uppercase confidentiality banners. Marker matching is deliberately
case-sensitive and anchored: a guard that fires on ordinary prose gets bypassed
with `--no-verify`, which is worse than no guard.

Verify it still works after editing it — force-add a fake leak and confirm the
script exits non-zero.

## Commands

```bash
bash scripts/render_corpus.sh --check     # report tool availability, exit
bash scripts/render_corpus.sh             # render every source document
bash scripts/render_corpus.sh D06         # render one doc_id, all languages

bash scripts/check-no-private.sh          # run the leak guard manually
```

Rendering needs `pandoc`, `imagemagick`, `img2pdf`, `libreoffice`,
`poppler-utils`. `--check` reports which are missing.

**There is no build, no linter and no test suite yet.** The eval harness
(`eval/run.py`, `eval/parsing.py`) and the retrieval service (`service/`) are
specified in §13 but not written. Do not invent commands for them.

## Architecture

### Two corpora, different jobs

| | Generated — "SENTRIQ" | Real — company EDR docs |
|---|---|---|
| Where | `corpus/source/` → `corpus/rendered/`, committed | `corpus/private/`, gitignored |
| Job | Learning, reproducibility, **measurable parsing** | Internal demo credibility |

`corpus/source/*.md` is **ground truth and is never indexed.** The pipeline reads
only `corpus/rendered/`. That gap is the point: extracted text can be diffed
against the markdown that produced it, which is what makes parsing accuracy
measurable via NED/TEDS. Real documents have no such source, so parsing there is
checked against a hand-transcribed sample instead.

### Document naming and front matter

```
corpus/source/D06.vi.md    →    doc_id . language . md
```

Translations of one document **share a `doc_id`**. Retrieval groups on it before
applying top-k, which is what stops three translations from consuming three of
five result slots. It cannot be reconstructed after ingest. Front-matter contract
is documented in `corpus/source/README.md`.

### Two ladders, ordered by when cost is paid

The organising idea of the whole design (spec §9):

- **Parsing P0–P4** runs at ingest — paid once per document
- **Retrieval L0–L8** runs at query time — paid on every request, forever

Spend at ingest before query time. This is why the cross-encoder reranker sits at
**L7, last**, and why parsing runs before any retrieval work. A rung is climbed
only when evaluation shows the current one failing on a specific question
category.

### Two environments, one codebase

Learning host has an RTX 3090 (24 GB VRAM). The **demo host has no GPU** — WSL2,
8 GB, calling the company's hosted models (`qwen36_a3b`, `embedding-qwen3-4b`,
`qwen3-rerank-0.6B`) over the internal network. Switching is configuration
(`LLM_BASE_URL`, `EMBED_DEVICE`), never a code path.

**Latency and cost figures must be measured on the demo host**, never the 3090.
Retrieval-quality figures are hardware-independent. Spec §5.3.3.

## Deliberate traps — do not "fix" these

The corpus contains planted defects. Each one exists to make a specific failure
visible during the seminar, and each maps to a row in `corpus/BIBLE.md` §7.
Correcting them silently destroys the demo:

- **`D08.vi` is version 3.8 while `D08.en` is 4.2.** Different threshold, different
  command. This is the translation-drift teaching example; its front matter says
  `drift_note: ... Do not fix.`
- **`D16` has no Vietnamese version.** English and Japanese only. Removing this
  gap removes the only proof that cross-lingual retrieval is required.
- **`D12` never says it is deprecated in its body.** Only front matter marks it.
  That is the lesson — metadata saves you, prose does not.
- **`D08` and `D09` open with a byte-identical symptom paragraph.** Intentional.
- **`D07` renders scanned**, so it extracts to nothing without OCR.
- **Ticket shorthand** (`col2`, `văng`, `nghẽn`, `lỗi bắt tay`, `kho` — BIBLE §3)
  appears in **tickets only, never in documents**, which use the formal form
  (`sq-collector-02`, "Offline", "back-pressure"). Writing shorthand into a
  runbook closes the gap and removes the trap.

If a change seems to require fixing one of these, it is more likely the change is
wrong.

## Working conventions

**Never guess — measure.** Results are reported as a **rung × failure-mode
matrix**, never as a headline number, because averaging hides regressions. A rung
is adopted only if it improves at least one cell and regresses none. Cells where
the L0 baseline already succeeds grant later rungs no credit.

**Label claims about the user's organisation.** `docs/talk/logic-flow.md` §2 is an
assumptions register marking every such claim Verified, Assumed, or Hypothesis.
This exists because an earlier draft asserted "writing more documentation was
already tried and failed" — which no stakeholder ever said, and which was
repeated as fact across several revisions before being caught. Nothing marked
Assumed or Hypothesis may be stated as fact in the seminar.

**Corrections belong in the spec's revision log.** Several versions exist purely
to correct earlier errors (v2.1 corrected v2.0's conflation of the two hosts; v2.2
corrected v2.1's claim about CPU reranking). Record what changed and why rather
than silently editing.

**Vietnamese content needs native review** before it is used to measure
cross-lingual retrieval. Translationese embeds differently from natural writing
and would make the language demos flattering rather than honest.

## Note on the inherited CLAUDE.md

`/home/phucvd/CLAUDE.md` sits in a parent directory and is loaded automatically.
It documents an unrelated **dotfiles** repository — GNU Stow, `scripts/install.sh`,
program installers. None of it applies here.

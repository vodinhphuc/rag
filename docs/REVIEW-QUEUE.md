# Review queue — things only you can check

Running list of what I did autonomously and what needs your eyes. Newest work is
appended; nothing here is blocking a commit, but several items should be verified
before the corpus is used to *measure* anything or shown at the seminar.

Priority key: **[P1]** verify before measuring/demoing · **[P2]** verify before
polishing · **[P3]** nice to confirm.

---

## A. Vietnamese language — native review **[P1]**

Everything Vietnamese in the corpus is my writing. It follows your confirmed
vocabulary, but translationese embeds differently from natural writing and would
make the cross-lingual demos flattering rather than honest (spec working
convention). Please read for naturalness, not correctness of facts:

- **Runbooks (formal register):** `corpus/source/D06.vi.md`, `D07.vi.md`,
  `D08.vi.md`, `D09.vi.md`, `D10.vi.md`, `D12.vi.md` — and any new `*.vi.md` /
  `*.ja.md` I add below.
- **Tickets (shorthand register):** `corpus/tickets/tickets.jsonl` — 50 tickets.
  These deliberately use the informal 2 a.m. register (`sensor treo`, `col nghẽn`,
  `xin whitelist`). Check the shorthand reads like your team, and that `văng` /
  `nghẽn` sit on the right side of the formal/informal line.
- **Japanese:** `D06.ja.md`, `D16.ja.md` (+ any new). I do not read Japanese well;
  these need a stronger check than the Vietnamese.

**Specific worry:** `nghẽn` vs `tồn queue` are used as *mechanism* vs *measurement*
in the tickets (see `corpus/BIBLE.md` §3). If that distinction is wrong in real
usage, the D08/D09 confusion-pair lesson weakens.

## B. Eval harness needs YOUR real questions **[P1]**

The gold question set I can write is illustrative by construction — my questions
about my corpus — so it validates the pipeline but cannot judge quality. This is
catalog **F0.4** (demo works, production doesn't, because it was evaluated on
invented questions). The single highest-value thing you can provide:

- **20–40 real NOC questions** mined from actual tickets/chat, with which document
  or past incident answers each. Drop them into `eval/questions.yaml` (scaffold
  created below) and the harness scores every rung against them.
- **The deflection denominator:** of the last ~100 escalations, how many had an
  existing playbook? That number is the business case and nobody knows it yet.

## C. Invented SENTRIQ details — domain plausibility **[P2]**

I invented an EDR product (see `corpus/BIBLE.md`). A domain expert should sanity-
check that the procedures, error codes, thresholds and component model read as
plausible EDR operations, not obviously-AI-generated. Not for accuracy (it is
fictional) but for *credibility* to the seminar audience.

## D. Planted-trap integrity **[P2]**

Each trap must survive authoring/rendering or its demo breaks. Verified by me
where noted, but worth a spot check against `corpus/BIBLE.md` §7:

- D08.vi (v3.8, threshold 10.000) vs D08.en (v4.2, threshold 50.000) — drift pair
- D06 "không restart collector" vs D12 "restart collector" — staleness pair
- D08/D09 byte-identical opening symptom — confusion pair
- D16 has no `.vi` version — cross-lingual gap
- D07 renders scanned → 0 chars at P0 — silent-failure demo

## E. Autonomous decisions to confirm **[P3]**

- Confidence thresholds picked by calibration on my data: retrieval-answerable
  gate **0.55** (nb 06), incident-similarity gate **0.55** (nb 07). Real
  thresholds tune on your gold set.
- Notebook model is `bge-m3` (multilingual, fits the 3090). The demo/eval will
  also run the hosted `Qwen3-Embedding-4B` to match the demo index (spec §5.3.4).
- Ticket `resolved_by` names, dates, and root causes are invented but internally
  consistent with the runbooks.

---

## Work log (what I did, newest first)

### 2026-08-05 — eval harness scaffold (`eval/`)
- `eval/ingest.py` — full-corpus ingestion: parses every format (PDF/DOCX/XLSX
  text, OCR for the scan), attaches metadata from source front matter, and
  concatenates multi-sheet workbooks (fixing an only-first-sheet bug in my own
  ingest, F1.14). 182 chunks (132 doc + 50 ticket). Figures excluded — they need
  P4 captioning.
- `eval/run.py` — scores L0–L4 against the gold questions as a **rung ×
  failure-mode matrix** (spec §8.4), never a headline number. Also reports open
  failure modes and refusal accuracy on the unanswerable questions.
- `eval/questions.yaml` — **18 ILLUSTRATIVE questions. [P1] REPLACE with 20–40
  real NOC questions** (F0.4). The harness is done; only the questions need you.
- Current illustrative result (means little until real questions): L2/L4 ≈ 87%
  recall@5; `negation` is an open failure mode (needs structure/captioning, not
  retrieval); refusal 2/3 — the counting question "how many P2 incidents" scores
  above the gate, correctly flagged as a false-answer risk that needs a structured
  query, not retrieval. **[P3] confirm this matches your intuition.**

### 2026-08-05 — authored the remaining documents
- Added D01–D05, D13–D15, D17–D25 (English primaries) + D14.vi. Corpus source is
  now ~25 documents; 31 rendered files. **[P2] review the new English prose for
  domain plausibility; [P1] the new D14.vi for Vietnamese naturalness.**
- New traps in place and verified: D03 (docx table, per-component upgrade timings —
  P2), D05 (xlsx two sheets, ports + timeouts — P2), D04 (signal-dilution: the
  console-outage answer buried mid-paragraph — the reranker's justified case),
  D18 (dependency map PNG, hosts the negation trap "what does NOT talk to the
  store"), D19/D20 (screenshot PNGs — answer only in the image, P4).
- **Caught and fixed a trap violation I introduced:** the new D04/D13/D14 leaked
  ticket shorthand (`sensor`, `whitelist`, `FP`) into formal docs, which would
  close the vocabulary gap those traps depend on. All removed; docs now say
  `agent`/`exclusion`/`false positive`. Full corpus re-scanned clean. **[P3]
  confirm you're happy docs never abbreviate "false positive" to "FP", even in
  D14 which is about false positives — I kept it spelled out to preserve the trap.**
- **Known limitation:** D01 is marked `pdf-2col` but xelatex is absent on this
  host, so it renders single-column via the libreoffice fallback. The two-column
  reading-order trap (parsing P1) will not manifest until a TeX engine is
  installed (`sudo apt install texlive-xetex`). **[P3] decide whether P1 matters
  enough to install TeX.**
- Still missing: vi/ja versions of D01/D04/D13 (the flooding docs — BIBLE §6.1),
  being added next.

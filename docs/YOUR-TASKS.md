# Your tasks — concrete, do-later

A work-through checklist of everything that needs **you** (not Claude). Each item
has: why it matters, the exact file, the exact steps, and how to check it worked.
Ordered by priority. The running log of what was built is in `REVIEW-QUEUE.md`;
this file is the action list.

---

## ★ TASK 1 — Give the eval real NOC questions  `[blocks all real measurement]`

**Why.** The harness scores retrieval, but only against the questions you give it.
Right now `eval/questions.yaml` holds 18 *invented* questions — my questions about
my corpus. They prove the harness runs; they cannot prove the system is good. A
demo built on invented questions works in the room and fails in production
(failure catalog F0.4). Real questions are the single highest-value input.

**File.** `eval/questions.yaml`

**Steps.**
1. Pull **20–40 real questions** from actual NOC tickets, chat logs, or escalation
   records. Prefer ones where you *know* which document or past incident answered
   them.
2. For each, add a row in this exact shape:

   ```yaml
   - id: R01                      # any unique id
     q: "sensor văng cả cụm sau khi update, log lỗi bắt tay"   # the operator's real words
     lang: vi                     # vi | en | ja
     category: repeat             # see the category list at the top of questions.yaml
     expect: T04                  # the doc_id (D06) or ticket id (T04) that answers it
                                  #   use a list [D06, T04] if more than one is acceptable
                                  #   use null if genuinely unanswerable
     verdict: ANSWER              # ANSWER (a playbook exists) or ESCALATE
     severity: P3                 # P1..P4, or null
   ```
3. You can **delete my Q01–Q18** once you have real ones, or keep them alongside.
4. **The `expect` field is the hard part and the important part.** It is the
   ground truth. If you are unsure which document answers a question, that
   uncertainty is itself a finding worth noting.

**Check it worked.**
```bash
uv run python eval/run.py
```
You want the matrix to reflect *your* questions. Watch especially the
**refusal-accuracy** line (unanswerable questions must not get a confident answer)
and any category that stays 0 across all rungs (an open failure mode).

**Bonus number worth finding while you're in the tickets:** of the last ~100
escalations, how many had an existing playbook? That single fraction is the
business case for the whole project, and nobody knows it yet. Put it in the
seminar's Act I.

---

## ★ TASK 2 — Native Vietnamese / Japanese review  `[blocks cross-lingual claims]`

**Why.** Every non-English word in the corpus is mine. It follows your confirmed
vocabulary, but translationese embeds differently from natural writing — if the
Vietnamese reads translated, the cross-lingual retrieval demos will look better
than they deserve. Read for **naturalness**, not fact.

**Files, in priority order.**

1. **Tickets (informal register)** — `corpus/tickets/tickets.jsonl`, 50 rows.
   - Does the shorthand read like your team at 2 a.m.? (`sensor treo`, `col nghẽn`,
     `xin whitelist`, `văng`, `tồn queue`).
   - **Specific worry:** in the tickets I use `nghẽn` = mechanism (collector
     throttling) and `tồn queue` = measurement (queue depth) as *different* things
     (see `corpus/BIBLE.md` §3). If that split is wrong in real usage, the D08/D09
     confusion-pair lesson weakens. Confirm or correct.

2. **Vietnamese runbooks (formal register)** — `corpus/source/D06.vi.md`,
   `D07.vi.md`, `D08.vi.md`, `D09.vi.md`, `D10.vi.md`, `D12.vi.md`, `D14.vi.md`.
   - These must **never** use ticket shorthand (that is the whole vocabulary trap).
     They should read as formal documentation: "not responding", "Offline",
     "back-pressure", "exclusion", "agent" — not `treo`, `văng`, `nghẽn`,
     `whitelist`, `sensor`.

3. **Japanese** — `corpus/source/D06.ja.md`, `D16.ja.md`. I do not read Japanese
   well; these need the hardest check.

**How to fix.** Edit the `.md` in `corpus/source/`, then re-render:
```bash
bash scripts/render_corpus.sh D06        # re-render one doc_id, all languages
```

**Check the traps still hold after your edits** (do not accidentally introduce
shorthand into a doc, or fix a deliberate defect):
```bash
# no ticket shorthand should appear in any document:
grep -rniE '(treo|văng|nghẽn|tồn queue|whitelist|sensor)' corpus/source/D*.md
# D08.vi must stay version 3.8 (the drift trap) — do NOT "fix" it to 4.2
grep -n 'version' corpus/source/D08.vi.md
```

---

## TASK 3 — Sanity-check the invented product  `[before the seminar]`

**Why.** SENTRIQ is fictional (`corpus/BIBLE.md`). A domain expert should confirm
the procedures, error codes, thresholds and component model read as *plausible*
EDR operations — not for accuracy, but so the seminar audience finds it credible.

**Files.** Skim `corpus/BIBLE.md` (the reference) and a few runbooks. Flag anything
that reads obviously-AI-generated or operationally wrong.

---

## TASK 4 — Confirm the decisions I made for you  `[quick]`

Small calls I made autonomously. Confirm or change:

- **"FP" is spelled out "false positive" in every document, even D14 which is
  entirely about false positives.** I did this to keep the FP→false-positive
  vocabulary trap intact. If that reads unnaturally formal, tell me and I'll
  reconsider the trap.
- **Confidence thresholds are 0.55** (answer-vs-escalate gate, notebook 06; and
  incident-similarity gate, notebook 07). Calibrated on my data. Real thresholds
  should be tuned on your gold set once Task 1 is done.
- **The notebooks use `bge-m3`.** The demo/eval will also run the company's hosted
  `Qwen3-Embedding-4B` to match the demo index. For *learning* the model choice
  doesn't change any lesson.

---

## TASK 5 — Optional, only if you want the last traps  `[low value]`

- **vi/ja versions of D01, D04, D13** — BIBLE §6.1 lists them for the top-k
  flooding trap, but flooding is already demonstrated via D06 (which has all three
  languages), so this is completeness, not capability. Say the word and I'll write
  them.
- **Parsing P1 (two-column reading order)** — dormant because this host has no TeX
  engine. To enable: `sudo apt install texlive-xetex`, then
  `bash scripts/render_corpus.sh D01` and the two-column trap will render.
- **Parsing P4 (figure captioning)** — D18/D19/D20 are images with no extractable
  text (answer-only-in-a-figure). Making them searchable needs a vision model
  (the company's hosted vision-capable Qwen). Until then those questions correctly
  fail in the eval.

---

## When you're ready to hand me back the wheel

Tell me any of:
- "questions are in" → I re-run the full eval and report the real matrix.
- "Vietnamese is reviewed" → I re-verify the traps and re-render.
- "write the vi/ja / install TeX / do P4" → I pick the optional work back up.

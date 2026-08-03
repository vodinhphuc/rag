# Authored corpus source

Ground truth for the generated corpus. **Never indexed** — `scripts/render_corpus.sh`
renders these into `corpus/rendered/`, and ingest reads only that. Keeping the
markdown back is what makes parsing accuracy measurable (spec §6.1).

All content describes **SENTRIQ**, an invented EDR product. See `../BIBLE.md`.

## Naming

```
D06.vi.md     doc_id . language . md
D06.en.md
D06.ja.md
```

Translations of one document **share a `doc_id`**. That is what makes
grouping-before-top-k possible (spec §6.6), and it cannot be reconstructed after
ingest.

## Front matter

```yaml
doc_id: D06           # same across all language versions
language: vi          # vi | en | ja
version: "4.2"        # product version this procedure applies to
status: current       # current | deprecated
title: ...
type: runbook         # runbook | reference | guide
service: sq-agent     # owning component, from BIBLE §1
error_codes: [SQ-1004]
severity: P3
updated: 2026-03-15
render: markdown      # markdown | pdf | pdf-2col | pdf-scanned | docx | xlsx | png
```

`status: deprecated` appears **only in front matter, never in the body.** A
superseded runbook that announces itself is not a trap — the lesson is that
metadata saves you and prose does not.

## Vietnamese content

Written as a Vietnamese engineer would: Vietnamese prose with English technical
terms left inline (`agent`, `collector`, `queue depth`, `restart`), not
translated. **A native speaker should review these before they are used to
measure cross-lingual retrieval** — translationese embeds differently from
natural writing, and unnatural text would make the language demos misleading.

## Internal vocabulary

The ticket shorthand in `BIBLE.md` §3 appears in **tickets only, never in these
documents.** Two groups:

| Never write in a document | Always write instead |
|---|---|
| `treo` | "not responding", "unresponsive" |
| `văng` | "Offline", "mất heartbeat" |
| `nghẽn` | "back-pressure", "agents throttled" |
| `lỗi bắt tay` | `mTLS handshake failed` |
| `tồn queue` | "queue depth" |
| `whitelist` | **"exclusion"**, "exception" |
| `sensor` | **"agent"**, `sq-agent` |
| `FP` | "false positive" |

That gap is the point, and it is not exotic: it is the ordinary difference
between how people write documentation and how they type into a ticket at 2 a.m.
Every one of those words is lexically disjoint from the doc phrase meaning the
same thing, so BM25 cannot bridge them. It is what the domain vocabulary map
(spec §9.2, L5) exists to fix.

**When authoring documents, always use the right-hand column.** Introducing
ticket shorthand into a runbook closes the gap and removes the trap. `whitelist`
in particular must never appear — D10 is a whole runbook about exclusions and
its value as a trap depends on never using the word a ticket would use.

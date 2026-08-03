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

The nicknames in `BIBLE.md` §3 (`con bò`, `quạt`, `đứt tay`, `nhà kho`) appear in
**tickets only, never in these documents.** That gap is the point: it is what the
domain vocabulary map (spec §9.2, L5) exists to bridge.

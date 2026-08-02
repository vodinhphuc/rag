# SENTRIQ EDR — corpus bible

**Not part of the corpus.** Ingest reads `corpus/rendered/` only. This file is
the internal reference that keeps all generated documents consistent, so that
gold answers are unambiguous and planted traps land where intended.

SENTRIQ is **entirely invented**. No relationship to any real EDR product,
vendor or company. Deliberately so: the generated corpus is public, and the
real corpus (`corpus/private/`, gitignored) is where actual company material
stays.

---

## 1. The product

**SENTRIQ Endpoint Detection & Response**, by the fictional vendor *Norvale
Security*. Deployed on-premises. Current version **4.2**; **3.8** is still in
the field and is the source of several version-mismatch traps.

### Components

| Component | Code | Runs on | Purpose |
|---|---|---|---|
| Sentriq Agent | `sq-agent` | Endpoints (Windows/Linux) | Telemetry collection, local detection, response actions |
| Collector | `sq-collector` | 3 nodes, on-prem | Receives agent telemetry, normalizes, forwards |
| Detection Engine | `sq-detect` | 2 nodes | Rule evaluation, correlation, alert generation |
| Console | `sq-console` | 1 node | Web UI for SOC, REST API |
| Policy Service | `sq-policy` | 1 node | Distributes policy and exclusions to agents |
| Event Store | `sq-store` | 4-node cluster | Telemetry retention, 90 days |
| Update Relay | `sq-relay` | 2 nodes | Signature and agent-version distribution |

### Ports (used in troubleshooting docs)

| Port | Between |
|---|---|
| 8443 | agent → collector (mTLS) |
| 9200 | collector → store |
| 8080 | console → detect |
| 7443 | agent → policy (policy pull) |
| 8843 | agent → relay (updates) |

### Environments

`prod`, `staging`, `dr`. Traps depend on prod/staging having near-identical
symptoms with different resolutions.

---

## 2. Error codes

Deliberately structured so that **the code is semantically meaningless** — this
is what defeats dense retrieval and proves hybrid search (spec §6.3).

| Code | Meaning | Owning component |
|---|---|---|
| `SQ-1004` | Agent heartbeat missed > 15 min | sq-agent |
| `SQ-1017` | Agent certificate expired | sq-agent |
| `SQ-2003` | Collector queue depth above threshold | sq-collector |
| `SQ-2011` | Collector back-pressure, agents throttled | sq-collector |
| `SQ-3009` | Detection rule compilation failure | sq-detect |
| `SQ-3021` | Correlation window overflow | sq-detect |
| `SQ-4002` | Console session store unavailable | sq-console |
| `SQ-5006` | Policy push rejected by agent | sq-policy |
| `SQ-5013` | Exclusion conflict — overlapping paths | sq-policy |
| `SQ-6008` | Event store shard unassigned | sq-store |
| `SQ-6014` | Retention job overrun | sq-store |
| `SQ-7005` | Relay signature bundle checksum mismatch | sq-relay |

**`SQ-2011` and `SQ-6008` are the near-identical-symptom pair**: both surface to
NOC as "agents showing offline", with different root causes and resolutions.
This is the metadata-scoping trap.

---

## 3. Internal vocabulary

Terms used in tickets but **never defined in the documentation** — the domain
vocabulary trap (spec §9.2 L5). Retrieval only works once these are mapped.

| Term | Actually means | Appears in |
|---|---|---|
| "con bò" | *sq-collector node 2*, nicknamed after its hostname `bo2` | Tickets only |
| "quạt" | The relay fan-out job (`sq-relay` distribution) | Tickets only |
| "đứt tay" | Agent-to-collector mTLS handshake failure | Tickets only |
| "nhà kho" | The event store cluster | Tickets only |
| `TTD` | Time To Detect | Docs and tickets, never expanded |
| `EPP` | Endpoint Protection Platform (the older product SENTRIQ replaced) | Docs only |
| `GA build` | The signed release build, vs `RC build` | Tickets only |

Vietnamese nicknames are realistic for a Vietnamese ops team and directly
exercise the VI/EN cross-lingual requirement.

---

## 4. People and ownership

| Name | Role | Owns |
|---|---|---|
| Trần Minh Đức | Platform lead | sq-collector, sq-store |
| Nguyễn Thị Lan | Detection lead | sq-detect, rule content |
| Phạm Quốc Huy | Endpoint lead | sq-agent, sq-policy |
| Lê Hoàng Nam | SRE | Infrastructure, sq-relay |
| SOC Tier-1 rota | — | Alert triage |

All invented. Used for the "module owner" field of the context packet (§7.4).

---

## 5. Severity model

| Level | Definition | Deflectable? |
|---|---|---|
| P1 | Detection blind — no telemetry from >20% of endpoints | **Never.** Severity gate (§7.2) |
| P2 | Degraded — delayed detection, partial data loss | Only with an exact playbook match |
| P3 | Single-component or single-endpoint issue | Yes |
| P4 | Cosmetic, informational | Yes |

The severity gate trap: **`SQ-6008` at P1 has a complete playbook, and must
still escalate.**

---

## 6. Document register

Each generated document is authored in one voice and language mix, and rendered
to a specific format so parsing rungs are exercised.

| # | Document | Language | Rendered as | Traps carried |
|---|---|---|---|---|
| D01 | Agent installation guide (Windows) | EN | digital PDF, 2-column | Reading order (P1) |
| D02 | Agent installation guide (Linux) | EN | DOCX | — |
| D03 | Agent upgrade 3.8 → 4.2 | EN | DOCX + table | Table extraction (P2) |
| D04 | Architecture overview | EN | PDF + diagram | Figure captioning (P4) |
| D05 | Port and firewall reference | EN | XLSX | Multi-sheet (P2) |
| D06 | Runbook: agent offline (SQ-1004) | VI + EN terms | markdown | Cross-lingual |
| D07 | Runbook: certificate expiry (SQ-1017) | VI | **scanned PDF** | OCR (P3) — silent loss |
| D08 | Runbook: collector back-pressure (SQ-2011) | VI | markdown | Near-identical to D09 |
| D09 | Runbook: store shard unassigned (SQ-6008) | VI | markdown | Near-identical to D08 |
| D10 | Runbook: exclusion conflict (SQ-5013) | VI + EN | DOCX | — |
| D11 | Runbook: rule compilation failure (SQ-3009) | EN | markdown | — |
| D12 | **Deprecated** runbook: agent offline (v3.8 procedure) | VI | PDF | Staleness — contradicts D06 |
| D13 | SOC alert triage playbook | EN | PDF | — |
| D14 | False-positive handling procedure | VI + EN | DOCX | — |
| D15 | Signature update failure (SQ-7005) | EN | markdown | — |
| D16 | Console access + RBAC guide | EN | PDF, 30pp | Repeated footer (P1) |
| D17 | Retention and storage planning | EN | XLSX + prose | Counting questions |
| D18 | Service dependency map | EN | PNG diagram only | Figure-only answer (P4) |
| D19 | Dashboard screenshot: queue depth alarm | — | PNG | Screenshot text (P4) |
| D20 | Error dialog screenshot: SQ-1017 | — | PNG | OCR-aware caption (P4) |
| D21–D25 | Configuration reference, per component | EN | DOCX | — |
| T01–T50 | Incident tickets | Mixed VI/EN | JSON | Repeat incidents, vocabulary |

`D06` and `D12` are the staleness pair: D12 is dated 2024 and describes the 3.8
procedure that is now wrong. D06 is current. Both are indexed.

`D08`/`D09` are the confusion pair: both begin "agents hiển thị offline trên
console" and diverge only in the diagnostic step.

---

## 7. Trap-to-document index

Cross-check that every trap in spec §6.3 has a home.

| Trap | Lives in |
|---|---|
| VI question → EN-only doc | D01, D04, D13 |
| Error code, semantically empty | All `SQ-*` codes |
| Contradicting stale runbook | D06 vs D12 |
| Near-identical errors, different services | D08 vs D09 |
| Answer ranks ~7th | D16 (long, many similar sections) |
| Unanswerable | *(no document covers agent behaviour on ARM Macs)* |
| Repeat incident with playbook | T-series, matched to D06/D08 |
| P1 with playbook — gate must hold | D09 + `SQ-6008` at P1 |
| Undefined acronym | `TTD`, `GA build` |
| Signal dilution | D04, one sentence buried in a long paragraph |
| Negation | "which components do **not** talk to sq-store" → D18 |
| Listing / counting | "how many P2 incidents touched sq-collector last quarter" → T-series |
| Out-of-domain vocabulary | "con bò", "quạt", "đứt tay" |
| Table-only answer | D03, D05 (retry timeouts per component) |
| Scanned-only answer | D07 |
| Screenshot-only answer | D19, D20 |
| Diagram-only answer | D18 |
| Two-column reading order | D01 |
| Repeated footer | D16 |
| Cross-format duplicate | D02 present as both DOCX and exported PDF |

Every trap in the spec has at least one home, and no document carries more than
two — so a failure attributes to one cause.

---

## 8. Consistency rules for generation

1. Component names, ports and error codes come **only** from this file.
2. A fact appears in exactly one document unless duplication is the trap.
3. Vietnamese runbooks keep English technical terms inline — that mix is the
   point, not an inconsistency to clean up.
4. D21–D25 are written in a flat, uniform, AI-generated register; the runbooks
   are not. Inconsistent voice across authors is realistic.
5. Dates: current docs 2026, deprecated docs 2024, tickets spread over 18 months.
6. No real IPs, hostnames, domains or people. Reserved ranges only
   (`10.20.x.x`, `.internal.norvale.test`).

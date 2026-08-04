# %% [markdown]
# # 07 — Retrieving over incident history: repeat-incident deflection
#
# Notebooks 01–06 retrieved over *documents*. But the most deflectable question a
# NOC operator asks is not "what does the runbook say" — it is "has this happened
# before, and what did we do." That question is answered against the **ticket
# history**, not the docs, and it turns out to be both easier and more useful.
#
# Two findings drive this notebook:
# 1. A new ticket, written in NOC shorthand, matches its past siblings cleanly —
#    because both are in the same shorthand register, there is *no vocabulary gap*
#    to bridge. Incident history is a better-matched index for recurring problems
#    than the formally-worded runbooks.
# 2. The matched past ticket already tells us what to do: if it was resolved with a
#    playbook, ANSWER; if it was a novel bug that got escalated, ESCALATE — but with
#    that prior investigation attached, which is most of the value for the hard slice.

# %%
import numpy as np
from _shared import load_tickets, load_chunks, DenseIndex, BM25Index

rows, ticket_chunks = load_tickets()
tickets = DenseIndex(ticket_chunks)      # same index, now over 50 incidents
print(f"{len(rows)} tickets indexed")
resolved = sum(1 for r in rows if r["runbook"])
print(f"  {resolved} resolved with a runbook, {len(rows)-resolved} novel (escalated, no runbook)")

# %% [markdown]
# ## 1. Repeat-incident matching — shorthand finds shorthand
#
# A fresh alert arrives, phrased the way NOC actually types. Retrieve the nearest
# past incidents. Note the scores: 0.7–0.85, far higher than the 0.5–0.68 we saw
# retrieving shorthand queries against formal documents. Same words, both sides —
# nothing to translate.

# %%
def nearest_incidents(text, k=3):
    scores = tickets.scores(text)
    out = []
    for i in np.argsort(-scores)[:k]:
        r = rows[i]
        out.append((r["id"], r["runbook"], r["resolved_by"], float(scores[i])))
    return out

for alert in [
    "sensor văng cả loạt, collector nghẽn tồn queue cao",
    "xin whitelist path cho máy build, sensor quét chậm",
    "sensor treo mấy máy, restart là lên",
]:
    print(f"\nALERT: {alert!r}")
    for tid, rb, who, sc in nearest_incidents(alert):
        print(f"   {sc:.3f}  {tid}  runbook={rb}  resolved_by={who}")

# %% [markdown]
# ## 2. Why this beats matching the runbook directly
#
# Recall the vocabulary gap from the ticket corpus: shorthand like `sensor`,
# `văng`, `nghẽn`, `whitelist` appears in tickets but *never* in the documents,
# which say `agent`, `Offline`, `back-pressure`, `exclusion`. Matching a shorthand
# alert against a formal runbook has to cross that gap; matching it against a past
# ticket does not. Below, the same alert against the document corpus scores lower
# and less certainly than against the incident history.

# %%
docs, doc_chunks = load_chunks()
doc_index = DenseIndex(doc_chunks)
alert = "sensor văng cả loạt, collector nghẽn tồn queue cao"
d_top = float(doc_index.scores(alert).max())
t_top = nearest_incidents(alert, 1)[0][3]
print(f"alert: {alert!r}")
print(f"  best score vs DOCUMENTS (formal, vocab gap): {d_top:.3f}")
print(f"  best score vs TICKETS   (shorthand, no gap): {t_top:.3f}")
print("  -> the incident history is the better-matched index for a recurring problem")

# %% [markdown]
# ## 3. The verdict — the matched ticket already knows the answer
#
# The decision does not need the runbook text at all. The nearest past incident
# carries its own resolution:
# - **similar incident, resolved with a playbook** → ANSWER: "this is incident
#   {id}, resolved via {runbook} by {who}" — the repeat-incident deflection.
# - **similar incident, but it was a novel bug (no runbook)** → ESCALATE, and hand
#   the engineer that prior investigation. The hard slice is not answered; it is
#   accelerated.
# - **nothing similar enough** → ESCALATE as genuinely new.

# %%
SIM = 0.55      # below this, no past incident is close enough to rely on

def triage(alert):
    top = nearest_incidents(alert, 1)[0]
    tid, runbook, who, score = top
    if score < SIM:
        return {"decision": "ESCALATE", "reason": "no similar past incident", "score": round(score, 3)}
    if runbook:
        return {"decision": "ANSWER", "like": tid, "via": runbook,
                "precedent": f"resolved by {who}", "score": round(score, 3)}
    return {"decision": "ESCALATE", "reason": "resembles a past NOVEL bug",
            "like": tid, "prior_investigation": f"handled by {who}", "score": round(score, 3)}

def show(alert):
    print(f"ALERT: {alert!r}")
    for k, v in triage(alert).items():
        print(f"    {k}: {v}")
    print()

# %% [markdown]
# ## 4. The three shapes, decided
#
# A recurring incident with a playbook, a recurrence of a hard bug, and a genuinely
# new symptom — each routed correctly by its nearest precedent.

# %%
show("sensor treo mấy máy restart là lên")                        # repeat, D06 -> ANSWER
show("telemetry đếm gấp đôi trên dashboard sau khi thêm node")     # repeat of novel bug -> ESCALATE + prior
show("agent ăn CPU cao liên tục sau khi lên bản 4.2")             # repeat of novel bug -> ESCALATE + prior
show("người dùng phàn nàn font chữ trong report bị vỡ")           # nothing similar -> ESCALATE new

# %% [markdown]
# ## 5. What this rung adds to the product
#
# - **Deflection gets cheaper and surer.** The highest-value deflection — "we have
#   seen this exact thing" — is answered against incident history, where the query
#   and the record share a vocabulary, at higher confidence than any document match.
# - **The hard slice gets a warm start.** A recurrence of an unresolved bug cannot
#   be answered, but the engineer is handed the prior ticket and who worked it —
#   the context packet the spec builds the escalation product around (§7.4).
# - **The vocabulary map (L5) still earns its place** — but now we can see *where*:
#   for matching alerts to formal runbooks and for the BM25 arm, not for the
#   ticket-to-ticket matching that carries most of the deflection load. As always,
#   the measurement says which rung is worth which effort.
#
# Deliberately still not here: generation, the parsing ladder (P0–P4, which would
# unlock D07/D10/D12/D16 and let the vocabulary map be measured against the whole
# document set), and the hosted-model L6 comparison. Each waits for its inputs.

# Spec: "Ask FreshyFresh" data agent

## Goal
Business users ask freshness, food-safety and service questions in plain English and get grounded answers from
three sources (lakehouse, semantic model, eventhouse). Builders and agents (Claude Code, later Copilot
Studio/Foundry) consume the same agent through its MCP endpoint.

## Artefacts (single source of truth, versioned in Git)
- `agent/instructions.md`: description, context, sources & relationships, business rules.
- `agent/fewshots_lakehouse.json`: T-SQL examples (flat `{question: query}`, Fabric bulk-import format).
- `agent/fewshots_kql.json`: KQL examples.
- `agent/golden_answers.json`: eval oracle (Q1–Q8).

Few-shots deliberately use different lots, dates and facilities than the golden questions, so the eval measures
generalisation, not recall.

## FT5: Ask FreshyFresh in Claude Code on trial (no Data Agent)
`/ask-freshyfresh <question>` and `/ask-freshyfresh eval` in Claude Code. Iterate on instructions and few-shots until Q1–Q8
PASS. Log each prompt change and its effect in `docs/lab-log.md` (prompt engineering as an engineering loop).

## FT6: publish a Fabric Data Agent (paid F2, same region as the trial)
1. Create the F2 capacity in Azure. Assign it to `WS-FRESHYFRESH-AGENT`. Enable the tenant settings in `docs/setup.md` §2.
2. New item → Data agent → `DA_Ask_FreshyFresh`.
3. Add data sources:
   - `LH_FreshyFresh`: tick only the gold tables.
   - `SM_FreshyFresh_Ops`.
   - `KQL_ColdChain`: table `ReeferTelemetry`.
   - *Verify* cross-workspace sources work from an F2 workspace to a trial workspace (architecture.md, open risks).
4. Paste the instructions. Bulk-import the few-shot JSON per source (lakehouse, KQL). Add semantic-model
   instructions if the UI offers per-source notes.
5. Test in the agent UI with Q1–Q8. Inspect the generated SQL/DAX/KQL for each answer.
6. Publish. Use the description from `agent/instructions.md`, because it becomes the MCP tool description.
7. Settings → Model Context Protocol: copy the server URL. Add it to Claude Code (`docs/setup.md` §7).
8. Run `/ask-freshyfresh eval` through the published agent. Compare with the FT5 results and golden answers.

## Quality bar
- Q1–Q8 PASS (tolerances in the `ask-freshyfresh` skill).
- Every answer states the date range used and which source it queried.
- No contact PII in answers unless explicitly requested.
- Naive excursion trap avoided (4 shipments, not 112).

## Governance notes for the client conversation
- Agent and MCP answers can leave Fabric's compliance boundary / region (Learn warning). This needs a data
  classification decision before any real data.
- RLS: confirm on Learn whether data-agent queries run under the caller's identity for each source type. Test
  with the P03 test user before claiming it.
- Capacity: agent usage consumes CUs on the agent's capacity. Size and monitor it with the Capacity Metrics app.

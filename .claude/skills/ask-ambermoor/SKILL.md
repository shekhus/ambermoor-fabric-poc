---
name: ask-ambermoor
description: Act as the "Ask Ambermoor" data agent prototype - answer business questions about the synthetic Ambermoor data (recalls, lot traceability, cold chain, truck location, dock wait, trip cost, waste, OTIF, sales) with T-SQL or KQL, run the golden-answer eval, or export the agent config for a Fabric Data Agent. Use for natural-language data questions in this repo or "/ask-ambermoor eval".
argument-hint: "[question | eval | export]"
---

# Ask Ambermoor: agent prototype (runtime-agnostic)

Request: $ARGUMENTS

The agent's behaviour is defined once, in `agent/instructions.md` (context, sources, relationships, business rules)
and `agent/fewshots_lakehouse.json` / `agent/fewshots_kql.json`. Read them first and follow them exactly. These are
the same artefacts you would paste or import into a Fabric Data Agent, so prompt-engineering work here carries over.

## Answer mode (a question)
1. Route the question to a source using the routing table in `agent/instructions.md`:
   - KPIs → semantic model
   - lots / trace / orders / trip cost / dock wait → lakehouse `gold` (`fact_trip`)
   - telemetry: temperature, live truck position → KQL
2. Write the query: T-SQL for the Fabric SQL analytics endpoint / Warehouse, or KQL. Reuse the few-shot patterns.
3. Execute it through the best available path, and **say which one you used**:
   - a. `ambermoor-agent` MCP connected (FT6, paid F2): ask the published Fabric Data Agent the same question.
     Compare its answer and generated query with yours.
   - b. **Live Fabric via `tools/fabric_query.py`** (FT5, works on trial; read-only):
     - T-SQL: `python tools/fabric_query.py sql "<query>"` against the LH_Ambermoor SQL analytics endpoint.
     - KQL: `python tools/fabric_query.py kql "<query>"` against KQL_ColdChain.
     - It needs `fabric.endpoints.json` and `az login`.
   - c. Optional Preview MCPs, if Shekhar has connected them: the Fabric Data Warehouse or Eventhouse remote MCP.
     Verify their status and auth on Learn first.
   - d. Otherwise run an equivalent query with DuckDB over `data/generated/` and label the answer
     **"LOCAL REPLICA, not Fabric"**. Note any T-SQL → DuckDB dialect change you made.
   - e. If none is possible, hand Shekhar the query to run in the SQL analytics endpoint or KQL queryset.
4. Answer in business language first, then the query. Never fabricate rows. If the data can't answer it, say so.

## Eval mode (`eval`)
For each question Q1–Q10 in `agent/golden_answers.json`:
1. Answer it as above, without reading the golden values first.
2. Compare with the golden values, using the tolerance below.
3. Print a table with columns: question, your answer, golden, PASS/FAIL, path used.

For every FAIL, propose the smallest change to `agent/instructions.md` or a new few-shot that would fix it.
Treat prompt changes like code: one change, rerun, compare.

Tolerance:
- Exact for counts and IDs.
- ±0.1 percentage points for rates.
- ±0.5% for revenue and trip cost.
- ±0.05 h for dock-wait / drive-time averages.

## Export mode (`export`)
Check that the artefacts are ready for a Fabric Data Agent:
- `agent/instructions.md` stays under the agent-instructions size limit. Verify the current limit on Learn
  before quoting a number.
- Few-shot files are flat JSON objects `{ "question": "query" }`. This is the format used for bulk import in the
  Fabric Data Agent tutorial repo. Re-verify the import format on Learn.
- The agent description (top of `agent/instructions.md`) is specific. When the agent is published, this
  description becomes the MCP tool description that clients use for routing.

Then list the manual steps from `docs/specs/agent-ask-ambermoor.md` §Publish.

## Guardrails
- The data is synthetic. Still, phrase recall and food-safety answers as "in-scope per the data". Never present a
  synthetic result as a real food-safety determination.
- Excursions use the cumulative rule (≥ 30 min above 5.0 °C). Point out the naive "any reading > 5 °C" trap
  if the user's question implies it.

# Fast track: Fabric App + "Ask Ambermoor" agent working this weekend (Sat 10 – Sun 11 Oct)

Run it with `/fast-track next` in Claude Code (repo root), or step by step with `/fast-track FT3`.
Time boxes are rough estimates. Steps marked 🖱️ are portal clicks you do; 🤖 is what Claude Code does.
Nothing is written to Fabric without your OK (CLAUDE.md safety rules).

| Step | When | Outcome | DP-700 credit |
|---|---|---|---|
| FT0 Prep | Sat AM (~1 h) | Tenant settings, workspaces, test users, local toolchain | L0 (part) |
| FT1 Data in | Sat (~1 h) | `LH_Ambermoor` bronze + gold, acceptance PASS | L1, L3 (part) |
| FT2 Eventhouse | Sat (~30 min) | Telemetry in `KQL_ColdChain`, excursion KQL = 4 | L6 (part) |
| FT3 Semantic model | Sat (~45 min) | `SM_Ambermoor_Ops` with measures + RLS, validation queries pass | L7, L5 (part) |
| FT5 Ask Ambermoor (Claude Code) | Sat eve (~1 h) | `/ask-ambermoor eval` against live Fabric, Q1–Q8 | — |
| FT4 Fabric App | Sun (~3–4 h) | Freshness Command Center live, RLS + writeback tested | — (Preview) |
| FT6 Fabric Data Agent on F2 | Sun PM (~1.5 h) | Published agent + MCP into Claude Code | — |

FT5 comes before FT4 on purpose. It's cheap, and it proves the gold data that the app will show.

---

## FT0 Prep
- 🖱️ **Tenant settings** (Admin portal): *Fabric Apps (preview)*; the semantic-model **Execute Queries REST API**
  setting (*verify* exact label). For FT6: **XMLA endpoint**, **Fabric data agent**, **Copilot and Azure OpenAI**,
  **cross-geo processing/storing for AI** if your region needs it.
- 🖱️ Note your **trial capacity region** (Admin portal → Capacity settings → Trial). The F2 in FT6 must be in the
  **same region**. A third-party write-up reports that data agents can't query sources in another region.
- 🖱️ Create workspaces `WS-AMBERMOOR-DEV` and `WS-AMBERMOOR-APP` on the trial capacity.
- 🖱️ Create test users in Entra: `qa.p03@<tenant>` and `ops.director@<tenant>`. Don't add them to DEV.
- 🤖 Local checks:
  - Node **22**: the `dataapp` template asks for v22; Rayfin needs 20+.
  - Python 3.11+, `az login`.
  - `npm install -g @playwright/cli@latest`, used by the template's validation flow.
  - Microsoft **ODBC Driver 18 for SQL Server**, used by `tools/fabric_query.py`.
  - `claude mcp list`: `fabric` + `microsoft-learn` connected.

## FT1 Data in  [D2]
1. 🤖 `python tools/generate_ambermoor_data.py --out data/generated --seed 42` → `python tools/verify_golden.py`
   (9× PASS).
2. 🤖 Optional, shift-left: `python tools/run_notebooks_local.py --data data/generated`. Needs Java 17+ and pyspark.
3. 🖱️ In DEV, create lakehouse `LH_Ambermoor` with **schemas enabled**. Upload the 18 `.parquet` files to
   `Files/landing/ambermoor/`. 🤖 Alternatively, Claude uploads via the `fabric` MCP OneLake tools, after your OK.
4. 🖱️ Create notebooks `NB_01_load_bronze` and `NB_03_gold_fasttrack` from `fabric/notebooks/`. Attach
   `LH_Ambermoor` as the default lakehouse.
   - In NB_03's parameter cell, set `upn_overrides = {"P03": "qa.p03@<tenant>"}`.
5. ✅ NB_01 prints `PASS: all bronze tables match the manifest`. NB_03 prints `PASS: gold matches golden answers`.

## FT2 Eventhouse  [D2]
1. 🖱️ In DEV, create Eventhouse `EH_Ambermoor` → KQL database `KQL_ColdChain`.
2. 🖱️ In a KQL queryset, run block 1 of `fabric/kql/coldchain.kql` (`.create-merge table`).
3. 🖱️ Get data → Local file → `data/generated/reefer_telemetry.csv` (~11 MB) → existing table `ReeferTelemetry`.
4. ✅ Run blocks 2–4. Expect 183,921 rows, **4** excursion shipments (all TRK-117), and **112** on the naive query.
5. Live streaming with Eventstream + `tools/reefer_simulator.py` waits for lab L6. It isn't needed for the demo.

## FT3 Semantic model  [D1]
Follow `fabric/semantic-model/SM_Ambermoor_Ops.md`:
1. Create the model.
2. Add relationships and measures.
3. Add the QA Manager and Ops Director roles.
4. Bind the Direct Lake **fixed identity**.
5. Give `qa.p03` and `ops.director` **Read + Build** on the model.

✅ Validation queries A–D match the golden answers.

## FT5 Ask Ambermoor in Claude Code (trial, no Data Agent)
1. 🖱️ Copy the SQL analytics endpoint host (LH_Ambermoor → SQL analytics endpoint → settings) and the KQL Query URI
   into `fabric.endpoints.json` (template: `fabric.endpoints.example.json`; the file is gitignored).
2. 🤖 Smoke test:
   - `python tools/fabric_query.py sql "SELECT TOP 5 * FROM gold.dim_facility" --format table`
   - `python tools/fabric_query.py kql "ReeferTelemetry | count"`
3. 🤖 `/ask-ambermoor eval` → Q1–Q8 through `fabric_query.py` against live Fabric.
   ✅ All PASS, or a logged prompt fix for each fail.
4. Try a cross-source question:
   *"Which customers received product made with onion lot ILOT-P02-ING02-20260908, and were any of those shipments
   on TRK-117?"*

## FT4 Fabric App (Preview)
1. 🤖 From the repo root, with your OK:
   ```bash
   npx rayfin init --list-templates        # confirm "dataapp" exists in your CLI version
   npm create @microsoft/rayfin@latest app -- --template dataapp
   cp templates/app-CLAUDE.md app/CLAUDE.md
   cd app && npm install
   ```
2. 🤖 Provision the app item with your OK:
   - `npx rayfin login`
   - `npx rayfin up --workspace-uri "<WS-AMBERMOOR-APP URL>"`
3. 🤖 Register the model: `npx fabric-app-data add ambermoor --from-url "<SM_Ambermoor_Ops URL>"`.
4. 🖱️ **Restart Claude Code from `app/`.** That cockpit has the template's agent instructions and the `rayfin` MCP.
   Prompt:
   > Implement ../docs/specs/app-command-center.md. Page 1 first: validate each visual with npm run validate:visual
   > and in the Fabric portal embed. Then page 2, then page 3 (writeback). Ask before every rayfin up.
5. 🖱️ Preview: `npm run dev`, then open the app item in Fabric and append `&devUri=http://localhost:5173` to the URL.
6. ✅ Run the acceptance tests in the spec. Most important: sign in as `qa.p03` and see only P03.

## FT6 Real Fabric Data Agent on F2
1. 🖱️ Azure portal → create a **Microsoft Fabric capacity**:
   - SKU **F2**
   - **same region as the trial**
   - you as capacity admin
2. 🖱️ Create `WS-AMBERMOOR-AGENT` and assign it to the F2.
3. 🖱️ Create data agent `DA_Ask_Ambermoor`. Add these sources:
   - `LH_Ambermoor` (tick the gold tables incl. `trace_genealogy`)
   - `SM_Ambermoor_Ops`
   - `KQL_ColdChain`
4. 🖱️ Paste `agent/instructions.md`. Bulk-import `agent/fewshots_lakehouse.json` and `agent/fewshots_kql.json`.
   Test Q1–Q8. Publish with the description from the instructions file.
5. 🤖 Connect the published agent to Claude Code (`docs/setup.md` §7), then run `/ask-ambermoor eval`. It now goes
   through the real agent and compares with the FT5 answers.
6. **If the agent can't read sources in the trial workspace**, use these fallbacks in order:
   - a. In `WS-AMBERMOOR-AGENT`, create `LH_Ambermoor_Agent` with **OneLake shortcuts** to the DEV gold tables, and
     point the agent at it. Learn says agents can query shortcut-backed tables.
   - b. Temporarily assign `WS-AMBERMOOR-DEV` to the F2 for the demo, then move it back.
7. 🖱️ **Pause the F2** in the Azure portal when you're done.
   - One third-party source quotes pay-as-you-go at about **$0.36/hour, ~$263/month always-on**, for US West 2
     (July 2026 list price).
   - That's approximate; check the Azure pricing calculator for your region and currency.

---

## 5-minute demo storyline
1. **Supplier notice** lands (`SN-2026-001`). In the app's Lot trace page, search the onion lot: 36 lots,
   10 customers, 145 cases shipped, 551 destroyed.
2. **Place holds**, then log a corrective action. Show the row landing in the app's SQL database.
3. Switch user to `qa.p03`. **RLS** shows only the Great Lakes Plant (P03).
4. **Ask Ambermoor**:
   - "Which shipments broke the cold chain in September and why?" → 4 TRK-117 shipments. The agent explains the
     30-minute rule versus 112 door-open spikes.
   - "Where are we late?" → P07 Southeast DC, Monday foodservice.
5. Close: one governed copy of the data in OneLake. The app, the model, the agent and Claude Code all read it,
   with security inherited from Fabric.

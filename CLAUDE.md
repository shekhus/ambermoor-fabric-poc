# FreshyFresh Ops — Microsoft Fabric POC

## Mission (priority order)
1. **Fast track (Sat 10 – Sun 11 Oct 2026).** Get the Fabric App (freshness & food-safety command center with
   writeback) and the "Ask FreshyFresh" agent working end to end.
   - Runbook: `docs/fast-track.md`; drive it with `/fast-track`.
   - Agent: Claude Code on trial first (FT5), then a real Fabric Data Agent on a paid F2 (FT6).
2. **DP-700 readiness.** Shekhar sits DP-700 before the client kickoff (~early Nov 2026). Labs resume after the
   fast track.
3. **Reusable implementation patterns.** Medallion, orchestration, governance, CI/CD for the client engagement.

Company: **FreshyFresh Foods**, a *fictional* refrigerated prepared-foods maker. Products: deli salads,
sides, dips, entrees, Mexican foods & tortillas, desserts, cut potatoes. Channels: retail + foodservice,
US/MX/CA. **All data is synthetic.** Never use real company or client data, brands, logos, plants, customers or
incidents. Never name real companies in demo content.

## Accuracy rules (non-negotiable)
- Never invent Fabric/Rayfin/Azure APIs, CLI flags, item properties, KQL or T-SQL functions. Verify first:
  `microsoft-learn` MCP (`microsoft_docs_search` / `microsoft_docs_fetch`), `fabric` MCP `docs_*` tools,
  Rayfin docs (`https://rayfin.ai/<route>.md`) or the `rayfin` MCP. If you could not verify, say so explicitly.
- Label every Fabric feature you use **GA**, **Preview**, or **status unverified**. Fabric changes monthly and
  your training data may be stale. Prefer the Learn page's current wording.
- Flag numbers you are not certain of (limits, SKUs, CU costs) as approximate, with the Learn page to check.
- Missing context (IDs, which workspace, which user): ask. Don't assume.

## Working with Shekhar
- AI engineer/consultant. Strong Spark + Databricks medallion background. **Fabric beginner.**
- When introducing a Fabric concept, give the Databricks analogue in one line (table below).
- Tag lab steps and answers with the DP-700 domain:
  - **[D1]** Implement & manage an analytics solution
  - **[D2]** Ingest & transform data
  - **[D3]** Monitor & optimize
  - **[—]** not on DP-700, as far as you can verify
- Bold the **interview keywords** (e.g. **Direct Lake**, **V-Order**, **shortcut**, **SCD Type 2**) and give one
  concrete example per concept.

## Environment
- Tenant: Shekhar's own. Capacity: **Fabric trial** (time-limited; check remaining days in the Fabric portal).
- Workspaces:
  - `WS-FRESHYFRESH-DEV`, `WS-FRESHYFRESH-TEST` (deployment pipeline), `WS-FRESHYFRESH-APP` (Fabric App): trial capacity.
  - `WS-FRESHYFRESH-AGENT`: FT6 only, on a **paid F2** capacity in the **same region as the trial**. Fabric Data
    Agents don't run on trial. Pause the F2 when idle.
- DEV items:
  - Lakehouse `LH_FreshyFresh`, schema-enabled: `bronze` / `silver` / `gold`
  - Warehouse `WH_FreshyFresh`
  - Semantic model `SM_FreshyFresh_Ops` (Direct Lake on `gold`)
  - Eventhouse `EH_FreshyFresh`, KQL DB `KQL_ColdChain`, table `ReeferTelemetry`
  - Eventstream `ES_ReeferTelemetry`
  - Pipeline `PL_FreshyFresh_Daily`, Dataflow Gen2 `DF_Customer_Master`
  - Notebooks `NB_01_load_bronze`, `NB_03_gold_fasttrack` (fast track); `NB_02_silver`, `NB_03_gold` (lab L3)
  - Gold extras for app/agent: `trace_genealogy` mart; `fact_shipment` has `otif`, `is_excursion`, `tor_minutes`
  - Fleet slice: `dim_truck`, gold `fact_trip` (dock wait, trip cost); GPS columns on `ReeferTelemetry`;
    dashboard `RTD_FreshyFresh_Fleet` (spec: `docs/specs/fleet-trucks.md`)
- IDs (workspace/item GUIDs) live in `CLAUDE.local.md` (gitignored). Ask if missing. Never hard-code them in committed files.

## Two cockpits: where to launch Claude Code
| Work | Launch from | MCP servers |
|---|---|---|
| Data platform, labs, docs, Ask FreshyFresh | repo root | `fabric`, `microsoft-learn` (+ `freshyfresh-agent` after FT6) |
| Fabric App (FT4) | `app/` | `rayfin` (written by Rayfin into `app/.mcp.json`; must run from the Rayfin project root) |

- The app uses the Rayfin `dataapp` template:
  - Reads: Microsoft's `fabric-app-data` SDK queries `SM_FreshyFresh_Ops` as the signed-in user.
  - Writes: Rayfin entities.
- Claude Code does not read `app/.agents/skills/`. Use the `rayfin-app` skill, which points you to those files.

## Repo map
- `tools/`
  - `generate_freshyfresh_data.py`: synthetic data + `golden_answers.json`
  - `verify_golden.py`: DuckDB cross-check
  - `reefer_simulator.py`: Eventstream replay
  - `fabric-token-header.mjs`: bearer token for the data agent MCP
  - `fabric_query.py`: **read-only** T-SQL/KQL against live Fabric (Ask FreshyFresh on trial)
  - `run_notebooks_local.py`: run the notebooks with local PySpark before using capacity
- `fabric/`
  - `notebooks/`: PySpark source, `.py`
  - `kql/`: Eventhouse queries
  - `sql/`: Warehouse T-SQL
  - `semantic-model/`: model spec, DAX measures, RLS, validation queries
- `agent/`: Ask FreshyFresh instructions, few-shot JSON in Fabric Data Agent import format, golden answers
- `docs/`:
  - `setup.md`, `architecture.md`, `phase-plan.md` (status lives here)
  - `data-model.md`: the data contract
  - `lab-log.md`
  - `specs/`: app and agent specs
- `templates/app-CLAUDE.md`: copied to `app/CLAUDE.md` after scaffolding the Rayfin app
- `data/generated/`: generated files (gitignored; regenerate with seed 42)

## Commands
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python tools/generate_freshyfresh_data.py --out data/generated --seed 42   # ~35 s, deterministic
python tools/verify_golden.py --data data/generated                   # must print all PASS
python tools/run_notebooks_local.py --data data/generated              # optional: Java 17+ and pyspark
python tools/fabric_query.py sql "SELECT TOP 5 * FROM gold.dim_facility" --format table   # needs fabric.endpoints.json
python tools/reefer_simulator.py --dry-run --limit 5                  # live: needs EVENTSTREAM_CONNECTION_STRING in .env
az login --tenant <TENANT_ID> --allow-no-subscriptions                # Fabric auth for MCP + token helper
claude mcp list                                                       # check servers are connected
```

## Fabric safety rules
- **Read-only by default.** Any create/update/delete on Fabric (MCP tool, REST, `rayfin up`, uploads) needs:
  1. a one-line plan,
  2. Shekhar's explicit OK in this session.
- Never delete workspaces, lakehouses, warehouses or capacities. Never use `rayfin up --force`.
- Target `WS-FRESHYFRESH-DEV` unless told otherwise. State the target workspace before every write.
- Never print, log or commit tokens, connection strings, `.env`, `CLAUDE.local.md` or `rayfin/.deployments.json`.
- Data agent and Fabric MCP answers may leave Fabric's compliance boundary. Synthetic data only.

## Conventions
- **Medallion:**
  - `bronze` = as delivered, plus `_ingested_at` and `_source_file`; overwrite per load.
  - `silver` = typed, deduplicated, conformed; **SCD Type 2** on customer via Delta `MERGE`.
  - `gold` = star schema with business-friendly names for **Direct Lake**.
- **Code-first.** Notebooks as `.py` source in `fabric/notebooks/`, KQL in `.kql`, T-SQL in `.sql`. Portal-only
  steps go into the lab's `docs/lab-log.md` entry as a click-path.
- Item naming prefixes: `LH_ WH_ SM_ EH_ KQL_ ES_ PL_ DF_ NB_ RPT_ RTD_ MAP_ APP_ DA_`.
- The data contract is `docs/data-model.md`. If a column changes, update the generator, the contract,
  `agent/` few-shots and the golden answers together, then rerun `verify_golden.py`.
- Business rules shared by the app, the agent and the model:
  - **OTIF** = on time (delivered ≤ requested + 1 h) AND all lines delivered in full.
  - **Fill rate** = cases shipped / cases ordered.
  - **Cold-chain excursion** = cumulative time above 5.0 °C ≥ 30 min, with 15-min readings.
  - **Waste rate** = (Aged Out + Damaged + QA Reject) cases / cases produced, per month.
  - These are POC rules; a real client's QA team must confirm them before any client use.

## Lab workflow
`/dp700-lab <id>` runs a lab. After each lab:
1. Append a `docs/lab-log.md` entry: what/why, DP-700 tag, Databricks analogue, gotcha, Learn link,
   GA/Preview status.
2. Write 3 exam-style questions with explanations.
3. Tick the lab in `docs/phase-plan.md`.

## Databricks → Fabric (conceptual, not 1:1; verify details on Learn)
| Databricks | Fabric |
|---|---|
| Unity Catalog catalog/schema | Workspace + Lakehouse (schemas) in OneLake; **OneLake catalog** for discovery |
| Volumes / DBFS | Lakehouse `Files/` |
| External location | **OneLake shortcut** (ADLS Gen2, S3, GCS, other OneLake items) |
| SQL warehouse | **Warehouse** (read/write T-SQL) or **SQL analytics endpoint** (read-only over a lakehouse) |
| Workflows / Jobs | Data Factory **pipelines**, notebook schedules |
| Structured Streaming / streaming ingest | **Eventstream** → **Eventhouse** (KQL) or Lakehouse; Spark streaming also available |
| AI/BI dashboards | Power BI on **Direct Lake** |
| Genie space | **Fabric Data Agent** (paid F2+; not on trial) |
| Databricks Apps | **Fabric Apps** via Rayfin SDK (**Preview**) |
| Asset Bundles | **Git integration** + **deployment pipelines** (or the `fabric-cicd` library; verify) |
| Cluster / SQL warehouse sizing | **Capacity** (CU) + Spark pools / Environments |
| System tables, job runs UI | **Monitoring hub**, Capacity Metrics app |

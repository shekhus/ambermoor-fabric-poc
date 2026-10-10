---
name: dp700-lab
description: Run a DP-700 hands-on lab (L0-L10) on the synthetic Ambermoor data in Microsoft Fabric. Use when Shekhar says "lab", "next lab", a lab id like L3, or wants to practise a DP-700 skill hands-on.
argument-hint: "[lab id, e.g. L3, or 'next']"
---

# DP-700 lab runner

Lab requested: $ARGUMENTS. If it is empty or `next`, take the first unticked lab in `docs/phase-plan.md`.

## Procedure
1. **Confirm the ground truth.** Read `docs/phase-plan.md` for status and `docs/data-model.md` for table and column names.
   Confirm the target workspace with Shekhar if it isn't `WS-AMBERMOOR-DEV`.
2. **Verify before teaching.** For every Fabric feature in the lab, check the current Learn page with the
   `microsoft-learn` MCP. Record **GA / Preview / unverified**. Re-check the lab's DP-700 tag against the study
   guide (https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/dp-700).
   An earlier session flagged an outline update on 19 Oct 2026; verify it.
3. **Plan.** Show the steps, tagged [D1]/[D2]/[D3], with the Databricks analogue in one line. Wait for OK before any
   Fabric write.
4. **Build code-first.** Write notebook source in `fabric/notebooks/`, T-SQL in `fabric/sql/`, KQL in `fabric/kql/`.
   For portal-only steps, give a precise click-path and let Shekhar click. That is exam practice too.
5. **Run the acceptance checks** listed for the lab. Compare numbers to `agent/golden_answers.json` where relevant.
6. **Log.** Append to `docs/lab-log.md` using the template there. Tick the lab in `docs/phase-plan.md`.
7. **Exam drill.** Write 3 exam-style questions from the lab: scenario-based, 4 options, with the answer and a
   2-line explanation of why each wrong option is wrong. Bold the **interview keywords**.

## Lab catalog
| Id | Lab | Domain | Core skills | Acceptance check |
|---|---|---|---|---|
| L0 | Workspaces, capacity, settings | D1 | Create the DEV/TEST/APP workspaces on trial; workspace roles; Spark settings (starter pool, environment); domain/tags (verify) | All 3 workspaces show trial capacity under License info |
| L1 | Land + bronze | D2 | Upload `data/generated/*.parquet` to `LH_Ambermoor` `Files/landing/ambermoor/`; run `NB_01_load_bronze` | 18 bronze tables; row counts = `data/generated/manifest.json` |
| L2 | Orchestrate | D2/D3 | `PL_Ambermoor_Daily`: parameters, Notebook activities, dependencies, retry, failure path; `DF_Customer_Master` (Dataflow Gen2) from a CSV | Pipeline run succeeds; a forced failure triggers the failure path |
| L3 | Silver + gold (PySpark) | D2 | Typing, dedupe, data-quality checks, **SCD Type 2** on customer with Delta `MERGE`, gold star schema | Gold OTIF/fill rate = golden Q4/Q6 |
| L4 | Warehouse | D2 | `WH_Ambermoor`; cross-database query from the lakehouse SQL endpoint; CTAS; stored procedure for incremental load; views | Warehouse revenue by channel = golden Q7 |
| L5 | Security | D1 | Workspace roles vs item permissions; Warehouse **RLS / CLS / DDM** (`fabric/sql/wh_security_reference.sql`); **OneLake security** roles on `LH_Ambermoor`; test as a second user | QA manager for P03 sees only P03 rows; emails are masked |
| L6 | Real-time | D2/D3 | `ES_ReeferTelemetry` (custom endpoint) + `tools/reefer_simulator.py` → `EH_Ambermoor`; ingest history CSV; KQL (`fabric/kql/coldchain.kql`); OneLake availability + **shortcut** into the lakehouse; Activator alert (optional) | KQL excursion query returns golden Q2 (4 shipments, TRK-117) |
| L7 | Direct Lake model | D1/— | `SM_Ambermoor_Ops` on gold; measures (OTIF, fill rate, waste %, excursion count); RLS role per facility | Model numbers = golden; RLS tested with a real second user |
| L8 | CI/CD | D1 | **Git integration** (connect, commit, update, branch-out); **deployment pipeline** DEV→TEST with deployment rules | TEST items point at TEST data after deploy |
| L9 | Monitor + optimize | D3 | Monitoring hub; Capacity Metrics app; Spark run details; Delta `OPTIMIZE` / **V-Order** / `VACUUM`; small-file problem; Warehouse query insights; KQL ingestion failures | Before/after file counts and timings recorded in the lab log |
| L10 | Mirroring + shortcuts | D2 | SQL database in Fabric (auto-replicated to OneLake) for QA holds; shortcut it into the lakehouse; compare with mirrored Azure SQL/Snowflake (concept) | A row inserted in the SQL database appears via the shortcut (note the latency) |

## Rules
- Fabric writes need Shekhar's OK (see CLAUDE.md, "Fabric safety rules").
- Don't hand over finished solutions for L3/L4 code before Shekhar has tried. Offer hints first, then the
  solution on request. Reference files in `fabric/` are labelled "reference".
- If a feature turns out to be unavailable on trial, say so, log it, and propose the closest alternative.

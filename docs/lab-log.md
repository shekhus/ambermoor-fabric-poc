# Lab log

Claude appends one entry per lab (newest first). Keep each entry short. It doubles as revision notes.

<!-- Template
## L<id> · <title> · <date> · [D1|D2|D3]
- **What / why:** …
- **Built:** files / Fabric items (workspace)
- **Databricks analogue:** …
- **Status:** GA | Preview | unverified, with the Learn link
- **Gotcha:** …
- **Interview keywords:** **…**, **…**
- **Exam drill:** 3 questions → answers + why-not explanations
- **Acceptance check:** result vs golden / expected
-->

## FT1 · Data in (bronze + fast-track gold) · 9 Oct 2026 · [D2]
- **What / why:** Landed 18 synthetic parquet files in `LH_FreshyFresh/Files/landing/ambermoor`, loaded `bronze`
  (NB_01), built app/agent-ready `gold` (NB_03_gold_fasttrack), and skipped silver for the fast track.
- **Built:** `WS-FRESHYFRESH-DEV` (Fabric Trial FTL64, West US 3): `LH_FreshyFresh` (schemas enabled),
  `NB_01_load_bronze`, `NB_03_gold_fasttrack`. Notebooks are imported from `build/notebooks/*.ipynb`
  (`tools/py_to_ipynb.py`), so no cell pasting.
- **Databricks analogue:** COPY INTO / Auto Loader from a Volume into bronze Delta, then a gold serving job.
- **Status:** Lakehouse and notebooks GA. Lakehouse schemas: *verify* GA/Preview on Learn
  (https://learn.microsoft.com/fabric/data-engineering/lakehouse-schemas).
- **Gotchas:**
  - Each notebook needs its own default lakehouse. NB_03 first ran with "No data sources added" and failed,
    so no `gold` schema appeared in the semantic-model picker.
  - The OneLake catalog lists each lakehouse twice: the lakehouse plus its **SQL analytics endpoint**. Pick the
    lakehouse icon.
  - Workspace settings: "License info" is now **Workspace type**.
- **Interview keywords:** **schema-enabled lakehouse**, **default lakehouse**, **SQL analytics endpoint**.
- **Acceptance check:** NB_01 PASS (18 tables = manifest). NB_03: 7/7 PASS (36 lots, 145 cases, 10 customers,
  4 excursions, on-time 94.81%, P02 OTIF 90.09%, fill rate 99.54%); `trace_genealogy` = 85,656 rows.

## FT3 · SM_FreshyFresh_Ops as code (TMDL) · 9 Oct 2026 · [D1]
- **What / why:** Created the Direct Lake model from the lakehouse in the portal (all gold tables). Then pulled its
  definition as **TMDL**, added 19 relationships, 15 measures, the date table and RLS roles with
  `tools/sm_patch_tmdl.py`, and pushed it back with `tools/sm_definition.py` (Fabric REST `getDefinition` /
  `updateDefinition`). No clicking in relationships or measures.
- **Built:** `WS-FRESHYFRESH-DEV`/`SM_FreshyFresh_Ops` (Direct Lake on OneLake, per `PBI_ProTooling` annotation).
- **Databricks analogue:** metric view / dataset defined in YAML and deployed by Asset Bundles. Here the model
  definition is TMDL deployed by REST (the same files Git integration stores).
- **Status:** Semantic model definition REST APIs: GA (Fabric REST v1,
  https://learn.microsoft.com/rest/api/fabric/semanticmodel/items/update-semantic-model-definition). TMDL view in
  the web editor shows "(Preview)".
- **Gotcha:** Close the web model editor (Editing mode) before `updateDefinition`, or it may save over you. Keep LF
  line endings in TMDL.
- **Interview keywords:** **Direct Lake**, **TMDL**, **RLS** (`USERPRINCIPALNAME()`), **date table**.
- **Acceptance check:** validation queries A–D via `npx fabric-app-data query`: all PASS (99.54% / 4 / 94.81%;
  P02 90.09% lowest; P01 Cut Potatoes 5.42%; 36 / 145 / 10).
- **Open:** add role members (Security), bind Direct Lake fixed identity, grant qa.p03 Read + Build.

## FT4 · Freshness Command Center deployed · 9 Oct 2026 · [—] (Fabric Apps = Preview)
- **What / why:** Rayfin `dataapp` template (Rayfin 1.36.2). Three pages:
  - **Plant pulse:** KPI tiles, waste trend, top waste SKUs, on-time heatmap with a channel toggle.
  - **Lot trace:** supplier-notice chip, recall scope, 36-lot grid with "Place hold", customers chart.
  - **Holds & actions:** writeback to QualityHold / CorrectiveAction / HoldUpdate.
- **Built:**
  - `app/src/queries/{pulse,trace,scope}` (DAX in `.dax`, factories, Vega-Lite JSON)
  - `app/src/pages/*`, `app/src/services/holds.service.ts`, `app/rayfin/data/*`
  - Deployed into the existing App item `WS-AMBERMOOR-APP` (still its name: the item keeps the workspace's first name), which created its Fabric SQL database.
- **Databricks analogue:** a Databricks App reading a SQL warehouse plus writing to Lakebase. Here the reads are DAX
  through the semantic model (RLS) and the writes go to Fabric SQL DB via Rayfin's Data API Builder.
- **Status:** Fabric Apps **Preview**. Rayfin docs: https://rayfin.ai/docs/deploy/fabric-apps.md
- **Gotchas:**
  - `rayfin up` asks before reusing a manually created App item. Enter = **No**; type `y`.
  - SUMMARIZECOLUMNS with a measure that's never blank (`+ 0`) cross-joins dimensions: 1,000 rows instead of 36.
  - Template rule: never pipe `validate:visual` output (it can hide a non-zero exit).
- **Interview keywords:** **Direct Lake**, **RLS via USERPRINCIPALNAME()**, **writeback**, **delegated identity**.
- **Acceptance check:**
  - validate:visual 5/5 PASS.
  - Trace summary 36 / 145 / 10 / 13 shipments / 551 destroyed = golden.
  - `rayfin up status` healthy.
- **Open:**
  - In-portal smoke test and hold writeback (AT5).
  - RLS as qa.p03 (AT4).
  - DB-level facility policy for holds; today the UI scopes holds by the model's RLS-visible facilities.

## FT4 fixes after first portal run · 9 Oct 2026 · [D1]
- **`Waste Cases (Operational)` sliced by reason showed the SKU total for every reason.**
  - Cause: `CALCULATE(…, col IN {…})` **replaces** the existing filter on that column.
  - Fix: `KEEPFILTERS(…)` in the measure. Pushed via `updateDefinition`; A–D re-validated PASS.
  - **Exam keyword: KEEPFILTERS.**
- **Scope showed 9 facilities.** `SUMMARIZECOLUMNS` over `dim_facility` returned a blank row although no fact has
  orphan facility keys (checked with `RELATED`). The query now filters blanks. Root cause: open (weekend).
- **Lot grid dates showed `T00:00…`.** DAX returns ISO date-times; `useTable` now trims date-format columns to
  `YYYY-MM-DD`.
- Redeployed with `rayfin up`. No reuse prompt once a deployment is recorded.

## FT4 · Portal smoke test + writeback · 10 Oct 2026 01:10 IST
- **Acceptance:**
  - AT1–AT3 values match golden in the embedded app (fill rate 99.54%, 4 excursions, recall 36/145/10/551,
    waste by reason correct after KEEPFILTERS).
  - AT6 `rayfin up status` healthy.
  - Writeback: hold `LP02-260908-005` created from Lot trace, then Released. Timeline rows written with the
    signed-in UPN.
- **Finding:** Fabric SSO sessions carry the user's email (`opened_by` = the deployer's UPN). That makes a
  claims-based Rayfin row policy feasible for facility-scoped holds (follow-up).
- **Open:**
  - AT4/AT5 RLS tests with `qa.p03`.
  - Clear the hold detail on tab switch.
  - Root cause of the blank `dim_facility` member.

## FT4 · RLS tested as a P03 user (AT4) · 21 Oct 2026 · [D1]
- **What/why:** sign in as the P03 QA-manager test user (a B2B guest, Viewer on WS-FRESHYFRESH-APP) and check the
  app shows P03 only. Proves the model's RLS reaches the Fabric App, because the app queries as the signed-in user.
- **Result: PASS.** The app shows "P03 · Great Lakes Plant" only: 35,338 cases, waste 1.46%, OTIF 91.1%,
  4 excursions (all TRK-117, based at P03). The header now has a "Viewing: <scope>" badge built from the
  RLS-filtered facility list, so it can't disagree with the data.
- **Three fixes were needed, in this order:**
  1. **Write bypasses RLS.** The test user had *All permissions* on SM_FreshyFresh_Ops (Write included), so the
     roles were ignored. Fix: remove access, re-grant **Read + Build** only. Workspace Admin/Member/Contributor
     also imply Write, so the user holds no role in DEV.
  2. **Empty roles.** Nobody was in QA Manager. Added the test user directly (not via a group).
  3. **"Cannot find table dim_date / dim_facility / fact_waste".** **Direct Lake** used **SSO** (default), so it
     read OneLake as the viewer, who has no lakehouse access. Fix: model Settings > Gateway and cloud
     connections > Maps to > Create a connection (OAuth 2.0, Shekhar's account, SSO **off**) = a **fixed
     identity**. Don't grant the viewer lakehouse access instead: they could then read every plant from OneLake
     and skip the model's RLS.
- **Databricks analogue:** a Genie space / AI/BI dashboard that runs with the owner's credentials, plus a row
  filter function on the table. In Fabric the row filter lives in the semantic model and only binds Read users.
- **Gotchas:**
  - A guest lands in their home tenant; open Fabric with `?ctid=<Kion tenant id>`.
  - Workspace **Manage access** is not item permissions: the model's own *Manage permissions* page is where
    Write hides.
  - RLS roles add up: someone in QA Manager and Ops Director sees everything.
- **Learn:** https://learn.microsoft.com/fabric/fundamentals/direct-lake-security-integration
  (permission requirements; "data-access rules aren't enforced for users who have Write permission").
- **Status:** Direct Lake, semantic model RLS, cloud connections: **GA**. Fabric Apps: **Preview**.
- **Interview keywords:** **Direct Lake**, **fixed identity vs SSO**, **RLS (USERPRINCIPALNAME())**,
  **Build permission**, **B2B guest UPN**.
- **Exam-style questions:**
  1. A Viewer in the workspace has Write on a Direct Lake model with RLS. What do they see? *All rows. RLS is
     not enforced for Write (or Admin/Member/Contributor) users.*
  2. Report users get "Cannot find table" on a Direct Lake model; the author sees data. Least-privilege fix?
     *Bind the model to a cloud connection with a fixed identity and SSO disabled; don't grant users lakehouse
     access.*
  3. Why add test users to roles directly instead of via an Entra group during a POC? *Group membership can
     take time to propagate and nested/mail groups add doubt; direct membership isolates the RLS rule itself.*
- **Open:** AT5 (a second plant user, e.g. P02, sees only P02).

## Fleet F1/F3/F5 · data, dashboard and model as code · 21 Oct 2026 · [D1][D2]
- **What:** fleet data loaded (F1), `RTD_FreshyFresh_Fleet` built from JSON (F3), model §6 pushed (F5), and a
  "Fleet & freight" tab in the app. All by REST from Claude Code; no portal clicks.
- **Acceptance:** NB_03 asserts PASS (Q9 14, Q10 $3,957,156.99); model E/F PASS (P08 $31.93 highest, P06 $19.05
  lowest); guest still sees P03 only; 7 RTD tile queries return rows; app validate:visual 3/3.
- **Gotchas (all hit today):**
  - **`///` in TMDL is a description, not a comment.** Before a relationship it fails updateDefinition with
    "Property 'description' is unknown".
  - **New Direct Lake tables need a refresh (framing)** after updateDefinition, or DAX says the measure "cannot be
    determined".
  - **Role members are not in the TMDL definition** that getDefinition returns; they survived updateDefinition.
    Members added in the portal stay in the service. Test with executeQueries + `impersonatedUserName`.
  - **`last` is a reserved word in KQL**: `let last = ...` fails with "incomplete fragment"; use `last_ts`.
  - An empty Real-Time Dashboard's definition is `{}`; the format is the ADX dashboard JSON schema
    (`dataexplorer.azure.com/static/d/schema/89/dashboard.json`), data source kind `kusto-trident`.
- **Databricks analogue:** Asset Bundles deploying a job, a Lakeview dashboard JSON and a metric view, then a
  `REFRESH` on the serving layer.
- **Status:** Real-Time Dashboard, KQL DB, Direct Lake, Fabric REST item definitions: **GA**. Fabric Apps:
  **Preview**. Dashboard schema version 89: **status unverified** for Fabric (worked here).
- **Interview keywords:** **item definition (updateDefinition)**, **framing**, **impersonatedUserName**,
  **Real-Time Dashboard**, **arg_max latest-state**.

## Rename to FreshyFresh + live golden eval · 21 Oct 2026 · [D1][D3]
- **What:** renamed the fictional company Ambermoor → FreshyFresh in the repo, the app, the docs and Fabric
  (workspaces and items, by REST `PATCH displayName`). Then ran `/ask-freshyfresh eval` on live Fabric through
  `tools/fabric_query.py` (ODBC Driver 18.7) and KQL.
- **Result:** Q1–Q10 **10/10 PASS** (recall 36 lots / 10 customers / 145 cases / 551 destroyed; 4 excursions on
  TRK-117, 158 cases rejected; P01 Cut Potatoes 5.42%; P07 Foodservice Monday 64.1%; fill 99.54%; 41 QA lots /
  1,594 cases; P07 14/14 dock-caused, 6.26 h; trip cost $3,957,156.99).
- **Gotchas:**
  - **A Delta table can be in OneLake and in the Direct Lake model but missing from the SQL analytics endpoint.**
    `gold.bridge_lot_ingredient` (21,927 rows) was absent from `INFORMATION_SCHEMA.TABLES`. Fix: Items - Refresh
    Sql Endpoint Metadata, scoped to that table (`POST .../sqlEndpoints/{id}/refreshMetadata`, LRO).
  - **Renames are by ID-safe for links, not for name lookups.** Tools that find items by `displayName` had to change
    with the rename. Rayfin names its app item after the workspace at first deploy; renaming the workspace is fine
    (`rayfin up --dry-run` reused the same item), but renaming the app item itself would create a new app.
  - The lakehouse rename renamed its SQL analytics endpoint too; Direct Lake kept working (bound by ID).
- **Databricks analogue:** `REFRESH TABLE` / `MSCK REPAIR` when the metastore misses a table that exists in storage.
- **Status:** SQL analytics endpoint metadata refresh API: **GA** (REST reference, Sep 2026). Item/workspace
  update API: **GA**. New metadata sync (`sp_dw_refresh_ext_table`): **Preview**, not enabled here.
- **Interview keywords:** **SQL analytics endpoint metadata sync**, **refreshMetadata**, **displayName vs ID**.
- **Exam-style questions:**
  1. A new lakehouse table is queryable in Spark but not in the SQL analytics endpoint. First fix? *Refresh the
     endpoint metadata (portal Refresh, or the refreshMetadata REST API).*
  2. You rename a lakehouse. What breaks? *Anything that refers to it by name (notebook code using the name, tools
     using displayName, SQL connection database name); ID-bound items such as Direct Lake models keep working.*
  3. How do you refresh one table's endpoint metadata instead of the whole lakehouse? *refreshMetadata with
     `tables: [{schema, tableNames}]` (max 25 per call); `recreateTables: true` drops and rebuilds them.*

## RLS for every fact · 21 Oct 2026 · [D1]
- **What:** six facts (shipment lines, lot↔ingredient bridge, QA tests, orders, ingredient receipts, supplier notices)
  had no path to `dim_facility`, so the QA Manager role did not filter them. Gold now carries `facility_id` on the
  four that lacked it, and each fact relates directly to `dim_facility` (star, no fact↔fact links).
- **How (all code, one command):** `tools/rls_links_apply.py` = push + run NB_03 (Job Scheduler) → SQL endpoint
  metadata refresh → TMDL get/patch/update (`tools/sm_add_facility_links.py`, add-only) → model refresh.
- **Result:** validation G as admin = full totals; impersonating the P03 guest = P03 rows only, equal to the SQL
  counts (4,087 / 4,559 / 3,147 / 539 / 405 / 0). The app's Ask tab no longer blocks any table.
- **Gotcha:** RLS on a dimension only filters tables that relationship paths reach. A fact with no relationship is
  fully visible to every role member: check every table, not just the ones on report pages.
- **Databricks analogue:** a row filter on every table in Unity Catalog, not just the dimension.
- **Status:** RLS, Direct Lake, Job Scheduler API: **GA**.
- **Exam-style question:** A role filters `dim_facility`. Which tables does it restrict? *Only tables reached from
  `dim_facility` through active relationships in the filter direction; unrelated tables are unfiltered.*

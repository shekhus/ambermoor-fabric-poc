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
- **What / why:** Landed 18 synthetic parquet files in `LH_Ambermoor/Files/landing/ambermoor`, loaded `bronze`
  (NB_01), built app/agent-ready `gold` (NB_03_gold_fasttrack), and skipped silver for the fast track.
- **Built:** `WS-AMBERMOOR-DEV` (Fabric Trial FTL64, West US 3): `LH_Ambermoor` (schemas enabled),
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

## FT3 · SM_Ambermoor_Ops as code (TMDL) · 9 Oct 2026 · [D1]
- **What / why:** Created the Direct Lake model from the lakehouse in the portal (all gold tables). Then pulled its
  definition as **TMDL**, added 19 relationships, 15 measures, the date table and RLS roles with
  `tools/sm_patch_tmdl.py`, and pushed it back with `tools/sm_definition.py` (Fabric REST `getDefinition` /
  `updateDefinition`). No clicking in relationships or measures.
- **Built:** `WS-AMBERMOOR-DEV`/`SM_Ambermoor_Ops` (Direct Lake on OneLake, per `PBI_ProTooling` annotation).
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
  - Deployed into the existing App item `WS-AMBERMOOR-APP`, which created its Fabric SQL database.
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

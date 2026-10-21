# Spec: FreshyFresh Command Center (Fabric App, Rayfin `dataapp` template), **Preview**

Hand this to Claude Code **from `app/`**:
> Implement ../docs/specs/app-command-center.md. Page 1 first. Validate each visual with npm run validate:visual
> and in the Fabric portal embed, then page 2, then page 3 (writeback). Ask before every rayfin up.

## Objective
Plant QA managers and the Ops director see freshness, food-safety and service KPIs for *their* scope. They act on
what they see: put lots on hold, log corrective actions, track updates. The writeback is real Fabric data in the
app's SQL database, so it can be reported on and queried later.

## Business narrative (the demo)
A supplier notice lands on 15 Sep: onion lot `ILOT-P02-ING02-20260908`.
1. The P02 QA manager opens the app and traces the lot to 36 finished lots and 10 customers.
2. She sees 145 cases shipped and 551 destroyed, then places holds and logs a corrective action.
3. The Ops director sees every open hold network-wide.

## Architecture (as scaffolded by the template)
- **Read.** Microsoft's `fabric-app-data` SDK through the template's `useSemanticModelQuery` hook queries
  `SM_FreshyFresh_Ops` (alias `ambermoor`).
  - The app runs embedded in the Fabric portal as the signed-in user, so the **model's RLS applies**.
  - All reads come from the model, including lot trace via `trace_genealogy`. One security model, one source.
- **Write.** Rayfin entities in the app's Fabric SQL database. Enable `services.data` with `dialect: mssql`; the
  template ships with it disabled.
- **No calls from the app to the Data Agent.** The agent lives next to the app (decided 9 Oct). This avoids the
  app-identity vs per-user RLS problem.

## Personas and scope
| Persona | Read scope | Writeback |
|---|---|---|
| QA manager (one facility) | Own facility, via model role **QA Manager** (`dim_facility[qa_manager_upn] = USERPRINCIPALNAME()`) | Create/update holds and actions for own facility |
| Ops director | All facilities, via model role **Ops Director** | Read all; update status of any |

## Pages
1. **Plant pulse.** Measures from `fabric/semantic-model/SM_FreshyFresh_Ops.md`.
   - KPI tiles: Cases Produced, Waste Rate %, OTIF %, Fill Rate %, Excursion Shipments, Open Holds (from app data).
   - Waste Rate % by month (line) vs network. Top 5 waste SKUs by reason (bar).
   - On Time % heatmap: requested weekday × channel. It should make the P07 Monday Foodservice dip visible.
     Use `dim_date[weekday]` × `dim_customer[channel]`.
2. **Lot trace.** DAX over `trace_genealogy`.
   - Search by ingredient lot, finished lot or supplier notice id.
   - Show ingredient lot → finished lots (SKU, production date, best-by) → shipments → customers, with cases
     shipped.
   - Cases destroyed for the same lots come from `fact_waste`: use TREATAS on the lot list.
   - "Place hold" button per finished lot.
3. **Holds & actions.** Writeback.
   - Tabs: Open / Released / Destroyed.
   - Hold detail: updates timeline, corrective actions, status changes.

## Entities (Rayfin `@entity` classes; follow the installed version's docs and agent rules)
| Entity | Fields | Notes |
|---|---|---|
| QualityHold | id (uuid), lot_id (text max 40), facility_id (text max 8), reason (text max 200), severity (Low/Medium/High/Critical; text max 10), status (Open/Released/Destroyed; text max 12), cases_on_hold (int), source_ref (text max 40, e.g. SN-2026-001), opened_by (text max 120), opened_at (date) | `@text` always with `max` |
| CorrectiveAction | id, hold (`@one` → QualityHold, FK `hold_id`), title (text max 200), owner_upn (text max 120), due_date (date), status (Open/Done/Cancelled; text max 12), root_cause_category (Supplier/Process/Equipment/People/Other; text max 12) | |
| HoldUpdate | id, hold (`@one` → QualityHold), note (text max 1000), author (text max 120), created_at (date) | append-only |

**Permissions.**
- Explicit decorator on every entity. Signed-in users only; `assetAccess: protected`.
- Facility-scoped rows for QA managers. The facility↔user mapping is not a Rayfin claim, so pick a mechanism from
  `https://rayfin.ai/docs/data/permissions.md` and document it. Options:
  - a `FacilityAssignment` entity keyed by user, or
  - `opened_by` from claims plus a facility check.
- Do not invent decorator options.

## Acceptance tests (expected values from `agent/golden_answers.json`)
| # | Test | Expected |
|---|---|---|
| AT1 | Ops director, page 1, full window | Fill Rate 99.54%; Excursion Shipments 4; OTIF lowest at P02 (90.09%) |
| AT2 | Lot trace `ILOT-P02-ING02-20260908` | 36 lots · 145 cases shipped · 10 customers · 551 destroyed |
| AT3 | Waste Rate %, Aug 2026, by facility × category | P01 / Cut Potatoes 5.42% on top |
| AT4 | Sign in as `qa.p03` (Read + Build on model; not Contributor+ on DEV) | Only P03 data on every page |
| AT5 | `qa.p03` creates a hold → row exists in app SQL database; P02 user can't see it | as stated |
| AT6 | `npx rayfin up status` after deploy | entities readable; hosting URL live |

## Later (not this weekend)
- Fabric deployment pipeline for the app (Rayfin has a deployment-pipelines guide).
- Email/Teams alerts on Critical holds (Activator).
- Shortcut the app's SQL database tables into the lakehouse so the agent can answer "which holds are still open?"
  (lab L10).

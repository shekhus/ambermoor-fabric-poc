# Phase plan: fast track first, then DP-700 labs

Today: Fri 9 Oct 2026. Client kickoff: ~early Nov 2026.
- **Book the DP-700 exam date: ________.** An earlier session flagged a skills-outline update on **19 Oct 2026**.
  If you sit after that date, study against the new outline (verify on the study guide).
- Claude keeps the checkboxes and notes current.

## Fast track: App + agent working (Sat 10 – Sun 11 Oct) → `docs/fast-track.md`, `/fast-track`
- [ ] FT0 Prep: tenant settings, trial region noted, DEV + APP workspaces, 2 test users, Node 22/ODBC/Playwright
- [x] FT1 Data in (9 Oct, 20:11 IST): bronze + `NB_03_gold_fasttrack` PASS (counts as L1 + part of L3)
- [x] FT2 Eventhouse: telemetry ingested, excursion KQL = 4 (part of L6). **21 Oct: 183,921 rows incl. GPS columns via `.ingest inline`; excursions = 4, naive = 112; `TruckLatestPosition()` = 48 trucks.**
- [x] FT3 Semantic model: measures + RLS, validation queries A–D pass (L7, part of L5). **9 Oct: model + measures + roles pushed as TMDL, A–D PASS. 21 Oct: role members set, fixed-identity connection bound (SSO off), test user Read+Build.**
- [ ] FT5 Ask Ambermoor in Claude Code via `fabric_query.py`: `/ask-ambermoor eval` Q1–Q8
- [ ] FT4 Fabric App (Preview): KPI page, lot trace, hold writeback, RLS tested as `qa.p03`. **9 Oct: 3 pages built + deployed to WS-AMBERMOOR-APP (status healthy); visuals validated vs golden. 10 Oct 01:10: portal smoke test PASS (AT1–AT3 values, AT6 healthy); writeback PASS (hold created → Released, timeline). 21 Oct: AT4 PASS: P03 guest test user sees only "P03 · Great Lakes Plant" (scope badge added). Open: P02 user isolation (AT5).**
- [ ] FT6 Fabric Data Agent on F2 (same region): published, MCP in Claude Code, eval re-run, **F2 paused**

## Fleet slice: trucks, live location, trip cost → `docs/specs/fleet-trucks.md` (added 21 Oct)
Before 28 Oct, or after the exam window. Local part done 21 Oct: generator, golden Q9/Q10, `verify_golden` 14 × PASS.
- [x] F1 Re-upload 19 files, re-run NB_01 + NB_03 (fact_trip checks PASS) [D2] **21 Oct: uploaded via OneLake DFS, notebooks updated via REST (P03 mapping kept), both runs Completed = all golden asserts PASS.**
- [x] F2 Eventhouse with GPS columns + `TruckLatestPosition()` (done with FT2, 21 Oct) [D2]
- [ ] F3 `RTD_Ambermoor_Fleet` dashboard, live replay of TRK-117 [D2] **21 Oct: 7-tile dashboard pushed as code (`tools/rtd_fleet_build.py`, schema 89), every tile query tested. Open: visual check in portal, parameters, live replay.**
- [ ] F4 Activator rule: warm load on moving truck [D3]
- [ ] F5 Model §6 + Fleet & freight page; `/ask-ambermoor eval` Q1–Q10 [D1] **21 Oct: model §6 pushed (`tools/sm_add_fleet.py`, roles kept) + refreshed: E/F PASS ($3,957,156.99; 14; P08 31.93 / P06 19.05); guest still P03-only. Fleet & freight tab deployed (validate:visual 3/3). Open: Q1–Q10 eval (needs ODBC 18).**

## Phase 1: DP-700 labs (Mon 12 – Wed 28 Oct)
Labs already partly covered by the fast track get a lighter pass: theory, exam traps and the missing pieces.

| Week | Labs | Domain focus |
|---|---|---|
| Wk 1 (12–18 Oct) | L0 settings + Git · L2 orchestrate · L3 silver/SCD2 + proper gold · L4 warehouse | D1, D2 |
| Wk 2 (19–25 Oct) | L5 security (WH RLS/CLS/DDM, OneLake security) · L6 live Eventstream · L10 mirroring + shortcuts | D1, D2 |
| Wk 3 (26–28 Oct) | L8 CI/CD (incl. the app via deployment pipelines) · L9 monitor + optimize (the fast track's CU usage is real data for this) | D1, D3 |

- [ ] L0 · [ ] L2 · [ ] L3 · [ ] L4 · [ ] L5 · [ ] L6 · [ ] L8 · [ ] L9 · [ ] L10
- [ ] (L1 and L7 done via FT1/FT3; revisit theory + exam drill only)
- [ ] Practice assessment on Microsoft Learn (free) ≥ 2 full runs; log weak areas in `docs/lab-log.md`

## Exam window (~29 Oct – 2 Nov): revision only, no new builds

## After the exam: harden the demo for the client conversation
- [ ] Rebuild gold through silver (L3) and repoint the model; app and agent keep working because column names are stable
- [ ] Deployment pipeline DEV → TEST for lakehouse, model, app (Rayfin deployment-pipelines doc) and agent
- [ ] Governance write-up: compliance boundary for agent/MCP answers, RLS identity model, capacity sizing

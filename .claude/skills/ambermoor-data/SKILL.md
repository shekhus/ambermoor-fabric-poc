---
name: ambermoor-data
description: Generate, verify, explain or load the synthetic Ambermoor refrigerated-foods dataset (lots, traceability, shipments, reefer telemetry, waste) and its golden answers. Use for questions about the data model, planted storylines, regenerating data, or uploading it to OneLake.
---

# Ambermoor synthetic data

All data is fictional. The contract is `docs/data-model.md`. Read it before writing any query or transform.

## Regenerate and verify
```bash
python tools/generate_ambermoor_data.py --out data/generated --seed 42 [--upn-domain <your-tenant-domain>]
python tools/verify_golden.py --data data/generated     # all PASS or stop and investigate
cp data/generated/golden_answers.json agent/golden_answers.json   # only if the generator changed
```
- Seed 42 with the default window (2026-07-01, 90 days) is the shared baseline. Golden answers depend on it.
- `--upn-domain` sets the synthetic `qa_manager_upn` values on `dim_facility`. For real RLS tests, map one or two
  facilities to real test-user UPNs in the silver/gold layer. Don't edit the generator for that.

## Load to Fabric (needs Shekhar's OK, target `WS-AMBERMOOR-DEV`)
1. Upload the 18 `.parquet` files to `LH_Ambermoor` → `Files/landing/ambermoor/`.
   Use the portal upload, or the `fabric` MCP OneLake upload tool (check its current name with the server's tool list).
2. Run `fabric/notebooks/nb_01_load_bronze.py` (as notebook `NB_01_load_bronze`) to create the `bronze.*` tables.
3. Telemetry: `reefer_telemetry.csv` → Eventhouse `KQL_ColdChain` table `ReeferTelemetry`, through Get data → Local file.
   The live stream comes later from `tools/reefer_simulator.py` (lab L6).

## Planted storylines (what the data is built to reveal)
1. **Mock recall.** Supplier notice `SN-2026-001` (2026-09-15) flags onion lot `ILOT-P02-ING02-20260908`.
   - Trace it through `bridge_lot_ingredient` → `fact_lot` → `fact_shipment_line` → `fact_shipment` → `dim_customer`.
   - In scope: 36 finished lots, 145 cases shipped to 10 customers. 551 cases were destroyed before shipping.
2. **Cold chain.** Truck `TRK-117` (P03 fleet) has a reefer fault on shipments departing 2026-09-10..14.
   - 4 shipments show cumulative time above 5 °C ≥ 30 min. Customers rejected them, and waste reason = `Temp Excursion`.
   - Trap: 112 shipments have *some* reading above 5 °C (single door-open spikes). The rule must use cumulative minutes.
3. **Over-production.** P01 over-planned Cut Potatoes in August (×1.6). Its waste rate is about 10× the network median.
4. **Late Mondays.** P07 Southeast DC, Foodservice, Monday deliveries: about 64% on time vs ~93% overall.

Exact values: `agent/golden_answers.json`. Treat them as the eval oracle for the app and the agent.

## Changing the data
Edit the generator constants. Then update, in the same change:
- `docs/data-model.md`
- `agent/fewshots_*.json` and `agent/instructions.md`
- `agent/golden_answers.json`

Rerun `verify_golden.py`.

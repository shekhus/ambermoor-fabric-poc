# Data contract: Ambermoor Fresh Ops (synthetic)

**Generator:** `tools/generate_ambermoor_data.py` (seed 42, window 2026-07-01 → 2026-09-28, UTC).

Everything is fictional. Plant names, brands (Homestyle Kitchen, Bistro Select, Casa Fresca, Harvest Table),
customers, suppliers, shelf lives and prices are placeholders, **not** any real company's data. Ambermoor Fresh
Foods is an invented company. Shelf lives, min-life rules and the 5 °C excursion threshold are demo assumptions.
A real client's QA team must validate them before reuse.

## Grain and keys
| Table | Grain / PK | Rows (seed 42) | Notes |
|---|---|---|---|
| dim_facility | facility_id | 8 | P01–P06 plants, P07/P08 DCs; `qa_manager_upn` for RLS demos |
| dim_product | sku_id | 49 | 7 categories; Retail (2 lb ×6) and Foodservice (10 lb ×2) packs; `min_remaining_days` = customer min-life |
| dim_customer | customer_id | 120 | channel, ship_from_facility_id; `contact_email`/`contact_phone`/`credit_limit_usd` exist for CLS/DDM labs |
| dim_supplier | supplier_id | 8 | |
| dim_ingredient | ingredient_id | 30 | `is_high_risk_raw`, `allergen` |
| dim_date | date | 174 | |
| fact_ingredient_receipt | ingredient_lot_id | 2,040 | weekly receipts (Tuesdays) per plant × ingredient |
| fact_lot | lot_id | 5,416 | finished-goods lots; `best_by_date`, `has_failed_qa` |
| bridge_lot_ingredient | lot_id + ingredient_id | 21,927 | **traceability genealogy** |
| fact_quality_test | test_id | 16,248 | 3 tests per lot; ~0.8% micro fails |
| fact_order | order_id | 3,317 | |
| fact_order_line | order_id + order_line | 16,519 | ordered / shipped / delivered cases; net revenue on delivered |
| fact_shipment | shipment_id (1:1 order) | 3,317 | truck, timestamps, `on_time`, `rejected_on_delivery` |
| fact_shipment_line | shipment_id + order_line + lot_id | 20,837 | **lot → customer link** (FEFO allocation) |
| fact_waste | waste_id | 310 | reasons: Aged Out, Damaged, QA Reject, Supplier Recall, Temp Excursion |
| fact_inventory_daily | snapshot_date + facility_id + sku_id | 12,960 | plant-level (not lot-level) |
| fact_supplier_notice | notice_id | 1 | SN-2026-001 |
| reefer_telemetry | ts + shipment_id | 183,921 | 15-min readings in transit → Eventhouse `ReeferTelemetry` |

Row counts are reproducible with seed 42. `data/generated/manifest.json` is the source of truth after a run.

## Relationships (star + bridge)
- `fact_lot.sku_id` → `dim_product`; `fact_lot.facility_id` → `dim_facility`.
- `bridge_lot_ingredient.lot_id` → `fact_lot`; `.ingredient_lot_id` → `fact_ingredient_receipt` → `dim_ingredient`,
  `dim_supplier`.
- `fact_order_line.order_id` → `fact_order` → `dim_customer`; `fact_shipment.order_id` → `fact_order`.
- `fact_shipment_line.shipment_id` → `fact_shipment`; `.lot_id` → `fact_lot`.
- `ReeferTelemetry.shipment_id` → `fact_shipment` (cross-engine join: KQL → lakehouse via OneLake shortcut, lab L6).

## Medallion targets
- **bronze**: 1:1 with the files, plus `_ingested_at` and `_source_file`.
- **silver**:
  - Types enforced; dedupe on PK.
  - `dim_customer` as **SCD Type 2** (`valid_from`, `valid_to`, `is_current`). To practise, apply a change file
    in lab L3.
- **gold**:
  - Business-ready star schema with the same table names as above, consumed by `SM_Ambermoor_Ops` (Direct Lake),
    the agent and the app.
  - Keep the gold column names identical to this contract. `agent/` few-shots depend on them.

## Gold additions from `NB_03_gold_fasttrack` (used by the model, app and agent)
| Table | Added | Why |
|---|---|---|
| fact_shipment | `in_full`, `otif`, `tor_minutes`, `max_temp_c`, `is_excursion`, `requested_delivery_date`, `ship_date` | KPIs as simple measures; cold-chain flag without a cross-engine join |
| fact_order_line | `ship_from_facility_id` | direct star join to `dim_facility` (no snowflake path, so RLS filters cleanly) |
| trace_genealogy | new, 85,656 rows (seed 42): ingredient lot → finished lot → shipment line → customer | one-query recall/trace for app and agent |
| dim_facility | `qa_manager_upn` overridable via `upn_overrides` | map real test users for RLS |

## Business rules (shared by model, app and agent)
| Metric | Definition |
|---|---|
| OTIF | delivered_ts ≤ requested_delivery_ts + 1 h AND all order lines `cases_delivered = cases_ordered` |
| Fill rate | Σ cases_shipped / Σ cases_ordered |
| Waste rate | (Aged Out + Damaged + QA Reject cases, by waste_date) / cases produced (by production_date), same period |
| Excursion | Σ(readings with temp_c > 5.0) × 15 min ≥ 30 min per shipment |
| Best-selling | by cases delivered |

## Planted storylines (golden answers in `agent/golden_answers.json`)
| # | Story | Where it shows | Expected |
|---|---|---|---|
| Q1 | Supplier notice on onion lot `ILOT-P02-ING02-20260908` | bridge → lots → shipments → customers | 36 lots; 145 cases shipped to 10 customers; 551 cases destroyed |
| Q2 | TRK-117 reefer fault, departures 2026-09-10..14 | ReeferTelemetry + waste | 4 excursion shipments; 158 cases rejected (naive query: 112 shipments) |
| Q3 | P01 over-planned Cut Potatoes in August | fact_lot vs fact_waste | P01 Cut Potatoes 5.42% vs network median 0.54% |
| Q4 | P07 Southeast DC late on Monday Foodservice deliveries | fact_shipment | 64.1% on time vs 94.8% overall |
| Q5–Q8 | Top SKUs, fill rate, revenue by channel, QA rejects | facts | see JSON |

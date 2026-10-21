# SM_FreshyFresh_Ops: Direct Lake semantic model (fast track FT3)                [D1]

Built on `LH_FreshyFresh` **gold** after `NB_03_gold_fasttrack`. One model serves three consumers:
the Fabric App (via the template's `fabric-app-data` SDK), the Fabric Data Agent, and Power BI.
DAX below was written against this exact gold schema but **has not been executed in a model yet**.
Run the validation queries at the end before building UI on it.

Databricks analogue: a Unity Catalog metric view / AI/BI dataset, but with **Direct Lake** (reads Delta in OneLake
directly, no import refresh) and model-level **RLS**.

## 1. Create
1. Lakehouse `LH_FreshyFresh` → **New semantic model**. Name it `SM_FreshyFresh_Ops` and pick these `gold` tables:
   - Dims: `dim_facility`, `dim_product`, `dim_customer`, `dim_date`
   - Facts: `fact_order_line`, `fact_shipment`, `fact_lot`, `fact_waste`, `fact_inventory_daily`, `trace_genealogy`
2. The UI may offer Direct Lake on OneLake vs on SQL endpoint. Default is fine for the POC. *Verify* the current
   options and status on Learn.
3. Mark `dim_date` as a date table (`dim_date[date]`).

## 2. Relationships (all many-to-one, single direction, dim → fact; no fact↔fact links = no ambiguous paths)
| From (many) | To (one) |
|---|---|
| `fact_order_line[ship_from_facility_id]`, `fact_shipment[ship_from_facility_id]`, `fact_lot[facility_id]`, `fact_waste[facility_id]`, `fact_inventory_daily[facility_id]`, `trace_genealogy[facility_id]` | `dim_facility[facility_id]` |
| `fact_order_line[sku_id]`, `fact_lot[sku_id]`, `fact_waste[sku_id]`, `fact_inventory_daily[sku_id]`, `trace_genealogy[sku_id]` | `dim_product[sku_id]` |
| `fact_order_line[customer_id]`, `fact_shipment[customer_id]`, `trace_genealogy[customer_id]` | `dim_customer[customer_id]` |
| `fact_order_line[requested_delivery_date]`, `fact_shipment[requested_delivery_date]`, `fact_lot[production_date]`, `fact_waste[waste_date]`, `fact_inventory_daily[snapshot_date]` | `dim_date[date]` |

`trace_genealogy` has no date relationship on purpose. It is a lookup mart; filter it by `ingredient_lot_id` or
`lot_id`.

## 3. Measures (home table: create a `_Measures` table, or put them on `fact_shipment`)
```dax
Cases Ordered = SUM ( fact_order_line[cases_ordered] )
Cases Shipped = SUM ( fact_order_line[cases_shipped] )
Cases Delivered = SUM ( fact_order_line[cases_delivered] )
Fill Rate % = DIVIDE ( [Cases Shipped], [Cases Ordered] )
Net Revenue = SUM ( fact_order_line[net_revenue_usd] )

Shipments = COUNTROWS ( fact_shipment )
On Time % = DIVIDE ( CALCULATE ( [Shipments], fact_shipment[on_time] = TRUE () ), [Shipments] )
OTIF % = DIVIDE ( CALCULATE ( [Shipments], fact_shipment[otif] = TRUE () ), [Shipments] )
Excursion Shipments = CALCULATE ( [Shipments], fact_shipment[is_excursion] = TRUE () )

Cases Produced = SUM ( fact_lot[cases_produced] )
Waste Cases (Operational) =
    CALCULATE ( SUM ( fact_waste[cases] ), fact_waste[reason] IN { "Aged Out", "Damaged", "QA Reject" } )
Waste Rate % = DIVIDE ( [Waste Cases (Operational)], [Cases Produced] )
Waste Cost = SUM ( fact_waste[cost_usd] )
Recall Cases Destroyed = CALCULATE ( SUM ( fact_waste[cases] ), fact_waste[reason] = "Supplier Recall" )

Cases On Hand (Latest) =
VAR LastSnapshot = MAX ( fact_inventory_daily[snapshot_date] )
RETURN
    CALCULATE ( SUM ( fact_inventory_daily[cases_on_hand] ), fact_inventory_daily[snapshot_date] = LastSnapshot )
```
Format: percentages as `0.0%`, revenue as currency, cases as whole numbers.

## 4. Security (RLS) and access
- Role **QA Manager**: on table `dim_facility`, filter `[qa_manager_upn] = USERPRINCIPALNAME()`.
  - To map real test users, set `upn_overrides` in `NB_03_gold_fasttrack`, e.g. `{"P03": "qa.p03@<tenant>"}`,
    and re-run it.
- Role **Ops Director**: no filter (`TRUE()`). With roles defined, a Read-only user must be in a role to see data.
- Add members under the model's **Security** page.
- **Test users must NOT be Contributor/Member/Admin on `WS-FRESHYFRESH-DEV`.** Those roles bypass RLS.
  Give them **Read + Build** on the semantic model only. The app's DAX queries go through the semantic-model query
  API, which needs Build.
- **Direct Lake identity.** For model-only consumers, bind the model's OneLake connection to a **fixed identity**
  (your account or a service principal), with SSO for queries off. Users then don't need lakehouse access.
  See [Direct Lake security integration](https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-security-integration).
  This is the same pattern the Vestra demo README documents.

## 5. Validation queries (run in the model's DAX query view; expected values from `agent/golden_answers.json`)
```dax
// A. Headline KPIs: expect Fill Rate 99.54%, Excursion Shipments 4, On Time 94.81%
EVALUATE
ROW ( "Fill Rate %", [Fill Rate %], "Excursion Shipments", [Excursion Shipments], "On Time %", [On Time %] )

// B. OTIF by facility: expect P02 90.09% lowest, P06 95.20% highest (golden Q4)
EVALUATE
SUMMARIZECOLUMNS ( dim_facility[facility_id], "OTIF %", [OTIF %] )
ORDER BY [OTIF %] ASC

// C. Waste rate Aug 2026: expect P01 / Cut Potatoes 5.42% at the top (golden Q3)
EVALUATE
TOPN (
    5,
    SUMMARIZECOLUMNS (
        dim_facility[facility_id], dim_product[category],
        TREATAS ( { "2026-08" }, dim_date[year_month] ),
        "Waste Rate %", [Waste Rate %]
    ),
    [Waste Rate %], DESC
)

// D. Mock recall: expect 36 lots, 145 cases shipped, 10 customers (golden Q1)
EVALUATE
CALCULATETABLE (
    ROW (
        "Lots", DISTINCTCOUNT ( trace_genealogy[lot_id] ),
        "Cases shipped", SUM ( trace_genealogy[cases_shipped] ),
        "Customers", DISTINCTCOUNTNOBLANK ( trace_genealogy[customer_id] )
    ),
    trace_genealogy[ingredient_lot_id] = "ILOT-P02-ING02-20260908"
)
```
If a number is off, compare with `NB_03_gold_fasttrack`'s acceptance cell first. That narrows it down to the
data or the DAX.

## 6. Fleet extension (pushed 21 Oct 2026 with `tools/sm_add_fleet.py`; validation E/F PASS)
Adds trucking cost and dock wait for the Power BI / Fabric App "Fleet & freight" page. Live position stays in KQL
(Real-Time Dashboard); the model only holds trip history. Apply with the same TMDL route as FT3, after
`NB_03_gold_fasttrack` has written `gold.fact_trip` and `gold.dim_truck`.

| From (many) | To (one) |
|---|---|
| `fact_trip[ship_from_facility_id]` | `dim_facility[facility_id]` (RLS flows to trips) |
| `fact_trip[customer_id]` | `dim_customer[customer_id]` |
| `fact_trip[truck_id]` | `dim_truck[truck_id]` |
| `fact_trip[requested_delivery_date]` | `dim_date[date]` |

```dax
Trips = COUNTROWS ( fact_trip )
Trip Cost = SUM ( fact_trip[trip_cost_usd] )
Freight Cost per Case = DIVIDE ( [Trip Cost], SUM ( fact_trip[cases_delivered] ) )
Avg Dock Wait (h) = AVERAGE ( fact_trip[dock_wait_h] )
Avg Drive (h) = AVERAGE ( fact_trip[drive_h] )
Dock-Delayed Late Trips = CALCULATE ( [Trips], fact_trip[is_dock_delayed] = TRUE (), fact_trip[on_time] = FALSE () )
```

```dax
// E. Fleet: expect Trip Cost 3,957,156.99 and Dock-Delayed Late Trips 14 (golden Q9/Q10)
EVALUATE ROW ( "Trip Cost", [Trip Cost], "Dock-Delayed Late Trips", [Dock-Delayed Late Trips] )

// F. Freight cost per case by facility: expect P08 31.93 highest, P06 19.05 lowest
EVALUATE SUMMARIZECOLUMNS ( dim_facility[facility_id], "Cost per case", [Freight Cost per Case] )
ORDER BY [Cost per case] DESC
```

## Optional accelerator: let Claude Code build the model
Microsoft's Power BI Modeling/Authoring MCP server can create tables, relationships, measures and roles
(local server GA v1.0.0, Sept 2026; hosted endpoint Preview). It needs the XMLA endpoint (Read Write).
*Verify* that XMLA Read Write is available on your trial capacity and that the local server supports your OS
(the local server doesn't run on macOS). Otherwise the portal steps above take ~20 minutes.

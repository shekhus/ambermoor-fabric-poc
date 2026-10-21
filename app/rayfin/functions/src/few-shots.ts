// Question -> DAX examples for the Ask function. Each one was run against the live SM_Ambermoor_Ops (21 Oct 2026)
// and matches agent/golden_answers.json where a golden answer exists. Keep them RLS-safe: no BLOCKED_TABLES.
export const FEW_SHOTS: ReadonlyArray<{ question: string; dax: string }> = [
    {
        question: "Which plant has the highest waste rate?",
        dax: `EVALUATE
TOPN ( 8, SUMMARIZECOLUMNS ( dim_facility[facility_id], dim_facility[facility_name], "Waste Rate %", [Waste Rate %] ), [Waste Rate %], DESC )
ORDER BY [Waste Rate %] DESC`,
    },
    {
        question: "Show OTIF and on-time % by plant",
        dax: `EVALUATE
SUMMARIZECOLUMNS ( dim_facility[facility_id], dim_facility[facility_name], "OTIF %", [OTIF %], "On Time %", [On Time %], "Shipments", [Shipments] )
ORDER BY [OTIF %] ASC`,
    },
    {
        question: "Which shipments had a cold-chain excursion, and on which truck?",
        dax: `EVALUATE
CALCULATETABLE (
    SELECTCOLUMNS ( fact_shipment, "Shipment", fact_shipment[shipment_id], "Truck", fact_shipment[truck_id],
        "Plant", fact_shipment[ship_from_facility_id], "Minutes above 5 C", fact_shipment[tor_minutes], "Max temp C", fact_shipment[max_temp_c] ),
    fact_shipment[is_excursion] = TRUE ()
)
ORDER BY [Minutes above 5 C] DESC`,
    },
    {
        question: "Which customers received product made with ingredient lot ILOT-P02-ING02-20260908?",
        dax: `EVALUATE
CALCULATETABLE (
    SUMMARIZECOLUMNS ( dim_customer[customer_id], dim_customer[customer_name],
        "Finished lots", DISTINCTCOUNT ( trace_genealogy[lot_id] ), "Cases shipped", SUM ( trace_genealogy[cases_shipped] ) ),
    trace_genealogy[ingredient_lot_id] = "ILOT-P02-ING02-20260908",
    NOT ISBLANK ( trace_genealogy[customer_id] )
)
ORDER BY [Cases shipped] DESC`,
    },
    {
        question: "Waste rate by month for P02",
        dax: `EVALUATE
CALCULATETABLE (
    SUMMARIZECOLUMNS ( dim_date[year_month], "Waste Rate %", [Waste Rate %], "Waste cases", [Waste Cases (Operational)] ),
    dim_facility[facility_id] = "P02"
)
ORDER BY dim_date[year_month]`,
    },
    {
        question: "What are the 5 most expensive delivery lanes?",
        dax: `EVALUATE
TOPN ( 5, SUMMARIZECOLUMNS ( fact_trip[lane_id], dim_customer[customer_name], "Trip Cost", [Trip Cost], "Trips", [Trips] ), [Trip Cost], DESC )
ORDER BY [Trip Cost] DESC`,
    },
    {
        question: "Are late deliveries caused by dock waits? Break it down by plant, weekday and channel",
        dax: `EVALUATE
FILTER (
    SUMMARIZECOLUMNS ( dim_facility[facility_id], dim_date[weekday], dim_customer[channel],
        "Late trips caused by dock wait", [Dock-Delayed Late Trips], "Avg dock wait (h)", [Avg Dock Wait (h)] ),
    [Late trips caused by dock wait] > 0
)
ORDER BY [Late trips caused by dock wait] DESC`,
    },
    {
        question: "Fill rate by channel",
        dax: `EVALUATE
SUMMARIZECOLUMNS ( dim_customer[channel], "Fill Rate %", [Fill Rate %], "Cases ordered", [Cases Ordered], "Cases shipped", [Cases Shipped] )
ORDER BY [Fill Rate %] ASC`,
    },
];

# NB_03_gold_fasttrack: bronze -> app/agent-ready gold, in one pass          [D2]
# -----------------------------------------------------------------------------------
# FAST TRACK ONLY. Skips silver on purpose, to get the Fabric App + agent running this weekend.
# Lab L3 later rebuilds gold properly through silver (typing, dedupe, SCD Type 2).
#
# How to use:
# - Fabric notebook "NB_03_gold_fasttrack", default lakehouse = LH_FreshyFresh, run after NB_01_load_bronze.
# - Paste each "# %%" block into its own cell. Mark the first cell as the parameter cell.
#
# What it adds on top of bronze, so the semantic model, the app and the agent stay simple:
#   - gold.fact_shipment: in_full, otif, tor_minutes, max_temp_c, is_excursion, requested_delivery_date, ship_date
#   - gold.fact_order_line: + ship_from_facility_id (direct star join to dim_facility, no snowflake path)
#   - gold.fact_shipment_line, bridge_lot_ingredient, fact_quality_test (+ lot's plant), fact_supplier_notice
#     (+ receiving plant): + facility_id, so RLS on dim_facility filters them too
#   - gold.trace_genealogy: ingredient lot -> finished lot -> shipment -> customer (denormalised traceability mart)
#   - gold.dim_facility: optional real test-user UPNs for RLS via upn_overrides
#   - gold.fact_trip: one trip per shipment with dock wait, drive time and trip cost (fleet extension)
# Databricks analogue: a gold "serving" job building denormalised marts for AI/BI and Genie.

# %% parameters
bronze_schema = "bronze"
gold_schema = "gold"
table_format = "delta"                  # keep "delta" in Fabric; tools/run_notebooks_local.py overrides to parquet
upn_overrides = {}                      # e.g. {"P03": "qa.p03@yourtenant.onmicrosoft.com"} for real RLS test users
excursion_threshold_c = 5.0
reading_minutes = 15
min_tor_minutes = 30
dock_wait_story_h = 2.0                 # Q9: a late shipment is "dock-caused" above this

# %% helpers
from pyspark.sql import functions as F

spark.conf.set("spark.sql.session.timeZone", "UTC")   # dates/weekdays in the business rules are UTC
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {gold_schema}")
META_COLS = ["_ingested_at", "_source_file"]
counts = {}


def bronze(t):
    df = spark.table(f"{bronze_schema}.{t}")
    return df.drop(*[c for c in META_COLS if c in df.columns])


def write(df, t):
    (df.write.format(table_format).mode("overwrite").option("overwriteSchema", "true")
       .saveAsTable(f"{gold_schema}.{t}"))
    counts[t] = spark.table(f"{gold_schema}.{t}").count()


# %% dimensions
facility = bronze("dim_facility")
if upn_overrides:
    upn_map = F.create_map(*[F.lit(x) for kv in upn_overrides.items() for x in kv])
    facility = facility.withColumn(
        "qa_manager_upn", F.coalesce(F.element_at(upn_map, F.col("facility_id")), F.col("qa_manager_upn")))
write(facility, "dim_facility")
for t in ["dim_product", "dim_customer", "dim_truck", "dim_supplier", "dim_ingredient", "dim_date"]:
    write(bronze(t), t)

# %% orders and shipments (OTIF + cold-chain flags precomputed)
orders = bronze("fact_order")
write(bronze("fact_order_line").join(orders.select("order_id", "ship_from_facility_id"), "order_id", "left"),
      "fact_order_line")
write(orders, "fact_order")

in_full = (bronze("fact_order_line")
           .groupBy("order_id")
           .agg(F.min(F.when(F.col("cases_delivered") == F.col("cases_ordered"), 1).otherwise(0)).alias("full_flag"))
           .select("order_id", (F.col("full_flag") == 1).alias("in_full")))

tor = (bronze("reefer_telemetry")
       .groupBy("shipment_id")
       .agg(F.sum(F.when(F.col("temp_c") > excursion_threshold_c, 1).otherwise(0)).alias("readings_above"),
            F.max("temp_c").alias("max_temp_c"))
       .select("shipment_id", (F.col("readings_above") * reading_minutes).alias("tor_minutes"), "max_temp_c"))

shipment = (bronze("fact_shipment")
            .join(in_full, "order_id", "left")
            .join(tor, "shipment_id", "left")
            .withColumn("in_full", F.coalesce(F.col("in_full"), F.lit(False)))
            .withColumn("tor_minutes", F.coalesce(F.col("tor_minutes"), F.lit(0)))
            .withColumn("otif", F.col("on_time") & F.col("in_full"))
            .withColumn("is_excursion", F.col("tor_minutes") >= min_tor_minutes)
            .withColumn("requested_delivery_date", F.to_date("requested_delivery_ts"))
            .withColumn("ship_date", F.to_date("ship_ts")))
write(shipment, "fact_shipment")

# %% production, waste, inventory, quality, traceability inputs
for t in ["fact_lot", "fact_waste", "fact_inventory_daily", "fact_ingredient_receipt"]:
    write(bronze(t), t)

# + facility_id so every fact joins dim_facility directly and RLS filters it (no fact-to-fact relationships):
# lot-level tables take the producing plant of the lot; a supplier notice takes the plant that received the lot.
lot_facility = bronze("fact_lot").select("lot_id", "facility_id")
for t in ["fact_shipment_line", "bridge_lot_ingredient", "fact_quality_test"]:
    write(bronze(t).join(lot_facility, "lot_id", "left"), t)
write(bronze("fact_supplier_notice")
      .join(bronze("fact_ingredient_receipt").select("ingredient_lot_id", "facility_id"), "ingredient_lot_id", "left"),
      "fact_supplier_notice")

# %% traceability mart: one row per (ingredient lot, finished lot, shipment line)
lots = bronze("fact_lot").select("lot_id", "sku_id", "facility_id", "production_date", "best_by_date")
trace = (bronze("bridge_lot_ingredient")
         .join(bronze("fact_ingredient_receipt").select("ingredient_lot_id", "supplier_id", "receipt_date"),
               "ingredient_lot_id")
         .join(lots, "lot_id")
         .join(bronze("fact_shipment_line").select("lot_id", "shipment_id", "order_line", "cases_shipped",
                                                   "cases_delivered"), "lot_id", "left")
         .join(bronze("fact_shipment").select("shipment_id", "customer_id", "ship_ts"), "shipment_id", "left")
         .withColumn("ship_date", F.to_date("ship_ts")).drop("ship_ts"))
write(trace, "trace_genealogy")

# %% fleet: one trip per shipment (dock wait, drive time, cost)
# dock_wait_h = departed_ts - ship_ts (planned departure); drive_h = delivered_ts - departed_ts.
# trip_cost_usd = route_km * cost_per_km_usd + (dock_wait_h + drive_h) * driver_cost_per_hour_usd (demo rates).
def hours(a, b):
    return (F.col(b).cast("double") - F.col(a).cast("double")) / 3600   # timestamp -> epoch seconds, keeps micros


cases = bronze("fact_shipment_line").groupBy("shipment_id").agg(F.sum("cases_delivered").alias("cases_delivered"))
trip = (shipment.select("shipment_id", "truck_id", "ship_from_facility_id", "customer_id", "ship_date",
                        "requested_delivery_date", "ship_ts", "departed_ts", "delivered_ts", "on_time", "otif",
                        "is_excursion")
        .join(bronze("dim_truck").select("truck_id", "cost_per_km_usd", "driver_cost_per_hour_usd"), "truck_id")
        .join(bronze("dim_customer").select("customer_id", "route_km"), "customer_id")
        .join(cases, "shipment_id", "left")
        .withColumn("cases_delivered", F.coalesce(F.col("cases_delivered"), F.lit(0)))
        .withColumn("lane_id", F.concat_ws("->", "ship_from_facility_id", "customer_id"))
        .withColumn("dock_wait_h", hours("ship_ts", "departed_ts"))
        .withColumn("drive_h", hours("departed_ts", "delivered_ts"))
        .withColumn("trip_cost_usd", F.round(F.col("route_km") * F.col("cost_per_km_usd")
                                             + (F.col("dock_wait_h") + F.col("drive_h"))
                                             * F.col("driver_cost_per_hour_usd"), 2))
        .withColumn("is_dock_delayed", F.col("dock_wait_h") > dock_wait_story_h))
write(trip, "fact_trip")

# %% acceptance checks against agent/golden_answers.json (seed 42)
g = spark.table(f"{gold_schema}.fact_shipment")
t = spark.table(f"{gold_schema}.trace_genealogy").where(F.col("ingredient_lot_id") == "ILOT-P02-ING02-20260908")
ol = spark.table(f"{gold_schema}.fact_order_line")
ft = spark.table(f"{gold_schema}.fact_trip")
p07_mon_fs_late = (ft.join(bronze("dim_customer").select("customer_id", "channel"), "customer_id")
                   .where("ship_from_facility_id = 'P07' AND channel = 'Foodservice' AND NOT on_time")
                   .where(F.dayofweek("requested_delivery_date") == 2))   # Spark: Sunday = 1, Monday = 2
checks = {
    "Q1 recall finished lots (36)": (t.select("lot_id").distinct().count(), 36),
    "Q1 recall cases shipped (145)": (t.agg(F.sum("cases_shipped")).first()[0], 145),
    "Q1 recall customers (10)": (t.where(F.col("customer_id").isNotNull()).select("customer_id").distinct().count(), 10),
    "Q2 excursion shipments (4)": (g.where("is_excursion").count(), 4),
    "Q4 overall on-time % (94.81)": (round(g.agg(F.avg(F.col("on_time").cast("int"))).first()[0] * 100, 2), 94.81),
    "Q4 P02 OTIF % (90.09)": (round(g.where("ship_from_facility_id = 'P02'")
                                     .agg(F.avg(F.col("otif").cast("int"))).first()[0] * 100, 2), 90.09),
    "Q6 fill rate % (99.54)": (round(ol.agg(F.sum("cases_shipped") / F.sum("cases_ordered")).first()[0] * 100, 2), 99.54),
    "Q9 P07 Mon Foodservice late, dock-caused (14)": (p07_mon_fs_late.where("is_dock_delayed").count(), 14),
    "Q9 late elsewhere, dock-caused (0)": (ft.where("NOT on_time AND is_dock_delayed").count()
                                           - p07_mon_fs_late.where("is_dock_delayed").count(), 0),
    "Q10 total trip cost USD (3957156.99)": (round(ft.agg(F.sum("trip_cost_usd")).first()[0], 2), 3957156.99),
    "RLS: rows with no facility_id (0)": (sum(spark.table(f"{gold_schema}.{x}").where("facility_id IS NULL").count()
                                              for x in ["fact_shipment_line", "bridge_lot_ingredient",
                                                        "fact_quality_test", "fact_supplier_notice"]), 0),
}
failed = {k: v for k, v in checks.items() if v[0] != v[1]}
for k, (got, exp) in checks.items():
    print(("PASS " if got == exp else "FAIL ") + f"{k}: got {got}")
print(counts)
assert not failed, f"Gold acceptance checks failed: {failed}"
print("PASS: gold matches golden answers")

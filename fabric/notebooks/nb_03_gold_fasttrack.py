# NB_03_gold_fasttrack: bronze -> app/agent-ready gold, in one pass          [D2]
# -----------------------------------------------------------------------------------
# FAST TRACK ONLY. Skips silver on purpose, to get the Fabric App + agent running this weekend.
# Lab L3 later rebuilds gold properly through silver (typing, dedupe, SCD Type 2).
#
# How to use:
# - Fabric notebook "NB_03_gold_fasttrack", default lakehouse = LH_Ambermoor, run after NB_01_load_bronze.
# - Paste each "# %%" block into its own cell. Mark the first cell as the parameter cell.
#
# What it adds on top of bronze, so the semantic model, the app and the agent stay simple:
#   - gold.fact_shipment: in_full, otif, tor_minutes, max_temp_c, is_excursion, requested_delivery_date, ship_date
#   - gold.fact_order_line: + ship_from_facility_id (direct star join to dim_facility, no snowflake path)
#   - gold.trace_genealogy: ingredient lot -> finished lot -> shipment -> customer (denormalised traceability mart)
#   - gold.dim_facility: optional real test-user UPNs for RLS via upn_overrides
# Databricks analogue: a gold "serving" job building denormalised marts for AI/BI and Genie.

# %% parameters
bronze_schema = "bronze"
gold_schema = "gold"
table_format = "delta"                  # keep "delta" in Fabric; tools/run_notebooks_local.py overrides to parquet
upn_overrides = {}                      # e.g. {"P03": "qa.p03@yourtenant.onmicrosoft.com"} for real RLS test users
excursion_threshold_c = 5.0
reading_minutes = 15
min_tor_minutes = 30

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
for t in ["dim_product", "dim_customer", "dim_supplier", "dim_ingredient", "dim_date"]:
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

# %% production, waste, inventory, quality, traceability inputs (pass-through)
for t in ["fact_lot", "fact_waste", "fact_inventory_daily", "fact_shipment_line", "fact_ingredient_receipt",
          "bridge_lot_ingredient", "fact_quality_test", "fact_supplier_notice"]:
    write(bronze(t), t)

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

# %% acceptance checks against agent/golden_answers.json (seed 42)
g = spark.table(f"{gold_schema}.fact_shipment")
t = spark.table(f"{gold_schema}.trace_genealogy").where(F.col("ingredient_lot_id") == "ILOT-P02-ING02-20260908")
ol = spark.table(f"{gold_schema}.fact_order_line")
checks = {
    "Q1 recall finished lots (36)": (t.select("lot_id").distinct().count(), 36),
    "Q1 recall cases shipped (145)": (t.agg(F.sum("cases_shipped")).first()[0], 145),
    "Q1 recall customers (10)": (t.where(F.col("customer_id").isNotNull()).select("customer_id").distinct().count(), 10),
    "Q2 excursion shipments (4)": (g.where("is_excursion").count(), 4),
    "Q4 overall on-time % (94.81)": (round(g.agg(F.avg(F.col("on_time").cast("int"))).first()[0] * 100, 2), 94.81),
    "Q4 P02 OTIF % (90.09)": (round(g.where("ship_from_facility_id = 'P02'")
                                     .agg(F.avg(F.col("otif").cast("int"))).first()[0] * 100, 2), 90.09),
    "Q6 fill rate % (99.54)": (round(ol.agg(F.sum("cases_shipped") / F.sum("cases_ordered")).first()[0] * 100, 2), 99.54),
}
failed = {k: v for k, v in checks.items() if v[0] != v[1]}
for k, (got, exp) in checks.items():
    print(("PASS " if got == exp else "FAIL ") + f"{k}: got {got}")
print(counts)
assert not failed, f"Gold acceptance checks failed: {failed}"
print("PASS: gold matches golden answers")

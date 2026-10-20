# NB_01_load_bronze: land Ambermoor parquet files as bronze Delta tables            [D2]
# -----------------------------------------------------------------------------------
# How to use: create a Fabric notebook "NB_01_load_bronze", attach LH_Ambermoor as the DEFAULT lakehouse,
# and paste each "# %%" block into its own cell. Mark the first cell as a parameter cell (lab L2 passes
# parameters from PL_Ambermoor_Daily).
#
# Prereq (lab L1): the 19 files from data/generated/*.parquet uploaded to LH_Ambermoor -> Files/landing/ambermoor/
# Databricks analogue: Auto Loader / COPY INTO from a Volume into a bronze Delta table. Here it's a plain batch
# read from the lakehouse Files area.
# Verify on Learn: schema-enabled lakehouse status, and whether CREATE SCHEMA via Spark SQL is supported in your
# lakehouse (otherwise create the schema in the lakehouse UI).

# %% parameters
landing_path = "Files/landing/ambermoor"   # relative path resolves against the default lakehouse
bronze_schema = "bronze"
table_format = "delta"                  # keep "delta" in Fabric; tools/run_notebooks_local.py overrides to parquet
tables = [
    "dim_facility", "dim_product", "dim_customer", "dim_truck", "dim_supplier", "dim_ingredient", "dim_date",
    "fact_ingredient_receipt", "fact_lot", "bridge_lot_ingredient", "fact_quality_test",
    "fact_order", "fact_order_line", "fact_shipment", "fact_shipment_line", "fact_waste",
    "fact_inventory_daily", "fact_supplier_notice", "reefer_telemetry",
]

# %% load
from pyspark.sql import functions as F

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {bronze_schema}")

results = []
for t in tables:
    src = f"{landing_path}/{t}.parquet"
    df = (
        spark.read.parquet(src)
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source_file", F.lit(src))
    )
    (
        df.write.format(table_format)
        .mode("overwrite")                     # bronze = full reload of the delivered snapshot
        .option("overwriteSchema", "true")
        .saveAsTable(f"{bronze_schema}.{t}")
    )
    results.append((t, spark.table(f"{bronze_schema}.{t}").count()))

# %% acceptance check: compare with data/generated/manifest.json (seed 42)
expected = {
    "dim_facility": 8, "dim_product": 49, "dim_customer": 120, "dim_truck": 48, "dim_supplier": 8, "dim_ingredient": 30,
    "dim_date": 174, "fact_ingredient_receipt": 2040, "fact_lot": 5416, "bridge_lot_ingredient": 21927,
    "fact_quality_test": 16248, "fact_order": 3317, "fact_order_line": 16519, "fact_shipment": 3317,
    "fact_shipment_line": 20837, "fact_waste": 310, "fact_inventory_daily": 12960, "fact_supplier_notice": 1,
    "reefer_telemetry": 183921,
}
bad = [(t, n, expected.get(t)) for t, n in results if n != expected.get(t)]
display(spark.createDataFrame(results, "table string, rows long"))
assert not bad, f"Row-count mismatch (table, got, expected): {bad}"
print("PASS: all bronze tables match the manifest")

#!/usr/bin/env python3
"""
Run the Fabric notebook sources (fabric/notebooks/*.py) locally with PySpark before using Fabric capacity.

It executes each "# %%" cell in order, overriding the parameter cell so that:
  - landing_path points at your generated parquet folder
  - table_format = "parquet" (local Spark has no Delta jars by default)

Requires Java 17+ and `pip install pyspark` (Fabric runs Spark 3.5; DataFrame APIs used here are the same in 3.5/4.0).
Usage:
  python tools/run_notebooks_local.py --data data/generated
"""
import argparse
import re
import shutil
import sys
from pathlib import Path


def cells(path):
    src = Path(path).read_text()
    parts = re.split(r"^# %%.*$", src, flags=re.M)
    return [p for p in parts[1:] if p.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/generated")
    ap.add_argument("--warehouse", default=".local-spark-warehouse")
    a = ap.parse_args()

    from pyspark.sql import SparkSession

    wh = Path(a.warehouse).resolve()
    shutil.rmtree(wh, ignore_errors=True)
    spark = (SparkSession.builder.master("local[2]").appName("freshyfresh-local")
             .config("spark.sql.warehouse.dir", str(wh))
             .config("spark.sql.session.timeZone", "UTC")
             .config("spark.ui.enabled", "false")
             .getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")
    overrides = {"landing_path": str(Path(a.data).resolve()), "table_format": "parquet"}

    for nb in ["fabric/notebooks/nb_01_load_bronze.py", "fabric/notebooks/nb_03_gold_fasttrack.py"]:
        print(f"\n=== {nb}")
        ns = {"spark": spark, "display": lambda df: df.show(50, truncate=False)}
        for i, cell in enumerate(cells(nb)):
            exec(compile(cell, f"{nb}#cell{i}", "exec"), ns)
            if i == 0:  # parameter cell
                ns.update({k: v for k, v in overrides.items() if k in ns})
    spark.stop()
    shutil.rmtree(wh, ignore_errors=True)
    print("\nLocal notebook run complete.")


if __name__ == "__main__":
    sys.exit(main())

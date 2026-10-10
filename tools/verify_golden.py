#!/usr/bin/env python3
"""
Independently re-compute key golden answers with SQL (DuckDB) over the generated files
and compare them with golden_answers.json. Exit code 1 on any mismatch.

Why: the generator computes golden answers in pandas; this checks them a second way,
the same way an agent would (SQL over tables), before you trust them as an eval oracle.

Usage:
  pip install duckdb
  python tools/verify_golden.py --data data/generated
"""
import argparse
import json
import sys
from pathlib import Path

import duckdb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/generated")
    a = ap.parse_args()
    d = Path(a.data)
    g = json.loads((d / "golden_answers.json").read_text())
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")  # golden answers use UTC weekdays/months
    for f in d.glob("*.parquet"):
        con.execute(f"CREATE VIEW {f.stem} AS SELECT * FROM read_parquet('{f.as_posix()}')")
    con.execute(f"CREATE VIEW ReeferTelemetry AS SELECT * FROM read_csv_auto('{(d / 'reefer_telemetry.csv').as_posix()}')")

    checks = []

    # Q1 mock recall
    ilot = g["Q1_mock_recall"]["ingredient_lot_id"]
    lots, shipped, customers, shipments = con.execute(f"""
        SELECT COUNT(DISTINCT b.lot_id),
               COALESCE(SUM(sl.cases_shipped), 0),
               COUNT(DISTINCT s.customer_id),
               COUNT(DISTINCT sl.shipment_id)
        FROM (SELECT DISTINCT lot_id FROM bridge_lot_ingredient WHERE ingredient_lot_id = '{ilot}') b
        LEFT JOIN fact_shipment_line sl ON sl.lot_id = b.lot_id
        LEFT JOIN fact_shipment s ON s.shipment_id = sl.shipment_id
    """).fetchone()
    q1 = g["Q1_mock_recall"]
    checks += [("Q1 finished lots", lots, q1["finished_lot_count"]), ("Q1 cases shipped", shipped, q1["cases_shipped"]),
               ("Q1 customers", customers, q1["customer_count"]), ("Q1 shipments", shipments, q1["shipment_count"])]

    # Q2 cold chain (same rule the KQL few-shot uses)
    rows = con.execute("""
        SELECT shipment_id, truck_id, SUM(CASE WHEN temp_c > 5.0 THEN 1 ELSE 0 END) * 15 AS tor_minutes
        FROM ReeferTelemetry GROUP BY shipment_id, truck_id HAVING tor_minutes >= 30 ORDER BY shipment_id
    """).fetchall()
    checks.append(("Q2 excursion shipments", [r[0] for r in rows],
                   [s["shipment_id"] for s in g["Q2_cold_chain_excursions"]["shipments"]]))
    naive = con.execute("SELECT COUNT(DISTINCT shipment_id) FROM ReeferTelemetry WHERE temp_c > 5.0").fetchone()[0]
    checks.append(("Q2 naive any-reading count", naive, g["Q2_cold_chain_excursions"]["shipments_with_any_reading_above_5c"]))

    # Q4 worst on-time segment
    worst = con.execute("""
        SELECT s.ship_from_facility_id, c.channel, dayname(s.requested_delivery_ts) AS wd,
               COUNT(*) AS n, ROUND(AVG(CASE WHEN s.on_time THEN 100.0 ELSE 0 END), 2) AS pct
        FROM fact_shipment s JOIN dim_customer c USING (customer_id)
        GROUP BY ALL HAVING COUNT(*) >= 20 ORDER BY pct ASC, n DESC LIMIT 1
    """).fetchone()
    w = g["Q4_otif"]["worst_on_time_segments"][0]
    checks.append(("Q4 worst segment", list(worst[:3]) + [float(worst[4])],
                   [w["facility_id"], w["channel"], w["requested_weekday"], w["on_time_pct"]]))

    # Q5 top 5 SKUs by volume, September 2026
    top = [r[0] for r in con.execute("""
        SELECT sku_id FROM fact_order_line WHERE month(requested_delivery_date) = 9
        GROUP BY sku_id ORDER BY SUM(cases_delivered) DESC LIMIT 5""").fetchall()]
    checks.append(("Q5 top5 SKUs", top, [x["sku_id"] for x in g["Q5_top5_skus_by_volume_sep_2026"]["top5"]]))

    # Q6 fill rate
    fr = con.execute("SELECT ROUND(SUM(cases_shipped) * 100.0 / SUM(cases_ordered), 2) FROM fact_order_line").fetchone()[0]
    checks.append(("Q6 fill rate %", float(fr), g["Q6_fill_rate"]["fill_rate_pct"]))

    ok = True
    for name, got, exp in checks:
        status = "PASS" if got == exp else "FAIL"
        ok &= status == "PASS"
        print(f"{status}  {name}: sql={got} golden={exp}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

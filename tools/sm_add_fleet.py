"""Add the fleet extension (SM_Ambermoor_Ops.md section 6) to a downloaded SM_Ambermoor_Ops TMDL definition.

    python tools/sm_definition.py get --workspace <ws> --model <id> --out build/sm_fleet          # read-only
    python tools/sm_add_fleet.py --src build/sm_fleet --schema build/fleet_schema.json             # local edit only
    python tools/sm_definition.py update --workspace <ws> --model <id> --src build/sm_fleet       # Fabric WRITE (ask first)

Add-only, unlike sm_patch_tmdl.py: it never rewrites roles or existing relationships. (Role members added in the
portal are not in getDefinition's TMDL and survive updateDefinition; checked 21 Oct with impersonatedUserName.)
Adds Direct Lake tables gold.dim_truck and gold.fact_trip, four relationships into fact_trip and the
fleet measures on fact_trip. Idempotent: re-running replaces what it added.

--schema is {"dim_truck": [[column, delta_type], ...], "fact_trip": [...]}, read from each table's Delta log so the
column types match the lakehouse exactly.
"""
import argparse
import json
import re
import uuid
from pathlib import Path

TABLES = ["dim_truck", "fact_trip"]
RELATIONSHIPS = [
    (("fact_trip", "ship_from_facility_id"), ("dim_facility", "facility_id")),   # RLS on dim_facility flows to trips
    (("fact_trip", "customer_id"), ("dim_customer", "customer_id")),
    (("fact_trip", "truck_id"), ("dim_truck", "truck_id")),
    (("fact_trip", "requested_delivery_date"), ("dim_date", "date")),
]
PCT, WHOLE, USD, USD2, HOURS = "0.0%", "#,0", "\\$#,0", "\\$#,0.00", "0.00"
MEASURES = [
    ("Trips", "COUNTROWS ( fact_trip )", WHOLE),
    ("Trip Cost", "SUM ( fact_trip[trip_cost_usd] )", USD),
    ("Freight Cost per Case", "DIVIDE ( [Trip Cost], SUM ( fact_trip[cases_delivered] ) )", USD2),
    ("Avg Dock Wait (h)", "AVERAGE ( fact_trip[dock_wait_h] )", HOURS),
    ("Avg Drive (h)", "AVERAGE ( fact_trip[drive_h] )", HOURS),
    ("Dock-Delayed Late Trips",
     "CALCULATE ( [Trips], fact_trip[is_dock_delayed] = TRUE (), fact_trip[on_time] = FALSE () )", WHOLE),
]
DTYPE = {"string": "string", "double": "double", "float": "double", "long": "int64", "integer": "int64",
         "short": "int64", "boolean": "boolean", "timestamp": "dateTime", "timestamp_ntz": "dateTime",
         "date": "dateTime"}
MARK = "/// added by tools/sm_add_fleet.py"


def q(name: str) -> str:
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else "'" + name.replace("'", "''") + "'"


def lineage(*parts: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "ambermoor-fleet/" + "/".join(parts)))


def column_tmdl(table: str, col: str, delta_type: str) -> str:
    dt = DTYPE[delta_type]
    numeric = dt in ("double", "int64") and not col.endswith(("_id", "_year"))
    fmt = {"dateTime": "\t\tformatString: " + ("Short Date" if delta_type == "date" else "General Date") + "\n",
           "boolean": '\t\tformatString: """TRUE"";""TRUE"";""FALSE"""\n'}.get(dt, "")
    return (f"\tcolumn {q(col)}\n\t\tdataType: {dt}\n{fmt}\t\tlineageTag: {lineage(table, col)}\n"
            f"\t\tsourceLineageTag: {col}\n\t\tsummarizeBy: {'sum' if numeric else 'none'}\n"
            f"\t\tsourceColumn: {col}\n\n\t\tannotation SummarizationSetBy = Automatic\n\n")


def table_tmdl(table: str, cols: list, expression: str, measures: str = "") -> str:
    return (f"table {table}\n\tlineageTag: {lineage(table)}\n\tsourceLineageTag: [gold].[{table}]\n\n"
            + measures + "".join(column_tmdl(table, c, t) for c, t in cols)
            + f"\tpartition {table} = entity\n\t\tmode: directLake\n\t\tsource\n\t\t\tentityName: {table}\n"
              f"\t\t\tschemaName: gold\n\t\t\texpressionSource: {expression}\n\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="build/sm_fleet")
    ap.add_argument("--schema", required=True)
    a = ap.parse_args()
    defn = Path(a.src) / "definition"
    schema = json.loads(Path(a.schema).read_text(encoding="utf-8"))

    # reuse the Direct Lake expression the portal created (e.g. 'DirectLake - LH_Ambermoor')
    expr = re.search(r"^expression\s+('[^']+'|\S+)\s*=", (defn / "expressions.tmdl").read_text(encoding="utf-8"), re.M)
    if not expr:
        raise SystemExit("no Direct Lake expression found in expressions.tmdl")

    # 1. tables (fact_trip carries the measures)
    for t in TABLES:
        cols = [tuple(c) for c in schema[t]]
        unknown = sorted({ty for _, ty in cols if ty not in DTYPE})
        if unknown:
            raise SystemExit(f"{t}: unmapped Delta types {unknown}")
        measures = "".join(f"\t{MARK}\n\tmeasure {q(n)} = {e}\n\t\tformatString: {f}\n\t\tdisplayFolder: Fleet\n\n"
                           for n, e, f in MEASURES) if t == "fact_trip" else ""
        (defn / "tables" / f"{t}.tmdl").write_text(table_tmdl(t, cols, expr.group(1), measures),
                                                   encoding="utf-8", newline="\n")

    # 2. relationships: append ours, keep everything else. No MARK here: in TMDL "///" sets the next object's
    #    description, and relationships have none (updateDefinition rejects it). Ours are found by their uuid5 names.
    rel_file = defn / "relationships.tmdl"
    text = rel_file.read_text(encoding="utf-8") if rel_file.exists() else ""
    ours = {str(uuid.uuid5(uuid.NAMESPACE_URL, f"{t}.{c}->{dt}.{dc}")): (t, c, dt, dc)
            for (t, c), (dt, dc) in RELATIONSHIPS}
    text = re.sub(rf"(?:{re.escape(MARK)}\n)?relationship ({'|'.join(ours)})\n(?:\t.*\n)+\n?", "", text)
    text = text.rstrip("\n") + "\n\n"
    have = {c for c, _ in schema["fact_trip"]}
    for rid, (t, c, dt, dc) in ours.items():
        if c not in have:
            raise SystemExit(f"fact_trip has no column {c}")
        text += f"relationship {rid}\n\tfromColumn: {q(t)}.{q(c)}\n\ttoColumn: {q(dt)}.{q(dc)}\n\n"
    rel_file.write_text(text, encoding="utf-8", newline="\n")

    # 3. model.tmdl: reference the new tables (PBI_QueryOrder lists expressions, not tables: leave it)
    model = defn / "model.tmdl"
    mt = model.read_text(encoding="utf-8")
    for t in TABLES:
        refs = list(re.finditer(r"^ref table .*$", mt, re.M))
        if refs and not re.search(rf"^ref table {t}$", mt, re.M):
            end = refs[-1].end()
            mt = mt[:end] + f"\nref table {t}" + mt[end:]
    model.write_text(mt, encoding="utf-8", newline="\n")

    print(f"patched {defn}: tables {TABLES}, {len(RELATIONSHIPS)} relationships, {len(MEASURES)} measures; "
          f"roles untouched")


if __name__ == "__main__":
    main()

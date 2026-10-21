"""Add the app's writeback (holds, corrective actions, timeline) to a downloaded SM_FreshyFresh_Ops TMDL (§8).

    python tools/sm_definition.py get --workspace <ws> --model <id> --out build/sm_holds        # read-only
    python tools/sm_add_holds.py --src build/sm_holds --schema build/holds_schema.json        # local edit only
    python tools/sm_definition.py update --workspace <ws> --model <id> --src build/sm_holds    # Fabric WRITE (ask first)

Source: the app's Fabric SQL database is mirrored to OneLake automatically; a schema shortcut `app` in LH_FreshyFresh
points at its Tables/dbo, so Direct Lake reads app.QualityHolds / app.CorrectiveActions / app.HoldUpdates.
Add-only like sm_add_fleet.py: three tables, three relationships (RLS: dim_facility -> quality_hold -> actions and
timeline), hold measures. Archived holds (Tutorial reset) are excluded by every measure. Idempotent.

--schema is {"QualityHolds": [[column, delta_type], ...], ...}, read from each mirrored table's Delta log.
"""
import argparse
import json
import re
import uuid
from pathlib import Path

TABLES = {"quality_hold": "QualityHolds", "corrective_action": "CorrectiveActions", "hold_update": "HoldUpdates"}
RELATIONSHIPS = [
    (("quality_hold", "facility_id"), ("dim_facility", "facility_id")),   # RLS flows to holds ...
    (("corrective_action", "hold_id"), ("quality_hold", "id")),          # ... and on to their actions
    (("hold_update", "hold_id"), ("quality_hold", "id")),                # ... and timeline
]
LIVE = 'quality_hold[status] <> "Archived"'
MEASURES = [
    ("Holds", f"CALCULATE ( COUNTROWS ( quality_hold ), {LIVE} )", "#,0"),
    ("Open Holds", 'CALCULATE ( COUNTROWS ( quality_hold ), quality_hold[status] = "Open" )', "#,0"),
    ("Cases On Hold", 'CALCULATE ( SUM ( quality_hold[cases_on_hold] ), quality_hold[status] = "Open" )', "#,0"),
    ("Destroyed Holds", 'CALCULATE ( COUNTROWS ( quality_hold ), quality_hold[status] = "Destroyed" )', "#,0"),
    ("Open Actions", 'CALCULATE ( COUNTROWS ( corrective_action ), corrective_action[status] = "Open", '
                     f'{LIVE} )', "#,0"),
    ("Overdue Actions", 'CALCULATE ( COUNTROWS ( corrective_action ), corrective_action[status] = "Open", '
                        f'corrective_action[due_date] < TODAY (), {LIVE} )', "#,0"),
]
DTYPE = {"string": "string", "integer": "int64", "long": "int64", "double": "double", "boolean": "boolean",
         "timestamp": "dateTime", "timestamp_ntz": "dateTime", "date": "dateTime"}
MARK = "/// added by tools/sm_add_holds.py"


def lineage(*parts: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "freshyfresh-holds/" + "/".join(parts)))


def column_tmdl(table: str, col: str, delta_type: str) -> str:
    dt = DTYPE[delta_type]
    numeric = dt in ("double", "int64")
    fmt = "\t\tformatString: General Date\n" if dt == "dateTime" else ""
    return (f"\tcolumn {col}\n\t\tdataType: {dt}\n{fmt}\t\tlineageTag: {lineage(table, col)}\n"
            f"\t\tsourceLineageTag: {col}\n\t\tsummarizeBy: {'sum' if numeric else 'none'}\n"
            f"\t\tsourceColumn: {col}\n\n\t\tannotation SummarizationSetBy = Automatic\n\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="build/sm_holds")
    ap.add_argument("--schema", default="build/holds_schema.json")
    a = ap.parse_args()
    defn = Path(a.src) / "definition"
    schema = json.loads(Path(a.schema).read_text(encoding="utf-8"))
    expr = re.search(r"^expression\s+('[^']+'|\S+)\s*=", (defn / "expressions.tmdl").read_text(encoding="utf-8"), re.M)
    if not expr:
        raise SystemExit("no Direct Lake expression found in expressions.tmdl")

    # 1. tables (quality_hold carries the measures)
    for name, source in TABLES.items():
        cols = schema[source]
        unknown = sorted({t for _, t in cols if t not in DTYPE})
        if unknown:
            raise SystemExit(f"{source}: unmapped Delta types {unknown}")
        measures = "".join(f"\t{MARK}\n\tmeasure '{n}' = {e}\n\t\tformatString: {f}\n\t\tdisplayFolder: Holds\n\n"
                           for n, e, f in MEASURES) if name == "quality_hold" else ""
        (defn / "tables" / f"{name}.tmdl").write_text(
            f"table {name}\n\tlineageTag: {lineage(name)}\n\tsourceLineageTag: [app].[{source}]\n\n"
            + measures + "".join(column_tmdl(name, c, t) for c, t in cols)
            + f"\tpartition {name} = entity\n\t\tmode: directLake\n\t\tsource\n\t\t\tentityName: {source}\n"
              f"\t\t\tschemaName: app\n\t\t\texpressionSource: {expr.group(1)}\n\n",
            encoding="utf-8", newline="\n")

    # 2. relationships, found by their uuid5 names (no "///" before a relationship: TMDL reads it as a description)
    rel_file = defn / "relationships.tmdl"
    text = rel_file.read_text(encoding="utf-8")
    ours = {str(uuid.uuid5(uuid.NAMESPACE_URL, f"{t}.{c}->{dt}.{dc}")): (t, c, dt, dc)
            for (t, c), (dt, dc) in RELATIONSHIPS}
    text = re.sub(rf"relationship ({'|'.join(ours)})\n(?:\t.*\n)+\n?", "", text).rstrip("\n") + "\n\n"
    for rid, (t, c, dt, dc) in ours.items():
        if c not in {x for x, _ in schema[TABLES[t]]}:
            raise SystemExit(f"{t} has no column {c}")
        text += f"relationship {rid}\n\tfromColumn: {t}.{c}\n\ttoColumn: {dt}.{dc}\n\n"
    rel_file.write_text(text, encoding="utf-8", newline="\n")

    # 3. model.tmdl: reference the new tables
    model = defn / "model.tmdl"
    mt = model.read_text(encoding="utf-8")
    for t in TABLES:
        refs = list(re.finditer(r"^ref table .*$", mt, re.M))
        if refs and not re.search(rf"^ref table {t}$", mt, re.M):
            mt = mt[:refs[-1].end()] + f"\nref table {t}" + mt[refs[-1].end():]
    model.write_text(mt, encoding="utf-8", newline="\n")
    print(f"patched {defn}: tables {list(TABLES)}, {len(RELATIONSHIPS)} relationships, {len(MEASURES)} measures; "
          f"roles untouched")


if __name__ == "__main__":
    main()

"""Patch a downloaded SM_FreshyFresh_Ops TMDL definition with the spec in fabric/semantic-model/SM_FreshyFresh_Ops.md.

    python tools/sm_definition.py get --workspace <ws> --model <id> --out build/sm     # read-only
    python tools/sm_patch_tmdl.py --src build/sm                                      # local edit only
    python tools/sm_definition.py update --workspace <ws> --model <id> --src build/sm  # Fabric WRITE (ask first)

Adds: relationships (dim -> fact, single direction), measures on fact_shipment, dim_date as date table,
RLS roles "QA Manager" and "Ops Director". Idempotent: re-running replaces what it added.
"""
import argparse
import re
import uuid
from pathlib import Path

RELATIONSHIPS = [
    # (from table, from column) -> (to table, to column)
    *[((t, c), ("dim_facility", "facility_id")) for t, c in [
        ("fact_order_line", "ship_from_facility_id"), ("fact_shipment", "ship_from_facility_id"),
        ("fact_lot", "facility_id"), ("fact_waste", "facility_id"), ("fact_inventory_daily", "facility_id"),
        ("trace_genealogy", "facility_id")]],
    *[((t, "sku_id"), ("dim_product", "sku_id")) for t in [
        "fact_order_line", "fact_lot", "fact_waste", "fact_inventory_daily", "trace_genealogy"]],
    *[((t, "customer_id"), ("dim_customer", "customer_id")) for t in [
        "fact_order_line", "fact_shipment", "trace_genealogy"]],
    *[((t, c), ("dim_date", "date")) for t, c in [
        ("fact_order_line", "requested_delivery_date"), ("fact_shipment", "requested_delivery_date"),
        ("fact_lot", "production_date"), ("fact_waste", "waste_date"), ("fact_inventory_daily", "snapshot_date")]],
]

PCT, WHOLE, USD = "0.0%", "#,0", "\\$#,0"
MEASURES = [
    ("Cases Ordered", "SUM ( fact_order_line[cases_ordered] )", WHOLE),
    ("Cases Shipped", "SUM ( fact_order_line[cases_shipped] )", WHOLE),
    ("Cases Delivered", "SUM ( fact_order_line[cases_delivered] )", WHOLE),
    ("Fill Rate %", "DIVIDE ( [Cases Shipped], [Cases Ordered] )", PCT),
    ("Net Revenue", "SUM ( fact_order_line[net_revenue_usd] )", USD),
    ("Shipments", "COUNTROWS ( fact_shipment )", WHOLE),
    ("On Time %", "DIVIDE ( CALCULATE ( [Shipments], fact_shipment[on_time] = TRUE () ), [Shipments] )", PCT),
    ("OTIF %", "DIVIDE ( CALCULATE ( [Shipments], fact_shipment[otif] = TRUE () ), [Shipments] )", PCT),
    ("Excursion Shipments", "CALCULATE ( [Shipments], fact_shipment[is_excursion] = TRUE () )", WHOLE),
    ("Cases Produced", "SUM ( fact_lot[cases_produced] )", WHOLE),
    ("Waste Cases (Operational)",
     'CALCULATE ( SUM ( fact_waste[cases] ), KEEPFILTERS ( fact_waste[reason] IN { "Aged Out", "Damaged", "QA Reject" } ) )', WHOLE),
    ("Waste Rate %", "DIVIDE ( [Waste Cases (Operational)], [Cases Produced] )", PCT),
    ("Waste Cost", "SUM ( fact_waste[cost_usd] )", USD),
    ("Recall Cases Destroyed", 'CALCULATE ( SUM ( fact_waste[cases] ), fact_waste[reason] = "Supplier Recall" )', WHOLE),
    ("Cases On Hand (Latest)",
     "VAR LastSnapshot = MAX ( fact_inventory_daily[snapshot_date] ) RETURN CALCULATE ( SUM ( "
     "fact_inventory_daily[cases_on_hand] ), fact_inventory_daily[snapshot_date] = LastSnapshot )", WHOLE),
]

ROLES = {
    "QA Manager": "\ttablePermission dim_facility = [qa_manager_upn] = USERPRINCIPALNAME()\n",
    "Ops Director": "\ttablePermission dim_facility = TRUE()\n",
}
MARK = "/// added by tools/sm_patch_tmdl.py"


def q(name: str) -> str:
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else "'" + name.replace("'", "''") + "'"


def table_file(defn: Path, table: str) -> Path:
    for p in (defn / "tables").glob("*.tmdl"):
        if re.match(rf"^table\s+'?{re.escape(table)}'?\s*$", p.read_text(encoding="utf-8").splitlines()[0].strip()):
            return p
    raise SystemExit(f"table {table} not found in {defn / 'tables'}: add it to the model in the portal first")


def has_column(defn: Path, table: str, column: str) -> bool:
    return re.search(rf"^\tcolumn\s+'?{re.escape(column)}'?\s*$", table_file(defn, table).read_text(encoding="utf-8"),
                     re.M) is not None


def strip_added(text: str) -> str:
    # remove blocks previously added by this script (from MARK up to the next blank line)
    return re.sub(rf"\n?\t?{re.escape(MARK)}\n(?:\t.*\n)+", "\n", text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="build/sm")
    defn = Path(ap.parse_args().src) / "definition"

    # 1. relationships: replace the whole file (the portal-created model has none)
    missing = [f"{t}[{c}]" for (t, c), (dt, dc) in RELATIONSHIPS for (t, c) in [(t, c), (dt, dc)]
               if not has_column(defn, t, c)]
    if missing:
        raise SystemExit(f"columns missing in model: {sorted(set(missing))}")
    rel = "".join(f"relationship {uuid.uuid5(uuid.NAMESPACE_URL, f'{t}.{c}->{dt}.{dc}')}\n"
                  f"\tfromColumn: {q(t)}.{q(c)}\n\ttoColumn: {q(dt)}.{q(dc)}\n\n"
                  for (t, c), (dt, dc) in RELATIONSHIPS)
    (defn / "relationships.tmdl").write_text(rel, encoding="utf-8", newline="\n")

    # 2. measures on fact_shipment
    fs = table_file(defn, "fact_shipment")
    text = strip_added(fs.read_text(encoding="utf-8")).rstrip("\n") + "\n\n"
    text += "".join(f"\t{MARK}\n\tmeasure {q(n)} = {expr}\n\t\tformatString: {fmt}\n\t\tdisplayFolder: KPIs\n\n"
                    for n, expr, fmt in MEASURES)
    fs.write_text(text, encoding="utf-8", newline="\n")

    # 3. dim_date as date table
    dd = table_file(defn, "dim_date")
    lines = dd.read_text(encoding="utf-8").splitlines()
    if not any(l.strip() == "dataCategory: Time" for l in lines):
        lines.insert(1, "\tdataCategory: Time")
    for i, l in enumerate(lines):
        if re.match(r"^\tcolumn\s+'?date'?\s*$", l) and not any(x.strip() == "isKey" for x in lines[i + 1:i + 4]):
            lines.insert(i + 1, "\t\tisKey")
            break
    dd.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    # 4. RLS roles
    (defn / "roles").mkdir(exist_ok=True)
    for name, perm in ROLES.items():
        (defn / "roles" / f"{name}.tmdl").write_text(f"role {q(name)}\n\tmodelPermission: read\n\n{perm}",
                                                       encoding="utf-8", newline="\n")

    print(f"patched {defn}: {len(RELATIONSHIPS)} relationships, {len(MEASURES)} measures, "
          f"date table, roles {list(ROLES)}")


if __name__ == "__main__":
    main()

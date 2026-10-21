"""Make the 6 unfiltered facts RLS-scoped: relate each one directly to dim_facility (SM_FreshyFresh_Ops.md §7).

    python tools/sm_definition.py get --workspace <ws> --model <id> --out build/sm_rls             # read-only
    python tools/sm_add_facility_links.py --src build/sm_rls                                       # local edit only
    python tools/sm_definition.py update --workspace <ws> --model <id> --src build/sm_rls          # Fabric WRITE (ask first)

Needs gold with `facility_id` on fact_shipment_line, bridge_lot_ingredient, fact_quality_test and fact_supplier_notice
(NB_03_gold_fasttrack, 21 Oct 2026). Add-only like sm_add_fleet.py: adds that column where the table lacks it and
six many-to-one relationships to dim_facility[facility_id]; roles and other relationships stay as they are.
Idempotent. Refresh (frame) the model after the update.
"""
import argparse
import re
import uuid
from pathlib import Path

NEW_COLUMN = ["fact_shipment_line", "bridge_lot_ingredient", "fact_quality_test", "fact_supplier_notice"]
RELATIONSHIPS = [(t, "facility_id") for t in NEW_COLUMN + ["fact_ingredient_receipt"]] + \
                [("fact_order", "ship_from_facility_id")]


def lineage(*parts: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "freshyfresh-rls/" + "/".join(parts)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="build/sm_rls")
    defn = Path(ap.parse_args().src) / "definition"

    # 1. facility_id column (string), placed before the partition so the table file keeps its usual order
    for t in NEW_COLUMN:
        f = defn / "tables" / f"{t}.tmdl"
        text = f.read_text(encoding="utf-8")
        if re.search(r"^\tcolumn facility_id$", text, re.M):
            continue
        col = (f"\tcolumn facility_id\n\t\tdataType: string\n\t\tlineageTag: {lineage(t, 'facility_id')}\n"
               f"\t\tsourceLineageTag: facility_id\n\t\tsummarizeBy: none\n\t\tsourceColumn: facility_id\n\n"
               f"\t\tannotation SummarizationSetBy = Automatic\n\n")
        text, n = re.subn(r"^(\tpartition )", col.replace("\\", "\\\\") + r"\1", text, count=1, flags=re.M)
        if not n:
            raise SystemExit(f"{t}: no partition found")
        f.write_text(text, encoding="utf-8", newline="\n")

    # 2. relationships, found by their uuid5 names (no "///" marker: TMDL would read it as a description)
    rel_file = defn / "relationships.tmdl"
    text = rel_file.read_text(encoding="utf-8")
    ours = {str(uuid.uuid5(uuid.NAMESPACE_URL, f"{t}.{c}->dim_facility.facility_id")): (t, c) for t, c in RELATIONSHIPS}
    text = re.sub(rf"relationship ({'|'.join(ours)})\n(?:\t.*\n)+\n?", "", text).rstrip("\n") + "\n\n"
    for t, c in RELATIONSHIPS:
        if re.search(rf"fromColumn: {t}\.{c}\n\ttoColumn: dim_facility\.facility_id", text):
            raise SystemExit(f"{t}.{c} -> dim_facility already exists under another name; nothing to add")
    for rid, (t, c) in ours.items():
        text += f"relationship {rid}\n\tfromColumn: {t}.{c}\n\ttoColumn: dim_facility.facility_id\n\n"
    rel_file.write_text(text, encoding="utf-8", newline="\n")
    print(f"patched {defn}: facility_id on {len(NEW_COLUMN)} tables, {len(RELATIONSHIPS)} relationships to "
          f"dim_facility; roles untouched")


if __name__ == "__main__":
    main()

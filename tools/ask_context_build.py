"""Build the model context for the app's "Ask" function from the live SM_Ambermoor_Ops (read-only).          [D1]

    python tools/ask_context_build.py                  # writes app/rayfin/functions/src/model-context.ts

The Ask function sends this text to Claude with each question, so Claude can write DAX against the real model.
It holds table/column/measure names, measure DAX, relationships and a few small dimension value lists (plant ids
and names, channels, waste reasons). No fact rows, no IDs, no emails. Re-run after any model change.
Needs `az login` and Write on the model (executeQueries over INFO functions runs as you, an admin).
"""
import base64
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

FABRIC = "https://api.fabric.microsoft.com/v1"
PBI = "https://api.powerbi.com/v1.0/myorg"
OUT = Path("app/rayfin/functions/src/model-context.ts")
# small, non-personal dimension lists that help Claude write correct filters
VALUE_LISTS = {
    "dim_facility": 'SELECTCOLUMNS ( dim_facility, "v", dim_facility[facility_id] & " = " & dim_facility[facility_name] '
                    '& " (" & dim_facility[facility_type] & ", " & dim_facility[country] & ")" )',
    "dim_customer[channel]": "VALUES ( dim_customer[channel] )",
    "fact_waste[reason]": "VALUES ( fact_waste[reason] )",
    "dim_product[category]": "VALUES ( dim_product[category] )",
    "dim_truck[unit_type]": "VALUES ( dim_truck[unit_type] )",
}
SKIP_COLUMNS = {"qa_manager_upn", "contact_email", "contact_phone"}   # RLS key and PII-style columns: never needed


def token(resource: str) -> str:
    return subprocess.run(f"az account get-access-token --resource {resource} --query accessToken -o tsv",
                          shell=True, capture_output=True, text=True, check=True).stdout.strip()


def call(url, tok, body=None):
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                               headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
                               method="POST" if body else "GET")
    with urllib.request.urlopen(r, timeout=120) as resp:
        return json.loads(resp.read())


def measures(ws, sm, ftok):
    """Measure DAX from the TMDL definition (INFO.MEASURES() is not allowed through executeQueries)."""
    r = urllib.request.Request(f"{FABRIC}/workspaces/{ws}/semanticModels/{sm}/getDefinition?format=TMDL", data=b"",
                               method="POST", headers={"Authorization": f"Bearer {ftok}"})
    with urllib.request.urlopen(r, timeout=120) as resp:
        loc, body = resp.headers.get("Location"), resp.read()
    while resp.status == 202 and loc:
        time.sleep(3)
        st = call(loc, ftok)
        if st["status"] == "Succeeded":
            body = json.dumps(call(loc + "/result", ftok)).encode()
            break
        if st["status"] in ("Failed", "Cancelled"):
            sys.exit(f"getDefinition {st['status']}")
    out = []
    for part in json.loads(body)["definition"]["parts"]:
        if part["path"].startswith("definition/tables/"):
            tmdl = base64.b64decode(part["payload"]).decode("utf-8")
            out += [(m.group(1).strip("'"), m.group(2)) for m in re.finditer(r"^	measure (.+?) = (.+)$", tmdl, re.M)]
    return out


def main():
    ftok, ptok = token("https://api.fabric.microsoft.com"), token("https://analysis.windows.net/powerbi/api")
    ws = next(w["id"] for w in call(f"{FABRIC}/workspaces", ftok)["value"] if w["displayName"] == "WS-AMBERMOOR-DEV")
    sm = next(i["id"] for i in call(f"{FABRIC}/workspaces/{ws}/items?type=SemanticModel", ftok)["value"]
              if i["displayName"] == "SM_Ambermoor_Ops")

    def dax(q):
        try:
            res = call(f"{PBI}/groups/{ws}/datasets/{sm}/executeQueries", ptok, {"queries": [{"query": q}]})
        except urllib.error.HTTPError as e:
            raise SystemExit(f"DAX failed: {q[:80]}... -> {e.code} {e.read()[:300]!r}")
        return [list(r.values()) for r in res["results"][0]["tables"][0]["rows"]]

    cols = dax('EVALUATE SELECTCOLUMNS ( INFO.VIEW.COLUMNS (), "t", [Table], "c", [Name], "d", [DataType] )')
    meas = measures(ws, sm, ftok)
    rels = dax('EVALUATE SELECTCOLUMNS ( INFO.VIEW.RELATIONSHIPS (), "f", [FromTable] & "[" & [FromColumn] & "]", '
               '"t", [ToTable] & "[" & [ToColumn] & "]" )')

    # RLS lives on dim_facility, so only facts with a relationship to it are row-filtered. Facts without one would
    # show every plant's rows to a plant user: keep them out of the Ask context (the function also blocks them).
    scoped = {f.split("[")[0] for f, t in rels if t.startswith("dim_facility[")}
    allowed = {t for t, _, _ in cols if t.startswith("dim_") or t in scoped}
    blocked = sorted({t for t, _, _ in cols} - allowed)
    rels = [(f, t) for f, t in rels if f.split("[")[0] in allowed]
    tables: dict[str, list[str]] = {}
    for t, c, d in cols:
        if t in allowed and not c.startswith("RowNumber") and c not in SKIP_COLUMNS:
            tables.setdefault(t, []).append(f"{c} ({d})")
    lines = ["TABLES (columns with data type):"]
    lines += [f"- {t}: {', '.join(cs)}" for t, cs in sorted(tables.items())]
    lines += ["", "RELATIONSHIPS (many -> one, single direction, dimension filters fact):"]
    lines += [f"- {f} -> {t}" for f, t in sorted(rels)]
    lines += ["", "MEASURES (use these instead of re-deriving the business rules):"]
    lines += [f"- [{m}] = {' '.join(e.split())}" for m, e in sorted(meas)]
    lines += ["", "VALUE LISTS:"]
    for name, q in VALUE_LISTS.items():
        lines.append(f"- {name}: " + "; ".join(sorted(str(v[0]) for v in dax(f"EVALUATE {q}") if v and v[0] is not None)))

    text = "\n".join(lines)
    OUT.write_text("// Generated by tools/ask_context_build.py from the live SM_Ambermoor_Ops. Do not edit by hand.\n"
                   "// Names, measure DAX and small dimension lists only: no fact rows, IDs or emails.\n"
                   f"export const MODEL_CONTEXT = {json.dumps(text)};\n"
                   "// Facts with no relationship to dim_facility: RLS does not filter them, so Ask must not query them.\n"
                   f"export const BLOCKED_TABLES: readonly string[] = {json.dumps(blocked)};\n", encoding="utf-8")
    print(f"wrote {OUT}: {len(tables)} tables, {len(meas)} measures, {len(rels)} relationships, {len(text):,} chars; "
          f"blocked (not RLS-scoped): {blocked}")


if __name__ == "__main__":
    main()

"""One run that connects the app's holds to SM_FreshyFresh_Ops.                              [D1][D2] Fabric WRITE

    python tools/holds_link_apply.py

1. Schema shortcut `app` in LH_FreshyFresh (WS-FRESHYFRESH-DEV) -> the app SQL database's mirrored Tables/dbo
   (WS-FRESHYFRESH-APP). The SQL database mirrors to OneLake automatically; this adds no copy.
2. Refresh the lakehouse SQL endpoint metadata for the app schema (so T-SQL and the agent see it).
3. Read the mirrored Delta schemas -> build/holds_schema.json.
4. Model: get TMDL -> tools/sm_add_holds.py -> update (add-only; roles untouched).
5. Refresh (frame) SM_FreshyFresh_Ops and wait.
Every step stops on failure. IDs are looked up by name and never printed; the token is never printed.
Learn: https://learn.microsoft.com/rest/api/fabric/core/onelake-shortcuts/create-shortcut,
https://learn.microsoft.com/fabric/database/sql/mirroring-overview
"""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

FABRIC, PBI = "https://api.fabric.microsoft.com/v1", "https://api.powerbi.com/v1.0/myorg"
ONELAKE = "https://onelake.dfs.fabric.microsoft.com"
SOURCES = ["QualityHolds", "CorrectiveActions", "HoldUpdates"]


def token(resource):
    return subprocess.run(f"az account get-access-token --resource {resource} --query accessToken -o tsv",
                          shell=True, capture_output=True, text=True, check=True).stdout.strip()


def call(tok, method, url, body=None, raw=False):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method,
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json",
                                          "x-ms-version": "2023-11-03"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
            return r.status, r.headers, (data if raw else (json.loads(data) if data else None))
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {url.split('/v1')[-1].split('?')[0][:50]}... -> {e.code} {e.read()[:400]!r}")


def step(name, cmd):
    print(f"== {name}", flush=True)
    if subprocess.run(cmd).returncode:
        sys.exit(f"stopped: {name} failed")


def delta_schema(st, ws, item, table):
    """Columns of a Delta table from its log: the newest metaData in the JSON commits, else the last checkpoint."""
    import duckdb
    base = f"{ONELAKE}/{ws}"
    paths = [p["name"] for p in call(st, "GET", f"{base}?resource=filesystem&recursive=true&directory="
                                                f"{item}/Tables/dbo/{table}/_delta_log")[2]["paths"]]
    schema = None
    checkpoints = sorted(p for p in paths if p.endswith(".checkpoint.parquet"))
    if checkpoints:
        f = Path(f"build/holds_schema/{table}.checkpoint.parquet")
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(call(st, "GET", f"{base}/{checkpoints[-1]}", raw=True)[2])
        row = duckdb.sql(f"SELECT metaData.schemaString FROM read_parquet('{f.as_posix()}') "
                         "WHERE metaData IS NOT NULL").fetchone()
        schema = json.loads(row[0]) if row else None
    for commit in sorted(p for p in paths if p.endswith(".json")):
        for line in call(st, "GET", f"{base}/{commit}", raw=True)[2].decode().splitlines():
            entry = json.loads(line)
            if "metaData" in entry:
                schema = json.loads(entry["metaData"]["schemaString"])
    if not schema:
        sys.exit(f"no Delta schema found for {table}")
    return [[c["name"], c["type"]] for c in schema["fields"]]


def main():
    ft, st = token("https://api.fabric.microsoft.com"), token("https://storage.azure.com")
    spaces = {w["displayName"]: w["id"] for w in call(ft, "GET", f"{FABRIC}/workspaces")[2]["value"]}
    dev, app = spaces["WS-FRESHYFRESH-DEV"], spaces["WS-FRESHYFRESH-APP"]
    items = call(ft, "GET", f"{FABRIC}/workspaces/{dev}/items")[2]["value"]
    lh = next(i["id"] for i in items if i["type"] == "Lakehouse" and i["displayName"] == "LH_FreshyFresh")
    ep = next(i["id"] for i in items if i["type"] == "SQLEndpoint" and i["displayName"] == "LH_FreshyFresh")
    sm = next(i["id"] for i in items if i["type"] == "SemanticModel" and i["displayName"] == "SM_FreshyFresh_Ops")
    dbs = call(ft, "GET", f"{FABRIC}/workspaces/{app}/sqlDatabases")[2]["value"]
    if len(dbs) != 1:
        sys.exit(f"expected 1 SQL database in WS-FRESHYFRESH-APP, found {len(dbs)}")
    db = dbs[0]["id"]

    print("== 1. schema shortcut LH_FreshyFresh/Tables/app -> app SQL database Tables/dbo", flush=True)
    call(ft, "POST", f"{FABRIC}/workspaces/{dev}/items/{lh}/shortcuts?shortcutConflictPolicy=CreateOrOverwrite",
         {"path": "Tables", "name": "app", "target": {"oneLake": {"workspaceId": app, "itemId": db, "path": "Tables/dbo"}}})
    time.sleep(10)
    seen = sorted(p["name"].split("/")[-1] for p in call(st, "GET", f"{ONELAKE}/{dev}?resource=filesystem&recursive=false"
                                                                    f"&directory={lh}/Tables/app")[2]["paths"])
    print("   app schema tables:", seen)
    if not set(SOURCES) <= set(seen):
        sys.exit("stopped: the shortcut does not show the hold tables")

    print("== 2. refresh SQL endpoint metadata (app schema)", flush=True)
    status, headers, body = call(ft, "POST", f"{FABRIC}/workspaces/{dev}/sqlEndpoints/{ep}/refreshMetadata",
                                 {"tables": [{"schema": "app", "tableNames": SOURCES}]})
    while status == 202:
        time.sleep(int(headers.get("Retry-After", 5)))
        op = call(ft, "GET", headers["Location"])[2]
        if op["status"] in ("Succeeded", "Failed"):
            body = call(ft, "GET", headers["Location"] + "/result")[2] if op["status"] == "Succeeded" else op
            break
    print("  ", [(t["tableName"], t["status"]) for t in (body or {}).get("value", [])])

    print("== 3. read mirrored Delta schemas", flush=True)
    schema = {t: delta_schema(st, app, db, t) for t in SOURCES}
    Path("build").mkdir(exist_ok=True)
    Path("build/holds_schema.json").write_text(json.dumps(schema, indent=1), encoding="utf-8")
    print("  ", {t: len(c) for t, c in schema.items()}, "columns")

    step("4a. get model definition", [sys.executable, "tools/sm_definition.py", "get", "--workspace", dev,
                                      "--model", sm, "--out", "build/sm_holds"])
    step("4b. patch", [sys.executable, "tools/sm_add_holds.py", "--src", "build/sm_holds",
                       "--schema", "build/holds_schema.json"])
    step("4c. update model definition", [sys.executable, "tools/sm_definition.py", "update", "--workspace", dev,
                                         "--model", sm, "--src", "build/sm_holds"])

    print("== 5. refresh (frame) the model", flush=True)
    pt = token("https://analysis.windows.net/powerbi/api")
    call(pt, "POST", f"{PBI}/groups/{dev}/datasets/{sm}/refreshes", {"notifyOption": "NoNotification"})
    for _ in range(60):
        time.sleep(10)
        last = call(pt, "GET", f"{PBI}/groups/{dev}/datasets/{sm}/refreshes?$top=1")[2]["value"][0]
        if last["status"] != "Unknown":   # Unknown = still running
            print(f"   refresh {last['status']}")
            sys.exit(0 if last["status"] == "Completed" else 1)
    sys.exit("refresh still running after 10 min; check the model's refresh history")


if __name__ == "__main__":
    main()

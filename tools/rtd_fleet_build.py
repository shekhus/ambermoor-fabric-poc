"""Build (and optionally push) the RTD_FreshyFresh_Fleet Real-Time Dashboard definition as code.        [D3]

    python tools/rtd_fleet_build.py --out build/rtd                 # read-only: resolve IDs, write + validate JSON
    python tools/rtd_fleet_build.py --out build/rtd --push          # Fabric WRITE: updateDefinition (ask first)

Tiles come from fabric/kql/fleet_dashboard.kql, without dashboard parameters (historical data has no "now"; the
truck tiles use TRK-117, the cold-chain story truck). Add parameters later in the dashboard UI.
Format: RealTimeDashboard.json, schema https://dataexplorer.azure.com/static/d/schema/89/dashboard.json
(Learn: "Real-time dashboard - Git integration"). Every id must be an RFC 4122 UUID and every query is referenced
exactly once; ids are uuid5 so reruns keep them. The output holds workspace/item IDs: build/ is gitignored.
Optional local validation: pip install jsonschema, and put the schema files (dashboard, tile, query, parameter,
dataSource .json) in --schema-dir.
"""
import argparse
import base64
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

API = "https://api.fabric.microsoft.com/v1"
SCHEMA_VERSION = 89
NS = uuid.uuid5(uuid.NAMESPACE_URL, "ambermoor/RTD_Ambermoor_Fleet")

LAST_DAYS = "let last_ts = toscalar(ReeferTelemetry | summarize max(ts));\n"
TILES = [
    # (title, visualType, layout x, y, w, h, visualOptions, KQL)
    ("Where every truck is now (latest reading)", "map", 0, 0, 14, 10,
     {"map__type": "bubble", "map__bubbleFormat": "dot", "map__geoType": "numeric",
      "map__latitudeColumn": "latitude", "map__longitudeColumn": "longitude", "map__labelColumn": "truck_id",
      "map__sizeDisabled": True},
     "TruckLatestPosition()\n| project truck_id, latitude, longitude, status, temp_c, speed_kmh, shipment_id, ts"),
    ("Fleet at a glance", "table", 14, 0, 10, 4, {},
     "TruckLatestPosition()\n| summarize Trucks = count(), Moving = countif(status == \"Moving\"),\n"
     "    ['Stopped or at dock'] = countif(status in (\"Stopped\", \"At dock / parked\")),\n"
     "    ['Warm loads'] = countif(status startswith \"Warm load\")"),
    ("Warm-load alarms (same rows the Activator rule fires on)", "table", 14, 4, 10, 6, {},
     "TruckLatestPosition()\n| where status startswith \"Warm load\"\n"
     "| project truck_id, shipment_id, temp_c, speed_kmh, status, ts"),
    ("TRK-117 reefer temperature, last 2 days of readings", "timechart", 0, 10, 12, 8, {},
     "let last_ts = toscalar(ReeferTelemetry | where truck_id == \"TRK-117\" | summarize max(ts));\n"
     "ReeferTelemetry\n| where truck_id == \"TRK-117\" and ts > last_ts - 2d\n| project ts, temp_c, setpoint_c\n"
     "| order by ts asc"),
    ("Breadcrumb trail of shipment SH000752 (TRK-117 excursion)", "map", 12, 10, 12, 8,
     {"map__type": "bubble", "map__bubbleFormat": "dot", "map__geoType": "numeric",
      "map__latitudeColumn": "latitude", "map__longitudeColumn": "longitude", "map__labelColumn": "temp_c",
      "map__sizeDisabled": True},
     "ReeferTelemetry\n| where shipment_id == \"SH000752\"\n"
     "| project ts, latitude, longitude, temp_c, speed_kmh, reefer_status\n| order by ts asc"),
    ("Shipments that waited > 2 h at the dock (from GPS)", "column", 0, 18, 12, 8, {},
     "ReeferTelemetry\n| summarize first_ts = min(ts), departed_ts = minif(ts, speed_kmh > 0) by shipment_id, facility_id\n"
     "| extend dock_wait_h = (departed_ts - first_ts) / 1h\n"
     "| summarize ['Waited > 2 h'] = countif(dock_wait_h > 2) by facility_id\n| order by facility_id asc"),
    ("Trucks on the road per hour, last 3 days of data", "timechart", 12, 18, 12, 8, {},
     LAST_DAYS + "ReeferTelemetry\n| where ts > last_ts - 3d\n"
     "| summarize ['Trucks moving'] = dcountif(truck_id, speed_kmh > 0) by bin(ts, 1h)\n| order by ts asc"),
]


def token() -> str:
    out = subprocess.run("az account get-access-token --resource https://api.fabric.microsoft.com --query accessToken -o tsv",
                         shell=True, capture_output=True, text=True, check=True)
    return out.stdout.strip()


def call(method, path, tok, body=None):
    url = path if path.startswith("http") else API + path
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method,
                               headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            raw = resp.read()
            return resp.status, dict(resp.headers), (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), {"error": e.read().decode(errors="replace")[:600]}


def wait(st, headers, body, tok):
    if st != 202:
        return st, body
    while True:
        time.sleep(3)
        _, _, s = call("GET", headers["Location"], tok)
        if s.get("status") in ("Succeeded", "Failed", "Cancelled"):
            return (200 if s["status"] == "Succeeded" else 500), s


def build(ws_id: str, db_id: str, cluster_uri: str) -> dict:
    uid = lambda *k: str(uuid.uuid5(NS, "/".join(k)))   # noqa: E731
    ds_id, page_id = uid("ds"), uid("page")
    tiles, queries = [], []
    for title, vt, x, y, w, h, opts, kql in TILES:
        qid = uid("query", title)
        queries.append({"id": qid, "dataSource": {"kind": "inline", "dataSourceId": ds_id}, "text": kql,
                        "usedVariables": []})
        tiles.append({"id": uid("tile", title), "title": title, "visualType": vt, "pageId": page_id,
                      "layout": {"x": x, "y": y, "width": w, "height": h},
                      "queryRef": {"kind": "query", "queryId": qid}, "visualOptions": opts})
    return {
        "$schema": f"https://dataexplorer.azure.com/static/d/schema/{SCHEMA_VERSION}/dashboard.json",
        "id": uid("dashboard"), "schema_version": SCHEMA_VERSION, "title": "RTD_FreshyFresh_Fleet",
        "tiles": tiles, "baseQueries": [], "parameters": [], "embeddedApps": [],
        "dataSources": [{"id": ds_id, "name": "KQL_ColdChain", "kind": "kusto-trident", "clusterUri": cluster_uri,
                         "databaseArtifactId": db_id, "database": db_id, "workspace": ws_id}],
        "pages": [{"id": page_id, "name": "Fleet now"}],
        "queries": queries,
    }


def validate(dash: dict, schema_dir: Path):
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
    resources = []
    for f in schema_dir.glob("*.json"):
        s = json.loads(f.read_text(encoding="utf-8"))
        resources.append((s["$id"], Resource.from_contents(s)))
    reg = Registry().with_resources(resources)
    root = next(r for i, r in resources if i.endswith("/dashboard.json")).contents
    errors = sorted(Draft202012Validator(root, registry=reg).iter_errors(dash), key=lambda e: list(e.path))
    for e in errors[:15]:
        print("SCHEMA:", "/".join(map(str, e.path)), "-", e.message[:200])
    return not errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default="WS-FRESHYFRESH-DEV")
    ap.add_argument("--out", default="build/rtd")
    ap.add_argument("--schema-dir")
    ap.add_argument("--push", action="store_true", help="Fabric WRITE: replace the dashboard definition")
    a = ap.parse_args()
    tok = token()
    _, _, w = call("GET", "/workspaces", tok)
    ws = next(x["id"] for x in w["value"] if x["displayName"] == a.workspace)
    _, _, items = call("GET", f"/workspaces/{ws}/items", tok)
    by = {(i["type"], i["displayName"]): i["id"] for i in items["value"]}
    db = by[("KQLDatabase", "KQL_ColdChain")]
    _, _, dbinfo = call("GET", f"/workspaces/{ws}/kqlDatabases/{db}", tok)
    dash = build(ws, db, dbinfo["properties"]["queryServiceUri"])
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "RealTimeDashboard.json").write_text(json.dumps(dash, indent=2), encoding="utf-8")
    print(f"wrote {out / 'RealTimeDashboard.json'}: {len(dash['tiles'])} tiles")
    if a.schema_dir and not validate(dash, Path(a.schema_dir)):
        sys.exit("schema validation failed")
    if a.push:
        rtd = by.get(("KQLDashboard", "RTD_FreshyFresh_Fleet"))
        if not rtd:
            sys.exit("RTD_FreshyFresh_Fleet not found: create it first (New item > Real-Time Dashboard)")
        payload = base64.b64encode(json.dumps(dash).encode()).decode()
        body = {"definition": {"parts": [{"path": "RealTimeDashboard.json", "payload": payload,
                                          "payloadType": "InlineBase64"}]}}
        st, res = wait(*call("POST", f"/workspaces/{ws}/kqlDashboards/{rtd}/updateDefinition", tok, body), tok)
        print("push:", "OK" if st == 200 else (st, res))


if __name__ == "__main__":
    main()

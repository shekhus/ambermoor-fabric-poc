"""One run that makes the 6 unfiltered facts RLS-scoped in WS-FRESHYFRESH-DEV.               [D1] Fabric WRITE

    python tools/rls_links_apply.py

1. Push + run NB_03_gold_fasttrack (adds facility_id to 4 gold tables; its acceptance cell checks no nulls).
2. Refresh the SQL analytics endpoint metadata for those 4 tables (T-SQL and the agent see the new column).
3. Model: get TMDL -> tools/sm_add_facility_links.py -> update (add-only; roles untouched).
4. Refresh (frame) SM_FreshyFresh_Ops and wait.
Every step stops on failure. IDs are looked up by name and never printed; the token is never printed.
"""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

FABRIC, PBI = "https://api.fabric.microsoft.com/v1", "https://api.powerbi.com/v1.0/myorg"
TABLES = ["fact_shipment_line", "bridge_lot_ingredient", "fact_quality_test", "fact_supplier_notice"]


def token(resource):
    return subprocess.run(f"az account get-access-token --resource {resource} --query accessToken -o tsv",
                          shell=True, capture_output=True, text=True, check=True).stdout.strip()


def call(tok, method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method,
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
            return r.status, r.headers, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} -> {e.code} {e.read()[:400]!r}")


def step(name, cmd):
    print(f"== {name}", flush=True)
    if subprocess.run(cmd).returncode:
        sys.exit(f"stopped: {name} failed")


def main():
    ft = token("https://api.fabric.microsoft.com")
    ws = next(w["id"] for w in call(ft, "GET", f"{FABRIC}/workspaces")[2]["value"]
              if w["displayName"] == "WS-FRESHYFRESH-DEV")
    items = call(ft, "GET", f"{FABRIC}/workspaces/{ws}/items")[2]["value"]
    sm = next(i["id"] for i in items if i["type"] == "SemanticModel" and i["displayName"] == "SM_FreshyFresh_Ops")
    ep = next(i["id"] for i in items if i["type"] == "SQLEndpoint" and i["displayName"] == "LH_FreshyFresh")

    step("1. push + run NB_03_gold_fasttrack", [sys.executable, "tools/nb_push_run.py", "NB_03_gold_fasttrack", "--run"])

    print("== 2. refresh SQL endpoint metadata", flush=True)
    st, h, body = call(ft, "POST", f"{FABRIC}/workspaces/{ws}/sqlEndpoints/{ep}/refreshMetadata",
                       {"tables": [{"schema": "gold", "tableNames": TABLES}]})
    while st == 202:
        time.sleep(int(h.get("Retry-After", 5)))
        op = call(ft, "GET", h["Location"])[2]
        if op["status"] in ("Succeeded", "Failed"):
            body = call(ft, "GET", h["Location"] + "/result")[2] if op["status"] == "Succeeded" else op
            break
    print("  ", [(t["tableName"], t["status"]) for t in (body or {}).get("value", [])])

    step("3a. get model definition", [sys.executable, "tools/sm_definition.py", "get", "--workspace", ws,
                                      "--model", sm, "--out", "build/sm_rls"])
    step("3b. patch", [sys.executable, "tools/sm_add_facility_links.py", "--src", "build/sm_rls"])
    step("3c. update model definition", [sys.executable, "tools/sm_definition.py", "update", "--workspace", ws,
                                         "--model", sm, "--src", "build/sm_rls"])

    print("== 4. refresh (frame) the model", flush=True)
    pt = token("https://analysis.windows.net/powerbi/api")
    call(pt, "POST", f"{PBI}/groups/{ws}/datasets/{sm}/refreshes", {"notifyOption": "NoNotification"})
    for _ in range(60):
        time.sleep(10)
        last = call(pt, "GET", f"{PBI}/groups/{ws}/datasets/{sm}/refreshes?$top=1")[2]["value"][0]
        if last["status"] != "Unknown":   # Unknown = still running
            print(f"   refresh {last['status']}")
            sys.exit(0 if last["status"] == "Completed" else 1)
    sys.exit("refresh still running after 10 min; check the model's refresh history")


if __name__ == "__main__":
    main()

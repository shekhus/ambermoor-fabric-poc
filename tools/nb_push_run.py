"""Push a notebook's repo source (fabric/notebooks/*.py) to its Fabric notebook, then optionally run it.  [D1][D2]

    python tools/nb_push_run.py NB_03_gold_fasttrack            # push only          (Fabric WRITE)
    python tools/nb_push_run.py NB_03_gold_fasttrack --run      # push, run, wait    (Fabric WRITE + capacity)

Keeps what only the live notebook holds: its metadata (default lakehouse binding) and the live `upn_overrides`
parameter line (real RLS test-user UPNs never live in the repo). Workspace WS-FRESHYFRESH-DEV, looked up by name.
APIs (Fabric REST v1): notebooks/{id}/getDefinition?format=ipynb, notebooks/{id}/updateDefinition,
notebooks/{id}/jobs/execute/instances?jobType=RunNotebook (Job Scheduler). The token is never printed.
Learn: https://learn.microsoft.com/fabric/data-engineering/notebook-public-api
"""
import argparse
import base64
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from py_to_ipynb import NOTEBOOKS, to_cells  # noqa: E402

API = "https://api.fabric.microsoft.com/v1"
WORKSPACE = "WS-FRESHYFRESH-DEV"
KEEP_LIVE_PARAMS = ["upn_overrides"]


def token() -> str:
    return subprocess.run("az account get-access-token --resource https://api.fabric.microsoft.com "
                          "--query accessToken -o tsv", shell=True, capture_output=True, text=True,
                          check=True).stdout.strip()


def call(tok, method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else
                                 (b"" if method == "POST" else None), method=method,
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
            return r.status, r.headers, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {url.split('/v1/')[-1][:60]}... -> {e.code} {e.read()[:400]!r}")


def wait_lro(tok, status, headers, body):
    """Long-running operation: poll the Location until Succeeded, then fetch /result if there is one."""
    while status == 202:
        time.sleep(int(headers.get("Retry-After", 3)))
        _, _, op = call(tok, "GET", headers["Location"])
        if op["status"] == "Succeeded":
            try:
                return call(tok, "GET", headers["Location"] + "/result")[2]
            except SystemExit:
                return None
        if op["status"] in ("Failed", "Cancelled"):
            sys.exit(f"operation {op['status']}: {op.get('error')}")
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("notebook", choices=sorted(NOTEBOOKS))
    ap.add_argument("--run", action="store_true", help="run it after the push and wait for the result")
    a = ap.parse_args()
    tok = token()
    ws = next(w["id"] for w in call(tok, "GET", f"{API}/workspaces")[2]["value"] if w["displayName"] == WORKSPACE)
    nb_id = next(i["id"] for i in call(tok, "GET", f"{API}/workspaces/{ws}/items?type=Notebook")[2]["value"]
                 if i["displayName"] == a.notebook)
    base = f"{API}/workspaces/{ws}/notebooks/{nb_id}"

    live = wait_lro(tok, *call(tok, "POST", f"{base}/getDefinition?format=ipynb"))
    part = next(p for p in live["definition"]["parts"] if p["path"].endswith(".ipynb"))
    nb = json.loads(base64.b64decode(part["payload"]))
    live_params = next(c for c in nb["cells"] if "parameters" in c.get("metadata", {}).get("tags", []))
    src = live_params["source"] if isinstance(live_params["source"], str) else "".join(live_params["source"])
    keep = {ln.split("=", 1)[0].strip(): ln for ln in src.splitlines()
            if ln.split("=", 1)[0].strip() in KEEP_LIVE_PARAMS}

    nb["cells"] = to_cells(Path(NOTEBOOKS[a.notebook]).read_text(encoding="utf-8"), keep)
    payload = base64.b64encode(json.dumps(nb).encode()).decode()
    wait_lro(tok, *call(tok, "POST", f"{base}/updateDefinition", {"definition": {"format": "ipynb", "parts": [
        {"path": part["path"], "payload": payload, "payloadType": "InlineBase64"}]}}))
    print(f"pushed {a.notebook}: {len(nb['cells'])} cells (kept live: {', '.join(keep) or 'none'})")
    if not a.run:
        return

    status, headers, _ = call(tok, "POST", f"{base}/jobs/execute/instances?jobType=RunNotebook")
    job = headers["Location"]
    started = time.time()
    while True:
        time.sleep(15)
        _, _, j = call(tok, "GET", job)
        if j["status"] in ("Completed", "Failed", "Cancelled", "Deduped"):
            break
        print(f"  {j['status']} ({time.time() - started:.0f} s)")
    print(f"run {j['status']} in {time.time() - started:.0f} s" + (f": {j.get('failureReason')}" if j["status"] != "Completed" else ""))
    sys.exit(0 if j["status"] == "Completed" else 1)


if __name__ == "__main__":
    main()

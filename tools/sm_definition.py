"""Get / update a semantic model definition (TMDL) through the Fabric REST API, using your `az login`.

    python tools/sm_definition.py get    --workspace <ws-guid> --model <model-guid> --out build/sm
    python tools/sm_definition.py update --workspace <ws-guid> --model <model-guid> --src build/sm   # Fabric WRITE

`get` is read-only. `update` overwrites the model definition: get Shekhar's OK first (CLAUDE.md safety rules).
APIs (Fabric REST v1, long-running operations):
  POST /v1/workspaces/{ws}/semanticModels/{id}/getDefinition?format=TMDL
  POST /v1/workspaces/{ws}/semanticModels/{id}/updateDefinition
Learn: https://learn.microsoft.com/rest/api/fabric/semanticmodel/items/update-semantic-model-definition
The token is never printed.
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

API = "https://api.fabric.microsoft.com/v1"


def token() -> str:
    out = subprocess.run(
        "az account get-access-token --resource https://api.fabric.microsoft.com --query accessToken -o tsv",
        shell=True, capture_output=True, text=True, check=True)
    return out.stdout.strip()


def call(method: str, url: str, tok: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return r.status, dict(r.headers), (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} {method} {url.split('?')[0]}\n{e.read().decode(errors='replace')}")


def run_lro(method: str, url: str, tok: str, body: dict | None = None, want_result: bool = False):
    status, headers, payload = call(method, url, tok, body)
    if status != 202:
        return payload
    op = headers.get("Location") or headers.get("location")
    while True:
        time.sleep(int(headers.get("Retry-After", 5)))
        _, headers, state = call("GET", op, tok)
        s = (state or {}).get("status")
        print(f"  operation: {s}")
        if s == "Succeeded":
            return call("GET", op.rstrip("/") + "/result", tok)[2] if want_result else state
        if s in ("Failed", "Cancelled"):
            sys.exit(json.dumps(state, indent=2))


def get(ws: str, model: str, out: Path):
    res = run_lro("POST", f"{API}/workspaces/{ws}/semanticModels/{model}/getDefinition?format=TMDL", token(), want_result=True)
    out.mkdir(parents=True, exist_ok=True)
    for part in res["definition"]["parts"]:
        p = out / part["path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(base64.b64decode(part["payload"]))
        print(f"wrote {p}")


def update(ws: str, model: str, src: Path):
    parts = [{"path": p.relative_to(src).as_posix(),
              "payload": base64.b64encode(p.read_bytes()).decode(),
              "payloadType": "InlineBase64"}
             for p in sorted(src.rglob("*")) if p.is_file() and p.name != ".platform"]
    print(f"uploading {len(parts)} parts: {[x['path'] for x in parts]}")
    run_lro("POST", f"{API}/workspaces/{ws}/semanticModels/{model}/updateDefinition", token(),
            {"definition": {"format": "TMDL", "parts": parts}})
    print("updateDefinition: Succeeded")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["get", "update"])
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", default="build/sm")
    ap.add_argument("--src", default="build/sm")
    a = ap.parse_args()
    get(a.workspace, a.model, Path(a.out)) if a.action == "get" else update(a.workspace, a.model, Path(a.src))

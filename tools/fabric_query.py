#!/usr/bin/env python3
"""
Read-only query tool for "Ask Ambermoor" on Fabric TRIAL (no Data Agent needed).
Lets Claude Code run T-SQL against the LH_Ambermoor SQL analytics endpoint and KQL against KQL_ColdChain,
using your Azure CLI sign-in. It refuses anything that isn't a read.

Setup (once):
  1. az login --tenant <TENANT_ID> --allow-no-subscriptions
  2. pip install -r requirements.txt   (pyodbc, azure-identity, azure-kusto-data)
     + Microsoft "ODBC Driver 18 for SQL Server" on your OS (Windows/macOS/Linux installers on Microsoft Learn)
  3. Copy fabric.endpoints.example.json -> fabric.endpoints.json (gitignored) and fill in:
       sql_server   : LH_Ambermoor > SQL analytics endpoint > settings > SQL connection string (host name)
       sql_database : LH_Ambermoor
       kql_query_uri: KQL_ColdChain > Database details > Query URI
       kql_database : KQL_ColdChain

Usage:
  python tools/fabric_query.py sql "SELECT TOP 5 * FROM gold.dim_facility"
  python tools/fabric_query.py kql "ReeferTelemetry | take 5"
  python tools/fabric_query.py sql --file query.sql --format table

Verify on Learn if auth fails: the SQL token audience used here is https://database.windows.net/.default
(the standard Entra audience for TDS endpoints); KQL uses Azure CLI auth via azure-kusto-data.
"""
import argparse
import csv
import json
import re
import struct
import sys
from pathlib import Path

WRITE_SQL = re.compile(r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|TRUNCATE|EXEC|EXECUTE|GRANT|REVOKE|DENY|"
                       r"COPY|BULK|OPENROWSET|SP_\w+)\b", re.I)


def load_config(path):
    p = Path(path)
    if not p.exists():
        sys.exit(f"Missing {p}. Copy fabric.endpoints.example.json to {p.name} and fill it in.")
    return json.loads(p.read_text())


def strip_sql_comments(q):
    q = re.sub(r"/\*.*?\*/", " ", q, flags=re.S)
    return re.sub(r"--[^\n]*", " ", q)


def run_sql(cfg, query, max_rows):
    body = strip_sql_comments(query).strip()
    if not re.match(r"^(SELECT|WITH)\b", body, re.I) or WRITE_SQL.search(body):
        sys.exit("Refused: fabric_query.py only runs read-only SELECT/WITH queries.")
    import pyodbc
    from azure.identity import AzureCliCredential

    token = AzureCliCredential().get_token("https://database.windows.net/.default").token
    raw = token.encode("utf-16-le")
    attrs = {1256: struct.pack(f"<I{len(raw)}s", len(raw), raw)}  # 1256 = SQL_COPT_SS_ACCESS_TOKEN
    conn_str = (f"Driver={{{cfg.get('odbc_driver', 'ODBC Driver 18 for SQL Server')}}};"
                f"Server={cfg['sql_server']},1433;Database={cfg['sql_database']};"
                "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30")
    with pyodbc.connect(conn_str, attrs_before=attrs) as conn:
        cur = conn.cursor()
        cur.execute(query)
        cols = [d[0] for d in cur.description]
        rows = [list(r) for r in cur.fetchmany(max_rows)]
    return cols, rows


def run_kql(cfg, query, max_rows):
    if query.lstrip().startswith("."):
        sys.exit("Refused: management commands (starting with '.') are not allowed. Run them in a KQL queryset.")
    from azure.kusto.data import KustoClient, KustoConnectionStringBuilder

    kcsb = KustoConnectionStringBuilder.with_az_cli_authentication(cfg["kql_query_uri"])
    resp = KustoClient(kcsb).execute(cfg["kql_database"], query)
    data = [r.to_dict() for r in resp.primary_results[0]]
    cols = list(data[0].keys()) if data else []
    return cols, [[row[c] for c in cols] for row in data[:max_rows]]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("engine", choices=["sql", "kql"])
    ap.add_argument("query", nargs="?", help="query text (or use --file)")
    ap.add_argument("--file")
    ap.add_argument("--config", default="fabric.endpoints.json")
    ap.add_argument("--format", choices=["json", "table", "csv"], default="json")
    ap.add_argument("--max-rows", type=int, default=200)
    a = ap.parse_args()
    query = Path(a.file).read_text() if a.file else a.query
    if not query:
        sys.exit("Provide a query or --file.")
    cfg = load_config(a.config)
    cols, rows = (run_sql if a.engine == "sql" else run_kql)(cfg, query, a.max_rows)

    if a.format == "json":
        print(json.dumps({"engine": a.engine, "columns": cols, "rows": rows, "row_count": len(rows),
                          "truncated_at": a.max_rows}, default=str, indent=1))
    elif a.format == "csv":
        w = csv.writer(sys.stdout)
        w.writerow(cols)
        w.writerows(rows)
    else:
        widths = [max(len(str(c)), *(len(str(r[i])) for r in rows)) if rows else len(str(c)) for i, c in enumerate(cols)]
        print(" | ".join(str(c).ljust(w) for c, w in zip(cols, widths)))
        print("-+-".join("-" * w for w in widths))
        for r in rows:
            print(" | ".join(str(v).ljust(w) for v, w in zip(r, widths)))


if __name__ == "__main__":
    main()

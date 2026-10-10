#!/usr/bin/env python3
"""
Replay synthetic reefer telemetry into a Fabric Eventstream custom endpoint (lab L6), re-timed to "now".

It reads data/generated/reefer_telemetry.csv, picks one day (default 2026-09-12, a TRK-117 fault day),
shifts timestamps so the first reading is now, and sends readings in time order. --speed 60 makes 15 minutes
of telemetry arrive every 15 seconds.

Eventstream: add a "Custom endpoint" source, open it, and copy the Event Hub-compatible connection string
(it normally contains EntityPath). Verify the exact UI labels on Learn; they change.
Put it in .env as EVENTSTREAM_CONNECTION_STRING=...  (never commit .env)

Usage:
  python tools/reefer_simulator.py --dry-run --limit 5
  python tools/reefer_simulator.py --day 2026-09-12 --speed 60
  python tools/reefer_simulator.py --truck TRK-117 --speed 120
"""
import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from itertools import groupby
from pathlib import Path


def load_env(path=".env"):
    p = Path(path)
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def parse_ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default="data/generated/reefer_telemetry.csv")
    ap.add_argument("--day", default="2026-09-12", help="UTC day to replay (YYYY-MM-DD)")
    ap.add_argument("--truck", help="only this truck, e.g. TRK-117")
    ap.add_argument("--speed", type=float, default=60.0, help="time compression factor")
    ap.add_argument("--limit", type=int, default=0, help="stop after N events (0 = all)")
    ap.add_argument("--dry-run", action="store_true", help="print events instead of sending")
    a = ap.parse_args()

    with open(a.csv, newline="") as f:
        rows = [r for r in csv.DictReader(f)
                if r["ts"].startswith(a.day) and (not a.truck or r["truck_id"] == a.truck)]
    if not rows:
        sys.exit(f"No telemetry rows for day={a.day} truck={a.truck}. Generate data first or change the filters.")
    rows.sort(key=lambda r: r["ts"])
    t0_orig, t0_now = parse_ts(rows[0]["ts"]), datetime.now(timezone.utc)

    producer = None
    if not a.dry_run:
        load_env()
        conn = os.environ.get("EVENTSTREAM_CONNECTION_STRING")
        if not conn:
            sys.exit("Set EVENTSTREAM_CONNECTION_STRING in .env (see docstring) or use --dry-run.")
        from azure.eventhub import EventData, EventHubProducerClient  # pip install azure-eventhub
        hub = os.environ.get("EVENTSTREAM_EVENTHUB_NAME")  # only needed if the string has no EntityPath
        producer = (EventHubProducerClient.from_connection_string(conn, eventhub_name=hub) if hub
                    else EventHubProducerClient.from_connection_string(conn))

    sent, prev_orig = 0, None
    try:
        for ts_str, group in groupby(rows, key=lambda r: r["ts"]):
            orig = parse_ts(ts_str)
            if prev_orig is not None:
                time.sleep(max(0.0, (orig - prev_orig).total_seconds() / a.speed))
            prev_orig = orig
            new_ts = (t0_now + (orig - t0_orig) / a.speed).strftime("%Y-%m-%dT%H:%M:%SZ")
            events = []
            for r in group:
                events.append(dict(ts=new_ts, truck_id=r["truck_id"], shipment_id=r["shipment_id"],
                                   facility_id=r["facility_id"], temp_c=float(r["temp_c"]),
                                   setpoint_c=float(r["setpoint_c"]), door_open=r["door_open"].lower() == "true",
                                   reefer_status=r["reefer_status"]))
            if a.limit:
                events = events[: max(0, a.limit - sent)]
            if not events:
                break
            if producer is None:
                for e in events:
                    print(json.dumps(e))
            else:
                batch = producer.create_batch()
                for e in events:
                    try:
                        batch.add(EventData(json.dumps(e)))
                    except ValueError:  # batch full: flush and start a new one
                        producer.send_batch(batch)
                        batch = producer.create_batch()
                        batch.add(EventData(json.dumps(e)))
                producer.send_batch(batch)
            sent += len(events)
            if a.limit and sent >= a.limit:
                break
    finally:
        if producer is not None:
            producer.close()
    print(f"{'Printed' if a.dry_run else 'Sent'} {sent} events (day={a.day}, truck={a.truck or 'all'}, speed={a.speed}x)",
          file=sys.stderr)


if __name__ == "__main__":
    main()

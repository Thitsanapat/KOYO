#!/usr/bin/env python3
"""Execute every Flux target in the provisioned KOYO Grafana dashboard."""

import csv
import io
import json
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DASHBOARD = ROOT / "grafana-dashboards" / "koyo_telemetry.json"
QUERY_URL = "http://localhost:8086/api/v2/query?org=koyo"
TOKEN = "koyo-local-dev-token"


def panels(items):
    for panel in items:
        yield panel
        yield from panels(panel.get("panels", []))


def runnable_flux(query):
    return (
        query.replace("v.timeRangeStart", "2026-07-07T00:00:00Z")
        .replace("v.timeRangeStop", "now()")
        .replace("v.windowPeriod", "1h")
    )


def query_rows(flux):
    request = urllib.request.Request(
        QUERY_URL,
        data=runnable_flux(flux).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "application/vnd.flux",
            "Accept": "text/csv",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        text = response.read().decode("utf-8")
    return [row for row in csv.reader(io.StringIO(text)) if row and not row[0].startswith("#")]


def main():
    dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    checks = []
    for panel in panels(dashboard.get("panels", [])):
        for target in panel.get("targets", []):
            flux = target.get("query")
            if flux:
                checks.append((panel.get("title", "untitled"), target.get("refId", "?"), flux))

    passed = 0
    for title, ref_id, flux in checks:
        try:
            rows = query_rows(flux)
            if len(rows) <= 1:
                raise RuntimeError("query returned no data rows")
            passed += 1
            print(f"PASS  {title} [{ref_id}] ({len(rows) - 1} rows)")
        except (OSError, RuntimeError, urllib.error.HTTPError) as error:
            print(f"FAIL  {title} [{ref_id}]: {error}")

    print(f"\nDashboard queries: {passed}/{len(checks)} passed")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())


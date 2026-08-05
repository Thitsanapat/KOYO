"""Loads data/koyo/decoded/decoded.csv into the local InfluxDB instance.

Run after every decode_koyo.py refresh to keep the Grafana dashboard current.
Requires the local stack to be running (see start.ps1).
"""
import csv
import urllib.request
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "koyo" / "decoded" / "decoded.csv"
INFLUX_URL = "http://localhost:8086/api/v2/write?org=koyo&bucket=koyo_telemetry&precision=s"
TOKEN = "koyo-local-dev-token"

NUMERIC_FIELDS = [
    "packet_counter", "uptime_ms", "obc_time_unix",
    "comm_voltage_candidate", "sp_voltage_candidate_1", "sp_voltage_candidate_2",
    "battery_th0_temp_c", "battery_th1_temp_c", "cdh_temp_c", "adcs_temp_c",
    "boot_counter", "pib_health_status", "sd_card_failure_count",
]


def esc_tag(v):
    return str(v).replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")


def build_lines(rows):
    lines = []
    for row in rows:
        ts = row.get("rtc_time_unix")
        if not ts or not ts.strip():
            continue
        try:
            ts_i = int(float(ts))
        except ValueError:
            continue

        fields = []
        for f in NUMERIC_FIELDS:
            v = row.get(f, "")
            if v is None or v.strip() == "":
                continue
            try:
                fv = float(v)
            except ValueError:
                continue
            fields.append(f"{f}={fv}")
        if not fields:
            continue

        obs_tag = esc_tag(row.get("obs_id", "unknown"))
        line = f"koyo,obs_id={obs_tag} " + ",".join(fields) + f" {ts_i}"
        lines.append(line)
    return lines


def write_batch(lines):
    body = "\n".join(lines).encode("utf-8")
    req = urllib.request.Request(
        INFLUX_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "text/plain; charset=utf-8",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status


def main():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    lines = build_lines(rows)
    print(f"Built {len(lines)} line-protocol points from {len(rows)} CSV rows")

    batch_size = 2000
    for i in range(0, len(lines), batch_size):
        batch = lines[i:i + batch_size]
        status = write_batch(batch)
        print(f"  wrote rows {i}-{i+len(batch)}: HTTP {status}")

    print("done")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Export a reviewable channel/value CSV from decoded KOYO telemetry.

This is a local draft contract, not an uploader. The final column order and
destination can be adapted once the HEX ingestion schema is provided.
"""

import csv
from datetime import datetime, timezone
from pathlib import Path

from load_influx import BEACON_CHANNELS, beacon_values


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "koyo" / "decoded" / "decoded.csv"
OUTPUT = ROOT / "data" / "koyo" / "decoded" / "koyo_hex_feedback.csv"


def main():
    count = 0
    with INPUT.open(newline="", encoding="utf-8") as src, OUTPUT.open(
        "w", newline="", encoding="utf-8"
    ) as dst:
        writer = csv.DictWriter(
            dst,
            fieldnames=["measurement", "time", "channel", "value", "unit", "quality", "source", "obs_id"],
        )
        writer.writeheader()
        for row in csv.DictReader(src):
            raw_ts = row.get("rtc_time_unix", "")
            if not raw_ts.strip():
                continue
            try:
                timestamp = int(float(raw_ts))
            except ValueError:
                continue
            utc_time = datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec="seconds")
            for spec, value in beacon_values(row):
                writer.writerow(
                    {
                        "measurement": "beacon",
                        "time": utc_time,
                        "channel": spec["channel"],
                        "value": value,
                        "unit": spec["unit"],
                        "quality": spec["quality"],
                        "source": "satnogs",
                        "obs_id": row.get("obs_id", "unknown"),
                    }
                )
                count += 1

    confirmed = sum(1 for item in BEACON_CHANNELS.values() if item["quality"] == "confirmed")
    candidates = len(BEACON_CHANNELS) - confirmed
    print(f"wrote {count} values to {OUTPUT}")
    print(f"contract: {confirmed} confirmed channels, {candidates} candidate channels")


if __name__ == "__main__":
    main()

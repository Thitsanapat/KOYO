#!/usr/bin/env python3
"""Summarize the complete decoded KOYO history separately from audio tests."""

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DECODED = ROOT / "data" / "koyo" / "decoded" / "decoded.csv"
INDEX = ROOT / "data" / "koyo" / "index.csv"
REPORT_DIR = ROOT / "reports"
LAUNCH_TS = int(datetime(2026, 7, 7, tzinfo=timezone.utc).timestamp())


def main():
    with INDEX.open(newline="", encoding="utf-8") as handle:
        index_rows = list(csv.DictReader(handle))
    stations = {row["obs_id"]: row.get("station", "") for row in index_rows}

    daily = defaultdict(lambda: {"frames": 0, "observations": set(), "stations": set(), "times": []})
    with DECODED.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                timestamp = int(float(row["rtc_time_unix"]))
            except (KeyError, TypeError, ValueError):
                continue
            if timestamp < LAUNCH_TS:
                continue
            day = datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()
            bucket = daily[day]
            bucket["frames"] += 1
            bucket["observations"].add(row["obs_id"])
            if stations.get(row["obs_id"]):
                bucket["stations"].add(stations[row["obs_id"]])
            bucket["times"].append(timestamp)

    rows = []
    for day in sorted(daily):
        bucket = daily[day]
        rows.append(
            {
                "date_utc": day,
                "decoded_frames": bucket["frames"],
                "observations": len(bucket["observations"]),
                "receiving_stations": len(bucket["stations"]),
                "first_frame_utc": datetime.fromtimestamp(min(bucket["times"]), timezone.utc).isoformat(),
                "last_frame_utc": datetime.fromtimestamp(max(bucket["times"]), timezone.utc).isoformat(),
            }
        )

    REPORT_DIR.mkdir(exist_ok=True)
    csv_path = REPORT_DIR / "koyo_historical_coverage.csv"
    fields = list(rows[0])
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    total_frames = sum(row["decoded_frames"] for row in rows)
    all_observations = set()
    all_stations = set()
    with DECODED.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                timestamp = int(float(row["rtc_time_unix"]))
            except (KeyError, TypeError, ValueError):
                continue
            if timestamp >= LAUNCH_TS:
                all_observations.add(row["obs_id"])
                if stations.get(row["obs_id"]):
                    all_stations.add(stations[row["obs_id"]])

    markdown = [
        "# KOYO Historical Coverage",
        "",
        "This report summarizes all locally decoded SatNOGS frames. It is separate from",
        "the smaller OGG-to-GNU-Radio byte-exact validation sample.",
        "",
        "## Summary",
        "",
        f"- UTC date range: {rows[0]['date_utc']} through {rows[-1]['date_utc']}",
        f"- Days with decoded frames: {len(rows)}",
        f"- Decoded frames: {total_frames}",
        f"- Distinct observations: {len(all_observations)}",
        f"- Receiving stations represented: {len(all_stations)}",
        "",
        "## Daily Coverage",
        "",
        "| UTC date | Frames | Observations | Stations |",
        "|---|---:|---:|---:|",
    ]
    for row in rows:
        markdown.append(
            f"| {row['date_utc']} | {row['decoded_frames']} | "
            f"{row['observations']} | {row['receiving_stations']} |"
        )
    markdown.append("")
    md_path = REPORT_DIR / "KOYO_HISTORICAL_COVERAGE.md"
    md_path.write_text("\n".join(markdown), encoding="utf-8")

    summary_path = REPORT_DIR / "koyo_historical_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "date_start_utc": rows[0]["date_utc"],
                "date_end_utc": rows[-1]["date_utc"],
                "days_with_frames": len(rows),
                "decoded_frames": total_frames,
                "distinct_observations": len(all_observations),
                "receiving_stations": len(all_stations),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"{len(rows)} days, {total_frames} frames, {len(all_observations)} observations, "
        f"{len(all_stations)} stations"
    )
    print(csv_path)
    print(md_path)
    print(summary_path)


if __name__ == "__main__":
    main()

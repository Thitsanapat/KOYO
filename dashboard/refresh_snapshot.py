#!/usr/bin/env python3
"""Refresh the standalone KOYO dashboard snapshot from decoded.csv.

The HTML page deliberately embeds its data so it opens without a server. This
script keeps that presentation fallback aligned with the same SatNOGS-derived
CSV used by the local Grafana dashboard.
"""

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "koyo" / "decoded" / "decoded.csv"
HTML_PATH = ROOT / "dashboard" / "koyo_dashboard.html"
LAUNCH_TS = int(datetime(2026, 7, 7, tzinfo=timezone.utc).timestamp())


def number(row: dict[str, str], key: str) -> float:
    return float(row[key])


def timestamp(row: dict[str, str]) -> int:
    return int(number(row, "rtc_time_unix"))


def utc_iso(row: dict[str, str]) -> str:
    return datetime.fromtimestamp(timestamp(row), timezone.utc).isoformat(timespec="seconds")


def replace_assignment(html: str, name: str, value: object) -> str:
    replacement = f"const {name} = {json.dumps(value, separators=(',', ':'))};\n"
    pattern = rf"const {name} = .*?;\r?\n"
    updated, count = re.subn(pattern, replacement, html, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"Could not replace {name} in {HTML_PATH}")
    return updated


def frame_row(row: dict[str, str]) -> dict[str, object]:
    return {
        "obs_id": row["obs_id"],
        "packet_counter": int(number(row, "packet_counter")),
        "uptime_ms": int(number(row, "uptime_ms")),
        "boot_counter": int(number(row, "boot_counter")),
        "rtc_datetime": utc_iso(row),
        "health": int(number(row, "pib_health_status")),
        "sd_fail": int(number(row, "sd_card_failure_count")),
    }


def main() -> None:
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        all_rows = list(csv.DictReader(handle))

    valid_rows = [row for row in all_rows if timestamp(row) >= 1_600_000_000]
    post_launch = [row for row in valid_rows if timestamp(row) >= LAUNCH_TS]
    post_launch.sort(key=timestamp)
    if not post_launch:
        raise RuntimeError("No post-launch frames found")

    first_seen_boots: set[int] = set()
    reboots = []
    last_sd_fail = None
    health_changes = []
    for row in post_launch:
        boot = int(number(row, "boot_counter"))
        if boot not in first_seen_boots:
            first_seen_boots.add(boot)
            reboots.append({"t": utc_iso(row), "boot": boot, "obs_id": row["obs_id"]})

        sd_fail = int(number(row, "sd_card_failure_count"))
        if sd_fail != last_sd_fail:
            health_changes.append({"t": utc_iso(row), "sd_fail": sd_fail, "obs_id": row["obs_id"]})
            last_sd_fail = sd_fail

    per_day = Counter(utc_iso(row)[:10] for row in post_launch)
    latest = post_launch[-1]
    latest_ts = timestamp(latest)
    window_start = latest_ts - 7 * 24 * 60 * 60
    window = [row for row in post_launch if timestamp(row) >= window_start]

    data = {
        "total_frames": len(all_rows),
        "valid_frames": len(valid_rows),
        "post_launch_frames": len(post_launch),
        "distinct_obs": len({row["obs_id"] for row in post_launch}),
        "date_start": utc_iso(post_launch[0]),
        "date_end": utc_iso(latest),
        "reboots": reboots,
        "per_day": [{"date": day, "count": per_day[day]} for day in sorted(per_day)],
        "table_rows": [frame_row(row) for row in reversed(post_launch[-200:])],
        "health_changes": health_changes,
    }
    eps = {
        "sp_voltage_1": number(latest, "sp_voltage_candidate_1") / 1000,
        "sp_voltage_2": number(latest, "sp_voltage_candidate_2") / 1000,
        "as_of": utc_iso(latest),
    }
    eps_temps = {
        "battery_th0_c": number(latest, "battery_th0_temp_c"),
        "battery_th1_c": number(latest, "battery_th1_temp_c"),
        "cdh_c": number(latest, "cdh_temp_c"),
        "adcs_c": number(latest, "adcs_temp_c"),
        "as_of": utc_iso(latest),
    }
    eps_series = [
        {
            "t": timestamp(row),
            "sp1": number(row, "sp_voltage_candidate_1") / 1000,
            "sp2": number(row, "sp_voltage_candidate_2") / 1000,
            "comm": number(row, "comm_voltage_candidate") / 100,
        }
        for row in window
    ]
    confirmed_series = [
        {
            "t": timestamp(row),
            "uptime_ms": int(number(row, "uptime_ms")),
            "packet_counter": int(number(row, "packet_counter")),
            "boot": int(number(row, "boot_counter")),
        }
        for row in window
    ]

    html = HTML_PATH.read_text(encoding="utf-8")
    for name, value in (
        ("DATA", data),
        ("EPS", eps),
        ("EPS_TEMPS", eps_temps),
        ("EPS_SERIES", eps_series),
        ("CONFIRMED_SERIES", confirmed_series),
    ):
        html = replace_assignment(html, name, value)
    HTML_PATH.write_text(html, encoding="utf-8", newline="\n")

    print(
        f"refreshed {HTML_PATH.name}: {len(post_launch)} post-launch frames, "
        f"{data['distinct_obs']} observations, through {data['date_end']}"
    )


if __name__ == "__main__":
    main()

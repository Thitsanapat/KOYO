#!/usr/bin/env python3
"""Decode KOYO beacon frames from hex files and export telemetry for local dashboards."""

import argparse
import csv
import json
import os
import re
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


FRAME_SIZE = 263


def decode_frame(frame: bytes) -> Dict[str, Any]:
    if len(frame) != FRAME_SIZE:
        raise ValueError(f"expected {FRAME_SIZE} bytes, got {len(frame)}")

    dest_callsign = "".join(chr(b >> 1) for b in frame[0:6]).strip()
    src_callsign = "".join(chr(b >> 1) for b in frame[7:13]).strip()

    packet_counter = struct.unpack_from(">H", frame, 18)[0]
    uptime_ms = struct.unpack_from("<I", frame, 24)[0]
    obc_time_unix = struct.unpack_from("<I", frame, 28)[0]
    # UNCONFIRMED candidates - see koyo.ksy for evidence
    comm_voltage_candidate = struct.unpack_from("<H", frame, 50)[0]
    sp_voltage_candidate_1 = struct.unpack_from("<H", frame, 62)[0]
    sp_voltage_candidate_2 = struct.unpack_from("<H", frame, 66)[0]
    # CONFIRMED - see koyo.ksy battery_th0_raw/battery_th1_raw/cdh_temp_raw/adcs_temp_raw
    battery_th0_raw, battery_th1_raw, cdh_temp_raw, adcs_temp_raw = struct.unpack_from("<4H", frame, 80)
    battery_th0_temp_c = battery_th0_raw * -0.001775 + 42.3638
    battery_th1_temp_c = battery_th1_raw * -0.001777 + 42.4137
    cdh_temp_c = cdh_temp_raw * -0.019402 + 45.7133
    adcs_temp_c = adcs_temp_raw * -0.021693 + 49.4657
    thr_safe_to_phoenix, thr_7500, thr_phoenix_to_safe, thr_safe_to_nominal = struct.unpack_from("<4H", frame, 120)
    boot_counter = struct.unpack_from("<I", frame, 130)[0]
    rtc_time_unix = struct.unpack_from("<I", frame, 239)[0]
    rtc_100th, rtc_seconds, rtc_minutes, rtc_hours, rtc_day, rtc_date, rtc_month = struct.unpack_from("<7B", frame, 249)
    rtc_year = struct.unpack_from("<H", frame, 256)[0]
    # 2026-08-05: swapped vs. earlier assignment. offset 259's old reading (175)
    # violated the documented SD Card Failure Count max (100) but fits PIB
    # HealthStatus's documented max (175) exactly. See CLAUDE.md oddity notes.
    sd_card_failure_count = frame[258]
    pib_health_status = frame[259]

    rtc_datetime: Optional[datetime] = None
    if rtc_year and 2000 <= rtc_year <= 2100 and rtc_month and rtc_date:
        try:
            rtc_datetime = datetime(
                rtc_year,
                rtc_month,
                rtc_date,
                rtc_hours,
                rtc_minutes,
                rtc_seconds,
                rtc_100th * 10000,
                tzinfo=timezone.utc,
            )
        except ValueError:
            rtc_datetime = None

    return {
        "dest_callsign": dest_callsign,
        "src_callsign": src_callsign,
        "packet_counter": packet_counter,
        "uptime_ms": uptime_ms,
        "obc_time_unix": obc_time_unix,
        "comm_voltage_candidate": comm_voltage_candidate,
        "sp_voltage_candidate_1": sp_voltage_candidate_1,
        "sp_voltage_candidate_2": sp_voltage_candidate_2,
        "battery_th0_temp_c": round(battery_th0_temp_c, 3),
        "battery_th1_temp_c": round(battery_th1_temp_c, 3),
        "cdh_temp_c": round(cdh_temp_c, 3),
        "adcs_temp_c": round(adcs_temp_c, 3),
        "thr_safe_to_phoenix": thr_safe_to_phoenix,
        "thr_7500": thr_7500,
        "thr_phoenix_to_safe": thr_phoenix_to_safe,
        "thr_safe_to_nominal": thr_safe_to_nominal,
        "boot_counter": boot_counter,
        "rtc_time_unix": rtc_time_unix,
        "rtc_100th": rtc_100th,
        "rtc_seconds": rtc_seconds,
        "rtc_minutes": rtc_minutes,
        "rtc_hours": rtc_hours,
        "rtc_day": rtc_day,
        "rtc_date": rtc_date,
        "rtc_month": rtc_month,
        "rtc_year": rtc_year,
        "pib_health_status": pib_health_status,
        "sd_card_failure_count": sd_card_failure_count,
        "rtc_datetime": rtc_datetime,
        "eps_block_hex": frame[32:120].hex(),
    }


def parse_hex_file(
    path: Path,
    obs_id: Optional[str] = None,
    rejects: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle, 1):
            token = line.strip()
            if not token:
                continue
            token = re.sub(r"\s+", "", token)
            if len(token) % 2 != 0:
                if rejects is not None:
                    rejects.append({
                        "obs_id": obs_id or path.stem,
                        "frame_index": idx,
                        "source_file": path.name,
                        "frame_size": "",
                        "reason": "odd-length hex input",
                        "hex_prefix": token[:80],
                    })
                    continue
                raise ValueError(f"odd-length hex input in {path} line {idx}")
            try:
                frame_bytes = bytes.fromhex(token)
                record = decode_frame(frame_bytes)
            except ValueError as exc:
                if rejects is not None:
                    rejects.append({
                        "obs_id": obs_id or path.stem,
                        "frame_index": idx,
                        "source_file": path.name,
                        "frame_size": len(token) // 2,
                        "reason": str(exc),
                        "hex_prefix": token[:80],
                    })
                    continue
                raise
            record["obs_id"] = obs_id or path.stem
            record["frame_index"] = idx
            record["source_file"] = path.name
            records.append(record)
    return records


def iter_input_files(input_dir: Path) -> Iterable[Path]:
    if not input_dir.exists():
        return []
    return sorted(input_dir.glob("*.txt")) + sorted(input_dir.glob("*.hex"))


def export_records(records: List[Dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "decoded.csv"
    json_path = output_dir / "decoded.json"

    fieldnames = [
        "obs_id",
        "frame_index",
        "source_file",
        "packet_counter",
        "uptime_ms",
        "obc_time_unix",
        "comm_voltage_candidate",
        "sp_voltage_candidate_1",
        "sp_voltage_candidate_2",
        "battery_th0_temp_c",
        "battery_th1_temp_c",
        "cdh_temp_c",
        "adcs_temp_c",
        "boot_counter",
        "rtc_time_unix",
        "rtc_datetime",
        "rtc_year",
        "rtc_month",
        "rtc_date",
        "rtc_hours",
        "rtc_minutes",
        "rtc_seconds",
        "pib_health_status",
        "sd_card_failure_count",
        "src_callsign",
        "dest_callsign",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = {k: record.get(k) for k in fieldnames}
            row["rtc_datetime"] = record["rtc_datetime"].isoformat() if record.get("rtc_datetime") else ""
            writer.writerow(row)

    serializable = []
    for record in records:
        row = dict(record)
        row["rtc_datetime"] = row["rtc_datetime"].isoformat() if row.get("rtc_datetime") else None
        serializable.append(row)

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(serializable, handle, indent=2)


def export_rejects(rejects: List[Dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "rejects.csv"
    fieldnames = ["obs_id", "frame_index", "source_file", "frame_size", "reason", "hex_prefix"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rejects)


def push_to_influx(records: List[Dict[str, Any]], influx_url: str, org: str, bucket: str, token: str) -> None:
    import requests

    if not records:
        return

    lines: List[str] = []
    for record in records:
        tags = [f"obs_id={record['obs_id']}", f"src={escape_tag_value(record['src_callsign'])}"]
        fields = [
            f"packet_counter={record['packet_counter']}",
            f"uptime_ms={record['uptime_ms']}",
            f"boot_counter={record['boot_counter']}",
            f"rtc_time_unix={record['rtc_time_unix']}",
            f"pib_health_status={record['pib_health_status']}",
            f"sd_card_failure_count={record['sd_card_failure_count']}",
        ]
        lines.append("koyo_telemetry," + ",".join(tags) + " " + ",".join(fields))

    payload = "\n".join(lines) + "\n"
    response = requests.post(
        f"{influx_url.rstrip('/')}/api/v2/write?org={org}&bucket={bucket}",
        headers={"Authorization": f"Token {token}", "Content-Type": "text/plain; charset=utf-8"},
        data=payload,
        timeout=30,
    )
    response.raise_for_status()


def escape_tag_value(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._/-]", "_", value or "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Decode KOYO frame hex files and export telemetry")
    parser.add_argument("--input-dir", default="data/koyo/frames_hex", help="directory containing frame hex text files")
    parser.add_argument("--output-dir", default="data/koyo", help="directory for decoded.csv and decoded.json")
    parser.add_argument("--influx-url", default="", help="optional InfluxDB 2.x write URL")
    parser.add_argument("--org", default="primary")
    parser.add_argument("--bucket", default="KOYO")
    parser.add_argument("--token", default="")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    files = list(iter_input_files(input_dir))
    if not files:
        print(f"No frame files found in {input_dir}. Run fetch_satnogs.py first or provide --input-dir with hex text files.")
        return 0

    records: List[Dict[str, Any]] = []
    rejects: List[Dict[str, Any]] = []
    for path in files:
        obs_id = path.stem
        records.extend(parse_hex_file(path, obs_id=obs_id, rejects=rejects))

    export_records(records, output_dir)
    export_rejects(rejects, output_dir)
    print(f"Decoded {len(records)} frames into {output_dir / 'decoded.csv'} and {output_dir / 'decoded.json'}")
    if rejects:
        print(f"Skipped {len(rejects)} unsupported frames into {output_dir / 'rejects.csv'}")

    if args.influx_url and args.token:
        push_to_influx(records, args.influx_url, args.org, args.bucket, args.token)
        print("Pushed telemetry to InfluxDB")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

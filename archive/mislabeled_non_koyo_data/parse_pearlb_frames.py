#!/usr/bin/env python3
"""Parse first-level PEARL-B/KOYO AX.25 frames from SatNOGS demoddata."""

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Optional


def decode_ax25_callsign(raw: bytes) -> str:
    chars = []
    for byte in raw[:6]:
        value = byte >> 1
        if value < 32 or value > 126:
            return ""
        chars.append(chr(value))
    callsign = "".join(chars).strip()
    ssid = (raw[6] >> 1) & 0x0F
    return f"{callsign}-{ssid}" if ssid else callsign


def parse_ax25(frame: bytes) -> Optional[dict[str, Any]]:
    if len(frame) < 16:
        return None
    dest = decode_ax25_callsign(frame[0:7])
    src = decode_ax25_callsign(frame[7:14])
    if not dest or not src:
        return None
    return {
        "dest": dest,
        "src": src,
        "control": frame[14],
        "pid": frame[15],
        "info": frame[16:],
    }


def clean_ascii(data: bytes) -> str:
    text = "".join(chr(byte) if 32 <= byte <= 126 else " " for byte in data)
    return re.sub(r"\s+", " ", text).strip()


def packet_type_name(packet_type: int) -> str:
    return {
        0x33: "telemetry_block",
        0x80: "text_beacon",
        0x81: "zero_block",
        0x82: "status_block",
        0x83: "status_block",
    }.get(packet_type, "unknown")


def parse_pearlb_frame(path: Path, obs_id: str) -> Optional[dict[str, Any]]:
    frame = path.read_bytes()
    ax25 = parse_ax25(frame)
    if not ax25:
        return None
    if ax25["src"] != "PEARLB" or ax25["dest"] != "NCUGS1":
        return None

    info = ax25["info"]
    if len(info) < 4:
        return None

    frame_counter = info[0]
    protocol = info[1:3].hex()
    packet_type = info[3]
    payload = info[4:]

    row: dict[str, Any] = {
        "obs_id": obs_id,
        "file": path.name,
        "frame_size": len(frame),
        "info_size": len(info),
        "payload_size": len(payload),
        "ax25_src": ax25["src"],
        "ax25_dest": ax25["dest"],
        "ax25_control": f"0x{ax25['control']:02x}",
        "ax25_pid": f"0x{ax25['pid']:02x}",
        "frame_counter": frame_counter,
        "protocol": protocol,
        "packet_type": f"0x{packet_type:02x}",
        "packet_type_name": packet_type_name(packet_type),
        "payload_hex": payload.hex(),
        "payload_ascii": clean_ascii(payload),
    }

    if packet_type == 0x33 and len(payload) >= 4:
        row["tlm_counter"] = payload[0]
        row["block_id"] = payload[1]
        row["subtype"] = payload[2]
        row["message_id"] = payload[3]
    else:
        row["tlm_counter"] = ""
        row["block_id"] = ""
        row["subtype"] = ""
        row["message_id"] = ""

    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames-dir", default=Path("data/koyo/frames"), type=Path)
    parser.add_argument("--output-dir", default=Path("data/koyo/pearlb"), type=Path)
    args = parser.parse_args()

    rows = []
    for path in sorted(args.frames_dir.glob("*.bin")):
        obs_id = path.stem.split("_")[0]
        row = parse_pearlb_frame(path, obs_id)
        if row:
            rows.append(row)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "pearlb_packets.csv"
    json_path = args.output_dir / "pearlb_packets.json"
    summary_path = args.output_dir / "pearlb_summary.csv"
    wide_path = args.output_dir / "pearlb_payload_wide.csv"

    fieldnames = [
        "obs_id",
        "file",
        "frame_size",
        "info_size",
        "payload_size",
        "ax25_src",
        "ax25_dest",
        "ax25_control",
        "ax25_pid",
        "frame_counter",
        "protocol",
        "packet_type",
        "packet_type_name",
        "tlm_counter",
        "block_id",
        "subtype",
        "message_id",
        "payload_ascii",
        "payload_hex",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    summary_rows = []
    for key, count in Counter(
        (row["packet_type"], row["packet_type_name"], row["frame_size"], row["payload_size"])
        for row in rows
    ).most_common():
        packet_type, name, frame_size, payload_size = key
        summary_rows.append({
            "packet_type": packet_type,
            "packet_type_name": name,
            "frame_size": frame_size,
            "payload_size": payload_size,
            "count": count,
        })
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["packet_type", "packet_type_name", "frame_size", "payload_size", "count"])
        writer.writeheader()
        writer.writerows(summary_rows)

    max_payload = max((int(row["payload_size"]) for row in rows), default=0)
    wide_fieldnames = [
        "obs_id",
        "file",
        "frame_counter",
        "packet_type",
        "packet_type_name",
        "tlm_counter",
        "block_id",
        "subtype",
        "message_id",
    ] + [f"p{i:02d}" for i in range(max_payload)]
    with wide_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=wide_fieldnames)
        writer.writeheader()
        for row in rows:
            payload = bytes.fromhex(row["payload_hex"])
            wide = {field: row.get(field, "") for field in wide_fieldnames}
            for idx, byte in enumerate(payload):
                wide[f"p{idx:02d}"] = byte
            writer.writerow(wide)

    print(f"parsed PEARLB packets: {len(rows)}")
    print(f"wrote: {csv_path}")
    print(f"wrote: {summary_path}")
    print(f"wrote: {wide_path}")
    for row in summary_rows:
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

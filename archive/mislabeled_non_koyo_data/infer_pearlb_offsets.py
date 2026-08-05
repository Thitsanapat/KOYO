#!/usr/bin/env python3
"""Generate offset candidates for PEARL-B telemetry blocks."""

import argparse
import csv
import math
import struct
from collections import defaultdict
from pathlib import Path
from typing import Callable


def read_packets(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def finite_float(value: float) -> bool:
    return math.isfinite(value) and abs(value) < 1e9


def summarize_values(values: list[float | int]) -> tuple[str, str, str, str]:
    unique = sorted(set(values))
    if not values:
        return "", "", "", ""
    return (
        str(min(values)),
        str(max(values)),
        str(len(unique)),
        " ".join(str(v) for v in unique[:8]),
    )


def decode_series(payloads: list[bytes], offset: int, size: int, unpack: Callable[[bytes], float | int]) -> list[float | int]:
    values = []
    for payload in payloads:
        if offset + size <= len(payload):
            try:
                value = unpack(payload[offset:offset + size])
            except struct.error:
                continue
            if isinstance(value, float) and not finite_float(value):
                continue
            values.append(value)
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packets", default=Path("data/koyo/pearlb/pearlb_packets.csv"), type=Path)
    parser.add_argument("--output", default=Path("data/koyo/pearlb/offset_candidates.csv"), type=Path)
    args = parser.parse_args()

    rows = read_packets(args.packets)
    groups: dict[tuple[str, str, str], list[bytes]] = defaultdict(list)
    for row in rows:
        if row["packet_type"] != "0x33":
            continue
        key = (row["block_id"], row["subtype"], row["message_id"])
        groups[key].append(bytes.fromhex(row["payload_hex"]))

    decoders: list[tuple[str, int, Callable[[bytes], float | int]]] = [
        ("u8", 1, lambda b: b[0]),
        ("i8", 1, lambda b: struct.unpack("<b", b)[0]),
        ("u16le", 2, lambda b: struct.unpack("<H", b)[0]),
        ("i16le", 2, lambda b: struct.unpack("<h", b)[0]),
        ("u32le", 4, lambda b: struct.unpack("<I", b)[0]),
        ("i32le", 4, lambda b: struct.unpack("<i", b)[0]),
        ("f32le", 4, lambda b: round(struct.unpack("<f", b)[0], 6)),
    ]

    out_rows = []
    for (block_id, subtype, message_id), payloads in sorted(groups.items(), key=lambda item: (int(item[0][0]), int(item[0][1]), int(item[0][2]))):
        max_len = max(len(payload) for payload in payloads)
        for offset in range(4, max_len):
            for kind, size, decoder in decoders:
                values = decode_series(payloads, offset, size, decoder)
                if len(values) < max(2, min(3, len(payloads))):
                    continue
                min_value, max_value, unique_count, samples = summarize_values(values)
                if unique_count == "1" and kind in {"u8", "i8"}:
                    continue
                out_rows.append({
                    "block_id": block_id,
                    "subtype": subtype,
                    "message_id": message_id,
                    "packet_count": len(payloads),
                    "offset_in_payload": offset,
                    "decoder": kind,
                    "min": min_value,
                    "max": max_value,
                    "unique_count": unique_count,
                    "samples": samples,
                })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "block_id",
            "subtype",
            "message_id",
            "packet_count",
            "offset_in_payload",
            "decoder",
            "min",
            "max",
            "unique_count",
            "samples",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"groups: {len(groups)}")
    print(f"candidates: {len(out_rows)}")
    print(f"wrote: {args.output}")
    for row in out_rows[:40]:
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Classify downloaded SatNOGS frames by length, AX.25 header, and ASCII hints."""

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional


def decode_ax25_callsign(raw: bytes) -> str:
    if len(raw) != 7:
        return ""
    chars = []
    for byte in raw[:6]:
        value = byte >> 1
        if value < 32 or value > 126:
            return ""
        chars.append(chr(value))
    callsign = "".join(chars).strip()
    ssid = (raw[6] >> 1) & 0x0F
    if ssid:
        callsign = f"{callsign}-{ssid}"
    return callsign


def parse_ax25(frame: bytes) -> Optional[dict[str, str | int]]:
    if len(frame) < 16:
        return None
    dest = decode_ax25_callsign(frame[0:7])
    src = decode_ax25_callsign(frame[7:14])
    if not dest or not src:
        return None
    control = frame[14]
    pid = frame[15]
    return {
        "dest": dest,
        "src": src,
        "control": control,
        "pid": pid,
        "info_offset": 16,
    }


def ascii_hint(frame: bytes) -> str:
    text = "".join(chr(b) if 32 <= b <= 126 else "." for b in frame)
    runs = re.findall(r"[ -~]{4,}", text)
    return " | ".join(runs[:4])


def load_metadata(root: Path) -> dict[str, dict]:
    path = root / "observations_good.json"
    if not path.exists():
        return {}
    return {str(item["id"]): item for item in json.loads(path.read_text(encoding="utf-8"))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=Path("data/koyo"), type=Path)
    parser.add_argument("--frames-dir", default=None, type=Path)
    parser.add_argument("--output", default=None, type=Path)
    args = parser.parse_args()

    root = args.root
    frames_dir = args.frames_dir or root / "frames"
    output = args.output or root / "frame_analysis.csv"
    metadata = load_metadata(root)

    rows = []
    for path in sorted(frames_dir.glob("*.bin")):
        frame = path.read_bytes()
        obs_id = path.stem.split("_")[0]
        ax25 = parse_ax25(frame)
        info_offset = ax25["info_offset"] if ax25 else 0
        info = frame[int(info_offset):]
        obs = metadata.get(obs_id, {})
        rows.append({
            "file": path.name,
            "obs_id": obs_id,
            "frame_index": path.stem.split("_")[-1],
            "size": len(frame),
            "mode": obs.get("transmitter_mode", ""),
            "station": obs.get("station_name", ""),
            "start": obs.get("start", ""),
            "ax25_dest": ax25["dest"] if ax25 else "",
            "ax25_src": ax25["src"] if ax25 else "",
            "ax25_control": f"0x{ax25['control']:02x}" if ax25 else "",
            "ax25_pid": f"0x{ax25['pid']:02x}" if ax25 else "",
            "ascii_hint": ascii_hint(info),
            "hex_prefix": frame[:32].hex(),
        })

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)

    by_ax25 = Counter((row["ax25_dest"], row["ax25_src"]) for row in rows if row["ax25_dest"])
    by_mode = Counter(row["mode"] for row in rows)
    by_obs = defaultdict(int)
    for row in rows:
        by_obs[row["obs_id"]] += 1

    print(f"frames: {len(rows)}")
    print(f"wrote: {output}")
    print("top AX.25 address pairs:")
    for (dest, src), count in by_ax25.most_common(12):
        print(f"  {count:4d}  {src} -> {dest}")
    print("top modes:")
    for mode, count in by_mode.most_common(12):
        print(f"  {count:4d}  {mode}")
    print("top observations:")
    for obs_id, count in sorted(by_obs.items(), key=lambda item: item[1], reverse=True)[:12]:
        print(f"  {count:4d}  {obs_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Inspect KISS frames emitted by gr-satellites/Dire Wolf style decoders."""

import argparse
from pathlib import Path


FEND = 0xC0
FESC = 0xDB
TFEND = 0xDC
TFESC = 0xDD


def unescape(frame: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(frame):
        if frame[i] == FESC and i + 1 < len(frame):
            if frame[i + 1] == TFEND:
                out.append(FEND)
                i += 2
                continue
            if frame[i + 1] == TFESC:
                out.append(FESC)
                i += 2
                continue
        out.append(frame[i])
        i += 1
    return bytes(out)


def read_kiss(path: Path) -> list[bytes]:
    data = path.read_bytes()
    frames = []
    for part in data.split(bytes([FEND])):
        if not part:
            continue
        payload = unescape(part)
        if payload and payload[0] <= 0x0F:
            payload = payload[1:]
        if payload:
            frames.append(payload)
    return frames


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kiss", type=Path)
    args = parser.parse_args()

    frames = read_kiss(args.kiss)
    print(f"{args.kiss}: {len(frames)} frame(s)")
    for idx, frame in enumerate(frames, 1):
        print(f"{idx:03d} len={len(frame):4d} hex={frame.hex()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

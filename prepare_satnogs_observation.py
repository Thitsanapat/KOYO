#!/usr/bin/env python3
"""Prepare one SatNOGS observation for local demod/telemetry work."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def find_ffmpeg(explicit: str | None) -> str:
    if explicit:
        return explicit

    found = shutil.which("ffmpeg")
    if found:
        return found

    localappdata = Path.home() / "AppData" / "Local"
    winget_root = localappdata / "Microsoft" / "WinGet" / "Packages"
    matches = sorted(winget_root.glob("Gyan.FFmpeg_*/ffmpeg-*/bin/ffmpeg.exe"))
    if matches:
        return str(matches[-1])

    raise FileNotFoundError(
        "ffmpeg not found. Install it with: winget install --id Gyan.FFmpeg -e"
    )


def copy_if_present(src: Path | None, dst: Path) -> None:
    if src and src.exists():
        shutil.copy2(src, dst)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--obs-id", required=True)
    parser.add_argument("--audio", required=True, type=Path, help="SatNOGS .ogg audio file")
    parser.add_argument("--waterfall", type=Path, help="SatNOGS waterfall PNG")
    parser.add_argument("--trace", type=Path, help="optional signal trace CSV")
    parser.add_argument("--windows", type=Path, help="optional candidate windows CSV")
    parser.add_argument("--marked", type=Path, help="optional marked waterfall PNG")
    parser.add_argument("--out-root", default=Path("data/koyo/observations"), type=Path)
    parser.add_argument("--ffmpeg", help="explicit ffmpeg.exe path")
    parser.add_argument("--force", action="store_true", help="overwrite existing WAV")
    args = parser.parse_args()

    if not args.audio.exists():
        raise FileNotFoundError(args.audio)

    obs_dir = args.out_root / str(args.obs_id)
    obs_dir.mkdir(parents=True, exist_ok=True)

    copy_if_present(args.audio, obs_dir / "audio.ogg")
    copy_if_present(args.waterfall, obs_dir / "waterfall.png")
    copy_if_present(args.trace, obs_dir / "signal_trace.csv")
    copy_if_present(args.windows, obs_dir / "candidate_windows.csv")
    copy_if_present(args.marked, obs_dir / "waterfall_trace.png")

    wav_path = obs_dir / f"obs_{args.obs_id}.wav"
    if args.force or not wav_path.exists():
        ffmpeg = find_ffmpeg(args.ffmpeg)
        cmd = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-i",
            str(args.audio),
            "-ac",
            "1",
            "-ar",
            "48000",
            "-sample_fmt",
            "s16",
            str(wav_path),
        ]
        subprocess.run(cmd, check=True)

    metadata = {
        "obs_id": str(args.obs_id),
        "audio_ogg": "audio.ogg",
        "waterfall": "waterfall.png" if args.waterfall else None,
        "wav": wav_path.name,
        "sample_rate_hz": 48000,
        "channels": 1,
        "sample_format": "s16",
        "satnogs_mode": "FSK 9600",
        "framing": "AX.25",
    }
    (obs_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    print(f"prepared {obs_dir.resolve()}")
    print(f"wav: {wav_path.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

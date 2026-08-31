#!/usr/bin/env python3
"""Decode the latest available KOYO beacon directly from SatNOGS audio.

SatNOGS is store-and-forward: an observation appears after a ground station
uploads it, so this fetches the newest *available* good observation rather
than a live RF stream. SatNOGS' demodulated frames are downloaded only as an
optional byte-for-byte control; telemetry in live_decoded.json is produced by
the local GNU Radio/gr_satellites pipeline from the downloaded OGG audio.

Usage:
    python live_koyo.py
    python live_koyo.py --obs-id 14526577
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from decode_koyo import FRAME_SIZE, decode_frame
from fetch_satnogs import NETWORK, SATS, download, filter_observations_for_satellite, get_observation, polite_get
from inspect_kiss import read_kiss
from prepare_satnogs_observation import find_ffmpeg


ROOT = Path(__file__).resolve().parent
CONDA = Path.home() / "radioconda" / "Scripts" / "conda.exe"
CONFIG = ROOT / "koyo_gr_satellites.yml"
KOYO_SOURCE = "KOYOSC"
KOYO_DESTINATION = "GS-H20"


def parse_start(observation: dict) -> datetime:
    value = observation.get("start")
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def latest_available_observation() -> dict:
    sat = SATS["koyo"]
    params = {
        "sat_id": sat["sat_id"],
        "status": "good",
        "format": "json",
        "ordering": "-start",
    }
    response = polite_get(
        f"{NETWORK}/observations/?{urlencode(params)}",
        "latest KOYO observations",
        timeout=60,
    )
    observations = filter_observations_for_satellite(response.json(), sat)
    with_audio = [observation for observation in observations if observation.get("payload")]
    if not with_audio:
        raise RuntimeError("SatNOGS returned no good KOYO observations with downloadable audio")
    return max(with_audio, key=parse_start)


def write_official_frames(observation: dict, obs_dir: Path) -> set[str]:
    """Download SatNOGS demoddata only for a control comparison."""
    official = set()
    controls_dir = obs_dir / "satnogs_control"
    for index, demod in enumerate(observation.get("demoddata") or [], start=1):
        url = demod.get("payload_demod")
        if not url:
            continue
        path = controls_dir / f"frame_{index:03d}.bin"
        download(str(url), str(path), f"control frame {observation['id']}_{index}")
        if path.exists():
            official.add(path.read_bytes().hex())
    return official


def convert_to_wav(audio_path: Path, wav_path: Path) -> None:
    ffmpeg = find_ffmpeg(None)
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-i",
            str(audio_path),
            "-ac",
            "1",
            "-ar",
            "48000",
            "-sample_fmt",
            "s16",
            str(wav_path),
        ],
        check=True,
    )


def force_download(url: str, path: Path, label: str) -> None:
    response = polite_get(url, label, timeout=120)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)


def decode_audio(wav_path: Path, kiss_path: Path, clk_bw: float) -> list[bytes]:
    if not CONDA.exists():
        raise FileNotFoundError(f"radioconda not found: {CONDA}")
    subprocess.run(
        [
            str(CONDA),
            "run",
            "-n",
            "base",
            "gr_satellites",
            str(CONFIG),
            "--satcfg",
            "--wavfile",
            str(wav_path),
            "--samp_rate",
            "48000",
            "--clk_bw",
            str(clk_bw),
            "--kiss_out",
            str(kiss_path),
        ],
        check=True,
    )
    return read_kiss(kiss_path)


def serializable_frame(frame: bytes, index: int) -> dict:
    decoded = decode_frame(frame)
    decoded["frame_index"] = index
    decoded["frame_hex"] = frame.hex()
    if decoded["rtc_datetime"]:
        decoded["rtc_datetime"] = decoded["rtc_datetime"].isoformat()
    return decoded


def push_to_dashboard(decoded: list[dict], result: dict) -> int:
    """Write locally decoded frames to the dashboard's native and beacon measurements."""
    local_stack = ROOT / "local-stack"
    if str(local_stack) not in sys.path:
        sys.path.insert(0, str(local_stack))
    from load_influx import build_decoder_run_line, build_lines, write_batch

    rows = [{**frame, "obs_id": result["observation_id"]} for frame in decoded]
    lines = build_lines(rows)
    lines.append(build_decoder_run_line(result))
    if not lines:
        raise RuntimeError("No decoded telemetry values were available for dashboard push")
    return write_batch(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Decode a latest-available KOYO beacon from SatNOGS audio")
    parser.add_argument("--obs-id", help="decode this SatNOGS observation instead of selecting the latest available one")
    parser.add_argument("--clk-bw", type=float, default=0.15, help="GNU Radio clock recovery bandwidth")
    parser.add_argument("--skip-control", action="store_true", help="do not download SatNOGS demoddata for comparison")
    parser.add_argument("--force-download", action="store_true", help="redownload audio even when this observation is cached locally")
    parser.add_argument("--push-dashboard", action="store_true", help="write valid locally decoded frames to local InfluxDB")
    args = parser.parse_args()

    observation = get_observation(args.obs_id) if args.obs_id else latest_available_observation()
    matching = filter_observations_for_satellite([observation], SATS["koyo"])
    if not matching:
        raise RuntimeError(f"Observation {observation.get('id')} is not a verified KOYO observation")
    observation = matching[0]
    obs_id = str(observation["id"])
    obs_dir = ROOT / "data" / "koyo" / "observations" / obs_id
    obs_dir.mkdir(parents=True, exist_ok=True)

    audio_path = obs_dir / "audio.ogg"
    wav_path = obs_dir / f"obs_{obs_id}.wav"
    kiss_path = obs_dir / "live.kiss"
    output_path = obs_dir / "live_decoded.json"

    print(f"SatNOGS observation: {obs_id}")
    print(f"start: {observation.get('start')}")
    print(f"station: {observation.get('station_name')}")
    print("Downloading audio...")
    if args.force_download:
        force_download(observation["payload"], audio_path, f"audio {obs_id}")
    elif not download(observation["payload"], str(audio_path), f"audio {obs_id}"):
        if not audio_path.exists():
            raise RuntimeError("SatNOGS audio download failed")
    convert_to_wav(audio_path, wav_path)

    official = set() if args.skip_control else write_official_frames(observation, obs_dir)
    print("Decoding audio with local GNU Radio pipeline...")
    captured = decode_audio(wav_path, kiss_path, args.clk_bw)
    valid = []
    decoded = []
    rejected_non_koyo = 0
    for frame in captured:
        if len(frame) != FRAME_SIZE:
            continue
        candidate = serializable_frame(frame, len(decoded) + 1)
        if (
            candidate["src_callsign"] != KOYO_SOURCE
            or candidate["dest_callsign"] != KOYO_DESTINATION
        ):
            rejected_non_koyo += 1
            continue
        valid.append(frame)
        decoded.append(candidate)
    matches = [frame.hex() for frame in valid if frame.hex() in official]

    result = {
        "source": "SatNOGS observation audio decoded locally with gr_satellites",
        "observation_id": obs_id,
        "observation_start": observation.get("start"),
        "station": observation.get("station_name"),
        "captured_kiss_frames": len(captured),
        "valid_koyo_frames": len(valid),
        "rejected_non_koyo_263_frames": rejected_non_koyo,
        "official_control_frames": len(official),
        "byte_exact_control_matches": len(matches),
        "telemetry": decoded,
    }

    if args.push_dashboard and decoded:
        result["dashboard_write_status"] = push_to_dashboard(decoded, result)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(f"KISS frames captured: {len(captured)}")
    print(f"Valid 263-byte KOYO frames: {len(valid)}")
    if official:
        print(f"Byte-exact SatNOGS control matches: {len(matches)}")
    if "dashboard_write_status" in result:
        print(f"Dashboard write: HTTP {result['dashboard_write_status']}")
    print(f"Local decoded telemetry: {output_path}")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

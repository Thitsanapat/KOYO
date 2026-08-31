#!/usr/bin/env python3
"""Run and report reproducible SatNOGS-audio validation for KOYO."""

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORT_DIR = ROOT / "reports"
DEFAULT_OBSERVATIONS = ["14526577", "14637273", "14909294", "14909617", "14909703"]


def run_observation(obs_id: str, force_download: bool, push_dashboard: bool) -> int:
    command = [sys.executable, str(ROOT / "live_koyo.py"), "--obs-id", obs_id]
    if force_download:
        command.append("--force-download")
    if push_dashboard:
        command.append("--push-dashboard")
    print(f"\n=== SatNOGS observation {obs_id} ===", flush=True)
    return subprocess.run(command, cwd=ROOT, check=False).returncode


def load_result(obs_id: str) -> dict:
    obs_dir = ROOT / "data" / "koyo" / "observations" / obs_id
    result_path = obs_dir / "live_decoded.json"
    if not result_path.exists():
        return {
            "obs_id": obs_id,
            "result": "FAIL",
            "error": "live_decoded.json was not produced",
        }

    result = json.loads(result_path.read_text(encoding="utf-8"))
    valid = int(result.get("valid_koyo_frames", 0))
    official = int(result.get("official_control_frames", 0))
    matches = int(result.get("byte_exact_control_matches", 0))
    if valid > 0 and matches > 0:
        status = "PASS"
    elif valid > 0 and official == 0:
        status = "VALID_NO_CONTROL"
    else:
        status = "FAIL"

    audio = obs_dir / "audio.ogg"
    wav = obs_dir / f"obs_{obs_id}.wav"
    recovery_rate = round(matches * 100.0 / official, 1) if official else ""
    return {
        "obs_id": obs_id,
        "observation_start_utc": result.get("observation_start", ""),
        "station": result.get("station", ""),
        "audio_bytes": audio.stat().st_size if audio.exists() else 0,
        "wav_bytes": wav.stat().st_size if wav.exists() else 0,
        "captured_kiss_frames": int(result.get("captured_kiss_frames", 0)),
        "valid_koyo_frames": valid,
        "official_control_frames": official,
        "byte_exact_matches": matches,
        "unrecovered_control_frames": max(official - matches, 0),
        "recovery_rate_percent": recovery_rate,
        "result": status,
        "error": "",
    }


def write_reports(rows: list[dict]) -> None:
    REPORT_DIR.mkdir(exist_ok=True)
    csv_path = REPORT_DIR / "koyo_audio_validation.csv"
    fields = [
        "obs_id",
        "observation_start_utc",
        "station",
        "audio_bytes",
        "wav_bytes",
        "captured_kiss_frames",
        "valid_koyo_frames",
        "official_control_frames",
        "byte_exact_matches",
        "unrecovered_control_frames",
        "recovery_rate_percent",
        "result",
        "error",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    passed = sum(row["result"] == "PASS" for row in rows)
    official_total = sum(int(row.get("official_control_frames", 0)) for row in rows)
    match_total = sum(int(row.get("byte_exact_matches", 0)) for row in rows)
    overall_rate = round(match_total * 100.0 / official_total, 1) if official_total else 0.0
    markdown = [
        "# KOYO SatNOGS Audio Validation",
        "",
        f"Generated: {generated}",
        "",
        "## Pipeline",
        "",
        "`SatNOGS OGG -> PCM WAV 48 kHz -> GNU Radio FSK 9600 -> G3RUH/AX.25 -> KISS -> KOYO decoder`",
        "",
        "GNU Radio parameters: 9600 baud, 48 kHz input, 3 kHz deviation, clock bandwidth 0.15.",
        "A PASS requires at least one valid 263-byte KOYO frame and at least one byte-exact match against the SatNOGS control frame for the same observation.",
        "",
        "## Results",
        "",
        "| Observation | Start UTC | Station | KISS | Valid KOYO | Controls | Exact | Recovery | Result |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        markdown.append(
            f"| {row['obs_id']} | {row.get('observation_start_utc', '')} | "
            f"{row.get('station', '')} | {row.get('captured_kiss_frames', 0)} | "
            f"{row.get('valid_koyo_frames', 0)} | {row.get('official_control_frames', 0)} | "
            f"{row.get('byte_exact_matches', 0)} | {row.get('recovery_rate_percent', '')}% | "
            f"{row['result']} |"
        )
    markdown.extend(
        [
            "",
            "## Conclusion",
            "",
            f"{passed} of {len(rows)} selected observations passed the strict byte-exact control test.",
            f"Overall exact recovery was {match_total}/{official_total} control frames ({overall_rate}%).",
            "Only CRC-valid AX.25 frames are accepted for telemetry decoding and dashboard feedback.",
            "Candidate engineering fields remain labelled as candidates until independently validated.",
            "",
            "## What Not Decoded Means",
            "",
            "An official control frame without a byte-exact local match was not recovered from the OGG by the current local demodulator settings. It is not automatically a bad spacecraft frame; receiver SNR, tuning, Doppler, gain, and clock recovery can affect local recovery.",
            "Short or malformed KISS PDUs are diagnostic output and are rejected before telemetry decoding because they do not have the expected 263-byte KOYO frame and AX.25 path.",
            "A valid local frame that is absent from the downloaded control set remains local-only evidence and is not counted as an exact recovery match.",
            "",
        ]
    )
    md_path = REPORT_DIR / "KOYO_AUDIO_VALIDATION.md"
    md_path.write_text("\n".join(markdown), encoding="utf-8")
    print(f"\nCSV report: {csv_path}")
    print(f"Markdown report: {md_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate several KOYO SatNOGS audio observations")
    parser.add_argument("--obs-id", action="append", dest="obs_ids", help="observation ID; repeat for several")
    parser.add_argument("--reuse", action="store_true", help="only summarize existing live_decoded.json files")
    parser.add_argument("--force-download", action="store_true", help="redownload each SatNOGS audio file")
    parser.add_argument("--push-dashboard", action="store_true", help="push valid decoded frames to local Grafana/InfluxDB")
    args = parser.parse_args()

    obs_ids = args.obs_ids or DEFAULT_OBSERVATIONS
    return_codes = {}
    if not args.reuse:
        for obs_id in obs_ids:
            return_codes[obs_id] = run_observation(obs_id, args.force_download, args.push_dashboard)

    rows = [load_result(obs_id) for obs_id in obs_ids]
    for row in rows:
        if return_codes.get(row["obs_id"], 0) != 0 and row["result"] != "PASS":
            row["error"] = f"live_koyo exit {return_codes[row['obs_id']]}"
    write_reports(rows)
    return 0 if all(row["result"] == "PASS" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())

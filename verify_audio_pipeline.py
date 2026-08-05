#!/usr/bin/env python3
"""Control test: does our local gr_satellites audio decode match SatNOGS' own decoder?

Runs gr_satellites against a KOYO observation's WAV, then checks whether any
locally-decoded KISS frame is a byte-for-byte match against SatNOGS' own
demoddata for the same observation (data/koyo/frames_hex/<obsid>.txt).

A match proves the local pipeline (WAV -> gr_satellites -> KISS -> hex) is
correct end-to-end. This is the KOYO half of the control Loren asked for:
KOYO audio decodes -> pipeline is trusted -> any SCION-X failure is a signal
problem (clock recovery), not a pipeline bug.

Usage:
    python verify_audio_pipeline.py --obs-id 14526577
"""

import argparse
import subprocess
from pathlib import Path

from inspect_kiss import read_kiss

CONDA = Path.home() / "radioconda" / "Scripts" / "conda.exe"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--obs-id", required=True, help="observation ID with a local WAV and official demoddata")
    parser.add_argument("--config", default="koyo_gr_satellites.yml")
    parser.add_argument("--clk-bw", type=float, default=0.15, help="clock recovery bandwidth (default 0.06 in gr_satellites loses lock mid-frame on KOYO's 263-byte frames)")
    parser.add_argument("--samp-rate", default="48000")
    args = parser.parse_args()

    wav = Path("data/koyo/observations") / args.obs_id / f"obs_{args.obs_id}.wav"
    official_path = Path("data/koyo/frames_hex") / f"{args.obs_id}.txt"
    kiss_out = Path("data/koyo/observations") / args.obs_id / "verify.kiss"

    if not wav.exists():
        raise FileNotFoundError(f"{wav} not found - run prepare_satnogs_observation.py first")
    if not official_path.exists():
        raise FileNotFoundError(
            f"{official_path} not found - this observation has no official SatNOGS demoddata "
            "to compare against, so it can't be used as a control test"
        )

    subprocess.run(
        [
            str(CONDA), "run", "-n", "base", "gr_satellites", args.config, "--satcfg",
            "--wavfile", str(wav), "--samp_rate", args.samp_rate,
            "--clk_bw", str(args.clk_bw), "--kiss_out", str(kiss_out),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    official = set(official_path.read_text(encoding="utf-8").splitlines())
    local_frames = read_kiss(kiss_out)
    matches = [f.hex() for f in local_frames if f.hex() in official]

    print(f"local frames captured: {len(local_frames)} (sizes: {[len(f) for f in local_frames]})")
    print(f"official frames for obs {args.obs_id}: {len(official)}")
    print(f"exact byte-for-byte matches: {len(matches)}")
    if matches:
        print("PASS - local pipeline reproduced at least one official frame exactly")
        for m in matches:
            print(f"  {m}")
    else:
        print("FAIL - no local frame matched official demoddata")

    return 0 if matches else 1


if __name__ == "__main__":
    raise SystemExit(main())

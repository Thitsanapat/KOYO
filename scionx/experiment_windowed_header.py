"""Experiment 3: does the header itself show an internal settling trend, and
does calibrating from only its settled tail (instead of the full 144 bits)
help?

Part A: split the 144-bit header into 16-bit windows, print each window's
own local 0-level/1-level/midpoint/amplitude, to check whether there's a
real internal trend (vs. experiment 2's theory built from only 3 points).

Part B: recalibrate the decision threshold from only the last 64 header bits
(bits 80-144, presumably closer to settled) and apply it as a single global
threshold, same as the original method but with a different calibration
window - to see whether "which portion of the header" matters.

See NOTES.md for results (short version: real trend confirmed, but tail-only
calibration is worse than full-header calibration, not better).
"""
import os
import sys

import numpy as np

EXTERNAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "external", "scionx-decode-writeup")
sys.path.insert(0, EXTERNAL)
sys.path.insert(0, os.path.join(EXTERNAL, "04_Beacon"))

from scionx import audio_io, baseline  # noqa: E402
from scionx.hdlc import crc16_x25  # noqa: E402

import importlib.util as _ilu

_spec = _ilu.spec_from_file_location("beacon_decode", os.path.join(EXTERNAL, "04_Beacon", "04_beacon_field_decode.py"))
bd = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(bd)


def windowed_header_trend(y, start, win=16):
    t_bits = np.array(bd.bits_lsb_first(bd.FLAGS4) + bd.bits_lsb_first(bd.HEADER_ADDR), dtype=np.uint8)
    idx_hdr = start + bd.SPS * np.arange(0, 144) + bd.PHASE
    y_hdr = y[idx_hdr]

    print("bit#      segment    y0(win)   y1(win)   mid(win)   amp(win)")
    for i in range(0, 144, win):
        tb, yb = t_bits[i:i + win], y_hdr[i:i + win]
        v0, v1 = yb[tb == 0], yb[tb == 1]
        seg = "flags" if i < 32 else "address"
        if len(v0) and len(v1):
            m0, m1 = np.median(v0), np.median(v1)
            print(f"{i:4d}-{i + win:<4d}  {seg:8s}  {m0:8.4f}  {m1:8.4f}  {(m0 + m1) / 2:8.4f}   {(m1 - m0) / 2:7.4f}")


def decode_with_tail_threshold(y, start, tail_start=80):
    t_bits = np.array(bd.bits_lsb_first(bd.FLAGS4) + bd.bits_lsb_first(bd.HEADER_ADDR), dtype=np.uint8)
    idx_hdr = start + bd.SPS * np.arange(0, 144) + bd.PHASE
    y_hdr = y[idx_hdr]

    tb, yb = t_bits[tail_start:144], y_hdr[tail_start:144]
    grid = np.linspace(yb.min(), yb.max(), 2000)
    errs = [(yb[tb == 1] <= t).sum() + (yb[tb == 0] > t).sum() for t in grid]
    thr = grid[int(np.argmin(errs))]
    hdr_err = int(min(errs))

    span_j1 = int(bd.SEARCH_SAMPLES / bd.SPS)
    idx_all = start + bd.SPS * np.arange(0, span_j1) + bd.PHASE
    idx_all = idx_all[idx_all < y.size]
    body_bits_raw = (y[idx_all[32:]] > 0).astype(np.uint8)
    body_idx_raw = idx_all[32:]
    body_bits, body_sample_idx = bd.destuff_with_map(body_bits_raw, body_idx_raw)
    n_bits = min(body_bits.size, 274 * 8)
    body_sample_idx = body_sample_idx[:n_bits]

    decided_bit = (y[body_sample_idx] > thr).astype(np.uint8)

    ref_bits = np.array(bd.bits_lsb_first(bd.REF), dtype=np.uint8)
    n_cmp = min(n_bits, ref_bits.size)
    errs_total = int(np.sum(decided_bit[:n_cmp] != ref_bits[:n_cmp]))

    crc_pass = None
    if n_bits >= 274 * 8:
        fcs_bytes = bd.bits_to_bytes(decided_bit[272 * 8:274 * 8])
        crc_pass = (crc16_x25(bd.bits_to_bytes(decided_bit[:272 * 8])).to_bytes(2, "little") == fcs_bytes)

    return thr, hdr_err, errs_total, n_cmp, crc_pass


def main():
    y, fs = audio_io.read_audio(bd.AUDIO, expected_fs=bd.FS)
    bl = baseline.restore_baseline(y, num_iters=7, W=1000)
    yc = bl["y_comp_final"]
    template = bd.build_header_template()
    starts, zs = bd.detect_frame_starts(yc, template)

    print("=== Part A: windowed header trend, frame #2 ===")
    windowed_header_trend(y, starts[1])
    print()

    print("=== Part B: tail-64-calibrated global threshold, all frames ===")
    for i, start in enumerate(starts, start=1):
        thr, hdr_err, errs_total, n_cmp, crc_pass = decode_with_tail_threshold(y, start)
        print(f"[Frame #{i}] thr={thr:+.4f}  hdr_err(64)={hdr_err}/64  "
              f"total errors vs REF={errs_total}/{n_cmp}  CRC={'PASS' if crc_pass else 'fail'}")


if __name__ == "__main__":
    main()

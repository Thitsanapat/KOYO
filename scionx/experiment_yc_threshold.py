"""Experiment: does JacyyChang's already-computed baseline-compensated signal
(yc = y - slow-drift baseline) fix the data-segment bit errors that a single
frame-global fixed threshold on raw y can't track?

Context: scionx-decode-writeup's 04_beacon_field_decode.py computes yc via
decision-directed baseline restoration (scionx/baseline.py), but only uses it
for (a) frame-start cross-correlation and (b) the zero-run segments' bit
decisions. The address/data/FCS segments ("is_theta" in decode_frame()) use
raw y with ONE fixed threshold calibrated from the 144 header bits, applied
across the whole frame. Their own 03a diagnostic found a slow "invisible
curve" of drifting asymmetry across the data segments - exactly what yc's
baseline tracking exists to remove, but isn't applied there.

This script re-decodes all 3 frames using yc instead of raw y for every
segment (not just zero-runs), and checks whether CRC passes on any of them.
Reuses the reference repo's own functions (not our own repo) via sys.path -
see scionx/external/README_LOCAL.md for provenance.
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


def decode_frame_yc(y, yc, start):
    """Same structure as bd.decode_frame(), but every segment (not just
    zero-runs) is decided from yc at threshold 0, instead of raw y at a
    single frame-global fixed offset."""
    span_j1 = int(bd.SEARCH_SAMPLES / bd.SPS)
    idx_all = start + bd.SPS * np.arange(0, span_j1) + bd.PHASE
    idx_all = idx_all[idx_all < y.size]
    body_bits_raw = (y[idx_all[32:]] > 0).astype(np.uint8)  # structure pass still uses raw y, matches original
    body_idx_raw = idx_all[32:]
    body_bits, body_sample_idx = bd.destuff_with_map(body_bits_raw, body_idx_raw)

    n_bits = min(body_bits.size, 274 * 8)
    body_bits = body_bits[:n_bits]
    body_sample_idx = body_sample_idx[:n_bits]

    yc_at_bit = yc[body_sample_idx]
    decided_bit = (yc_at_bit > 0).astype(np.uint8)

    crc_pass = None
    if n_bits >= 274 * 8:
        fcs_bytes = bd.bits_to_bytes(decided_bit[272 * 8:274 * 8])
        crc_pass = (crc16_x25(bd.bits_to_bytes(decided_bit[:272 * 8])).to_bytes(2, "little") == fcs_bytes)

    # bit-error count vs REF (payload+FCS = 274 bytes), for diagnostics even if CRC fails
    ref_bits = np.array(bd.bits_lsb_first(bd.REF), dtype=np.uint8)
    n_cmp = min(n_bits, ref_bits.size)
    errs = int(np.sum(decided_bit[:n_cmp] != ref_bits[:n_cmp]))

    return decided_bit, n_bits, crc_pass, errs, n_cmp


def main():
    y, fs = audio_io.read_audio(bd.AUDIO, expected_fs=bd.FS)
    bl = baseline.restore_baseline(y, num_iters=7, W=1000)
    yc = bl["y_comp_final"]

    template = bd.build_header_template()
    starts, zs = bd.detect_frame_starts(yc, template)
    print(f"Detected {len(starts)} frame(s): " + ", ".join(f"@{s} (z={z:.2f})" for s, z in zip(starts, zs)))
    print()

    for i, start in enumerate(starts, start=1):
        decided_bit, n_bits, crc_pass, errs, n_cmp = decode_frame_yc(y, yc, start)
        print(f"[Frame #{i}] yc-threshold=0 decode: n_bits={n_bits}  "
              f"bit errors vs REF={errs}/{n_cmp}  CRC={'PASS' if crc_pass else 'fail'}")


if __name__ == "__main__":
    main()

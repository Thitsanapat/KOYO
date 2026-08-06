"""Experiment 2: interpolate a decision threshold between known-ground-truth
anchor points (header + the 2 zero-run segments) across the frame, instead of
either (a) one frame-global fixed threshold, or (b) experiment 1's
decision-directed yc (which made things worse - see NOTES.md).

Unlike yc, this never touches the data segments themselves when estimating
the baseline/threshold - it only ever uses positions where the true bit is
already known (header address bits, and the zero-run segments which are
always literal 0x00 in REFERENCE_FRAME.md), then linearly interpolates the
"0-level" between those 3 anchor points and adds a constant margin (the
offset from 0-level to decision threshold, taken from the header, the only
place both 0s and 1s are known) to get a *position-dependent* threshold for
every bit in between - including the data segments.
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


def decode_frame_interp(y, start):
    offset_thr, hdr_err = bd.calibrate_offset_threshold(y, start)

    # header anchor: same 144-bit window calibrate_offset_threshold uses
    t_bits = np.array(bd.bits_lsb_first(bd.FLAGS4) + bd.bits_lsb_first(bd.HEADER_ADDR), dtype=np.uint8)
    idx_hdr = start + bd.SPS * np.arange(0, 144) + bd.PHASE
    y_hdr = y[idx_hdr]
    y0_header = float(np.median(y_hdr[t_bits == 0]))
    x_header = float(np.median(idx_hdr))
    margin = offset_thr - y0_header  # offset from this frame's 0-level to its decision threshold

    # structure pass (unchanged) to get segment labels + per-bit sample indices
    span_j1 = int(bd.SEARCH_SAMPLES / bd.SPS)
    idx_all = start + bd.SPS * np.arange(0, span_j1) + bd.PHASE
    idx_all = idx_all[idx_all < y.size]
    body_bits_raw = (y[idx_all[32:]] > 0).astype(np.uint8)
    body_idx_raw = idx_all[32:]
    body_bits, body_sample_idx = bd.destuff_with_map(body_bits_raw, body_idx_raw)
    n_bits = min(body_bits.size, 274 * 8)
    body_sample_idx = body_sample_idx[:n_bits]

    seg_label = np.empty(n_bits, dtype=object)
    for label, b0, b1 in bd.build_segment_map():
        bit0, bit1 = b0 * 8, min(b1 * 8, n_bits)
        if bit0 < bit1:
            seg_label[bit0:bit1] = label

    # zero-run anchors: known-0 samples elsewhere in the frame
    anchors_x, anchors_y = [x_header], [y0_header]
    for zr_label in ("zero-run1", "zero-run2"):
        mask = (seg_label == zr_label)
        if mask.sum() >= 8:
            zr_idx = body_sample_idx[mask]
            anchors_x.append(float(np.median(zr_idx)))
            anchors_y.append(float(np.median(y[zr_idx])))

    order = np.argsort(anchors_x)
    ax = np.array(anchors_x)[order]
    ay = np.array(anchors_y)[order]

    y_at_bit = y[body_sample_idx]
    local_0level = np.interp(body_sample_idx, ax, ay)
    theta_local = local_0level + margin
    decided_bit = (y_at_bit > theta_local).astype(np.uint8)

    ref_bits = np.array(bd.bits_lsb_first(bd.REF), dtype=np.uint8)
    n_cmp = min(n_bits, ref_bits.size)
    errs = int(np.sum(decided_bit[:n_cmp] != ref_bits[:n_cmp]))

    crc_pass = None
    if n_bits >= 274 * 8:
        fcs_bytes = bd.bits_to_bytes(decided_bit[272 * 8:274 * 8])
        crc_pass = (crc16_x25(bd.bits_to_bytes(decided_bit[:272 * 8])).to_bytes(2, "little") == fcs_bytes)

    return decided_bit, n_bits, crc_pass, errs, n_cmp, len(ax), hdr_err


def main():
    y, fs = audio_io.read_audio(bd.AUDIO, expected_fs=bd.FS)
    bl = baseline.restore_baseline(y, num_iters=7, W=1000)
    yc = bl["y_comp_final"]

    template = bd.build_header_template()
    starts, zs = bd.detect_frame_starts(yc, template)
    print(f"Detected {len(starts)} frame(s): " + ", ".join(f"@{s} (z={z:.2f})" for s, z in zip(starts, zs)))
    print()

    for i, start in enumerate(starts, start=1):
        decided_bit, n_bits, crc_pass, errs, n_cmp, n_anchors, hdr_err = decode_frame_interp(y, start)
        print(f"[Frame #{i}] interpolated-threshold decode ({n_anchors} anchors): "
              f"hdr_err={hdr_err}/144  bit errors vs REF={errs}/{n_cmp}  CRC={'PASS' if crc_pass else 'fail'}")


if __name__ == "__main__":
    main()

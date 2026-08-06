# SCION-X decode notes

Working from `external/scionx-decode-writeup/` (JacyyChang, HEX20 team member -
gitignored, not ours to redistribute; see `CLAUDE.md` §10 for provenance and
the modulation/frame-size corrections found while reading it).

## 2026-08-07: reproduced their results

`01_frame_detection.py` and `04_beacon_field_decode.py` both reproduce
exactly: 3 frames detected (z-scores 12.01/12.74/12.25), 26-75 possibly-wrong
bits out of 2192 per frame, CRC fails on all 3. Frame #2 has a perfect header
(0/144 errors) but still fails CRC, so its remaining ~26 wrong bits are all
in the data/zero-run segments.

## Tried: use the already-computed baseline-compensated `yc` for data segments

Their pipeline computes `yc` (decision-directed baseline restoration,
`scionx/baseline.py`) for the whole recording, but only uses it for frame-start
correlation and the zero-run segments' bit decisions - the address/data/FCS
segments use raw `y` with a single frame-global threshold calibrated from the
144 header bits. Their own 03a diagnostic found a slow "invisible curve" of
drifting asymmetry across the data segments, which a single fixed threshold
can't track but `yc`'s baseline-tracking exists specifically to remove -
seemed like an obvious gap to test.

**Result: worse, not better.** Swapping to `yc` for every segment (either
threshold=0, matching the zero-run convention, or a `yc`-recalibrated header
threshold) gives ~300/2176 bit errors per frame - roughly 10x worse than the
original ~26-75/2192. Script: `experiment_yc_threshold.py`.

**Likely why**: `restore_baseline`'s decision-directed loop assumes the
underlying signal is baseline + a well-behaved bit sequence and iteratively
hard-decides bits to estimate the residual baseline. That converges correctly
on zero-run segments (the true content genuinely is constant), but on data
segments the moving-average window (2001 samples, ~42ms) is comparable to or
longer than real runs of same-valued bits in the actual telemetry content -
so the "baseline" it estimates there is partly *absorbing real signal
structure*, not just slow channel drift. Using it corrupts data-segment bits
rather than cleaning them up.

**Not yet tried** (more principled, but more work): interpolate a threshold
between the header (start of frame) and the two zero-run segments (known-0
regions elsewhere in the frame) *without* decision-directed feedback on the
data itself - i.e. only ever calibrate from segments with known ground
truth, then linearly/piecewise interpolate across the data segments in
between, rather than either (a) one global constant or (b) a decision-directed
estimate that can absorb real content.

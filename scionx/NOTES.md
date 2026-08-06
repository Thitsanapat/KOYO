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

## Tried: interpolate a threshold between known-ground-truth anchors only

More principled version of the above: never touch the data segments when
estimating the baseline. Use only the 3 known-ground-truth anchor points in
each frame (header address bits + zero-run1 + zero-run2), take each anchor's
median raw-`y` "0-level," linearly interpolate the 0-level across all bit
positions in between using `np.interp`, then add a constant margin (the
offset from 0-level to decision threshold, taken from the header - the only
place both 0s and 1s are known) to get a position-dependent threshold.
Script: `experiment_interpolated_threshold.py`.

**Result: also worse, not better** (~290-389/2176 vs original ~26-75/2192).

**Why, and a real finding along the way**: debugging this turned up something
worth recording even though the fix didn't work. On frame #2, the header's
measured "0-level" (median of raw `y` at known-0 header bits) is **-0.55**,
while the zero-run1/zero-run2 segments' measured "0-level" is only **-0.03 to
-0.05** - roughly **10x smaller in magnitude**, despite being only ~90-200ms
later in the same ~228ms frame. That's a large, fast shift, concentrated
right at the start of the frame - consistent with an **AGC settling
transient** (receiver gain still adjusting for the first ~100ms after signal
acquisition) rather than a slow, uniform channel drift. If that's right, it's
not just the DC baseline (0-level) that's shifted during that transient - the
signal *amplitude* (1-level minus 0-level) is likely shifting too, which a
single frame-wide "margin" (borrowed from the header, itself measured during
the transient) can't correct for. That would explain why extrapolating the
header's calibration outward - linearly or otherwise - doesn't help: the
header itself may be the least representative part of the frame to calibrate
from, not the most reliable one, if it's sitting inside an AGC transient.

## Tried: check the AGC-transient theory by windowing the header itself

Split the 144-bit header into nine 16-bit windows and computed each window's
own local 0-level/1-level/midpoint/amplitude (frame #2). Result: the midpoint
(natural decision threshold) **does trend down** across the header - 0.308 ->
0.225 -> 0.152 -> 0.101 -> 0.063 -> **0.020** (window 6, bits 96-112) - then
ticks back **up** to 0.065-0.123 in the last two windows, before jumping to
the zero-run segments' own conditions (roughly -0.03 to -0.05) later in the
frame. So there's a real settling trend, but it isn't a clean monotonic decay
all the way to the zero-run level by the time the header ends - more like it
gets *close*, wobbles (16-bit windows are small, so each one's own noise
matters), then the frame moves on to data content before fully settling.

Tried the obvious next step - calibrate the decision threshold from *only*
the later, more-settled half of the header (bits 80-144, 64 bits) instead of
the full 144, then apply that single threshold globally. **Result: much
worse** (928-977/2176 errors, worse than either of the first two attempts).
Makes sense in hindsight: a threshold tuned for the *settled* regime is
badly wrong for the *early* part of the frame (which includes some of the
data segments), so "which single global threshold" was never really the
right axis to search along - the frame needs a genuinely position-varying
model, and none of the three simple ways tried here (borrow yc, linear
interpolation between 3 points, recalibrate from a different fixed window)
capture it.

## Where this stands

Three concrete ideas tried, all ruled out, with one solid diagnostic lead
(the header shows real, non-trivial AGC-like settling behavior, confirmed by
its own internal windowed trend - not just a guess from comparing 2-3 points
anymore). What's actually needed next is real signal-processing modeling:
either (a) fit a proper decaying-envelope/AGC model with many more sample
points and confidence weighting per window, robust to the small-window noise
seen here, or (b) use an actual AGC-compensation front end (e.g. GNU Radio's
`agc` block) before this pipeline's threshold logic even runs, rather than
correcting for a post-hoc gain transient in already-AGC'd audio. Both are
real DSP development, not a quick script - **time-boxed here**. Worth
mentioning the windowed-header finding back to JacyyChang/the gr-satellites
discussion even without a working fix - it narrows down where to look.

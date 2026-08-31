# KOYO SatNOGS Audio Validation

Generated: 2026-08-30T21:05:18+00:00

## Pipeline

`SatNOGS OGG -> PCM WAV 48 kHz -> GNU Radio FSK 9600 -> G3RUH/AX.25 -> KISS -> KOYO decoder`

GNU Radio parameters: 9600 baud, 48 kHz input, 3 kHz deviation, clock bandwidth 0.15.
A PASS requires at least one valid 263-byte KOYO frame and at least one byte-exact match against the SatNOGS control frame for the same observation.

## Results

| Observation | Start UTC | Station | KISS | Valid KOYO | Controls | Exact | Recovery | Result |
|---|---|---|---:|---:|---:|---:|---:|---|
| 14526577 | 2026-07-16T17:47:30Z | MAUSyagi | 6 | 1 | 35 | 1 | 2.9% | PASS |
| 14637273 | 2026-07-29T23:33:14Z | EA3AGB | 8 | 1 | 3 | 1 | 33.3% | PASS |
| 14909294 | 2026-08-30T16:58:25Z | MAUSyagi | 32 | 14 | 31 | 14 | 45.2% | PASS |
| 14909617 | 2026-08-30T18:36:38Z | W6MSU UHF | 8 | 4 | 4 | 3 | 75.0% | PASS |
| 14909703 | 2026-08-30T18:43:47Z | MAUSyagi-AK | 6 | 2 | 1 | 1 | 100.0% | PASS |

## Conclusion

5 of 5 selected observations passed the strict byte-exact control test.
Overall exact recovery was 20/74 control frames (27.0%).
Only CRC-valid AX.25 frames are accepted for telemetry decoding and dashboard feedback.
Candidate engineering fields remain labelled as candidates until independently validated.

## What Not Decoded Means

An official control frame without a byte-exact local match was not recovered from the OGG by the current local demodulator settings. It is not automatically a bad spacecraft frame; receiver SNR, tuning, Doppler, gain, and clock recovery can affect local recovery.
Short or malformed KISS PDUs are diagnostic output and are rejected before telemetry decoding because they do not have the expected 263-byte KOYO frame and AX.25 path.
A valid local frame that is absent from the downloaded control set remains local-only evidence and is not counted as an exact recovery match.

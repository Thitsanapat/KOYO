# KOYO Beacon Decoder - Morning Handoff

Date: 2026-08-31

## Objective

Build a reproducible KOYO beacon path from a SatNOGS observation recording to
CRC-valid telemetry and a local HEX-style Grafana dashboard.

## Delivered Pipeline

`SatNOGS OGG -> mono PCM WAV 48 kHz -> GNU Radio FSK 9600 -> G3RUH/AX.25 deframer -> KISS -> 263-byte KOYO decoder -> InfluxDB -> Grafana`

The audio is decoded locally. SatNOGS demodulated frames are downloaded only
as a control set for byte-for-byte validation; they are not used as decoder
input.

## GNU Radio Configuration

- Modulation: FSK, 9600 baud
- Audio input: mono, 48 kHz PCM WAV
- Clock recovery bandwidth: 0.15
- Link layer: G3RUH-scrambled AX.25/HDLC
- Accepted telemetry frame length: 263 bytes
- Expected AX.25 path: `KOYOSC -> GS-H20`
- Flowgraph: `gnuradio/koyo_audio_rx.grc`

The AX.25 deframer performs NRZI handling, G3RUH descrambling, HDLC boundary
detection, bit de-stuffing, and CRC checking. Short or malformed PDUs can be
visible in diagnostic KISS output, but only valid 263-byte KOYO frames proceed
to telemetry decoding and dashboard feedback.

## Validation Result

Five SatNOGS observations from four receiving stations were tested. All five
passed the strict criterion: at least one locally decoded 263-byte frame and at
least one byte-exact match against the SatNOGS control for the same observation.

| Observation | Station | KISS frames | Valid KOYO | Exact matches | Result |
|---|---|---:|---:|---:|---|
| 14526577 | MAUSyagi | 6 | 1 | 1 | PASS |
| 14637273 | EA3AGB | 8 | 1 | 1 | PASS |
| 14909294 | MAUSyagi | 32 | 14 | 14 | PASS |
| 14909617 | W6MSU UHF | 8 | 4 | 3 | PASS |
| 14909703 | MAUSyagi-AK | 6 | 2 | 1 | PASS |

Total: 22 locally decoded valid frames and 20 byte-exact control matches.
Overall exact recovery: 20 of 74 official control frames (27.0%). This measures
the current local OGG demodulator recovery, not spacecraft packet validity.
Detailed evidence is in `reports/koyo_audio_validation.csv` and
`reports/KOYO_AUDIO_VALIDATION.md`.

`Not decoded` means the current local GNU Radio settings did not reproduce an
official control frame from the OGG, or a diagnostic PDU failed the expected
263-byte KOYO length/path checks. It does not by itself mean that the official
spacecraft frame was invalid.

## Historical Coverage

The five rows above are controlled OGG-to-GNU-Radio tests, not the full mission
history. The complete locally decoded dataset spans 55 UTC days, 17,155 frames,
1,055 SatNOGS observations, and 114 receiving stations. Daily frame,
observation, and receiving-station counts are reported separately in
`reports/koyo_historical_coverage.csv` and `reports/KOYO_HISTORICAL_COVERAGE.md`.

## Dashboard

Grafana: `http://localhost:3000/d/koyo-telemetry/koyo-telemetry`

- Local InfluxDB stores native `koyo` points and HEX-style `beacon` rows.
- A `decoder_run` measurement records PASS/NO MATCH status, observation,
  station, frame counts, exact recovery, and the latest CRC-valid raw HEX.
- Confirmed and candidate channels have separate `quality` tags and names.
- The full 43-panel layout covers summary, orbit, decoder evidence, electrical,
  solar arrays, battery, power distribution, comms, thermal/health, OBC, and
  recent feedback views.
- Unmapped target fields stay visible as `NOT DECODED`; no value is fabricated.
- All 22 live Flux query targets pass against the running InfluxDB instance.

## Demonstration

Latest available SatNOGS audio to dashboard:

```powershell
powershell -ExecutionPolicy Bypass -File .\local-stack\live_refresh.ps1
```

Verified demo run on 2026-08-31 with observation `14909703`: 6 captured KISS
frames, 2 valid 263-byte KOYO frames, 1 byte-exact control match, and successful
InfluxDB dashboard write (`HTTP 204`).

Reproduce the five-observation validation:

```powershell
.\.venv\Scripts\python.exe validate_audio_batch.py --push-dashboard
```

Open the editable GNU Radio flowgraph:

```powershell
& "$env:USERPROFILE\radioconda\Library\bin\gnuradio-companion.exe" .\gnuradio\koyo_audio_rx.grc
```

## Scope and Limitations

- SatNOGS is store-and-forward. "Latest" means the newest uploaded observation,
  not a continuous live RF socket.
- The full 17,155-frame history comes from SatNOGS demodulated data. Direct
  OGG-to-GNU-Radio byte-exact validation currently covers five observations.
- Running all 1,464 available recordings would require roughly 100 GB of
  temporary 48 kHz WAV data, so the submitted audio test is a controlled sample.
- Engineering fields whose byte mappings are not independently confirmed stay
  labelled `candidate`; no confidential mapping is included in this package.
- Full dashboard coverage does not mean every target field has been decoded.
  The next technical step is to validate candidate and unavailable field
  mappings against an authorized reference.

## Suggested 60-Second Explanation

"The decoder now starts from SatNOGS OGG audio rather than pre-decoded HEX. It
converts the recording to 48 kHz WAV, runs a local GNU Radio 9600-baud G3RUH
AX.25 chain, keeps CRC-valid 263-byte KOYO frames, decodes confirmed telemetry,
and writes HEX-style channel/value feedback plus decoder evidence to InfluxDB
and Grafana. I tested five observations from four stations: all passed,
producing 22 valid frames and 20 byte-exact matches against SatNOGS controls.
The full dashboard shows confirmed values, labelled candidates, and explicit
NOT DECODED states for mappings that are not yet authorized."

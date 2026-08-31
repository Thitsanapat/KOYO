# KOYO Beacon Decoder Submission

## Start Here

- `KOYO_Beacon_Decoder_Final_Presentation.pdf`: detailed 15-slide presentation
- `KOYO_Beacon_Decoder_Final_Presentation.pptx`: editable presentation with
  Thai-first and English backup speaker notes on every slide
- `KOYO_PRESENTATION_SCRIPT_TH_EN.md`: complete rehearsal script and ten likely
  questions with Thai/English answers
- `KOYO_Real_Results.xlsx`: seven-sheet workbook containing formulas, real
  audio validation rows, historical coverage, latest demo output, telemetry,
  and dashboard coverage
- `reports/KOYO_MORNING_HANDOFF.md`: technical handoff and demo notes
- `reports/KOYO_AUDIO_VALIDATION.md`: OGG recovery and byte-exact evidence
- `reports/KOYO_HISTORICAL_COVERAGE.md`: complete historical coverage summary
- `gnuradio/koyo_audio_rx.grc`: editable GNU Radio Companion flowgraph
- `gnuradio/koyo_audio_rx_companion_public.png`: actual GNU Radio Companion
  screenshot with the local user path removed
- `deliverables/koyo_full_telemetry_dashboard.png`: full dashboard evidence

## Demonstration

Run from the full project workspace on the prepared Windows machine:

```powershell
powershell -ExecutionPolicy Bypass -File .\local-stack\live_refresh.ps1
```

The command selects the latest uploaded SatNOGS observation, downloads its OGG,
converts it to a 48 kHz mono WAV, decodes it locally with GNU Radio, filters for
the expected 263-byte KOYO AX.25 path, and pushes telemetry to local
InfluxDB/Grafana.

The submitted command path was exercised end-to-end with observation
`14909703`: 6 KISS frames, 2 valid KOYO frames, 1 byte-exact control match, and
an InfluxDB write response of `HTTP 204`.

The Grafana dashboard contains the full target structure and 43 panels. Its 22
live Flux queries pass against InfluxDB. Decoder status and raw HEX come from
the latest actual run; target fields without an authorized mapping display
`NOT DECODED`, and tentative engineering fields display `CANDIDATE`.

## Evidence Boundary

- Full history: 17,155 SatNOGS-demodulated frames, 1,055 observations, 55 UTC
  days, and 114 receiving stations.
- Direct OGG validation: five observations, 22 valid local frames, 20 byte-exact
  matches from 74 official controls, giving 27.0% exact recovery.
- `Not decoded` means the current local OGG pipeline did not reproduce an
  official control frame, or a diagnostic PDU failed the expected frame/path
  checks. It does not automatically indicate a bad spacecraft frame.
- SatNOGS is store-and-forward, not continuous live RF streaming.
- Candidate telemetry fields remain explicitly labelled as candidates.
- A complete visual layout does not imply that every telemetry byte mapping is
  known; unavailable target fields are intentionally shown as `NOT DECODED`.

## Deliberate Exclusions

The portable ZIP excludes downloaded OGG/WAV recordings, local Grafana/InfluxDB
binaries and runtime state, raw mission data, and confidential source documents
or mapping-bearing dashboard/ingestion source. These remain in the controlled
local workspace where authorized. The dashboard is represented in the package
by the full evidence image and the presentation/report.

For GitHub, publish only the separately generated
`github-public/KOYO-Beacon-Decoder` directory. Never publish the private
workspace root or its Git history.

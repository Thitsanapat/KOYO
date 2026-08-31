# KOYO Beacon Decoder

A reproducible evidence package for receiving a KOYO satellite beacon from
SatNOGS audio, demodulating 9600-baud FSK with GNU Radio, validating G3RUH
AX.25 frames, and presenting traceable results for telemetry visualization.

This public repository focuses on the signal-processing proof and the evidence
needed to review it. Confidential mission documents, private telemetry byte
mappings, raw recordings, and local operations infrastructure are deliberately
excluded.

## At a Glance

| Result | Value |
|---|---:|
| Direct OGG observations tested | 5 |
| Observations meeting the strict PASS rule | 5/5 |
| Valid local KOYO frames | 22 |
| Byte-exact SatNOGS control matches | 20 |
| Official control frames in the sample | 74 |
| Overall exact recovery | 27.0% |
| Historical SatNOGS-demodulated frames | 17,155 |
| Historical observations | 1,055 |
| UTC days represented | 55 |
| Receiving stations represented | 114 |
| Grafana panels in the operational layout | 43 |
| Validated live Flux query targets | 22/22 |

The direct audio test and the historical dataset are different evidence sets.
Only the five selected observations were re-demodulated locally from OGG for
the byte-exact GNU Radio proof.

## Project Goal

The project answers three questions:

1. Can the receive chain start from a SatNOGS OGG recording rather than from
   HEX that was already decoded elsewhere?
2. Can a locally recovered frame be checked against an independent control in
   a way that is stronger than visual similarity?
3. Can the result be carried into a telemetry dashboard without inventing
   values for fields whose mappings are still uncertain?

The acceptance rule for each tested observation is intentionally strict. A
PASS requires at least one CRC-valid 263-byte KOYO frame and at least one frame
that matches a same-observation SatNOGS control byte for byte.

## End-to-End Architecture

```text
SatNOGS observation
  |
  +-- OGG audio ------------------------------+
  |                                           |
  v                                           |
FFmpeg: mono 48 kHz PCM16 WAV                 |
  |                                           |
  v                                           |
GNU Radio: 9600-baud FSK demodulation         |
  |                                           |
  v                                           |
G3RUH descrambling + NRZI + HDLC deframing    |
  |                                           |
  v                                           |
CRC-valid AX.25 PDU -> KISS                    |
  |                                           |
  v                                           v
KOYO frame checks                    SatNOGS demodulated control
  |                                           |
  +------------ byte-exact comparison <-------+
  |
  v
Telemetry confidence contract
  |
  v
InfluxDB -> Grafana evidence dashboard
```

SatNOGS demodulated frames are used only as validation controls. They are not
fed into the local audio demodulator.

![GNU Radio Companion flowgraph](gnuradio/koyo_audio_rx_companion.png)

## Signal and Frame Configuration

| Parameter | Configuration |
|---|---|
| Input audio | Mono signed 16-bit PCM WAV |
| Audio sample rate | 48,000 samples/s |
| Modulation | FSK |
| Symbol rate | 9,600 baud |
| Samples per symbol | 5 |
| Frequency deviation | 3,000 Hz |
| Clock-recovery bandwidth | 0.15 |
| Data framing | AX.25 / HDLC |
| Line coding | NRZI |
| Scrambler | G3RUH |
| Expected complete frame length | 263 bytes |
| Local output format | KISS |

The public flowgraph uses the demodulator, AX.25 deframer, and KISS sink blocks
provided by gr-satellites.

## Validation Checks

A diagnostic PDU is accepted as a valid KOYO telemetry frame only when it
satisfies the expected frame contract:

1. The AX.25 deframer reports a valid CRC.
2. The complete frame is 263 bytes long.
3. The AX.25 source and destination path match the expected KOYO beacon path.
4. The frame type is the expected UI telemetry form.
5. For the strict observation PASS result, at least one accepted frame matches
   a SatNOGS control from the same observation byte for byte.

Short, malformed, or path-mismatched PDUs remain diagnostic output and are not
sent to telemetry interpretation.

## Direct Audio Validation Results

| Observation | Start UTC | Station | KISS | Valid KOYO | Controls | Exact | Recovery | Result |
|---|---|---|---:|---:|---:|---:|---:|---|
| 14526577 | 2026-07-16 17:47:30 | MAUSyagi | 6 | 1 | 35 | 1 | 2.9% | PASS |
| 14637273 | 2026-07-29 23:33:14 | EA3AGB | 8 | 1 | 3 | 1 | 33.3% | PASS |
| 14909294 | 2026-08-30 16:58:25 | MAUSyagi | 32 | 14 | 31 | 14 | 45.2% | PASS |
| 14909617 | 2026-08-30 18:36:38 | W6MSU UHF | 8 | 4 | 4 | 3 | 75.0% | PASS |
| 14909703 | 2026-08-30 18:43:47 | MAUSyagi-AK | 6 | 2 | 1 | 1 | 100.0% | PASS |

The selected observations represent four receiving stations. All five passes
produced at least one valid local frame and one byte-exact control match.

Detailed evidence is available in:

- [`reports/KOYO_AUDIO_VALIDATION.md`](reports/KOYO_AUDIO_VALIDATION.md)
- [`reports/koyo_audio_validation.csv`](reports/koyo_audio_validation.csv)
- [`reports/KOYO_Real_Results.xlsx`](reports/KOYO_Real_Results.xlsx)

## Understanding Recovery Rate

For this project, exact recovery is defined as:

```text
exact recovery = byte-exact local matches / official control frames
               = 20 / 74
               = 27.0%
```

This number measures how many control frames the current fixed demodulator
configuration reproduced from the selected OGG recordings. It is not the
spacecraft packet-validity rate, spacecraft health, or total decoder accuracy.

Local recovery can be affected by receiving-station SNR, frequency offset,
Doppler, gain, filtering, recording quality, and clock recovery. A control
frame that was not recovered locally is therefore not automatically a bad
spacecraft frame.

## Historical Coverage

The broader historical dataset contains SatNOGS-demodulated frame records from
2026-07-07 through 2026-08-30:

- 17,155 frames
- 1,055 observations
- 55 UTC days with frames
- 114 receiving stations

This dataset supports time-series coverage analysis and dashboard testing. It
must not be described as 17,155 frames independently re-demodulated from OGG by
this local GNU Radio flowgraph. Direct byte-exact OGG proof currently covers
five observations.

See [`reports/KOYO_HISTORICAL_COVERAGE.md`](reports/KOYO_HISTORICAL_COVERAGE.md)
for the daily table.

## Telemetry Confidence Contract

Telemetry output is separated into three confidence states:

| State | Meaning |
|---|---|
| `CONFIRMED` | The channel interpretation has validation evidence. |
| `CANDIDATE` | Behavior is plausible, but the mapping or engineering scale still requires review. |
| `NOT DECODED` | No authorized mapping is available, so no value is produced. |

`NOT DECODED` in the dashboard does not mean that the satellite transmitted a
bad frame. It means the project does not have enough authorized information to
turn that payload region into an engineering value.

The complete dashboard layout does not imply that every telemetry field has
been decoded.

## Dashboard Evidence

The operational Grafana layout contains 43 panels covering decoder evidence,
orbit context, electrical power, battery, communications, thermal, health, OBC,
and recent values. Its 22 live Flux query targets passed the project validator.

![KOYO telemetry dashboard](presentation/koyo_full_telemetry_dashboard.png)

The public repository includes dashboard screenshots and presentation evidence,
but intentionally excludes the mapping-bearing dashboard source and private
InfluxDB ingestion implementation.

## Requirements

To open and run the public signal-processing flowgraph, install:

- GNU Radio 3.10; the included runner was generated with GNU Radio 3.10.12
- gr-satellites compatible with GNU Radio 3.10
- Python 3 from the same GNU Radio environment
- FFmpeg, when converting an authorized OGG recording to PCM WAV

Raw recordings are not included in this repository.

## Quick Start

### 1. Prepare an authorized WAV

Convert an OGG recording to mono, 48 kHz, signed 16-bit PCM:

```powershell
ffmpeg -i input.ogg -ac 1 -ar 48000 -c:a pcm_s16le input.wav
```

### 2. Configure the flowgraph

Open [`gnuradio/koyo_audio_rx.grc`](gnuradio/koyo_audio_rx.grc) in GNU Radio
Companion and set:

- `audio_file` to the prepared WAV
- `kiss_file` to the desired KISS output path

### 3. Run in GNU Radio Companion

Execute the flowgraph. Valid CRC-checked AX.25 PDUs are printed for inspection
and written to the configured KISS file.

### 4. Generate the Python runner

```powershell
grcc -o ./gnuradio/generated ./gnuradio/koyo_audio_rx.grc
python ./gnuradio/generated/koyo_audio_rx.py
```

On the validated Windows environment, the equivalent RadioConda commands are
documented in [`gnuradio/README.md`](gnuradio/README.md).

The default paths in the flowgraph refer to a local validation recording that
is intentionally absent from the public repository. Replace both file paths
before running.

## Repository Layout

```text
.
|-- README.md
|-- CONTRIBUTING.md
|-- THIRD_PARTY_NOTICES.md
|-- LICENSES/
|   `-- GPL-3.0-only.txt
|-- docs/
|   `-- PUBLICATION_GUIDE.md
|-- gnuradio/
|   |-- koyo_audio_rx.grc
|   |-- koyo_audio_rx_companion.png
|   |-- koyo_gr_satellites.yml
|   |-- README.md
|   `-- generated/
|       `-- koyo_audio_rx.py
|-- reports/
|   |-- KOYO_AUDIO_VALIDATION.md
|   |-- KOYO_HISTORICAL_COVERAGE.md
|   |-- KOYO_Real_Results.xlsx
|   |-- koyo_audio_validation.csv
|   |-- koyo_historical_coverage.csv
|   `-- koyo_historical_summary.json
`-- presentation/
    |-- KOYO_Beacon_Decoder_Final_Presentation.pptx
    |-- KOYO_Beacon_Decoder_Final_Presentation.pdf
    |-- KOYO_PRESENTATION_SCRIPT_TH_EN.md
    `-- koyo_full_telemetry_dashboard.png
```

## Reproducibility Checklist

Before reporting a new observation as PASS, record:

- SatNOGS observation ID, station, and UTC start time
- OGG and converted WAV sizes
- GNU Radio and gr-satellites versions
- demodulator parameters
- captured KISS frame count
- accepted 263-byte KOYO frame count
- same-observation control count
- byte-exact match count
- recovery percentage and any error

Do not mix historical SatNOGS controls with direct local OGG results in one
headline metric.

## Limitations

- Direct OGG validation currently covers five observations.
- Overall exact recovery with the fixed settings is 27.0%.
- SatNOGS is store-and-forward; latest does not mean continuous live RF.
- Some telemetry fields remain candidate or not decoded.
- The public repository cannot reproduce the private telemetry mapping layer or
  full Grafana deployment because those materials are outside the publication
  scope.
- Processing all available recordings would require a streaming or temporary
  file strategy to avoid retaining roughly 100 GB of expanded WAV data.

## Suggested Next Work

- Add Doppler and frequency-offset compensation.
- Sweep clock-recovery and filter parameters automatically.
- Record SNR and tuning metadata with each validation result.
- Process OGG recordings as a stream and delete temporary WAV data.
- Expand multi-station direct audio validation.
- Add regression fixtures only when they can be legally redistributed.
- Confirm additional telemetry mappings through an authorized source.

## Public Disclosure Boundary

This release intentionally excludes:

- confidential mission and operations documents
- derived private byte offsets and unauthorized telemetry mappings
- raw OGG, WAV, KISS, IQ, and frame payload files
- private correspondence and personal contact information
- credentials, local service state, and local database contents
- uplink and telecommand functionality
- unrelated spacecraft research

Read [`docs/PUBLICATION_GUIDE.md`](docs/PUBLICATION_GUIDE.md) before publishing
a modified bundle. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for contribution
rules.

## Licensing and Attribution

The generated GNU Radio runner identifies itself as GPL-3.0-only. The license
text is included at [`LICENSES/GPL-3.0-only.txt`](LICENSES/GPL-3.0-only.txt).

GNU Radio and gr-satellites are third-party dependencies and are not vendored
here. SatNOGS observation identifiers, station names, dates, and aggregate
counts require source attribution and applicable share-alike treatment.

No license is granted for reports, presentations, images, data summaries, or
the flowgraph unless the file explicitly states otherwise. Review
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) before redistribution.

## Presentation Material

The `presentation/` directory contains the final English slide deck, PDF
export, dashboard image, and a Thai/English speaker script. The recommended
presentation length is 12 to 15 minutes plus questions.

## Final Result

The project demonstrates a real and traceable path from SatNOGS OGG audio to
CRC-valid KOYO AX.25 frames, with byte-exact independent controls across four
receiving stations. The signal-decoding path is proven for the selected sample;
the remaining work is recovery optimization and authorized telemetry mapping
completion.

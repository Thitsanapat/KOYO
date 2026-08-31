# KOYO Beacon Decoder

Public project evidence for a reproducible KOYO beacon receive chain that starts
from SatNOGS OGG audio, demodulates 9600-baud FSK with GNU Radio, validates
G3RUH AX.25 frames, and presents traceable decoder results in Grafana.

## Verified Result

- Five of five selected SatNOGS observations passed the strict test.
- The local audio pipeline produced 22 valid 263-byte KOYO frames.
- Twenty frames matched same-observation SatNOGS controls byte for byte.
- Overall exact OGG recovery was 20/74 controls, or 27.0 percent.
- The operational Grafana layout contains 43 panels and 22/22 validated Flux
  query targets.

An observation passes only when local audio decoding produces at least one
CRC-valid KOYO frame and at least one byte-exact control match.

## Signal Path

```text
SatNOGS OGG
  -> mono 48 kHz PCM WAV
  -> GNU Radio 9600-baud FSK
  -> G3RUH AX.25 / HDLC / CRC
  -> KISS
  -> 263-byte KOYO frame validation
  -> telemetry evidence and dashboard
```

SatNOGS demodulated frames are independent validation controls. They are not
used as input to the local audio decoder.

## Repository Contents

- `gnuradio/koyo_audio_rx.grc`: editable GNU Radio Companion flowgraph
- `gnuradio/generated/koyo_audio_rx.py`: generated flowgraph runner
- `reports/`: audio validation and historical coverage evidence
- `reports/KOYO_Real_Results.xlsx`: formatted real-results workbook with charts
- `presentation/`: final PPTX, PDF, dashboard image, and Thai/English script
- `docs/PUBLICATION_GUIDE.md`: safe publication and repository notes
- `THIRD_PARTY_NOTICES.md`: dependency and SatNOGS data attribution

## Evidence Boundary

The historical dataset contains 17,155 SatNOGS-demodulated frames across 1,055
observations, 55 UTC days, and 114 stations. Direct OGG-to-GNU-Radio byte-exact
validation currently covers five observations. These two evidence sets are
reported separately.

SatNOGS is store-and-forward. Latest means the newest uploaded observation,
not continuous live RF.

## Telemetry Confidence

The dashboard separates three states:

- `CONFIRMED`: validated channel mapping and engineering interpretation
- `CANDIDATE`: plausible behavior, but mapping or scale still requires review
- `NOT DECODED`: no authorized mapping, so no value is fabricated

The complete dashboard layout does not imply that every telemetry field has
been decoded.

## GNU Radio Requirements

The flowgraph requires GNU Radio with gr-satellites blocks. Raw OGG/WAV files
are intentionally excluded. Supply an authorized 48 kHz mono PCM WAV and set
the `audio_file` and `kiss_file` variables in GNU Radio Companion before
running the generated flowgraph.

## Public Scope

This public bundle intentionally excludes raw mission files, downloaded audio,
local service state, confidential documents, and mapping-bearing telemetry
source. It is an evidence and signal-processing release, not the complete
private operations workspace.

The generated GNU Radio runner carries its own GPL-3.0-only notice; the
corresponding license text is included under `LICENSES/`. No license is granted
for the remaining project reports, data summaries, presentation, images, or
flowgraph unless a file explicitly says otherwise. See
`THIRD_PARTY_NOTICES.md` before redistributing any part of this repository.

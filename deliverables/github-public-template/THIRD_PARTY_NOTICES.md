# Third-Party Notices and Data Attribution

This repository contains project evidence built with, or referring to, the
following external projects and public services. Their names are used only to
identify dependencies and data provenance; no endorsement is implied.

## GNU Radio

The generated runner at `gnuradio/generated/koyo_audio_rx.py` identifies itself
as GPL-3.0-only. A copy of that license is provided at
`LICENSES/GPL-3.0-only.txt`. GNU Radio itself is distributed under GPL-3.0.

Project: https://github.com/gnuradio/gnuradio

## gr-satellites

The flowgraph calls demodulator, AX.25 deframer, and KISS sink components from
gr-satellites. The dependency is not vendored in this repository and must be
installed separately. gr-satellites is distributed under GPL-3.0-or-later.

Project: https://github.com/daniestevez/gr-satellites

## SatNOGS

Observation IDs, station names, dates, and aggregated frame counts in the
reports were derived from publicly accessible SatNOGS observations. Raw audio,
raw frames, and full observation payloads are intentionally not redistributed
here. Attribute the source as "SatNOGS, Libre Space Foundation and contributing
ground stations" and preserve applicable attribution/share-alike terms when
redistributing SatNOGS-derived data.

Project principles: https://docs.satnogs.org/en/latest/project/principles.html

SatNOGS DB API license note: https://docs.satnogs.org/projects/satnogs-db/en/stable/api.html

## Project-Owned Material

Unless a file carries an explicit license notice, no permission is granted to
reuse project reports, presentations, images, data summaries, mission names,
or telemetry interpretations. Confidential mission documents and derived byte
mappings are not part of this repository.

This notice records practical publication boundaries and is not legal advice.

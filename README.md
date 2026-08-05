# KOYO telemetry decoder + dashboard

See [CLAUDE.md](CLAUDE.md) for full project context (scope, spacecraft details,
confirmed frame layout, people, constraints). This file is just the repo map.

## Status (2026-07-30)

- `koyo.ksy` / `decode_koyo.py` / `validate.py` — the real, verified KOYO decoder.
  Confirmed against two reference observations pulled directly from the SatNOGS
  API (`14468821`, `14526577`): 263-byte AX.25 frames, `KOYOSC` -> `GS-H20`,
  `boot_counter` matches HEX20's dashboard exactly (4 on 2026-07-09, 9 on
  2026-07-16). EPS block (offsets 32-119, 134-238) is still unconfirmed — that is
  the main remaining task, see CLAUDE.md section 4.
- **Important bug found and fixed 2026-07-30**: `fetch_satnogs.py`'s
  `satellite__norad_cat_id` API filter can silently return observations for the
  wrong satellite, because norad_cat_id is a temporary ID for newly-launched
  CubeSats and SatNOGS reassigns it. A batch fetched this way turned out to be
  mostly a *different* satellite (PEARL-1B, norad 98330) plus some unrelated
  ones, not KOYO. Moved to `archive/mislabeled_non_koyo_data/`.
  `fetch_satnogs.py` now filters by the permanent `sat_id` and cross-checks
  every fetched observation against it before keeping it - see
  `filter_observations_for_satellite()`.
- Full real dataset re-fetched with the fix: 9,674 decoded frames across 412
  observations, spanning launch (2026-07-07) to now, 17 reboots. Dashboard:
  see the artifact link shared in conversation, or regenerate from
  `data/koyo/decoded/decoded.csv`.
- **KOYO local audio decode confirmed working 2026-07-30** — see CLAUDE.md
  §9b and `verify_audio_pipeline.py`. `gr_satellites`' default clock-recovery
  bandwidth is too narrow for KOYO's 263-byte frames; `--clk_bw 0.15` fixes it,
  verified byte-for-byte against SatNOGS' own decoded output.
- **EPS block: 2 of ~24 fields identified 2026-07-30** — offsets 62 and 66 are
  very likely solar panel voltage channels (see CLAUDE.md §4). Found using
  HEX20's confidential LEOP telecommand doc's health-parameter table
  (STRICTLY CONFIDENTIAL, local use only - do not publish this mapping) cross
  referenced against real frame statistics. Not yet cross-checked against a
  live dashboard reading, so still a strong candidate, not fully confirmed.

## Pipeline order

```
fetch_satnogs.py            download frames/audio/waterfalls from SatNOGS
  -> data/koyo/frames_hex/<obsid>.txt      hex frames, one per line
  -> data/koyo/index.csv                   per-observation summary

decode_koyo.py               decode frames_hex/*.txt with the confirmed fields
  -> data/koyo/decoded/decoded.csv, decoded.json, rejects.csv

analyze_satnogs_frames.py    classify raw frames by AX.25 header (diagnostic)
prepare_satnogs_observation.py   per-observation audio -> WAV, for local demod
run_koyo_grsat.ps1 / koyo_gr_satellites.yml   local gr_satellites demod, KISS out
verify_audio_pipeline.py     control test: local audio decode vs SatNOGS' own demoddata
inspect_kiss.py              inspect KISS frames from gr_satellites/Dire Wolf
validate.py                  reference parser mirroring koyo.ksy, self-test
```

## Setup

```
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
```

## archive/

- `mislabeled_non_koyo_data/` — PEARL-1B and other unrelated satellites' data
  and decoder (`koyo_pearlb.ksy`, `parse_pearlb_frames.py`,
  `infer_pearlb_offsets.py`), pulled in by the norad_cat_id filter bug above.
  Kept for reference, not part of the KOYO deliverable.
- `superseded_data/` — earlier duplicate CSVs and a raw pre-consolidation copy
  of `download/`, superseded by `data/koyo/observations/<obsid>/`.

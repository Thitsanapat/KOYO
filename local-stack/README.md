# Local Grafana + InfluxDB stack

A real local Grafana instance reading real KOYO telemetry, in response to Loren's
2026-07-21 email asking for "a Grafana interface on SatNOGS." The `dashboard/`
HTML artifact elsewhere in this repo covers the same data but is not literally
Grafana - this is. Local only, not the public `dashboard.satnogs.org` (that still
needs the decoder merged upstream, which is on hold - see `CLAUDE.md` §7).

No Docker or WSL is installed on this machine, so both InfluxDB and Grafana run
as portable Windows binaries, downloaded (not authored) into `influxdb/` and
`grafana/` - both gitignored, along with their runtime data (`influxdb-data/`,
`grafana-data/`). Everything else in this folder (`start.ps1`, `stop.ps1`,
`provisioning/`, `grafana-dashboards/`, `load_influx.py`, this README) is tracked.

## Running it

```powershell
.\start.ps1
```

Wait ~15-20s for both to finish booting, then:

- Grafana: http://localhost:3000 - login `admin` / `admin` (default, never changed
  since this only binds to localhost). Dashboard is under the "KOYO" folder.
- InfluxDB: http://localhost:8086 - org `koyo`, bucket `koyo_telemetry`, token
  `koyo-local-dev-token` (dev-only token, fine for a localhost-only service).

```powershell
.\stop.ps1
```

## Refreshing data

After `decode_koyo.py` regenerates `data/koyo/decoded/decoded.csv`, reload it:

```powershell
python local-stack/load_influx.py
python local-stack/load_events.py
```

Both idempotent - re-running with the same CSV just overwrites identical points.
`load_influx.py` writes the raw per-frame telemetry (measurement `koyo`);
`load_events.py` derives reboot and health-status-transition events from the
same CSV (boot_counter/sd_card_failure_count changes between consecutive
frames) and writes them as measurement `koyo_events`, so the reboot-timeline
and health-transitions tables don't need to re-derive diffs in Flux.

## What's in the dashboard

Mirrors the confirmed/candidate fields from `CLAUDE.md` §3-4, plus the mission
overview/event tables also shown in the `dashboard/` HTML artifact:

- **EPS Temperatures**: the 4 CONFIRMED fields (battery TH0/TH1, CDH, ADCS)
- **EPS Voltage Candidates**: 2 high-confidence solar panel voltage candidates,
  1 weaker COMM voltage candidate - none fully CONFIRMED yet, see `CLAUDE.md` §4
- **Spacecraft Health**: uptime, packet counter, boot counter, PIB health
  status, SD card failure count (offsets 258/259 - corrected 2026-08-05, was a
  decode-side field swap, not a spacecraft anomaly - see `CLAUDE.md` §3)
- **Mission Overview**: total frames decoded, distinct observations, frames
  decoded per day
- **Event Log**: reboot timeline, health-status transitions (from `koyo_events`)
- **Recent Frames**: latest 30 frames across all core fields, one row each

Panel definitions live in `grafana-dashboards/koyo_telemetry.json` and are
provisioned automatically via `provisioning/dashboards/koyo-dashboards.yaml` -
edit the JSON and Grafana picks it up within ~10s, no UI editing required
(though UI edits are also allowed and will persist back to a copy in
`grafana-data/`).

Same caveat as everywhere else in this project: the solar panel voltage and COMM
voltage fields are candidates, not CONFIRMED - see `CLAUDE.md` §4 for what
resolving them still needs (timestamp-matched readings off `koyo.hex20.space`).

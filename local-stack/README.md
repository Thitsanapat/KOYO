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
```

Idempotent - re-running with the same CSV just overwrites identical points.

## What's in the dashboard

Mirrors the confirmed/candidate fields from `CLAUDE.md` §3-4: the 4 CONFIRMED
EPS temperatures (battery TH0/TH1, CDH, ADCS), the 2 high-confidence solar panel
voltage candidates, the weaker COMM voltage candidate, uptime, packet counter,
boot counter, PIB health status, and the SD card failure count anomaly (flagged
red - documented max is 100, every real frame reads 175). Panel definitions live
in `grafana-dashboards/koyo_telemetry.json` and are provisioned automatically via
`provisioning/dashboards/koyo-dashboards.yaml` - edit the JSON and Grafana picks
it up within ~10s, no UI editing required (though UI edits are also allowed and
will persist back to a copy in `grafana-data/`).

Same caveat as everywhere else in this project: the solar panel voltage and COMM
voltage fields are candidates, not CONFIRMED - see `CLAUDE.md` §4 for what
resolving them still needs (timestamp-matched readings off `koyo.hex20.space`).

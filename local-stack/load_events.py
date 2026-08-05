"""Derives reboot and health-status-transition events from decoded.csv and
writes them into InfluxDB as a separate measurement, so Grafana can show the
same event tables the HTML dashboard shows without re-deriving them in Flux.

Run after load_influx.py, any time decoded.csv is refreshed.
"""
import csv
import urllib.request
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "koyo" / "decoded" / "decoded.csv"
INFLUX_URL = "http://localhost:8086/api/v2/write?org=koyo&bucket=koyo_telemetry&precision=s"
TOKEN = "koyo-local-dev-token"


def esc_tag(v):
    return str(v).replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")


def load_rows():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get("rtc_time_unix") and r.get("rtc_datetime")]
    rows.sort(key=lambda r: int(r["rtc_time_unix"]))
    return rows


def find_reboots(rows):
    events = []
    prev = None
    for r in rows:
        if prev is not None and r["boot_counter"] != prev["boot_counter"]:
            events.append((int(r["rtc_time_unix"]), int(r["boot_counter"]), r["obs_id"]))
        prev = r
    return events


def find_health_transitions(rows):
    events = []
    prev_val = None
    for r in rows:
        v = r.get("sd_card_failure_count")
        if v and v != prev_val:
            events.append((int(r["rtc_time_unix"]), int(v), r["obs_id"]))
            prev_val = v
    return events


def write_batch(lines):
    if not lines:
        return
    body = "\n".join(lines).encode("utf-8")
    req = urllib.request.Request(
        INFLUX_URL, data=body, method="POST",
        headers={"Authorization": f"Token {TOKEN}", "Content-Type": "text/plain; charset=utf-8"},
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status


def main():
    rows = load_rows()

    reboots = find_reboots(rows)
    health = find_health_transitions(rows)

    lines = []
    for ts, boot_counter, obs_id in reboots:
        lines.append(f"koyo_events,event_type=reboot,obs_id={esc_tag(obs_id)} boot_counter={boot_counter}i {ts}")
    for ts, sd_val, obs_id in health:
        lines.append(f"koyo_events,event_type=health_change,obs_id={esc_tag(obs_id)} sd_card_failure_count={sd_val}i {ts}")

    print(f"{len(reboots)} reboot events, {len(health)} health-transition events")
    status = write_batch(lines)
    print(f"wrote {len(lines)} events: HTTP {status}")


if __name__ == "__main__":
    main()

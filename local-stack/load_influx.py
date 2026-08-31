"""Loads data/koyo/decoded/decoded.csv into the local InfluxDB instance.

Run after every decode_koyo.py refresh to keep the Grafana dashboard current.
Requires the local stack to be running (see start.ps1).
"""
import csv
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "koyo" / "decoded" / "decoded.csv"
INFLUX_URL = "http://localhost:8086/api/v2/write?org=koyo&bucket=koyo_telemetry&precision=s"
TOKEN = "koyo-local-dev-token"

NUMERIC_FIELDS = [
    "packet_counter", "uptime_ms", "obc_time_unix",
    "comm_voltage_candidate", "sp_voltage_candidate_1", "sp_voltage_candidate_2",
    "battery_th0_temp_c", "battery_th1_temp_c", "cdh_temp_c", "adcs_temp_c",
    "boot_counter", "pib_health_status", "sd_card_failure_count",
]

# HEX-style feedback contract. Confirmed and candidate channels deliberately use
# different names so an unverified byte offset cannot be mistaken for flight
# telemetry with a known physical channel assignment.
BEACON_CHANNELS = {
    "obc_time_unix": {"channel": "Obc time", "quality": "confirmed", "unit": "epoch_s", "scale": 1.0},
    "boot_counter": {"channel": "Boot Counter", "quality": "confirmed", "unit": "count", "scale": 1.0},
    "uptime_ms": {"channel": "OBC Uptime", "quality": "confirmed", "unit": "ms", "scale": 1.0},
    "packet_counter": {"channel": "Beacon Packet Counter", "quality": "confirmed", "unit": "count", "scale": 1.0},
    "battery_th0_temp_c": {"channel": "BatteryTH0_Temp", "quality": "confirmed", "unit": "degC", "scale": 1.0},
    "battery_th1_temp_c": {"channel": "BatteryTH1_Temp", "quality": "confirmed", "unit": "degC", "scale": 1.0},
    "cdh_temp_c": {"channel": "Cdh_Temp", "quality": "confirmed", "unit": "degC", "scale": 1.0},
    "adcs_temp_c": {"channel": "Adcs_Temp", "quality": "confirmed", "unit": "degC", "scale": 1.0},
    "pib_health_status": {"channel": "PIB Health Status", "quality": "confirmed", "unit": "code", "scale": 1.0},
    "sd_card_failure_count": {"channel": "SD Card Failure Count", "quality": "confirmed", "unit": "count", "scale": 1.0},
    "sp_voltage_candidate_1": {"channel": "Pv Voltage candidate 1", "quality": "candidate", "unit": "V", "scale": 0.001},
    "sp_voltage_candidate_2": {"channel": "Pv Voltage candidate 2", "quality": "candidate", "unit": "V", "scale": 0.001},
    "comm_voltage_candidate": {"channel": "Comm Voltage candidate raw", "quality": "candidate", "unit": "raw", "scale": 1.0},
}


def esc_tag(v):
    return str(v).replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")


def esc_string(v):
    return str(v).replace("\\", "\\\\").replace('"', '\\"')


def is_blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def beacon_values(row):
    for field, spec in BEACON_CHANNELS.items():
        raw = row.get(field, "")
        if is_blank(raw):
            continue
        try:
            value = float(raw) * spec["scale"]
        except (TypeError, ValueError):
            continue
        yield spec, value


def build_lines(rows):
    lines = []
    for row in rows:
        ts = row.get("rtc_time_unix")
        if is_blank(ts):
            continue
        try:
            ts_i = int(float(ts))
        except (TypeError, ValueError):
            continue

        fields = []
        for f in NUMERIC_FIELDS:
            v = row.get(f, "")
            if is_blank(v):
                continue
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            fields.append(f"{f}={fv}")
        if not fields:
            continue

        obs_tag = esc_tag(row.get("obs_id", "unknown"))
        line = f"koyo,obs_id={obs_tag} " + ",".join(fields) + f" {ts_i}"
        lines.append(line)

        for spec, value in beacon_values(row):
            channel = esc_tag(spec["channel"])
            quality = esc_tag(spec["quality"])
            unit = esc_tag(spec["unit"])
            lines.append(
                f"beacon,channel={channel},quality={quality},unit={unit},"
                f"source=satnogs,obs_id={obs_tag} value={value} {ts_i}"
            )
    return lines


def build_decoder_run_line(result):
    """Build one operational decoder-status point from a live decode result."""
    telemetry = result.get("telemetry") or []
    latest = telemetry[-1] if telemetry else {}
    timestamp = latest.get("rtc_time_unix")
    if is_blank(timestamp):
        observation_start = result.get("observation_start")
        try:
            timestamp = int(datetime.fromisoformat(observation_start.replace("Z", "+00:00")).timestamp())
        except (AttributeError, TypeError, ValueError):
            timestamp = int(datetime.now(timezone.utc).timestamp())
    timestamp = int(float(timestamp))

    captured = int(result.get("captured_kiss_frames", 0))
    valid = int(result.get("valid_koyo_frames", 0))
    official = int(result.get("official_control_frames", 0))
    exact = int(result.get("byte_exact_control_matches", 0))
    rejected = int(result.get("rejected_non_koyo_263_frames", 0))
    recovery = exact * 100.0 / official if official else 0.0
    if exact:
        status = "PASS"
        status_code = 1
    elif valid and not official:
        status = "LOCAL ONLY"
        status_code = 2
    elif valid:
        status = "NO MATCH"
        status_code = 3
    else:
        status = "NO FRAME"
        status_code = 0

    obs_id = str(result.get("observation_id", "unknown"))
    try:
        obs_id_number = int(obs_id)
    except ValueError:
        obs_id_number = 0
    station = str(result.get("station") or "unknown")
    frame_hex = str(latest.get("frame_hex") or "")
    fields = [
        f'decoder_status="{esc_string(status)}"',
        f"decoder_status_code={status_code}i",
        f'observation_id="{esc_string(obs_id)}"',
        f"observation_id_number={obs_id_number}i",
        f'station_name="{esc_string(station)}"',
        f"captured_kiss_frames={captured}i",
        f"valid_koyo_frames={valid}i",
        f"official_control_frames={official}i",
        f"byte_exact_matches={exact}i",
        f"rejected_non_koyo_frames={rejected}i",
        f"recovery_rate_percent={recovery}",
        f'latest_frame_hex="{esc_string(frame_hex)}"',
    ]
    return (
        f"decoder_run,obs_id={esc_tag(obs_id)},station={esc_tag(station)},source=satnogs "
        + ",".join(fields)
        + f" {timestamp}"
    )


def write_batch(lines):
    body = "\n".join(lines).encode("utf-8")
    req = urllib.request.Request(
        INFLUX_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Token {TOKEN}",
            "Content-Type": "text/plain; charset=utf-8",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status


def main():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    lines = build_lines(rows)
    print(
        f"Built {len(lines)} line-protocol points from {len(rows)} CSV rows "
        "(native koyo + HEX-style beacon channels)"
    )

    batch_size = 2000
    for i in range(0, len(lines), batch_size):
        batch = lines[i:i + batch_size]
        status = write_batch(batch)
        print(f"  wrote rows {i}-{i+len(batch)}: HTTP {status}")

    print("done")


if __name__ == "__main__":
    main()

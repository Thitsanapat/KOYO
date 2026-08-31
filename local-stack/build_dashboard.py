#!/usr/bin/env python3
"""Generate the provisioned KOYO Grafana dashboard."""

import json
from pathlib import Path


OUTPUT = Path(__file__).resolve().parent / "grafana-dashboards" / "koyo_telemetry.json"
DS = {"type": "influxdb", "uid": "koyo-influxdb"}
COLORS = ["green", "yellow", "blue", "red", "orange", "purple"]


def query(channel, label, *, latest=False, milliseconds=False):
    range_expr = "|> range(start: -400d)" if latest else "|> range(start: v.timeRangeStart, stop: v.timeRangeStop)"
    lines = [
        'from(bucket: "koyo_telemetry")',
        f"  {range_expr}",
        f'  |> filter(fn: (r) => r._measurement == "beacon" and r.channel == {json.dumps(channel)})',
        '  |> filter(fn: (r) => r._field == "value")',
        '  |> group(columns: ["channel"])',
    ]
    if not latest:
        lines.append("  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)")
    lines.append('  |> sort(columns: ["_time"])')
    if latest:
        lines.append("  |> last()")
    if milliseconds:
        lines.append("  |> map(fn: (r) => ({r with _value: float(v: r._value) * 1000.0}))")
    lines.extend(
        [
            '  |> keep(columns: ["_time", "_value"])',
            f"  |> rename(columns: {{_value: {json.dumps(label)}}})",
        ]
    )
    return "\n".join(lines)


def target(ref_id, channel, label, **kwargs):
    return {"refId": ref_id, "datasource": DS, "query": query(channel, label, **kwargs)}


def decoder_query(field, label):
    return "\n".join(
        [
            'from(bucket: "koyo_telemetry")',
            "  |> range(start: -400d)",
            f'  |> filter(fn: (r) => r._measurement == "decoder_run" and r._field == {json.dumps(field)})',
            "  |> group()",
            '  |> sort(columns: ["_time"])',
            "  |> last()",
            '  |> keep(columns: ["_time", "_value"])',
            f"  |> rename(columns: {{_value: {json.dumps(label)}}})",
        ]
    )


def decoder_target(ref_id, field, label):
    return {"refId": ref_id, "datasource": DS, "query": decoder_query(field, label)}


def row(panel_id, title, y):
    return {
        "type": "row",
        "title": title,
        "id": panel_id,
        "gridPos": {"x": 0, "y": y, "w": 24, "h": 1},
        "collapsed": False,
        "panels": [],
    }


def stat(panel_id, title, x, y, w, channel, *, unit="none", color="green", milliseconds=False):
    return {
        "type": "stat",
        "title": title,
        "id": panel_id,
        "gridPos": {"x": x, "y": y, "w": w, "h": 5},
        "datasource": DS,
        "targets": [target("A", channel, title, latest=True, milliseconds=milliseconds)],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "color": {"mode": "fixed", "fixedColor": color},
                "thresholds": {"mode": "absolute", "steps": [{"color": color, "value": None}]},
            },
            "overrides": [],
        },
        "options": {
            "colorMode": "value",
            "graphMode": "area",
            "justifyMode": "auto",
            "orientation": "horizontal",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "textMode": "auto",
            "wideLayout": True,
        },
    }


def gauge(panel_id, title, x, y, w, channel, *, unit, minimum, maximum, color="blue"):
    return {
        "type": "gauge",
        "title": title,
        "id": panel_id,
        "gridPos": {"x": x, "y": y, "w": w, "h": 5},
        "datasource": DS,
        "targets": [target("A", channel, title, latest=True)],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "min": minimum,
                "max": maximum,
                "color": {"mode": "fixed", "fixedColor": color},
                "thresholds": {"mode": "absolute", "steps": [{"color": color, "value": None}]},
            },
            "overrides": [],
        },
        "options": {
            "orientation": "auto",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "showThresholdLabels": False,
            "showThresholdMarkers": True,
            "sizing": "auto",
        },
    }


def timeseries(panel_id, title, x, y, w, h, series, *, unit="none", description=""):
    targets = [target(chr(65 + i), channel, label) for i, (channel, label) in enumerate(series)]
    overrides = []
    for i, (_, label) in enumerate(series):
        overrides.append(
            {
                "matcher": {"id": "byName", "options": label},
                "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": COLORS[i % len(COLORS)]}}],
            }
        )
    return {
        "type": "timeseries",
        "title": title,
        "id": panel_id,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "datasource": DS,
        "targets": targets,
        "description": description,
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "custom": {
                    "drawStyle": "line",
                    "lineInterpolation": "linear",
                    "lineWidth": 2,
                    "fillOpacity": 8,
                    "showPoints": "never",
                    "pointSize": 4,
                    "spanNulls": False,
                    "stacking": {"mode": "none", "group": "A"},
                    "axisPlacement": "auto",
                    "scaleDistribution": {"type": "linear"},
                    "thresholdsStyle": {"mode": "off"},
                },
            },
            "overrides": overrides,
        },
        "options": {
            "tooltip": {"mode": "multi", "sort": "none"},
            "legend": {
                "displayMode": "table",
                "placement": "bottom",
                "calcs": ["lastNotNull", "min", "max"],
                "showLegend": True,
            },
        },
    }


def note(panel_id, title, x, y, w, h, content):
    return {
        "type": "text",
        "title": title,
        "id": panel_id,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "options": {"mode": "markdown", "content": content},
    }


def unavailable(panel_id, title, x, y, w, h=5, detail="MAPPING REQUIRED"):
    content = f"""<div style="height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center">
<div style="font:600 22px/1.1 Inter,Arial;color:#ff9830">NOT DECODED</div>
<div style="margin-top:9px;font:600 10px/1.2 Inter,Arial;color:#8b8b98;letter-spacing:0">{detail}</div>
</div>"""
    return {
        "type": "text",
        "title": title,
        "id": panel_id,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "transparent": False,
        "options": {"mode": "html", "content": content},
    }


def decoder_stat(panel_id, title, x, y, w, field, *, unit="none", color="green", mappings=None):
    return {
        "type": "stat",
        "title": title,
        "id": panel_id,
        "gridPos": {"x": x, "y": y, "w": w, "h": 5},
        "datasource": DS,
        "targets": [decoder_target("A", field, title)],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "color": {"mode": "fixed", "fixedColor": color},
                "thresholds": {"mode": "absolute", "steps": [{"color": color, "value": None}]},
                "mappings": mappings or [],
            },
            "overrides": [],
        },
        "options": {
            "colorMode": "value",
            "graphMode": "none",
            "justifyMode": "center",
            "orientation": "horizontal",
            "reduceOptions": {"calcs": [], "fields": "", "values": True},
            "textMode": "value",
            "wideLayout": True,
        },
    }


def decoder_text_table(panel_id, title, x, y, w, field):
    return {
        "type": "table",
        "title": title,
        "id": panel_id,
        "gridPos": {"x": x, "y": y, "w": w, "h": 5},
        "datasource": DS,
        "targets": [decoder_target("A", field, title)],
        "fieldConfig": {
            "defaults": {"custom": {"align": "center", "cellOptions": {"type": "auto"}}},
            "overrides": [],
        },
        "options": {"showHeader": False, "cellHeight": "lg"},
    }


def decoder_hex_table(panel_id, y):
    flux = "\n".join(
        [
            'from(bucket: "koyo_telemetry")',
            "  |> range(start: -400d)",
            '  |> filter(fn: (r) => r._measurement == "decoder_run" and r._field == "latest_frame_hex")',
            "  |> group()",
            '  |> sort(columns: ["_time"])',
            "  |> last()",
            '  |> keep(columns: ["_time", "obs_id", "station", "_value"])',
            '  |> rename(columns: {_value: "CRC-valid frame HEX", obs_id: "Observation", station: "Station"})',
        ]
    )
    return {
        "type": "table",
        "title": "Latest CRC-Valid Raw Frame HEX",
        "id": panel_id,
        "gridPos": {"x": 0, "y": y, "w": 24, "h": 6},
        "datasource": DS,
        "targets": [{"refId": "A", "datasource": DS, "query": flux}],
        "fieldConfig": {
            "defaults": {"custom": {"cellOptions": {"type": "auto"}}},
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": "CRC-valid frame HEX"},
                    "properties": [{"id": "custom.width", "value": 1100}],
                }
            ],
        },
        "options": {"showHeader": True, "cellHeight": "sm"},
    }


def orbit(panel_id, y):
    content = """<style>
body.app-grafana{background:#09090b!important}
.react-grid-item>div{background:#131318!important;border:1px solid #292934!important;border-radius:4px!important}
.react-grid-item:has([data-testid^=\"data-testid dashboard-row-title\"])>div{background:transparent!important;border:0!important}
[data-testid^=\"data-testid dashboard-row-title\"]{font-size:15px!important;font-weight:600!important;text-transform:uppercase;color:#b7b7c2!important;letter-spacing:0!important}
.panel-title,.panel-header h2,[data-testid^=\"data-testid Panel header\"] h2{font-size:11px!important;font-weight:600!important;text-transform:uppercase!important;color:#8b8b98!important;letter-spacing:0!important}
.react-grid-item:has(.koyo-orbit) .panel-content{padding:0!important;position:relative}
.koyo-orbit{position:absolute;inset:0;background:#050507;overflow:hidden}
.koyo-orbit iframe{position:absolute;inset:0;width:100%;height:100%;border:0;display:block}
.react-grid-item:not(.react-grid-item--fullscreen) .koyo-orbit iframe{pointer-events:none}
</style>
<div class=\"koyo-orbit\"><iframe src=\"http://100.56.85.37:8790/?embed=1&amp;track=1\" title=\"KOYO live 3D orbit\" loading=\"eager\" referrerpolicy=\"no-referrer\"></iframe></div>"""
    return {
        "type": "text",
        "title": "Live Orbit - KOYO",
        "id": panel_id,
        "gridPos": {"x": 0, "y": y, "w": 24, "h": 16},
        "transparent": False,
        "options": {"mode": "html", "content": content},
    }


def table(panel_id, title, y):
    flux = "\n".join(
        [
            'from(bucket: "koyo_telemetry")',
            "  |> range(start: -7d)",
            '  |> filter(fn: (r) => r._measurement == "beacon" and r._field == "value")',
            "  |> group()",
            '  |> sort(columns: ["_time"], desc: true)',
            "  |> limit(n: 100)",
            '  |> keep(columns: ["_time", "channel", "_value", "unit", "quality", "obs_id"])',
            '  |> rename(columns: {_value: "value"})',
        ]
    )
    return {
        "type": "table",
        "title": title,
        "id": panel_id,
        "gridPos": {"x": 0, "y": y, "w": 24, "h": 10},
        "datasource": DS,
        "targets": [{"refId": "A", "datasource": DS, "query": flux}],
        "fieldConfig": {"defaults": {}, "overrides": []},
        "options": {"showHeader": True, "cellHeight": "sm", "sortBy": [{"displayName": "Time", "desc": True}]},
    }


def build():
    panels = [
        stat(1, "Latest Measurement (UTC)", 0, 0, 6, "Obc time", unit="dateTimeAsIso", color="blue", milliseconds=True),
        unavailable(2, "Spacecraft Mode", 6, 0, 4, detail="MODE FIELD NOT MAPPED"),
        stat(3, "Boot Counter", 10, 0, 4, "Boot Counter", color="green"),
        unavailable(4, "Battery Voltage", 14, 0, 5, detail="VOLTAGE FIELD NOT MAPPED"),
        unavailable(5, "Battery Current", 19, 0, 5, detail="CURRENT FIELD NOT MAPPED"),
        row(100, "Orbit", 5),
        orbit(6, 6),
        row(110, "Beacon Decoder Status", 22),
        decoder_stat(
            17,
            "Decoder Status",
            0,
            23,
            4,
            "decoder_status_code",
            color="green",
            mappings=[
                {
                    "type": "value",
                    "options": {
                        "0": {"text": "NO FRAME", "color": "red", "index": 0},
                        "1": {"text": "PASS", "color": "green", "index": 1},
                        "2": {"text": "LOCAL ONLY", "color": "yellow", "index": 2},
                        "3": {"text": "NO MATCH", "color": "orange", "index": 3},
                    },
                }
            ],
        ),
        decoder_stat(18, "Observation", 4, 23, 4, "observation_id_number", color="blue"),
        decoder_text_table(19, "Station", 8, 23, 4, "station_name"),
        decoder_stat(20, "Captured KISS", 12, 23, 3, "captured_kiss_frames", color="purple"),
        decoder_stat(21, "Valid KOYO", 15, 23, 3, "valid_koyo_frames", color="green"),
        decoder_stat(22, "Exact Matches", 18, 23, 3, "byte_exact_matches", color="orange"),
        decoder_stat(23, "Recovery", 21, 23, 3, "recovery_rate_percent", unit="percent", color="yellow"),
        decoder_hex_table(24, 28),
        row(101, "Electrical Power - Solar Arrays", 34),
        timeseries(
            7,
            "Solar Panel Voltages - 2/4 Candidate",
            0,
            35,
            8,
            9,
            [("Pv Voltage candidate 1", "PV candidate 1"), ("Pv Voltage candidate 2", "PV candidate 2")],
            unit="volt",
            description="Two voltage-like values are available; panel assignments remain unconfirmed.",
        ),
        unavailable(25, "Solar Panel Currents", 8, 35, 8, 9, "0/4 CHANNELS MAPPED"),
        unavailable(26, "Solar Panel Temperatures", 16, 35, 8, 9, "0/4 CHANNELS MAPPED"),
        row(102, "Battery", 44),
        timeseries(
            8,
            "Battery Temperatures",
            0,
            45,
            6,
            9,
            [("BatteryTH0_Temp", "TH0"), ("BatteryTH1_Temp", "TH1")],
            unit="celsius",
            description="Confirmed decoded temperatures derived from KOYO beacon frames.",
        ),
        unavailable(27, "Battery Charge Voltage", 6, 45, 6, 9, "VOLTAGE FIELD NOT MAPPED"),
        unavailable(28, "Battery Heater Voltage", 12, 45, 6, 9, "VOLTAGE FIELD NOT MAPPED"),
        unavailable(29, "Battery Heater Current", 18, 45, 6, 9, "CURRENT FIELD NOT MAPPED"),
        row(103, "Power Distribution", 54),
        unavailable(30, "Load & Battery Charge Current", 0, 55, 8, 9, "CHARGE / LOAD NOT MAPPED"),
        unavailable(31, "CDH Current", 8, 55, 8, 9, "CURRENT FIELD NOT MAPPED"),
        unavailable(32, "CDH Voltage", 16, 55, 8, 9, "VOLTAGE FIELD NOT MAPPED"),
        row(104, "Comms & Interface", 64),
        unavailable(33, "COMM Current", 0, 65, 8, 9, "CURRENT FIELD NOT MAPPED"),
        timeseries(
            10,
            "COMM Voltage - Raw Candidate",
            8,
            65,
            8,
            9,
            [("Comm Voltage candidate raw", "COMM raw ADC")],
            description="Candidate only. Engineering-unit scale is not validated.",
        ),
        unavailable(34, "IF Card MCU Current", 16, 65, 8, 9, "CURRENT FIELD NOT MAPPED"),
        row(105, "Thermal & Health", 74),
        timeseries(
            9,
            "Subsystem Temperatures",
            0,
            75,
            12,
            9,
            [("Cdh_Temp", "CDH"), ("Adcs_Temp", "ADCS")],
            unit="celsius",
        ),
        stat(11, "PIB Health Status", 12, 75, 6, "PIB Health Status", color="blue"),
        stat(12, "SD Card Failure Count", 18, 75, 6, "SD Card Failure Count", color="red"),
        note(
            13,
            "Channel Confidence",
            12,
            80,
            12,
            4,
            "**Confirmed:** OBC, temperatures, and health counters.  \n**Candidate:** two PV voltages and raw COMM voltage.  \n**Unavailable:** shown as NOT DECODED, never fabricated.",
        ),
        row(106, "OBC & Beacon", 84),
        timeseries(14, "OBC Uptime", 0, 85, 12, 9, [("OBC Uptime", "Uptime")], unit="ms"),
        timeseries(15, "Beacon Packet Counter", 12, 85, 12, 9, [("Beacon Packet Counter", "Packet Counter")]),
        row(107, "Recent Channel Values", 94),
        table(16, "Recent Channel Values", 95),
    ]
    return {
        "title": "KOYO Satellite Telemetry",
        "uid": "koyo-telemetry",
        "schemaVersion": 39,
        "version": 20,
        "editable": True,
        "timezone": "utc",
        "time": {"from": "2026-07-07T00:00:00.000Z", "to": "now"},
        "refresh": "30s",
        "tags": ["koyo", "satnogs", "beacon"],
        "annotations": {"list": []},
        "templating": {"list": []},
        "panels": panels,
    }


def main():
    OUTPUT.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()

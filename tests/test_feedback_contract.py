import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local-stack"))

from load_influx import BEACON_CHANNELS, beacon_values, build_decoder_run_line, build_lines  # noqa: E402


class FeedbackContractTests(unittest.TestCase):
    def setUp(self):
        self.row = {
            "obs_id": "14903011",
            "rtc_time_unix": "1788092432",
            "obc_time_unix": "1788092448",
            "boot_counter": "22",
            "uptime_ms": "15641181",
            "packet_counter": "57227",
            "battery_th0_temp_c": "6.402",
            "battery_th1_temp_c": "6.504",
            "cdh_temp_c": "12.09",
            "adcs_temp_c": "12.653",
            "pib_health_status": "175",
            "sd_card_failure_count": "65",
            "sp_voltage_candidate_1": "16875",
            "sp_voltage_candidate_2": "16846",
            "comm_voltage_candidate": "676",
        }

    def test_contract_separates_confirmed_and_candidate_channels(self):
        values = {spec["channel"]: (spec, value) for spec, value in beacon_values(self.row)}

        self.assertEqual(len(values), 13)
        self.assertEqual(values["BatteryTH0_Temp"][0]["quality"], "confirmed")
        self.assertEqual(values["BatteryTH0_Temp"][1], 6.402)
        self.assertEqual(values["Pv Voltage candidate 1"][0]["quality"], "candidate")
        self.assertAlmostEqual(values["Pv Voltage candidate 1"][1], 16.875)
        self.assertEqual(values["Comm Voltage candidate raw"][1], 676.0)

    def test_line_protocol_uses_beacon_channel_value_shape(self):
        lines = build_lines([self.row])

        self.assertEqual(len(lines), 1 + len(BEACON_CHANNELS))
        self.assertTrue(lines[0].startswith("koyo,obs_id=14903011 "))
        self.assertIn(
            "beacon,channel=Boot\\ Counter,quality=confirmed,unit=count,"
            "source=satnogs,obs_id=14903011 value=22.0 1788092432",
            lines,
        )

    def test_live_decoder_numeric_values_are_supported(self):
        live_row = {
            key: float(value) if "." in value else int(value)
            for key, value in self.row.items()
            if key != "obs_id"
        }
        live_row["obs_id"] = self.row["obs_id"]

        lines = build_lines([live_row])

        self.assertEqual(len(lines), 1 + len(BEACON_CHANNELS))
        self.assertTrue(lines[0].endswith(" 1788092432"))

    def test_decoder_run_line_contains_status_metrics_and_raw_hex(self):
        result = {
            "observation_id": "14909703",
            "observation_start": "2026-08-30T18:43:47Z",
            "station": "MAUSyagi-AK",
            "captured_kiss_frames": 6,
            "valid_koyo_frames": 2,
            "official_control_frames": 1,
            "byte_exact_control_matches": 1,
            "rejected_non_koyo_263_frames": 0,
            "telemetry": [{"rtc_time_unix": 1788114877, "frame_hex": "8ea65a90"}],
        }

        line = build_decoder_run_line(result)

        self.assertTrue(line.startswith("decoder_run,obs_id=14909703,station=MAUSyagi-AK,source=satnogs "))
        self.assertIn('decoder_status="PASS"', line)
        self.assertIn("decoder_status_code=1i", line)
        self.assertIn("observation_id_number=14909703i", line)
        self.assertIn("recovery_rate_percent=100.0", line)
        self.assertIn('latest_frame_hex="8ea65a90"', line)
        self.assertTrue(line.endswith(" 1788114877"))


if __name__ == "__main__":
    unittest.main()

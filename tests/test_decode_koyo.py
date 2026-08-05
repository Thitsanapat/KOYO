import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from decode_koyo import decode_frame


class DecodeKoyoTests(unittest.TestCase):
    def test_decode_frame_extracts_core_fields(self):
        frame = bytearray(263)
        struct.pack_into(">H", frame, 18, 7)
        struct.pack_into("<I", frame, 24, 123456)
        struct.pack_into("<I", frame, 28, 1700000000)
        struct.pack_into("<I", frame, 130, 42)
        struct.pack_into("<I", frame, 239, 1740000000)
        frame[249] = 12
        frame[250] = 34
        frame[251] = 56
        frame[252] = 7
        frame[253] = 8
        frame[254] = 16
        frame[255] = 7
        struct.pack_into("<H", frame, 256, 2026)
        struct.pack_into("<H", frame, 256, 2026)
        frame[258] = 65
        frame[259] = 175

        parsed = decode_frame(frame)

        self.assertEqual(parsed["packet_counter"], 7)
        self.assertEqual(parsed["uptime_ms"], 123456)
        self.assertEqual(parsed["obc_time_unix"], 1700000000)
        self.assertEqual(parsed["boot_counter"], 42)
        self.assertEqual(parsed["rtc_time_unix"], 1740000000)
        self.assertEqual(parsed["rtc_year"], 2026)
        self.assertEqual(parsed["pib_health_status"], 65)
        self.assertEqual(parsed["sd_card_failure_count"], 175)
        self.assertEqual(parsed["rtc_datetime"].year, 2026)


if __name__ == "__main__":
    unittest.main()

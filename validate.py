#!/usr/bin/env python3
"""Reference parser mirroring koyo.ksy - validates layout against real frames."""
import struct, datetime

def parse(f):
    assert len(f) == 263, f"expected 263 bytes, got {len(f)}"
    d = {}
    d['dest'] = ''.join(chr(b >> 1) for b in f[0:6]).strip()
    d['src']  = ''.join(chr(b >> 1) for b in f[7:13]).strip()
    d['ctl'], d['pid'] = f[14], f[15]
    d['packet_counter'] = struct.unpack_from(">H", f, 18)[0]
    d['uptime_ms']      = struct.unpack_from("<I", f, 24)[0]
    d['obc_time_unix']  = struct.unpack_from("<I", f, 28)[0]
    d['thr_safe_to_phoenix'], d['thr_7500'], d['thr_phoenix_to_safe'], d['thr_safe_to_nominal'] = \
        struct.unpack_from("<4H", f, 120)
    d['boot_counter']   = struct.unpack_from("<I", f, 130)[0]
    d['rtc_time_unix']  = struct.unpack_from("<I", f, 239)[0]
    (d['rtc_100th'], d['rtc_sec'], d['rtc_min'], d['rtc_hour'],
     d['rtc_day'], d['rtc_date'], d['rtc_month']) = struct.unpack_from("<7B", f, 249)
    d['rtc_year'] = struct.unpack_from("<H", f, 256)[0]
    d['pib_health'] = f[258]
    d['sd_fail']    = f[259]
    return d

def ts(v):
    if v == 0 or v < 1600000000: return f"{v} (INVALID)"
    return datetime.datetime.fromtimestamp(v, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

exec(open('analyze2.py').read().split('print("=== TAIL')[0])

for label, f in all_f:
    d = parse(f)
    print(f"\n{'='*58}\nFrame received {label} UTC\n{'='*58}")
    print(f"  AX.25          {d['src']} -> {d['dest']}   ctl=0x{d['ctl']:02X} pid=0x{d['pid']:02X}")
    print(f"  packet_counter {d['packet_counter']}")
    print(f"  uptime         {d['uptime_ms']} ms  ({d['uptime_ms']/3600000:.2f} h since boot)")
    print(f"  obc_time       {ts(d['obc_time_unix'])}")
    print(f"  boot_counter   {d['boot_counter']}")
    print(f"  thresholds     phoenix<{d['thr_safe_to_phoenix']}  ?={d['thr_7500']}  "
          f"safe>{d['thr_phoenix_to_safe']}  nominal>{d['thr_safe_to_nominal']}  (mV)")
    print(f"  rtc_time       {ts(d['rtc_time_unix'])}")
    print(f"  rtc_clock      {d['rtc_year']}-{d['rtc_month']:02d}-{d['rtc_date']:02d} "
          f"{d['rtc_hour']:02d}:{d['rtc_min']:02d}:{d['rtc_sec']:02d}.{d['rtc_100th']:02d}  (weekday {d['rtc_day']})")
    if d['rtc_time_unix'] > 1600000000:
        utc = datetime.datetime.fromtimestamp(d['rtc_time_unix'], datetime.timezone.utc)
        off = (d['rtc_hour']*3600 + d['rtc_min']*60) - (utc.hour*3600 + utc.minute*60)
        print(f"                 -> broken-down clock is UTC{off/3600:+.1f} h")
    print(f"  pib_health     {d['pib_health']}")
    print(f"  sd_fail_count  {d['sd_fail']}")

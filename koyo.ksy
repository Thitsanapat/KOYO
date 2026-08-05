meta:
  id: koyo
  title: KOYO
  endian: le
  license: CC0-1.0
  ks-version: 0.9

doc: |
  :field dest_callsign: ax25_header.dest_callsign
  :field src_callsign: ax25_header.src_callsign
  :field uptime_ms: payload.uptime_ms
  :field obc_time_unix: payload.obc_time_unix
  :field boot_counter: payload.boot_counter
  :field rtc_time_unix: payload.rtc_time_unix
  :field rtc_year: payload.rtc_year
  :field rtc_month: payload.rtc_month
  :field rtc_date: payload.rtc_date
  :field pib_health_status: payload.pib_health_status
  :field sd_card_failure_count: payload.sd_card_failure_count
  :field battery_th0_temp_c: payload.battery_th0_temp_c
  :field battery_th1_temp_c: payload.battery_th1_temp_c
  :field cdh_temp_c: payload.cdh_temp_c
  :field adcs_temp_c: payload.adcs_temp_c

doc-ref: |
  KOYO (NORAD 98273), HEX20 / National Central University.
  Downlink: 435.400 MHz, FSK 9600 baud, AX.25 UI frames, 263 bytes total.
  Beacon interval 10000 ms.
  WORK IN PROGRESS - field offsets marked "unknown" pending ICD from HEX20.

seq:
  - id: ax25_header
    type: ax25_header_t
    size: 16
  - id: payload
    type: beacon_t
    size-eos: true

types:

  ax25_header_t:
    seq:
      - id: dest_callsign_raw
        type: callsign_raw
      - id: dest_ssid_raw
        type: u1
      - id: src_callsign_raw
        type: callsign_raw
      - id: src_ssid_raw
        type: u1
      - id: ctl
        type: u1
        doc: 0x03 = UI frame
      - id: pid
        type: u1
        doc: 0xF0 = no layer 3 protocol
    instances:
      dest_callsign:
        value: dest_callsign_raw.callsign_ror.callsign
      src_callsign:
        value: src_callsign_raw.callsign_ror.callsign
      dest_ssid:
        value: (dest_ssid_raw & 0x1e) >> 1
      src_ssid:
        value: (src_ssid_raw & 0x1e) >> 1

  callsign_raw:
    seq:
      - id: callsign_ror
        process: ror(1)
        size: 6
        type: callsign

  callsign:
    seq:
      - id: callsign
        type: str
        encoding: ASCII
        size: 6
        valid:
          any-of:
            - '"KOYOSC"'
            - '"GS-H20"'

  beacon_t:
    seq:
      # ---- offset 16 ----
      - id: magic
        contents: [0x08, 0x01]
        doc: constant across all observed frames

      # ---- offset 18 ----
      - id: packet_counter
        type: u2be
        doc: |
          CONFIRMED behaviour: increments by 1 every beacon (10 s).
          Big-endian (unusual vs rest of frame) - verify with ICD.

      # ---- offset 20 ----
      - id: unknown_20
        size: 4
        doc: byte 21 constant 0xEB. TODO

      # ---- offset 24 ----
      - id: uptime_ms
        type: u4
        doc: |
          CONFIRMED: increments ~10000 per beacon.
          Cross-checked against RTC delta (102 s -> 103241 ms). Resets on boot.

      # ---- offset 28 ----
      - id: obc_time_unix
        type: u4
        doc: |
          CONFIRMED: OBC time, Unix epoch seconds, UTC.
          2026-07-09: uninitialised (2025-07-27). 2026-07-16: valid.
          -> evidence that CaliberateObcWithRtc (0x24) was executed.

      # ---- offset 32 ----
      - id: unknown_32
        size: 18
        doc: |
          TODO. Part of EPS block. Offsets unknown.

      # ---- offset 50 ----
      - id: comm_voltage_candidate
        type: u2
        doc: |
          UNCONFIRMED, weaker candidate than the sp_voltage ones. 2026-07-30:
          across 9,578 valid post-launch frames reads 676 constant (cv=0.0002,
          essentially a flat line) - matches the *shape* of COMM Voltage on
          HEX20's live dashboard (also a flat line, ~6V), but the scale factor
          to get from raw 676 to ~6V isn't a clean /1000 (mV) like the SP
          voltage fields - would need /100ish, unconfirmed. Not cross-checked
          against a specific timestamp-matched dashboard reading.

      # ---- offset 52 ----
      - id: unknown_52
        size: 10
        doc: TODO. Part of EPS block.

      # ---- offset 62 ----
      - id: sp_voltage_candidate_1
        type: u2
        doc: |
          UNCONFIRMED candidate: solar panel voltage (mV), one of SP
          YPlus/XPlus/YNegative/XNegative per HEX20 health-parameter spec
          (documented range 15-17V). 2026-07-30: across 9,578 valid
          post-launch frames, reads 16486-17103 (16.49-17.10V), extremely
          stable (coefficient of variation 0.005) - fits the documented
          range almost exactly. Not yet cross-checked against a live
          dashboard reading at a matching timestamp, so still a candidate,
          not confirmed. Which of the four SP channels this is is unknown.

      # ---- offset 64 ----
      - id: unknown_64
        size: 2
        doc: TODO. Part of EPS block.

      # ---- offset 66 ----
      - id: sp_voltage_candidate_2
        type: u2
        doc: |
          UNCONFIRMED candidate, same basis as sp_voltage_candidate_1.
          2026-07-30: reads 16517-17083 (16.52-17.08V), cv 0.005.

      # ---- offset 68 ----
      - id: unknown_68
        size: 12
        doc: TODO. Part of EPS block.

      # ---- offset 80 ----
      - id: battery_th0_raw
        type: u2
        doc: |
          CONFIRMED 2026-07-30: raw ADC for battery_th0_temp_c. Fitted
          against 8 real frames matched by rtc_time_unix against
          koyo.hex20.space's public "Battery & Interface Card Temps" table
          (exact-second timestamp matches, all 8). Linear fit
          temp = -0.001775*raw + 42.3638, R2=0.99989, max residual 0.0147 C.

      # ---- offset 82 ----
      - id: battery_th1_raw
        type: u2
        doc: |
          CONFIRMED 2026-07-30, same method as battery_th0_raw.
          temp = -0.001777*raw + 42.4137, R2=0.9999, max residual 0.0133 C.

      # ---- offset 84 ----
      - id: cdh_temp_raw
        type: u2
        doc: |
          CONFIRMED 2026-07-30, same method as battery_th0_raw.
          temp = -0.019402*raw + 45.7133, R2=0.99888, max residual 0.0896 C.

      # ---- offset 86 ----
      - id: adcs_temp_raw
        type: u2
        doc: |
          CONFIRMED 2026-07-30, same method as battery_th0_raw.
          temp = -0.021693*raw + 49.4657, R2=0.99928, max residual 0.0979 C.

      # ---- offset 88 ----
      - id: unknown_88
        size: 32
        doc: |
          TODO. Contains the rest of the EPS block (remaining solar panel
          V/I/T, battery V/I, heater, CDH, COMM, IF card current) per
          HEX20 health-parameter spec. Offsets unknown.

      # ---- offset 120 ----
      - id: thr_safe_to_phoenix
        type: u2
        doc: CONFIRMED 7000 (7.0 V) - matches Athira email 2026-07-07
      - id: thr_unknown_7500
        type: u2
        doc: reads 7500. Not in Athira's threshold list. TODO
      - id: thr_phoenix_to_safe
        type: u2
        doc: CONFIRMED 7300 (7.3 V)
      - id: thr_safe_to_nominal
        type: u2
        doc: CONFIRMED 8000 (8.0 V)

      # ---- offset 128 ----
      - id: unknown_128
        size: 2
        doc: reads 0x00 0x05, constant. TODO - mode fields?

      # ---- offset 130 ----
      - id: boot_counter
        type: u4
        doc: |
          CONFIRMED against HEX20 Grafana (= 9 on 2026-07-16).
          2026-07-09 = 4, 2026-07-16 = 9.

      # ---- offset 134 ----
      - id: unknown_134
        size: 105
        doc: TODO - ADCS / payload / write pointer blocks

      # ---- offset 239 ----
      - id: rtc_time_unix
        type: u4
        doc: CONFIRMED - RTC time, Unix epoch seconds, UTC.

      # ---- offset 243 ----
      - id: unknown_243
        size: 6
        doc: reads all zero. TODO

      # ---- offset 249: RTC broken-down time ----
      # NOTE: this block reads UTC+05:30 (India Standard Time),
      # while rtc_time_unix is UTC. Verified across 2026-07-09 and 2026-07-16.
      - id: rtc_100th_sec
        type: u1
      - id: rtc_seconds
        type: u1
      - id: rtc_minutes
        type: u1
      - id: rtc_hours
        type: u1
      - id: rtc_day
        type: u1
        doc: weekday code. Reads 5 on both 2026-07-09 and 2026-07-16 (Thursday).
      - id: rtc_date
        type: u1
        doc: CONFIRMED 9 on Jul 9, 16 on Jul 16
      - id: rtc_month
        type: u1
        doc: CONFIRMED 7
      - id: rtc_year
        type: u2
        doc: CONFIRMED 2026

      # ---- offset 258 ----
      # 2026-08-05: swapped vs. earlier guess. HEX20_KOYO_LEOPS_Telecommands_v1_R1.pdf
      # documents PIB HealthStatus range 0-175 and SD Card Failure Count range 0-100.
      # offset 258 reads {0, 65, 68} - fits SD Card Failure Count's 0-100 range.
      # offset 259 reads {0, 175} - fits PIB HealthStatus's 0-175 range exactly, and
      # VIOLATES SD Card Failure Count's 0-100 max under the old assignment. Not a
      # spacecraft anomaly - was a decode-side field swap. High confidence, not yet
      # triple-cross-validated against a live-dashboard reading like the temp fields.
      - id: sd_card_failure_count
        type: u1
        doc: reads {0, 65, 68} (spec range 0-100). Was mislabeled pib_health_status.
      - id: pib_health_status
        type: u1
        doc: reads {0, 175} (spec range 0-175). Was mislabeled sd_card_failure_count.

      # ---- offset 260 ----
      - id: trailing
        size: 3
        doc: reads 00 00 00. CRC? padding? TODO

    instances:
      battery_th0_temp_c:
        value: battery_th0_raw * -0.001775 + 42.3638
        doc: CONFIRMED - degrees C. See battery_th0_raw for evidence.
      battery_th1_temp_c:
        value: battery_th1_raw * -0.001777 + 42.4137
        doc: CONFIRMED - degrees C. See battery_th1_raw for evidence.
      cdh_temp_c:
        value: cdh_temp_raw * -0.019402 + 45.7133
        doc: CONFIRMED - degrees C. See cdh_temp_raw for evidence.
      adcs_temp_c:
        value: adcs_temp_raw * -0.021693 + 49.4657
        doc: CONFIRMED - degrees C. See adcs_temp_raw for evidence.

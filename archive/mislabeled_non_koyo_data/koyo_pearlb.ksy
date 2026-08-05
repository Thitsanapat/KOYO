meta:
  id: koyo_pearlb
  title: KOYO / PEARL-B AX.25 first-level frame
  endian: le
  ks-version: 0.9
  license: CC0-1.0

doc: |
  First-level parser for SatNOGS demoddata observed from KOYO / PEARL-B.
  Confirmed frames from observation 14633961 use AX.25 UI headers:
  PEARLB -> NCUGS1, control 0x03, PID 0xf0.

  This spec intentionally stops at packet classification. The engineering
  telemetry payload offsets still need to be locked against ground-truth
  Grafana/HEX20 values before naming EPS/OBC fields.

seq:
  - id: ax25
    type: ax25_header
  - id: pearl
    type: pearl_info
    size-eos: true

types:
  ax25_header:
    seq:
      - id: dest_callsign_raw
        type: ax25_callsign_raw
      - id: dest_ssid_raw
        type: u1
      - id: src_callsign_raw
        type: ax25_callsign_raw
      - id: src_ssid_raw
        type: u1
      - id: control
        type: u1
        doc: 0x03 for AX.25 UI frame
      - id: pid
        type: u1
        doc: 0xf0 for no layer 3 protocol
    instances:
      dest_callsign:
        value: dest_callsign_raw.callsign_ror.callsign
      src_callsign:
        value: src_callsign_raw.callsign_ror.callsign
      dest_ssid:
        value: (dest_ssid_raw & 0x1e) >> 1
      src_ssid:
        value: (src_ssid_raw & 0x1e) >> 1

  ax25_callsign_raw:
    seq:
      - id: callsign_ror
        process: ror(1)
        size: 6
        type: ax25_callsign

  ax25_callsign:
    seq:
      - id: callsign
        type: str
        encoding: ASCII
        size: 6

  pearl_info:
    seq:
      - id: frame_counter
        type: u1
      - id: protocol
        contents: [0x11, 0x01]
        doc: Constant in all observed PEARLB frames from obs 14633961
      - id: packet_type
        type: u1
        enum: packet_type
      - id: payload
        type:
          switch-on: packet_type
          cases:
            'packet_type::text_beacon': text_beacon_payload
            'packet_type::telemetry_block': telemetry_block_payload
            _: raw_payload
        size-eos: true

  telemetry_block_payload:
    seq:
      - id: tlm_counter
        type: u1
      - id: block_id
        type: u1
        doc: Observed 0x04 for all 0x33 telemetry blocks in current sample
      - id: subtype
        type: u1
      - id: message_id
        type: u1
        doc: Observed values include 0x46, 0x45, 0x1d, 0x1b, 0x04, 0x67
      - id: body
        size-eos: true

  text_beacon_payload:
    seq:
      - id: message
        type: str
        encoding: ASCII
        size-eos: true

  raw_payload:
    seq:
      - id: body
        size-eos: true

enums:
  packet_type:
    0x33: telemetry_block
    0x80: text_beacon
    0x81: zero_block
    0x82: status_block
    0x83: status_block_ext

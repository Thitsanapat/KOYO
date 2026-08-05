# KOYO SatNOGS telemetry decoder + dashboard

Internship project at National Central University (NCU), Taiwan. Read this whole
file before doing anything. Everything below is verified against real data unless
marked TODO or UNCONFIRMED.

---

## 1. What I am building and why

Two deliverables:

1. **`koyo.ksy`** — a Kaitai Struct definition that parses KOYO beacon frames into
   named engineering fields.
2. **A Grafana dashboard** showing KOYO telemetry over time, eventually hosted on
   `dashboard.satnogs.org` and linked from the KOYO page in the SatNOGS database.

Why the decoder is unavoidable: SatNOGS' Grafana can only read from SatNOGS'
own InfluxDB. That database is populated exclusively by decoders merged into the
public `satnogs-decoders` repository. There is no API to upload decoded telemetry
directly. So a Kaitai decoder has to exist before any SatNOGS-hosted dashboard can
show data.

**Current scope decision from my supervisor (Prof. Loren Chang, 2026-07-21):**
build the dashboard and get the de-packetizing working first, using HEX20's own
platform for verification. Whether to merge upstream into `satnogs-decoders` is a
later decision. So: do NOT open a merge request. Build and validate locally.

The stated purpose of the exercise is for me to learn satellite telemetry
handling — so prefer explaining what you're doing over silently doing it.

---

## 2. The spacecraft

**KOYO** — 3U-class CubeSat, built by HEX20 (India), operated with NCU.
Launched on SpaceX Transporter-17, 2026-07-07. Healthy and beaconing normally.

| Property | Value |
|---|---|
| SatNOGS NORAD ID | 98273 (temporary) |
| SatNOGS satellite ID | YZNT-7399-1272-5956-2962 |
| Telemetry downlink | 435.400 MHz, FSK, 9600 baud |
| Digipeater | 145.825 MHz, AFSK 1200, AX.25 (transceiver, only repeats — silent unless uplinked) |
| Callsign | KOYOSC |
| Beacon interval | 10000 ms |
| Frame length | **263 bytes** |
| Orbit | Sun-synchronous, ~600 km, inclination 97.75 deg |
| SatNOGS Rx success rate | ~52% |

Sibling spacecraft **SCION-X** (NORAD 98266, later 69885/69873, ~437.5 MHz,
launched on the same rocket, is in an anomalous state. **Modulation/frame
length UNCONFIRMED — was recorded here as "GMSK 9600, 294-byte frames" but a
HEX20 team member's hands-on signal analysis of real captured audio (see §10
SCION-X notes) says AFSK/1200bps and a 274-byte frame (272 payload + 2 FCS),
backed by a ground-test reference frame. Trust the hands-on analysis over
this row until reconciled** — do not mix the two satellites regardless of
which numbers turn out right; different modulation, different frame length,
different decoder. SCION-X is a later, separate task.

---

## 3. Frame format — what is CONFIRMED

263 bytes total. Standard AX.25 UI frame, then a payload. Multi-byte payload
fields are **little-endian**, except the packet counter which appears to be
big-endian (flagged below).

Verified by cross-checking three real frames from two different ground stations
on two different dates (2026-07-09 obs 14468821, 2026-07-16 obs 14526577), plus
against HEX20's public dashboard.

| Offset | Size | Field | Type | Evidence |
|---|---|---|---|---|
| 0–6 | 7 | AX.25 destination | callsign, ror(1) | decodes to `GS-H20` |
| 7–13 | 7 | AX.25 source | callsign, ror(1) | decodes to `KOYOSC` |
| 14 | 1 | AX.25 control | u1 | always `0x03` = UI frame |
| 15 | 1 | AX.25 PID | u1 | always `0xF0` = no layer 3 |
| 16–17 | 2 | magic / frame type | bytes | always `0x08 0x01` |
| 18–19 | 2 | packet counter | **u2be** | Increments during a boot session (up to 65486 observed), but is NOT "beacons since boot" — see oddity #3 below. Big-endian is odd vs the rest — UNCONFIRMED, verify |
| 20–23 | 4 | unknown | — | byte 21 is constantly `0xEB`. TODO |
| 24–27 | 4 | OBC uptime | u4le, milliseconds | increments ~10000 per beacon; cross-checked against RTC deltas within a pass. Resets on boot |
| 28–31 | 4 | OBC time | u4le, Unix seconds UTC | 2026-07-09 frame reads 2025-07-14 (uninitialised); 2026-07-16 frame matches RTC. Evidence that telecommand `0x24 CaliberateObcWithRtc` executed between those dates |
| 32–119 | 88 | **EPS block** | — | Panel/battery/CDH/COMM voltages, currents, temperatures live here. 6 of ~28 fields confirmed/candidate so far - see rows below and §4 |
| 62, 66 | 2+2 | solar panel voltage (candidate) | u2le, mV | see §4 - high-confidence candidate, not yet fully confirmed |
| 80–81 | 2 | battery TH0 temperature | u2le (raw ADC) | **CONFIRMED** `temp_c = raw * -0.001775 + 42.3638`. Fitted against 8 real frames matched by exact `rtc_time_unix` against koyo.hex20.space's public temperature table. R²=0.99989, max residual 0.015°C |
| 82–83 | 2 | battery TH1 temperature | u2le (raw ADC) | **CONFIRMED** `temp_c = raw * -0.001777 + 42.4137`. Same method, R²=0.9999, max residual 0.013°C |
| 84–85 | 2 | CDH temperature | u2le (raw ADC) | **CONFIRMED** `temp_c = raw * -0.019402 + 45.7133`. Same method, R²=0.99888, max residual 0.09°C |
| 86–87 | 2 | ADCS temperature | u2le (raw ADC) | **CONFIRMED** `temp_c = raw * -0.021693 + 49.4657`. Same method, R²=0.99928, max residual 0.098°C |
| 120–121 | 2 | threshold: safe→phoenix | u2le, mV | reads 7000; HEX20 stated 7.0 V |
| 122–123 | 2 | threshold: unknown | u2le, mV | reads 7500; not in HEX20's stated list. TODO |
| 124–125 | 2 | threshold: phoenix→safe | u2le, mV | reads 7300; HEX20 stated 7.3 V |
| 126–127 | 2 | threshold: safe→nominal | u2le, mV | reads 8000; HEX20 stated 8.0 V |
| 128–129 | 2 | unknown | — | always `0x00 0x05`. TODO |
| 130–133 | 4 | boot counter | u4le | reads 4 on 2026-07-09, 9 on 2026-07-16. **9 matches HEX20's dashboard exactly** |
| 134–238 | 105 | unknown | — | TODO. Likely ADCS, payload state, write pointers |
| 239–242 | 4 | RTC time | u4le, Unix seconds UTC | matches actual observation times |
| 243–248 | 6 | unknown | — | reads all zero |
| 249 | 1 | RTC hundredths | u1 | |
| 250 | 1 | RTC seconds | u1 | |
| 251 | 1 | RTC minutes | u1 | |
| 252 | 1 | RTC hours | u1 | |
| 253 | 1 | RTC weekday code | u1 | reads 5 on both 2026-07-09 and 2026-07-16, both Thursdays |
| 254 | 1 | RTC date | u1 | reads 9 and 16 respectively — exact match |
| 255 | 1 | RTC month | u1 | reads 7 |
| 256–257 | 2 | RTC year | u2le | reads 2026 |
| 258 | 1 | SD card failure count | u1 | **CORRECTED 2026-08-05** (was mislabeled `pib_health_status`). Reads {0, 65, 68} — fits documented range 0-100 |
| 259 | 1 | PIB health status | u1 | **CORRECTED 2026-08-05** (was mislabeled `sd_card_failure_count`). Reads {0, 175} — fits documented range 0-175 exactly |
| 260–262 | 3 | trailing | — | reads `00 00 00`. CRC? padding? TODO |

### Two oddities worth knowing

- **The broken-down RTC block (249–257) reads UTC+05:30 (India Standard Time)
  while `rtc_time_unix` at 239 reads UTC.** Consistent across both passes, so
  possibly intentional (HEX20 is in Kerala). Do not "fix" this — record it.
- ~~`sd_card_failure_count` reading 175 against a documented max of 100~~
  **RESOLVED 2026-08-05, was a decode bug, not a spacecraft anomaly.** HEX20's
  LEOP telecommand doc (health parameter table, slide 8) documents
  `PIB HealthStatus` range 0-175 and `SD Card Failure Count` range 0-100.
  offset 258 and 259 were swapped: the field previously labeled
  `pib_health_status` (offset 258) only ever reads {0, 65, 68} — fits SD Card
  Failure Count's 0-100 range with room to spare — while the field previously
  labeled `sd_card_failure_count` (offset 259) only ever reads {0, 175}, which
  is impossible for a 0-100 field but lands exactly on PIB HealthStatus's
  documented max of 175. Zero contradictions after swapping vs. one hard
  contradiction before. `koyo.ksy` and `decode_koyo.py` corrected; CSV/InfluxDB
  regenerated. High confidence (resolves a spec contradiction cleanly) but not
  triple-cross-validated against a live timestamp-matched dashboard reading
  the way the offset 80-87 temperature fields are.
- **`packet_counter` (offset 18-19) is bounded to the range 49153-65486 across
  all 10,900+ real post-launch frames — it never reads below ~49150.** Checked
  2026-08-05: across 19 confirmed reboot events (boot_counter N -> N+1, RTC
  populated on both sides), the post-reboot value is *always* 49160-51137,
  clustering tightly around **49152 = `0xC000` exactly** (mean 49525, spread
  only 1977). It then climbs during the boot session (up to 65486 observed)
  before the next reboot resets it back into that same narrow band. No
  in-session wraparound was found (zero drops >1000 within a single
  boot_counter value), so this isn't 16-bit overflow either.
  **This rules out "beacons transmitted since boot, starting at 0."** A
  counter that restarts near a round hex boundary on every single reboot
  looks more like a flash/EEPROM buffer write-pointer or session base address
  than a beacon tally - worth asking HEX20 directly, or checking against
  Aditya's Python decoder if it arrives (see §8).

---

## 4. The EPS block — how to crack offsets 32–119 and 134–238

**This is the primary task.** The method that already worked for the confirmed
fields:

1. Pick one frame. Read its `rtc_time_unix` (offset 239) to get the exact UTC
   timestamp of that beacon.
2. Open HEX20's public dashboard at **https://koyo.hex20.space/** and set the
   time range to that instant.
3. Read off the engineering values HEX20 displays for that moment.
4. Search the frame's bytes for a u16le (or u32le) that maps onto each value.
   Compute the scaling factor.
5. Confirm the candidate against a **second frame at a different time** — a
   single match can be coincidence. Two frames at different times, both matching,
   is solid.

### Fields the dashboard shows (so they must be in the frame somewhere)

Solar panel voltages (3), solar panel currents (3), solar panel temperatures (3),
battery voltage, battery current, battery temperatures (TH0, TH1), battery heater
voltage, battery heater current, load current, battery charge current, generated
current, CDH voltage, CDH current, CDH temperature, COMM voltage, COMM current,
IF card MCU current, ADCS temperature, spacecraft mode, satellite PIB mode,
antenna deployment status, solar panel deployment status, beacon flash write
pointer, beacon SD write pointer.

Note: the dashboard shows **more fields than HEX20's LEOP telecommand document
lists** (temperatures and heater values in particular). Reverse-engineering from
the document alone will not be complete — the dashboard is the better reference.

### Candidate offsets already narrowed down (all UNCONFIRMED unless noted)

| Offset | Reading on 2026-07-16 17:46 UTC | Guess |
|---|---|---|
| 40, 42, 44, 46 (u16le ×4) | 2934, 2963, 3866, 2959 (Jul-16 frame) | Solar panel voltages? One jumped to 3725 in 102 s, consistent with spacecraft rotation. But 2.9–3.9 V does not match the 15–17 V range in the spec, so **there is a scaling factor** |
| **62, 66** | 16948, 16929 (single-frame); confirmed 2026-07-30 across 9,578 valid post-launch frames: 16486-17103 and 16517-17083 respectively, cv=0.005 both | **Solar panel voltage, high confidence** - see `koyo.ksy` `sp_voltage_candidate_1`/`_2`. Extremely stable and fits the documented 15-17V range (as mV) almost exactly. Still short of full CONFIRMED status - not yet cross-checked against a live-dashboard reading at a matching timestamp, and which of the 4 SP channels (Y+/X+/Y-/X-) each one is remains unknown. The other 2 SP voltage channels were not found by the same method - see below. |
| 80, 82 | 20749, 20558 | Temperature? Barely changes. HEX20 dashboard showed battery temp 24.0 C — so likely a raw ADC value, not a direct unit |

2026-07-30: HEX20's LEOP telecommand doc (`HEX20_KOYO_LEOPS_Telecommands_v1_R1.pdf`,
**STRICTLY CONFIDENTIAL - local use only, see §7**) has a full health-parameter
table with data type and min/max for every EPS field. Ran a systematic offset
search (data type + documented range vs. real byte patterns across 9,578 valid
frames) - this is what confirmed 62/66 above. It did NOT cleanly resolve the
rest (other SP voltages, battery, CDH, currents, temperatures): candidates were
too ambiguous without a live-dashboard ground truth to pin the exact scale
factor, since most of those fields' documented ranges are wide/open-ended
("0 to X") and match many offsets at once. **The dashboard-hover method in this
section is still needed for the remaining fields.**

~~Also confirmed by the same document: `sd_card_failure_count` (offset 259) has
documented range 0-100, but every valid post-launch frame reads 175 - a hard
confirmed anomaly.~~ **See oddity #2 in §3 (resolved 2026-08-05): offsets 258
and 259 were swapped, not a spacecraft anomaly.** The 175-vs-100 contradiction
is exactly what led to catching the swap in the first place.

2026-07-30 (later): user shared screenshots of the live HEX20 dashboard
(koyo.hex20.space - public, fine to use per constraints above) showing Battery
Charge Voltage ~8.2-8.3V and CDH/COMM/ADCS-3V3 bus voltages as near-flat lines,
plus Solar Panel Voltages swinging 0-20V (shape matches sp_voltage_candidate_1/2
well - orbital day/night). Searched real frames for offsets matching each flat
line's *stability* (not just value range, since exact scale factor is unknown
without a timestamp-matched reading):

- **Offset 50** (`comm_voltage_candidate` in koyo.ksy): reads constant 676
  (cv=0.0002) - matches the flat-line shape of COMM Voltage, but 676 isn't a
  clean /1000 (mV) scale like the SP voltage fields are; would need ~/100.
  Weaker candidate than sp_voltage_candidate_1/2 - not confirmed.
- Battery Charge Voltage (~8.2-8.3V) and CDH Voltage (~3.3V): not found by this
  method. Either the scale isn't a round decimal factor, or they're not stored
  as simple linear-scaled uint16 - or the field just isn't in the byte ranges
  searched so far (32-119, 134-238).

2026-07-30 (later still): **the timestamp-match method actually worked.** User
pasted the live dashboard's "Battery & Interface Card Temps" table (public,
7-day history, exact UTC timestamps). Matched 8 of those timestamps
byte-for-byte against `rtc_time_unix` in already-downloaded frames (all 8
matched at 0-second delta - confirms the dashboard's displayed time **is**
`rtc_time_unix`, not the IST-offset broken-down clock). Linear-regression-fit
each candidate offset's raw u16le/i16le/u8/i8 value against each of the 4
temperature columns across those 8 frames. Four offsets fit at R²>0.998 with
sub-0.1°C max residual - see the CONFIRMED rows in section 3 (offsets 80-87).

**This is the method to repeat for the remaining ~20 fields** (other 2 SP
voltages, battery/CDH/COMM bus voltages, all the currents): get the live
dashboard's per-timestamp history table for each panel (not just current
value), pick several timestamps, match against `rtc_time_unix` in downloaded
frames (exact match expected), and linear-regression-fit every candidate
offset against the ground truth. Far more reliable than guessing round scale
factors - it also caught the exact linear coefficients (which aren't round
numbers), which no amount of range/stability guessing would have found.

**What would actually resolve this**: a specific frame's `rtc_time_unix`
matched against a dashboard reading at that *exact* timestamp (not "current
value," which doesn't line up with any downloaded frame). That's still the
most reliable path for the remaining ~20 fields.

Resolving the remaining solar panel/battery/CDH voltage and current scaling is
the single highest-value next step.

### 2026-08-05: full health parameter table (from the confidential LEOP doc)

Extracted from `HEX20_KOYO_LEOPS_Telecommands_v1_R1.pdf` slides 7-8 so it
doesn't need re-reading each session. **Local reference only per §7 — do not
copy this table into any public file.** All currents/voltages are `uint16_t`
unless noted; "-" means no documented bound on that side.

| Parameter | Min | Max | Unit |
|---|---|---|---|
| SP YPlus/XPlus/YNegative/XNegative Voltage | 15 | 17 | Volt |
| Cdh Current | - | 0.15 | Ampere |
| Cdh Voltage | - | 3.3 | Volt |
| Load Current (battery discharge) | - | 2.5 | Ampere |
| Load Voltage (battery discharge) | 5 | 8.3 | Volt |
| Generated Current (battery charge) | - | 3 | Ampere |
| Battery Charge Voltage | - | 8.3 | Volt |
| Aprs Pl Current (Digipeater) | - | 0.3 | Ampere |
| ADCS MCB Current | - | 0.8 | Ampere |
| ADCS 3V3 Current | - | 0.6 | Ampere |
| Amp Space Pl Current | - | 2 | Ampere |
| ADCS CMG Current | - | 0.8 | Ampere |
| Fog Pl Current | - | 0.5 | Ampere |
| IF Card MCU Current | 0 | - | Ampere |
| Satellite Current_mode | PHOENIX | NOMINAL | u1 enum |
| Satellite PIB Current_mode | PHOENIX | NOMINAL | u1 enum |
| Antenna Deployment Status | 0 | 2 (text says 3) | u1: 0=none,1=UHF,2=VHF,3=both |
| SP Deployment Status (retry count) | 0 | 15 | u1: 0=none,1=Y+,4=Y-,5=both |
| Boot Counter | - | 4 (stale example, real max is higher) | u32 |
| PIB HealthStatus | 0 | 175 | u1 |
| SD Card Failure Count | 0 | 100 | u1 |

Note: only Y+ and Y- solar panels have a deployment flag encoding — X+/X- are
presumably body-mounted fixed panels, not deployables. Consistent with only 2
of the 4 SP voltage channels (offsets 62/66) being pinned down so far.

**Fields the doc does NOT cover** (confirmed missing from this table, but
present on the live dashboard - see below): COMM Voltage, ADCS 3V3 Voltage,
all 3 payload *voltages* (FOG/APRS/Amp Space - only their currents are
documented), Command Accept Count, Command Reject Count. These will need the
dashboard-timestamp-match method exclusively, no doc shortcut available.

### 2026-08-05: full field list from the live dashboard (user-pasted)

Confirms every field name shown on `koyo.hex20.space`, useful as the
authoritative target list when searching unknown byte ranges 32-119/134-238:

- **Temperatures**: Battery TH0, Battery TH1, CDH, ADCS (all 4 CONFIRMED,
  offsets 80-87) · SP YPlus/XPlus/YNegative/XNegative Temperature (NOT in the
  LEOP doc's table at all - undocumented, still fully unknown)
- **Power**: CDH/Load/Generated Current · SP YPlus/XPlus/YNegative/XNegative
  Voltage (2 of 4 are `sp_voltage_candidate_1`/`_2`, offsets 62/66) · Battery
  Charge/CDH/COMM/ADCS-3V3 Bus Voltage
- **Payloads**: FOG/APRS/Amp Space Voltage and Current (6 fields, all unknown)
- **Command & Health**: Boot Counter, Command Accept Count, Command Reject
  Count (the latter two are new - not in koyo.ksy at all yet, must be
  somewhere in the still-unknown byte ranges)

Live snapshot values from the same paste (no `rtc_time_unix` match, so
reference only, not a confirmation): Battery TH0 7.0°C, TH1 6.9°C, CDH 14.2°C,
ADCS 15.0°C, Boot Counter 20, Command Accept Count 190, Command Reject Count
20. Boot Counter 20 matches the most recent real frame's `boot_counter` at
time of writing - good sanity check that the live dashboard and SatNOGS-fed
decoder are looking at the same spacecraft state.

---

## 5. Data

### Fetching

`fetch_satnogs.py` in this repo downloads everything SatNOGS holds:

```bash
pip install requests
python3 fetch_satnogs.py --audio --waterfall          # KOYO
python3 fetch_satnogs.py --sat scionx --audio         # SCION-X, later
```

Output:

```
data/koyo/frames/<obsid>_<n>.bin     raw demodulated frames, binary
data/koyo/frames_hex/<obsid>.txt     same as hex, one frame per line
data/koyo/audio/<obsid>.ogg          audio recordings
data/koyo/waterfall/<obsid>.png      waterfall images
data/koyo/observations.json          full API metadata
data/koyo/index.csv                  obsid, start, station, status, n_frames
```

**SatNOGS does not keep audio forever** — old recordings get deleted, while frames
persist longer. If audio matters, download it early.

The API needs no authentication:
`https://network.satnogs.org/api/observations/?satellite__norad_cat_id=98273&format=json`

### Known-good reference frames

Two observations already analysed, useful as regression fixtures:

- obs **14468821**, beacon RTC 2026-07-09 08:40:04 UTC, station SA2KNG Omni UHF/VHF (Sweden)
- obs **14526577**, beacon RTC 2026-07-16 17:46:22 UTC, station MAUSyagi

Both are embedded in `validate.py` as `REFERENCE`, so `python3 validate.py` with no
arguments is a self-contained regression test.

---

## 6. Repo layout and tooling

```
CLAUDE.md            this file
fetch_satnogs.py     downloader
koyo.ksy             Kaitai Struct definition — the deliverable
validate.py          Python reference parser, mirrors koyo.ksy, prints decoded fields
data/                downloaded frames, audio, waterfalls (gitignored)
```

`validate.py` exists so field-offset hypotheses can be tested in plain Python
without a Kaitai compile cycle. **Keep it in sync with `koyo.ksy`** — when a field
is added to one, add it to the other, and confirm both produce the same numbers on
the reference frames.

### Testing the .ksy

Two ways:

- **Kaitai Web IDE** — https://ide.kaitai.io/ — drag in `koyo.ksy` and a `.bin`
  frame, click the ksy to compile, click the bin to see the parsed object tree.
  Clicking a field highlights its bytes in the hex view. Good for exploration.
- **CLI** — `ksc` (kaitai-struct-compiler) to generate Python, then parse frames
  in a script. Better for regression tests.

Whichever is used, the acceptance test is the same: parse both reference frames
and check the confirmed fields in section 3 produce exactly the values listed.

---

## 7. Constraints — read before publishing anything

- **HEX20's LEOP Procedure and Telecommand document is marked STRICTLY
  CONFIDENTIAL.** `satnogs-decoders` is a public, openly licensed repository, so
  merging a decoder there would permanently publish KOYO's frame structure. I have
  raised this with HEX20 and they have not yet decided. **Do not open a merge
  request, do not push the frame structure to any public repository, and do not
  post it in a public issue or discussion.** Local work only.
- HEX20's own dashboard at `koyo.hex20.space` is public, so using its displayed
  values for verification is fine.
- Do not send telecommands to the spacecraft. Not my role, and uplink is NCU
  ground station operations.

---

## 8. People

| Name | Role | Notes |
|---|---|---|
| Prof. Loren Chang | My supervisor, NCU Dept. of Space Science & Engineering | Sets scope, replies fast |
| Aditya Chandran | HEX20, owns their Grafana | **Has a Python decoder for KOYO frames already.** Asked for it; not yet received |
| Athira B S | HEX20 Techno Manager | Answers technical questions thoroughly |
| Amal Chandran | HEX20 CEO | |
| Roger Tsai | HEX20, works at NCU | Ground station operations |

If Aditya's Python decoder arrives, it supersedes the reverse-engineering — the
task becomes translating it to Kaitai and verifying it against the reference
frames. Until then, reverse-engineer from the dashboard.

---

## 9. Working preferences

- I am a third-year Communications and Network Engineering student. Comfortable
  with Python, signal processing, and time-series data. New to Kaitai Struct and
  to SatNOGS internals.
- Be direct. Say when something is a guess. Distinguish "verified against two
  frames" from "plausible".
- Prefer small, checkable steps with a printed result over large refactors.
- Any byte-offset claim must state its evidence. An unverified guess belongs in a
  comment marked UNCONFIRMED, not asserted as fact.

---

## 9b. KOYO audio decode - CONFIRMED working (2026-07-30)

Control test per Loren's verbal instruction: decode KOYO's own audio locally
before touching SCION-X. `gr_satellites`' default clock-recovery bandwidth
(`--clk_bw`, default 0.06 relative to baudrate) is too narrow to track through
KOYO's full 263-byte frame - it locks onto the AX.25 header correctly (visible
as recognizable `KOYOSC`/`GS-H20` bytes) then loses lock partway through,
producing truncated/malformed captures.

Fix: `--clk_bw 0.15`. Verified against obs 14526577 - the resulting 263-byte
frame is an **exact byte-for-byte match** against SatNOGS' own server-side
decoded frame for the same observation. Reproducible via:

```
python verify_audio_pipeline.py --obs-id 14526577
```

Caveat: this basic flowgraph only fully locks the single strongest beacon per
pass (1 exact match out of ~35 official frames in that pass) - SatNOGS' own
decoder is presumably more heavily tuned. That's fine for a control test
(proves the pipeline is correct when it locks) but would need more DSP work
(better clock recovery, possibly GNU Radio Companion's visual tools for
eye-diagram inspection) to raise the capture rate if that becomes a goal.

`run_koyo_grsat.ps1` now defaults to `--clk_bw 0.15` and to obs 14526577 (its
old default, 14586261, has no official demoddata at all, so it was never a
valid test case - SatNOGS never decoded it either).

---

## 10. Next steps, in order

1. Run `fetch_satnogs.py` and confirm how many frames and observations landed.
2. Write a script that decodes every downloaded frame with the currently
   confirmed fields and dumps a CSV — one row per frame, columns for
   packet_counter, uptime_ms, obc_time_unix, boot_counter, rtc timestamp. Sanity
   check: does packet_counter increase monotonically within a pass, does
   boot_counter step in a way that matches reboots.
3. Crack the EPS block using the dashboard-comparison method in section 4. Start
   with solar panel voltages and the scaling factor.
4. Extend `koyo.ksy` and `validate.py` together as each field is confirmed.
5. **DONE (2026-08-05).** Local InfluxDB + Grafana stack running, fed from the
   decoded CSV, panels covering every confirmed/candidate field. See
   `local-stack/README.md`. This directly answers Loren's 2026-07-21 ask for
   "a Grafana interface on SatNOGS" — it's real Grafana, just local, since the
   public-facing version still needs the upstream merge decision. Re-run
   `local-stack/load_influx.py` after every `decode_koyo.py` refresh.

Later, separate task: SCION-X. Read
`https://github.com/daniestevez/gr-satellites/discussions/843` first — the
gr-satellites maintainer has already analysed SCION-X there. Its problem is clock
recovery, because NRZI and bit scrambling were not implemented, leaving long runs
of identical bits.

**2026-08-05: read the full discussion.** Confirmed technical details: UHF
437.5 MHz, GFSK, 9600 baud, HDLC/AX.25 framing, no NRZI/G3RUH scrambling - long
zero-runs create a CW tone that breaks clock recovery (root cause, per
maintainer daniestevez). **Unresolved as of the discussion** - no working fix
in gr-satellites yet.

Two separate resource threads exist, don't conflate them:
- **Jakub Horky** (external ground-station collaborator, Panska Ves, in the
  Loren/HEX20 email thread) - raw IQ recordings, Google Drive folder already
  noted in §5.
- **JacyyChang** (HEX20/SCION-X team member, active in the GitHub discussion)
  - shared a `.bin` sample + `.grc` flowgraph + README at
  `https://drive.google.com/drive/folders/1VRhHdQ0Pv2btzNrKJ77zNd0aG2Czc3t_`,
  and has a full independent decode attempt with code at
  `https://github.com/JacyyChang/scionx-decode-writeup` - **"IChen-Luna" in
  the discussion is also SCION-X team, likely who Loren meant by "Luna"** in
  verbal conversation.

**2026-08-05, corrected after actually reading the repo (`scionx/external/`,
gitignored - cloned locally, not ours to redistribute):** my first pass at
this ("just apply the NRZI fix to their pipeline") was wrong on two counts -
worth recording so the mistake isn't repeated.

- **Modulation is AFSK/1200bps, not GFSK/9600** per JacyyChang's own README,
  from hands-on analysis of the *same* SatNOGS observation (14459039) the
  gr-satellites discussion is about. This also fits the "long zero-runs make
  a CW tone" root cause better than GFSK would. My GFSK/9600 read of the
  discussion thread was very likely a mis-extraction - see the corrected
  spacecraft table row in §2.
- **There's no NRZI to "fix" on the ground.** If the satellite's firmware
  never NRZI-encodes the transmission (per daniestevez's diagnosis), there is
  nothing to *reverse* at the receiver - decoding the raw bits directly is
  already correct. The actual fallout of that design choice is that long
  zero-runs make the receiver's clock-recovery loop lose lock, which is a
  demodulator robustness problem, not a missing decode step.
- **Frame is 274 bytes (272 payload + 2 FCS), not 294** - `REFERENCE_FRAME.md`
  has an actual ground-test hex dump: dest `BN0CU `, src `BN0SCX`, control
  `0x03`, PID `0xF0`, matching `SCIONX_doppler.grc` in `6 COMM/`.

What the repo actually shows (very rigorous, already ruled out a lot):
frame detection is excellent (z-score 12-13, exact hits on all 3 known
frames). Header/address/PID decode perfectly and match the ground-test
reference exactly. Zero-run padding segments are mostly clean (0.8-2.5%
false-positive rate). **The problem is the data segments**: 2-7% of bit
decisions flip when the threshold changes, with a slow "invisible curve" of
drifting asymmetry across the segment. They tried real GNU Radio timing
recovery (Gardner, swept 125 parameter combinations) - best config dropped
header bit errors from 5/144 to 2/144 with a visibly cleaner eye diagram,
**but CRC still fails on all 3 frames** even then. Errors are "scattered at
high-transition, low-confidence bits," explicitly *not* concentrated in the
zero-run regions - so the classic "PLL loses lock during the CW-tone
zero-run" story may not even be the dominant driver of *this* pipeline's
specific CRC failures (their architecture uses cross-correlation frame
alignment + fixed-phase sampling for most stages, not a continuously-tracking
loop that would be vulnerable to that in the first place).

Their own README frames this as an open, unsolved problem and asks the
community for ideas - this is not a quick fix. Real prior art worth reading
in full (`scionx/external/scionx-decode-writeup/README.md` and each
subfolder's own README) before attempting anything new, but don't
underestimate the effort - a skilled HEX20 team member has already spent
real time on this without cracking it.

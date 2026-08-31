# KOYO Beacon Decoder - Presentation Script

Recommended duration: 12-15 minutes plus questions. The slides are in English
for an international audience. Read the Thai script to understand the story,
then rehearse the English backup. Do not claim that every dashboard field has
been decoded.

## Slide 01 - KOYO Beacon Decoder: SatNOGS Audio to Telemetry

### สคริปต์ไทย

สวัสดีครับ วันนี้ผมจะนำเสนอโปรเจกต์ KOYO Beacon Decoder งานนี้มีเป้าหมายคือรับไฟล์เสียงสัญญาณดาวเทียมจาก SatNOGS แล้วถอดสัญญาณด้วย GNU Radio ของเราเองจนได้เฟรมที่ตรวจ CRC ผ่าน จากนั้นจึงแปลงข้อมูลเป็น telemetry และแสดงผลใน Grafana ผลหลักคือ observation ที่เลือกทดสอบทั้งห้ารายการผ่านเกณฑ์ มีเฟรม KOYO ที่ถูกต้องจากการถอดเสียงในเครื่อง 22 เฟรม และตรงกับ control frame ของ SatNOGS แบบ byte-for-byte 20 เฟรม สิ่งสำคัญคือผมแยกให้ชัดระหว่างข้อมูลที่ยืนยันแล้ว ข้อมูล candidate และข้อมูลที่ยัง NOT DECODED เพื่อไม่สร้างค่าที่ไม่มีหลักฐาน

### English backup

Good morning. This project implements a KOYO beacon decoder from SatNOGS audio to operational telemetry. The recording is demodulated locally with GNU Radio, checked as G3RUH AX.25, filtered to CRC-valid KOYO frames, decoded, and displayed in Grafana. All five selected observations passed the strict test. The local pipeline produced 22 valid KOYO frames, including 20 byte-exact matches against SatNOGS control frames. Confirmed, candidate, and not-decoded fields are kept explicitly separate.

### Key result

`5/5 PASS | 22 valid local frames | 20 byte-exact matches`

## Slide 02 - Objective and Acceptance Criteria

### สคริปต์ไทย

ปัญหาที่ต้องแก้มีสามส่วนครับ หนึ่ง ต้องพิสูจน์ว่าเราเริ่มจากเสียง OGG จริง ไม่ได้เอา HEX ที่ SatNOGS ถอดไว้แล้วมาแสดงอย่างเดียว สอง ต้องมีหลักฐานว่าเฟรมที่เราถอดได้ถูกต้อง จึงใช้การเปรียบเทียบแบบ byte-exact กับ control ของ observation เดียวกัน สาม ต้องนำผลไปใช้งานต่อได้ผ่าน dashboard เกณฑ์ PASS ของแต่ละ observation จึงกำหนดว่าต้องได้อย่างน้อยหนึ่งเฟรม KOYO ความยาว 263 bytes ที่ผ่าน CRC และต้องมีอย่างน้อยหนึ่งเฟรมตรงกับ control ทุก byte ผลส่งมอบคือ GNU Radio flowgraph, คำสั่งเดโมเส้นทางเดียว, ตาราง validation, historical coverage และ full telemetry dashboard

### English backup

The project has three acceptance goals. First, prove that the decoder starts from OGG audio rather than pre-decoded HEX. Second, verify correctness with a byte-exact control from the same observation. Third, make the output operational through a dashboard. An observation passes only when the local chain produces at least one CRC-valid 263-byte KOYO frame and at least one byte-exact control match. The deliverables are the GNU Radio flowgraph, one-command demo, validation evidence, historical coverage, and the telemetry dashboard.

### Key result

The success criterion is reproducible and stricter than visual similarity.

## Slide 03 - What Each Stage Means

### สคริปต์ไทย

สไลด์นี้อธิบายคำหลักเพื่อให้เห็นภาพรวมครับ Beacon คือข้อความสั้นที่ดาวเทียมส่งสถานะเป็นระยะ OGG คือเสียงที่สถานีภาคพื้นบันทึกไว้ Demodulation คือการเปลี่ยนเสียง FSK กลับเป็นบิต AX.25 หรือ HDLC คือรูปแบบเฟรมที่กำหนดขอบเขต ที่อยู่ และ CRC ส่วน telemetry decoder คือการแปล payload bytes เป็นเวลา อุณหภูมิ counter และสถานะต่าง ๆ สุดท้าย dashboard ไม่ได้เป็นตัว decoder แต่เป็นชั้นแสดงผล ดังนั้นถ้าเสียงยังถอดไม่ได้ dashboard ก็ไม่ควรแสดงค่าปลอม ความเข้าใจนี้เป็นเหตุผลที่ระบบแยกทุกขั้นและเก็บผลลัพธ์ตรวจสอบได้

### English backup

A beacon is a periodic spacecraft status message. OGG is the recorded ground-station audio. Demodulation converts FSK audio back into bits. AX.25 and HDLC define frame boundaries, addressing, and CRC. The telemetry decoder interprets payload bytes as time, temperatures, counters, and status values. Grafana is only the presentation layer; it must never create telemetry that the upstream decoder did not produce.

### Key result

Audio decoding and telemetry visualization are separate responsibilities.

## Slide 04 - End-to-End Architecture

### สคริปต์ไทย

เส้นทางข้อมูลมีหกขั้นครับ เริ่มจากดาวน์โหลด SatNOGS OGG พร้อม metadata ของ observation จากนั้นแปลงเป็น mono PCM WAV ที่ 48 kilohertz เพื่อให้ GNU Radio อ่านได้แบบคงที่ GNU Radio demodulate FSK 9600 baud และ AX.25 deframer ทำ NRZI, G3RUH descrambling, HDLC framing, bit de-stuffing และ CRC เฟรมที่ผ่านจะออกเป็น KISS แล้วตัวกรองของ KOYO จะรับเฉพาะ path และความยาวที่คาดไว้ หลังจากนั้น decoder สร้าง telemetry และเขียนลง InfluxDB เพื่อให้ Grafana query ข้อควรจำคือ SatNOGS control frame อยู่ข้างเส้นทางหลัก ใช้ตรวจคำตอบเท่านั้น ไม่ได้ใช้เป็น input ของ decoder

### English backup

The pipeline has six stages: SatNOGS OGG acquisition, 48-kilohertz mono PCM conversion, GNU Radio FSK demodulation, G3RUH AX.25 and CRC validation, KOYO telemetry decoding, and InfluxDB/Grafana output. SatNOGS demodulated frames are placed beside this pipeline as validation controls only. They are never used as the local decoder input.

### Key result

`OGG -> WAV -> GNU Radio -> AX.25/KISS -> KOYO decoder -> InfluxDB/Grafana`

## Slide 05 - Stage 1: SatNOGS Observation Acquisition

### สคริปต์ไทย

ขั้นแรกคือเลือก observation ที่มี audio และข้อมูล demodulated สำหรับใช้เป็น control ตัวอย่างเดโมคือ observation 14909703 จากสถานี MAUSyagi-AK เริ่มบันทึกเวลา 18:43:47 UTC ไฟล์ OGG มีขนาดประมาณ 10.4 megabytes และยาวประมาณ 9 นาที 10 วินาที ระบบเก็บ observation ID, เวลา และสถานีไว้กับผลการถอด เพื่อย้อนตรวจได้ว่าแต่ละค่าใน dashboard มาจาก pass ไหน คำว่า latest ในระบบนี้หมายถึง observation ล่าสุดที่ถูกอัปโหลดมายัง SatNOGS เพราะ SatNOGS เป็น store-and-forward ไม่ใช่ stream RF แบบต่อเนื่อง

### English backup

The acquisition stage selects an observation with both audio and a demodulated control. The demonstration uses observation 14909703 from MAUSyagi-AK, starting at 18:43:47 UTC. Its OGG file is about 10.4 megabytes and about nine minutes ten seconds long. Observation ID, station, and time are preserved for traceability. Here, latest means the newest uploaded SatNOGS observation, not continuous live RF.

### Key result

Observation `14909703` was acquired with traceable source metadata.

## Slide 06 - Stage 2: Audio Preparation

### สคริปต์ไทย

OGG เป็นไฟล์บีบอัดและรูปแบบ sample ภายในอาจไม่เหมาะกับ flowgraph โดยตรง ระบบจึงใช้ FFmpeg แปลงเป็น WAV แบบ mono, 48 kilohertz, signed 16-bit PCM สำหรับ observation เดโม ไฟล์ WAV มีขนาดประมาณ 52.8 megabytes จาก OGG 10.4 megabytes ขนาดที่เพิ่มขึ้นเป็นเรื่องปกติเพราะ WAV ไม่บีบอัด จุดสำคัญคือ sample rate 48 kilohertz หารด้วย symbol rate 9600 ได้ 5 samples per symbol ซึ่งเหมาะกับ clock recovery ผลลัพธ์ขั้นนี้คือไฟล์เสียง input ที่แน่นอนและทำซ้ำได้สำหรับ GNU Radio

### English backup

The compressed OGG is converted with FFmpeg to mono, 48-kilohertz, signed 16-bit PCM WAV. For the demo observation, the WAV is about 52.8 megabytes compared with the 10.4-megabyte OGG, which is expected for uncompressed audio. A 48-kilohertz sample rate gives five samples per 9600-baud symbol. The result is a deterministic GNU Radio input.

### Key result

`10.4 MB OGG -> 52.8 MB WAV | mono | 48 kHz | PCM16`

## Slide 07 - Stage 3: GNU Radio Demodulation

### สคริปต์ไทย

ใน GNU Radio ใช้ chain สำหรับ FSK 9600 baud ค่า input 48 kilohertz, deviation 3 kilohertz และ clock recovery bandwidth 0.15 หลัง demodulation จะเข้าสู่ AX.25 deframer ที่จัดการ NRZI และ G3RUH scrambling ตามสัญญาณ UHF ของ KOYO แล้วจึงค้นหา HDLC flags, ลบ stuffed bits และตรวจ CRC ผลลัพธ์ถูกเขียนเป็น KISS เพื่อให้ Python อ่านต่อได้ Flowgraph อยู่ในไฟล์ koyo_audio_rx.grc และสามารถเปิดแก้ใน GNU Radio Companion ได้ สำหรับ observation เดโม GNU Radio สร้าง KISS output 6 เฟรม ก่อนผ่านตัวกรองเฉพาะของ KOYO

### English backup

GNU Radio demodulates 9600-baud FSK from 48-kilohertz audio using a 3-kilohertz deviation and 0.15 clock-recovery bandwidth. The AX.25 deframer handles NRZI, G3RUH descrambling, HDLC flag detection, bit de-stuffing, and CRC. Output is written as KISS for the Python validation stage. The editable flowgraph is koyo_audio_rx.grc. The demo observation produced six captured KISS frames.

### Key result

GNU Radio produced `6 KISS frames` from the demo OGG-derived WAV.

## Slide 08 - Stage 4: AX.25 and KOYO Frame Validation

### สคริปต์ไทย

ไม่ใช่ทุก PDU ที่ออกจาก chain จะเป็น telemetry ที่ใช้ได้ ตัวกรองจึงตรวจสี่อย่าง ได้แก่ CRC จาก deframer, ความยาวเฟรม 263 bytes, AX.25 path ที่คาดไว้คือ KOYOSC ไป GS-H20 และชนิดเฟรม control 03 กับ PID F0 เฟรมสั้นหรือ path ไม่ตรงจะถูกเก็บเป็น diagnostic แต่ไม่ส่งเข้า telemetry decoder สำหรับ observation 14909703 จาก KISS 6 เฟรม เหลือ valid KOYO 2 เฟรม และหนึ่งเฟรมตรงกับ SatNOGS control แบบ byte-for-byte นี่คือหลักฐานว่าลำดับบิตที่ได้จาก audio ถูกต้องจริงอย่างน้อยหนึ่งเฟรม

### English backup

Not every diagnostic PDU is valid telemetry. The filter requires deframer CRC success, the expected 263-byte frame length, the KOYOSC-to-GS-H20 AX.25 path, control 03, and PID F0. Short or mismatched frames are retained only as diagnostics. For observation 14909703, six KISS frames became two valid KOYO frames, with one byte-exact SatNOGS control match.

### Key result

`6 captured -> 2 valid KOYO -> 1 byte-exact control match`

## Slide 09 - Stage 5: Multi-Station Audio Validation

### สคริปต์ไทย

เพื่อไม่ให้ผลขึ้นกับสถานีเดียว ผมทดสอบห้า observations จากสี่สถานี ได้แก่ MAUSyagi, EA3AGB, W6MSU UHF และ MAUSyagi-AK ทุก observation ผ่านเกณฑ์ว่าต้องมี valid local frame และ exact match อย่างน้อยหนึ่งเฟรม รวมได้ local valid 22 เฟรม และ exact match 20 เฟรม ตารางแสดง recovery ของแต่ละ pass ตั้งแต่ 2.9 ถึง 100 เปอร์เซ็นต์ ความแตกต่างนี้สะท้อนคุณภาพเสียง SNR, tuning, Doppler และ receiver configuration แต่การที่ทั้งห้ารายการมี exact match แสดงว่า chain ทำงานซ้ำได้ข้ามสถานี

### English backup

To avoid a single-station result, five observations from four stations were tested: MAUSyagi, EA3AGB, W6MSU UHF, and MAUSyagi-AK. Every observation produced at least one valid local frame and one exact control match. The total was 22 valid local frames and 20 exact matches. Per-pass recovery ranges from 2.9 to 100 percent because SNR, tuning, Doppler, and receiver configuration vary.

### Key result

`5/5 observations passed across 4 receiving stations.`

## Slide 10 - Understanding Recovery Rate and Not Decoded

### สคริปต์ไทย

ค่า recovery รวมคือ exact matches 20 หารด้วย official control frames 74 เท่ากับ 27 เปอร์เซ็นต์ ตัวเลขนี้ไม่ใช่ packet validity ของดาวเทียม และไม่ได้แปลว่า decoder ผิด 73 เปอร์เซ็นต์ มันวัดว่าการตั้งค่า demodulator ปัจจุบันสามารถสร้าง control frame จากไฟล์ OGG ซ้ำได้กี่เฟรม สาเหตุที่พลาดได้มีทั้ง SNR ต่ำ ความถี่คลาด Doppler gain และ clock recovery คำว่า Not decoded ใน validation หมายถึง local chain ไม่ได้ exact match หรือ diagnostic PDU ไม่ผ่านความยาวและ path ส่วน NOT DECODED ใน dashboard หมายถึงยังไม่มี authorized telemetry mapping เป็นคนละบริบทกัน

### English backup

Overall exact recovery is 20 divided by 74 official control frames, or 27 percent. This is not spacecraft packet validity and does not mean that 73 percent of the decoder is wrong. It measures how many control frames the current local demodulator reproduces from OGG. Audio SNR, tuning, Doppler, gain, and clock recovery affect this value. In validation, not decoded means no local exact recovery. In the dashboard, NOT DECODED means no authorized telemetry mapping. These are different contexts.

### Key result

`27%` is local OGG recovery, not spacecraft health or total decoder accuracy.

## Slide 11 - Historical Mission Coverage

### สคริปต์ไทย

ตาราง validation ห้าแถวเป็นหลักฐานจากเสียงโดยตรง แต่ไม่ใช่ประวัติทั้งหมด ข้อมูล historical จาก SatNOGS demodulated frames ครอบคลุมวันที่ 7 กรกฎาคมถึง 30 สิงหาคม รวม 55 วัน, 17,155 เฟรม, 1,055 observations และ 114 สถานี ตัวเลขนี้ใช้สร้างแนวโน้ม telemetry และทดสอบ dashboard ได้กว้างขึ้น แต่ต้องพูดให้ชัดว่า 17,155 เฟรมไม่ได้ถูกถอดจาก OGG ด้วย GNU Radio ของเราเองทั้งหมด การพิสูจน์ OGG แบบ byte-exact ปัจจุบันมีห้า observations เพราะการแปลง audio ทั้ง 1,464 recordings จะใช้พื้นที่ WAV ประมาณหลัก 100 gigabytes

### English backup

The five-row validation table is direct audio evidence, not the full history. SatNOGS demodulated historical data covers 7 July through 30 August: 55 UTC days, 17,155 frames, 1,055 observations, and 114 stations. This history supports telemetry trends and dashboard testing. However, these 17,155 frames were not all re-demodulated locally from OGG. Direct byte-exact OGG validation currently covers five observations because processing all 1,464 recordings would require roughly 100 gigabytes of temporary WAV storage.

### Key result

Historical breadth and direct OGG proof are reported as separate datasets.

## Slide 12 - Stage 6: Telemetry Confidence Contract

### สคริปต์ไทย

หลังได้เฟรมที่ valid แล้ว decoder จะแปลเฉพาะ field ที่มีหลักฐานและติดป้าย confidence ทุก channel กลุ่ม confirmed ได้แก่ OBC time, boot counter, uptime, packet counter, battery temperatures, CDH และ ADCS temperatures และ health counters กลุ่ม candidate ได้แก่ solar voltage สอง channel และ COMM raw voltage ซึ่งมีพฤติกรรมสมเหตุผลแต่ mapping หรือ engineering scale ยังไม่ยืนยัน ส่วน target fields อย่าง spacecraft mode, battery voltage/current, solar currents และ power distribution จะแสดง NOT DECODED จนกว่าจะมีเอกสารที่ได้รับอนุญาต วิธีนี้ทำให้ dashboard ครบโครงสร้างโดยไม่แต่งตัวเลข

### English backup

After frame validation, every telemetry channel receives an explicit confidence state. Confirmed channels include OBC time, boot counter, uptime, packet counter, battery temperatures, CDH and ADCS temperatures, and health counters. Two solar-voltage channels and a raw COMM voltage remain candidates. Target fields such as spacecraft mode, battery voltage and current, solar currents, and power distribution remain NOT DECODED until an authorized mapping is available. This gives a complete layout without fabricated telemetry.

### Key result

`CONFIRMED`, `CANDIDATE`, and `NOT DECODED` are never mixed.

## Slide 13 - Stage 7: InfluxDB and Full Grafana Dashboard

### สคริปต์ไทย

ข้อมูลถูกเขียนลง InfluxDB สองแบบ แบบแรกคือ beacon channel/value สำหรับกราฟตามเวลา พร้อม tags เช่น quality, unit, source และ observation ID แบบที่สองคือ decoder_run ซึ่งเก็บสถานะ PASS, สถานี, จำนวน KISS, valid frames, exact matches, recovery และ raw HEX ล่าสุด Grafana รุ่นเต็มมี 43 panels ครอบคลุม summary, orbit, decoder evidence, solar, battery, power distribution, comms, thermal, health, OBC และ recent values มี live Flux queries 22 targets และผ่าน validator 22 จาก 22 ช่องที่ไม่มี mapping จะยังปรากฏในตำแหน่งที่ควรอยู่ แต่แสดง NOT DECODED สีส้ม

### English backup

InfluxDB stores two operational views. The beacon measurement stores time-series channel/value feedback with quality, unit, source, and observation tags. The decoder_run measurement stores PASS status, station, KISS count, valid frames, exact matches, recovery, and latest raw HEX. The full Grafana dashboard contains 43 panels across summary, orbit, decoder evidence, electrical, battery, power, comms, thermal, health, OBC, and recent values. All 22 live Flux query targets pass validation.

### Key result

`43 panels | 22/22 live queries passed | no fabricated values`

## Slide 14 - Reproducible End-to-End Demo

### สคริปต์ไทย

เดโมใช้คำสั่งเดียว live_refresh.ps1 ระบบจะเปิด local InfluxDB และ Grafana ถ้ายังไม่ทำงาน เลือก observation หรือใช้ ID ที่กำหนด ดาวน์โหลด OGG แปลง WAV เรียก GNU Radio กรองเฟรม เปรียบเทียบ control และ push dashboard ผลการรันล่าสุดกับ observation 14909703 คือ captured KISS 6, valid KOYO 2, exact match 1 และ InfluxDB ตอบ HTTP 204 หลังจากนั้น dashboard แสดง PASS และ raw HEX ของเฟรมล่าสุด เดโมนี้จึงพิสูจน์เส้นทาง end-to-end แต่ latest ยังหมายถึงไฟล์อัปโหลดล่าสุด ไม่ใช่ live RF socket

### English backup

The live_refresh command runs the complete path. It starts local services if needed, selects an observation, downloads OGG, creates WAV, invokes GNU Radio, filters and compares frames, and pushes the result to the dashboard. The verified run for observation 14909703 produced six KISS frames, two valid KOYO frames, one exact match, and an HTTP 204 InfluxDB write. Grafana then displayed PASS and the latest raw HEX. Latest still means the newest uploaded file, not a live RF socket.

### Key result

The one-command demo completed from SatNOGS audio to Grafana with `HTTP 204`.

## Slide 15 - Limitations, Next Steps, and Conclusion

### สคริปต์ไทย

สรุปครับ งานนี้พิสูจน์ว่าเราสามารถเริ่มจาก SatNOGS audio และถอดเป็นเฟรม KOYO ที่ตรงกับ control ได้จริง ระบบทำซ้ำได้ มี flowgraph แก้ไขได้ มี validation ข้ามสถานี และมี dashboard ที่บอก confidence ตรงไปตรงมา ข้อจำกัดคือ recovery จาก OGG รวมยัง 27 เปอร์เซ็นต์, direct audio validation มีห้า observations, SatNOGS ไม่ใช่ RF live stream และ telemetry mappings บางส่วนยัง candidate หรือ unavailable งานถัดไปคือปรับ demodulator แบบ adaptive, batch audio เพิ่มโดยไม่เก็บ WAV ถาวร, ยืนยัน field mappings จากแหล่งที่ได้รับอนุญาต และเพิ่ม automated regression tests ก่อน deployment

### English backup

In conclusion, the project proves a real SatNOGS-audio-to-KOYO-frame path with byte-exact control matches. It is reproducible, editable, validated across stations, and honest about telemetry confidence. Current limitations are 27-percent overall OGG recovery, five directly tested observations, store-and-forward rather than live RF, and remaining candidate or unavailable mappings. Next steps are adaptive demodulator tuning, streaming batch processing without permanent WAV files, authorized mapping validation, and broader automated regression tests.

### Key result

The decoder path is proven; the remaining work is recovery optimization and authorized mapping completion.

## Likely Questions and Answers

### 1. Why do you need GNU Radio if SatNOGS already provides HEX?

ไทย: เพราะโจทย์คือพิสูจน์ decoder ของเราเองจากสัญญาณเสียงครับ HEX ของ SatNOGS ใช้เป็น control เพื่อวัดว่าคำตอบตรงกัน ไม่ได้ใช้แทน input

English: The goal is to prove our own decoder from audio. SatNOGS HEX is an independent control, not the decoder input.

### 2. Is this real-time?

ไทย: เป็นการอัปเดตจาก observation ล่าสุดแบบ store-and-forward ยังไม่ใช่ continuous RF stream ถ้าจะ real-time จริงต้องต่อ SDR หรือ ground-station socket เข้าหน้า GNU Radio

English: It processes the latest uploaded observation. Continuous real-time operation would require an SDR or ground-station stream connected to GNU Radio.

### 3. Why is recovery only 27 percent?

ไทย: เป็นอัตรา exact reproduction จากไฟล์เสียงด้วยค่าตั้งปัจจุบัน คุณภาพเสียงและ Doppler ต่างกันในแต่ละสถานี แต่ทุก observation ที่เลือกมี exact match อย่างน้อยหนึ่งเฟรม

English: It measures exact reproduction from OGG under one parameter set. Audio conditions and Doppler vary, but every selected observation produced at least one exact match.

### 4. Does Not decoded mean the satellite sent bad data?

ไทย: ไม่จำเป็นครับ ใน validation หมายถึง local demodulator ยังถอด control frame นั้นไม่ได้ ส่วนใน dashboard หมายถึงยังไม่มี field mapping ที่ได้รับอนุญาต

English: No. In validation it means no local recovery; in the dashboard it means no authorized field mapping.

### 5. How do you know a local frame is correct?

ไทย: ผ่าน CRC, ความยาว 263 bytes, AX.25 path และ frame type ที่คาดไว้ และมีการเปรียบเทียบ byte-for-byte กับ control ของ observation เดียวกัน

English: It passes CRC, length, AX.25 path, and frame-type checks, then matches a control frame byte for byte.

### 6. Why were only five audio observations tested?

ไทย: เลือกเป็น controlled sample จากหลายสถานีเพื่อพิสูจน์ end-to-end ก่อน การแปลง OGG ทั้ง 1,464 observations เป็น WAV พร้อมกันจะใช้พื้นที่ประมาณหลัก 100 GB

English: Five multi-station observations form a controlled proof. Converting all 1,464 recordings to temporary WAV would require roughly 100 GB.

### 7. Are all 43 dashboard panels decoded?

ไทย: ไม่ครับ 43 panels หมายถึงโครงสร้าง dashboard ครบ ช่องที่ยืนยันแล้วแสดงค่าจริง ช่อง candidate มีป้าย และช่องที่ไม่มี mapping แสดง NOT DECODED

English: No. Forty-three panels means complete layout coverage. Confirmed values are real, candidates are labelled, and unavailable mappings show NOT DECODED.

### 8. What did you personally implement?

ไทย: ผมประกอบและทดสอบ audio pipeline, GNU Radio flowgraph, frame filtering, byte-exact validation, telemetry ingestion, dashboard contract, query validator, รายงาน coverage และเดโมคำสั่งเดียว

English: I implemented and tested the audio pipeline, GNU Radio flowgraph, frame filtering, byte-exact validation, telemetry ingestion, dashboard contract, query validator, coverage reporting, and one-command demo.

### 9. What would improve the decoder next?

ไทย: ทำ Doppler/tuning compensation, ทดลอง clock bandwidth หลายค่าอัตโนมัติ, ใช้ confidence จาก SNR และประมวลผล OGG แบบ streaming เพื่อลดพื้นที่

English: Add Doppler and tuning compensation, automatically sweep clock-recovery settings, use SNR confidence, and stream OGG processing to reduce storage.

### 10. Can this repository be public?

ไทย: เผยแพร่ได้เฉพาะชุดที่ผ่านการ sanitize ต้องตัดเอกสาร confidential, raw mission files และ source ที่เปิดเผย byte offsets หรือ mappings ที่ไม่ได้รับอนุญาต

English: Only the sanitized package should be public. Confidential documents, raw mission files, and unauthorized mapping-bearing source must remain excluded.

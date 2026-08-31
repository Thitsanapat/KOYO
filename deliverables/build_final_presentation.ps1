param(
    [string]$OutputDir = $PSScriptRoot
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$dashboardImage = Join-Path $root "local-stack\grafana-data\koyo-dashboard.png"
$grcScreenshot = Join-Path $root "gnuradio\koyo_audio_rx_companion_public.png"
$validationPath = Join-Path $root "reports\koyo_audio_validation.csv"
$coveragePath = Join-Path $root "reports\koyo_historical_coverage.csv"
$coverageSummaryPath = Join-Path $root "reports\koyo_historical_summary.json"
$scriptPath = Join-Path $OutputDir "KOYO_PRESENTATION_SCRIPT_TH_EN.md"
$pptxPath = Join-Path $OutputDir "KOYO_Beacon_Decoder_Final_Presentation.pptx"
$pdfPath = Join-Path $OutputDir "KOYO_Beacon_Decoder_Final_Presentation.pdf"
$previewDir = Join-Path $OutputDir "presentation-preview"

@($dashboardImage, $grcScreenshot, $validationPath, $coveragePath, $coverageSummaryPath, $scriptPath) |
    ForEach-Object { if (-not (Test-Path $_)) { throw "Presentation input missing: $_" } }
New-Item -ItemType Directory -Force -Path $OutputDir, $previewDir | Out-Null

$validation = @(Import-Csv $validationPath)
$coverage = @(Import-Csv $coveragePath)
$coverageSummary = Get-Content $coverageSummaryPath -Raw | ConvertFrom-Json
$validTotal = ($validation | Measure-Object valid_koyo_frames -Sum).Sum
$matchTotal = ($validation | Measure-Object byte_exact_matches -Sum).Sum
$officialTotal = ($validation | Measure-Object official_control_frames -Sum).Sum
$passTotal = @($validation | Where-Object result -eq "PASS").Count
$recovery = [Math]::Round(100 * $matchTotal / $officialTotal, 1)

function Color([int]$r, [int]$g, [int]$b) { $r + 256 * $g + 65536 * $b }
$C = @{
    Background = Color 10 13 18
    Panel = Color 18 23 31
    Panel2 = Color 25 31 41
    Text = Color 236 241 247
    Muted = Color 155 166 181
    Cyan = Color 49 166 232
    Green = Color 49 204 112
    Orange = Color 246 153 41
    Red = Color 239 81 62
    Grid = Color 49 59 73
}

function Add-Text($slide, [string]$text, [double]$left, [double]$top, [double]$width, [double]$height,
                  [double]$size = 18, [int]$color = $C.Text, [bool]$bold = $false,
                  [string]$font = "Aptos", [int]$align = 1) {
    $shape = $slide.Shapes.AddTextbox(1, $left, $top, $width, $height)
    $shape.TextFrame2.MarginLeft = 0
    $shape.TextFrame2.MarginRight = 0
    $shape.TextFrame2.MarginTop = 0
    $shape.TextFrame2.MarginBottom = 0
    $shape.TextFrame2.WordWrap = -1
    $shape.TextFrame2.TextRange.Text = $text
    $shape.TextFrame2.TextRange.Font.Name = $font
    $shape.TextFrame2.TextRange.Font.Size = $size
    $shape.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = $color
    $shape.TextFrame2.TextRange.Font.Bold = $(if ($bold) { -1 } else { 0 })
    $shape.TextFrame2.TextRange.ParagraphFormat.Alignment = $align
    $shape
}

function Add-Box($slide, [double]$left, [double]$top, [double]$width, [double]$height,
                 [int]$fill = $C.Panel, [int]$line = $C.Grid) {
    $shape = $slide.Shapes.AddShape(1, $left, $top, $width, $height)
    $shape.Fill.ForeColor.RGB = $fill
    $shape.Line.ForeColor.RGB = $line
    $shape.Line.Weight = 1
    $shape
}

function Add-Rule($slide, [double]$x1, [double]$y1, [double]$x2, [double]$y2,
                  [int]$color = $C.Cyan, [double]$weight = 2) {
    $line = $slide.Shapes.AddLine($x1, $y1, $x2, $y2)
    $line.Line.ForeColor.RGB = $color
    $line.Line.Weight = $weight
    $line
}

function New-Slide($presentation, [string]$title, [string]$kicker = "KOYO BEACON DECODER") {
    $slide = $presentation.Slides.Add($presentation.Slides.Count + 1, 12)
    $slide.FollowMasterBackground = 0
    $slide.Background.Fill.Solid()
    $slide.Background.Fill.ForeColor.RGB = $C.Background
    Add-Text $slide $kicker 42 24 640 18 10 $C.Cyan $true "Aptos" | Out-Null
    Add-Text $slide $title 42 48 860 44 27 $C.Text $true "Aptos Display" | Out-Null
    Add-Rule $slide 42 102 918 102 $C.Grid 1 | Out-Null
    Add-Text $slide ("{0:D2}" -f $slide.SlideIndex) 888 505 30 15 9 $C.Muted $false "Consolas" 3 | Out-Null
    $slide
}

function Add-Result($slide, [string]$text, [int]$color = $C.Green) {
    Add-Box $slide 46 450 868 49 $C.Panel2 $color | Out-Null
    Add-Text $slide "RESULT" 62 465 94 14 9.5 $C.Muted $true "Consolas" | Out-Null
    Add-Text $slide $text 155 459 739 24 13.5 $color $true | Out-Null
}

function Add-Column($slide, [double]$x, [string]$title, [string[]]$lines, [int]$accent = $C.Cyan) {
    Add-Box $slide $x 137 410 278 $C.Panel $C.Grid | Out-Null
    Add-Text $slide $title ($x + 20) 158 370 22 11 $accent $true "Consolas" | Out-Null
    $y = 205
    foreach ($line in $lines) {
        Add-Text $slide "-" ($x + 20) $y 16 20 13 $accent $true "Consolas" | Out-Null
        Add-Text $slide $line ($x + 42) $y 342 42 13 $C.Text | Out-Null
        $y += 49
    }
}

function Add-TwoColumnSlide($presentation, [string]$title, [string]$leftTitle, [string[]]$leftLines,
                            [string]$rightTitle, [string[]]$rightLines, [string]$result,
                            [int]$rightAccent = $C.Green) {
    $slide = New-Slide $presentation $title
    Add-Column $slide 46 $leftTitle $leftLines $C.Cyan
    Add-Column $slide 504 $rightTitle $rightLines $rightAccent
    Add-Result $slide $result
    $slide
}

function Set-SpeakerNotes($slide, [string]$notes) {
    try {
        $body = $slide.NotesPage.Shapes.Placeholders.Item(2)
        $body.TextFrame.TextRange.Text = $notes
    } catch {
        Write-Warning "Could not attach notes to slide $($slide.SlideIndex): $($_.Exception.Message)"
    }
}

$ppt = $null
$presentation = $null
$originalUserName = $null
try {
    $ppt = New-Object -ComObject PowerPoint.Application
    try {
        $originalUserName = $ppt.UserName
        $ppt.UserName = "KOYO Project"
    } catch {}
    $ppt.Visible = -1
    $ppt.DisplayAlerts = 1
    $presentation = $ppt.Presentations.Add()
    $presentation.PageSetup.SlideWidth = 960
    $presentation.PageSetup.SlideHeight = 540

    # 01
    $s = New-Slide $presentation "SatNOGS Audio to Operational Telemetry" "KOYO FINAL PROJECT"
    Add-Text $s "BEACON DECODER" 42 130 700 58 38 $C.Text $true "Aptos Display" | Out-Null
    Add-Text $s "GNU Radio | G3RUH AX.25 | CRC-valid 263-byte frames" 44 198 820 28 18 $C.Cyan | Out-Null
    $metrics = @(
        @("$passTotal / $($validation.Count)", "observations passed", $C.Green),
        @("$validTotal", "valid local frames", $C.Cyan),
        @("$matchTotal", "byte-exact matches", $C.Orange)
    )
    for ($i = 0; $i -lt $metrics.Count; $i++) {
        $x = 42 + ($i * 292)
        Add-Box $s $x 278 270 122 $C.Panel $C.Grid | Out-Null
        Add-Text $s $metrics[$i][0] ($x + 20) 298 230 46 33 $metrics[$i][2] $true "Aptos Display" | Out-Null
        Add-Text $s $metrics[$i][1] ($x + 20) 350 230 22 14 $C.Muted | Out-Null
    }
    Add-Text $s "Final presentation | 31 Aug 2026" 44 468 500 18 11 $C.Muted $false "Consolas" | Out-Null

    # 02
    $s = Add-TwoColumnSlide $presentation "Objective and Acceptance Criteria" "PROJECT OBJECTIVE" @(
        "Decode the beacon from SatNOGS OGG audio.",
        "Verify locally recovered frames independently.",
        "Feed traceable telemetry into an operational dashboard."
    ) "STRICT PASS CRITERION" @(
        "At least one CRC-valid local KOYO frame.",
        "Expected 263-byte frame, AX.25 path, and type.",
        "At least one byte-exact match for the same observation."
    ) "Success is reproducible and measurable, not based on visual similarity."

    # 03
    $s = Add-TwoColumnSlide $presentation "What Each Stage Means" "SIGNAL SIDE" @(
        "Beacon: periodic spacecraft status message.",
        "OGG: audio recorded by a SatNOGS ground station.",
        "Demodulation: convert 9600-baud FSK audio back to bits."
    ) "DATA SIDE" @(
        "AX.25/HDLC: frame boundaries, addressing, and CRC.",
        "Telemetry: interpret payload bytes as engineering values.",
        "Dashboard: present evidence without inventing data."
    ) "Audio decoding and telemetry visualization are separate responsibilities." $C.Cyan

    # 04
    $s = New-Slide $presentation "End-to-End Architecture"
    $pipeline = @(
        @("SatNOGS OGG", "recording + metadata"),
        @("PCM WAV", "mono / 48 kHz / PCM16"),
        @("GNU Radio", "FSK / 9600 baud"),
        @("AX.25 + KISS", "G3RUH / HDLC / CRC"),
        @("KOYO Decoder", "263-byte filter"),
        @("Influx + Grafana", "evidence + telemetry")
    )
    for ($i = 0; $i -lt $pipeline.Count; $i++) {
        $x = 40 + ($i * 151)
        Add-Box $s $x 160 128 112 $C.Panel $C.Grid | Out-Null
        Add-Text $s $pipeline[$i][0] ($x + 10) 184 108 30 14 $C.Text $true | Out-Null
        Add-Text $s $pipeline[$i][1] ($x + 10) 228 108 34 10 $C.Muted | Out-Null
        if ($i -lt 5) {
            Add-Rule $s ($x + 128) 216 ($x + 146) 216 $C.Cyan 2 | Out-Null
            Add-Text $s ">" ($x + 134) 205 12 20 14 $C.Cyan $true "Consolas" | Out-Null
        }
    }
    Add-Box $s 189 310 582 89 $C.Panel2 $C.Orange | Out-Null
    Add-Text $s "INDEPENDENT CONTROL" 209 329 180 18 10 $C.Orange $true "Consolas" | Out-Null
    Add-Text $s "SatNOGS demodulated frames are used only for byte-exact comparison. They are not local decoder input." 389 324 355 52 12.5 $C.Text | Out-Null
    Add-Result $s "OGG -> WAV -> GNU Radio -> AX.25/KISS -> decoder -> dashboard" $C.Cyan

    # 05
    $s = Add-TwoColumnSlide $presentation "Stage 1 - SatNOGS Observation Acquisition" "DEMO OBSERVATION" @(
        "Observation 14909703 from MAUSyagi-AK.",
        "Start: 2026-08-30 18:43:47 UTC.",
        "Duration 00:09:09.61; OGG size 10,431,019 bytes."
    ) "TRACEABILITY AND SCOPE" @(
        "Observation ID, station, and UTC follow every result.",
        "Same-observation demodulated frames are controls.",
        "Latest means newest upload, not continuous live RF."
    ) "Observation 14909703 acquired with complete source metadata."

    # 06
    $s = Add-TwoColumnSlide $presentation "Stage 2 - Audio Preparation" "SOURCE AUDIO" @(
        "Compressed SatNOGS Vorbis OGG.",
        "10.4 MB for the demonstration observation.",
        "Converted automatically with FFmpeg."
    ) "GNU RADIO INPUT" @(
        "Mono, 48 kHz, signed 16-bit PCM WAV.",
        "52.8 MB uncompressed output.",
        "Five samples per 9600-baud symbol."
    ) "A deterministic 48 kHz PCM input is created for GNU Radio."

    # 07
    $s = New-Slide $presentation "Stage 3 - GNU Radio Demodulation"
    $s.Shapes.AddPicture($grcScreenshot, 0, -1, 42, 124, 660, 305) | Out-Null
    Add-Box $s 724 124 190 305 $C.Panel $C.Grid | Out-Null
    Add-Text $s "PARAMETERS" 742 143 150 18 10 $C.Cyan $true "Consolas" | Out-Null
    Add-Text $s "FSK: 9600 baud`nInput: 48 kHz`nDeviation: 3 kHz`nClock BW: 0.15" 742 178 150 104 13 $C.Text | Out-Null
    Add-Text $s "DEFRAMER" 742 307 150 18 10 $C.Green $true "Consolas" | Out-Null
    Add-Text $s "NRZI`nG3RUH descramble`nHDLC + CRC`nKISS output" 742 338 150 78 12 $C.Muted | Out-Null
    Add-Result $s "Six KISS frames were captured from the demo OGG-derived WAV."

    # 08
    $s = Add-TwoColumnSlide $presentation "Stage 4 - AX.25 and KOYO Frame Validation" "ACCEPTANCE GATES" @(
        "CRC accepted by the AX.25 deframer.",
        "Exactly 263 bytes with KOYOSC -> GS-H20 path.",
        "Expected control 03 and PID F0 frame type."
    ) "DEMO FRAME FUNNEL" @(
        "Six KISS frames captured.",
        "Two frames passed all KOYO checks.",
        "One frame matched SatNOGS control byte for byte."
    ) "6 captured -> 2 valid KOYO -> 1 byte-exact control match."

    # 09
    $s = New-Slide $presentation "Stage 5 - Multi-Station Audio Validation"
    $headers = @("OBSERVATION", "STATION", "CONTROL", "LOCAL", "EXACT", "RECOVERY", "RESULT")
    $columns = @(50, 220, 455, 550, 625, 705, 820)
    for ($i = 0; $i -lt $headers.Count; $i++) {
        Add-Text $s $headers[$i] $columns[$i] 132 $(if ($i -eq 1) { 230 } else { 120 }) 18 10 $C.Muted $true "Consolas" | Out-Null
    }
    Add-Rule $s 48 156 910 156 $C.Grid 1 | Out-Null
    for ($r = 0; $r -lt $validation.Count; $r++) {
        $row = $validation[$r]
        $y = 175 + ($r * 49)
        if ($r % 2 -eq 0) { Add-Box $s 46 ($y - 8) 868 38 $C.Panel $C.Panel | Out-Null }
        Add-Text $s $row.obs_id $columns[0] $y 145 18 12 $C.Text $false "Consolas" | Out-Null
        Add-Text $s $row.station $columns[1] $y 230 18 12 $C.Text | Out-Null
        Add-Text $s $row.official_control_frames $columns[2] $y 70 18 12 $C.Text $false "Consolas" | Out-Null
        Add-Text $s $row.valid_koyo_frames $columns[3] $y 70 18 12 $C.Cyan $true "Consolas" | Out-Null
        Add-Text $s $row.byte_exact_matches $columns[4] $y 70 18 12 $C.Orange $true "Consolas" | Out-Null
        Add-Text $s "$($row.recovery_rate_percent)%" $columns[5] $y 90 18 12 $C.Text $true "Consolas" | Out-Null
        Add-Text $s $row.result $columns[6] $y 90 18 12 $C.Green $true "Consolas" | Out-Null
    }
    Add-Result $s "$passTotal/$($validation.Count) PASS across four stations | $validTotal valid local | $matchTotal exact matches"

    # 10
    $s = Add-TwoColumnSlide $presentation "Understanding Recovery Rate and Not Decoded" "27% EXACT RECOVERY" @(
        "$matchTotal exact matches divided by $officialTotal controls.",
        "Measures local OGG reproduction under current settings.",
        "Affected by SNR, tuning, Doppler, gain, and clock recovery."
    ) "TWO DIFFERENT MEANINGS" @(
        "Validation: no exact local recovery or rejected diagnostic PDU.",
        "Dashboard: no authorized telemetry field mapping.",
        "Neither automatically means invalid spacecraft data."
    ) "27% is audio recovery, not spacecraft health or total decoder accuracy." $C.Orange

    # 11
    $s = New-Slide $presentation "Historical Mission Coverage"
    $historyMetrics = @(
        @($coverageSummary.days_with_frames, "UTC days", $C.Green),
        @($coverageSummary.distinct_observations, "observations / 114 stations", $C.Cyan),
        @($coverageSummary.decoded_frames, "SatNOGS-demodulated frames", $C.Orange)
    )
    for ($i = 0; $i -lt $historyMetrics.Count; $i++) {
        $x = 46 + ($i * 299)
        Add-Box $s $x 124 270 92 $C.Panel $C.Grid | Out-Null
        Add-Text $s ("{0:N0}" -f $historyMetrics[$i][0]) ($x + 18) 139 230 37 28 $historyMetrics[$i][2] $true "Aptos Display" | Out-Null
        Add-Text $s $historyMetrics[$i][1] ($x + 18) 180 230 18 11.5 $C.Muted | Out-Null
    }
    Add-Text $s "$($coverage[0].date_utc) to $($coverage[-1].date_utc) UTC" 48 232 500 18 12 $C.Text $true "Consolas" | Out-Null
    $maxDaily = ($coverage | Measure-Object decoded_frames -Maximum).Maximum
    for ($i = 0; $i -lt $coverage.Count; $i++) {
        $height = 8 + (122 * ([double]$coverage[$i].decoded_frames / [double]$maxDaily))
        $bar = $s.Shapes.AddShape(1, 48 + ($i * 14.7), 410 - $height, 9.5, $height)
        $bar.Fill.ForeColor.RGB = $C.Cyan
        $bar.Line.Visible = 0
    }
    Add-Rule $s 48 410 906 410 $C.Grid 1 | Out-Null
    Add-Text $s "JUL 07" 48 416 100 16 9 $C.Muted $false "Consolas" | Out-Null
    Add-Text $s "AUG 01" 414 416 100 16 9 $C.Muted $false "Consolas" | Out-Null
    Add-Text $s "AUG 30" 806 416 100 16 9 $C.Muted $false "Consolas" 3 | Out-Null
    Add-Result $s "17,155 historical controls; direct byte-exact OGG proof covers five observations." $C.Orange

    # 12
    $s = New-Slide $presentation "Stage 6 - Telemetry Confidence Contract"
    $confidence = @(
        @("CONFIRMED", $C.Green, "OBC time and counters`nBattery TH0 / TH1`nCDH and ADCS temperatures`nPIB and SD health counters"),
        @("CANDIDATE", $C.Orange, "Solar voltage channels 1 / 2`nCOMM raw voltage`nBehavior plausible`nMapping or scale unverified"),
        @("NOT DECODED", $C.Red, "Spacecraft mode`nBattery voltage / current`nSolar currents`nPower distribution fields")
    )
    for ($i = 0; $i -lt $confidence.Count; $i++) {
        $x = 46 + ($i * 292)
        Add-Box $s $x 139 270 270 $C.Panel $confidence[$i][1] | Out-Null
        Add-Text $s $confidence[$i][0] ($x + 18) 162 234 28 16 $confidence[$i][1] $true "Consolas" | Out-Null
        Add-Text $s $confidence[$i][2] ($x + 18) 214 234 154 13 $C.Text | Out-Null
    }
    Add-Result $s "Complete target structure with explicit confidence and zero fabricated values."

    # 13
    $s = New-Slide $presentation "Stage 7 - InfluxDB and Full Grafana Dashboard"
    $s.Shapes.AddPicture($dashboardImage, 0, -1, 42, 122, 876, 326) | Out-Null
    Add-Box $s 42 456 876 44 $C.Panel2 $C.Green | Out-Null
    Add-Text $s "43 PANELS" 56 469 120 16 11 $C.Green $true "Consolas" | Out-Null
    Add-Text $s "decoder status + raw HEX" 184 469 210 16 11 $C.Text $true | Out-Null
    Add-Text $s "22 / 22 Flux queries passed" 410 469 240 16 11 $C.Cyan $true | Out-Null
    Add-Text $s "no fabricated values" 680 469 210 16 11 $C.Orange $true | Out-Null

    # 14
    $s = Add-TwoColumnSlide $presentation "Reproducible End-to-End Demo" "ONE COMMAND" @(
        "live_refresh.ps1 -ObsId 14909703",
        "Download OGG, create WAV, run GNU Radio.",
        "Filter, compare controls, and push the dashboard."
    ) "VERIFIED OUTPUT" @(
        "Six KISS frames; two valid KOYO frames.",
        "One byte-exact control match.",
        "InfluxDB HTTP 204; Grafana PASS plus raw HEX."
    ) "SatNOGS audio -> local GNU Radio -> InfluxDB/Grafana completed successfully."

    # 15
    $s = Add-TwoColumnSlide $presentation "Limitations, Next Steps, and Conclusion" "CURRENT LIMITATIONS" @(
        "27% exact OGG recovery; five direct audio tests.",
        "SatNOGS is store-and-forward, not continuous RF.",
        "Candidate and unavailable telemetry mappings remain."
    ) "NEXT TECHNICAL STEPS" @(
        "Adaptive Doppler, tuning, and clock recovery.",
        "Stream OGG processing without permanent WAV files.",
        "Expand validation and authorize remaining mappings."
    ) "The audio-to-frame path is proven; recovery optimization and mapping validation remain."

    $scriptText = Get-Content $scriptPath -Raw -Encoding UTF8
    $noteSections = [regex]::Matches($scriptText, '(?ms)^## Slide (?<number>\d{2})[^\r\n]*\r?\n(?<body>.*?)(?=^## Slide |^## Likely Questions|\z)')
    foreach ($section in $noteSections) {
        $slideNumber = [int]$section.Groups['number'].Value
        if ($slideNumber -le $presentation.Slides.Count) {
            Set-SpeakerNotes $presentation.Slides.Item($slideNumber) $section.Groups['body'].Value.Trim()
        }
    }

    try { $presentation.BuiltInDocumentProperties.Item("Author").Value = "KOYO Project" } catch {}
    try { $presentation.BuiltInDocumentProperties.Item("Last Save By").Value = "KOYO Project" } catch {}
    try { $presentation.BuiltInDocumentProperties.Item("Company").Value = "" } catch {}

    $presentation.SaveAs($pptxPath, 24)
    $presentation.SaveAs($pdfPath, 32)
    foreach ($slide in $presentation.Slides) {
        $previewPath = Join-Path $previewDir ("slide-{0:D2}.png" -f $slide.SlideIndex)
        $slide.Export($previewPath, "PNG", 1920, 1080)
    }
    Write-Host "Slides: $($presentation.Slides.Count)"
    Write-Host "PPTX: $pptxPath"
    Write-Host "PDF:  $pdfPath"
    Write-Host "Script: $scriptPath"
    Write-Host "Previews: $previewDir"
}
finally {
    if ($presentation) { $presentation.Close() }
    if ($ppt -and $originalUserName) {
        try { $ppt.UserName = $originalUserName } catch {}
    }
    if ($ppt) { $ppt.Quit() }
    if ($presentation) { [Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) | Out-Null }
    if ($ppt) { [Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

& (Join-Path $PSScriptRoot "sanitize_public_metadata.ps1") -PresentationPath $pptxPath -PdfPath $pdfPath

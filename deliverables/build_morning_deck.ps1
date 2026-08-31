param(
    [string]$OutputDir = (Join-Path $PSScriptRoot ".")
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$dashboardImage = Join-Path $root "local-stack\grafana-data\koyo-dashboard.png"
$grcScreenshot = Join-Path $root "gnuradio\koyo_audio_rx_companion.png"
$csvPath = Join-Path $root "reports\koyo_audio_validation.csv"
$coveragePath = Join-Path $root "reports\koyo_historical_coverage.csv"
$coverageSummaryPath = Join-Path $root "reports\koyo_historical_summary.json"
$pptxPath = Join-Path $OutputDir "KOYO_Beacon_Decoder_Final_Presentation.pptx"
$pdfPath = Join-Path $OutputDir "KOYO_Beacon_Decoder_Final_Presentation.pdf"
$dashboardSlidePreviewPath = Join-Path $OutputDir "koyo_dashboard_slide_preview.png"
$scriptPath = Join-Path $OutputDir "KOYO_PRESENTATION_SCRIPT_TH_EN.md"

if (-not (Test-Path $dashboardImage)) { throw "Dashboard screenshot not found: $dashboardImage" }
if (-not (Test-Path $grcScreenshot)) { throw "GNU Radio screenshot not found: $grcScreenshot" }
if (-not (Test-Path $csvPath)) { throw "Validation CSV not found: $csvPath" }
if (-not (Test-Path $coveragePath)) { throw "Coverage CSV not found: $coveragePath" }
if (-not (Test-Path $coverageSummaryPath)) { throw "Coverage summary not found: $coverageSummaryPath" }
if (-not (Test-Path $scriptPath)) { throw "Presentation script not found: $scriptPath" }
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$validation = @(Import-Csv $csvPath)
$coverage = @(Import-Csv $coveragePath)
$coverageSummary = Get-Content $coverageSummaryPath -Raw | ConvertFrom-Json
$validTotal = ($validation | Measure-Object -Property valid_koyo_frames -Sum).Sum
$matchTotal = ($validation | Measure-Object -Property byte_exact_matches -Sum).Sum
$passTotal = @($validation | Where-Object result -eq "PASS").Count
$officialTotal = ($validation | Measure-Object -Property official_control_frames -Sum).Sum
$overallRecovery = [Math]::Round(100.0 * $matchTotal / $officialTotal, 1)
$historyFrames = $coverageSummary.decoded_frames
$historyObservations = $coverageSummary.distinct_observations
$historyDays = $coverageSummary.days_with_frames

function Color([int]$r, [int]$g, [int]$b) { return $r + 256 * $g + 65536 * $b }

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
    return $shape
}

function Add-Box($slide, [double]$left, [double]$top, [double]$width, [double]$height,
                 [int]$fill = $C.Panel, [int]$line = $C.Grid) {
    $shape = $slide.Shapes.AddShape(1, $left, $top, $width, $height)
    $shape.Fill.ForeColor.RGB = $fill
    $shape.Line.ForeColor.RGB = $line
    $shape.Line.Weight = 1
    return $shape
}

function Add-Rule($slide, [double]$x1, [double]$y1, [double]$x2, [double]$y2, [int]$color = $C.Cyan, [double]$weight = 2) {
    $line = $slide.Shapes.AddLine($x1, $y1, $x2, $y2)
    $line.Line.ForeColor.RGB = $color
    $line.Line.Weight = $weight
    return $line
}

function New-Slide($presentation, [string]$title, [string]$kicker = "KOYO BEACON DECODER") {
    $slide = $presentation.Slides.Add($presentation.Slides.Count + 1, 12)
    $slide.FollowMasterBackground = 0
    $slide.Background.Fill.Solid()
    $slide.Background.Fill.ForeColor.RGB = $C.Background
    Add-Text $slide $kicker 42 24 500 18 10 $C.Cyan $true "Aptos" | Out-Null
    Add-Text $slide $title 42 48 850 44 28 $C.Text $true "Aptos Display" | Out-Null
    Add-Rule $slide 42 102 918 102 $C.Grid 1 | Out-Null
    Add-Text $slide ("{0:D2}" -f $slide.SlideIndex) 888 505 30 15 9 $C.Muted $false "Consolas" 3 | Out-Null
    return $slide
}

function Add-ResultBanner($slide, [string]$label, [string]$result, [int]$color = $C.Green) {
    Add-Box $slide 46 449 868 50 $C.Panel2 $color | Out-Null
    Add-Text $slide $label 62 461 150 16 10 $C.Muted $true "Consolas" | Out-Null
    Add-Text $slide $result 206 457 688 24 14 $color $true "Aptos" | Out-Null
}

function Set-SpeakerNotes($slide, [string]$notes) {
    try {
        $body = $slide.NotesPage.Shapes.Placeholders.Item(2)
        $body.TextFrame.TextRange.Text = $notes
    } catch {
        Write-Warning "Could not attach speaker notes to slide $($slide.SlideIndex): $($_.Exception.Message)"
    }
}

$ppt = $null
$presentation = $null
try {
    $ppt = New-Object -ComObject PowerPoint.Application
    $ppt.Visible = -1
    $ppt.DisplayAlerts = 1
    $presentation = $ppt.Presentations.Add()
    $presentation.PageSetup.SlideWidth = 960
    $presentation.PageSetup.SlideHeight = 540

    $s = New-Slide $presentation "SatNOGS Audio to Operational Telemetry" "KOYO"
    Add-Text $s "BEACON DECODER" 42 132 620 58 38 $C.Text $true "Aptos Display" | Out-Null
    Add-Text $s "GNU Radio  |  G3RUH AX.25  |  CRC-valid 263-byte frames" 44 198 760 28 18 $C.Cyan $false | Out-Null
    Add-Box $s 42 278 260 122 $C.Panel $C.Grid | Out-Null
    Add-Text $s "$passTotal / $($validation.Count)" 62 298 220 48 34 $C.Green $true "Aptos Display" | Out-Null
    Add-Text $s "observations passed" 62 350 220 24 14 $C.Muted | Out-Null
    Add-Box $s 326 278 260 122 $C.Panel $C.Grid | Out-Null
    Add-Text $s "$validTotal" 346 298 220 48 34 $C.Cyan $true "Aptos Display" | Out-Null
    Add-Text $s "valid local frames" 346 350 220 24 14 $C.Muted | Out-Null
    Add-Box $s 610 278 308 122 $C.Panel $C.Grid | Out-Null
    Add-Text $s "$matchTotal" 630 298 268 48 34 $C.Orange $true "Aptos Display" | Out-Null
    Add-Text $s "byte-exact control matches" 630 350 268 24 14 $C.Muted | Out-Null
    Add-Text $s "Morning handoff  |  31 Aug 2026" 44 468 520 18 11 $C.Muted $false "Consolas" | Out-Null

    $s = New-Slide $presentation "End-to-End Architecture"
    $labels = @(
        @("SatNOGS OGG", "downloaded observation"),
        @("PCM WAV", "mono / 48 kHz"),
        @("GNU Radio", "FSK / 9600 baud"),
        @("AX.25", "G3RUH + HDLC + CRC"),
        @("KOYO Decoder", "263-byte frames"),
        @("Influx + Grafana", "channel / value feedback")
    )
    for ($i = 0; $i -lt $labels.Count; $i++) {
        $x = 40 + ($i * 151)
        Add-Box $s $x 188 128 106 $C.Panel $C.Grid | Out-Null
        Add-Text $s $labels[$i][0] ($x + 10) 210 108 28 16 $C.Text $true | Out-Null
        Add-Text $s $labels[$i][1] ($x + 10) 246 108 34 10.5 $C.Muted | Out-Null
        if ($i -lt $labels.Count - 1) {
            Add-Rule $s ($x + 128) 241 ($x + 146) 241 $C.Cyan 2 | Out-Null
            Add-Text $s ">" ($x + 134) 230 12 20 14 $C.Cyan $true "Consolas" | Out-Null
        }
    }
    Add-Text $s "Decoder input" 40 330 200 18 11 $C.Muted $true | Out-Null
    Add-Text $s "The OGG recording is the source. SatNOGS demodulated frames are used only as an independent validation control." 40 356 865 44 17 $C.Text | Out-Null
    Add-Text $s "Store-and-forward: newest available upload, not continuous live RF." 40 432 865 26 14 $C.Orange $true | Out-Null

    $s = New-Slide $presentation "Mission Data Coverage"
    Add-Box $s 46 134 270 112 $C.Panel $C.Grid | Out-Null
    Add-Text $s "$historyDays" 66 154 230 42 32 $C.Green $true "Aptos Display" | Out-Null
    Add-Text $s "UTC days with frames" 66 202 230 20 13 $C.Muted | Out-Null
    Add-Box $s 345 134 270 112 $C.Panel $C.Grid | Out-Null
    Add-Text $s ("{0:N0}" -f $historyObservations) 365 154 230 42 32 $C.Cyan $true "Aptos Display" | Out-Null
    Add-Text $s "SatNOGS observations / $($coverageSummary.receiving_stations) stations" 365 202 230 20 12 $C.Muted | Out-Null
    Add-Box $s 644 134 270 112 $C.Panel $C.Grid | Out-Null
    Add-Text $s ("{0:N0}" -f $historyFrames) 664 154 230 42 32 $C.Orange $true "Aptos Display" | Out-Null
    Add-Text $s "decoded frames" 664 202 230 20 13 $C.Muted | Out-Null
    Add-Text $s "$($coverage[0].date_utc)  to  $($coverage[-1].date_utc) UTC" 48 274 500 20 13 $C.Text $true "Consolas" | Out-Null
    Add-Text $s "Daily decoded frame coverage" 48 308 350 18 11 $C.Muted $true | Out-Null
    $maxDaily = ($coverage | Measure-Object -Property decoded_frames -Maximum).Maximum
    $barWidth = 14.7
    for ($i = 0; $i -lt $coverage.Count; $i++) {
        $height = 8 + (135 * ([double]$coverage[$i].decoded_frames / [double]$maxDaily))
        $bar = $s.Shapes.AddShape(1, 48 + ($i * $barWidth), 470 - $height, 9.5, $height)
        $bar.Fill.ForeColor.RGB = $C.Cyan
        $bar.Line.Visible = 0
    }
    Add-Rule $s 48 470 906 470 $C.Grid 1 | Out-Null
    Add-Text $s "JUL 07" 48 480 100 16 9 $C.Muted $false "Consolas" | Out-Null
    Add-Text $s "AUG 01" 414 480 100 16 9 $C.Muted $false "Consolas" | Out-Null
    Add-Text $s "AUG 30" 806 480 100 16 9 $C.Muted $false "Consolas" 3 | Out-Null
    Add-Text $s "The 5-row audio table is a controlled end-to-end sample, not the full history." 48 508 820 18 11 $C.Orange $true | Out-Null

    $s = New-Slide $presentation "GNU Radio Receive Flowgraph"
    $blocks = @(
        @("WAV File Source", "48 kHz mono"),
        @("FSK Demodulator", "9600 baud / clk_bw 0.15"),
        @("AX.25 Deframer", "NRZI + G3RUH + HDLC + CRC"),
        @("KISS File Sink", "validated frame output")
    )
    for ($i = 0; $i -lt $blocks.Count; $i++) {
        $x = 55 + ($i * 222)
        Add-Box $s $x 170 180 116 $C.Panel2 $(if ($i -eq 2) { $C.Green } else { $C.Cyan }) | Out-Null
        Add-Text $s $blocks[$i][0] ($x + 14) 195 152 25 15 $C.Text $true | Out-Null
        Add-Text $s $blocks[$i][1] ($x + 14) 232 152 38 10.5 $C.Muted | Out-Null
        if ($i -lt $blocks.Count - 1) {
            Add-Rule $s ($x + 180) 228 ($x + 214) 228 $C.Cyan 2 | Out-Null
            Add-Text $s ">" ($x + 195) 217 14 20 14 $C.Cyan $true "Consolas" | Out-Null
        }
    }
    Add-Text $s "Editable flowgraph" 56 326 200 18 11 $C.Cyan $true | Out-Null
    Add-Text $s "gnuradio/koyo_audio_rx.grc" 56 352 420 24 17 $C.Text $false "Consolas" | Out-Null
    Add-Text $s "Observed malformed or short PDUs stay diagnostic. Only CRC-valid 263-byte KOYO frames reach telemetry decoding." 56 406 845 48 16 $C.Text | Out-Null

    $s = New-Slide $presentation "GNU Radio Companion - Actual Flowgraph"
    $s.Shapes.AddPicture($grcScreenshot, 0, -1, 42, 124, 876, 362) | Out-Null
    Add-Text $s "Captured from the installed radioconda GNU Radio Companion; the same .grc compiled and produced a byte-exact control match." 44 500 850 18 10 $C.Muted | Out-Null

    $s = New-Slide $presentation "Audio Validation Across Stations"
    $headers = @("OBSERVATION", "STATION", "OFFICIAL", "LOCAL", "EXACT", "RECOVERY", "RESULT")
    $columns = @(50, 220, 455, 550, 625, 705, 820)
    for ($i = 0; $i -lt $headers.Count; $i++) {
        Add-Text $s $headers[$i] $columns[$i] 140 $(if ($i -eq 1) { 230 } else { 120 }) 18 10 $C.Muted $true "Consolas" | Out-Null
    }
    Add-Rule $s 48 164 910 164 $C.Grid 1 | Out-Null
    for ($r = 0; $r -lt $validation.Count; $r++) {
        $row = $validation[$r]
        $y = 184 + ($r * 54)
        if ($r % 2 -eq 0) { Add-Box $s 46 ($y - 9) 868 42 $C.Panel $C.Panel | Out-Null }
        Add-Text $s $row.obs_id $columns[0] $y 145 18 13 $C.Text $false "Consolas" | Out-Null
        Add-Text $s $row.station $columns[1] $y 230 18 13 $C.Text | Out-Null
        Add-Text $s $row.official_control_frames $columns[2] $y 70 18 13 $C.Text $false "Consolas" | Out-Null
        Add-Text $s $row.valid_koyo_frames $columns[3] $y 70 18 13 $C.Cyan $true "Consolas" | Out-Null
        Add-Text $s $row.byte_exact_matches $columns[4] $y 70 18 13 $C.Orange $true "Consolas" | Out-Null
        Add-Text $s "$($row.recovery_rate_percent)%" $columns[5] $y 90 18 13 $C.Text $true "Consolas" | Out-Null
        Add-Text $s $row.result $columns[6] $y 90 18 13 $C.Green $true "Consolas" | Out-Null
    }
    Add-Text $s "Overall exact recovery: $matchTotal / $officialTotal = $overallRecovery%" 50 450 840 20 13 $C.Orange $true | Out-Null
    Add-Text $s "Not decoded = not recovered from OGG by current settings, or rejected diagnostic PDU; it does not automatically mean an invalid spacecraft frame." 50 478 840 30 10.5 $C.Muted | Out-Null

    $s = New-Slide $presentation "Operational Dashboard"
    $s.Shapes.AddPicture($dashboardImage, 0, -1, 42, 124, 876, 368) | Out-Null
    Add-Text $s "43 panels  |  decoder status + raw HEX  |  confirmed, candidate, and NOT DECODED states remain explicit" 44 502 850 16 10 $C.Muted | Out-Null
    $s.Export($dashboardSlidePreviewPath, "PNG", 1920, 1080)

    $s = New-Slide $presentation "Morning Demo and Next Step"
    Add-Text $s "ONE-COMMAND DEMO" 48 136 250 18 10 $C.Cyan $true "Consolas" | Out-Null
    Add-Box $s 46 166 868 66 $C.Panel $C.Grid | Out-Null
    Add-Text $s "powershell -ExecutionPolicy Bypass -File .\\local-stack\\live_refresh.ps1" 66 188 828 24 16 $C.Text $false "Consolas" | Out-Null
    Add-Text $s "What it demonstrates" 48 274 300 26 18 $C.Text $true | Out-Null
    Add-Text $s "1. Fetch newest uploaded SatNOGS OGG`n2. Decode locally with GNU Radio`n3. Keep CRC-valid 263-byte frames`n4. Push telemetry to InfluxDB and Grafana" 56 314 410 120 15 $C.Text | Out-Null
    Add-Text $s "Current boundary" 516 274 300 26 18 $C.Text $true | Out-Null
    Add-Text $s "SatNOGS is store-and-forward.`nUnconfirmed engineering mappings stay candidate.`nNext: validate remaining fields against an authorized reference." 524 314 370 100 15 $C.Text | Out-Null
    Add-Text $s "Result: reproducible audio-to-dashboard chain with traceable validation evidence." 48 464 840 24 16 $C.Green $true | Out-Null

    $presentation.SaveAs($pptxPath, 24)
    $presentation.SaveAs($pdfPath, 32)
    Write-Host "PPTX: $pptxPath"
    Write-Host "PDF:  $pdfPath"
}
finally {
    if ($presentation) { $presentation.Close() }
    if ($ppt) { $ppt.Quit() }
    if ($presentation) { [Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) | Out-Null }
    if ($ppt) { [Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

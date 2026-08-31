param(
    [string]$OutputPath = (Join-Path $PSScriptRoot "KOYO_Real_Results.xlsx")
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$validationPath = Join-Path $root "reports\koyo_audio_validation.csv"
$coveragePath = Join-Path $root "reports\koyo_historical_coverage.csv"
$summaryPath = Join-Path $root "reports\koyo_historical_summary.json"
$demoPath = Join-Path $root "data\koyo\observations\14909703\live_decoded.json"

@($validationPath, $coveragePath, $summaryPath, $demoPath) | ForEach-Object {
    if (-not (Test-Path $_)) { throw "Workbook input missing: $_" }
}

$validation = @(Import-Csv $validationPath)
$coverage = @(Import-Csv $coveragePath)
$history = Get-Content $summaryPath -Raw | ConvertFrom-Json
$demo = Get-Content $demoPath -Raw | ConvertFrom-Json
$outputPath = [IO.Path]::GetFullPath($OutputPath)

function Color([int]$r, [int]$g, [int]$b) { $r + 256 * $g + 65536 * $b }
$C = @{
    Navy = Color 18 32 47
    Blue = Color 33 150 243
    Green = Color 46 204 113
    Orange = Color 255 152 0
    Red = Color 239 83 80
    Light = Color 238 243 248
    Gray = Color 98 112 126
    PaleBlue = Color 225 240 252
    PaleGreen = Color 226 246 234
    PaleOrange = Color 255 239 213
}

function Set-Title($sheet, [string]$title, [string]$subtitle) {
    $sheet.Range("A1:H1").Merge()
    $sheet.Range("A1").Value2 = $title
    $sheet.Range("A1").Font.Size = 20
    $sheet.Range("A1").Font.Bold = $true
    $sheet.Range("A1").Font.Color = 16777215
    $sheet.Range("A1:H1").Interior.Color = $C.Navy
    $sheet.Range("A2:H2").Merge()
    $sheet.Range("A2").Value2 = $subtitle
    $sheet.Range("A2").Font.Size = 10
    $sheet.Range("A2").Font.Color = $C.Gray
    $sheet.Rows("1:2").RowHeight = 24
}

function Format-Header($range) {
    $range.Font.Bold = $true
    $range.Font.Color = 16777215
    $range.Interior.Color = $C.Navy
    $range.HorizontalAlignment = -4108
    $range.VerticalAlignment = -4108
    $range.WrapText = $true
}

function Add-ExcelTable($sheet, [string]$rangeAddress, [string]$name) {
    $range = $sheet.Range($rangeAddress)
    $table = $sheet.ListObjects.Add(1, $range, $null, 1)
    $table.Name = $name
    $table.TableStyle = "TableStyleMedium2"
    $table
}

function Set-CellValue($cell, $value) {
    if ($null -eq $value) {
        $cell.Value2 = ""
    } elseif ($value -is [double] -or $value -is [int] -or $value -is [long] -or $value -is [decimal]) {
        $cell.Value2 = [double]$value
    } else {
        $cell.Value2 = [string]$value
    }
}

function Limit-ColumnWidths($sheet, [int]$lastColumn) {
    $sheet.Columns("A:$([char](64 + [Math]::Min($lastColumn, 26)))").AutoFit() | Out-Null
    for ($column = 1; $column -le $lastColumn; $column++) {
        if ($sheet.Columns.Item($column).ColumnWidth -gt 28) {
            $sheet.Columns.Item($column).ColumnWidth = 28
        }
    }
}

$excel = $null
$workbook = $null
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $workbook = $excel.Workbooks.Add()
    while ($workbook.Worksheets.Count -lt 7) { $workbook.Worksheets.Add() | Out-Null }

    $names = @("Read Me", "Summary", "Audio Validation", "Historical Daily", "Latest Demo", "Latest Telemetry", "Dashboard Coverage")
    for ($i = 1; $i -le $names.Count; $i++) { $workbook.Worksheets.Item($i).Name = $names[$i - 1] }

    # Read Me
    $sheet = $workbook.Worksheets.Item("Read Me")
    Set-Title $sheet "KOYO Beacon Decoder - Real Results" "Generated from locally verified project evidence; no fabricated telemetry values."
    $readme = @(
        @("Purpose", "Provide reviewable project results in one Excel workbook."),
        @("Direct audio evidence", "Five SatNOGS OGG observations decoded locally with GNU Radio."),
        @("Historical evidence", "SatNOGS-demodulated history; separate from direct OGG proof."),
        @("Confirmed", "Validated channel interpretation used for operational output."),
        @("Candidate", "Plausible channel behavior; mapping or engineering scale remains unverified."),
        @("Not decoded", "No authorized field mapping; no value is invented."),
        @("Latest", "Newest uploaded SatNOGS observation, not continuous live RF."),
        @("Public boundary", "No raw HEX, byte offsets, confidential documents, or downloaded audio are included.")
    )
    $sheet.Range("A4").Value2 = "Item"
    $sheet.Range("B4").Value2 = "Meaning"
    Format-Header $sheet.Range("A4:B4")
    for ($i = 0; $i -lt $readme.Count; $i++) {
        $sheet.Cells.Item(5 + $i, 1).Value2 = $readme[$i][0]
        $sheet.Cells.Item(5 + $i, 2).Value2 = $readme[$i][1]
    }
    Add-ExcelTable $sheet "A4:B$($readme.Count + 4)" "ReadMeTable" | Out-Null
    $sheet.Columns.Item(1).ColumnWidth = 24
    $sheet.Columns.Item(2).ColumnWidth = 85
    $sheet.Range("A4:B20").WrapText = $true

    # Summary
    $sheet = $workbook.Worksheets.Item("Summary")
    Set-Title $sheet "Project Summary" "Formulas link directly to the evidence sheets in this workbook."
    $sheet.Range("A4").Value2 = "Metric"
    $sheet.Range("B4").Value2 = "Value"
    $sheet.Range("C4").Value2 = "Interpretation"
    Format-Header $sheet.Range("A4:C4")
    $summaryRows = @(
        @("Selected audio observations", "=COUNTA('Audio Validation'!A2:A6)", "Controlled direct OGG-to-GNU-Radio sample"),
        @("Passed observations", "=COUNTIF('Audio Validation'!L2:L6,""PASS"")", "Each has a valid local frame and exact match"),
        @("Valid local KOYO frames", "=SUM('Audio Validation'!G2:G6)", "CRC-valid 263-byte frames from local audio"),
        @("Official control frames", "=SUM('Audio Validation'!H2:H6)", "Same-observation SatNOGS controls"),
        @("Byte-exact matches", "=SUM('Audio Validation'!I2:I6)", "Local frames equal to controls byte for byte"),
        @("Overall exact recovery", "=SUM('Audio Validation'!I2:I6)/SUM('Audio Validation'!H2:H6)", "Local OGG recovery, not spacecraft health"),
        @("Historical UTC days", [string]$history.days_with_frames, "SatNOGS-demodulated historical coverage"),
        @("Historical frames", [string]$history.decoded_frames, "Not all re-demodulated locally from OGG"),
        @("Historical observations", [string]$history.distinct_observations, "Distinct SatNOGS observations"),
        @("Receiving stations", [string]$history.receiving_stations, "Stations represented in historical data"),
        @("Grafana panels", "43", "Complete target layout"),
        @("Validated Flux queries", "22", "22 of 22 live query targets passed")
    )
    for ($i = 0; $i -lt $summaryRows.Count; $i++) {
        $row = 5 + $i
        $sheet.Cells.Item($row, 1).Value2 = $summaryRows[$i][0]
        if ($summaryRows[$i][1].StartsWith("=")) {
            $sheet.Cells.Item($row, 2).Formula = $summaryRows[$i][1]
        } else {
            $sheet.Cells.Item($row, 2).Value2 = [double]$summaryRows[$i][1]
        }
        $sheet.Cells.Item($row, 3).Value2 = $summaryRows[$i][2]
    }
    $sheet.Range("B5:B16").NumberFormat = "#,##0.0"
    $sheet.Range("B10").NumberFormat = "0.0%"
    Add-ExcelTable $sheet "A4:C16" "SummaryTable" | Out-Null
    $sheet.Columns.Item(1).ColumnWidth = 29
    $sheet.Columns.Item(2).ColumnWidth = 18
    $sheet.Columns.Item(3).ColumnWidth = 62
    $sheet.Range("A4:C16").WrapText = $true

    # Audio Validation
    $sheet = $workbook.Worksheets.Item("Audio Validation")
    $audioHeaders = @("Observation ID", "Start UTC", "Station", "OGG bytes", "WAV bytes", "Captured KISS", "Valid KOYO", "Control frames", "Exact matches", "Unrecovered", "Recovery %", "Result", "Error")
    for ($column = 0; $column -lt $audioHeaders.Count; $column++) { $sheet.Cells.Item(1, $column + 1).Value2 = $audioHeaders[$column] }
    Format-Header $sheet.Range("A1:M1")
    for ($i = 0; $i -lt $validation.Count; $i++) {
        $row = $i + 2
        $source = $validation[$i]
        $values = @($source.obs_id, $source.observation_start_utc, $source.station, [double]$source.audio_bytes, [double]$source.wav_bytes,
            [double]$source.captured_kiss_frames, [double]$source.valid_koyo_frames, [double]$source.official_control_frames,
            [double]$source.byte_exact_matches, [double]$source.unrecovered_control_frames, [double]$source.recovery_rate_percent,
            $source.result, $source.error)
        for ($column = 0; $column -lt $values.Count; $column++) { Set-CellValue ($sheet.Cells.Item($row, $column + 1)) $values[$column] }
    }
    Add-ExcelTable $sheet "A1:M$($validation.Count + 1)" "AudioValidationTable" | Out-Null
    $sheet.Range("D2:K$($validation.Count + 1)").NumberFormat = "#,##0.0"
    $sheet.Range("K2:K$($validation.Count + 1)").NumberFormat = "0.0"
    $sheet.Range("L2:L$($validation.Count + 1)").Interior.Color = $C.PaleGreen
    $chartObject = $sheet.ChartObjects().Add(760, 20, 560, 300)
    $chart = $chartObject.Chart
    $chart.ChartType = 51
    $chart.SetSourceData($sheet.Range("A1:A$($validation.Count + 1),K1:K$($validation.Count + 1)"))
    $chart.HasTitle = $true
    $chart.ChartTitle.Text = "Exact Recovery by Observation (%)"
    $chart.HasLegend = $false
    $sheet.Application.ActiveWindow.SplitRow = 1
    $sheet.Application.ActiveWindow.FreezePanes = $true
    Limit-ColumnWidths $sheet 13

    # Historical Daily
    $sheet = $workbook.Worksheets.Item("Historical Daily")
    $historyHeaders = @("UTC Date", "Decoded frames", "Observations", "Receiving stations", "First frame UTC", "Last frame UTC")
    for ($column = 0; $column -lt $historyHeaders.Count; $column++) { $sheet.Cells.Item(1, $column + 1).Value2 = $historyHeaders[$column] }
    Format-Header $sheet.Range("A1:F1")
    for ($i = 0; $i -lt $coverage.Count; $i++) {
        $row = $i + 2
        $source = $coverage[$i]
        $values = @($source.date_utc, [double]$source.decoded_frames, [double]$source.observations,
            [double]$source.receiving_stations, $source.first_frame_utc, $source.last_frame_utc)
        for ($column = 0; $column -lt $values.Count; $column++) { Set-CellValue ($sheet.Cells.Item($row, $column + 1)) $values[$column] }
    }
    Add-ExcelTable $sheet "A1:F$($coverage.Count + 1)" "HistoricalDailyTable" | Out-Null
    $chartObject = $sheet.ChartObjects().Add(720, 20, 700, 330)
    $chart = $chartObject.Chart
    $chart.ChartType = 4
    $chart.SetSourceData($sheet.Range("A1:B$($coverage.Count + 1)"))
    $chart.HasTitle = $true
    $chart.ChartTitle.Text = "Daily SatNOGS-Demodulated Frames"
    $chart.HasLegend = $false
    $sheet.Application.ActiveWindow.SplitRow = 1
    $sheet.Application.ActiveWindow.FreezePanes = $true
    Limit-ColumnWidths $sheet 6

    # Latest Demo
    $sheet = $workbook.Worksheets.Item("Latest Demo")
    Set-Title $sheet "Latest Verified Demo" "One-command SatNOGS audio -> GNU Radio -> InfluxDB/Grafana result."
    $demoRows = @(
        @("Source", $demo.source, "Actual local run"),
        @("Observation ID", $demo.observation_id, "SatNOGS observation"),
        @("Observation start", $demo.observation_start, "UTC"),
        @("Station", $demo.station, "Receiving ground station"),
        @("Captured KISS", [string]$demo.captured_kiss_frames, "Diagnostic output from GNU Radio"),
        @("Valid KOYO", [string]$demo.valid_koyo_frames, "Passed CRC, frame length, path, and type"),
        @("Official controls", [string]$demo.official_control_frames, "Same-observation comparison set"),
        @("Byte-exact matches", [string]$demo.byte_exact_control_matches, "Strict correctness evidence"),
        @("Recovery", "=B12/B11", "Exact matches divided by controls"),
        @("Dashboard write", [string]$demo.dashboard_write_status, "HTTP 204 means successful write")
    )
    $sheet.Range("A4").Value2 = "Metric"
    $sheet.Range("B4").Value2 = "Value"
    $sheet.Range("C4").Value2 = "Meaning"
    Format-Header $sheet.Range("A4:C4")
    for ($i = 0; $i -lt $demoRows.Count; $i++) {
        $row = $i + 5
        $sheet.Cells.Item($row, 1).Value2 = $demoRows[$i][0]
        if ($demoRows[$i][1].StartsWith("=")) { $sheet.Cells.Item($row, 2).Formula = $demoRows[$i][1] }
        else { $sheet.Cells.Item($row, 2).Value2 = $demoRows[$i][1] }
        $sheet.Cells.Item($row, 3).Value2 = $demoRows[$i][2]
    }
    $sheet.Range("B13").NumberFormat = "0.0%"
    Add-ExcelTable $sheet "A4:C14" "LatestDemoTable" | Out-Null
    $sheet.Columns.Item(1).ColumnWidth = 25
    $sheet.Columns.Item(2).ColumnWidth = 54
    $sheet.Columns.Item(3).ColumnWidth = 56
    $sheet.Range("A4:C14").WrapText = $true

    # Latest Telemetry
    $sheet = $workbook.Worksheets.Item("Latest Telemetry")
    $telemetryHeaders = @("Frame", "RTC UTC", "Source", "Destination", "Packet counter", "Uptime hours", "Boot counter",
        "Battery TH0 C", "Battery TH1 C", "CDH C", "ADCS C", "PIB health", "SD failures", "PV candidate 1 V", "PV candidate 2 V", "COMM raw candidate")
    for ($column = 0; $column -lt $telemetryHeaders.Count; $column++) { $sheet.Cells.Item(1, $column + 1).Value2 = $telemetryHeaders[$column] }
    Format-Header $sheet.Range("A1:P1")
    for ($i = 0; $i -lt $demo.telemetry.Count; $i++) {
        $row = $i + 2
        $frame = $demo.telemetry[$i]
        $values = @([double]$frame.frame_index, $frame.rtc_datetime, $frame.src_callsign, $frame.dest_callsign,
            [double]$frame.packet_counter, ([double]$frame.uptime_ms / 3600000.0), [double]$frame.boot_counter,
            [double]$frame.battery_th0_temp_c, [double]$frame.battery_th1_temp_c, [double]$frame.cdh_temp_c,
            [double]$frame.adcs_temp_c, [double]$frame.pib_health_status, [double]$frame.sd_card_failure_count,
            ([double]$frame.sp_voltage_candidate_1 / 1000.0), ([double]$frame.sp_voltage_candidate_2 / 1000.0),
            [double]$frame.comm_voltage_candidate)
        for ($column = 0; $column -lt $values.Count; $column++) { Set-CellValue ($sheet.Cells.Item($row, $column + 1)) $values[$column] }
    }
    Add-ExcelTable $sheet "A1:P$($demo.telemetry.Count + 1)" "LatestTelemetryTable" | Out-Null
    $sheet.Range("A2:M$($demo.telemetry.Count + 1)").Interior.Color = $C.PaleGreen
    $sheet.Range("N2:P$($demo.telemetry.Count + 1)").Interior.Color = $C.PaleOrange
    $sheet.Range("F2:F$($demo.telemetry.Count + 1)").NumberFormat = "0.000"
    $sheet.Range("H2:O$($demo.telemetry.Count + 1)").NumberFormat = "0.000"
    $sheet.Application.ActiveWindow.SplitRow = 1
    $sheet.Application.ActiveWindow.FreezePanes = $true
    Limit-ColumnWidths $sheet 16

    # Dashboard Coverage
    $sheet = $workbook.Worksheets.Item("Dashboard Coverage")
    Set-Title $sheet "Dashboard Coverage" "A complete layout does not imply that every telemetry field is decoded."
    $dashboardRows = @(
        @("Summary", "Latest time; boot counter", "Confirmed + unavailable", "Mode, battery voltage/current remain NOT DECODED"),
        @("Orbit", "External 3D viewer", "External dependency", "Requires orbit viewer service"),
        @("Beacon decoder", "PASS, observation, station, frame counts, recovery", "Confirmed", "Includes latest CRC-valid raw HEX in Grafana"),
        @("Solar arrays", "Two voltage candidates", "Candidate + unavailable", "Currents and temperatures remain NOT DECODED"),
        @("Battery", "TH0 and TH1 temperatures", "Confirmed + unavailable", "Electrical and heater fields remain NOT DECODED"),
        @("Power distribution", "Target layout", "Unavailable", "No authorized mappings"),
        @("Comms", "One raw voltage candidate", "Candidate + unavailable", "Current and IF MCU current remain NOT DECODED"),
        @("Thermal and health", "CDH/ADCS temperatures; PIB/SD counters", "Confirmed", "Real historical values"),
        @("OBC", "Uptime and packet counter", "Confirmed", "Real historical values"),
        @("Overall", "43 panels; 22 live Flux targets", "22/22 passed", "No fabricated telemetry values")
    )
    $dashHeaders = @("Group", "Available evidence", "Confidence", "Boundary")
    for ($column = 0; $column -lt $dashHeaders.Count; $column++) { $sheet.Cells.Item(4, $column + 1).Value2 = $dashHeaders[$column] }
    Format-Header $sheet.Range("A4:D4")
    for ($i = 0; $i -lt $dashboardRows.Count; $i++) {
        for ($column = 0; $column -lt 4; $column++) { $sheet.Cells.Item(5 + $i, $column + 1).Value2 = $dashboardRows[$i][$column] }
    }
    Add-ExcelTable $sheet "A4:D$($dashboardRows.Count + 4)" "DashboardCoverageTable" | Out-Null
    $sheet.Columns.Item(1).ColumnWidth = 22
    $sheet.Columns.Item(2).ColumnWidth = 52
    $sheet.Columns.Item(3).ColumnWidth = 26
    $sheet.Columns.Item(4).ColumnWidth = 58
    $sheet.Range("A4:D20").WrapText = $true

    foreach ($worksheet in $workbook.Worksheets) {
        $worksheet.Cells.VerticalAlignment = -4108
        $worksheet.PageSetup.Orientation = 2
        $worksheet.PageSetup.Zoom = $false
        $worksheet.PageSetup.FitToPagesWide = 1
        $worksheet.PageSetup.FitToPagesTall = $false
    }

    if (Test-Path $outputPath) { Remove-Item -LiteralPath $outputPath -Force }
    $workbook.Worksheets.Item("Read Me").Activate() | Out-Null
    $workbook.SaveAs($outputPath, 51)
    Write-Host "Workbook: $outputPath"
    Write-Host "Sheets: $($workbook.Worksheets.Count)"
}
finally {
    if ($workbook) { $workbook.Close($false) }
    if ($excel) { $excel.Quit() }
    if ($workbook) { [Runtime.InteropServices.Marshal]::ReleaseComObject($workbook) | Out-Null }
    if ($excel) { [Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [IO.Compression.ZipFile]::Open($outputPath, [IO.Compression.ZipArchiveMode]::Update)
try {
    $entry = $archive.GetEntry("docProps/core.xml")
    if ($entry) {
        $reader = New-Object IO.StreamReader($entry.Open(), [Text.Encoding]::UTF8)
        try { [xml]$document = $reader.ReadToEnd() } finally { $reader.Dispose() }
        $namespaces = New-Object Xml.XmlNamespaceManager($document.NameTable)
        $namespaces.AddNamespace("dc", "http://purl.org/dc/elements/1.1/")
        $namespaces.AddNamespace("cp", "http://schemas.openxmlformats.org/package/2006/metadata/core-properties")
        $creator = $document.SelectSingleNode("//dc:creator", $namespaces)
        $lastModifiedBy = $document.SelectSingleNode("//cp:lastModifiedBy", $namespaces)
        if ($creator) { $creator.InnerText = "KOYO Project" }
        if ($lastModifiedBy) { $lastModifiedBy.InnerText = "KOYO Project" }
        $entry.Delete()
        $newEntry = $archive.CreateEntry("docProps/core.xml", [IO.Compression.CompressionLevel]::Optimal)
        $settings = New-Object Xml.XmlWriterSettings
        $settings.Encoding = New-Object Text.UTF8Encoding($false)
        $writer = [Xml.XmlWriter]::Create($newEntry.Open(), $settings)
        try { $document.Save($writer) } finally { $writer.Dispose() }
    }

    $workbookEntry = $archive.GetEntry("xl/workbook.xml")
    if ($workbookEntry) {
        $reader = New-Object IO.StreamReader($workbookEntry.Open(), [Text.Encoding]::UTF8)
        try { [xml]$workbookDocument = $reader.ReadToEnd() } finally { $reader.Dispose() }
        $namespaces = New-Object Xml.XmlNamespaceManager($workbookDocument.NameTable)
        $namespaces.AddNamespace("x15ac", "http://schemas.microsoft.com/office/spreadsheetml/2010/11/ac")
        $absolutePaths = @($workbookDocument.SelectNodes("//x15ac:absPath", $namespaces))
        foreach ($absolutePath in $absolutePaths) {
            $absolutePath.ParentNode.RemoveChild($absolutePath) | Out-Null
        }
        $workbookEntry.Delete()
        $newEntry = $archive.CreateEntry("xl/workbook.xml", [IO.Compression.CompressionLevel]::Optimal)
        $settings = New-Object Xml.XmlWriterSettings
        $settings.Encoding = New-Object Text.UTF8Encoding($false)
        $writer = [Xml.XmlWriter]::Create($newEntry.Open(), $settings)
        try { $workbookDocument.Save($writer) } finally { $writer.Dispose() }
    }
} finally {
    $archive.Dispose()
}
Write-Host "Workbook metadata author: KOYO Project"

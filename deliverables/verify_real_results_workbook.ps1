param(
    [string]$WorkbookPath = (Join-Path $PSScriptRoot "KOYO_Real_Results.xlsx")
)

$ErrorActionPreference = "Stop"
$workbookPath = (Resolve-Path $WorkbookPath).Path
$excel = $null
$workbook = $null
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $workbook = $excel.Workbooks.Open($workbookPath, 0, $true)

    $expectedSheets = @("Read Me", "Summary", "Audio Validation", "Historical Daily", "Latest Demo", "Latest Telemetry", "Dashboard Coverage")
    $actualSheets = @($workbook.Worksheets | ForEach-Object { $_.Name })
    if (($actualSheets -join "|") -ne ($expectedSheets -join "|")) {
        throw "Unexpected workbook sheets: $($actualSheets -join ', ')"
    }

    $summary = $workbook.Worksheets.Item("Summary")
    $checks = @(
        @("selected observations", $summary.Range("B5").Value2, 5),
        @("passed observations", $summary.Range("B6").Value2, 5),
        @("valid local frames", $summary.Range("B7").Value2, 22),
        @("official controls", $summary.Range("B8").Value2, 74),
        @("exact matches", $summary.Range("B9").Value2, 20),
        @("historical days", $summary.Range("B11").Value2, 55),
        @("historical frames", $summary.Range("B12").Value2, 17155),
        @("historical observations", $summary.Range("B13").Value2, 1055),
        @("receiving stations", $summary.Range("B14").Value2, 114),
        @("Grafana panels", $summary.Range("B15").Value2, 43),
        @("Flux queries", $summary.Range("B16").Value2, 22)
    )
    foreach ($check in $checks) {
        if ([double]$check[1] -ne [double]$check[2]) {
            throw "$($check[0]) mismatch: expected $($check[2]), got $($check[1])"
        }
    }
    $recovery = [double]$summary.Range("B10").Value2
    if ([Math]::Abs($recovery - (20.0 / 74.0)) -gt 0.000001) {
        throw "Overall recovery formula mismatch: $recovery"
    }

    $audio = $workbook.Worksheets.Item("Audio Validation")
    $history = $workbook.Worksheets.Item("Historical Daily")
    $demo = $workbook.Worksheets.Item("Latest Demo")
    $telemetry = $workbook.Worksheets.Item("Latest Telemetry")
    if ($audio.UsedRange.Rows.Count -ne 6 -or $audio.ChartObjects().Count -ne 1) { throw "Audio Validation layout mismatch." }
    if ($history.UsedRange.Rows.Count -ne 56 -or $history.ChartObjects().Count -ne 1) { throw "Historical Daily layout mismatch." }
    if ([double]$demo.Range("B9").Value2 -ne 6 -or [double]$demo.Range("B10").Value2 -ne 2 -or
        [double]$demo.Range("B12").Value2 -ne 1 -or [double]$demo.Range("B14").Value2 -ne 204) {
        throw "Latest Demo 6 -> 2 -> 1 / HTTP 204 values are incorrect."
    }
    if ($telemetry.UsedRange.Rows.Count -ne 3 -or $telemetry.UsedRange.Columns.Count -ne 16) {
        throw "Latest Telemetry shape mismatch."
    }

    Write-Host "Sheets: $($actualSheets.Count)"
    Write-Host "Audio observations: 5; charts: $($audio.ChartObjects().Count)"
    Write-Host "Historical rows: 55; charts: $($history.ChartObjects().Count)"
    Write-Host "Summary: 5/5 PASS, 22 local, 20/74 exact, 17,155 historical"
    Write-Host "Latest demo: 6 KISS -> 2 valid -> 1 exact; HTTP 204"
    Write-Host "Latest telemetry frames: 2"
}
finally {
    if ($workbook) { $workbook.Close($false) }
    if ($excel) { $excel.Quit() }
    if ($workbook) { [Runtime.InteropServices.Marshal]::ReleaseComObject($workbook) | Out-Null }
    if ($excel) { [Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

param(
    [string]$ZipPath = (Join-Path $PSScriptRoot "KOYO_Final_Project_Submission.zip")
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$tempRoot = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
$stage = [IO.Path]::GetFullPath((Join-Path $env:TEMP "koyo-submission-stage"))
if (-not $stage.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Unsafe staging path: $stage"
}
if (Test-Path $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
$bundle = Join-Path $stage "KOYO_Beacon_Decoder_Submission"
New-Item -ItemType Directory -Force -Path $bundle | Out-Null

function Copy-Relative([string]$relative) {
    $source = Join-Path $root $relative
    if (-not (Test-Path $source)) { throw "Submission file missing: $relative" }
    $destination = Join-Path $bundle $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

$files = @(
    "deliverables\SUBMISSION_README.md",
    "deliverables\KOYO_Beacon_Decoder_Final_Presentation.pdf",
    "deliverables\KOYO_Beacon_Decoder_Final_Presentation.pptx",
    "deliverables\KOYO_PRESENTATION_SCRIPT_TH_EN.md",
    "deliverables\KOYO_Real_Results.xlsx",
    "deliverables\koyo_full_telemetry_dashboard.png",
    "deliverables\build_dashboard_evidence.ps1",
    "deliverables\build_final_presentation.ps1",
    "deliverables\verify_final_presentation.ps1",
    "deliverables\sanitize_public_metadata.ps1",
    "deliverables\build_real_results_workbook.ps1",
    "deliverables\verify_real_results_workbook.ps1",
    "deliverables\github-public-template\docs\PUBLICATION_GUIDE.md",
    "reports\KOYO_MORNING_HANDOFF.md",
    "reports\KOYO_AUDIO_VALIDATION.md",
    "reports\koyo_audio_validation.csv",
    "reports\KOYO_HISTORICAL_COVERAGE.md",
    "reports\koyo_historical_coverage.csv",
    "reports\koyo_historical_summary.json",
    "gnuradio\README.md",
    "gnuradio\koyo_audio_rx.grc",
    "gnuradio\koyo_audio_rx_companion_public.png",
    "gnuradio\generated\koyo_audio_rx.py",
    "koyo_gr_satellites.yml",
    "live_koyo.py",
    "validate_audio_batch.py",
    "summarize_coverage.py",
    "local-stack\live_refresh.ps1",
    "local-stack\validate_dashboard.py",
    "dashboard\capture_grafana.ps1"
)
$files | ForEach-Object { Copy-Relative $_ }

if (Test-Path $ZipPath) { Remove-Item -LiteralPath $ZipPath -Force }
Compress-Archive -LiteralPath $bundle -DestinationPath $ZipPath -CompressionLevel Optimal
Remove-Item -LiteralPath $stage -Recurse -Force

$zip = Get-Item $ZipPath
$hash = Get-FileHash $ZipPath -Algorithm SHA256
Write-Host "ZIP: $($zip.FullName)"
Write-Host "Size: $($zip.Length) bytes"
Write-Host "SHA256: $($hash.Hash)"

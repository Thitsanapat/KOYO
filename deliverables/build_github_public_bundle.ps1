param(
    [string]$BundlePath = (Join-Path $PSScriptRoot "..\github-public\KOYO-Beacon-Decoder"),
    [string]$ZipPath = (Join-Path $PSScriptRoot "KOYO_GitHub_Public_Bundle.zip")
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$publicRoot = [IO.Path]::GetFullPath((Join-Path $root "github-public")).TrimEnd('\') + '\'
$bundle = [IO.Path]::GetFullPath($BundlePath)
if (-not $bundle.StartsWith($publicRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Unsafe public bundle path: $bundle"
}

if (Test-Path $bundle) {
    $resolvedBundle = [IO.Path]::GetFullPath((Resolve-Path $bundle).Path)
    if (-not $resolvedBundle.StartsWith($publicRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to replace path outside github-public: $resolvedBundle"
    }
    Remove-Item -LiteralPath $resolvedBundle -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $bundle | Out-Null

function Copy-PublicFile([string]$sourceRelative, [string]$destinationRelative) {
    $source = Join-Path $root $sourceRelative
    if (-not (Test-Path $source)) { throw "Public bundle source missing: $sourceRelative" }
    $destination = Join-Path $bundle $destinationRelative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

$files = @(
    @("deliverables\github-public-template\README.md", "README.md"),
    @("deliverables\github-public-template\.gitignore", ".gitignore"),
    @("deliverables\github-public-template\.gitattributes", ".gitattributes"),
    @("deliverables\github-public-template\THIRD_PARTY_NOTICES.md", "THIRD_PARTY_NOTICES.md"),
    @("deliverables\github-public-template\LICENSES\GPL-3.0-only.txt", "LICENSES\GPL-3.0-only.txt"),
    @("deliverables\github-public-template\docs\PUBLICATION_GUIDE.md", "docs\PUBLICATION_GUIDE.md"),
    @("gnuradio\README.md", "gnuradio\README.md"),
    @("gnuradio\koyo_audio_rx.grc", "gnuradio\koyo_audio_rx.grc"),
    @("gnuradio\koyo_audio_rx_companion_public.png", "gnuradio\koyo_audio_rx_companion.png"),
    @("gnuradio\generated\koyo_audio_rx.py", "gnuradio\generated\koyo_audio_rx.py"),
    @("koyo_gr_satellites.yml", "gnuradio\koyo_gr_satellites.yml"),
    @("reports\KOYO_AUDIO_VALIDATION.md", "reports\KOYO_AUDIO_VALIDATION.md"),
    @("reports\koyo_audio_validation.csv", "reports\koyo_audio_validation.csv"),
    @("reports\KOYO_HISTORICAL_COVERAGE.md", "reports\KOYO_HISTORICAL_COVERAGE.md"),
    @("reports\koyo_historical_coverage.csv", "reports\koyo_historical_coverage.csv"),
    @("reports\koyo_historical_summary.json", "reports\koyo_historical_summary.json"),
    @("deliverables\KOYO_Real_Results.xlsx", "reports\KOYO_Real_Results.xlsx"),
    @("deliverables\KOYO_Beacon_Decoder_Final_Presentation.pptx", "presentation\KOYO_Beacon_Decoder_Final_Presentation.pptx"),
    @("deliverables\KOYO_Beacon_Decoder_Final_Presentation.pdf", "presentation\KOYO_Beacon_Decoder_Final_Presentation.pdf"),
    @("deliverables\KOYO_PRESENTATION_SCRIPT_TH_EN.md", "presentation\KOYO_PRESENTATION_SCRIPT_TH_EN.md"),
    @("deliverables\koyo_full_telemetry_dashboard.png", "presentation\koyo_full_telemetry_dashboard.png")
)
$files | ForEach-Object { Copy-PublicFile $_[0] $_[1] }

$forbiddenExtensions = @(".ogg", ".wav", ".kiss", ".docx", ".bin", ".raw", ".iq", ".pcap", ".sqlite", ".db", ".zip", ".7z", ".rar")
$forbiddenNames = @("koyosource", "grafana-data", "koyo_dashboard.html", "load_influx.py", "decode_koyo.py")
$allFiles = @(Get-ChildItem -LiteralPath $bundle -Recurse -File -Force)
$violations = @($allFiles | Where-Object {
    $relative = $_.FullName.Substring($bundle.Length).TrimStart('\').ToLowerInvariant()
    $forbiddenExtensions -contains $_.Extension.ToLowerInvariant() -or
    @($forbiddenNames | Where-Object { $relative.Contains($_) }).Count -gt 0
})
if ($violations.Count -gt 0) {
    throw "Forbidden public files detected: $($violations.FullName -join ', ')"
}

if (Test-Path $ZipPath) { Remove-Item -LiteralPath $ZipPath -Force }
Compress-Archive -LiteralPath $bundle -DestinationPath $ZipPath -CompressionLevel Optimal
$hash = Get-FileHash $ZipPath -Algorithm SHA256
Write-Host "Public directory: $bundle"
Write-Host "Files: $($allFiles.Count)"
Write-Host "ZIP: $ZipPath"
Write-Host "SHA256: $($hash.Hash)"

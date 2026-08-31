param(
    [string]$CaptureDirectory = (Join-Path $PSScriptRoot "..\local-stack\grafana-data")
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$captureDirectory = (Resolve-Path $CaptureDirectory).Path
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$overviewSource = Join-Path $captureDirectory "koyo-dashboard-full-top.png"
$overviewTarget = Join-Path $captureDirectory "koyo-dashboard.png"
$evidenceTarget = Join-Path $root "deliverables\koyo_full_telemetry_dashboard.png"
$sources = @(
    $overviewSource,
    (Join-Path $captureDirectory "koyo-dashboard-full-section-2.png"),
    (Join-Path $captureDirectory "koyo-dashboard-full-section-3.png"),
    (Join-Path $captureDirectory "koyo-dashboard-full-section-4.png"),
    (Join-Path $captureDirectory "koyo-dashboard-full-section-5.png")
)

foreach ($source in $sources) {
    if (-not (Test-Path $source)) { throw "Dashboard capture missing: $source" }
}

Copy-Item -LiteralPath $overviewSource -Destination $overviewTarget -Force

$images = @($sources | ForEach-Object { [Drawing.Image]::FromFile($_) })
try {
    $width = [int](($images | Measure-Object Width -Maximum).Maximum)
    $height = [int](($images | Measure-Object Height -Sum).Sum)
    $canvas = [Drawing.Bitmap]::new($width, $height)
    try {
        $graphics = [Drawing.Graphics]::FromImage($canvas)
        try {
            $graphics.Clear([Drawing.Color]::Black)
            $y = 0
            foreach ($sourceImage in $images) {
                $graphics.DrawImageUnscaled($sourceImage, 0, $y)
                $y += $sourceImage.Height
            }
        } finally {
            $graphics.Dispose()
        }
        $canvas.Save($evidenceTarget, [Drawing.Imaging.ImageFormat]::Png)
    } finally {
        $canvas.Dispose()
    }
} finally {
    $images | ForEach-Object { $_.Dispose() }
}

$evidence = Get-Item $evidenceTarget
Write-Host "Dashboard overview: $overviewTarget"
Write-Host "Full dashboard evidence: $($evidence.FullName) ($($evidence.Length) bytes)"

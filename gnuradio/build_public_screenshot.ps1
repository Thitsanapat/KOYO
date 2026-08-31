param(
    [string]$SourcePath = (Join-Path $PSScriptRoot "koyo_audio_rx_companion.png"),
    [string]$OutputPath = (Join-Path $PSScriptRoot "koyo_audio_rx_companion_public.png"),
    [int]$CropTopPixels = 30
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
$sourcePath = (Resolve-Path $SourcePath).Path
$source = [Drawing.Image]::FromFile($sourcePath)
try {
    if ($CropTopPixels -lt 0 -or $CropTopPixels -ge $source.Height) {
        throw "Invalid top crop: $CropTopPixels"
    }
    $height = $source.Height - $CropTopPixels
    $output = [Drawing.Bitmap]::new($source.Width, $height)
    try {
        $graphics = [Drawing.Graphics]::FromImage($output)
        try {
            $graphics.DrawImage(
                $source,
                [Drawing.Rectangle]::new(0, 0, $source.Width, $height),
                [Drawing.Rectangle]::new(0, $CropTopPixels, $source.Width, $height),
                [Drawing.GraphicsUnit]::Pixel
            )
        } finally {
            $graphics.Dispose()
        }
        $output.Save($OutputPath, [Drawing.Imaging.ImageFormat]::Png)
    } finally {
        $output.Dispose()
    }
} finally {
    $source.Dispose()
}

Write-Host "Public-safe GNU Radio screenshot: $OutputPath"

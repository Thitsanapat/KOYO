param(
    [string]$OutputPath = (Join-Path $PSScriptRoot "koyo_audio_rx_companion.png")
)

$ErrorActionPreference = "Stop"
$exe = Join-Path $env:USERPROFILE "radioconda\Scripts\conda.exe"
$grc = (Resolve-Path (Join-Path $PSScriptRoot "koyo_audio_rx.grc")).Path
if (-not (Test-Path $exe)) { throw "radioconda not found: $exe" }

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class WindowCapture {
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int command);
}
"@

$started = Start-Process -FilePath $exe -ArgumentList @(
    "run", "--no-capture-output", "-n", "base", "gnuradio-companion", $grc
) -PassThru
$window = $null
$deadline = (Get-Date).AddSeconds(45)
while ((Get-Date) -lt $deadline) {
    $window = Get-Process -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -match "koyo_audio_rx|GNU Radio Companion" } |
        Select-Object -First 1
    if ($window) { break }
    Start-Sleep -Milliseconds 500
}
if (-not $window) { throw "GNU Radio Companion window did not appear" }

[WindowCapture]::ShowWindow($window.MainWindowHandle, 3) | Out-Null
[WindowCapture]::SetForegroundWindow($window.MainWindowHandle) | Out-Null
Start-Sleep -Seconds 4

$rect = New-Object WindowCapture+RECT
if (-not [WindowCapture]::GetWindowRect($window.MainWindowHandle, [ref]$rect)) {
    throw "Could not read GNU Radio Companion window bounds"
}
$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top
if ($width -lt 600 -or $height -lt 400) { throw "Unexpected window size: ${width}x${height}" }
$captureHeight = [Math]::Min($height, 640)

$bitmap = New-Object System.Drawing.Bitmap $width, $captureHeight
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
try {
    $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bitmap.Size)
    $bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
}
finally {
    $graphics.Dispose()
    $bitmap.Dispose()
    $window.CloseMainWindow() | Out-Null
}

Write-Host "GNU Radio Companion screenshot: $OutputPath"

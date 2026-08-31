# Starts the local dashboard stack and reloads the current decoded CSV.
# Run with:
#   powershell -ExecutionPolicy Bypass -File .\local-stack\refresh.ps1

$ErrorActionPreference = "Stop"
$base = Split-Path -Parent $MyInvocation.MyCommand.Path

& "$base\start.ps1"

function Wait-ForHttp([string]$Url, [int]$TimeoutSeconds = 75) {
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    try {
      Invoke-WebRequest $Url -UseBasicParsing | Out-Null
      return
    } catch {
      Start-Sleep -Seconds 2
    }
  }
  throw "Timed out waiting for $Url"
}

Wait-ForHttp "http://localhost:8086/health"
python "$base\load_influx.py"
python "$base\load_events.py"
python "$base\export_hex_feedback.py"
Wait-ForHttp "http://localhost:3000/api/health"

Write-Host "Dashboard ready: http://localhost:3000/d/koyo-telemetry/koyo-telemetry"

# Latest available SatNOGS audio -> local GNU Radio -> InfluxDB -> Grafana.
param(
  [string]$ObsId = "",
  [switch]$SkipControl
)

$ErrorActionPreference = "Stop"
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $base

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
Wait-ForHttp "http://localhost:3000/api/health"

$args = @("$repo\live_koyo.py", "--force-download", "--push-dashboard")
if ($ObsId) { $args += @("--obs-id", $ObsId) }
if ($SkipControl) { $args += "--skip-control" }

& "$repo\.venv\Scripts\python.exe" @args
if ($LASTEXITCODE -ne 0) {
  throw "KOYO live audio decode failed with exit code $LASTEXITCODE"
}

Write-Host "Dashboard updated: http://localhost:3000/d/koyo-telemetry/koyo-telemetry"

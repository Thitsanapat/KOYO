<#
Refreshes KOYO telemetry data: fetches new SatNOGS observations (with the
sat_id-based filter, see fetch_satnogs.py) and re-decodes all frames.
Run manually, or via Task Scheduler (see setup_schedule.ps1).
Does NOT republish the dashboard artifact - that step needs a Claude Code
session, run it manually when you want an updated snapshot.
#>

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$LogDir = Join-Path $PSScriptRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir ("refresh_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$LockFile = Join-Path $PSScriptRoot "refresh_koyo.lock"

# Overlap guard: a run can take a long time if SatNOGS is rate-limiting, and
# the scheduler firing again mid-run would launch a second fetch_satnogs.py
# hitting the same throttled API - this happened on 2026-07-30 and made the
# throttling worse. Bail out if a previous run's lock is still there.
if (Test-Path $LockFile) {
    $age = (Get-Date) - (Get-Item $LockFile).LastWriteTime
    if ($age.TotalHours -lt 6) {
        "=== $(Get-Date -Format o): skipped, previous run still locked (age $($age.TotalMinutes.ToString('0'))min) ===" |
            Out-File -FilePath $LogFile -Encoding utf8
        exit 0
    }
    # stale lock (>6h old, e.g. from a crash) - proceed and overwrite it
}
New-Item -ItemType File -Path $LockFile -Force | Out-Null

try {
    $Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    "=== $(Get-Date -Format o) ===" | Out-File -FilePath $LogFile -Encoding utf8 -Append
    & $Python fetch_satnogs.py --refresh-observations 2>&1 | Out-File -FilePath $LogFile -Encoding utf8 -Append
    & $Python decode_koyo.py --input-dir data\koyo\frames_hex --output-dir data\koyo\decoded 2>&1 | Out-File -FilePath $LogFile -Encoding utf8 -Append
    "=== done $(Get-Date -Format o) ===" | Out-File -FilePath $LogFile -Encoding utf8 -Append
} finally {
    Remove-Item -Path $LockFile -Force -ErrorAction SilentlyContinue
}

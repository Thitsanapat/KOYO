# Starts the local InfluxDB + Grafana stack for the KOYO dashboard.
# Not part of git (local-stack/ is gitignored) - portable binaries, regenerate by re-running setup.

$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$dashboardDir = "$base\grafana-data\provisioned-dashboards"
New-Item -ItemType Directory -Force -Path $dashboardDir | Out-Null
Copy-Item -LiteralPath "$base\grafana-dashboards\koyo_telemetry.json" -Destination "$dashboardDir\koyo_telemetry.json" -Force

function Test-LocalPort([int]$Port) {
  return $null -ne (netstat -ano -p tcp |
    Select-String -Pattern "^\s*TCP\s+.*:$Port\s+.*LISTENING" |
    Select-Object -First 1)
}

if (Test-LocalPort 8086) {
  Write-Host "InfluxDB is already listening on port 8086."
} else {
  Write-Host "Starting InfluxDB..."
  $influxArgs = @(
    "--bolt-path=$base\influxdb-data\influxd.bolt",
    "--engine-path=$base\influxdb-data\engine",
    "--http-bind-address=:8086"
  )
  Start-Process -FilePath "$base\influxdb\influxd.exe" -ArgumentList $influxArgs -WorkingDirectory $base -WindowStyle Hidden
}

if (Test-LocalPort 3000) {
  Write-Host "Grafana is already listening on port 3000."
} else {
  Write-Host "Starting Grafana..."
  $grafanaHome = "$base\grafana\grafana-12.2.0"
  $dataDir = "$base\grafana-data"
  $grafanaArgs = @(
    "--homepath=$grafanaHome",
    "--config=$grafanaHome\conf\defaults.ini",
    "cfg:paths.data=$dataDir",
    "cfg:paths.logs=$dataDir\logs",
    "cfg:paths.provisioning=$base\provisioning",
    "cfg:default.server.http_port=3000",
    "cfg:panels.disable_sanitize_html=true"
  )
  Start-Process -FilePath "$grafanaHome\bin\grafana-server.exe" -ArgumentList $grafanaArgs -WorkingDirectory $grafanaHome -WindowStyle Hidden
}

Write-Host ""
Write-Host "InfluxDB: http://localhost:8086  (org=koyo, bucket=koyo_telemetry, token=koyo-local-dev-token)"
Write-Host "Grafana:  http://localhost:3000  (login admin/admin, dashboard under folder 'KOYO')"
Write-Host "Grafana can take up to a minute to finish booting before its first use."

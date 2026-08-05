# Starts the local InfluxDB + Grafana stack for the KOYO dashboard.
# Not part of git (local-stack/ is gitignored) - portable binaries, regenerate by re-running setup.

$base = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting InfluxDB..."
$influxArgs = @(
  "--bolt-path=$base\influxdb-data\influxd.bolt",
  "--engine-path=$base\influxdb-data\engine",
  "--http-bind-address=:8086"
)
Start-Process -FilePath "$base\influxdb\influxd.exe" -ArgumentList $influxArgs -WorkingDirectory $base -WindowStyle Hidden

Write-Host "Starting Grafana..."
$grafanaHome = "$base\grafana\grafana-12.2.0"
$dataDir = "$base\grafana-data"
$grafanaArgs = @(
  "--homepath=$grafanaHome",
  "--config=$grafanaHome\conf\defaults.ini",
  "cfg:default.paths.data=$dataDir",
  "cfg:default.paths.logs=$dataDir\logs",
  "cfg:default.paths.provisioning=$base\provisioning",
  "cfg:default.server.http_port=3000"
)
Start-Process -FilePath "$grafanaHome\bin\grafana-server.exe" -ArgumentList $grafanaArgs -WorkingDirectory $grafanaHome -WindowStyle Hidden

Write-Host ""
Write-Host "InfluxDB: http://localhost:8086  (org=koyo, bucket=koyo_telemetry, token=koyo-local-dev-token)"
Write-Host "Grafana:  http://localhost:3000  (login admin/admin, dashboard under folder 'KOYO')"
Write-Host "Give both ~15-20s to finish booting before opening the browser."

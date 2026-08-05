# Stops the local InfluxDB + Grafana stack.

Get-Process influxd -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process grafana-server -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "Stopped."

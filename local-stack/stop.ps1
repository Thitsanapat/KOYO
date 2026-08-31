# Stops the local InfluxDB + Grafana stack.

Get-Process influxd,grafana,grafana-server -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "Stopped."

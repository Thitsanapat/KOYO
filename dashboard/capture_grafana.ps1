param(
    [string]$OutputPath = (Join-Path $PSScriptRoot "..\local-stack\grafana-data\koyo-dashboard-full.png")
)

$ErrorActionPreference = "Stop"
$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chrome)) { throw "Chrome not found: $chrome" }

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$loginBody = @{ user = "admin"; password = "admin" } | ConvertTo-Json
$login = Invoke-WebRequest -Uri "http://localhost:3000/login" -Method Post `
    -ContentType "application/json" -Body $loginBody -WebSession $session -UseBasicParsing
if ($login.StatusCode -ne 200) { throw "Grafana login failed: HTTP $($login.StatusCode)" }

$port = 9237
$profile = Join-Path $env:TEMP "koyo-chrome-cdp"
$tempRoot = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
$profileFull = [IO.Path]::GetFullPath($profile)
if (-not $profileFull.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Unsafe Chrome profile path: $profileFull"
}
if (Test-Path $profile) { Remove-Item -LiteralPath $profile -Recurse -Force }

$chromeArgs = @(
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--hide-scrollbars",
    "--remote-debugging-port=$port",
    "--user-data-dir=$profile",
    "--window-size=1920,1080",
    "about:blank"
)
$process = Start-Process -FilePath $chrome -ArgumentList $chromeArgs -PassThru -WindowStyle Hidden

$client = $null
try {
    $deadline = (Get-Date).AddSeconds(20)
    $page = $null
    while ((Get-Date) -lt $deadline) {
        try {
            $pages = Invoke-RestMethod "http://127.0.0.1:$port/json"
            $page = $pages | Where-Object type -eq "page" | Select-Object -First 1
            if ($page) { break }
        } catch { Start-Sleep -Milliseconds 250 }
    }
    if (-not $page) { throw "Chrome DevTools endpoint did not appear" }

    $client = [Net.WebSockets.ClientWebSocket]::new()
    $client.ConnectAsync([Uri]$page.webSocketDebuggerUrl, [Threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null
    $script:cdpId = 0

    function Invoke-Cdp([string]$Method, [hashtable]$Params = @{}) {
        $script:cdpId++
        $id = $script:cdpId
        $payload = @{ id = $id; method = $Method; params = $Params } | ConvertTo-Json -Depth 20 -Compress
        $bytes = [Text.Encoding]::UTF8.GetBytes($payload)
        $segment = [ArraySegment[byte]]::new($bytes)
        $client.SendAsync($segment, [Net.WebSockets.WebSocketMessageType]::Text, $true, [Threading.CancellationToken]::None).GetAwaiter().GetResult()

        while ($true) {
            $stream = [IO.MemoryStream]::new()
            do {
                $buffer = New-Object byte[] 1048576
                $received = $client.ReceiveAsync([ArraySegment[byte]]::new($buffer), [Threading.CancellationToken]::None).GetAwaiter().GetResult()
                $stream.Write($buffer, 0, $received.Count)
            } while (-not $received.EndOfMessage)
            $message = [Text.Encoding]::UTF8.GetString($stream.ToArray()) | ConvertFrom-Json
            if ($message.id -eq $id) {
                if ($message.error) { throw "$Method failed: $($message.error.message)" }
                return $message.result
            }
        }
    }

    Invoke-Cdp "Network.enable" | Out-Null
    foreach ($cookie in $session.Cookies.GetCookies("http://localhost:3000")) {
        Invoke-Cdp "Network.setCookie" @{
            name = $cookie.Name
            value = $cookie.Value
            url = "http://localhost:3000"
            path = "/"
        } | Out-Null
    }
    Invoke-Cdp "Page.enable" | Out-Null
    Invoke-Cdp "Runtime.enable" | Out-Null
    Invoke-Cdp "Emulation.setDeviceMetricsOverride" @{
        width = 1920
        height = 1080
        deviceScaleFactor = 1
        mobile = $false
    } | Out-Null
    $url = "http://localhost:3000/d/koyo-telemetry/koyo-telemetry?orgId=1&from=1783382400000&to=now&kiosk"
    Invoke-Cdp "Page.navigate" @{ url = $url } | Out-Null
    $pageState = $null
    $renderDeadline = (Get-Date).AddSeconds(40)
    while ((Get-Date) -lt $renderDeadline) {
        Start-Sleep -Seconds 2
        $pageState = Invoke-Cdp "Runtime.evaluate" @{
            expression = 'JSON.stringify({ready:document.readyState,panels:document.querySelectorAll(".react-grid-item").length,text:document.body.innerText.slice(0,1000)})'
            returnByValue = $true
        }
        $state = $pageState.result.value | ConvertFrom-Json
        if ($state.panels -ge 5 -and $state.text -match "Latest Measurement") { break }
    }
    Write-Host "Page ready=$($state.ready) panels=$($state.panels)"
    Write-Host (($state.text -replace "`r?`n", " | ").Substring(0, [Math]::Min(500, ($state.text -replace "`r?`n", " | ").Length)))
    if ($state.panels -lt 5) { throw "Grafana panels did not render" }

    $topShot = Invoke-Cdp "Page.captureScreenshot" @{
        format = "png"
        fromSurface = $true
        captureBeyondViewport = $false
    }
    $outputFull = [IO.Path]::GetFullPath($OutputPath)
    $topPath = [IO.Path]::Combine(
        [IO.Path]::GetDirectoryName($outputFull),
        [IO.Path]::GetFileNameWithoutExtension($outputFull) + "-top.png"
    )
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($outputFull)) | Out-Null
    [IO.File]::WriteAllBytes($topPath, [Convert]::FromBase64String($topShot.data))

    $metrics = Invoke-Cdp "Page.getLayoutMetrics"
    $height = [Math]::Min([Math]::Ceiling($metrics.cssContentSize.height), 12000)
    $sectionPositions = @(0, 900, 1800, 2700, [Math]::Max(0, $height - 1080)) | Select-Object -Unique
    $sectionIndex = 0
    foreach ($position in $sectionPositions) {
        $sectionIndex++
        Invoke-Cdp "Runtime.evaluate" @{
            expression = "window.scrollTo(0, $position)"
            returnByValue = $true
        } | Out-Null
        Start-Sleep -Seconds 2
        $sectionShot = Invoke-Cdp "Page.captureScreenshot" @{
            format = "png"
            fromSurface = $true
            captureBeyondViewport = $false
        }
        $sectionPath = [IO.Path]::Combine(
            [IO.Path]::GetDirectoryName($outputFull),
            [IO.Path]::GetFileNameWithoutExtension($outputFull) + "-section-$sectionIndex.png"
        )
        [IO.File]::WriteAllBytes($sectionPath, [Convert]::FromBase64String($sectionShot.data))
    }
    Invoke-Cdp "Runtime.evaluate" @{ expression = "window.scrollTo(0, 0)"; returnByValue = $true } | Out-Null
    $shot = Invoke-Cdp "Page.captureScreenshot" @{
        format = "png"
        fromSurface = $true
        captureBeyondViewport = $true
        clip = @{ x = 0; y = 0; width = 1920; height = $height; scale = 1 }
    }
    [IO.File]::WriteAllBytes($outputFull, [Convert]::FromBase64String($shot.data))
    Write-Host "Grafana screenshots: $topPath, section 1-$sectionIndex, and $outputFull (${height}px high)"

    Invoke-Cdp "Browser.close" | Out-Null
}
finally {
    if ($client) { $client.Dispose() }
    if (-not $process.HasExited) { $process.Kill() }
}

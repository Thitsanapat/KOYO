param(
    [string]$BundlePath = (Join-Path $PSScriptRoot "..\github-public\KOYO-Beacon-Decoder")
)

$ErrorActionPreference = "Stop"
$bundle = (Resolve-Path $BundlePath).Path
$expected = @(
    ".gitattributes",
    ".gitignore",
    "README.md",
    "THIRD_PARTY_NOTICES.md",
    "docs\PUBLICATION_GUIDE.md",
    "gnuradio\generated\koyo_audio_rx.py",
    "gnuradio\koyo_audio_rx.grc",
    "gnuradio\koyo_audio_rx_companion.png",
    "gnuradio\koyo_gr_satellites.yml",
    "gnuradio\README.md",
    "LICENSES\GPL-3.0-only.txt",
    "presentation\KOYO_Beacon_Decoder_Final_Presentation.pdf",
    "presentation\KOYO_Beacon_Decoder_Final_Presentation.pptx",
    "presentation\koyo_full_telemetry_dashboard.png",
    "presentation\KOYO_PRESENTATION_SCRIPT_TH_EN.md",
    "reports\koyo_audio_validation.csv",
    "reports\KOYO_AUDIO_VALIDATION.md",
    "reports\koyo_historical_coverage.csv",
    "reports\KOYO_HISTORICAL_COVERAGE.md",
    "reports\koyo_historical_summary.json",
    "reports\KOYO_Real_Results.xlsx"
)

$gitDirectory = (Join-Path $bundle ".git").TrimEnd('\') + '\'
$files = @(Get-ChildItem -LiteralPath $bundle -Recurse -File -Force | Where-Object {
    -not $_.FullName.StartsWith($gitDirectory, [StringComparison]::OrdinalIgnoreCase)
})
$relative = @($files | ForEach-Object { $_.FullName.Substring($bundle.Length + 1) })
$unexpected = @($relative | Where-Object { $_ -notin $expected })
$missing = @($expected | Where-Object { $_ -notin $relative })
if ($unexpected.Count -or $missing.Count) {
    throw "Allowlist mismatch. Unexpected: $($unexpected -join ', '); missing: $($missing -join ', ')"
}

$forbiddenExtensions = @(
    ".ogg", ".wav", ".kiss", ".bin", ".raw", ".iq", ".pcap", ".sqlite",
    ".db", ".zip", ".7z", ".rar", ".doc", ".docx", ".xls", ".key", ".pem"
)
$badExtensions = @($files | Where-Object { $forbiddenExtensions -contains $_.Extension.ToLowerInvariant() })
if ($badExtensions.Count) {
    throw "Forbidden file types: $($badExtensions.FullName -join ', ')"
}

$sensitivePatterns = @(
    '(?i)C:\\Users\\|OneDrive|\\Downloads\\|\\Desktop\\',
    '(?i)HEX20_KOYO_LEOPS|HEX20_KOYO_GS.{0,8}MISSION_SUPPORT|STRICTLY\s+CONFIDENTIAL',
    '(?i)\b(?:byte\s+)?offsets?\s*(?:[:=]\s*)?\d',
    '(?i)(?<![\d.])(?:100\.56|192\.168|10\.\d{1,3})\.\d{1,3}\.\d{1,3}(?![\d.])',
    '(?i)\b(?:password|passwd|secret|api[_ -]?key|access[_ -]?token)\s*[:=]\s*[^\s<]+',
    '(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----',
    '(?i)\bgh[pousr]_[A-Za-z0-9_]{20,}\b|\bAKIA[0-9A-Z]{16}\b|\bxox[baprs]-[A-Za-z0-9-]+\b',
    '(?i)\b[A-Z0-9._%+-]+@(?!users\.noreply\.github\.com\b)[A-Z0-9.-]+\.[A-Z]{2,}\b',
    '(?i)\b[0-9a-f]{160,}\b'
)

function Test-Text([string]$label, [string]$text) {
    foreach ($pattern in $sensitivePatterns) {
        if ($text -match $pattern) {
            throw "Sensitive pattern in ${label}: $($Matches[0])"
        }
    }
}

$textExtensions = @(".md", ".csv", ".json", ".yml", ".yaml", ".grc", ".py", ".txt", ".gitignore", ".gitattributes")
foreach ($file in $files) {
    if ($file.Name -in @("GPL-3.0-only.txt")) { continue }
    if ($textExtensions -contains $file.Extension.ToLowerInvariant() -or $file.Name.StartsWith(".")) {
        Test-Text $file.FullName ([IO.File]::ReadAllText($file.FullName))
    }
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
foreach ($file in $files | Where-Object { $_.Extension -in @(".pptx", ".xlsx") }) {
    $archive = [IO.Compression.ZipFile]::OpenRead($file.FullName)
    try {
        $embedded = @($archive.Entries | Where-Object {
            $_.FullName -match '(?i)(^|/)(embeddings|externalLinks|customXml)/|vbaProject\.bin$'
        })
        if ($embedded.Count) {
            throw "Unexpected embedded Office content in $($file.Name): $($embedded.FullName -join ', ')"
        }
        foreach ($entry in $archive.Entries | Where-Object { $_.FullName -match '\.(xml|rels)$' }) {
            $reader = [IO.StreamReader]::new($entry.Open())
            try { $content = $reader.ReadToEnd() } finally { $reader.Dispose() }
            Test-Text "$($file.Name):$($entry.FullName)" $content
        }
    } finally {
        $archive.Dispose()
    }
}

foreach ($file in $files | Where-Object { $_.Extension -in @(".pdf", ".png") }) {
    $bytes = [IO.File]::ReadAllBytes($file.FullName)
    Test-Text $file.FullName ([Text.Encoding]::ASCII.GetString($bytes))
}

$duplicates = @($files | ForEach-Object {
    [PSCustomObject]@{ Path = $_.FullName; Hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
} | Group-Object Hash | Where-Object Count -gt 1)
if ($duplicates.Count) {
    throw "Byte-identical duplicate files detected: $($duplicates.Group.Path -join ', ')"
}

$totalBytes = ($files | Measure-Object Length -Sum).Sum
$bundleHashInput = $files | Sort-Object FullName | ForEach-Object {
    "{0}  {1}" -f (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash, $_.FullName.Substring($bundle.Length + 1)
}
$sha = [Security.Cryptography.SHA256]::Create()
try {
    $manifestHash = ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes(($bundleHashInput -join "`n"))))).Replace("-", "")
} finally {
    $sha.Dispose()
}

Write-Host "PUBLIC AUDIT: PASS"
Write-Host "Files: $($files.Count)"
Write-Host "Bytes: $totalBytes"
Write-Host "Manifest SHA256: $manifestHash"

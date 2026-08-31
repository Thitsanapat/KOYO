param(
    [string]$PresentationPath = (Join-Path $PSScriptRoot "KOYO_Beacon_Decoder_Final_Presentation.pptx"),
    [string]$PdfPath = (Join-Path $PSScriptRoot "KOYO_Beacon_Decoder_Final_Presentation.pdf"),
    [string]$PrivateAuthor = "Thitsanapat S",
    [string]$PublicAuthor = "KOYO Project"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$presentationPath = (Resolve-Path $PresentationPath).Path
$pdfPath = (Resolve-Path $PdfPath).Path

$archive = [IO.Compression.ZipFile]::Open($presentationPath, [IO.Compression.ZipArchiveMode]::Update)
try {
    $entry = $archive.GetEntry("docProps/core.xml")
    if (-not $entry) { throw "PPTX core metadata entry not found." }
    $reader = New-Object IO.StreamReader($entry.Open(), [Text.Encoding]::UTF8)
    try {
        [xml]$document = $reader.ReadToEnd()
    } finally {
        $reader.Dispose()
    }

    $namespaces = New-Object Xml.XmlNamespaceManager($document.NameTable)
    $namespaces.AddNamespace("dc", "http://purl.org/dc/elements/1.1/")
    $namespaces.AddNamespace("cp", "http://schemas.openxmlformats.org/package/2006/metadata/core-properties")
    $creator = $document.SelectSingleNode("//dc:creator", $namespaces)
    $lastModifiedBy = $document.SelectSingleNode("//cp:lastModifiedBy", $namespaces)
    if ($creator) { $creator.InnerText = $PublicAuthor }
    if ($lastModifiedBy) { $lastModifiedBy.InnerText = $PublicAuthor }

    $entry.Delete()
    $replacementEntry = $archive.CreateEntry("docProps/core.xml", [IO.Compression.CompressionLevel]::Optimal)
    $settings = New-Object Xml.XmlWriterSettings
    $settings.Encoding = New-Object Text.UTF8Encoding($false)
    $settings.Indent = $false
    $writer = [Xml.XmlWriter]::Create($replacementEntry.Open(), $settings)
    try {
        $document.Save($writer)
    } finally {
        $writer.Dispose()
    }
} finally {
    $archive.Dispose()
}

$padding = $PrivateAuthor.Length - $PublicAuthor.Length
if ($padding -lt 0) {
    throw "Public PDF author must not be longer than the private author."
}
$search = [Text.Encoding]::UTF8.GetBytes($PrivateAuthor)
$replace = [Text.Encoding]::UTF8.GetBytes("$PublicAuthor$(' ' * $padding)")
if ($search.Length -ne $replace.Length) { throw "PDF metadata replacement length mismatch." }

$pdfBytes = [IO.File]::ReadAllBytes($pdfPath)
$matches = 0
for ($i = 0; $i -le $pdfBytes.Length - $search.Length; $i++) {
    $matched = $true
    for ($j = 0; $j -lt $search.Length; $j++) {
        if ($pdfBytes[$i + $j] -ne $search[$j]) {
            $matched = $false
            break
        }
    }
    if ($matched) {
        [Array]::Copy($replace, 0, $pdfBytes, $i, $replace.Length)
        $matches++
        $i += $search.Length - 1
    }
}
if ($matches -gt 0) { [IO.File]::WriteAllBytes($pdfPath, $pdfBytes) }

Write-Host "Sanitized PPTX/PDF author metadata: $PublicAuthor ($matches PDF occurrence(s))"

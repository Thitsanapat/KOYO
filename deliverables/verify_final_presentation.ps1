param(
    [string]$PresentationPath = (Join-Path $PSScriptRoot "KOYO_Beacon_Decoder_Final_Presentation.pptx")
)

$ErrorActionPreference = "Stop"
$presentationPath = (Resolve-Path $PresentationPath).Path
$ppt = $null
$presentation = $null
try {
    $ppt = New-Object -ComObject PowerPoint.Application
    $ppt.Visible = -1
    $presentation = $ppt.Presentations.Open($presentationPath, -1, 0, 0)
    $missingNotes = @()
    $overflow = @()

    foreach ($slide in $presentation.Slides) {
        $notes = $slide.NotesPage.Shapes.Placeholders.Item(2).TextFrame.TextRange.Text
        if ([string]::IsNullOrWhiteSpace($notes) -or $notes.Length -lt 100) {
            $missingNotes += $slide.SlideIndex
        }

        foreach ($shape in $slide.Shapes) {
            if ($shape.HasTextFrame -and $shape.TextFrame2.HasText) {
                $boundHeight = $shape.TextFrame2.TextRange.BoundHeight
                if ($boundHeight -gt ($shape.Height + 3)) {
                    $overflow += "slide $($slide.SlideIndex): $($shape.Name)"
                }
            }
        }
    }

    Write-Host "Slides: $($presentation.Slides.Count)"
    Write-Host "Slides missing detailed notes: $($missingNotes.Count)"
    Write-Host "Detected vertical text overflow: $($overflow.Count)"
    $overflow | ForEach-Object { Write-Host "  $_" }

    if ($presentation.Slides.Count -ne 15 -or $missingNotes.Count -gt 0 -or $overflow.Count -gt 0) {
        throw "Presentation verification failed."
    }
}
finally {
    if ($presentation) { $presentation.Close() }
    if ($ppt) { $ppt.Quit() }
    if ($presentation) { [Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) | Out-Null }
    if ($ppt) { [Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

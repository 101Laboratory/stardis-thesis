# Convert all SVG files under Figures/ to PDF using Inkscape (incremental).
# Only converts when the PDF is missing or older than the SVG.
# Requires: Inkscape (winget install Inkscape.Inkscape)

param(
    [string]$FiguresDir = (Join-Path $PSScriptRoot '..\Figures')
)

$FiguresDir = (Resolve-Path $FiguresDir).Path

# Locate Inkscape
$inkscape = $null
$inkscapePaths = @(
    "C:\Program Files\Inkscape\bin\inkscape.exe",
    "C:\Program Files (x86)\Inkscape\bin\inkscape.exe"
)
foreach ($p in $inkscapePaths) {
    if (Test-Path $p) { $inkscape = $p; break }
}
if (-not $inkscape) {
    $inkscape = (Get-Command inkscape -ErrorAction SilentlyContinue).Source
}
if (-not $inkscape) {
    Write-Error "Inkscape not found. Install via: winget install Inkscape.Inkscape"
    exit 1
}
Write-Host "Using Inkscape: $inkscape"

$svgFiles = Get-ChildItem -Path $FiguresDir -Recurse -Filter '*.svg'

if ($svgFiles.Count -eq 0) {
    Write-Host "No SVG files found under $FiguresDir"
    exit 0
}

$converted = 0
foreach ($svg in $svgFiles) {
    $pdf = $svg.FullName -replace '\.svg$', '.pdf'
    if (!(Test-Path $pdf) -or ($svg.LastWriteTime -gt (Get-Item $pdf).LastWriteTime)) {
        Write-Host "Converting: $($svg.FullName)"
        & $inkscape $svg.FullName --export-type=pdf --export-filename=$pdf 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Inkscape failed for $($svg.Name)"
            exit 1
        }
        $converted++
    } else {
        Write-Host "Up-to-date: $($svg.Name)"
    }
}

Write-Host "`nDone. Converted $converted of $($svgFiles.Count) SVG file(s)."

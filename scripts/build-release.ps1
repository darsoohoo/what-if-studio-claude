# Build a release ZIP of What If Studio.
#
# Uses `git archive`, so the ZIP contains exactly the committed files at HEAD -
# the app, the pipeline scripts/fonts, and docs - and never the generated or
# gitignored content (AI image cache, downloaded music, rendered output).
#
# Run from anywhere in the repo:  ./scripts/build-release.ps1
# Optional version label:         ./scripts/build-release.ps1 -Version v1.0-beta

param([string]$Version = "v1.0-beta")

$ErrorActionPreference = "Stop"
$repo = (git rev-parse --show-toplevel).Trim()
$dist = Join-Path $repo "dist"
New-Item -ItemType Directory -Force -Path $dist | Out-Null

$zip = Join-Path $dist "what-if-studio-$Version.zip"
Write-Host "Packaging committed files at HEAD -> $zip"
git -C $repo archive --format=zip --prefix="what-if-studio/" -o $zip HEAD

$sizeMb = [math]::Round((Get-Item $zip).Length / 1MB, 2)
$count = (& git -C $repo archive --format=tar HEAD | & tar -tf - 2>$null | Measure-Object -Line).Lines
Write-Host "Done: $zip ($sizeMb MB)"
Write-Host "Unzip it anywhere and double-click what-if-studio/index.html to run the app."
Write-Host ""
Write-Host "To publish this as a GitHub release (after merging the beta PRs to main):"
Write-Host "  git tag -a $Version -m 'What If Studio $Version'"
Write-Host "  git push origin $Version"
Write-Host "  gh release create $Version `"$zip`" --title 'What If Studio $Version' --notes-file RELEASE_NOTES.md"

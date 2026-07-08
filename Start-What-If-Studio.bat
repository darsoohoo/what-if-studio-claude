@echo off
rem ============================================================
rem  What If Studio - one-click launcher.
rem  Starts everything: the review dashboard server (powers the
rem  Videos page + the AI writer), the Downloads watcher (auto-
rem  renders queue exports), and opens the Studio in your browser.
rem  Safe to double-click again anytime - already-running services
rem  are detected and skipped.
rem ============================================================
set "ROOT=%~dp0"
set "PIPELINE=%ROOT%pipeline"

rem Dashboard server (skip if already listening on 8765)
powershell -NoProfile -Command "if (-not (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue)) { Start-Process python -ArgumentList 'review.py' -WorkingDirectory '%PIPELINE%' -WindowStyle Hidden }"

rem Watcher (its own single-instance guard makes duplicates exit quietly)
powershell -NoProfile -Command "Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File','watch_downloads.ps1' -WorkingDirectory '%PIPELINE%' -WindowStyle Hidden"

rem Open the Studio (Start-Process is more reliable than start on OneDrive paths)
powershell -NoProfile -Command "Start-Process '%ROOT%index.html'"

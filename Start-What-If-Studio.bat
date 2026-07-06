@echo off
rem ============================================================
rem  What If Studio - one-click launcher.
rem  Starts everything: the review dashboard server (powers the
rem  Videos page + the AI writer), the Downloads watcher (auto-
rem  renders queue exports), and opens the Studio in your browser.
rem  Safe to double-click again anytime - already-running services
rem  are detected and skipped.
rem ============================================================
cd /d "%~dp0pipeline"

rem Dashboard server (skip if already listening on 8765)
powershell -NoProfile -Command "if (-not (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue)) { Start-Process python -ArgumentList 'review.py' -WindowStyle Hidden }"

rem Watcher (its own single-instance guard makes duplicates exit quietly)
powershell -NoProfile -Command "Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File','watch_downloads.ps1' -WindowStyle Hidden"

rem Open the Studio
start "" "%~dp0index.html"

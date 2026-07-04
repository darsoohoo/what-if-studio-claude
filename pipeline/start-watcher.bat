@echo off
rem What If Studio - start the auto-render watcher for this session.
rem Double-click this ONCE when you sit down to make content. From then on,
rem every "Export queue (.json)" from the app renders automatically and the
rem output folder pops open when videos are ready.
rem The watcher stops when you log off or restart. Nothing is installed.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell.exe -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File','%~dp0watch_downloads.ps1' -WindowStyle Hidden"
echo.
echo Watcher is running. Queue exports will now render automatically.
echo You can close this window.
echo.
timeout /t 8 >nul

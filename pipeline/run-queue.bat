@echo off
rem What If Studio - one-click video maker.
rem Finds your newest queue export (in Downloads or this folder),
rem then renders every queued package with free AI visuals.
cd /d "%~dp0"

rem Grab the newest export from Downloads (handles "whatifstudio-queue (1).json" etc.)
for /f "delims=" %%f in ('dir /b /o-d "%USERPROFILE%\Downloads\whatifstudio-queue*.json" 2^>nul') do (
    copy /y "%USERPROFILE%\Downloads\%%f" "whatifstudio-queue.json" >nul
    echo Using queue export from Downloads: %%f
    goto :run
)

:run
if not exist "whatifstudio-queue.json" (
    echo No queue export found.
    echo.
    echo In the app, click "Export queue (.json) for video pipeline" first,
    echo then double-click this file again.
    echo.
    pause
    exit /b 1
)

python make_videos.py whatifstudio-queue.json --ai-visuals
echo.
echo Done. Your videos are in the "output" folder next to this file.
echo.
pause

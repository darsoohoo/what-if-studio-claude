@echo off
rem What If Studio - open the video review dashboard.
rem Watch rendered videos, reorder your posting queue, add notes,
rem and remove videos (moved to output\trash, recoverable).
rem Local-only (127.0.0.1). Close this window to stop the dashboard.
cd /d "%~dp0"
python review.py --open
pause

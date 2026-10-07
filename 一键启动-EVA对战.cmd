@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  py -3 tools\launch_game.py --mode eva
) else (
  python tools\launch_game.py --mode eva
)
if errorlevel 1 pause

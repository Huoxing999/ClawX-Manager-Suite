@echo off
setlocal
cd /d "%~dp0"

echo Starting ClawX Provider Manager Portable...
py -3 provider_manager.py
if errorlevel 1 (
  echo.
  echo Provider Manager exited with error.
  pause
)

@echo off
chcp 65001 >nul
cd /d "%~dp0"
title RF Regional Analytics
echo.
echo  ========================================
echo   RF Regional Analytics - simple start
echo  ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo  [ERROR] Python not found. Install from https://www.python.org/downloads/
  echo  Enable: Add python.exe to PATH
  pause
  exit /b 1
)

python bootstrap.py %*
if errorlevel 1 (
  echo.
  echo  Something failed. Read messages above.
  pause
  exit /b 1
)

@echo off
chcp 65001 >nul
title RF Political Trends Analyzer — Installer
echo.
echo  Starting PowerShell installer...
echo  (If you see an execution policy error, run:)
echo  powershell -ExecutionPolicy Bypass -File "%~dp0install.ps1"
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
if errorlevel 1 (
    echo.
    echo  Installation failed. See messages above.
    pause
    exit /b 1
)
pause

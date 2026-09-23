#Requires -Version 5.1
<#
.SYNOPSIS
    RF Political Trends Analyzer - Windows Installer (v1.3)
.NOTES
    powershell -ExecutionPolicy Bypass -File install.ps1
#>

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\RFPoliticalTrends",
    [string]$RepoUrl = "https://github.com/karalik19-a11y/rf-political-trends-analyzer.git",
    [string]$Branch = "main",
    [switch]$SkipDailyTask,
    [switch]$NoDesktopShortcut,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step([string]$msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn([string]$msg) { Write-Host "  [!] $msg" -ForegroundColor Yellow }
function Write-Err([string]$msg)  { Write-Host "  [ERROR] $msg" -ForegroundColor Red }

function Write-BatFile {
    param([string]$Path, [string[]]$Lines)
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllLines($Path, $Lines, $utf8NoBom)
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor White
Write-Host "  RF Political Trends Analyzer - Windows Installer" -ForegroundColor White
Write-Host "  Independent media only (no state media)" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor White

Write-Step "Checking Python 3.9+ ..."
$python = $null
foreach ($cmd in @("python", "py", "python3")) {
    try {
        $verOutput = & $cmd --version 2>&1 | Out-String
        if ($verOutput -match "Python 3\.(\d+)") {
            $minor = [int]$Matches[1]
            if ($minor -ge 9) {
                $python = (Get-Command $cmd -ErrorAction Stop).Source
                Write-Ok "Found: $($verOutput.Trim()) ($python)"
                break
            }
        }
    } catch {}
}
if (-not $python) {
    Write-Err "Python 3.9+ not found. Install from python.org with Add to PATH."
    exit 1
}

Write-Step "Checking Git ..."
$hasGit = $false
try { $null = & git --version 2>&1; $hasGit = $true; Write-Ok "Git found" } catch { Write-Warn "No Git - using ZIP" }

Write-Step "Install directory: $InstallDir"
if (Test-Path -LiteralPath $InstallDir) {
    if ($Force) {
        Remove-Item -LiteralPath $InstallDir -Recurse -Force
    } else {
        $ans = Read-Host "Directory exists. Overwrite? (y/N)"
        if ($ans -notin @("y", "Y", "yes")) { Write-Host "Aborted."; exit 0 }
        Remove-Item -LiteralPath $InstallDir -Recurse -Force
    }
}
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

Write-Step "Downloading sources..."
$appDir = Join-Path $InstallDir "app"
if ($hasGit) {
    & git clone --depth 1 --branch $Branch $RepoUrl $appDir
    if ($LASTEXITCODE -ne 0) { throw "git clone failed" }
} else {
    $zipUrl = "https://github.com/karalik19-a11y/rf-political-trends-analyzer/archive/refs/heads/$Branch.zip"
    $zipPath = Join-Path $env:TEMP "rf-pta.zip"
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
    Expand-Archive -Path $zipPath -DestinationPath $InstallDir -Force
    $extracted = Get-ChildItem -Path $InstallDir -Directory | Where-Object { $_.Name -like "rf-political-trends-analyzer-*" } | Select-Object -First 1
    if (-not $extracted) { throw "Extract failed" }
    Rename-Item -LiteralPath $extracted.FullName -NewName "app"
    Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue
}
if (-not (Test-Path -LiteralPath (Join-Path $appDir "src"))) { throw "App sources missing" }
Write-Ok "Sources ready"

Write-Step "Creating venv..."
$venvDir = Join-Path $InstallDir "venv"
& $python -m venv $venvDir
$pip = Join-Path $venvDir "Scripts\pip.exe"
$pythonVenv = Join-Path $venvDir "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonVenv)) { throw "venv failed" }
Write-Ok "venv OK"

Write-Step "Installing packages (lightweight: no torch by default)..."
& $pip install --upgrade pip setuptools wheel
# Core deps without heavy torch - sentiment optional later
& $pip install feedparser requests pyyaml pandas streamlit plotly sqlalchemy python-dateutil nltk scikit-learn beautifulsoup4 lxml apscheduler
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
Write-Ok "Dependencies installed"

New-Item -ItemType Directory -Path (Join-Path $appDir "data") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $appDir "exports") -Force | Out-Null

Write-Step "Creating launchers..."
$launcherDir = Join-Path $InstallDir "bin"
New-Item -ItemType Directory -Path $launcherDir -Force | Out-Null

Write-BatFile -Path (Join-Path $launcherDir "Start-Dashboard.bat") -Lines @(
    "@echo off",
    "chcp 65001 >nul",
    "cd /d `"$appDir`"",
    "echo Starting dashboard... browser will open shortly.",
    "`"$pythonVenv`" `"$appDir\run_dashboard.py`"",
    "if errorlevel 1 (",
    "  echo FAILED. Press any key.",
    "  pause",
    ")"
)

Write-BatFile -Path (Join-Path $launcherDir "Run-Collector.bat") -Lines @(
    "@echo off",
    "chcp 65001 >nul",
    "cd /d `"$appDir`"",
    "`"$pythonVenv`" `"$appDir\run_collector.py`"",
    "echo.",
    "pause"
)

Write-BatFile -Path (Join-Path $launcherDir "Start-Scheduler.bat") -Lines @(
    "@echo off",
    "chcp 65001 >nul",
    "cd /d `"$appDir`"",
    "echo Scheduler Ctrl+C to stop",
    "`"$pythonVenv`" -m src.scheduler --hour 6 --minute 0",
    "pause"
)

Write-BatFile -Path (Join-Path $launcherDir "Export-Data.bat") -Lines @(
    "@echo off",
    "chcp 65001 >nul",
    "cd /d `"$appDir`"",
    "`"$pythonVenv`" -m src.export --format both",
    "echo Saved to exports folder",
    "pause"
)

Write-BatFile -Path (Join-Path $launcherDir "Diagnose.bat") -Lines @(
    "@echo off",
    "chcp 65001 >nul",
    "cd /d `"$appDir`"",
    "echo Python:",
    "`"$pythonVenv`" --version",
    "echo.",
    "echo Testing imports...",
    "`"$pythonVenv`" -c `"import feedparser,streamlit,pandas,yaml,requests; print('OK')`"",
    "echo.",
    "pause"
)

Write-Ok "Launchers in $launcherDir"

Write-Step "Shortcuts..."
$WshShell = New-Object -ComObject WScript.Shell
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\RF Political Trends"
New-Item -ItemType Directory -Path $startMenu -Force | Out-Null

function New-AppShortcut([string]$Name, [string]$Target, [string]$WorkDir) {
    $sc = $WshShell.CreateShortcut((Join-Path $startMenu "$Name.lnk"))
    $sc.TargetPath = $Target
    $sc.WorkingDirectory = $WorkDir
    $sc.Save()
}

New-AppShortcut "Dashboard" (Join-Path $launcherDir "Start-Dashboard.bat") $appDir
New-AppShortcut "Run Collector" (Join-Path $launcherDir "Run-Collector.bat") $appDir
New-AppShortcut "Diagnose" (Join-Path $launcherDir "Diagnose.bat") $appDir
New-AppShortcut "Export Data" (Join-Path $launcherDir "Export-Data.bat") $appDir

if (-not $NoDesktopShortcut) {
    $desk = [Environment]::GetFolderPath("Desktop")
    $sc = $WshShell.CreateShortcut((Join-Path $desk "RF Political Trends Dashboard.lnk"))
    $sc.TargetPath = (Join-Path $launcherDir "Start-Dashboard.bat")
    $sc.WorkingDirectory = $appDir
    $sc.Save()
    Write-Ok "Desktop shortcut"
}

if (-not $SkipDailyTask) {
    Write-Step "Task Scheduler daily 06:00..."
    $taskName = "RFPoliticalTrendsDailyCollect"
    try {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
        $action = New-ScheduledTaskAction -Execute $pythonVenv -Argument "`"$appDir\run_collector.py`"" -WorkingDirectory $appDir
        $trigger = New-ScheduledTaskTrigger -Daily -At "06:00"
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
        $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
        Write-Ok "Task registered"
    } catch { Write-Warn "Task not registered: $_" }
}

$uninstPath = Join-Path $InstallDir "uninstall.ps1"
$uninstLines = @(
    "#Requires -Version 5.1",
    "`$ErrorActionPreference = 'SilentlyContinue'",
    "Unregister-ScheduledTask -TaskName 'RFPoliticalTrendsDailyCollect' -Confirm:`$false",
    "Remove-Item -Recurse -Force (Join-Path `$env:APPDATA 'Microsoft\Windows\Start Menu\Programs\RF Political Trends')",
    "Remove-Item (Join-Path ([Environment]::GetFolderPath('Desktop')) 'RF Political Trends Dashboard.lnk') -Force",
    "Remove-Item -Recurse -Force '$InstallDir'",
    "Write-Host 'Done.' -ForegroundColor Green"
)
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllLines($uninstPath, $uninstLines, $utf8NoBom)

Write-Step "Test collector once?..."
$doCollect = Read-Host "Collect news now? (Y/n)"
if ($doCollect -notin @("n", "N", "no")) {
    Push-Location $appDir
    try {
        & $pythonVenv (Join-Path $appDir "run_collector.py")
        Write-Ok "Collection done"
    } catch { Write-Warn "$_" }
    Pop-Location
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  INSTALL OK" -ForegroundColor Green
Write-Host "  $InstallDir" -ForegroundColor Green
Write-Host "  Desktop shortcut -> Dashboard" -ForegroundColor Green
Write-Host "  If RSS blocked in RF, use VPN then Run Collector" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Green

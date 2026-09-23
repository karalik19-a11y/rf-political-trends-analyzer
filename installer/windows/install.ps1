#Requires -Version 5.1
<#
.SYNOPSIS
    RF Political Trends Analyzer - Windows Installer
.DESCRIPTION
    Downloads the application, creates a virtual environment, installs dependencies,
    links all components, creates Start Menu / Desktop shortcuts and optional daily task.
.NOTES
    Run:  powershell -ExecutionPolicy Bypass -File install.ps1
    Or double-click install.bat
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
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string[]]$Lines
    )
    # Write batch file as ANSI/ASCII lines - no PowerShell here-strings with @echo
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllLines($Path, $Lines, $utf8NoBom)
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor White
Write-Host "  RF Political Trends Analyzer - Windows Installer" -ForegroundColor White
Write-Host "  Public RSS collector + NLP + Streamlit dashboard" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor White

# ---------- 1. Check Python ----------
Write-Step "Checking Python 3.9+ ..."
$python = $null
foreach ($cmd in @("python", "python3", "py")) {
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
    } catch {
        # try next
    }
}
if (-not $python) {
    Write-Err "Python 3.9+ not found."
    Write-Host "Download from https://www.python.org/downloads/ and enable 'Add to PATH'." -ForegroundColor Yellow
    Write-Host "Then re-run this installer." -ForegroundColor Yellow
    exit 1
}

# ---------- 2. Check Git ----------
Write-Step "Checking Git ..."
$hasGit = $false
try {
    $null = & git --version 2>&1
    $hasGit = $true
    Write-Ok "Git found"
} catch {
    Write-Warn "Git not found - will download ZIP instead of cloning"
}

# ---------- 3. Prepare install directory ----------
Write-Step "Install directory: $InstallDir"
if (Test-Path -LiteralPath $InstallDir) {
    if ($Force) {
        Write-Warn "Removing existing installation..."
        Remove-Item -LiteralPath $InstallDir -Recurse -Force
    } else {
        $ans = Read-Host "Directory already exists. Overwrite? (y/N)"
        if ($ans -notin @("y", "Y", "yes")) {
            Write-Host "Aborted."
            exit 0
        }
        Remove-Item -LiteralPath $InstallDir -Recurse -Force
    }
}
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Write-Ok "Created $InstallDir"

# ---------- 4. Download sources ----------
Write-Step "Downloading application sources..."
$appDir = Join-Path $InstallDir "app"
if ($hasGit) {
    & git clone --depth 1 --branch $Branch $RepoUrl $appDir
    if ($LASTEXITCODE -ne 0) { throw "git clone failed" }
    Write-Ok "Cloned repository"
} else {
    $zipUrl = "https://github.com/karalik19-a11y/rf-political-trends-analyzer/archive/refs/heads/$Branch.zip"
    $zipPath = Join-Path $env:TEMP "rf-pta.zip"
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
    Expand-Archive -Path $zipPath -DestinationPath $InstallDir -Force
    $extracted = Get-ChildItem -Path $InstallDir -Directory | Where-Object { $_.Name -like "rf-political-trends-analyzer-*" } | Select-Object -First 1
    if ($extracted) {
        Rename-Item -LiteralPath $extracted.FullName -NewName "app"
    } else {
        throw "Could not find extracted folder"
    }
    Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue
    Write-Ok "Downloaded and extracted ZIP"
}

if (-not (Test-Path -LiteralPath (Join-Path $appDir "src"))) {
    throw "App sources not found in $appDir"
}

# ---------- 5. Create virtual environment ----------
Write-Step "Creating Python virtual environment..."
$venvDir = Join-Path $InstallDir "venv"
& $python -m venv $venvDir
if ($LASTEXITCODE -ne 0) { throw "Failed to create venv" }
$pip = Join-Path $venvDir "Scripts\pip.exe"
$pythonVenv = Join-Path $venvDir "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonVenv)) {
    throw "venv python not found: $pythonVenv"
}
Write-Ok "venv created"

# ---------- 6. Install dependencies ----------
Write-Step "Installing dependencies (may take several minutes)..."
& $pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) { Write-Warn "pip upgrade returned non-zero" }

Write-Host "  Installing torch (CPU)..." -ForegroundColor DarkGray
& $pip install torch --index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE -ne 0) {
    Write-Warn "CPU torch install failed, trying default torch..."
    & $pip install torch
}

$reqFile = Join-Path $appDir "requirements.txt"
$reqLines = Get-Content -LiteralPath $reqFile | Where-Object { $_ -notmatch "^\s*torch" }
$tmpReq = Join-Path $env:TEMP "rf-req-filtered.txt"
$reqLines | Set-Content -LiteralPath $tmpReq -Encoding UTF8
& $pip install -r $tmpReq
if ($LASTEXITCODE -ne 0) {
    Write-Warn "Some packages failed. Installing core set without version pins..."
    & $pip install feedparser requests pyyaml pandas streamlit plotly sqlalchemy python-dateutil nltk scikit-learn beautifulsoup4 lxml apscheduler transformers sentencepiece protobuf
}
Remove-Item -LiteralPath $tmpReq -Force -ErrorAction SilentlyContinue
Write-Ok "Dependencies installed"

# ---------- 7. data / exports ----------
New-Item -ItemType Directory -Path (Join-Path $appDir "data") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $appDir "exports") -Force | Out-Null

# ---------- 8. Launchers (NO here-strings with @echo) ----------
Write-Step "Creating launchers..."
$launcherDir = Join-Path $InstallDir "bin"
New-Item -ItemType Directory -Path $launcherDir -Force | Out-Null

# Escape paths for batch (quotes)
$appDirBat = $appDir
$pythonVenvBat = $pythonVenv

Write-BatFile -Path (Join-Path $launcherDir "Start-Dashboard.bat") -Lines @(
    "@echo off",
    "chcp 65001 >nul",
    "cd /d `"$appDirBat`"",
    "`"$pythonVenvBat`" -m streamlit run src\dashboard.py --server.headless true",
    "if errorlevel 1 pause"
)

Write-BatFile -Path (Join-Path $launcherDir "Run-Collector.bat") -Lines @(
    "@echo off",
    "chcp 65001 >nul",
    "cd /d `"$appDirBat`"",
    "`"$pythonVenvBat`" -m src.collector",
    "echo.",
    "pause"
)

Write-BatFile -Path (Join-Path $launcherDir "Start-Scheduler.bat") -Lines @(
    "@echo off",
    "chcp 65001 >nul",
    "cd /d `"$appDirBat`"",
    "echo Starting daily scheduler (Ctrl+C to stop)...",
    "`"$pythonVenvBat`" -m src.scheduler --hour 6 --minute 0",
    "pause"
)

Write-BatFile -Path (Join-Path $launcherDir "Export-Data.bat") -Lines @(
    "@echo off",
    "chcp 65001 >nul",
    "cd /d `"$appDirBat`"",
    "`"$pythonVenvBat`" -m src.export --format both",
    "echo.",
    "echo Files saved to: $appDirBat\exports",
    "pause"
)

Write-Ok "Launchers created in $launcherDir"

# ---------- 9. Shortcuts ----------
Write-Step "Creating shortcuts..."
$WshShell = New-Object -ComObject WScript.Shell

$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\RF Political Trends"
New-Item -ItemType Directory -Path $startMenu -Force | Out-Null

function New-AppShortcut {
    param([string]$Name, [string]$Target, [string]$WorkDir, [string]$Description)
    $lnkPath = Join-Path $startMenu "$Name.lnk"
    $sc = $WshShell.CreateShortcut($lnkPath)
    $sc.TargetPath = $Target
    $sc.WorkingDirectory = $WorkDir
    $sc.Description = $Description
    $sc.Save()
}

New-AppShortcut -Name "Dashboard" -Target (Join-Path $launcherDir "Start-Dashboard.bat") -WorkDir $appDir -Description "Open Streamlit dashboard"
New-AppShortcut -Name "Run Collector" -Target (Join-Path $launcherDir "Run-Collector.bat") -WorkDir $appDir -Description "Collect news once"
New-AppShortcut -Name "Start Scheduler" -Target (Join-Path $launcherDir "Start-Scheduler.bat") -WorkDir $appDir -Description "Daily collection scheduler"
New-AppShortcut -Name "Export Data" -Target (Join-Path $launcherDir "Export-Data.bat") -WorkDir $appDir -Description "Export CSV/JSON"

if (-not $NoDesktopShortcut) {
    $desk = [Environment]::GetFolderPath("Desktop")
    $sc = $WshShell.CreateShortcut((Join-Path $desk "RF Political Trends Dashboard.lnk"))
    $sc.TargetPath = (Join-Path $launcherDir "Start-Dashboard.bat")
    $sc.WorkingDirectory = $appDir
    $sc.Description = "RF Political Trends Analyzer"
    $sc.Save()
    Write-Ok "Desktop shortcut created"
}
Write-Ok "Start Menu shortcuts created"

# ---------- 10. Daily Task Scheduler ----------
if (-not $SkipDailyTask) {
    Write-Step "Registering daily collection task (06:00 local time)..."
    $taskName = "RFPoliticalTrendsDailyCollect"
    try {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
        $action = New-ScheduledTaskAction -Execute $pythonVenv -Argument "-m src.collector" -WorkingDirectory $appDir
        $trigger = New-ScheduledTaskTrigger -Daily -At "06:00"
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
        $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
        Write-Ok "Task Scheduler job '$taskName' registered (daily 06:00)"
    } catch {
        Write-Warn "Could not register Task Scheduler job: $_"
        Write-Warn "You can still run Start-Scheduler.bat manually."
    }
}

# ---------- 11. Uninstall script ----------
$uninstPath = Join-Path $InstallDir "uninstall.ps1"
$uninstLines = @(
    "#Requires -Version 5.1",
    "`$ErrorActionPreference = 'SilentlyContinue'",
    "`$InstallDir = '$InstallDir'",
    "Write-Host 'Uninstalling RF Political Trends Analyzer...'",
    "Unregister-ScheduledTask -TaskName 'RFPoliticalTrendsDailyCollect' -Confirm:`$false",
    "`$startMenu = Join-Path `$env:APPDATA 'Microsoft\Windows\Start Menu\Programs\RF Political Trends'",
    "Remove-Item -Recurse -Force `$startMenu",
    "`$desk = [Environment]::GetFolderPath('Desktop')",
    "Remove-Item (Join-Path `$desk 'RF Political Trends Dashboard.lnk') -Force",
    "Remove-Item -Recurse -Force `$InstallDir",
    "Write-Host 'Done.' -ForegroundColor Green"
)
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllLines($uninstPath, $uninstLines, $utf8NoBom)
Write-Ok "Uninstall script: $uninstPath"

# ---------- 12. Optional first collection ----------
Write-Step "Initial data collection (optional)..."
$doCollect = Read-Host "Collect news now? (Y/n)"
if ($doCollect -notin @("n", "N", "no")) {
    Push-Location $appDir
    try {
        & $pythonVenv -m src.collector
        Write-Ok "Initial collection finished"
    } catch {
        Write-Warn "Collection had issues: $_"
    }
    Pop-Location
}

# ---------- Done ----------
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  INSTALLATION COMPLETE" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Location : $InstallDir"
Write-Host "  Dashboard: Start Menu -> RF Political Trends -> Dashboard"
Write-Host "             or Desktop shortcut"
Write-Host "  Daily job: Task Scheduler -> RFPoliticalTrendsDailyCollect"
Write-Host "  Uninstall: $uninstPath"
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Open the Dashboard shortcut to start working." -ForegroundColor Cyan

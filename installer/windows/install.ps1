#Requires -Version 5.1
<#
.SYNOPSIS
    RF Political Trends Analyzer — Windows Installer
.DESCRIPTION
    Downloads the application, creates a virtual environment, installs dependencies,
    links all components, creates Start Menu / Desktop shortcuts and optional daily task.
.NOTES
    Run in PowerShell (preferably as current user, not necessarily Admin).
    Example:  powershell -ExecutionPolicy Bypass -File install.ps1
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

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  [!] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "  [ERROR] $msg" -ForegroundColor Red }

Write-Host @"
╔══════════════════════════════════════════════════════════╗
║   RF Political Trends Analyzer — Windows Installer      ║
║   Public RSS collector + NLP + Streamlit dashboard       ║
╚══════════════════════════════════════════════════════════╝
"@ -ForegroundColor White

# ---------- 1. Check / find Python ----------
Write-Step "Checking Python 3.9+ ..."
$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3\.(\d+)") {
            $minor = [int]$Matches[1]
            if ($minor -ge 9) {
                $python = (Get-Command $cmd).Source
                Write-Ok "Found: $ver ($python)"
                break
            }
        }
    } catch {}
}
if (-not $python) {
    Write-Err "Python 3.9+ not found."
    Write-Host "Download from https://www.python.org/downloads/ and enable 'Add to PATH'." -ForegroundColor Yellow
    Write-Host "Then re-run this installer." -ForegroundColor Yellow
    exit 1
}

# ---------- 2. Check Git (optional but preferred) ----------
Write-Step "Checking Git ..."
$hasGit = $false
try {
    $null = & git --version 2>&1
    $hasGit = $true
    Write-Ok "Git found"
} catch {
    Write-Warn "Git not found — will download ZIP instead of cloning"
}

# ---------- 3. Prepare install directory ----------
Write-Step "Install directory: $InstallDir"
if (Test-Path $InstallDir) {
    if ($Force) {
        Write-Warn "Removing existing installation..."
        Remove-Item -Recurse -Force $InstallDir
    } else {
        $ans = Read-Host "Directory already exists. Overwrite? (y/N)"
        if ($ans -notin @("y", "Y", "yes")) {
            Write-Host "Aborted."
            exit 0
        }
        Remove-Item -Recurse -Force $InstallDir
    }
}
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Write-Ok "Created $InstallDir"

# ---------- 4. Download sources ----------
Write-Step "Downloading application sources..."
$appDir = Join-Path $InstallDir "app"
if ($hasGit) {
    & git clone --depth 1 --branch $Branch $RepoUrl $appDir 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "git clone failed" }
    Write-Ok "Cloned repository"
} else {
    $zipUrl = "https://github.com/karalik19-a11y/rf-political-trends-analyzer/archive/refs/heads/$Branch.zip"
    $zipPath = Join-Path $env:TEMP "rf-pta.zip"
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
    Expand-Archive -Path $zipPath -DestinationPath $InstallDir -Force
    $extracted = Get-ChildItem $InstallDir -Directory | Where-Object { $_.Name -like "rf-political-trends-analyzer-*" } | Select-Object -First 1
    if ($extracted) {
        Rename-Item $extracted.FullName "app"
    }
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
    Write-Ok "Downloaded and extracted ZIP"
}

# ---------- 5. Create virtual environment ----------
Write-Step "Creating Python virtual environment..."
$venvDir = Join-Path $InstallDir "venv"
& $python -m venv $venvDir
if ($LASTEXITCODE -ne 0) { throw "Failed to create venv" }
$pip = Join-Path $venvDir "Scripts\pip.exe"
$pythonVenv = Join-Path $venvDir "Scripts\python.exe"
Write-Ok "venv created"

# ---------- 6. Install dependencies ----------
Write-Step "Installing dependencies (this may take several minutes, especially torch)..."
& $pip install --upgrade pip setuptools wheel | Out-Null

# Prefer CPU torch on Windows to avoid huge CUDA download
Write-Host "  Installing torch (CPU)..." -ForegroundColor DarkGray
& $pip install torch --index-url https://download.pytorch.org/whl/cpu 2>&1 | Out-Null

$reqFile = Join-Path $appDir "requirements.txt"
# Remove torch from requirements if present to avoid conflict (already installed CPU)
$reqContent = Get-Content $reqFile | Where-Object { $_ -notmatch "^torch" }
$tmpReq = Join-Path $env:TEMP "rf-req-filtered.txt"
$reqContent | Set-Content $tmpReq -Encoding UTF8
& $pip install -r $tmpReq
if ($LASTEXITCODE -ne 0) {
    Write-Warn "Some packages may have failed. Trying again without strict version pins..."
    & $pip install feedparser requests pyyaml pandas streamlit plotly sqlalchemy python-dateutil nltk scikit-learn beautifulsoup4 lxml apscheduler transformers sentencepiece protobuf
}
Remove-Item $tmpReq -Force -ErrorAction SilentlyContinue
Write-Ok "Dependencies installed"

# ---------- 7. Create data / exports folders ----------
New-Item -ItemType Directory -Path (Join-Path $appDir "data") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $appDir "exports") -Force | Out-Null

# ---------- 8. Write launcher scripts ----------
Write-Step "Creating launchers..."

$launcherDir = Join-Path $InstallDir "bin"
New-Item -ItemType Directory -Path $launcherDir -Force | Out-Null

# Dashboard launcher
$dashBat = @"
@echo off
cd /d "$appDir"
"$pythonVenv" -m streamlit run src\dashboard.py --server.headless true
pause
"@
Set-Content -Path (Join-Path $launcherDir "Start-Dashboard.bat") -Value $dashBat -Encoding ASCII

# Collector launcher
$collectBat = @"
@echo off
cd /d "$appDir"
"$pythonVenv" -m src.collector
pause
"@
Set-Content -Path (Join-Path $launcherDir "Run-Collector.bat") -Value $collectBat -Encoding ASCII

# Scheduler launcher (console)
$schedBat = @"
@echo off
cd /d "$appDir"
echo Starting daily scheduler (Ctrl+C to stop)...
"$pythonVenv" -m src.scheduler --hour 6 --minute 0
pause
"@
Set-Content -Path (Join-Path $launcherDir "Start-Scheduler.bat") -Value $schedBat -Encoding ASCII

# Export launcher
$exportBat = @"
@echo off
cd /d "$appDir"
"$pythonVenv" -m src.export --format both
echo.
echo Files saved to: $appDir\exports
pause
"@
Set-Content -Path (Join-Path $launcherDir "Export-Data.bat") -Value $exportBat -Encoding ASCII

Write-Ok "Launchers created in $launcherDir"

# ---------- 9. Shortcuts ----------
Write-Step "Creating shortcuts..."
$WshShell = New-Object -ComObject WScript.Shell

$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\RF Political Trends"
New-Item -ItemType Directory -Path $startMenu -Force | Out-Null

function New-Shortcut($name, $target, $workdir, $desc) {
    $sc = $WshShell.CreateShortcut((Join-Path $startMenu "$name.lnk"))
    $sc.TargetPath = $target
    $sc.WorkingDirectory = $workdir
    $sc.Description = $desc
    $sc.Save()
}

New-Shortcut "Dashboard" (Join-Path $launcherDir "Start-Dashboard.bat") $appDir "Open Streamlit dashboard"
New-Shortcut "Run Collector" (Join-Path $launcherDir "Run-Collector.bat") $appDir "Collect news once"
New-Shortcut "Start Scheduler" (Join-Path $launcherDir "Start-Scheduler.bat") $appDir "Daily collection scheduler"
New-Shortcut "Export Data" (Join-Path $launcherDir "Export-Data.bat") $appDir "Export CSV/JSON"

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

# ---------- 10. Optional daily Task Scheduler job ----------
if (-not $SkipDailyTask) {
    Write-Step "Registering daily collection task (06:00 local time)..."
    $taskName = "RFPoliticalTrendsDailyCollect"
    $action = New-ScheduledTaskAction -Execute $pythonVenv `
        -Argument "-m src.collector" `
        -WorkingDirectory $appDir
    $trigger = New-ScheduledTaskTrigger -Daily -At "06:00"
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

    try {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
        Write-Ok "Task Scheduler job '$taskName' registered (daily 06:00)"
    } catch {
        Write-Warn "Could not register Task Scheduler job: $_"
        Write-Warn "You can still run Start-Scheduler.bat manually."
    }
}

# ---------- 11. Write uninstall helper ----------
$uninst = @"
#Requires -Version 5.1
`$InstallDir = "$InstallDir"
Write-Host "Uninstalling RF Political Trends Analyzer..."
Unregister-ScheduledTask -TaskName "RFPoliticalTrendsDailyCollect" -Confirm:`$false -ErrorAction SilentlyContinue
`$startMenu = Join-Path `$env:APPDATA "Microsoft\Windows\Start Menu\Programs\RF Political Trends"
Remove-Item -Recurse -Force `$startMenu -ErrorAction SilentlyContinue
`$desk = [Environment]::GetFolderPath("Desktop")
Remove-Item (Join-Path `$desk "RF Political Trends Dashboard.lnk") -Force -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force `$InstallDir -ErrorAction SilentlyContinue
Write-Host "Done." -ForegroundColor Green
"@
Set-Content -Path (Join-Path $InstallDir "uninstall.ps1") -Value $uninst -Encoding UTF8

# ---------- 12. First collection (optional) ----------
Write-Step "Running initial data collection (optional)..."
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
Write-Host @"

╔══════════════════════════════════════════════════════════╗
║                  INSTALLATION COMPLETE                   ║
╠══════════════════════════════════════════════════════════╣
║  Location : $InstallDir
║  Dashboard: Start Menu → RF Political Trends → Dashboard
║             or Desktop shortcut
║  Daily job: Task Scheduler → RFPoliticalTrendsDailyCollect
║  Uninstall: $InstallDir\uninstall.ps1
╚══════════════════════════════════════════════════════════╝

Open the Dashboard shortcut to start working.
"@ -ForegroundColor Green

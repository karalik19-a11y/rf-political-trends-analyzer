#!/usr/bin/env python3
"""
One entry point:
  python bootstrap.py           -> ensure env + open dashboard
  python bootstrap.py --update  -> update from GitHub then open dashboard
  python bootstrap.py --collect -> collect media then open dashboard
  python bootstrap.py --no-browser
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / "venv"
REQ = ROOT / "requirements.txt"


def venv_python() -> Path:
    if sys.platform == "win32":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def ensure_venv() -> Path:
    py = venv_python()
    if py.exists():
        return py
    print("[1/3] Creating virtual environment...")
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
    if not py.exists():
        raise SystemExit("Failed to create venv")
    return py


def ensure_deps(py: Path) -> None:
    marker = VENV / ".deps_ok"
    need = True
    if marker.exists() and REQ.exists():
        if marker.stat().st_mtime >= REQ.stat().st_mtime:
            need = False
    if not need:
        print("[2/3] Dependencies OK")
        return
    print("[2/3] Installing dependencies (first time may take a few minutes)...")
    subprocess.check_call([str(py), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    subprocess.check_call([str(py), "-m", "pip", "install", "-r", str(REQ)])
    marker.write_text("ok", encoding="utf-8")
    print("     Done.")


def run_update(py: Path) -> None:
    print("[update] Downloading latest from GitHub...")
    # run updater with venv python so requests is available
    code = r"
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve() / 'src'))
from updater import apply_update, check_update
av, info = check_update()
print('local:', info.get('local_version'), 'remote:', info.get('remote_version'), info.get('remote_sha'))
if av or True:
    print(apply_update())
else:
    print('Already up to date')
"
    subprocess.check_call([str(py), "-c", code], cwd=str(ROOT))
    # refresh deps after update
    marker = VENV / ".deps_ok"
    if marker.exists():
        marker.unlink()
    ensure_deps(py)


def run_collect(py: Path) -> None:
    print("[collect] Fetching media + geo tags...")
    subprocess.call([str(py), str(ROOT / "run_collector_regional.py")], cwd=str(ROOT))


def run_dashboard(py: Path) -> None:
    print("[3/3] Starting dashboard (browser will open)...")
    print("      Close the window or Ctrl+C to stop.\n")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + str(ROOT)
    # Prefer regional dashboard; fallback to old if missing
    dash = ROOT / "src" / "dashboard_regional.py"
    if not dash.exists():
        dash = ROOT / "src" / "dashboard.py"
    cmd = [
        str(py),
        "-m",
        "streamlit",
        "run",
        str(dash),
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]
    os.chdir(ROOT)
    raise SystemExit(subprocess.call(cmd, env=env))


def main() -> None:
    parser = argparse.ArgumentParser(description="RF Analytics simple launcher")
    parser.add_argument("--update", action="store_true", help="Update code from GitHub first")
    parser.add_argument("--collect", action="store_true", help="Collect news before UI")
    parser.add_argument("--skip-update-check", action="store_true")
    args = parser.parse_args()

    os.chdir(ROOT)
    py = ensure_venv()
    ensure_deps(py)

    if args.update:
        try:
            run_update(py)
        except Exception as e:
            print("[update] Failed:", e)
            print("         Continuing with local files...")

    if args.collect:
        run_collect(py)

    run_dashboard(py)


if __name__ == "__main__":
    main()

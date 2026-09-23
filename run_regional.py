"""Launch regional analytics dashboard."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    from streamlit.web import cli as stcli

    sys.argv = [
        "streamlit",
        "run",
        str(ROOT / "src" / "dashboard_regional.py"),
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]
    sys.exit(stcli.main())

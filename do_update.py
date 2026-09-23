"""Run self-update (called by bootstrap / UPDATE.bat)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from updater import apply_update, check_update

if __name__ == "__main__":
    available, info = check_update()
    print("local:", info.get("local_version"), info.get("local_sha"))
    print("remote:", info.get("remote_version"), info.get("remote_sha"))
    print(apply_update())

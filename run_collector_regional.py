import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))

from collector_regional import collect_regional

if __name__ == "__main__":
    print("New:", collect_regional())

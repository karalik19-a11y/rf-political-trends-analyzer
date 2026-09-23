"""Reliable entry point for one-shot collection."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    from collector import collect

    n = collect()
    print(f"New items: {n}")

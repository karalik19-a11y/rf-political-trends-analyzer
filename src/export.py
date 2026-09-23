"""Export collected data to CSV / JSON."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from .database import get_all_for_analysis, init_db

BASE_DIR = Path(__file__).resolve().parent.parent
EXPORT_DIR = BASE_DIR / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def export_to_csv(limit: Optional[int] = None, filename: Optional[str] = None) -> Path:
    init_db()
    data = get_all_for_analysis(limit=limit or 10000)
    if not data:
        raise ValueError("No data to export")
    df = pd.DataFrame(data)
    # Convert datetime for clean CSV
    if "published" in df.columns:
        df["published"] = pd.to_datetime(df["published"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = EXPORT_DIR / (filename or f"political_news_{ts}.csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def export_to_json(limit: Optional[int] = None, filename: Optional[str] = None) -> Path:
    init_db()
    data = get_all_for_analysis(limit=limit or 10000)
    if not data:
        raise ValueError("No data to export")
    # Make JSON-serializable
    for item in data:
        if item.get("published") and hasattr(item["published"], "isoformat"):
            item["published"] = item["published"].isoformat()
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = EXPORT_DIR / (filename or f"political_news_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Export RF political news data")
    parser.add_argument("--format", choices=["csv", "json", "both"], default="both")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    if args.format in ("csv", "both"):
        p = export_to_csv(limit=args.limit)
        print(f"CSV exported: {p}")
    if args.format in ("json", "both"):
        p = export_to_json(limit=args.limit)
        print(f"JSON exported: {p}")

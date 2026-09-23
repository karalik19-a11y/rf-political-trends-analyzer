"""B: Election results by federal subject — load public CSV + demo seed."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from territories import load_regions, region_by_code

BASE = Path(__file__).resolve().parent.parent
ELECTIONS_DIR = BASE / "data" / "elections"
ELECTIONS_DIR.mkdir(parents=True, exist_ok=True)

# Expected CSV columns for user-supplied official extracts:
# election_id,region_code,region_name,turnout_pct,valid_ballots,registered_voters,leader_share_pct,source,note
REQUIRED_COLS = [
    "election_id",
    "region_code",
    "turnout_pct",
]


def demo_seed_path() -> Path:
    return ELECTIONS_DIR / "demo_presidential_structure.csv"


def write_demo_seed() -> Path:
    """
    Structural DEMO file for UI/pipeline testing.
    Figures are illustrative placeholders for layout — replace with official CIK extracts.
    """
    path = demo_seed_path()
    rows = []
    # Illustrative variation by federal district only — NOT official results
    fd_bias = {
        "Центральный": (58.0, 72.0),
        "Северо-Западный": (55.0, 68.0),
        "Южный": (62.0, 78.0),
        "Северо-Кавказский": (70.0, 85.0),
        "Приволжский": (57.0, 70.0),
        "Уральский": (56.0, 69.0),
        "Сибирский": (54.0, 67.0),
        "Дальневосточный": (52.0, 65.0),
    }
    for i, r in enumerate(load_regions()):
        lo, hi = fd_bias.get(r.get("fd", ""), (55.0, 70.0))
        # deterministic pseudo variation from code
        code_n = int(r["code"]) if r["code"].isdigit() else i
        turnout = round(lo + (code_n % 17) * (hi - lo) / 20.0, 2)
        leader = round(min(95.0, turnout * 0.9 + (code_n % 11)), 2)
        rows.append(
            {
                "election_id": "DEMO-STRUCTURE-ONLY",
                "region_code": r["code"],
                "region_name": r["name"],
                "turnout_pct": turnout,
                "valid_ballots": 100000 + code_n * 13000,
                "registered_voters": int((100000 + code_n * 13000) / max(turnout / 100, 0.01)),
                "leader_share_pct": leader,
                "source": "DEMO",
                "note": "Placeholder for pipeline/UI — replace via load_elections_csv with official open data",
            }
        )
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return path


def load_elections_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing columns: {missing}. Need at least {REQUIRED_COLS}")
    df["region_code"] = df["region_code"].astype(str).str.zfill(2)
    return df


def list_election_files() -> List[Path]:
    return sorted(ELECTIONS_DIR.glob("*.csv"))


def load_all_elections() -> pd.DataFrame:
    files = list_election_files()
    if not files:
        write_demo_seed()
        files = list_election_files()
    frames = []
    for p in files:
        try:
            frames.append(load_elections_csv(p))
        except Exception:
            continue
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def elections_with_geo() -> pd.DataFrame:
    df = load_all_elections()
    if df.empty:
        return df
    regions = {r["code"]: r for r in load_regions()}
    df["lat"] = df["region_code"].map(lambda c: regions.get(c, {}).get("lat"))
    df["lon"] = df["region_code"].map(lambda c: regions.get(c, {}).get("lon"))
    df["fd"] = df["region_code"].map(lambda c: regions.get(c, {}).get("fd"))
    if "region_name" not in df.columns:
        df["region_name"] = df["region_code"].map(lambda c: regions.get(c, {}).get("name"))
    return df

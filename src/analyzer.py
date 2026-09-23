"""Simple trend and keyword analysis."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple

import pandas as pd

from .database import get_all_for_analysis, get_items_by_date_range


def load_dataframe(limit: int = 3000) -> pd.DataFrame:
    data = get_all_for_analysis(limit=limit)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df["published"] = pd.to_datetime(df["published"], errors="coerce")
    df = df.dropna(subset=["published"])
    return df


def top_keywords(df: pd.DataFrame, top_n: int = 30) -> List[Tuple[str, int]]:
    counter = Counter()
    for kws in df["keywords"].dropna():
        for kw in str(kws).split(","):
            kw = kw.strip()
            if kw:
                counter[kw] += 1
    return counter.most_common(top_n)


def volume_by_day(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    daily = df.set_index("published").resample("D").size().reset_index(name="count")
    return daily


def volume_by_source(df: pd.DataFrame) -> pd.Series:
    return df["source"].value_counts()


def recent_trends(days: int = 7) -> Dict[str, Any]:
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    items = get_items_by_date_range(start, end)
    if not items:
        return {"period_days": days, "total": 0, "top_keywords": [], "by_source": {}}

    titles = [i.title for i in items]
    all_text = " ".join(titles)
    # reuse simple extractor logic
    from .collector import extract_keywords
    kws = extract_keywords(all_text, max_kw=15)
    top = [(k, 1) for k in kws.split(",") if k]  # simplified

    by_source = Counter(i.source for i in items)
    return {
        "period_days": days,
        "total": len(items),
        "top_keywords": top,
        "by_source": dict(by_source),
        "sample_titles": titles[:10],
    }


def keyword_timeline(df: pd.DataFrame, keyword: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    mask = df["title"].str.contains(keyword, case=False, na=False) | df["summary"].str.contains(
        keyword, case=False, na=False
    )
    filtered = df[mask]
    if filtered.empty:
        return pd.DataFrame()
    daily = filtered.set_index("published").resample("D").size().reset_index(name="count")
    return daily

"""Trend and keyword analysis + sentiment aggregates."""

from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple

import pandas as pd

try:
    from database import get_all_for_analysis, get_items_by_date_range
    from nlp_utils import extract_keywords
except ImportError:
    from .database import get_all_for_analysis, get_items_by_date_range
    from .nlp_utils import extract_keywords


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


def sentiment_stats(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty or "sentiment_score" not in df.columns:
        return {"avg": None, "positive": 0, "neutral": 0, "negative": 0, "total_with_score": 0}
    scores = df["sentiment_score"].dropna()
    if scores.empty:
        return {"avg": None, "positive": 0, "neutral": 0, "negative": 0, "total_with_score": 0}
    pos = int((scores > 0.2).sum())
    neg = int((scores < -0.2).sum())
    neu = len(scores) - pos - neg
    return {
        "avg": float(scores.mean()),
        "positive": pos,
        "neutral": neu,
        "negative": neg,
        "total_with_score": len(scores),
    }


def recent_trends(days: int = 7) -> Dict[str, Any]:
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    items = get_items_by_date_range(start, end)
    if not items:
        return {"period_days": days, "total": 0, "top_keywords": [], "by_source": {}, "sentiment": {}, "sample_titles": []}

    titles = [i.title for i in items]
    all_text = " ".join(titles)
    kws = extract_keywords(all_text, max_kw=15)
    top = [(k, 1) for k in kws.split(",") if k]
    by_source = Counter(i.source for i in items)
    scores = [i.sentiment_score for i in items if i.sentiment_score is not None]
    sent = {"avg": sum(scores) / len(scores) if scores else None, "count": len(scores)}
    return {
        "period_days": days,
        "total": len(items),
        "top_keywords": top,
        "by_source": dict(by_source),
        "sample_titles": titles[:10],
        "sentiment": sent,
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
    return filtered.set_index("published").resample("D").size().reset_index(name="count")

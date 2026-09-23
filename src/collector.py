"""Collect public RSS feeds for RF political news."""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from email.utils import parsedate_to_datetime

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup

from .database import init_db, upsert_item
from .nlp_utils import extract_keywords, analyze_sentiment

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "sources.yaml"


def load_config() -> Dict[str, Any]:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def clean_html(text: str) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, "lxml")
    return soup.get_text(separator=" ", strip=True)


def parse_date(entry) -> datetime:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6])
            except Exception:
                pass
    for attr in ("published", "updated"):
        s = getattr(entry, attr, None)
        if s:
            try:
                return parsedate_to_datetime(s)
            except Exception:
                pass
    return datetime.utcnow()


def fetch_feed(url: str, user_agent: str, timeout: int) -> feedparser.FeedParserDict:
    headers = {"User-Agent": user_agent}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return feedparser.parse(resp.content)


def collect() -> int:
    """Run one collection cycle. Returns number of new items."""
    init_db()
    cfg = load_config()
    settings = cfg.get("settings", {})
    ua = settings.get("user_agent", "RF-Political-Trends-Analyzer/1.1")
    timeout = settings.get("request_timeout", 15)
    delay = settings.get("delay_between_requests", 1.5)
    max_items = settings.get("max_items_per_source", 50)
    enable_sentiment = settings.get("enable_sentiment", True)
    model_name = settings.get("sentiment_model", "cointegrated/rubert-tiny-sentiment-balanced")

    total_new = 0
    for src in cfg.get("sources", []):
        if not src.get("enabled", True):
            continue
        name = src["name"]
        url = src["url"]
        logger.info("Collecting from %s ...", name)
        try:
            feed = fetch_feed(url, ua, timeout)
            count = 0
            for entry in feed.entries[:max_items]:
                link = entry.get("link") or entry.get("id")
                if not link:
                    continue
                title = clean_html(entry.get("title", ""))
                summary = clean_html(entry.get("summary", "") or entry.get("description", ""))
                published = parse_date(entry)
                full_text = f"{title} {summary}"
                keywords = extract_keywords(full_text)

                sentiment = None
                if enable_sentiment:
                    sentiment = analyze_sentiment(full_text, model_name=model_name)

                item = {
                    "source": name,
                    "title": title,
                    "link": link,
                    "summary": summary[:2000] if summary else None,
                    "published": published,
                    "category": src.get("category", "politics"),
                    "language": src.get("language", "ru"),
                    "keywords": keywords,
                    "sentiment_score": sentiment,
                }
                if upsert_item(item):
                    count += 1
                    total_new += 1
            logger.info("  +%d new items from %s", count, name)
        except Exception as e:
            logger.error("  Error collecting %s: %s", name, e)
        time.sleep(delay)

    logger.info("Done. Total new items: %d", total_new)
    return total_new


if __name__ == "__main__":
    collect()

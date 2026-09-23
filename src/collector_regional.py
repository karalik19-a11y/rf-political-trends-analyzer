"""Collect independent RSS + geo-tag to regions/cities."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup

from geo_tagger import tag_text
from nlp_utils import extract_keywords
from regional_db import init_regional_db, upsert_news

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
    return BeautifulSoup(text, "lxml").get_text(separator=" ", strip=True)


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


def collect_regional() -> int:
    init_regional_db()
    cfg = load_config()
    settings = cfg.get("settings", {})
    ua = settings.get("user_agent", "RF-Regional-Analytics/2.0")
    timeout = settings.get("request_timeout", 20)
    delay = settings.get("delay_between_requests", 2.0)
    max_items = settings.get("max_items_per_source", 40)

    total_new = 0
    for src in cfg.get("sources", []):
        if not src.get("enabled", True):
            continue
        name = src["name"]
        url = src["url"]
        logger.info("Collecting %s", name)
        try:
            resp = requests.get(url, headers={"User-Agent": ua}, timeout=timeout)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            count = 0
            for entry in feed.entries[:max_items]:
                link = entry.get("link") or entry.get("id")
                if not link:
                    continue
                title = clean_html(entry.get("title", ""))
                summary = clean_html(entry.get("summary", "") or entry.get("description", ""))
                full = f"{title} {summary}"
                geo = tag_text(full)
                item = {
                    "source": name,
                    "title": title,
                    "link": link,
                    "summary": (summary or "")[:2000] or None,
                    "published": parse_date(entry),
                    "category": src.get("category", "politics"),
                    "language": src.get("language", "ru"),
                    "keywords": extract_keywords(full),
                    "region_code": geo.get("region_code"),
                    "city_tag": geo.get("city"),
                }
                if upsert_news(item):
                    count += 1
                    total_new += 1
            logger.info("  +%d from %s", count, name)
        except Exception as e:
            logger.error("  %s: %s", name, e)
        time.sleep(delay)
    logger.info("Total new: %d", total_new)
    return total_new


if __name__ == "__main__":
    collect_regional()

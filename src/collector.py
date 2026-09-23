"""Collect public RSS feeds for RF political news."""

import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from email.utils import parsedate_to_datetime

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup

from .database import init_db, upsert_item

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


def parse_date(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6])
            except Exception:
                pass
    # fallback string parse
    for attr in ("published", "updated"):
        s = getattr(entry, attr, None)
        if s:
            try:
                return parsedate_to_datetime(s)
            except Exception:
                pass
    return datetime.utcnow()


def extract_keywords(text: str, max_kw: int = 8) -> str:
    """Very simple keyword extraction (frequency-based). For production use better NLP."""
    if not text:
        return ""
    # Russian stopwords (minimal set)
    stop = {
        "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то", "все",
        "она", "так", "его", "но", "да", "ты", "к", "у", "же", "вы", "за", "бы", "по",
        "только", "ее", "мне", "было", "вот", "от", "меня", "еще", "нет", "о", "из",
        "ему", "теперь", "когда", "даже", "ну", "вдруг", "ли", "если", "уже", "или",
        "ни", "быть", "был", "него", "до", "вас", "нибудь", "опять", "уж", "вам",
        "ведь", "там", "потом", "себя", "ничего", "ей", "может", "они", "тут", "где",
        "есть", "надо", "ней", "для", "мы", "тебя", "их", "чем", "была", "сам",
        "чтоб", "без", "будто", "чего", "раз", "тоже", "себе", "под", "будет",
        "ж", "тогда", "кто", "этот", "того", "потому", "этого", "какой", "совсем",
        "ним", "здесь", "этом", "один", "почти", "мой", "тем", "чтобы", "нее",
        "сейчас", "были", "куда", "зачем", "всех", "никогда", "можно", "при",
        "наконец", "два", "об", "другой", "хоть", "после", "над", "больше",
        "тот", "через", "эти", "нас", "про", "всего", "них", "какая", "много",
        "разве", "три", "эту", "моя", "впрочем", "хорошо", "свою", "этой",
        "перед", "иногда", "лучше", "чуть", "том", "нельзя", "такой", "им",
        "более", "всегда", "конечно", "всю", "между", "это", "также", "россия",
        "рф", "российский", "года", "году", "года",
    }
    words = []
    for w in text.lower().replace(".", " ").replace(",", " ").split():
        w = w.strip("«»\"'\-–—()[]")
        if len(w) > 3 and w not in stop and w.isalpha():
            words.append(w)
    from collections import Counter
    most = Counter(words).most_common(max_kw)
    return ",".join(w for w, _ in most)


def fetch_feed(url: str, user_agent: str, timeout: int) -> feedparser.FeedParserDict:
    headers = {"User-Agent": user_agent}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return feedparser.parse(resp.content)


def collect() -> None:
    init_db()
    cfg = load_config()
    settings = cfg.get("settings", {})
    ua = settings.get("user_agent", "RF-Political-Trends-Analyzer/1.0")
    timeout = settings.get("request_timeout", 15)
    delay = settings.get("delay_between_requests", 1.5)
    max_items = settings.get("max_items_per_source", 50)

    total_new = 0
    for src in cfg.get("sources", []):
        if not src.get("enabled", True):
            continue
        name = src["name"]
        url = src["url"]
        print(f"Collecting from {name} ...")
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

                item = {
                    "source": name,
                    "title": title,
                    "link": link,
                    "summary": summary[:2000] if summary else None,
                    "published": published,
                    "category": src.get("category", "politics"),
                    "language": src.get("language", "ru"),
                    "keywords": keywords,
                }
                if upsert_item(item):
                    count += 1
                    total_new += 1
            print(f"  +{count} new items from {name}")
        except Exception as e:
            print(f"  Error collecting {name}: {e}")
        time.sleep(delay)

    print(f"Done. Total new items: {total_new}")


if __name__ == "__main__":
    collect()

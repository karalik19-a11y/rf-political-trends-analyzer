"""SQLite extensions: media items with region tags."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Index, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "political_news.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    link = Column(String(1000), unique=True, nullable=False)
    summary = Column(Text)
    published = Column(DateTime, index=True)
    collected_at = Column(DateTime, default=datetime.utcnow)
    category = Column(String(50))
    language = Column(String(10), default="ru")
    keywords = Column(Text)
    sentiment_score = Column(Float, nullable=True)
    region_code = Column(String(8), index=True, nullable=True)
    city_tag = Column(String(100), nullable=True)

    __table_args__ = (Index("ix_region_published", "region_code", "published"),)


def init_regional_db() -> None:
    Base.metadata.create_all(engine)
    # migrate: add columns if old DB exists without them
    with engine.connect() as conn:
        cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(news_items)").fetchall()]
        if "region_code" not in cols:
            conn.exec_driver_sql("ALTER TABLE news_items ADD COLUMN region_code VARCHAR(8)")
            conn.commit()
        if "city_tag" not in cols:
            conn.exec_driver_sql("ALTER TABLE news_items ADD COLUMN city_tag VARCHAR(100)")
            conn.commit()


def upsert_news(item: Dict[str, Any]) -> bool:
    session = SessionLocal()
    try:
        existing = session.query(NewsItem).filter_by(link=item["link"]).first()
        if existing:
            # update geo if empty
            if not existing.region_code and item.get("region_code"):
                existing.region_code = item["region_code"]
                existing.city_tag = item.get("city_tag")
                session.commit()
            return False
        row = NewsItem(
            source=item.get("source", "unknown"),
            title=(item.get("title") or "")[:500],
            link=item["link"],
            summary=item.get("summary"),
            published=item.get("published"),
            category=item.get("category"),
            language=item.get("language", "ru"),
            keywords=item.get("keywords"),
            sentiment_score=item.get("sentiment_score"),
            region_code=item.get("region_code"),
            city_tag=item.get("city_tag"),
        )
        session.add(row)
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def media_by_region(limit: int = 5000) -> List[Dict[str, Any]]:
    session = SessionLocal()
    try:
        rows = (
            session.query(NewsItem)
            .order_by(NewsItem.published.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "source": r.source,
                "title": r.title,
                "summary": r.summary or "",
                "published": r.published,
                "keywords": r.keywords,
                "region_code": r.region_code,
                "city_tag": r.city_tag,
                "link": r.link,
            }
            for r in rows
        ]
    finally:
        session.close()


def region_mention_counts() -> Dict[str, int]:
    from collections import Counter
    session = SessionLocal()
    try:
        rows = session.query(NewsItem.region_code).filter(NewsItem.region_code.isnot(None)).all()
        return dict(Counter(r[0] for r in rows if r[0]))
    finally:
        session.close()

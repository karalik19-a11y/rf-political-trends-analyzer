"""SQLite storage for collected news items."""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Index
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
    keywords = Column(Text)  # comma-separated
    sentiment_score = Column(Float, nullable=True)  # -1 .. +1

    __table_args__ = (
        Index("ix_published_source", "published", "source"),
    )


def init_db() -> None:
    Base.metadata.create_all(engine)


def upsert_item(item: Dict[str, Any]) -> bool:
    """Insert if link not exists. Returns True if inserted."""
    session = SessionLocal()
    try:
        existing = session.query(NewsItem).filter_by(link=item["link"]).first()
        if existing:
            return False
        news = NewsItem(
            source=item.get("source", "unknown"),
            title=item.get("title", "")[:500],
            link=item["link"],
            summary=item.get("summary"),
            published=item.get("published"),
            category=item.get("category"),
            language=item.get("language", "ru"),
            keywords=item.get("keywords"),
            sentiment_score=item.get("sentiment_score"),
        )
        session.add(news)
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_recent_items(limit: int = 100, source: Optional[str] = None) -> List[NewsItem]:
    session = SessionLocal()
    try:
        q = session.query(NewsItem).order_by(NewsItem.published.desc())
        if source:
            q = q.filter(NewsItem.source == source)
        return q.limit(limit).all()
    finally:
        session.close()


def get_items_by_date_range(start: datetime, end: datetime) -> List[NewsItem]:
    session = SessionLocal()
    try:
        return (
            session.query(NewsItem)
            .filter(NewsItem.published >= start, NewsItem.published <= end)
            .order_by(NewsItem.published.desc())
            .all()
        )
    finally:
        session.close()


def get_all_for_analysis(limit: int = 5000) -> List[Dict[str, Any]]:
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
                "sentiment_score": r.sentiment_score,
                "link": r.link,
            }
            for r in rows
        ]
    finally:
        session.close()


def get_all_items(limit: Optional[int] = None) -> List[NewsItem]:
    session = SessionLocal()
    try:
        q = session.query(NewsItem).order_by(NewsItem.published.desc())
        if limit:
            q = q.limit(limit)
        return q.all()
    finally:
        session.close()

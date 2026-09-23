"""Russian NLP utilities: keywords + sentiment using transformers."""

from __future__ import annotations

import logging
from collections import Counter
from functools import lru_cache
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Minimal Russian stopwords
STOPWORDS = {
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
    "рф", "российский", "года", "году", "года", "который", "которая", "которые",
}


def extract_keywords(text: str, max_kw: int = 8) -> str:
    """Frequency-based keyword extraction for Russian text."""
    if not text:
        return ""
    words = []
    for w in text.lower().replace(".", " ").replace(",", " ").replace("!", " ").replace("?", " ").split():
        w = w.strip("«»\"'\-–—()[]:;").lower()
        if len(w) > 3 and w not in STOPWORDS and w.isalpha():
            words.append(w)
    most = Counter(words).most_common(max_kw)
    return ",".join(w for w, _ in most)


@lru_cache(maxsize=1)
def _load_sentiment_pipeline(model_name: str = "cointegrated/rubert-tiny-sentiment-balanced"):
    """Lazy-load sentiment pipeline. Falls back gracefully if transformers/torch unavailable."""
    try:
        from transformers import pipeline
        pipe = pipeline(
            "sentiment-analysis",
            model=model_name,
            tokenizer=model_name,
            truncation=True,
            max_length=512,
        )
        logger.info("Sentiment model loaded: %s", model_name)
        return pipe
    except Exception as e:
        logger.warning("Could not load sentiment model (%s). Sentiment will be skipped. Error: %s", model_name, e)
        return None


def analyze_sentiment(text: str, model_name: str = "cointegrated/rubert-tiny-sentiment-balanced") -> Optional[float]:
    """
    Return sentiment score in [-1, 1] range roughly:
    positive ~ +1, neutral ~ 0, negative ~ -1.
    Returns None if model unavailable or text empty.
    """
    if not text or not text.strip():
        return None
    pipe = _load_sentiment_pipeline(model_name)
    if pipe is None:
        return None
    try:
        # Take first 500 chars to stay within limits
        result = pipe(text[:500])[0]
        label = result["label"].lower()
        score = float(result["score"])
        if "positive" in label or label in ("pos", "positive"):
            return score
        if "negative" in label or label in ("neg", "negative"):
            return -score
        # neutral or other
        return 0.0
    except Exception as e:
        logger.debug("Sentiment analysis failed: %s", e)
        return None


def batch_sentiment(texts: List[str], model_name: str = "cointegrated/rubert-tiny-sentiment-balanced") -> List[Optional[float]]:
    """Analyze a list of texts. Returns list of scores."""
    pipe = _load_sentiment_pipeline(model_name)
    if pipe is None:
        return [None] * len(texts)
    results = []
    for t in texts:
        results.append(analyze_sentiment(t, model_name))
    return results

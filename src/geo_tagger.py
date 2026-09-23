"""C: Bind media text to region/city (aggregate toponyms, not individuals)."""

from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

from territories import alias_map, region_by_code, CITY_TO_REGION


def _normalize(text: str) -> str:
    t = text.lower().replace("ё", "е")
    t = re.sub(r"[^\w\s\-]", " ", t, flags=re.UNICODE)
    return t


def tag_text(text: str) -> Dict[str, Optional[str]]:
    """
    Return primary region_code, city_name (if matched), and all matched codes.
    Uses longest-token / multi-word city names first.
    """
    if not text:
        return {"region_code": None, "city": None, "all_codes": []}

    norm = _normalize(text)
    aliases = alias_map()

    # Sort keys by length desc to match «нижний новгород» before «новгород»
    keys = sorted(aliases.keys(), key=len, reverse=True)
    found_codes: List[str] = []
    found_city: Optional[str] = None

    for key in keys:
        if len(key) < 3:
            continue
        # word-boundary-ish
        pattern = r"(?<!\w)" + re.escape(key) + r"(?!\w)"
        if re.search(pattern, norm):
            code = aliases[key]
            found_codes.append(code)
            if key in CITY_TO_REGION and not found_city:
                found_city = key

    if not found_codes:
        return {"region_code": None, "city": found_city, "all_codes": []}

    # majority vote
    primary = Counter(found_codes).most_common(1)[0][0]
    return {
        "region_code": primary,
        "city": found_city,
        "all_codes": list(dict.fromkeys(found_codes)),
    }


def tag_batch(texts: List[str]) -> List[Dict]:
    return [tag_text(t) for t in texts]

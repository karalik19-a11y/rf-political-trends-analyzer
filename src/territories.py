"""A: Territory reference — regions + major cities for geo binding."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE = Path(__file__).resolve().parent.parent
REGIONS_PATH = BASE / "data" / "reference" / "regions.json"

# Major cities → region code (for media geo-tagging). Not street-level.
CITY_TO_REGION: Dict[str, str] = {
    "москва": "77", "санкт-петербург": "78", "петербург": "78", "спб": "78",
    "новосибирск": "54", "екатеринбург": "66", "казань": "16", "нижний новгород": "52",
    "челябинск": "74", "самара": "63", "омск": "55", "ростов-на-дону": "61", "ростов": "61",
    "уфа": "02", "красноярск": "24", "пермь": "59", "воронеж": "36", "волгоград": "34",
    "краснодар": "23", "саратов": "64", "тюмень": "72", "тольятти": "63", "ижевск": "18",
    "барнаул": "22", "ульяновск": "73", "иркутск": "38", "хабаровск": "27",
    "ярославль": "76", "владивосток": "25", "махачкала": "05", "томск": "70",
    "оренбург": "56", "кемерово": "42", "новокузнецк": "42", "рязань": "62",
    "астрахань": "30", "пенза": "58", "липецк": "48", "тула": "71", "киров": "43",
    "чебоксары": "21", "калининград": "39", "брянск": "32", "курск": "46",
    "иваново": "37", "магнитогорск": "74", "тверь": "69", "ставрополь": "26",
    "белгород": "31", "сочи": "23", "нижний тагил": "66", "архангельск": "29",
    "владикавказ": "15", "калуга": "40", "смоленск": "67", "череповец": "35",
    "саранск": "13", "вологда": "35", "якутск": "14", "грозный": "20",
    "таганрог": "61", "кострома": "44", "петрозаводск": "10", "стерлитамак": "02",
    "орёл": "57", "орел": "57", "мурманск": "51", "смоленск": "67",
    "набережные челны": "16", "сыктывкар": "11", "комсомольск-на-амуре": "27",
    "таганрог": "61", "йошкар-ола": "12", "братск": "38", "дзержинск": "52",
    "орск": "56", "ангарск": "38", "благовещенск": "28", "псков": "60",
    "бийск": "22", "прокопьевск": "42", "химки": "50", "балашиха": "50",
    "подольск": "50", "мытищи": "50", "люберцы": "50", "королев": "50",
    "севастополь": "92", "симферополь": "91",
}

# Aliases for region names in text
REGION_ALIASES: Dict[str, str] = {}


@lru_cache(maxsize=1)
def load_regions() -> List[Dict[str, Any]]:
    if not REGIONS_PATH.exists():
        return []
    with open(REGIONS_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_alias_map() -> Dict[str, str]:
    m: Dict[str, str] = {}
    for r in load_regions():
        code = r["code"]
        name = r["name"].lower()
        m[name] = code
        # short forms
        for part in name.replace("—", "-").split():
            if len(part) > 4 and part not in ("республика", "область", "край", "округ", "автономный", "автономная"):
                m[part] = code
        capital = r.get("capital", "").lower()
        if capital:
            m[capital] = code
        m[r["code"]] = code
    m.update({k: v for k, v in CITY_TO_REGION.items()})
    return m


@lru_cache(maxsize=1)
def alias_map() -> Dict[str, str]:
    return build_alias_map()


def region_by_code(code: str) -> Optional[Dict[str, Any]]:
    for r in load_regions():
        if r["code"] == code:
            return r
    return None


def all_region_codes() -> List[str]:
    return [r["code"] for r in load_regions()]


def regions_dataframe():
    import pandas as pd
    return pd.DataFrame(load_regions())

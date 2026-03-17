"""
USDA FoodData Central API client.

Used for ingredient canonicalization: get FDC ID + food category for an
ingredient name. Prices come from LLM (see pricing.py) — USDA FDC is
nutritional data only, but the category is valuable context for price estimates.
"""

import httpx
from config import get_settings

_BASE = "https://api.nal.usda.gov/fdc/v1"
_DATA_TYPES = "Foundation,SR Legacy"  # most reliable for whole-food ingredients


def search_ingredient(name: str) -> dict | None:
    """
    Search USDA FoodData Central for an ingredient by name.

    Returns:
        {"fdc_id": int, "name": str, "category": str | None}
        or None if no match found or API key is missing.
    """
    settings = get_settings()
    if not settings.usda_api_key:
        return None

    try:
        resp = httpx.get(
            f"{_BASE}/foods/search",
            params={
                "query": name,
                "api_key": settings.usda_api_key,
                "pageSize": 5,
                "dataType": _DATA_TYPES,
            },
            timeout=8,
        )
        resp.raise_for_status()
    except Exception:
        return None

    foods = resp.json().get("foods", [])
    if not foods:
        return None

    best = foods[0]
    category = (
        best.get("foodCategory")
        or best.get("foodCategoryLabel")
        or best.get("wweiaFoodCategory", {}).get("wweiaFoodCategoryDescription")
    )
    return {
        "fdc_id": best.get("fdcId"),
        "name": best.get("description", name),
        "category": category,
    }

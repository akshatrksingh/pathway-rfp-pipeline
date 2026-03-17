"""
Ingredient pricing service.

Strategy:
  1. Check DB cache — return existing price_data if TTL still valid.
  2. USDA FDC lookup — enriches ingredient with fdc_id + category (no price).
  3. LLM estimate — generate calibrated wholesale price using ingredient name
     + USDA category + regional + seasonal context.
     Source="llm_estimate", confidence="low", TTL=1d.
"""

import json
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session

from models import Ingredient, PriceData
from services.usda_client import search_ingredient
from services.llm_client import LLMClient

_LLM_TTL = timedelta(days=1)

# ---------------------------------------------------------------------------
# Calibration anchors injected into every LLM prompt
# ---------------------------------------------------------------------------
_ANCHOR_TEXT = """
Calibration anchors (US wholesale / restaurant-supply, 2025-2026):
- Tomatoes (roma/plum): $1.40–$1.80/lb
- Chicken breast (boneless): $3.20–$3.80/lb
- Chicken wings: $2.80–$3.50/lb
- Ground beef (80/20): $4.00–$5.00/lb
- Mozzarella (low-moisture block): $3.60–$4.20/lb
- Cheddar: $3.20–$3.80/lb
- Butter (unsalted): $3.80–$4.50/lb
- Whole milk: $3.50–$4.20/gallon
- All-purpose flour: $0.45–$0.65/lb
- White rice: $0.55–$0.80/lb
- Pasta (dried): $0.90–$1.30/lb
- Olive oil (extra virgin): $14–$18/gallon
- Vegetable oil: $6–$9/gallon
- Yellow onions: $0.40–$0.70/lb
- Russet potatoes: $0.50–$0.80/lb
- Garlic: $1.20–$1.80/lb
- Lettuce (romaine): $0.80–$1.20/lb
- Bell peppers: $0.90–$1.40/lb
- Eggs (large grade A): $3.50–$4.50/dozen
- Salmon (Atlantic fillet): $8–$11/lb
- Shrimp (31/40 count): $6–$9/lb
- Heavy cream: $4.50–$6.00/gallon
- Sour cream: $2.50–$3.50/lb
- Cream cheese: $3.00–$4.00/lb
- Chicken thighs (bone-in): $2.00–$2.80/lb
- Hot sauce / buffalo sauce: $12–$22/gallon
- Ketchup: $8–$14/gallon
- Marinara / tomato sauce: $9–$16/gallon
- Pizza dough (fresh, 16oz ball): $1.20–$2.00/each
- Bread flour: $0.55–$0.75/lb
- Yeast (instant dry): $4–$7/lb
""".strip()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _current_season() -> str:
    m = date.today().month
    if m in (12, 1, 2):  return "winter"
    if m == 3:            return "late winter / early spring"
    if m in (4, 5):       return "spring"
    if m in (6, 7, 8):    return "summer"
    if m == 9:            return "early fall"
    return "fall"


def _normalize_unit(raw: str) -> str:
    if not raw:
        return "lb"
    u = raw.lower().strip()
    for prefix in ("usd/", "$/", "us$/"):
        if u.startswith(prefix):
            u = u[len(prefix):]
    unit_map = {
        "lbs": "lb", "pound": "lb", "pounds": "lb",
        "gallons": "gallon", "gal": "gallon",
        "dozens": "dozen",
        "ounce": "oz", "ounces": "oz",
        "case": "case", "cases": "case",
        "each": "each", "ea": "each",
        "kilogram": "kg", "kilograms": "kg",
    }
    return unit_map.get(u, u)


def _canonical_unit(name: str, usda_category: str | None) -> str:
    name_lower = name.lower()
    liquid_keywords = (
        "sauce", "juice", "oil", "milk", "cream", "broth", "stock",
        "vinegar", "syrup", "dressing", "marinade", "brine", "water",
        "soda", "beer", "wine", "liquor", "spirit", "extract",
    )
    if any(k in name_lower for k in liquid_keywords):
        return "gallon"
    if "egg" in name_lower:
        return "dozen"
    return "lb"


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _get_cached(db: Session, ingredient_id: int) -> PriceData | None:
    return (
        db.query(PriceData)
        .filter(
            PriceData.ingredient_id == ingredient_id,
            PriceData.expires_at > datetime.utcnow(),
        )
        .order_by(PriceData.fetched_at.desc())
        .first()
    )


# ---------------------------------------------------------------------------
# LLM estimate
# ---------------------------------------------------------------------------

def _llm_estimate(
    name: str,
    usda_category: str | None,
    unit: str,
    city: str,
    state: str,
) -> dict:
    season = _current_season()
    location = f"{city}, {state}" if city or state else "a major US city"
    category_hint = f" (USDA category: {usda_category})" if usda_category else ""

    client = LLMClient()
    messages = [
        {
            "role": "system",
            "content": (
                "You are a restaurant food-cost analyst specializing in US wholesale markets.\n\n"
                f"{_ANCHOR_TEXT}\n\n"
                "Instructions:\n"
                "- Provide WHOLESALE / restaurant-supply prices only — NOT retail supermarket prices.\n"
                f"- Location: {location}. Adjust for any regional cost differences.\n"
                f"- Current season: {season}. Seasonal produce costs more out of season.\n"
                f"- Use {unit} as the price unit (standard bulk wholesale unit).\n"
                "- Be realistic. Cross-check your answer against the calibration anchors above.\n"
                "- Return ONLY JSON, no explanation:\n"
                '{"price_low": number, "price_avg": number, "price_high": number, "unit": "string"}'
            ),
        },
        {
            "role": "user",
            "content": (
                f"Estimate the US wholesale restaurant-supply price for: "
                f"{name}{category_hint}, per {unit}."
            ),
        },
    ]
    return client.get_json_completion(messages)


# ---------------------------------------------------------------------------
# Batch LLM estimate — one call for all uncached ingredients
# ---------------------------------------------------------------------------

def _llm_estimate_batch(
    items: list[dict],   # [{name, usda_category, unit}, ...]
    city: str,
    state: str,
) -> dict[str, dict]:
    """
    Single LLM call for all uncached ingredients.
    Returns {name_lower: {price_low, price_avg, price_high, unit}}.
    """
    if not items:
        return {}

    season   = _current_season()
    location = f"{city}, {state}" if city or state else "a major US city"
    items_json = json.dumps([
        {"name": i["name"], "unit": i["unit"],
         **({"usda_category": i["usda_category"]} if i.get("usda_category") else {})}
        for i in items
    ])

    client = LLMClient()
    messages = [
        {
            "role": "system",
            "content": (
                "You are a restaurant food-cost analyst specializing in US wholesale markets.\n\n"
                f"{_ANCHOR_TEXT}\n\n"
                "Instructions:\n"
                "- Provide WHOLESALE / restaurant-supply prices only — NOT retail supermarket prices.\n"
                f"- Location: {location}. Adjust for any regional cost differences.\n"
                f"- Current season: {season}. Seasonal produce costs more out of season.\n"
                "- Be realistic. Cross-check against the calibration anchors above.\n"
                "- Return ONLY JSON — no explanation:\n"
                '{"estimates": [{"name": "string", "price_low": number, '
                '"price_avg": number, "price_high": number, "unit": "string"}]}\n'
                "Include every ingredient in the input, even if uncertain."
            ),
        },
        {
            "role": "user",
            "content": f"Estimate US wholesale restaurant-supply prices for:\n{items_json}",
        },
    ]
    try:
        result = client.get_json_completion(messages)
        entries = result.get("estimates", []) if isinstance(result, dict) else result
        return {
            (e.get("name") or "").lower().strip(): e
            for e in entries
            if e.get("price_avg") is not None
        }
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def price_ingredient(
    db: Session,
    ingredient: Ingredient,
    unit: str | None = None,
    city: str = "",
    state: str = "",
) -> tuple[PriceData, str]:
    """
    Return (PriceData, origin).
    origin: 'cached' | 'llm_estimate' | 'failed'

    Side-effects:
      - Updates ingredient.usda_fdc_id / usda_category if USDA returns a match.
      - Writes a new PriceData row (unless returning cached).
    """
    # 1. Cache check
    cached = _get_cached(db, ingredient.id)
    if cached:
        return cached, "cached"

    # 2. USDA enrichment (non-fatal — provides category context for LLM)
    try:
        usda = search_ingredient(ingredient.name)
        if usda:
            ingredient.usda_fdc_id   = usda["fdc_id"]
            ingredient.usda_category = usda["category"]
            db.flush()
    except Exception:
        pass

    bulk_unit  = _canonical_unit(ingredient.name, ingredient.usda_category)
    price_low = price_avg = price_high = None
    price_unit = bulk_unit
    source     = "failed"
    confidence = "none"
    expires_at = datetime.utcnow() + timedelta(hours=1)

    # 3. LLM estimate
    try:
        est = _llm_estimate(
            name=ingredient.name,
            usda_category=ingredient.usda_category,
            unit=bulk_unit,
            city=city,
            state=state,
        )
        price_low  = est.get("price_low")
        price_avg  = est.get("price_avg")
        price_high = est.get("price_high")
        price_unit = _normalize_unit(est.get("unit") or bulk_unit)
        source     = "llm_estimate"
        confidence = "low"
        expires_at = datetime.utcnow() + _LLM_TTL
    except Exception:
        pass

    pd = PriceData(
        ingredient_id=ingredient.id,
        price_low=price_low,
        price_avg=price_avg,
        price_high=price_high,
        unit=price_unit,
        source=source,
        confidence=confidence,
        expires_at=expires_at,
    )
    db.add(pd)
    db.flush()
    return pd, source

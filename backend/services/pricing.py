"""
Ingredient pricing service.

Strategy (real data first, LLM fallback):
  1. Check DB cache — return existing price_data if TTL still valid.
  2. USDA FDC lookup — enriches ingredient with fdc_id + category (no price).
  3. Tavily search — search for current US wholesale prices; LLM extracts
     structured price from search snippets. Source="tavily", confidence="high", TTL=7d.
  4. LLM estimate fallback — if Tavily yields nothing, generate a calibrated
     wholesale price using anchors + regional + seasonal context.
     Source="llm_estimate", confidence="low", TTL=1d.

TTLs:
  - Tavily / API prices : 7 days
  - LLM estimates       : 1 day   (refresh when real data becomes available)
"""

from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session

from config import get_settings
from models import Ingredient, PriceData
from services.usda_client import search_ingredient
from services.llm_client import LLMClient

settings = get_settings()

_TAVILY_TTL = timedelta(days=7)
_LLM_TTL    = timedelta(days=1)

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
- Chicken wings (frozen, IQF): $2.80–$3.50/lb
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
    """Return a descriptive season string based on today's month."""
    m = date.today().month
    if m in (12, 1, 2):
        return "winter"
    if m == 3:
        return "late winter / early spring"
    if m in (4, 5):
        return "spring"
    if m in (6, 7, 8):
        return "summer"
    if m == 9:
        return "early fall"
    return "fall"


def _normalize_unit(raw: str) -> str:
    """
    Normalize unit strings from LLM/Tavily extraction.
    'USD/lb' → 'lb', 'Gallon' → 'gallon', '$/dozen' → 'dozen', etc.
    """
    if not raw:
        return "lb"
    u = raw.lower().strip()
    # Strip currency prefixes like "usd/", "$/"
    for prefix in ("usd/", "$/", "us$/"):
        if u.startswith(prefix):
            u = u[len(prefix):]
    # Normalize common variants
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


def _sanity_check(price: float | None, unit: str, ingredient_name: str) -> float | None:
    """
    Reject prices outside plausible wholesale food ranges.
    Returns None → caller falls back to LLM estimate.
    """
    if price is None:
        return None
    if unit == "lb"     and (price < 0.05 or price > 60):
        return None
    if unit == "gallon" and (price < 0.50 or price > 70):
        return None
    if unit == "dozen"  and (price < 0.50 or price > 40):
        return None
    if unit == "oz"     and (price < 0.01 or price > 8):
        return None
    if unit == "case"   and (price < 5    or price > 300):
        return None
    return price


def _canonical_unit(name: str, usda_category: str | None) -> str:
    """
    Pick the most natural bulk wholesale unit for an ingredient.
    Liquids → gallons. Eggs → dozen. Everything else → lbs.
    """
    name_lower = name.lower()
    cat_lower  = (usda_category or "").lower()

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
# Step 2: Tavily price search
# ---------------------------------------------------------------------------

def _tavily_price_search(ingredient_name: str, unit: str) -> list[dict]:
    """Search Tavily for current wholesale prices. Returns [] on any failure."""
    if not settings.tavily_api_key:
        return []
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_api_key)
        query  = f"wholesale {ingredient_name} price per {unit} restaurant supply USA 2025 2026"
        resp   = client.search(query=query, max_results=4, search_depth="basic")
        return resp.get("results", [])
    except Exception:
        return []


def _extract_price_from_search(
    ingredient_name: str,
    unit: str,
    search_results: list[dict],
) -> dict | None:
    """
    Use LLM to extract a structured wholesale price from Tavily snippets.
    Returns {price_low, price_avg, price_high, unit} or None.
    """
    if not search_results:
        return None

    snippets = []
    for r in search_results:
        title   = r.get("title", "")
        content = (r.get("content") or r.get("raw_content") or "")[:500]
        snippets.append(f"Title: {title}\n{content}")
    blob = "\n\n---\n\n".join(snippets)

    client = LLMClient()
    messages = [
        {
            "role": "system",
            "content": (
                "You are a data extraction assistant. Extract the wholesale or restaurant-supply "
                f"price for '{ingredient_name}' per {unit} from the search results below.\n\n"
                "Rules:\n"
                "- Only extract prices that clearly refer to wholesale / food-service / bulk pricing.\n"
                "- Ignore retail grocery prices.\n"
                "- If multiple prices are found, derive a low, average, and high.\n"
                "- If NO credible wholesale price data is present, return null.\n\n"
                "Return ONLY JSON:\n"
                '{"price_low": number_or_null, "price_avg": number_or_null, '
                '"price_high": number_or_null, "unit": "string_or_null"}\n'
                "Return {\"price_low\": null, \"price_avg\": null, \"price_high\": null, \"unit\": null} "
                "if nothing credible is found."
            ),
        },
        {
            "role": "user",
            "content": f"Search results:\n\n{blob}",
        },
    ]
    try:
        result = client.get_json_completion(messages)
        if result.get("price_avg") is None:
            return None
        return result
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Step 3: LLM estimate (calibrated fallback)
# ---------------------------------------------------------------------------

def _llm_estimate(
    name: str,
    usda_category: str | None,
    unit: str,
    city: str,
    state: str,
) -> dict:
    """
    Generate a calibrated wholesale price estimate via LLM.
    Uses anchors, regional context, and season for realism.
    """
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

    origin: 'cached' | 'tavily' | 'llm_estimate' | 'failed'

    Side-effects:
      - Updates ingredient.usda_fdc_id / usda_category if USDA returns a match.
      - Writes a new PriceData row (unless returning cached).
    """
    # 1. Cache hit
    cached = _get_cached(db, ingredient.id)
    if cached:
        return cached, "cached"

    # 2. USDA enrichment (non-fatal — provides category context for LLM)
    usda = search_ingredient(ingredient.name)
    if usda:
        ingredient.usda_fdc_id   = usda["fdc_id"]
        ingredient.usda_category = usda["category"]
        db.flush()

    # Determine canonical bulk unit
    bulk_unit = _canonical_unit(ingredient.name, ingredient.usda_category)

    # 3. Tavily price search
    price_low = price_avg = price_high = None
    price_unit = bulk_unit
    source     = "failed"
    confidence = "none"
    expires_at = datetime.utcnow() + timedelta(hours=1)

    search_results = _tavily_price_search(ingredient.name, bulk_unit)
    if search_results:
        extracted = _extract_price_from_search(ingredient.name, bulk_unit, search_results)
        if extracted and extracted.get("price_avg") is not None:
            raw_unit   = _normalize_unit(extracted.get("unit") or bulk_unit)
            p_avg      = _sanity_check(extracted.get("price_avg"), raw_unit, ingredient.name)
            if p_avg is not None:
                price_low  = _sanity_check(extracted.get("price_low"),  raw_unit, ingredient.name)
                price_avg  = p_avg
                price_high = _sanity_check(extracted.get("price_high"), raw_unit, ingredient.name)
                price_unit = raw_unit
                source     = "tavily"
                confidence = "high"
                expires_at = datetime.utcnow() + _TAVILY_TTL

    # 4. LLM estimate fallback
    if source != "tavily":
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
            pass  # leave source="failed"

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

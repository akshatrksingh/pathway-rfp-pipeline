"""
Ingredient pricing service.

Strategy (API-first, LLM-fallback):
  1. Check DB cache — return existing price_data if TTL is still valid.
  2. USDA FDC lookup — enriches ingredient with fdc_id + category (no price data).
  3. LLM estimate — generate wholesale price range using ingredient name + USDA
     category as context. Stored with source="llm_estimate", confidence="low", TTL=1d.

TTLs:
  - API-sourced prices  : 7 days  (placeholder for future real pricing API)
  - LLM estimates       : 1 day   (refresh often so real data can replace them)
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models import Ingredient, PriceData
from services.usda_client import search_ingredient
from services.llm_client import LLMClient

_API_TTL  = timedelta(days=7)
_LLM_TTL  = timedelta(days=1)


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
# LLM price estimate
# ---------------------------------------------------------------------------

def _llm_estimate(name: str, usda_category: str | None, unit: str | None) -> dict:
    category_hint = f" (USDA category: {usda_category})" if usda_category else ""
    unit_hint     = f" per {unit}" if unit else " per lb"

    client = LLMClient()
    messages = [
        {
            "role": "system",
            "content": (
                "You are a food cost expert. Estimate the typical US wholesale restaurant "
                "price range for the given ingredient. Return ONLY JSON, no explanation:\n"
                '{"price_low": number, "price_avg": number, "price_high": number, "unit": "string"}\n'
                "Use realistic 2024 US wholesale market prices. "
                "price_low/avg/high are all in USD. unit should match the most natural bulk unit."
            ),
        },
        {
            "role": "user",
            "content": f"Wholesale price for: {name}{category_hint}{unit_hint}",
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
) -> tuple[PriceData, str]:
    """
    Return (PriceData, origin) where origin is 'cached' | 'llm_estimate' | 'failed'.

    Side-effects:
      - Updates ingredient.usda_fdc_id / usda_category if USDA returns a match.
      - Writes a new PriceData row (unless returning cached).
    """
    # 1. Cache hit
    cached = _get_cached(db, ingredient.id)
    if cached:
        return cached, "cached"

    # 2. USDA enrichment (non-fatal)
    usda = search_ingredient(ingredient.name)
    if usda:
        ingredient.usda_fdc_id  = usda["fdc_id"]
        ingredient.usda_category = usda["category"]
        db.flush()

    # 3. LLM price estimate
    try:
        est = _llm_estimate(
            name=ingredient.name,
            usda_category=ingredient.usda_category,
            unit=unit,
        )
        price_low  = est.get("price_low")
        price_avg  = est.get("price_avg")
        price_high = est.get("price_high")
        price_unit = est.get("unit") or unit or "lb"
        expires_at = datetime.utcnow() + _LLM_TTL
        source     = "llm_estimate"
        confidence = "low"
    except Exception:
        price_low = price_avg = price_high = None
        price_unit = unit or "lb"
        expires_at = datetime.utcnow() + timedelta(hours=1)
        source     = "failed"
        confidence = "none"

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

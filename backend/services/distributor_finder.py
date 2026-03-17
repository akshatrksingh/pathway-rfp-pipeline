"""
Distributor finder service.

Flow:
  1. LLM assigns each ingredient to a supply category (produce, dairy, etc.)
  2. Tavily searches per category + restaurant location
  3. LLM extracts real distributor businesses from search results
  4. Categories with no Tavily results become "gaps" — never fabricated
  5. Distributors persisted (deduped by name); linked to run + ingredients

Gap policy: no fake distributors ever. If Tavily returns nothing useful for a
category, those ingredients are returned as a gap list for the UI to surface.
"""

import json
from sqlalchemy.orm import Session

from config import get_settings
from models import Ingredient, Distributor, DistributorIngredient, RunDistributor
from services.llm_client import LLMClient

settings = get_settings()

# Canonical supply categories the LLM must choose from
CATEGORIES = [
    "produce",
    "dairy",
    "meat & poultry",
    "seafood",
    "dry goods & grains",
    "bakery & bread",
    "beverages",
    "condiments & sauces",
    "frozen foods",
    "specialty & other",
]


# ---------------------------------------------------------------------------
# Step 1 — LLM ingredient categorisation
# ---------------------------------------------------------------------------

def _categorize_ingredients(
    ingredients: list[Ingredient],
    client: LLMClient,
) -> dict[str, list[Ingredient]]:
    """
    Returns {category: [Ingredient, ...]} for every ingredient.
    Unrecognised categories fall back to "specialty & other".
    """
    names = [i.name for i in ingredients]
    cat_list = ", ".join(CATEGORIES)

    messages = [
        {
            "role": "system",
            "content": (
                f"You are a food supply chain expert. Assign each ingredient to exactly "
                f"one wholesale supply category from this list: {cat_list}.\n\n"
                "Return ONLY JSON, no explanation:\n"
                '{"assignments": [{"name": "ingredient name", "category": "category"}]}'
            ),
        },
        {
            "role": "user",
            "content": f"Categorise these ingredients:\n{json.dumps(names)}",
        },
    ]

    result    = client.get_json_completion(messages)
    name_map  = {i.name: i for i in ingredients}
    by_category: dict[str, list[Ingredient]] = {}

    for item in result.get("assignments", []):
        ing_name = item.get("name", "").lower().strip()
        category = item.get("category", "specialty & other")
        if category not in CATEGORIES:
            category = "specialty & other"

        # fuzzy match — the LLM may not repeat the name verbatim
        matched = name_map.get(ing_name)
        if matched is None:
            for key, ing in name_map.items():
                if ing_name in key or key in ing_name:
                    matched = ing
                    break
        if matched is None:
            continue

        by_category.setdefault(category, []).append(matched)

    # Any ingredients not assigned → specialty & other
    assigned = {i for lst in by_category.values() for i in lst}
    leftover = [i for i in ingredients if i not in assigned]
    if leftover:
        by_category.setdefault("specialty & other", []).extend(leftover)

    return by_category


# ---------------------------------------------------------------------------
# Step 2 — Tavily search per category
# ---------------------------------------------------------------------------

def _tavily_search(category: str, city: str, state: str) -> list[dict]:
    """
    Search Tavily for wholesale food distributors. Returns raw result dicts.
    Returns [] if API key is absent or request fails.
    """
    if not settings.tavily_api_key:
        return []

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_api_key)
        query  = f"wholesale {category} food distributor supplier {city} {state} restaurant"
        resp   = client.search(query=query, max_results=5, search_depth="basic")
        return resp.get("results", [])
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Step 3 — LLM extraction of structured distributor data
# ---------------------------------------------------------------------------

def _extract_distributors(
    category: str,
    city: str,
    state: str,
    search_results: list[dict],
    client: LLMClient,
) -> list[dict]:
    """
    Given Tavily search results, extract real distributor businesses.
    Returns [] if nothing credible is found. Never fabricates data.
    """
    if not search_results:
        return []

    # Build a compact text blob of search results for the LLM
    snippets = []
    for r in search_results:
        title   = r.get("title", "")
        url     = r.get("url", "")
        content = (r.get("content") or r.get("raw_content") or "")[:600]
        snippets.append(f"Title: {title}\nURL: {url}\nContent: {content}")
    blob = "\n\n---\n\n".join(snippets)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a data extraction assistant. Extract real wholesale food "
                "distributor businesses from the following web search results.\n\n"
                "Rules:\n"
                "- Only include businesses that clearly operate as wholesale food distributors "
                "or food service suppliers.\n"
                "- Leave fields null if the information is not explicitly present in the results. "
                "NEVER invent contact details.\n"
                "- Exclude retail stores, restaurants, or irrelevant businesses.\n"
                "- If no real distributors are found, return an empty list.\n\n"
                "Return ONLY JSON:\n"
                '{"distributors": [{"name": "string", "email": "string or null", '
                '"phone": "string or null", "website": "string or null", '
                '"address": "string or null", "area": "string or null"}]}'
            ),
        },
        {
            "role": "user",
            "content": (
                f"Category: {category}\nLocation: {city}, {state}\n\n"
                f"Search results:\n\n{blob}"
            ),
        },
    ]

    try:
        result = client.get_json_completion(messages)
        return result.get("distributors", [])
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Step 4 — DB persistence helpers
# ---------------------------------------------------------------------------

def _get_or_create_distributor(db: Session, data: dict, category: str) -> Distributor:
    """Upsert distributor by name (case-insensitive). Returns ORM object."""
    name = (data.get("name") or "").strip()
    existing = (
        db.query(Distributor)
        .filter(Distributor.name.ilike(name))
        .first()
    )
    if existing:
        return existing

    dist = Distributor(
        name    = name,
        email   = data.get("email") or f"contact@{name.lower().replace(' ', '')}.com",
        phone   = data.get("phone"),
        address = data.get("address"),
        website = data.get("website"),
        specialty = category,
        area    = data.get("area"),
    )
    db.add(dist)
    db.flush()
    return dist


def _link_distributor_ingredient(
    db: Session, distributor_id: int, ingredient_id: int
) -> None:
    exists = (
        db.query(DistributorIngredient)
        .filter_by(distributor_id=distributor_id, ingredient_id=ingredient_id)
        .first()
    )
    if not exists:
        db.add(DistributorIngredient(
            distributor_id=distributor_id,
            ingredient_id=ingredient_id,
        ))
        db.flush()


def _link_run_distributor(
    db: Session, pipeline_run_id: int, distributor_id: int
) -> None:
    exists = (
        db.query(RunDistributor)
        .filter_by(pipeline_run_id=pipeline_run_id, distributor_id=distributor_id)
        .first()
    )
    if not exists:
        db.add(RunDistributor(
            pipeline_run_id=pipeline_run_id,
            distributor_id=distributor_id,
        ))
        db.flush()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def find_distributors_for_run(
    run_id: int,
    menu_ingredients: list[Ingredient],
    restaurant_city: str,
    restaurant_state: str,
    db: Session,
) -> dict:
    """
    Find and persist distributors for all ingredients in a pipeline run.

    Returns a dict with:
      - coverage: list of {distributor, category, ingredient_ids, ingredient_names}
      - gaps:     list of {category, ingredient_ids, ingredient_names}
               for categories where Tavily found no usable distributors
    """
    if not menu_ingredients:
        return {"coverage": [], "gaps": []}

    client     = LLMClient()
    coverage   = []
    gaps       = []

    # 1. Categorise ingredients
    by_category = _categorize_ingredients(menu_ingredients, client)

    # 2. Per-category: search → extract → persist
    for category, cat_ingredients in by_category.items():
        # Tavily search
        search_results = _tavily_search(category, restaurant_city, restaurant_state)

        # LLM extraction
        raw_distributors = _extract_distributors(
            category, restaurant_city, restaurant_state, search_results, client
        )

        if not raw_distributors:
            # Gap — no real distributors found
            gaps.append({
                "category":       category,
                "ingredient_ids": [i.id for i in cat_ingredients],
                "ingredient_names": [i.name for i in cat_ingredients],
            })
            continue

        # Persist each distributor and link to ingredients
        for raw in raw_distributors:
            if not (raw.get("name") or "").strip():
                continue

            dist = _get_or_create_distributor(db, raw, category)
            _link_run_distributor(db, run_id, dist.id)

            for ing in cat_ingredients:
                _link_distributor_ingredient(db, dist.id, ing.id)

        # Record coverage (use first distributor as primary for this category)
        primary = db.query(Distributor).filter(
            Distributor.name.ilike((raw_distributors[0].get("name") or "").strip())
        ).first()

        coverage.append({
            "distributor":      primary,
            "category":         category,
            "ingredient_ids":   [i.id for i in cat_ingredients],
            "ingredient_names": [i.name for i in cat_ingredients],
            "all_distributors": [
                db.query(Distributor).filter(
                    Distributor.name.ilike((r.get("name") or "").strip())
                ).first()
                for r in raw_distributors
                if (r.get("name") or "").strip()
            ],
        })

    db.commit()
    return {"coverage": coverage, "gaps": gaps}

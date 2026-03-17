"""
Distributor finder service.

Total API calls: 2 (one Tavily search, two LLM calls).
  1. ONE LLM call — categorise all ingredients into supply categories.
  2. ONE Tavily search — "wholesale food distributors near {city} {state}".
  3. ONE LLM call — extract distributors from results + map to categories.

Gap policy: no fake distributors ever. Categories with no matched distributor
are returned as gaps for the UI to surface.
"""

import json
from sqlalchemy.orm import Session

from config import get_settings
from models import Ingredient, Distributor, DistributorIngredient, RunDistributor
from services.llm_client import LLMClient

settings = get_settings()

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
# Step 1 — ONE LLM call: categorise all ingredients
# ---------------------------------------------------------------------------

def _categorize_ingredients(
    ingredients: list[Ingredient],
    client: LLMClient,
) -> dict[str, list[Ingredient]]:
    """Returns {category: [Ingredient, ...]}. One LLM call total."""
    names    = [i.name for i in ingredients]
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

    result   = client.get_json_completion(messages)
    name_map = {i.name: i for i in ingredients}
    by_category: dict[str, list[Ingredient]] = {}

    for item in result.get("assignments", []):
        ing_name = item.get("name", "").lower().strip()
        category = item.get("category", "specialty & other")
        if category not in CATEGORIES:
            category = "specialty & other"

        matched = name_map.get(ing_name)
        if matched is None:
            for key, ing in name_map.items():
                if ing_name in key or key in ing_name:
                    matched = ing
                    break
        if matched is None:
            continue

        by_category.setdefault(category, []).append(matched)

    # Anything unassigned → specialty & other
    assigned = {i for lst in by_category.values() for i in lst}
    leftover = [i for i in ingredients if i not in assigned]
    if leftover:
        by_category.setdefault("specialty & other", []).extend(leftover)

    return by_category


# ---------------------------------------------------------------------------
# Step 2 — ONE Tavily search for all distributors
# ---------------------------------------------------------------------------

def _tavily_search_all(city: str, state: str) -> list[dict]:
    """Single Tavily search covering all wholesale food distributors near the restaurant."""
    if not settings.tavily_api_key:
        return []
    try:
        from tavily import TavilyClient
        tc    = TavilyClient(api_key=settings.tavily_api_key)
        query = f"wholesale food distributor supplier {city} {state} restaurant supply"
        resp  = tc.search(query=query, max_results=8, search_depth="basic")
        return resp.get("results", [])
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Step 3 — ONE LLM call: extract distributors + map to categories
# ---------------------------------------------------------------------------

def _extract_and_match_distributors(
    search_results: list[dict],
    present_categories: list[str],
    city: str,
    state: str,
    client: LLMClient,
) -> list[dict]:
    """
    From one search result blob, extract real distributors and map each to the
    supply categories it serves.

    Returns [{"name", "categories": [...], "email", "phone", "website", "area"}]
    """
    if not search_results:
        return []

    snippets = []
    for r in search_results:
        title   = r.get("title", "")
        url     = r.get("url", "")
        content = (r.get("content") or r.get("raw_content") or "")[:600]
        snippets.append(f"Title: {title}\nURL: {url}\nContent: {content}")
    blob = "\n\n---\n\n".join(snippets)

    cat_json = json.dumps(present_categories)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a data extraction assistant. Extract real wholesale food distributor "
                "businesses from the web search results below. For each distributor, identify "
                "which supply categories from the provided list it serves.\n\n"
                "Rules:\n"
                "- Only include businesses that clearly operate as wholesale food distributors "
                "or food-service suppliers.\n"
                "- Leave contact fields null if not in the results. NEVER invent details.\n"
                "- Exclude retail stores, restaurants, or irrelevant businesses.\n"
                f"- Categories to map to: {cat_json}\n"
                "- Each distributor may cover multiple categories.\n"
                "- If no real distributors are found, return an empty list.\n\n"
                "Return ONLY JSON:\n"
                '{"distributors": [{"name": "string", '
                '"categories": ["category1", "category2"], '
                '"email": "string or null", "phone": "string or null", '
                '"website": "string or null", "area": "string or null"}]}'
            ),
        },
        {
            "role": "user",
            "content": f"Location: {city}, {state}\n\nSearch results:\n\n{blob}",
        },
    ]

    try:
        result = client.get_json_completion(messages)
        return result.get("distributors", [])
    except Exception:
        return []


# ---------------------------------------------------------------------------
# DB persistence helpers
# ---------------------------------------------------------------------------

def _get_or_create_distributor(db: Session, data: dict, primary_category: str) -> Distributor:
    name = (data.get("name") or "").strip()
    existing = db.query(Distributor).filter(Distributor.name.ilike(name)).first()
    if existing:
        return existing

    dist = Distributor(
        name      = name,
        email     = data.get("email") or "",
        phone     = data.get("phone"),
        address   = data.get("address"),
        website   = data.get("website"),
        specialty = primary_category,
        area      = data.get("area"),
    )
    db.add(dist)
    db.flush()
    return dist


def _link_distributor_ingredient(db: Session, distributor_id: int, ingredient_id: int) -> None:
    exists = db.query(DistributorIngredient).filter_by(
        distributor_id=distributor_id, ingredient_id=ingredient_id
    ).first()
    if not exists:
        db.add(DistributorIngredient(distributor_id=distributor_id, ingredient_id=ingredient_id))
        db.flush()


def _link_run_distributor(db: Session, pipeline_run_id: int, distributor_id: int) -> None:
    exists = db.query(RunDistributor).filter_by(
        pipeline_run_id=pipeline_run_id, distributor_id=distributor_id
    ).first()
    if not exists:
        db.add(RunDistributor(pipeline_run_id=pipeline_run_id, distributor_id=distributor_id))
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
    Find and persist distributors for all ingredients. Returns coverage + gaps.

    API calls: 1 LLM (categorise) + 1 Tavily + 1 LLM (extract+match) = 3 total.
    """
    if not menu_ingredients:
        return {"coverage": [], "gaps": []}

    client = LLMClient()

    # Step 1: categorise all ingredients (1 LLM call)
    by_category = _categorize_ingredients(menu_ingredients, client)

    # Step 2: one Tavily search for all distributors
    search_results = _tavily_search_all(restaurant_city, restaurant_state)

    # Step 3: extract distributors + map to categories (1 LLM call)
    present_categories = list(by_category.keys())
    raw_distributors   = _extract_and_match_distributors(
        search_results, present_categories, restaurant_city, restaurant_state, client
    )

    # Build a category → [distributor_dicts] mapping from LLM output
    category_to_raws: dict[str, list[dict]] = {}
    for raw in raw_distributors:
        if not (raw.get("name") or "").strip():
            continue
        for cat in raw.get("categories", []):
            if cat in CATEGORIES:
                category_to_raws.setdefault(cat, []).append(raw)

    # Persist distributors and build coverage/gaps
    coverage: list[dict] = []
    gaps:     list[dict] = []

    for category, cat_ingredients in by_category.items():
        raws = category_to_raws.get(category, [])

        if not raws:
            gaps.append({
                "category":         category,
                "ingredient_ids":   [i.id for i in cat_ingredients],
                "ingredient_names": [i.name for i in cat_ingredients],
            })
            continue

        dist_objects = []
        for raw in raws:
            dist = _get_or_create_distributor(db, raw, category)
            _link_run_distributor(db, run_id, dist.id)
            for ing in cat_ingredients:
                _link_distributor_ingredient(db, dist.id, ing.id)
            dist_objects.append(dist)

        coverage.append({
            "distributor":      dist_objects[0],
            "category":         category,
            "ingredient_ids":   [i.id for i in cat_ingredients],
            "ingredient_names": [i.name for i in cat_ingredients],
            "all_distributors": dist_objects,
        })

    db.commit()
    return {"coverage": coverage, "gaps": gaps}

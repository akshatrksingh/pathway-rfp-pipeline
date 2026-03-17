from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Restaurant, Menu, Dish, Ingredient, DishIngredient, PipelineRun, Distributor
from schemas import (
    PipelineStartRequest, PipelineStartResponse,
    IngredientPriceResult, PricingResponse,
    DistributorOut, DistributorCoverage, DistributorGap, DistributorSearchResponse,
)
from datetime import datetime, timedelta
from services.pricing import _get_cached, _canonical_unit, _normalize_unit, _llm_estimate_batch, _LLM_TTL
from services.usda_client import search_ingredient
from models import PriceData
from services.distributor_finder import find_distributors_for_run

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


# ---------------------------------------------------------------------------
# POST /api/pipeline/start
# ---------------------------------------------------------------------------

@router.post("/start", response_model=PipelineStartResponse)
def start_pipeline(body: PipelineStartRequest, db: Session = Depends(get_db)):
    """
    Persist confirmed dishes/ingredients and create a pipeline run.

    Steps:
      1. Create Restaurant
      2. Create Menu (raw_text stores dish count as a summary)
      3. Create PipelineRun
      4. For each dish: Dish → Ingredient (get-or-create, global) → DishIngredient
    """
    # 1. Restaurant
    restaurant = Restaurant(
        name=body.restaurant_name or "Unnamed restaurant",
        address=body.restaurant_address or "",
        city=body.restaurant_city or "",
        state=body.restaurant_state or "",
    )
    db.add(restaurant)
    db.flush()

    # 2. Menu
    dish_names = ", ".join(d.name for d in body.dishes[:5])
    summary    = f"{len(body.dishes)} dishes: {dish_names}{'…' if len(body.dishes) > 5 else ''}"
    menu = Menu(
        restaurant_id=restaurant.id,
        name="Confirmed menu",
        raw_text=summary,
    )
    db.add(menu)
    db.flush()

    # 3. Pipeline run
    run = PipelineRun(
        restaurant_id=restaurant.id,
        menu_id=menu.id,
        status="ingredients_confirmed",
    )
    db.add(run)
    db.flush()

    # 4. Dishes + ingredients
    for dish_data in body.dishes:
        dish = Dish(
            menu_id=menu.id,
            name=dish_data.name,
            description=dish_data.description,
            category=dish_data.category,
        )
        db.add(dish)
        db.flush()

        for ing_data in dish_data.ingredients:
            canonical = ing_data.name.lower().strip()
            if not canonical:
                continue

            # Global ingredient dedup by name
            ingredient = (
                db.query(Ingredient)
                .filter(Ingredient.name == canonical)
                .first()
            )
            if not ingredient:
                ingredient = Ingredient(name=canonical)
                db.add(ingredient)
                db.flush()

            qty = float(ing_data.quantity) if ing_data.quantity is not None else None
            db.add(DishIngredient(
                dish_id=dish.id,
                ingredient_id=ingredient.id,
                quantity=qty,
                unit=ing_data.unit,
                notes=ing_data.notes,
                edit_status="unchanged",
            ))

    db.commit()

    return PipelineStartResponse(
        run_id=run.id,
        restaurant_id=restaurant.id,
        menu_id=menu.id,
    )


# ---------------------------------------------------------------------------
# POST /api/pipeline/{run_id}/pricing
# ---------------------------------------------------------------------------

@router.post("/{run_id}/pricing", response_model=PricingResponse)
def run_pricing(run_id: int, db: Session = Depends(get_db)):
    """
    Price every unique ingredient in a pipeline run.

    Pass 1: return cached prices immediately.
    Pass 2: USDA-enrich all uncached ingredients (adds category context).
    Pass 3: one batch LLM call for all uncached → single rate-limit slot.
    """
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found.")

    restaurant = db.query(Restaurant).filter(Restaurant.id == run.restaurant_id).first()
    city  = restaurant.city  if restaurant else ""
    state = restaurant.state if restaurant else ""

    dish_ids = [
        row.id for row in db.query(Dish.id).filter(Dish.menu_id == run.menu_id).all()
    ]
    if not dish_ids:
        raise HTTPException(status_code=422, detail="No dishes found for this run.")

    dis = db.query(DishIngredient).filter(DishIngredient.dish_id.in_(dish_ids)).all()
    seen: dict[int, str | None] = {}
    for di in dis:
        if di.ingredient_id not in seen:
            seen[di.ingredient_id] = di.unit

    results:      list[IngredientPriceResult] = []
    cached_count = 0
    uncached:     list[Ingredient] = []

    # Pass 1: serve cached, collect uncached
    for ing_id in seen:
        ingredient = db.query(Ingredient).filter(Ingredient.id == ing_id).first()
        if not ingredient:
            continue
        cached = _get_cached(db, ingredient.id)
        if cached:
            cached_count += 1
            results.append(IngredientPriceResult(
                ingredient_id=ingredient.id,
                ingredient_name=ingredient.name,
                fdc_id=ingredient.usda_fdc_id,
                usda_category=ingredient.usda_category,
                price_low=cached.price_low,
                price_avg=cached.price_avg,
                price_high=cached.price_high,
                unit=cached.unit,
                source=cached.source,
                confidence=cached.confidence,
            ))
        else:
            uncached.append(ingredient)

    # Pass 2: USDA-enrich uncached (fast REST calls, adds category for LLM context)
    for ingredient in uncached:
        try:
            usda = search_ingredient(ingredient.name)
            if usda:
                ingredient.usda_fdc_id   = usda["fdc_id"]
                ingredient.usda_category = usda["category"]
                db.flush()
        except Exception:
            pass

    # Pass 3: one batch LLM call for all uncached ingredients
    batch_items = [
        {"name": ing.name,
         "usda_category": ing.usda_category,
         "unit": _canonical_unit(ing.name, ing.usda_category)}
        for ing in uncached
    ]
    llm_prices = _llm_estimate_batch(batch_items, city, state)

    llm_count = 0
    for ingredient in uncached:
        bulk_unit = _canonical_unit(ingredient.name, ingredient.usda_category)
        est       = llm_prices.get(ingredient.name.lower().strip(), {})

        if est.get("price_avg") is not None:
            source     = "llm_estimate"
            confidence = "low"
            expires_at = datetime.utcnow() + _LLM_TTL
            llm_count += 1
        else:
            source     = "failed"
            confidence = "none"
            expires_at = datetime.utcnow() + timedelta(hours=1)

        pd = PriceData(
            ingredient_id=ingredient.id,
            price_low=est.get("price_low"),
            price_avg=est.get("price_avg"),
            price_high=est.get("price_high"),
            unit=_normalize_unit(est.get("unit") or bulk_unit),
            source=source,
            confidence=confidence,
            expires_at=expires_at,
        )
        db.add(pd)
        db.flush()

        results.append(IngredientPriceResult(
            ingredient_id=ingredient.id,
            ingredient_name=ingredient.name,
            fdc_id=ingredient.usda_fdc_id,
            usda_category=ingredient.usda_category,
            price_low=pd.price_low,
            price_avg=pd.price_avg,
            price_high=pd.price_high,
            unit=pd.unit,
            source=pd.source,
            confidence=pd.confidence,
        ))

    run.status = "pricing_complete"
    db.commit()

    return PricingResponse(
        run_id=run_id,
        results=results,
        total=len(results),
        api_count=0,
        llm_count=llm_count,
        cached_count=cached_count,
    )


# ---------------------------------------------------------------------------
# POST /api/pipeline/{run_id}/distributors
# ---------------------------------------------------------------------------

@router.post("/{run_id}/distributors", response_model=DistributorSearchResponse)
def run_distributors(run_id: int, db: Session = Depends(get_db)):
    """
    Find wholesale distributors for every ingredient in the pipeline run.

    Steps:
      1. Load all unique ingredients for this run.
      2. LLM assigns each to a supply category.
      3. Tavily search per category + restaurant location.
      4. LLM extracts real distributor data from search results.
      5. Persist distributors + links; return coverage + gaps.

    Gaps = categories where no real distributor was found. Never fabricated.
    """
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found.")

    restaurant = db.query(Restaurant).filter(Restaurant.id == run.restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found.")

    # Collect unique ingredients for this run
    dish_ids = [
        row.id for row in db.query(Dish.id).filter(Dish.menu_id == run.menu_id).all()
    ]
    if not dish_ids:
        raise HTTPException(status_code=422, detail="No dishes found for this run.")

    dis = db.query(DishIngredient).filter(DishIngredient.dish_id.in_(dish_ids)).all()
    seen_ids: set[int] = set()
    ingredients: list[Ingredient] = []
    for di in dis:
        if di.ingredient_id not in seen_ids:
            seen_ids.add(di.ingredient_id)
            ing = db.query(Ingredient).filter(Ingredient.id == di.ingredient_id).first()
            if ing:
                ingredients.append(ing)

    if not ingredients:
        raise HTTPException(status_code=422, detail="No ingredients found for this run.")

    # Run the finder
    result = find_distributors_for_run(
        run_id=run_id,
        menu_ingredients=ingredients,
        restaurant_city=restaurant.city,
        restaurant_state=restaurant.state,
        db=db,
    )

    # Build response
    coverage_out: list[DistributorCoverage] = []
    all_dist_ids: set[int] = set()

    for cov in result["coverage"]:
        dist_ids   = [d.id for d in cov["all_distributors"] if d]
        dist_names = [d.name for d in cov["all_distributors"] if d]
        all_dist_ids.update(dist_ids)
        coverage_out.append(DistributorCoverage(
            category=cov["category"],
            distributor_ids=dist_ids,
            distributor_names=dist_names,
            ingredient_ids=cov["ingredient_ids"],
            ingredient_names=cov["ingredient_names"],
        ))

    gaps_out: list[DistributorGap] = [
        DistributorGap(
            category=g["category"],
            ingredient_ids=g["ingredient_ids"],
            ingredient_names=g["ingredient_names"],
        )
        for g in result["gaps"]
    ]

    # Full distributor detail for every found distributor
    distributors_out = [
        DistributorOut.model_validate(
            db.query(Distributor).filter(Distributor.id == did).first()
        )
        for did in all_dist_ids
    ]

    gap_ingredient_count = sum(len(g["ingredient_ids"]) for g in result["gaps"])
    covered_count        = len(ingredients) - gap_ingredient_count

    run.status = "distributors_found"
    db.commit()

    return DistributorSearchResponse(
        run_id=run_id,
        coverage=coverage_out,
        gaps=gaps_out,
        distributors=distributors_out,
        total_ingredients=len(ingredients),
        covered_count=covered_count,
        gap_count=gap_ingredient_count,
    )

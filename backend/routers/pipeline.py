from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Restaurant, Menu, Dish, Ingredient, DishIngredient, PipelineRun
from schemas import (
    PipelineStartRequest, PipelineStartResponse,
    IngredientPriceResult, PricingResponse,
)
from services.pricing import price_ingredient

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

    For each ingredient:
      - Returns cached price if TTL is valid.
      - Otherwise: USDA FDC lookup (enriches ingredient) + LLM price estimate.
    """
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found.")

    # Collect unique ingredients (ingredient_id → representative unit)
    dish_ids = [
        row.id
        for row in db.query(Dish.id).filter(Dish.menu_id == run.menu_id).all()
    ]
    if not dish_ids:
        raise HTTPException(status_code=422, detail="No dishes found for this run.")

    dis = (
        db.query(DishIngredient)
        .filter(DishIngredient.dish_id.in_(dish_ids))
        .all()
    )
    # First occurrence of each ingredient gives us the unit
    seen: dict[int, str | None] = {}
    for di in dis:
        if di.ingredient_id not in seen:
            seen[di.ingredient_id] = di.unit

    results:      list[IngredientPriceResult] = []
    llm_count    = 0
    cached_count = 0
    api_count    = 0

    for ing_id, unit in seen.items():
        ingredient = db.query(Ingredient).filter(Ingredient.id == ing_id).first()
        if not ingredient:
            continue

        pd, origin = price_ingredient(db, ingredient, unit)

        if origin == "cached":
            cached_count += 1
        elif origin == "llm_estimate":
            llm_count += 1
        else:
            api_count += 1

        results.append(IngredientPriceResult(
            ingredient_id=ing_id,
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
        api_count=api_count,
        llm_count=llm_count,
        cached_count=cached_count,
    )

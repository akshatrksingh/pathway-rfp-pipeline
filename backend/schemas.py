from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel


# --- Restaurant ---

class RestaurantCreate(BaseModel):
    name: str
    address: str
    city: str
    state: str


class RestaurantOut(RestaurantCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Menu ---

class MenuCreate(BaseModel):
    restaurant_id: int
    name: Optional[str] = None
    raw_text: str
    source_url: Optional[str] = None


class MenuOut(MenuCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Ingredient ---

class IngredientOut(BaseModel):
    id: int
    name: str
    usda_fdc_id: Optional[int] = None
    usda_category: Optional[str] = None
    default_unit: Optional[str] = None

    model_config = {"from_attributes": True}


# --- DishIngredient ---

class DishIngredientBase(BaseModel):
    ingredient_id: int
    quantity: Optional[float] = None
    unit: Optional[str] = None
    notes: Optional[str] = None
    edit_status: str = "unchanged"


class DishIngredientOut(DishIngredientBase):
    id: int
    dish_id: int
    ingredient: IngredientOut

    model_config = {"from_attributes": True}


# --- Dish ---

class DishOut(BaseModel):
    id: int
    menu_id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    dish_ingredients: list[DishIngredientOut] = []

    model_config = {"from_attributes": True}


# --- PriceData ---

class PriceDataOut(BaseModel):
    id: int
    ingredient_id: int
    price_low: Optional[float] = None
    price_avg: Optional[float] = None
    price_high: Optional[float] = None
    unit: Optional[str] = None
    source: str
    confidence: str
    fetched_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


# --- PipelineRun ---

class PipelineRunCreate(BaseModel):
    restaurant_id: int
    menu_id: int


class PipelineRunOut(PipelineRunCreate):
    id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Distributor ---

class DistributorOut(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    specialty: Optional[str] = None
    area: Optional[str] = None

    model_config = {"from_attributes": True}


# --- RfpEmail ---

class RfpEmailOut(BaseModel):
    id: int
    pipeline_run_id: int
    distributor_id: int
    subject: str
    body: str
    status: str
    sent_at: Optional[datetime] = None
    distributor: DistributorOut

    model_config = {"from_attributes": True}


class RfpEmailUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None


class RfpEmailPromptEdit(BaseModel):
    instruction: str


# --- Quote ---

class QuoteOut(BaseModel):
    id: int
    rfp_email_id: int
    distributor_id: int
    ingredient_id: int
    quoted_price: Optional[float] = None
    unit: Optional[str] = None
    delivery_terms: Optional[str] = None
    valid_until: Optional[date] = None
    received_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Menu Parse (LLM output) ---

class ParsedIngredient(BaseModel):
    name: str
    quantity_per_serving: Optional[float] = None  # per individual serving of the dish
    unit: Optional[str] = None
    notes: Optional[str] = None


class ParsedDish(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    servings_per_day: Optional[int] = None  # LLM estimate for a mid-size restaurant
    ingredients: list[ParsedIngredient]


class ParsedMenu(BaseModel):
    dishes: list[ParsedDish]


# --- Pipeline SSE event ---

class PipelineEvent(BaseModel):
    step: str
    status: str  # running | complete | error
    message: str
    data: Optional[dict] = None

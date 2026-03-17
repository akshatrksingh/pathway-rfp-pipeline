from datetime import datetime
from sqlalchemy import (
    Integer, String, Text, Float, DateTime, Date,
    ForeignKey, UniqueConstraint, PrimaryKeyConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    city: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    menus: Mapped[list["Menu"]] = relationship("Menu", back_populates="restaurant")
    pipeline_runs: Mapped[list["PipelineRun"]] = relationship("PipelineRun", back_populates="restaurant")


class Menu(Base):
    __tablename__ = "menus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(Integer, ForeignKey("restaurants.id"), nullable=False)
    name: Mapped[str | None] = mapped_column(String)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    restaurant: Mapped["Restaurant"] = relationship("Restaurant", back_populates="menus")
    dishes: Mapped[list["Dish"]] = relationship("Dish", back_populates="menu")
    pipeline_runs: Mapped[list["PipelineRun"]] = relationship("PipelineRun", back_populates="menu")


class Dish(Base):
    __tablename__ = "dishes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    menu_id: Mapped[int] = mapped_column(Integer, ForeignKey("menus.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String)

    menu: Mapped["Menu"] = relationship("Menu", back_populates="dishes")
    dish_ingredients: Mapped[list["DishIngredient"]] = relationship("DishIngredient", back_populates="dish")


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    usda_fdc_id: Mapped[int | None] = mapped_column(Integer)
    usda_category: Mapped[str | None] = mapped_column(String)
    default_unit: Mapped[str | None] = mapped_column(String)

    dish_ingredients: Mapped[list["DishIngredient"]] = relationship("DishIngredient", back_populates="ingredient")
    price_data: Mapped[list["PriceData"]] = relationship("PriceData", back_populates="ingredient")
    distributor_ingredients: Mapped[list["DistributorIngredient"]] = relationship("DistributorIngredient", back_populates="ingredient")
    rfp_email_ingredients: Mapped[list["RfpEmailIngredient"]] = relationship("RfpEmailIngredient", back_populates="ingredient")
    quotes: Mapped[list["Quote"]] = relationship("Quote", back_populates="ingredient")


class DishIngredient(Base):
    __tablename__ = "dish_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dish_id: Mapped[int] = mapped_column(Integer, ForeignKey("dishes.id"), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(Integer, ForeignKey("ingredients.id"), nullable=False)
    quantity: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(Text)
    edit_status: Mapped[str] = mapped_column(String, default="unchanged")

    dish: Mapped["Dish"] = relationship("Dish", back_populates="dish_ingredients")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="dish_ingredients")


class PriceData(Base):
    __tablename__ = "price_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ingredient_id: Mapped[int] = mapped_column(Integer, ForeignKey("ingredients.id"), nullable=False)
    price_low: Mapped[float | None] = mapped_column(Float)
    price_avg: Mapped[float | None] = mapped_column(Float)
    price_high: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String)
    source: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[str] = mapped_column(String, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="price_data")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(Integer, ForeignKey("restaurants.id"), nullable=False)
    menu_id: Mapped[int] = mapped_column(Integer, ForeignKey("menus.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, default="started")
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    restaurant: Mapped["Restaurant"] = relationship("Restaurant", back_populates="pipeline_runs")
    menu: Mapped["Menu"] = relationship("Menu", back_populates="pipeline_runs")
    run_distributors: Mapped[list["RunDistributor"]] = relationship("RunDistributor", back_populates="pipeline_run")
    rfp_emails: Mapped[list["RfpEmail"]] = relationship("RfpEmail", back_populates="pipeline_run")


class Distributor(Base):
    __tablename__ = "distributors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String)
    address: Mapped[str | None] = mapped_column(String)
    website: Mapped[str | None] = mapped_column(String)
    specialty: Mapped[str | None] = mapped_column(String)
    area: Mapped[str | None] = mapped_column(String)

    run_distributors: Mapped[list["RunDistributor"]] = relationship("RunDistributor", back_populates="distributor")
    distributor_ingredients: Mapped[list["DistributorIngredient"]] = relationship("DistributorIngredient", back_populates="distributor")
    rfp_emails: Mapped[list["RfpEmail"]] = relationship("RfpEmail", back_populates="distributor")
    quotes: Mapped[list["Quote"]] = relationship("Quote", back_populates="distributor")


class RunDistributor(Base):
    __tablename__ = "run_distributors"

    pipeline_run_id: Mapped[int] = mapped_column(Integer, ForeignKey("pipeline_runs.id"), primary_key=True)
    distributor_id: Mapped[int] = mapped_column(Integer, ForeignKey("distributors.id"), primary_key=True)

    pipeline_run: Mapped["PipelineRun"] = relationship("PipelineRun", back_populates="run_distributors")
    distributor: Mapped["Distributor"] = relationship("Distributor", back_populates="run_distributors")


class DistributorIngredient(Base):
    __tablename__ = "distributor_ingredients"

    distributor_id: Mapped[int] = mapped_column(Integer, ForeignKey("distributors.id"), primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(Integer, ForeignKey("ingredients.id"), primary_key=True)

    distributor: Mapped["Distributor"] = relationship("Distributor", back_populates="distributor_ingredients")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="distributor_ingredients")


class RfpEmail(Base):
    __tablename__ = "rfp_emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_run_id: Mapped[int] = mapped_column(Integer, ForeignKey("pipeline_runs.id"), nullable=False)
    distributor_id: Mapped[int] = mapped_column(Integer, ForeignKey("distributors.id"), nullable=False)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="draft")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)

    pipeline_run: Mapped["PipelineRun"] = relationship("PipelineRun", back_populates="rfp_emails")
    distributor: Mapped["Distributor"] = relationship("Distributor", back_populates="rfp_emails")
    rfp_email_ingredients: Mapped[list["RfpEmailIngredient"]] = relationship("RfpEmailIngredient", back_populates="rfp_email")
    quotes: Mapped[list["Quote"]] = relationship("Quote", back_populates="rfp_email")


class RfpEmailIngredient(Base):
    __tablename__ = "rfp_email_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rfp_email_id: Mapped[int] = mapped_column(Integer, ForeignKey("rfp_emails.id"), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(Integer, ForeignKey("ingredients.id"), nullable=False)
    quantity_needed: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String)

    rfp_email: Mapped["RfpEmail"] = relationship("RfpEmail", back_populates="rfp_email_ingredients")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="rfp_email_ingredients")


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rfp_email_id: Mapped[int] = mapped_column(Integer, ForeignKey("rfp_emails.id"), nullable=False)
    distributor_id: Mapped[int] = mapped_column(Integer, ForeignKey("distributors.id"), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(Integer, ForeignKey("ingredients.id"), nullable=False)
    quoted_price: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String)
    delivery_terms: Mapped[str | None] = mapped_column(Text)
    valid_until: Mapped[datetime | None] = mapped_column(Date)
    received_at: Mapped[datetime | None] = mapped_column(DateTime)
    raw_email_text: Mapped[str | None] = mapped_column(Text)

    rfp_email: Mapped["RfpEmail"] = relationship("RfpEmail", back_populates="quotes")
    distributor: Mapped["Distributor"] = relationship("Distributor", back_populates="quotes")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="quotes")

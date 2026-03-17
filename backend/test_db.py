from database import Base, engine, SessionLocal
from models import Restaurant

# Create all tables
Base.metadata.create_all(engine)
print("✓ Tables created:", sorted(Base.metadata.tables.keys()))

# Insert a dummy restaurant
db = SessionLocal()
try:
    restaurant = Restaurant(
        name="The Golden Fork",
        address="123 Main St",
        city="Brooklyn",
        state="NY",
    )
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    print(f"✓ Inserted restaurant: id={restaurant.id}, name='{restaurant.name}', created_at={restaurant.created_at}")

    # Read it back
    fetched = db.query(Restaurant).filter(Restaurant.id == restaurant.id).first()
    print(f"✓ Fetched back:        id={fetched.id}, city={fetched.city}, state={fetched.state}")
finally:
    db.close()

print("\nAll checks passed.")

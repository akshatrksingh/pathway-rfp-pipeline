from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from routers import menus, pipeline

# Create all tables on startup
Base.metadata.create_all(engine)

app = FastAPI(title="RFP Pipeline API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(menus.router)
app.include_router(pipeline.router)

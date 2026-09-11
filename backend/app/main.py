from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.recommendations import router as recommendations_router
from app.api.routes.nfl import router as nfl_router
from app.api.routes.leagues import router as leagues_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Win-probability-first fantasy football lineup optimizer.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(nfl_router, prefix="/api")
app.include_router(leagues_router, prefix="/api")
app.include_router(recommendations_router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Fantasy Lineup Optimizer API", "docs": "/docs"}

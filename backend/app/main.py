import os
from pathlib import Path

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.recommendations import router as recommendations_router
from app.api.routes.nfl import router as nfl_router
from app.api.routes.leagues import router as leagues_router
from app.core.config import get_settings

from app.api.routes.news import router as news_router
from app.api.routes.cron import router as cron_router
from app.services.news import collect_daily
from app.services.report_collector import collect_reports


@asynccontextmanager
async def lifespan(app):
    tasks = [] if os.getenv("VERCEL") else [asyncio.create_task(collect_daily()), asyncio.create_task(collect_reports())]
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task


settings = get_settings()

app = FastAPI(
    lifespan=lifespan,
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

app.include_router(news_router, prefix="/api")
app.include_router(cron_router, prefix="/api")
app.include_router(health_router, prefix="/api")
app.include_router(nfl_router, prefix="/api")
app.include_router(leagues_router, prefix="/api")
app.include_router(recommendations_router, prefix="/api")


frontend_dist = Path(os.environ['FRONTEND_DIST']) if os.getenv('FRONTEND_DIST') else None


@app.get("/")
def root():
    if frontend_dist:
        return FileResponse(frontend_dist / 'index.html', headers={'Cache-Control': 'no-cache'})
    return {"message": "Fantasy Lineup Optimizer API", "docs": "/docs"}


if frontend_dist:
    # API routes take precedence. Serve only the built frontend directory.
    app.mount('/', StaticFiles(directory=frontend_dist, html=True), name='frontend')

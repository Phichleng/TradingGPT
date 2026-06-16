from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.config import settings
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    from app.db.base import Base
    from app.db.session import engine
    Base.metadata.create_all(bind=engine)

    from app.core.scheduler import scheduler, setup_scheduler
    markets = [m.strip() for m in settings.scheduler_markets.split(",") if m.strip()]
    timeframes = [t.strip() for t in settings.scheduler_timeframes.split(",") if t.strip()]
    setup_scheduler(markets, timeframes)
    scheduler.start()

    yield

    # --- shutdown ---
    scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.include_router(api_router)

    # Serve the dashboard from backend/static/ at /ui
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    static_dir = os.path.normpath(static_dir)
    if os.path.isdir(static_dir):
        app.mount("/ui", StaticFiles(directory=static_dir, html=True), name="static")

    return app


app = create_app()

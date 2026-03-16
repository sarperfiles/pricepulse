from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import auth, users, products, price_history, alert_rules, notifications

logger = logging.getLogger("pricepulse")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("PricePulse API is starting up")
    yield
    logger.info("PricePulse API is shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="PricePulse",
        version="0.1.0",
        lifespan=lifespan,
        redirect_slashes=True,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # register routers
    routers = [auth.router, users.router, products.router, price_history.router, alert_rules.router, notifications.router]
    for r in routers:
        app.include_router(r)

    @app.get("/api/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

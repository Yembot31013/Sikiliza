from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.providers.factory import is_configured, resolve_provider_name
from app.routers.stream import router as stream_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = get_settings()
    logger.info(
        "Sikiliza ready provider=%s mode=%s configured=%s",
        resolve_provider_name(settings),
        settings.mode,
        is_configured(settings),
    )
    try:
        yield
    finally:
        from app.providers.http import close_http_client

        await close_http_client()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(stream_router)

    @app.get("/health")
    async def health() -> dict:
        current = get_settings()
        provider = resolve_provider_name(current)
        return {
            "ok": True,
            "provider": provider,
            "mode": current.mode,
            "configured": is_configured(current),
        }

    return app


app = create_app()

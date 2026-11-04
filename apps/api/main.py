import logging
from contextlib import asynccontextmanager

from app.infrastructure.persistence.database import Base, engine
from app.presentation.assistant_router import router as assistant_router
from app.presentation.auth import router as auth_router
from app.presentation.categories_router import router as categories_router
from app.presentation.export_router import router as export_router
from app.presentation.ingestion_router import router as ingestion_router
from app.presentation.llm_router import router as llm_router
from app.presentation.notifications_router import router as notifications_router
from app.presentation.rules_router import router as rules_router
from app.presentation.telegram_router import router as telegram_router
from app.presentation.transactions_router import router as transactions_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cashbuffer")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is created on startup
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified.")
    except Exception as e:
        logger.error(f"Error initializing DB schema: {e}")

    # Start OAuth daemon
    import asyncio

    from app.application.oauth_daemon_service import oauth_refresh_daemon_loop

    daemon_task = asyncio.create_task(oauth_refresh_daemon_loop())
    yield

    daemon_task.cancel()
    try:
        await daemon_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="CashBuffer API",
    description="Autonomous, multi-tenant financial assistant backend.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 routers
api_v1_routers = [
    auth_router,
    transactions_router,
    categories_router,
    rules_router,
    ingestion_router,
    llm_router,
    assistant_router,
    notifications_router,
    telegram_router,
    export_router,
]

for r in api_v1_routers:
    app.include_router(r, prefix="/api/v1")
    # Also include at root prefix for convenience and backwards compatibility
    app.include_router(r)


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "service": "CashBuffer", "version": "1.0.0"}

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.assistant import router as assistant_router
from app.api.auth import router as auth_router
from app.api.categories import router as categories_router
from app.api.export import router as export_router
from app.api.ingestion import router as ingestion_router
from app.api.ingress import router as ingress_router
from app.api.llm import router as llm_router
from app.api.notifications import router as notifications_router
from app.api.rules import router as rules_router
from app.api.telegram import router as telegram_router
from app.api.transactions import router as transactions_router
from app.infrastructure.persistence.db_pool import close_db_pool, get_db_pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cashbuffer")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize native psycopg 3 connection pool
    try:
        pool = await get_db_pool()
        if pool is not None:
            logger.info("Native psycopg 3 database connection pool initialized.")
    except Exception as e:
        logger.warning(f"Database pool initialization skipped or failed: {e}")

    # Start OAuth refresh daemon in background if available
    import asyncio

    daemon_task = None
    try:
        from app.services.oauth_daemon import oauth_refresh_daemon_loop

        daemon_task = asyncio.create_task(oauth_refresh_daemon_loop())
    except Exception as e:
        logger.debug(f"OAuth daemon not started: {e}")

    yield

    if daemon_task:
        daemon_task.cancel()
        try:
            await daemon_task
        except asyncio.CancelledError:
            pass

    await close_db_pool()
    logger.info("Database connection pool closed.")

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
    ingress_router,
    transactions_router,
    categories_router,
    rules_router,
    ingestion_router,
    llm_router,
    assistant_router,
    telegram_router,
    notifications_router,
    export_router,
]

for router in api_v1_routers:
    app.include_router(router, prefix="/api/v1")

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "cashbuffer-api"}

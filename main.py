import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.assistant import router as assistant_router
from app.api.auth import router as auth_router
from app.api.categories import router as categories_router
from app.api.ingestion import router as ingestion_router
from app.api.llm import router as llm_router
from app.api.notifications import router as notifications_router
from app.api.rules import router as rules_router
from app.api.telegram import router as telegram_router
from app.api.transactions import router as transactions_router
from app.db.database import Base, engine
from app.services.oauth_daemon import start_oauth_refresh_daemon, stop_oauth_refresh_daemon

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
    logger.info("Starting oauth daemon")
    daemon_task = asyncio.create_task(start_oauth_refresh_daemon())
    yield
    await stop_oauth_refresh_daemon(daemon_task)


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
]

for r in api_v1_routers:
    app.include_router(r, prefix="/api/v1")
    # Also include at root prefix for convenience and backwards compatibility
    app.include_router(r)


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "service": "CashBuffer", "version": "1.0.0"}

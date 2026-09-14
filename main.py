from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.transactions import router as transactions_router
from app.api.ingestion import router as ingestion_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Cash Buffer API",
        description="Zero-friction Multi-tenant Financial Assistant Engine",
        version="1.0.0",
    )

    # Core routing
    app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
    app.include_router(transactions_router, prefix="/api", tags=["Transactions"])
    app.include_router(ingestion_router, prefix="/ingest", tags=["Ingestion"])

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "Cash Buffer API"}

    return app


app = create_app()

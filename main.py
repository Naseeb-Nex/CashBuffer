from fastapi import FastAPI
from app.api.auth import router as auth_router

def create_app() -> FastAPI:
    app = FastAPI(
        title="Cash Buffer API",
        description="Zero-friction Multi-tenant Financial Assistant Engine",
        version="1.0.0"
    )

    # Core routing
    app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "Cash Buffer API"}

    return app

app = create_app()

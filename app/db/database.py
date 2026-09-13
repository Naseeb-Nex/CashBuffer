from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# asyncpg handles ssl differently, we need to strip `sslmode=require&channel_binding=require`
# from the connection string and pass connect_args={"ssl": "require"} instead.
db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
db_url = db_url.split("?")[0] # Strip the ?sslmode query params

# Create the async engine for FastAPI + Neon DB
engine = create_async_engine(
    db_url, 
    echo=False,
    connect_args={"ssl": "require"}
)

# Session factory bound to engine
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    autoflush=False, 
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    """Dependency for injecting DB sessions into FastAPI routes."""
    async with AsyncSessionLocal() as session:
        yield session

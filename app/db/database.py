from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, StaticPool

from app.core.config import settings

db_url = settings.DATABASE_URL
connect_args = {}
if "postgresql" in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    db_url = db_url.split("?")[0]
    connect_args = {"ssl": "require"}
    engine = create_async_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,
        poolclass=NullPool,
        connect_args=connect_args,
    )
elif "sqlite" in db_url:
    connect_args = {"check_same_thread": False}
    engine = create_async_engine(
        db_url,
        echo=False,
        poolclass=StaticPool,
        connect_args=connect_args,
    )
else:
    engine = create_async_engine(
        db_url,
        echo=False,
    )

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db():
    """Dependency for injecting DB sessions into FastAPI routes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

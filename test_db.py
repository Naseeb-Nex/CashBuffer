import asyncio

from app.db.database import Base, engine
from app.db.models import *


async def init_db():
    print("starting tables create")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("created tables")


asyncio.run(init_db())

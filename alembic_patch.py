import os

with open("alembic/env.py", "r") as f:
    content = f.read()

# Make alembic aware of our models and config
import_statement = """
import sys
from os.path import abspath, dirname
sys.path.insert(0, dirname(dirname(abspath(__file__))))

from app.db.database import Base
from app.db.models import *  # strictly import models so they register
from app.core.config import settings

target_metadata = Base.metadata

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
"""

content = content.replace("target_metadata = None", import_statement)

with open("alembic/env.py", "w") as f:
    f.write(content)

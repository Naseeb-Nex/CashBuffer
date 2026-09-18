import re

with open("tests/test_stats_aggregation.py", "r") as f:
    content = f.read()

# Add imports for OAuthCredential and others
imports = """import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta, timezone

from app.core.crypto import encrypt_key
from app.db.models import OAuthCredential
"""
content = re.sub(r'import pytest\nfrom httpx import AsyncClient', imports, content)

# Change method signature to inject db_session
content = re.sub(r'async def test_stats_summary_aggregation\(client: AsyncClient, auth_headers_alice, unique_user_alice\):',
                 r'async def test_stats_summary_aggregation(client: AsyncClient, auth_headers_alice, unique_user_alice, db_session):', content)

# Insert the db seed logic before the first comment
seed_logic = """    # Seed an active OAuthCredential for the user
    now = datetime.now(timezone.utc)
    cred = OAuthCredential(
        user_id=unique_user_alice,
        source="gmail",
        encrypted_access_token=encrypt_key("fake_access"),
        encrypted_refresh_token=encrypt_key("fake_refresh"),
        expires_at=now + timedelta(hours=1),
        is_valid=True,
    )
    db_session.add(cred)
    await db_session.commit()

    # 1. Ingest transactions to simulate activity across "multiple accounts" dynamically handled"""
content = re.sub(r'    # 1. Ingest transactions to simulate activity across "multiple accounts" dynamically handled', seed_logic, content)

# Replace the assertion
content = content.replace('assert "linked_accounts_count" in data', 'assert data["linked_accounts_count"] == 1')

with open("tests/test_stats_aggregation.py", "w") as f:
    f.write(content)

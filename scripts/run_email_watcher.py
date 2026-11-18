import asyncio

from app.email.watcher import (
    get_email_body,
    get_gmail_service,
    mark_as_read,
    search_recent_bank_alerts,
)
from app.infrastructure.persistence.db_pool import close_db_pool, get_db_pool
from app.infrastructure.persistence.native_repository import NativeRepository
from app.services.transactions import ingest_from_raw_email
from scripts.gmail_auth import authenticate_gmail


async def run_email_ingestion_loop(user_id: str):
    """
    Pulls the last 2 months of Axis bank alerts and inserts them.
    Note: For production scheduled ingestion, prefer apps/ingress microservice daemon.
    """
    creds = authenticate_gmail()
    if not creds:
        print("Cannot start email ingestion: Missing token.json authorization.")
        return

    service = get_gmail_service(creds)
    print("Email Service Started. Checking for Axis Bank history...")

    # Grab the last 2 months of Axis bank alerts
    messages = search_recent_bank_alerts(service, sender_email="alerts@axis.bank.in", newer_than="2m")
    print(f"Found {len(messages)} matching Axis Bank alerts.")

    success_count = 0
    fail_count = 0

    pool = await get_db_pool()
    if not pool:
        print("Cannot connect to database pool.")
        return

    repo = NativeRepository(pool)
    try:
        for msg in messages:
            msg_id = msg["id"]
            # Fetch the actual email text
            body = get_email_body(service, msg_id)

            if body:
                tx = await ingest_from_raw_email(repo, user_id, body)
                if tx:
                    print(f"✅ Saved Tx: {tx.record_date} | {tx.amount} {tx.currency} | {tx.vendor_raw}")
                    success_count += 1
                    mark_as_read(service, msg_id)
                else:
                    fail_count += 1
                    print(f"⚠️ Could not extract money pattern or quarantined: {msg_id}")
            else:
                fail_count += 1

        print("\n--- Ingestion Complete ---")
        print(f"Valid Saves: {success_count} | Parse Fails: {fail_count}")
    finally:
        await close_db_pool()


if __name__ == "__main__":
    TEST_USER_ID = "kinde_test_123"
    asyncio.run(run_email_ingestion_loop(TEST_USER_ID))

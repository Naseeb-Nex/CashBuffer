import asyncio

from app.db.database import AsyncSessionLocal
from app.email.parser import AxisBankParser
from app.email.watcher import (
    get_email_body,
    get_gmail_service,
    mark_as_read,
    search_recent_bank_alerts,
)
from app.services.transactions import create_transaction_from_parsed
from scripts.gmail_auth import authenticate_gmail


async def run_email_ingestion_loop(user_id: str):
    """
    Pulls the last 2 months of Axis bank alerts and inserts them.
    """
    creds = authenticate_gmail()
    if not creds:
        print("Cannot start email ingestion: Missing token.json authorization.")
        return

    service = get_gmail_service(creds)
    print("Email Service Started. Checking for Axis Bank history...")

    # Grab the last 2 months of Axis bank alerts
    messages = search_recent_bank_alerts(
        service, sender_email="alerts@axis.bank.in", newer_than="2m"
    )
    print(f"Found {len(messages)} matching Axis Bank alerts.")

    success_count = 0
    fail_count = 0

    async with AsyncSessionLocal() as db:
        for msg in messages:
            msg_id = msg["id"]
            # Fetch the actual email text
            body = get_email_body(service, msg_id)

            if body:
                parsed_data = AxisBankParser.parse(body)
                if parsed_data:
                    # Save into postgres
                    tx = await create_transaction_from_parsed(db, user_id, parsed_data)
                    print(
                        f"✅ Saved Tx: {tx.record_date} | {tx.amount} {tx.currency} | {tx.vendor_raw}"
                    )
                    success_count += 1

                    # Mark as read so we don't treat it as unseen strictly
                    mark_as_read(service, msg_id)
                else:
                    fail_count += 1
                    print(f"⚠️ Could not extract money pattern from email: {msg_id}")
            else:
                fail_count += 1
    print("\n--- Ingestion Complete ---")
    print(f"Valid Saves: {success_count} | Parse Fails: {fail_count}")


if __name__ == "__main__":
    TEST_USER_ID = "kinde_test_123"
    asyncio.run(run_email_ingestion_loop(TEST_USER_ID))

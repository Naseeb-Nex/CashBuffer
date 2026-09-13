from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Transaction, TransactionStatus

async def create_transaction_from_parsed(db: AsyncSession, user_id: str, parsed_data: dict) -> Transaction:
    """
    Inserts a newly parsed bank alert into the multi-tenant ledger.
    Sets status to PARSED awaiting the LangGraph Agent loop.
    """
    new_tx = Transaction(
        user_id=user_id,
        amount=parsed_data["amount"],
        currency=parsed_data.get("currency", "INR"),
        is_inflow=parsed_data["is_inflow"],
        record_date=parsed_data["record_date"],
        vendor_raw=parsed_data["vendor_raw"],
        status=TransactionStatus.PARSED
    )
    db.add(new_tx)
    await db.commit()
    await db.refresh(new_tx)
    return new_tx

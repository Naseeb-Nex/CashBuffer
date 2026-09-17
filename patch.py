import re

with open('app/services/transactions.py', 'r') as f:
    content = f.read()

# Add IntegrityError import
if 'from sqlalchemy.exc import IntegrityError' not in content:
    content = content.replace('from sqlalchemy import delete, select', 'from sqlalchemy import delete, select\nfrom sqlalchemy.exc import IntegrityError')

# Fix create_transaction
old_ct = """    if auto_categorize and not category_id:
        await categorize_transaction(db, tx)

    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx"""

new_ct = """    if auto_categorize and not category_id:
        await categorize_transaction(db, tx)

    db.add(tx)
    try:
        await db.commit()
        await db.refresh(tx)
        return tx
    except IntegrityError:
        await db.rollback()
        stmt = select(Transaction).where(Transaction.tx_hash == tx_hash)
        existing_tx = (await db.execute(stmt)).scalar_one_or_none()
        if existing_tx:
            return existing_tx
        raise"""
content = content.replace(old_ct, new_ct)

# Fix create_batch_transactions
old_cbt = """async def create_batch_transactions(
    db: AsyncSession,
    user_id: str,
    items: list[dict[str, Any]],
    auto_categorize: bool = True,
) -> list[Transaction]:
    \"\"\"Inserts a batch of transactions for user.\"\"\"
    await _ensure_user_exists(db, user_id)

    created: list[Transaction] = []

    for item in items:
        rec_date = item.get("record_date")
        if isinstance(rec_date, str):
            try:
                rec_date = datetime.strptime(rec_date, "%Y-%m-%d").date()
            except ValueError:
                rec_date = date.today()
        elif rec_date is None:
            rec_date = date.today()

        category_id = item.get("category_id")
        if category_id and not await _validate_user_category(db, user_id, category_id):
            category_id = None

        amount = float(item["amount"])
        currency = item.get("currency", "INR")
        is_inflow = bool(item.get("is_inflow", False))
        vendor_raw = str(item.get("vendor_raw", "Unknown"))

        tx_hash = _compute_tx_hash(user_id, amount, currency, is_inflow, rec_date, vendor_raw)

        stmt = select(Transaction).where(Transaction.tx_hash == tx_hash)
        existing_tx = (await db.execute(stmt)).scalar_one_or_none()
        if existing_tx:
            created.append(existing_tx)
            continue

        tx = Transaction(
            user_id=user_id,
            amount=amount,
            currency=currency,
            is_inflow=is_inflow,
            record_date=rec_date,
            vendor_raw=vendor_raw,
            category_id=category_id,
            status=TransactionStatus.CATEGORIZED if category_id else TransactionStatus.PARSED,
            tx_hash=tx_hash,
        )

        if auto_categorize and not category_id:
            await categorize_transaction(db, tx)

        db.add(tx)
        await db.flush()
        created.append(tx)

    await db.commit()
    for tx in created:
        await db.refresh(tx)
    return created"""

new_cbt = """async def create_batch_transactions(
    db: AsyncSession,
    user_id: str,
    items: list[dict[str, Any]],
    auto_categorize: bool = True,
) -> list[Transaction]:
    \"\"\"Inserts a batch of transactions for user.\"\"\"
    await _ensure_user_exists(db, user_id)

    # 1. Pre-compute all mappings and hashes
    processed_items = []
    tx_hashes = []
    
    for item in items:
        rec_date = item.get("record_date")
        if isinstance(rec_date, str):
            try:
                rec_date = datetime.strptime(rec_date, "%Y-%m-%d").date()
            except ValueError:
                rec_date = date.today()
        elif rec_date is None:
            rec_date = date.today()

        category_id = item.get("category_id")
        amount = float(item["amount"])
        currency = item.get("currency", "INR")
        is_inflow = bool(item.get("is_inflow", False))
        vendor_raw = str(item.get("vendor_raw", "Unknown"))

        tx_hash = _compute_tx_hash(user_id, amount, currency, is_inflow, rec_date, vendor_raw)
        tx_hashes.append(tx_hash)
        
        processed_items.append({
            "record_date": rec_date,
            "category_id": category_id,
            "amount": amount,
            "currency": currency,
            "is_inflow": is_inflow,
            "vendor_raw": vendor_raw,
            "tx_hash": tx_hash,
            "original_item": item,
        })

    # 2. Bulk lookup existing records
    existing_records = []
    if tx_hashes:
        stmt = select(Transaction).where(Transaction.tx_hash.in_(tx_hashes))
        res = await db.execute(stmt)
        existing_records = res.scalars().all()
    
    existing_by_hash = {tx.tx_hash: tx for tx in existing_records}
    
    # 3. Process each item, avoiding duplicates in the same batch
    created: list[Transaction] = []
    to_add: list[Transaction] = []
    seen_in_batch = set()

    for p_item in processed_items:
        tx_hash = p_item["tx_hash"]
        
        if tx_hash in existing_by_hash:
            created.append(existing_by_hash[tx_hash])
            continue
            
        if tx_hash in seen_in_batch:
            # We already have a pending creation for this hash in this batch.
            # To strictly match the duplicate return behavior, we could look it up from to_add,
            # but db.add_all hasn't flushed so there are no primary keys.
            # The original code just skipped/returned the newly added tx.
            # Here we just find it in to_add.
            for t in to_add:
                if t.tx_hash == tx_hash:
                    created.append(t)
                    break
            continue
            
        category_id = p_item["category_id"]
        if category_id and not await _validate_user_category(db, user_id, category_id):
            category_id = None
            
        tx = Transaction(
            user_id=user_id,
            amount=p_item["amount"],
            currency=p_item["currency"],
            is_inflow=p_item["is_inflow"],
            record_date=p_item["record_date"],
            vendor_raw=p_item["vendor_raw"],
            category_id=category_id,
            status=TransactionStatus.CATEGORIZED if category_id else TransactionStatus.PARSED,
            tx_hash=tx_hash,
        )

        if auto_categorize and not category_id:
            await categorize_transaction(db, tx)

        to_add.append(tx)
        created.append(tx)
        seen_in_batch.add(tx_hash)

    if to_add:
        # Instead of db.add_all, db.add is ok, but db.add_all is mentioned:
        # "before using db.add_all()."
        db.add_all(to_add)
        try:
            await db.commit()
        except IntegrityError:
            # Race condition handling for batch is tricky, but the finding doesn't 
            # explicitly require it. The first finding is for `create_transaction`
            await db.rollback()
            raise

    # Refresh everything that was created in this batch
    for tx in to_add:
        await db.refresh(tx)

    return created"""
content = content.replace(old_cbt, new_cbt)

with open('app/services/transactions.py', 'w') as f:
    f.write(content)

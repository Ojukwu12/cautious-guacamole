import hashlib
import json
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import TransactionLedger

# The fallback hash used for the very first transaction in the system
GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

async def get_previous_hash(db_session: AsyncSession) -> str:
    """
    Fetches the 'current_hash' of the most recently inserted transaction.
    If the ledger is completely empty, it returns the Genesis Hash.
    """
    query = select(TransactionLedger.current_hash).order_by(TransactionLedger.created_at.desc()).limit(1)
    result = await db_session.execute(query)
    latest_hash = result.scalar_one_or_none()
    
    if latest_hash is None:
        return GENESIS_HASH
        
    return latest_hash

def generate_tx_hash(transaction_data: dict, previous_hash: str) -> str:
    """
    Creates an immutable SHA-256 signature by combining the new payload
    with the cryptographic signature of the preceding block.
    """
    # 1. Ensure the dictionary is sorted by keys so the JSON string is always identical
    block_string = json.dumps(transaction_data, sort_keys=True)
    
    # 2. Append the previous hash to the new payload
    chained_string = f"{block_string}{previous_hash}"
    
    # 3. Generate and return the SHA-256 hex digest
    return hashlib.sha256(chained_string.encode('utf-8')).hexdigest()
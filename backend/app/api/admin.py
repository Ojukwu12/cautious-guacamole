from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, UUID4
from sqlalchemy import cast, delete, func, or_, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import get_current_admin
from app.core.config import settings
from app.db.connection import get_db
from app.db.models import CheckoutSession, TransactionLedger, User, Withdrawal
from app.services.ledger_hash import GENESIS_HASH
from app.services.conversion import fetch_live_usd_rates

router = APIRouter(prefix="/api/admin", tags=["Administration"])

class RolePayload(BaseModel):
    role: str

def transaction_result(transaction):
    return {
        "id": str(transaction.tx_id),
        "merchant_id": str(transaction.merchant_id),
        "currency": transaction.currency,
        "payment_currency": transaction.payment_currency,
        "payment_amount": transaction.payment_amount,
        "payment_method": transaction.payment_method,
        "status": transaction.status,
        "settlement_value": transaction.settlement_value,
        "platform_fee_percentage": transaction.platform_fee_percentage,
        "platform_fee_value": transaction.platform_fee_value,
        "customer_total": transaction.customer_total,
        "current_hash": transaction.current_hash,
        "previous_hash": transaction.previous_hash,
        "created_at": transaction.created_at,
    }

@router.get("/overview")
async def admin_overview(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    merchant_count = await db.scalar(select(func.count(User.id)).where(User.role == "merchant"))
    session_count = await db.scalar(select(func.count(CheckoutSession.id)))
    transaction_count = await db.scalar(select(func.count(TransactionLedger.tx_id)))
    withdrawal_count = await db.scalar(select(func.count(Withdrawal.id)))
    volume_result = await db.execute(
        select(TransactionLedger.currency, func.sum(TransactionLedger.settlement_value))
        .group_by(TransactionLedger.currency)
        .order_by(TransactionLedger.currency.asc())
    )
    live_rates = await fetch_live_usd_rates()
    recent_merchants = await db.execute(
        select(User).where(User.role == "merchant").order_by(User.created_at.desc()).limit(10)
    )
    recent_transactions = await db.execute(
        select(TransactionLedger).order_by(TransactionLedger.created_at.desc()).limit(10)
    )
    recent_withdrawals = await db.execute(
        select(Withdrawal).order_by(Withdrawal.created_at.desc()).limit(10)
    )
    ledger_hashes = await db.execute(
        select(TransactionLedger.current_hash, TransactionLedger.previous_hash).order_by(TransactionLedger.created_at.asc())
    )
    hash_rows = ledger_hashes.all()
    hashes_valid = all(
        isinstance(current_hash, str)
        and len(current_hash) == 64
        and isinstance(previous_hash, str)
        and len(previous_hash) == 64
        for current_hash, previous_hash in hash_rows
    )
    chain_starts_at_genesis = not hash_rows or hash_rows[0][1] == GENESIS_HASH
    chain_links_valid = all(
        hash_rows[index][1] == hash_rows[index - 1][0]
        for index in range(1, len(hash_rows))
    )
    return {
        "admin_email": admin.email,
        "metrics": {
            "merchants": merchant_count or 0,
            "checkout_sessions": session_count or 0,
            "transactions": transaction_count or 0,
            "withdrawals": withdrawal_count or 0,
        },
        "transaction_volume": [
            {"currency": currency, "amount": float(amount or 0)}
            for currency, amount in volume_result.all()
        ],
        "live_rates": [
            {"currency": currency, "per_usd": rate}
            for currency, rate in sorted((live_rates or {}).items())
            if currency != "USD"
        ],
        "merchants": [
            {"id": str(user.id), "email": user.email, "settlement_asset": user.settlement_asset, "created_at": user.created_at}
            for user in recent_merchants.scalars().all()
        ],
        "transactions": [
            transaction_result(transaction)
            for transaction in recent_transactions.scalars().all()
        ],
        "withdrawals": [
            {"id": str(withdrawal.id), "merchant_id": str(withdrawal.merchant_id), "asset": withdrawal.asset, "amount": withdrawal.amount, "status": withdrawal.status, "created_at": withdrawal.created_at}
            for withdrawal in recent_withdrawals.scalars().all()
        ],
        "system_status": {
            "conversion": {
                "active": True,
                "real_time": settings.LIVE_RATES_ENABLED,
                "mode": "live_provider" if settings.LIVE_RATES_ENABLED else "disabled",
                "message": "Conversion is active using the configured live rate provider."
                if settings.LIVE_RATES_ENABLED
                else "Live conversion is disabled.",
            },
            "ledger_hashing": {
                "active": hashes_valid and chain_starts_at_genesis and chain_links_valid,
                "records_checked": len(hash_rows),
                "chain_starts_at_genesis": chain_starts_at_genesis,
                "chain_links_valid": chain_links_valid,
                "message": "SHA-256 chained hash links are structurally valid."
                if hashes_valid and chain_starts_at_genesis and chain_links_valid
                else "Ledger hash verification needs attention.",
            },
        },
    }

@router.delete("/merchants/{merchant_id}")
async def delete_merchant(merchant_id: str, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.id == merchant_id, User.role == "merchant")
    )
    merchant = result.scalar_one_or_none()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant account not found.")

    transaction_count = await db.scalar(
        select(func.count(TransactionLedger.tx_id)).where(TransactionLedger.merchant_id == merchant.id)
    )
    if transaction_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This merchant has ledger transactions and cannot be deleted without breaking the immutable audit history.",
        )

    await db.execute(delete(CheckoutSession).where(CheckoutSession.merchant_id == merchant.id))
    await db.execute(delete(Withdrawal).where(Withdrawal.merchant_id == merchant.id))
    await db.delete(merchant)
    await db.commit()
    return {"status": "success", "message": "Merchant account deleted.", "merchant_id": merchant_id}

@router.get("/users")
async def list_users(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return {"status": "success", "data": [{"id": str(user.id), "email": user.email, "role": user.role, "created_at": user.created_at} for user in result.scalars().all()]}

@router.patch("/users/{user_id}/role")
async def update_user_role(user_id: UUID4, payload: RolePayload, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    if payload.role not in {"admin", "merchant"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role must be admin or merchant.")
    if str(admin.id) == str(user_id) and payload.role != "admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot demote your own administrator account.")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")
    if str(user.role) == "admin" and payload.role == "merchant":
        admin_count = await db.scalar(select(func.count(User.id)).where(User.role == "admin"))
        if (admin_count or 0) <= 1:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The platform must retain at least one administrator.")
    setattr(user, "role", payload.role)
    await db.commit()
    return {"status": "success", "user_id": str(user.id), "role": user.role}

@router.get("/transactions/search")
async def search_transactions(query: str, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    pattern = f"%{query.strip()}%"
    result = await db.execute(
        select(TransactionLedger)
        .where(or_(cast(TransactionLedger.tx_id, String).ilike(pattern), TransactionLedger.current_hash.ilike(pattern)))
        .order_by(TransactionLedger.created_at.desc())
        .limit(50)
    )
    return {"status": "success", "data": [transaction_result(transaction) for transaction in result.scalars().all()]}
from fastapi import APIRouter, Depends
from sqlalchemy import cast, func, or_, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import get_current_admin
from app.db.connection import get_db
from app.db.models import CheckoutSession, TransactionLedger, User, Withdrawal

router = APIRouter(prefix="/api/admin", tags=["Administration"])

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
    recent_merchants = await db.execute(
        select(User).where(User.role == "merchant").order_by(User.created_at.desc()).limit(10)
    )
    recent_transactions = await db.execute(
        select(TransactionLedger).order_by(TransactionLedger.created_at.desc()).limit(10)
    )
    recent_withdrawals = await db.execute(
        select(Withdrawal).order_by(Withdrawal.created_at.desc()).limit(10)
    )
    return {
        "admin_email": admin.email,
        "metrics": {
            "merchants": merchant_count or 0,
            "checkout_sessions": session_count or 0,
            "transactions": transaction_count or 0,
            "withdrawals": withdrawal_count or 0,
        },
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
    }

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
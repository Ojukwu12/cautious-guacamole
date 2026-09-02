from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, UUID4, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import get_current_user
from app.db.connection import get_db
from app.db.models import CheckoutSession, TransactionLedger, User
from app.services.conversion import get_secured_exchange_rate
from app.services.ledger_hash import get_previous_hash, generate_tx_hash
from app.exceptions.custom_exceptions import PaymentProcessingException, InvalidCurrencyException
from app.services.webhook_queue import enqueue_webhook_notification

router = APIRouter(prefix="/api/checkout", tags=["Checkout Gateway"])

class SessionPayload(BaseModel):
    fiat_amount: float = Field(gt=0)
    fiat_currency: str = Field(min_length=3, max_length=3)
    settlement_asset: str = Field(min_length=2, max_length=20)

def session_response(session: CheckoutSession) -> dict:
    return {
        "session_id": str(session.id),
        "merchant_id": str(session.merchant_id),
        "fiat_amount": session.fiat_amount,
        "fiat_currency": session.fiat_currency,
        "settlement_asset": session.settlement_asset,
        "settlement_value": round(session.fiat_amount * session.exchange_rate, 8),
        "exchange_rate": session.exchange_rate,
        "quote_id": session.quote_id,
        "status": session.status,
        "expires_at": session.expires_at,
        "checkout_url": f"/pay/{session.id}",
    }

@router.post("/session", status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionPayload, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pair = f"{payload.fiat_currency.upper()}_{payload.settlement_asset.upper()}"
    rate_data = get_secured_exchange_rate(pair)
    if not rate_data or "rate" not in rate_data:
        raise InvalidCurrencyException(pair)
    session = CheckoutSession(
        merchant_id=user.id,
        fiat_amount=payload.fiat_amount,
        fiat_currency=payload.fiat_currency.upper(),
        settlement_asset=payload.settlement_asset.upper(),
        exchange_rate=rate_data["rate"],
        quote_id=rate_data["quote_id"],
        expires_at=datetime.utcnow() + timedelta(minutes=15),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session_response(session)

@router.get("/session/{session_id}")
async def get_session(session_id: UUID4, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CheckoutSession).where(CheckoutSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise PaymentProcessingException("Checkout session not found.")
    if session.status == "open" and session.expires_at < datetime.utcnow():
        session.status = "expired"
        await db.commit()
    return session_response(session)

@router.post("/session/{session_id}/pay", status_code=status.HTTP_201_CREATED)
async def pay_session(session_id: UUID4, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CheckoutSession).where(CheckoutSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session or session.status != "open" or session.expires_at < datetime.utcnow():
        raise PaymentProcessingException("This checkout session is unavailable or expired.")
    transaction_data = {
        "merchant_id": str(session.merchant_id),
        "fiat_amount": session.fiat_amount,
        "currency": f"{session.fiat_currency}_{session.settlement_asset}",
        "settlement_value": round(session.fiat_amount * session.exchange_rate, 8),
        "quote_id": session.quote_id,
    }
    previous_hash = await get_previous_hash(db)
    current_hash = generate_tx_hash(transaction_data, previous_hash)
    transaction = TransactionLedger(
        merchant_id=session.merchant_id,
        fiat_amount=session.fiat_amount,
        currency=transaction_data["currency"],
        settlement_value=transaction_data["settlement_value"],
        current_hash=current_hash,
        previous_hash=previous_hash,
    )
    session.status = "paid"
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)
    merchant_result = await db.execute(select(User).where(User.id == session.merchant_id))
    merchant = merchant_result.scalar_one()
    enqueue_webhook_notification(
        str(transaction.tx_id), str(session.merchant_id), transaction.settlement_value,
        "success", merchant.webhook_secret, merchant.webhook_url,
    )
    return {
        "status": "success",
        "transaction_id": str(transaction.tx_id),
        "settlement_value": transaction.settlement_value,
        "hash_signature": current_hash,
    }

@router.get("/history")
async def get_transaction_history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TransactionLedger)
        .where(TransactionLedger.merchant_id == user.id)
        .order_by(TransactionLedger.created_at.desc())
    )
    return {"status": "success", "data": result.scalars().all()}

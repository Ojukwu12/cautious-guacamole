from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, UUID4, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import get_current_user
from app.db.connection import get_db
from app.db.models import CheckoutSession, TransactionLedger, User, Withdrawal
from app.services.conversion import apply_platform_fee, get_secured_exchange_rate, get_customer_quote, SUPPORTED_PAYMENT_CURRENCIES
from app.services.ledger_hash import get_previous_hash, generate_tx_hash
from app.exceptions.custom_exceptions import PaymentProcessingException, InvalidCurrencyException, RateProviderException
from app.services.webhook_queue import enqueue_webhook_notification

router = APIRouter(prefix="/api/checkout", tags=["Checkout Gateway"])

class SessionPayload(BaseModel):
    fiat_amount: float = Field(gt=0)
    fiat_currency: str = Field(default="NGN", min_length=3, max_length=3)
    settlement_asset: str | None = Field(default=None, min_length=2, max_length=20)

class PaymentPayload(BaseModel):
    payment_method: str
    payment_currency: str = Field(min_length=3, max_length=10)
    simulation_outcome: str = Field(default="success", pattern="^(success|failure)$")
    card_brand: str | None = Field(default=None, pattern="^(visa|mastercard)$")

class WithdrawalPayload(BaseModel):
    amount: float = Field(gt=0)
    destination: str = Field(min_length=4, max_length=120)

def payment_instructions(currency: str, method: str) -> dict:
    country = {"NGN": "Nigeria", "USD": "United States", "GBP": "United Kingdom", "EUR": "European Union"}.get(currency, "your region")
    if method == "crypto":
        asset = "BTC" if currency != "NGN" else "USDT"
        return {"kind": "crypto", "asset": asset, "address": "0xVGMOCK" + currency + "7f82a19c4d", "network": "Prototype testnet"}
    if method == "bank_transfer":
        return {"kind": "bank", "country": country, "bank_name": "Verve Gate Demo Bank", "account_name": "Verve Gate Test Collection", "account_number": {"NGN": "0123456789", "USD": "021000021", "GBP": "404784001", "EUR": "VGDEMO123456"}.get(currency, "0000000000"), "reference": "VG-TEST-" + currency}
    if method == "bank_app":
        return {"kind": "bank_app", "provider": {"NGN": "DemoPay NG", "USD": "Demo ACH", "GBP": "Demo Faster Payments", "EUR": "Demo SEPA"}.get(currency, "Verve Demo App"), "instruction": "Open the demo banking app and approve this test request."}
    return {"kind": "card", "test_key": "pk_test_verve_gate_demo", "instruction": "Use any test card number; no real charge is made."}

def session_response(session: CheckoutSession) -> dict:
    return {
        "session_id": str(session.id),
        "merchant_id": str(session.merchant_id),
        "fiat_amount": session.fiat_amount,
        "fiat_currency": session.fiat_currency,
        "settlement_asset": session.settlement_asset,
        "settlement_value": round(session.fiat_amount * session.exchange_rate, 8),
        "platform_fee_percentage": session.platform_fee_percentage,
        "platform_fee_value": session.platform_fee_value,
        "customer_total": session.customer_total,
        "exchange_rate": session.exchange_rate,
        "quote_id": session.quote_id,
        "payment_options": session.payment_options,
        "supported_payment_currencies": SUPPORTED_PAYMENT_CURRENCIES,
        "status": session.status,
        "expires_at": session.expires_at,
        "checkout_url": f"/pay/{session.id}",
    }

def public_session_response(session: CheckoutSession) -> dict:
    response = session_response(session)
    response.pop("merchant_id", None)
    response.pop("settlement_asset", None)
    response.pop("settlement_value", None)
    return response

@router.post("/session", status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionPayload, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    settlement_asset = user.settlement_asset.upper()
    fee = apply_platform_fee(payload.fiat_amount)
    pair = f"{payload.fiat_currency.upper()}_{settlement_asset}"
    rate_data = await get_secured_exchange_rate(pair, spread_percentage=0)
    if not rate_data or "rate" not in rate_data:
        raise RateProviderException()
    session = CheckoutSession(
        merchant_id=user.id,
        fiat_amount=payload.fiat_amount,
        fiat_currency=payload.fiat_currency.upper(),
        settlement_asset=settlement_asset,
        exchange_rate=rate_data["rate"],
        platform_fee_percentage=fee["platform_fee_percentage"],
        platform_fee_value=fee["platform_fee_value"],
        customer_total=fee["customer_total"],
        quote_id=rate_data["quote_id"],
        expires_at=datetime.utcnow() + timedelta(minutes=15),
        payment_options=user.payment_options or ["card", "bank_transfer", "bank_app", "crypto"],
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return public_session_response(session)

@router.get("/session/{session_id}")
async def get_session(session_id: UUID4, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CheckoutSession).where(CheckoutSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise PaymentProcessingException("Checkout session not found.")
    if session.status == "open" and session.expires_at < datetime.utcnow():
        session.status = "expired"
        await db.commit()
    return public_session_response(session)

@router.post("/session/{session_id}/cancel")
async def cancel_session(session_id: UUID4, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CheckoutSession).where(CheckoutSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session or session.status != "open":
        raise PaymentProcessingException("This checkout session cannot be cancelled.")
    session.status = "cancelled"
    await db.commit()
    return {"status": "cancelled", "message": "Checkout session cancelled."}

@router.post("/session/{session_id}/pay", status_code=status.HTTP_201_CREATED)
async def pay_session(session_id: UUID4, payload: PaymentPayload, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CheckoutSession).where(CheckoutSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session or session.status != "open" or session.expires_at < datetime.utcnow() or payload.payment_method not in session.payment_options:
        raise PaymentProcessingException("This checkout session is unavailable or expired.")
    if payload.payment_method == "card" and payload.card_brand not in {"visa", "mastercard"}:
        raise PaymentProcessingException("Select a Visa or Mastercard test card.")
    customer_quote = await get_customer_quote(session.fiat_amount, session.fiat_currency, payload.payment_currency)
    if not customer_quote:
        raise RateProviderException()
    if payload.simulation_outcome == "failure":
        return {
            "status": "failed",
            "message": "This is a simulated payment failure. No funds were moved.",
            "payment_currency": customer_quote["payment_currency"],
            "payment_amount": customer_quote["payment_amount"],
            "payment_method": payload.payment_method,
        }
    transaction_data = {
        "merchant_id": str(session.merchant_id),
        "fiat_amount": session.fiat_amount,
        "currency": f"{session.fiat_currency}_{session.settlement_asset}",
        "settlement_value": round(session.fiat_amount * session.exchange_rate, 8),
        "platform_fee_percentage": session.platform_fee_percentage,
        "platform_fee_value": session.platform_fee_value,
        "customer_total": session.customer_total,
        "quote_id": session.quote_id,
    }
    previous_hash = await get_previous_hash(db)
    current_hash = generate_tx_hash(transaction_data, previous_hash)
    transaction = TransactionLedger(
        merchant_id=session.merchant_id,
        fiat_amount=session.fiat_amount,
        currency=transaction_data["currency"],
        settlement_value=transaction_data["settlement_value"],
        platform_fee_percentage=session.platform_fee_percentage,
        platform_fee_value=session.platform_fee_value,
        customer_total=session.customer_total,
        payment_currency=customer_quote["payment_currency"],
        payment_amount=customer_quote["payment_amount"],
        payment_method=payload.payment_method,
        status="completed",
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
        "platform_fee_percentage": transaction.platform_fee_percentage,
        "platform_fee_value": transaction.platform_fee_value,
        "customer_total": transaction.customer_total,
        "hash_signature": current_hash,
        "payment_method": payload.payment_method,
        "payment_currency": customer_quote["payment_currency"],
        "payment_amount": customer_quote["payment_amount"],
    }

@router.get("/history")
async def get_transaction_history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TransactionLedger)
        .where(TransactionLedger.merchant_id == user.id)
        .order_by(TransactionLedger.created_at.desc())
    )
    return {"status": "success", "data": result.scalars().all()}

@router.get("/session/{session_id}/quote/{payment_currency}")
async def get_customer_payment_quote(session_id: UUID4, payment_currency: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CheckoutSession).where(CheckoutSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise PaymentProcessingException("Checkout session not found.")
    quote = await get_customer_quote(session.fiat_amount, session.fiat_currency, payment_currency)
    if not quote:
        raise RateProviderException()
    return {**quote, "expires_at": session.expires_at}

@router.get("/session/{session_id}/payment-instructions/{method}")
async def get_payment_instructions(session_id: UUID4, method: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CheckoutSession).where(CheckoutSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session or method not in session.payment_options:
        raise PaymentProcessingException("Payment method is unavailable for this session.")
    return payment_instructions(session.fiat_currency, method)

@router.post("/withdrawals", status_code=status.HTTP_201_CREATED)
async def create_withdrawal(payload: WithdrawalPayload, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    withdrawal = Withdrawal(merchant_id=user.id, asset=user.settlement_asset, amount=payload.amount, destination=payload.destination)
    db.add(withdrawal)
    await db.commit()
    await db.refresh(withdrawal)
    return {"status": "success", "message": "Mock withdrawal queued for review.", "withdrawal_id": str(withdrawal.id), "asset": withdrawal.asset, "amount": withdrawal.amount, "destination": withdrawal.destination}

@router.get("/withdrawals")
async def get_withdrawals(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Withdrawal).where(Withdrawal.merchant_id == user.id).order_by(Withdrawal.created_at.desc()))
    return {"status": "success", "data": result.scalars().all()}

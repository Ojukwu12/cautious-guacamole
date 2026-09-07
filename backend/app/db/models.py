import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="merchant") # 'admin' or 'merchant'
    api_key = Column(String(64), unique=True, nullable=True)
    webhook_url = Column(String(500), nullable=True)
    webhook_secret = Column(String(128), nullable=True)
    settlement_asset = Column(String(20), default="NGN")
    payment_options = Column(JSON, default=lambda: ["card", "bank_transfer", "bank_app", "crypto"])
    created_at = Column(DateTime, default=datetime.now)

class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    asset = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    destination = Column(String(120), nullable=False)
    status = Column(String(20), default="processing", nullable=False)
    created_at = Column(DateTime, default=datetime.now)

class TransactionLedger(Base):
    __tablename__ = "transactions_ledger"

    tx_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    fiat_amount = Column(Float, nullable=False)
    currency = Column(String(20), nullable=False)
    settlement_value = Column(Float, nullable=False)
    payment_currency = Column(String(10), nullable=True)
    payment_amount = Column(Float, nullable=True)
    payment_method = Column(String(30), nullable=True)
    status = Column(String(20), default="completed", nullable=False)
    
    # The Cryptographic Chain
    current_hash = Column(String(64), unique=True, nullable=False)
    previous_hash = Column(String(64), nullable=False)
    
    created_at = Column(DateTime, default=datetime.now)

class CheckoutSession(Base):
    __tablename__ = "checkout_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    fiat_amount = Column(Float, nullable=False)
    fiat_currency = Column(String(3), nullable=False)
    settlement_asset = Column(String(20), nullable=False)
    exchange_rate = Column(Float, nullable=False)
    quote_id = Column(String(64), nullable=False)
    payment_options = Column(JSON, nullable=False)
    status = Column(String(20), default="open", nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
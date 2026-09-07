import secrets
import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, EmailStr

from app.db.connection import get_db
from app.db.models import User
from app.core.security import get_password_hash, verify_password, create_access_token, get_current_user
from app.exceptions.custom_exceptions import (
    DuplicateEmailException, 
    InvalidCredentialsException, 
    DatabaseOperationException
)

router = APIRouter(
    prefix="/api/auth",
    tags=["Merchant Authentication"]
)
logger = logging.getLogger(__name__)

class MerchantRegister(BaseModel):
    email: EmailStr
    password: str

class MerchantLogin(BaseModel):
    email: EmailStr
    password: str

class SettlementSettings(BaseModel):
    settlement_asset: str
    webhook_url: str | None = None
    payment_options: list[str] = ["card", "bank_transfer", "bank_app", "crypto"]

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_merchant(payload: MerchantRegister, db: AsyncSession = Depends(get_db)):
    try:
        # 1. Check for existing email
        query = select(User).where(User.email == payload.email)
        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise DuplicateEmailException()

        # 2. Hash password & generate API key
        hashed_pwd = get_password_hash(payload.password)
        new_api_key = f"vg_live_{secrets.token_hex(16)}"

        # 3. Commit to database
        new_merchant = User(
            email=payload.email,
            password_hash=hashed_pwd,
            api_key=new_api_key,
            webhook_secret=secrets.token_urlsafe(32),
            role="merchant"
        )
        
        db.add(new_merchant)
        await db.commit()
        await db.refresh(new_merchant)
        access_token = create_access_token(data={"sub": str(new_merchant.id), "role": new_merchant.role})

        return {
            "status": "success",
            "message": "Merchant registered successfully.",
            "merchant_id": str(new_merchant.id),
            "api_key": new_api_key,
            "email": new_merchant.email,
            "access_token": access_token,
            "token_type": "bearer",
            "role": new_merchant.role,
        }

    except DuplicateEmailException as de:
        raise de
    except Exception as e:
        await db.rollback()
        logger.exception("Merchant registration failed", exc_info=e)
        raise DatabaseOperationException("Registration could not be completed. Please try again.")

@router.post("/login")
async def login_merchant(payload: MerchantLogin, db: AsyncSession = Depends(get_db)):
    try:
        # 1. Fetch user
        query = select(User).where(User.email == payload.email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        # 2. Verify password match
        if not user or not verify_password(payload.password, str(user.password_hash)):
            raise InvalidCredentialsException()

        # 3. Mint JWT token
        access_token = create_access_token(data={"sub": str(user.id), "role": user.role})

        return {
            "status": "success",
            "access_token": access_token,
            "token_type": "bearer",
            "merchant_id": str(user.id),
            "role": user.role,
        }

    except InvalidCredentialsException as ice:
        raise ice
    except Exception as e:
        await db.rollback()
        logger.exception("Merchant login failed", exc_info=e)
        raise DatabaseOperationException("Login could not be completed. Please try again.")

@router.get("/me")
async def get_profile(user=Depends(get_current_user)):
    return {
        "merchant_id": str(user.id),
        "role": user.role,
        "email": user.email,
        "api_key": user.api_key,
        "settlement_asset": user.settlement_asset,
        "webhook_url": user.webhook_url,
        "payment_options": user.payment_options or [],
    }

@router.patch("/settings")
async def update_settings(payload: SettlementSettings, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user.settlement_asset = payload.settlement_asset.upper()
    user.webhook_url = payload.webhook_url
    user.payment_options = payload.payment_options
    await db.commit()
    return {"status": "success", "settlement_asset": user.settlement_asset, "webhook_url": user.webhook_url, "payment_options": user.payment_options}
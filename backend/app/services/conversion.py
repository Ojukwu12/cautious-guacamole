import json
import uuid
from datetime import datetime
from typing import cast

import httpx
import redis
from redis.exceptions import RedisError

from app.core.config import settings

# Initialize Redis with a short 2-second timeout
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True, socket_connect_timeout=2)

SUPPORTED_PAYMENT_CURRENCIES = ["USD", "NGN", "GHS", "EUR", "GBP", "BTC", "ETH", "USDT"]
LIVE_RATES_CACHE_KEY = "rates:usd:live"

def apply_platform_fee(amount: float) -> dict[str, float]:
    fee = round(amount * settings.PLATFORM_FEE_PERCENTAGE / 100, 8)
    return {
        "platform_fee_percentage": settings.PLATFORM_FEE_PERCENTAGE,
        "platform_fee_value": fee,
        "customer_total": round(amount + fee, 8),
    }

async def fetch_live_usd_rates() -> dict[str, float] | None:
    if not settings.LIVE_RATES_ENABLED:
        return None
    try:
        cached_data = redis_client.get(LIVE_RATES_CACHE_KEY)
        if cached_data:
            return json.loads(cast(str, cached_data))
    except (RedisError, json.JSONDecodeError):
        pass
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(settings.RATE_PROVIDER_URL)
            response.raise_for_status()
            payload = response.json()
        raw_rates = payload.get("data", {}).get("rates", {})
        rates = {currency.upper(): float(rate) for currency, rate in raw_rates.items()}
        rates["USD"] = 1.0
        if not all(currency in rates for currency in SUPPORTED_PAYMENT_CURRENCIES):
            return None
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        return None
    try:
        redis_client.setex(LIVE_RATES_CACHE_KEY, settings.RATE_CACHE_SECONDS, json.dumps(rates))
    except RedisError:
        pass
    return rates

async def get_customer_quote(amount: float, source_currency: str, payment_currency: str) -> dict | None:
    source = source_currency.upper()
    target = payment_currency.upper()
    if source not in SUPPORTED_PAYMENT_CURRENCIES or target not in SUPPORTED_PAYMENT_CURRENCIES:
        return None
    rates = await fetch_live_usd_rates()
    if not rates or source not in rates or target not in rates:
        return None
    rate = rates[target] / rates[source]
    fee = apply_platform_fee(amount)
    return {
        "source_currency": source,
        "payment_currency": target,
        "rate": round(rate, 10),
        "payment_amount": round(fee["customer_total"] * rate, 8),
        **fee,
        "quote_source": "Coinbase live exchange rates",
        "quote_timestamp": datetime.utcnow().isoformat(),
    }

async def get_secured_exchange_rate(currency_pair: str, spread_percentage: float = 1.5) -> dict | None:
    source, target = currency_pair.upper().split("_", 1)
    rates = await fetch_live_usd_rates()
    if not rates or source not in rates or target not in rates:
        return None
    raw_rate = rates[target] / rates[source]
    secured_rate = raw_rate * (1 + (spread_percentage / 100))
    return {"quote_id": str(uuid.uuid4()), "currency_pair": currency_pair.upper(), "rate": round(secured_rate, 8), "expires_in_seconds": settings.RATE_CACHE_SECONDS, "timestamp": datetime.utcnow().isoformat(), "quote_source": "Coinbase live exchange rates"}
import redis
from redis.exceptions import RedisError
import json
import uuid
from datetime import datetime
from typing import cast

# Initialize Redis with a short 2-second timeout
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True, socket_connect_timeout=2)

SUPPORTED_PAYMENT_CURRENCIES = ["USD", "NGN", "GHS", "EUR", "GBP", "BTC", "ETH", "USDT"]
UNITS_PER_USD = {
    "USD": 1.0, "NGN": 1500.0, "GHS": 15.0, "EUR": 0.92,
    "GBP": 0.78, "BTC": 0.000015, "ETH": 0.0004, "USDT": 1.0,
}

def get_customer_quote(amount: float, source_currency: str, payment_currency: str) -> dict | None:
    source = source_currency.upper()
    target = payment_currency.upper()
    if source not in UNITS_PER_USD or target not in UNITS_PER_USD:
        return None
    rate = UNITS_PER_USD[target] / UNITS_PER_USD[source]
    return {
        "source_currency": source,
        "payment_currency": target,
        "rate": round(rate, 10),
        "payment_amount": round(amount * rate, 8),
        "quote_source": "Verve Gate deterministic prototype oracle",
    }

def fetch_raw_market_rate(currency_pair: str) -> float:
    mock_rates = {
        "USD_NGN": 1500.00, "GBP_NGN": 1900.00, "EUR_NGN": 1650.00,
        "NGN_USD": 0.000667, "NGN_GBP": 0.000526, "NGN_EUR": 0.000606,
        "USD_USD": 1.0, "GBP_GBP": 1.0, "EUR_EUR": 1.0, "NGN_NGN": 1.0,
        "USD_BTC": 0.000015, "GBP_BTC": 0.000019, "EUR_BTC": 0.000017,
        "USD_USDT": 1.0, "GBP_USDT": 1.27, "EUR_USDT": 1.08, "NGN_USDT": 0.000667,
    }
    return mock_rates.get(currency_pair, 1.0)

def get_secured_exchange_rate(currency_pair: str, spread_percentage: float = 1.5) -> dict:
    cache_key = f"rate:{currency_pair}:{spread_percentage}"
    
    # 1. Try to check Redis for an unexpired cached rate
    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cast(str, cached_data))
    except RedisError:
        pass 

    # 2. Fetch fresh rate and apply spread
    raw_rate = fetch_raw_market_rate(currency_pair)
    markup_multiplier = 1 + (spread_percentage / 100)
    secured_rate = raw_rate * markup_multiplier

    # 3. Generate a Rate Lock ID for the checkout session
    quote_id = str(uuid.uuid4())
    
    quote_data = {
        "quote_id": quote_id,
        "currency_pair": currency_pair,
        "rate": round(secured_rate, 8),
        "expires_in_seconds": 60,
        "timestamp": datetime.utcnow().isoformat()
    }

    # 4. Try to save to Redis, ignore if offline
    try:
        redis_client.setex(cache_key, 60, json.dumps(quote_data))
    except RedisError:
        pass 
        
    return quote_data
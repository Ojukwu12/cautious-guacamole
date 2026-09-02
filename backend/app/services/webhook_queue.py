import json
import hashlib
import hmac
import redis
from redis.exceptions import RedisError
from datetime import datetime, timezone

# Initialize Redis client with a short timeout for graceful degradation
# (If Redis is offline, it won't break the payment processing flow)
redis_client = redis.Redis(
    host='localhost', 
    port=6379, 
    db=0, 
    decode_responses=True, 
    socket_connect_timeout=2
)

QUEUE_NAME = "verve_gate_webhooks"

def enqueue_webhook_notification(
    transaction_id: str,
    merchant_id: str,
    settlement_value: float,
    status: str,
    webhook_secret: str | None = None,
    webhook_url: str | None = None,
):
    """
    Pushes a transaction notification payload into the Redis background queue.
    """
    payload = {
        "event": "transaction.successful",
        "transaction_id": transaction_id,
        "merchant_id": merchant_id,
        "settlement_value": settlement_value,
        "status": status,
    }
    timestamp = str(int(datetime.now(timezone.utc).timestamp()))
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    signature = hmac.new(
        (webhook_secret or "prototype-secret").encode(),
        f"{timestamp}.{body}".encode(),
        hashlib.sha256,
    ).hexdigest()
    queued_event = {
        "payload": payload,
        "webhook_url": webhook_url,
        "timestamp": timestamp,
        "signature": f"sha256={signature}",
        "attempt": 0,
        "max_attempts": 3,
    }
    
    try:
        # Push to the right side of the Redis list (Queue)
        redis_client.rpush(QUEUE_NAME, json.dumps(queued_event))
        print(f"[Webhook Queue] Successfully enqueued notification for TX: {transaction_id}")
    except RedisError as e:
        # Graceful degradation: Log the failure but do not crash the payment flow
        print(f"[Webhook Queue Warning] Redis offline. Could not enqueue webhook: {str(e)}")
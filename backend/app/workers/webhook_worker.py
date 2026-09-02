import time
import json
import redis
from redis.exceptions import ConnectionError, RedisError
from typing import cast
from app.services.webhook_queue import QUEUE_NAME

redis_client = redis.Redis(
    host='localhost', 
    port=6379, 
    db=0, 
    decode_responses=True
)

def start_worker():
    print("[*] Verve Gate Webhook Background Worker started. Listening for events...")
    while True:
        event_data = None
        try:
            # Block and wait for items in the Redis queue (timeout after 5 seconds)
            result = cast(tuple[str, str] | None, redis_client.blpop([QUEUE_NAME], timeout=5))
            if result:
                _, raw_data = result
                event_data = json.loads(raw_data)
                payload = event_data["payload"]
                
                print(f"\n[Webhook Worker] Processing event: {payload['event']}")
                print(f" -> Simulating POST for Merchant ID: {payload['merchant_id']}")
                print(f" -> HMAC: {event_data['signature']} | Attempt: {event_data['attempt'] + 1}/{event_data['max_attempts']}")
                print(f" -> Data: Transaction {payload['transaction_id']} | Value: {payload['settlement_value']}")
                
                # Simulate network request delay to a merchant server
                time.sleep(1)
                print("[Webhook Worker] Status: Simulated delivery successfully (no network request)\n")
                
        except ConnectionError:
            print("[Webhook Worker Warning] Redis connection lost. Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"[Webhook Worker Error] An unexpected error occurred: {str(e)}")
            if event_data and event_data["attempt"] + 1 < event_data["max_attempts"]:
                event_data["attempt"] += 1
                try:
                    redis_client.rpush(QUEUE_NAME, json.dumps(event_data))
                except RedisError:
                    print("[Webhook Worker] Could not requeue the failed event.")
                print(f"[Webhook Worker] Event requeued for attempt {event_data['attempt'] + 1}.")
            else:
                print("[Webhook Worker] Event exhausted its retry budget and was discarded.")

if __name__ == "__main__":
    start_worker()
## Verve Gate

Verve Gate is a cross-border payment gateway prototype. Merchants authenticate with JWT, create PostgreSQL-backed checkout sessions, resolve a mockable fiat-to-asset quote, and record completed payments in a chained SHA-256 ledger.

### Run locally

1. Start PostgreSQL and create a database named `verve_gate`. Redis is optional; it only powers the webhook worker.
2. Set `DATABASE_URL`, `SECRET_KEY`, `ALGORITHM`, and `ACCESS_TOKEN_EXPIRE_MINUTES` in `.env`.
3. Install backend dependencies with `pip install -r backend/requirements.txt`.
4. Apply the schema with `alembic -c backend/alembic.ini upgrade head`.
5. Start the API from `backend` with `uvicorn app.main:app --reload`.
6. Start the frontend from `frontend` with `npm install` and `npm run dev`.

The API runs on `http://localhost:8000` and the Vite app on `http://localhost:5173`.

### Main flows

- `POST /api/auth/register` and `POST /api/auth/login` manage merchant access.
- Authenticated merchants call `POST /api/checkout/session` to create a 15-minute checkout link.
- Customers open `/pay/{session_id}` and confirm payment without receiving merchant credentials.
- `GET /api/checkout/history` returns only the authenticated merchant's ledger entries.

Exchange rates are deterministic mock rates in `backend/app/services/conversion.py`, making the prototype reliable offline and easy to replace with a licensed provider later. Webhook events are signed with HMAC-SHA256 and include bounded retry metadata, but `webhook_worker.py` only simulates delivery and never calls an external endpoint.

Copy `frontend/.env.example` to `frontend/.env` and set `VITE_API_BASE_URL` to change the API origin. The default is `http://localhost:8000/api`.

# Valkey Ecommerce Backend

This backend is a FastAPI service that implements the requested ecommerce features using Valkey as the datastore.

## Install

```bash
cd /Users/rajanitak/Documents/valkey-ecommerce-demo/backend
python3 -m pip install -r requirements.txt
```

## Run

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Environment

Create a `.env` file in `backend/` to override defaults:

```text
VALKEY_URL=redis://localhost:6379
SECRET_KEY=your-secret-key
OPEN_SEARCH_URL=http://localhost:9200
```

## Endpoints

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /metrics`
- `POST /api/products`
- `GET /api/products`
- `POST /api/cart/items`
- `POST /api/checkout/start`
- `GET /api/trending`
- `GET /api/search`
- `POST /api/agent/search`
- and more

## Notes

- Products are stored as JSON objects in Valkey.
- Sessions are stored as expiring keys in Valkey.
- Coupon and cart data are stored in Redis hashes and strings.
- Search and semantic search use Valkey Search index commands.
- Delivery updates are published over Redis pub/sub for SSE streaming.
- Metrics are exposed on `/metrics` in Prometheus format.

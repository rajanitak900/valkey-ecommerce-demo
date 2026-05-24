import asyncio
import hashlib
import hmac
import json
import math
import os
import struct
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as redis
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, BaseSettings, Field, validator


class Settings(BaseSettings):
    VALKEY_URL: str = "redis://localhost:6379"
    SECRET_KEY: str = "change-me-please"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 86400
    CART_TTL_SECONDS: int = 604800
    COUPON_TTL_SECONDS: int = 86400
    RESERVATION_TTL_SECONDS: int = 600
    DELIVERY_HISTORY_TTL: int = 86400
    OPEN_SEARCH_URL: str = "http://localhost:9200"
    OPEN_SEARCH_USER: Optional[str] = None
    OPEN_SEARCH_PASSWORD: Optional[str] = None
    RATE_LIMITS: Dict[str, Dict[str, int]] = {
        "/api/search": {"anonymous": 20, "authenticated": 60, "window": 60},
        "/api/checkout/start": {"anonymous": 0, "authenticated": 5, "window": 60},
        "/api/auth/login": {"anonymous": 5, "authenticated": 5, "window": 900},
        "/api/products": {"anonymous": 30, "authenticated": 100, "window": 60},
        "/api/cart": {"anonymous": 10, "authenticated": 30, "window": 60},
    }
    PROMETHEUS_NAMESPACE: str = "ecommerce"

    class Config:
        env_file = ".env"


settings = Settings()

redis_client = redis.from_url(settings.VALKEY_URL, decode_responses=False)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

registry = CollectorRegistry()
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
    registry=registry,
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    registry=registry,
)
ACTIVE_USERS = Gauge(
    "active_users_total", "Current unique active users", registry=registry
)


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=8)
    full_name: Optional[str]

    @validator("email")
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    created_at: str
    last_login_at: Optional[str]


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CategoryIn(BaseModel):
    name: str
    parent_id: Optional[str]
    description: Optional[str]


class ProductIn(BaseModel):
    name: str
    description: str
    brand: str
    vendor_id: str
    category_id: str
    price: int
    currency: str = "INR"
    inventory_quantity: int = 0
    tags: List[str] = []
    status: str = "active"
    rating: float = 0.0


class ProductPatch(BaseModel):
    name: Optional[str]
    description: Optional[str]
    brand: Optional[str]
    vendor_id: Optional[str]
    category_id: Optional[str]
    price: Optional[int]
    inventory_quantity: Optional[int]
    tags: Optional[List[str]]
    status: Optional[str]
    rating: Optional[float]


class CartItem(BaseModel):
    product_id: str
    quantity: int = Field(gt=0)


class CouponApply(BaseModel):
    code: str


class EventIn(BaseModel):
    product_id: str
    category_id: Optional[str]
    user_id: Optional[str]


class AdIn(BaseModel):
    title: str
    image_url: str
    target_url: str
    target_categories: List[str] = []
    target_keywords: List[str] = []
    bid_amount: int
    daily_budget: int
    vendor_id: str
    status: str = "active"


class SearchParams(BaseModel):
    q: Optional[str] = None
    category: Optional[str] = None
    minPrice: Optional[int] = None
    maxPrice: Optional[int] = None
    sort: Optional[str] = None
    page: int = 1
    pageSize: int = 20


class CheckoutStart(BaseModel):
    cart_items: List[CartItem]
    coupon: Optional[str] = None
    idempotency_key: Optional[str] = None


class PaymentConfirm(BaseModel):
    order_id: str
    idempotency_key: Optional[str] = None


class LocationUpdate(BaseModel):
    lat: float
    lng: float
    status: Optional[str] = "in_transit"


class DeliveryCheck(BaseModel):
    lat: float
    lng: float


class AgentRequest(BaseModel):
    session_id: str
    message: str


class AgentResponse(BaseModel):
    session_id: str
    response: str
    results: List[Dict[str, Any]] = []
    follow_up: Optional[str] = None
    context: Dict[str, Any] = {}


def epoch_seconds() -> int:
    return int(time.time())


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS))
    payload = {"sub": subject, "exp": expire.isoformat()}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def generate_session_token() -> str:
    return uuid.uuid4().hex


def generate_text_embedding(text: str, dim: int = 384) -> List[float]:
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    vector = []
    for i in range(dim):
        value = ((seed[i % len(seed)] / 255.0) - 0.5) * 2.0
        vector.append(value)
    return vector


def pack_vector(vector: List[float]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


def compute_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def run_redis_command(*args, **kwargs):
    return await redis_client.execute_command(*args, **kwargs)


async def json_set(key: str, data: Any, ex: Optional[int] = None) -> None:
    await run_redis_command("JSON.SET", key, "$", json.dumps(data))
    if ex is not None:
        await redis_client.expire(key, ex)


async def json_get(key: str) -> Optional[Any]:
    payload = await run_redis_command("JSON.GET", key)
    if not payload:
        return None
    if isinstance(payload, bytes):
        payload = payload.decode()
    return json.loads(payload)


async def log_event(level: str, message: str, context: Dict[str, Any]) -> None:
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": level,
        "message": message,
        "context": context,
    }
    await run_redis_command("XADD", "logs:app", "*", "data", json.dumps(entry))


async def write_trace(trace_id: str, span: Dict[str, Any]) -> None:
    key = f"trace:{trace_id}"
    exists = await redis_client.exists(key)
    if not exists:
        trace = {"traceId": trace_id, "spans": [span], "status": span.get("status", "ok"), "totalDuration": span.get("duration", 0)}
        await json_set(key, trace, ex=3600)
    else:
        trace = await json_get(key)
        if trace:
            trace["spans"].append(span)
            trace["totalDuration"] = sum(s.get("duration", 0) for s in trace["spans"])
            trace["status"] = span.get("status", trace.get("status", "ok"))
            await json_set(key, trace, ex=3600)


async def get_rate_limit_config(path: str) -> Optional[Dict[str, int]]:
    for candidate, config in settings.RATE_LIMITS.items():
        if path.startswith(candidate):
            return config
    return None


async def rate_limit(request: Request, response: Response) -> None:
    path = request.url.path
    config = await get_rate_limit_config(path)
    if config is None:
        return
    auth_header = request.headers.get("authorization", "")
    user_id = None
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        user_id = decode_access_token(token)
    identifier = user_id or request.client.host
    window = config.get("window", 60)
    limit = config["authenticated"] if user_id else config["anonymous"]
    if limit == 0:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
    key = f"ratelimit:sliding:{identifier}:{path}"
    now = int(time.time() * 1000)
    member = str(uuid.uuid4())
    await run_redis_command("ZADD", key, now, member)
    await run_redis_command("ZREMRANGEBYSCORE", key, 0, now - window * 1000)
    count = await run_redis_command("ZCARD", key)
    await redis_client.expire(key, window + 2)
    remaining = max(limit - int(count), 0)
    reset = window
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset)
    if int(count) > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Retry after {reset} seconds.",
        )


async def get_current_user(authorization: str = Header(None)) -> Dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization token")
    token = authorization.split(" ", 1)[1].strip()
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = await json_get(f"user:{user_id}")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


app = FastAPI(title="Valkey Ecommerce Backend")


@app.middleware("http")
async def trace_rate_limit_metrics(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex
    response = Response("Internal server error", status_code=500)
    start = time.time()
    try:
        response = Response(status_code=500)
        await rate_limit(request, response)
        response = await call_next(request)
        return response
    except HTTPException as exc:
        response = JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        raise exc
    finally:
        duration = time.time() - start
        REQUEST_COUNT.labels(request.method, request.url.path, str(response.status_code)).inc()
        REQUEST_LATENCY.labels(request.method, request.url.path).observe(duration)
        await log_event(
            "info",
            "request.completed",
            {
                "path": request.url.path,
                "method": request.method,
                "status": response.status_code,
                "trace_id": trace_id,
                "duration_ms": int(duration * 1000),
            },
        )
        response.headers["X-Trace-Id"] = trace_id
        response.headers["Content-Type"] = response.headers.get("Content-Type", "application/json")


@app.on_event("startup")
async def startup_event():
    await create_search_index()


async def create_search_index() -> None:
    try:
        await run_redis_command("FT.INFO", "idx:products")
        return
    except Exception:
        pass
    try:
        await run_redis_command(
            "FT.CREATE",
            "idx:products",
            "ON",
            "JSON",
            "PREFIX",
            1,
            "product:",
            "SCHEMA",
            "$.name",
            "AS",
            "name",
            "TEXT",
            "WEIGHT",
            5.0,
            "$.description",
            "AS",
            "description",
            "TEXT",
            "WEIGHT",
            1.0,
            "$.brand",
            "AS",
            "brand",
            "TAG",
            "$.category_id",
            "AS",
            "categoryId",
            "TAG",
            "$.price",
            "AS",
            "price",
            "NUMERIC",
            "SORTABLE",
            "$.status",
            "AS",
            "status",
            "TAG",
            "$.created_at",
            "AS",
            "createdAt",
            "TEXT",
            "SORTABLE",
            "$.embedding",
            "AS",
            "embedding",
            "VECTOR",
            "HNSW",
            "6",
            "TYPE",
            "FLOAT32",
            "DIM",
            384,
            "DISTANCE_METRIC",
            "COSINE",
        )
    except Exception:
        pass


@app.get("/metrics")
async def metrics() -> Response:
    data = generate_latest(registry)
    return Response(content=data, media_type="text/plain; version=0.0.4")


@app.post("/api/auth/register", response_model=UserOut)
async def register(payload: UserCreate):
    existing_id = await redis_client.get(f"email_to_user:{payload.email}")
    if existing_id:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = f"user:{uuid.uuid4().hex}"
    user_data = {
        "id": user_id,
        "email": payload.email,
        "full_name": payload.full_name,
        "hashed_password": hash_password(payload.password),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "last_login_at": None,
    }
    await json_set(user_id, user_data)
    await redis_client.set(f"email_to_user:{payload.email}", user_id)
    return UserOut(**{k: user_data[k] for k in ["id", "email", "full_name", "created_at", "last_login_at"]})


@app.post("/api/auth/login", response_model=Token)
async def login(payload: UserLogin):
    user_id = await redis_client.get(f"email_to_user:{payload.email.strip().lower()}")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    user_id = user_id.decode()
    user = await json_get(user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not verify_password(payload.password, user["hashed_password"]):
        failed_key = f"login_attempts:{payload.email.strip().lower()}"
        await redis_client.incr(failed_key)
        await redis_client.expire(failed_key, 900)
        raise HTTPException(status_code=400, detail="Invalid credentials")
    user["last_login_at"] = datetime.utcnow().isoformat() + "Z"
    await json_set(user_id, user)
    token = create_access_token(user_id)
    session_token = generate_session_token()
    await redis_client.set(f"session:{session_token}", user_id, ex=settings.ACCESS_TOKEN_EXPIRE_SECONDS)
    return Token(access_token=token)


@app.post("/api/auth/logout")
async def logout(authorization: str = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")
    token = authorization.split(" ", 1)[1].strip()
    session_keys = await redis_client.keys("session:*")
    for key in session_keys:
        value = await redis_client.get(key)
        if value and value.decode() == decode_access_token(token):
            await redis_client.delete(key)
    return {"status": "logged_out"}


@app.get("/api/auth/me", response_model=UserOut)
async def auth_me(user: Dict[str, Any] = Depends(get_current_user)):
    return UserOut(
        id=user["id"],
        email=user["email"],
        full_name=user.get("full_name"),
        created_at=user["created_at"],
        last_login_at=user.get("last_login_at"),
    )


@app.post("/api/auth/refresh")
async def refresh_session(authorization: str = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")
    token = authorization.split(" ", 1)[1].strip()
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    keys = await redis_client.keys("session:*")
    for key in keys:
        value = await redis_client.get(key)
        if value and value.decode() == user_id:
            await redis_client.expire(key, settings.ACCESS_TOKEN_EXPIRE_SECONDS)
            return {"status": "session_refreshed"}
    raise HTTPException(status_code=401, detail="Session not found")


@app.post("/api/products")
async def create_product(payload: ProductIn, user: Dict[str, Any] = Depends(get_current_user)):
    product_id = f"product:{uuid.uuid4().hex}"
    data = {
        "id": product_id,
        "name": payload.name,
        "description": payload.description,
        "brand": payload.brand,
        "vendor_id": payload.vendor_id,
        "category_id": payload.category_id,
        "price": payload.price,
        "currency": payload.currency,
        "inventory": {"quantity": payload.inventory_quantity, "reserved": 0},
        "tags": payload.tags,
        "status": payload.status,
        "rating": payload.rating,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "embedding": generate_text_embedding(payload.name + " " + payload.description),
    }
    await json_set(product_id, data)
    await redis_client.sadd(f"brand_products:{payload.brand}", product_id)
    await redis_client.zadd(f"category_products:{payload.category_id}", {product_id: epoch_seconds()})
    await redis_client.zadd("price_index", {product_id: payload.price})
    await redis_client.execute_command("FT.SUGADD", "autocomplete", payload.name, 1)
    return data


@app.get("/api/products")
async def list_products(
    q: Optional[str] = None,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    minPrice: Optional[int] = None,
    maxPrice: Optional[int] = None,
    page: int = 1,
    pageSize: int = 20,
):
    offset = (page - 1) * pageSize
    if q:
        try:
            query = f"@name:({q})|@description:({q})"
            response = await run_redis_command(
                "FT.SEARCH",
                "idx:products",
                query,
                "LIMIT",
                offset,
                pageSize,
                "DIALECT",
                2,
            )
            total = int(response[0]) if response else 0
            results = []
            for i in range(1, len(response), 2):
                product_key = response[i].decode()
            product = await json_get(product_key)
            if product:
                results.append(product)
            return {"query": q, "total": total, "page": page, "pageSize": pageSize, "results": results}
        except Exception:
            pass
    keys = await redis_client.keys("product:*")
    start = offset
    end = offset + pageSize
    results = []
    for key in keys[start:end]:
        product = await json_get(key)
        if product:
            results.append(product)
    return {"query": q, "total": len(keys), "page": page, "pageSize": pageSize, "results": results}


@app.get("/api/products/{product_id}")
async def get_product(product_id: str):
    product = await json_get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.patch("/api/products/{product_id}")
async def update_product(product_id: str, payload: ProductPatch, user: Dict[str, Any] = Depends(get_current_user)):
    product = await json_get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    updated = payload.dict(exclude_unset=True)
    if "inventory_quantity" in updated:
        product["inventory"]["quantity"] = updated.pop("inventory_quantity")
    product.update(updated)
    await json_set(product_id, product)
    return product


@app.post("/api/categories")
async def create_category(payload: CategoryIn, user: Dict[str, Any] = Depends(get_current_user)):
    category_id = f"category:{uuid.uuid4().hex}"
    data = {
        "id": category_id,
        "name": payload.name,
        "parent_id": payload.parent_id,
        "description": payload.description,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    await json_set(category_id, data)
    return data


@app.get("/api/categories")
async def list_categories():
    keys = await redis_client.keys("category:*")
    categories = []
    for key in keys:
        category = await json_get(key)
        if category:
            categories.append(category)
    return categories


@app.get("/api/categories/{category_id}/products")
async def list_category_products(category_id: str, page: int = 1, pageSize: int = 20):
    offset = (page - 1) * pageSize
    products = await redis_client.zrevrange(f"category_products:{category_id}", offset, offset + pageSize - 1)
    result = []
    for item in products:
        product_key = item.decode()
        product = await json_get(product_key)
        if product:
            result.append(product)
    return {"category_id": category_id, "products": result}


@app.get("/api/vendors/{vendor_id}/products")
async def list_vendor_products(vendor_id: str, page: int = 1, pageSize: int = 20):
    keys = await redis_client.keys("product:*")
    results = []
    for key in keys:
        product = await json_get(key)
        if product and product.get("vendor_id") == vendor_id:
            results.append(product)
    offset = (page - 1) * pageSize
    return {"vendor_id": vendor_id, "products": results[offset : offset + pageSize]}


async def load_coupon(code: str) -> Optional[Dict[str, Any]]:
    return await json_get(f"coupon:{code}")


async def validate_coupon(code: str, cart_total: int, user_id: str) -> Dict[str, Any]:
    coupon = await load_coupon(code)
    if not coupon or not coupon.get("active", False):
        raise HTTPException(status_code=400, detail="Coupon invalid")
    now = datetime.utcnow().isoformat() + "Z"
    if coupon.get("valid_from") and coupon["valid_from"] > now:
        raise HTTPException(status_code=400, detail="Coupon not active yet")
    if coupon.get("valid_until") and coupon["valid_until"] < now:
        raise HTTPException(status_code=400, detail="Coupon expired")
    if coupon.get("usage_limit", 0) and coupon.get("usedCount", 0) >= coupon["usage_limit"]:
        raise HTTPException(status_code=400, detail="Coupon usage limit reached")
    if coupon.get("minOrderAmount", 0) > cart_total:
        raise HTTPException(status_code=400, detail="Cart total does not meet coupon minimum")
    used = await redis_client.sismember(f"coupon_used:{code}", user_id)
    if used:
        raise HTTPException(status_code=400, detail="Coupon already used by this user")
    return coupon


async def calculate_cart(user_id: str) -> Dict[str, Any]:
    cart_data = await redis_client.hgetall(f"cart:{user_id}")
    items = []
    subtotal = 0
    for key, value in cart_data.items():
        product_id = key.decode()
        quantity = int(value.decode())
        product = await json_get(product_id)
        if not product:
            continue
        line_total = product["price"] * quantity
        subtotal += line_total
        items.append({"product": product, "quantity": quantity, "line_total": line_total})
    coupon_code = await redis_client.get(f"cart_coupon:{user_id}")
    discount = 0
    coupon = None
    if coupon_code:
        coupon = await validate_coupon(coupon_code.decode(), subtotal, user_id)
        if coupon["type"] == "percentage":
            discount = subtotal * coupon["value"] // 100
            discount = min(discount, coupon.get("maxDiscount", discount))
        else:
            discount = coupon["value"]
    total = subtotal - discount
    return {"items": items, "subtotal": subtotal, "discount": discount, "total": total, "coupon": coupon}


@app.get("/api/cart")
async def get_cart(user: Dict[str, Any] = Depends(get_current_user)):
    cart = await calculate_cart(user["id"])
    return cart


@app.post("/api/cart/items")
async def add_cart_item(item: CartItem, user: Dict[str, Any] = Depends(get_current_user)):
    await redis_client.hincrby(f"cart:{user['id']}", item.product_id, item.quantity)
    await redis_client.expire(f"cart:{user['id']}", settings.CART_TTL_SECONDS)
    return await calculate_cart(user["id"])


@app.patch("/api/cart/items/{product_id}")
async def update_cart_item(product_id: str, item: CartItem, user: Dict[str, Any] = Depends(get_current_user)):
    await redis_client.hset(f"cart:{user['id']}", product_id, item.quantity)
    return await calculate_cart(user["id"])


@app.delete("/api/cart/items/{product_id}")
async def remove_cart_item(product_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    await redis_client.hdel(f"cart:{user['id']}", product_id)
    return await calculate_cart(user["id"])


@app.delete("/api/cart")
async def clear_cart(user: Dict[str, Any] = Depends(get_current_user)):
    await redis_client.delete(f"cart:{user['id']}")
    await redis_client.delete(f"cart_coupon:{user['id']}")
    return {"status": "cart_cleared"}


@app.post("/api/cart/coupon")
async def apply_coupon(payload: CouponApply, user: Dict[str, Any] = Depends(get_current_user)):
    cart = await calculate_cart(user["id"])
    await validate_coupon(payload.code, cart["subtotal"], user["id"])
    await redis_client.set(f"cart_coupon:{user['id']}", payload.code)
    return await calculate_cart(user["id"])


@app.delete("/api/cart/coupon")
async def remove_coupon(user: Dict[str, Any] = Depends(get_current_user)):
    await redis_client.delete(f"cart_coupon:{user['id']}")
    return await calculate_cart(user["id"])


async def record_trending(event_type: str, product_id: str, category_id: Optional[str]):
    weight = {"view": 1, "add_to_cart": 3, "purchase": 5}.get(event_type, 1)
    for window, seconds in [("1h", 3600), ("6h", 21600), ("24h", 86400)]:
        await redis_client.zincrby(f"trending:global:{window}", weight, product_id)
        await redis_client.expire(f"trending:global:{window}", seconds)
        if category_id:
            await redis_client.zincrby(f"trending:category:{category_id}:{window}", weight, product_id)
            await redis_client.expire(f"trending:category:{category_id}:{window}", seconds)


@app.post("/api/events/view")
async def record_view(event: EventIn):
    await record_trending("view", event.product_id, event.category_id)
    return {"status": "view_recorded"}


@app.post("/api/events/add-to-cart")
async def record_add_to_cart(event: EventIn):
    await record_trending("add_to_cart", event.product_id, event.category_id)
    return {"status": "add_to_cart_recorded"}


@app.post("/api/events/purchase")
async def record_purchase(event: EventIn):
    await record_trending("purchase", event.product_id, event.category_id)
    return {"status": "purchase_recorded"}


@app.get("/api/trending")
async def get_trending(window: str = "1h", limit: int = 10):
    products = await redis_client.zrevrange(f"trending:global:{window}", 0, limit - 1, withscores=True)
    results = []
    for pid, score in products:
        product = await json_get(pid)
        if product:
            results.append({"product": product, "score": score})
    return results


@app.get("/api/trending/{category_id}")
async def get_category_trending(category_id: str, window: str = "1h", limit: int = 10):
    products = await redis_client.zrevrange(f"trending:category:{category_id}:{window}", 0, limit - 1, withscores=True)
    results = []
    for pid, score in products:
        product = await json_get(pid)
        if product:
            results.append({"product": product, "score": score})
    return results


@app.post("/api/ads")
async def create_ad(payload: AdIn, user: Dict[str, Any] = Depends(get_current_user)):
    ad_id = f"ad:{uuid.uuid4().hex}"
    ad = {
        "id": ad_id,
        "title": payload.title,
        "image_url": payload.image_url,
        "target_url": payload.target_url,
        "target_categories": payload.target_categories,
        "target_keywords": payload.target_keywords,
        "bid_amount": payload.bid_amount,
        "daily_budget": payload.daily_budget,
        "vendor_id": payload.vendor_id,
        "status": payload.status,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    await json_set(ad_id, ad)
    for category in payload.target_categories:
        await redis_client.zadd(f"ads:category:{category}", {ad_id: payload.bid_amount})
    return ad


@app.get("/api/ads")
async def get_ads(category: Optional[str] = None, query: Optional[str] = None, user_id: Optional[str] = None):
    candidates = []
    if category:
        ad_keys = await redis_client.zrevrange(f"ads:category:{category}", 0, -1)
        candidates = [k.decode() for k in ad_keys]
    else:
        keys = await redis_client.keys("ad:*")
        candidates = [k.decode() for k in keys]
    ads = []
    for key in candidates:
        ad = await json_get(key)
        if not ad:
            continue
        if ad["status"] != "active":
            continue
        if query:
            if query.lower() not in ad["title"].lower() and not any(query.lower() in kw.lower() for kw in ad["target_keywords"]):
                continue
        if category and category not in ad["target_categories"]:
            continue
        if ad["daily_budget"] <= 0:
            continue
        if user_id:
            freq = await redis_client.get(f"ad_freq:{user_id}:{ad['id']}:{datetime.utcnow().date()}")
            if freq and int(freq.decode()) >= 3:
                continue
        ads.append(ad)
    ads.sort(key=lambda x: x["bid_amount"], reverse=True)
    return ads[:10]


@app.post("/api/ads/{ad_id}/impression")
async def record_ad_impression(ad_id: str, user_id: Optional[str] = None):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    await redis_client.incr(f"ad_impressions:{ad_id}:{today}")
    await redis_client.expire(f"ad_impressions:{ad_id}:{today}", 86400)
    if user_id:
        await redis_client.incr(f"ad_freq:{user_id}:{ad_id}:{today}")
        await redis_client.expire(f"ad_freq:{user_id}:{ad_id}:{today}", 86400)
    return {"status": "impression_recorded"}


@app.post("/api/ads/{ad_id}/click")
async def record_ad_click(ad_id: str):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    await redis_client.incr(f"ad_clicks:{ad_id}:{today}")
    await redis_client.expire(f"ad_clicks:{ad_id}:{today}", 86400)
    ad = await json_get(ad_id)
    if ad:
        await redis_client.incrby(f"ad_spend:{ad_id}:{today}", ad["bid_amount"])
        await redis_client.expire(f"ad_spend:{ad_id}:{today}", 86400)
    return {"status": "click_recorded"}


@app.get("/api/ads/{ad_id}/stats")
async def ad_stats(ad_id: str):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    impressions = await redis_client.get(f"ad_impressions:{ad_id}:{today}")
    clicks = await redis_client.get(f"ad_clicks:{ad_id}:{today}")
    spend = await redis_client.get(f"ad_spend:{ad_id}:{today}")
    return {
        "ad_id": ad_id,
        "impressions": int(impressions.decode()) if impressions else 0,
        "clicks": int(clicks.decode()) if clicks else 0,
        "spend": int(spend.decode()) if spend else 0,
    }


@app.get("/api/search")
async def search_products(
    q: Optional[str] = None,
    category: Optional[str] = None,
    minPrice: Optional[int] = None,
    maxPrice: Optional[int] = None,
    sort: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
):
    offset = (page - 1) * pageSize
    if not q:
        q = "*"
    query = q
    if category:
        query = f"(@categoryId:{{{category}}}) {query}"
    if minPrice is not None or maxPrice is not None:
        low = minPrice or 0
        high = maxPrice or 999999999
        query += f" @price:[{low} {high}]"
    try:
        command = ["FT.SEARCH", "idx:products", query]
        if sort in {"price_asc", "price_desc"}:
            command += ["SORTBY", "price", "ASC" if sort == "price_asc" else "DESC"]
        command += ["LIMIT", offset, pageSize, "DIALECT", 2]
        response = await run_redis_command(*command)
        total = int(response[0]) if response else 0
        results = []
        for i in range(1, len(response), 2):
            product_key = response[i].decode()
            product = await json_get(product_key)
            if product:
                results.append(product)
        return {"query": q, "total": total, "page": page, "pageSize": pageSize, "results": results}
    except Exception:
        return {"query": q, "total": 0, "page": page, "pageSize": pageSize, "results": []}


@app.get("/api/search/suggest")
async def suggest_search(q: str):
    try:
        response = await run_redis_command("FT.SUGGET", "autocomplete", q, "FUZZY", "MAX", 10)
        return {"query": q, "suggestions": [item.decode() for item in response]}
    except Exception:
        return {"query": q, "suggestions": []}


@app.get("/api/search/facets")
async def search_facets(q: str):
    try:
        response = await run_redis_command(
            "FT.AGGREGATE",
            "idx:products",
            q,
            "GROUPBY",
            1,
            "@brand",
            "REDUCE",
            "COUNT",
            0,
            "AS",
            "count",
            "SORTBY",
            2,
            "@count",
            "DESC",
            "LIMIT",
            0,
            10,
            "DIALECT",
            2,
        )
        facets = []
        for i in range(1, len(response)):
            row = response[i]
            if isinstance(row, list) and len(row) >= 4:
                facets.append({row[1].decode(): int(row[3].decode())})
        return {"query": q, "facets": facets}
    except Exception:
        return {"query": q, "facets": []}


@app.get("/api/search/semantic")
async def semantic_search(q: str, limit: int = 10):
    vector = generate_text_embedding(q)
    query_vec = pack_vector(vector)
    try:
        response = await run_redis_command(
            "FT.SEARCH",
            "idx:products",
            "*=>[KNN",
            limit,
            "@embedding",
            "$query_vec",
            "AS",
            "score]",
            "PARAMS",
            2,
            "query_vec",
            query_vec,
            "SORTBY",
            "score",
            "LIMIT",
            0,
            limit,
            "DIALECT",
            2,
        )
        total = int(response[0]) if response else 0
        results = []
        for i in range(1, len(response), 2):
            product_key = response[i].decode()
            product = await json_get(product_key)
            if product:
                results.append(product)
        return {"query": q, "total": total, "results": results}
    except Exception:
        return await search_products(q=q, page=1, pageSize=limit)


@app.get("/api/products/{product_id}/similar")
async def similar_products(product_id: str, limit: int = 10):
    product = await json_get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not product.get("embedding"):
        raise HTTPException(status_code=400, detail="Product has no embedding")
    vector = product["embedding"]
    query_vec = pack_vector(vector)
    try:
        response = await run_redis_command(
            "FT.SEARCH",
            "idx:products",
            "*=>[KNN",
            limit,
            "@embedding",
            "$query_vec",
            "AS",
            "score]",
            "PARAMS",
            2,
            "query_vec",
            query_vec,
            "SORTBY",
            "score",
            "LIMIT",
            0,
            limit,
            "DIALECT",
            2,
        )
        results = []
        for i in range(1, len(response), 2):
            product_key = response[i].decode()
            if product_key == product_id:
                continue
            product = await json_get(product_key)
            if product:
                results.append(product)
        return results
    except Exception:
        return []


@app.post("/api/checkout/start")
async def checkout_start(payload: CheckoutStart, user: Dict[str, Any] = Depends(get_current_user)):
    idempotency_key = payload.idempotency_key or uuid.uuid4().hex
    existing = await json_get(f"idempotency:{idempotency_key}")
    if existing:
        return existing
    reserved_items = []
    for item in payload.cart_items:
        product = await json_get(item.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        available = product["inventory"]["quantity"] - product["inventory"]["reserved"]
        if available < item.quantity:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} out of stock")
        product["inventory"]["reserved"] += item.quantity
        await json_set(item.product_id, product)
        await redis_client.set(f"reservation:{idempotency_key}:{item.product_id}", item.quantity, ex=settings.RESERVATION_TTL_SECONDS)
        reserved_items.append(item.dict())
    order_id = f"order:{uuid.uuid4().hex}"
    order = {
        "id": order_id,
        "user_id": user["id"],
        "items": [item.dict() for item in payload.cart_items],
        "coupon": payload.coupon,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "idempotency_key": idempotency_key,
    }
    await json_set(order_id, order)
    await json_set(f"idempotency:{idempotency_key}", order, ex=86400)
    return order


@app.post("/api/checkout/payment")
async def checkout_payment(payload: PaymentConfirm, user: Dict[str, Any] = Depends(get_current_user)):
    order = await json_get(payload.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["status"] != "pending":
        raise HTTPException(status_code=400, detail="Order already processed")
    order["status"] = "paid"
    order["paid_at"] = datetime.utcnow().isoformat() + "Z"
    await json_set(payload.order_id, order)
    return order


@app.post("/api/checkout/confirm")
async def checkout_confirm(payload: PaymentConfirm, user: Dict[str, Any] = Depends(get_current_user)):
    order = await json_get(payload.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["status"] != "paid":
        raise HTTPException(status_code=400, detail="Payment not confirmed")
    for item in order["items"]:
        product = await json_get(item["product_id"])
        if not product:
            continue
        product["inventory"]["quantity"] -= item["quantity"]
        product["inventory"]["reserved"] -= item["quantity"]
        await json_set(item["product_id"], product)
    order["status"] = "confirmed"
    order["confirmed_at"] = datetime.utcnow().isoformat() + "Z"
    await json_set(payload.order_id, order)
    await redis_client.zadd(f"user_orders:{user['id']}", {order["confirmed_at"]: epoch_seconds()})
    return order


@app.post("/api/checkout/cancel")
async def checkout_cancel(payload: PaymentConfirm, user: Dict[str, Any] = Depends(get_current_user)):
    order = await json_get(payload.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["status"] in ["confirmed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Order cannot be cancelled")
    for item in order["items"]:
        product = await json_get(item["product_id"])
        if not product:
            continue
        product["inventory"]["reserved"] -= item["quantity"]
        await json_set(item["product_id"], product)
    order["status"] = "cancelled"
    order["cancelled_at"] = datetime.utcnow().isoformat() + "Z"
    await json_set(payload.order_id, order)
    return order


@app.get("/api/orders")
async def list_orders(user: Dict[str, Any] = Depends(get_current_user)):
    order_ids = await redis_client.zrange(f"user_orders:{user['id']}", 0, -1)
    orders = []
    for oid in order_ids:
        order = await json_get(oid)
        if order:
            orders.append(order)
    return orders


@app.get("/api/orders/{order_id}")
async def get_order(order_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    order = await json_get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    return order


@app.post("/api/delivery/{tracking_id}/location")
async def update_delivery_location(tracking_id: str, payload: LocationUpdate):
    tracking_key = f"delivery:{tracking_id}"
    record = {
        "trackingId": tracking_id,
        "currentLocation": {"lat": payload.lat, "lng": payload.lng},
        "status": payload.status,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    await json_set(tracking_key, record, ex=settings.DELIVERY_HISTORY_TTL)
    await redis_client.geoadd("delivery_agents", payload.lng, payload.lat, tracking_id)
    message = json.dumps({"trackingId": tracking_id, "lat": payload.lat, "lng": payload.lng, "status": payload.status})
    await redis_client.publish(f"delivery:location:{tracking_id}", message)
    return record


@app.get("/api/delivery/{tracking_id}")
async def get_delivery(tracking_id: str):
    delivery = await json_get(f"delivery:{tracking_id}")
    if not delivery:
        raise HTTPException(status_code=404, detail="Tracking ID not found")
    return delivery


@app.get("/api/delivery/check-serviceability")
async def check_serviceability(lat: float, lng: float):
    warehouses = await run_redis_command(
        "GEOSEARCH",
        "warehouses",
        "FROMLONLAT",
        lng,
        lat,
        "BYRADIUS",
        25,
        "km",
        "ASC",
        "COUNT",
        3,
    )
    return {"serviceable": len(warehouses) > 0, "warehouses": warehouses}


@app.get("/api/delivery/eta")
async def estimate_eta(from_lat: float, from_lng: float, to_lat: float, to_lng: float):
    distance_km = compute_distance(from_lat, from_lng, to_lat, to_lng)
    speed_kmh = 40.0
    eta_minutes = int(distance_km / speed_kmh * 60)
    return {"distance_km": round(distance_km, 2), "eta_minutes": eta_minutes}


@app.get("/api/delivery/{tracking_id}/track")
async def track_delivery(tracking_id: str):
    async def event_generator():
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"delivery:location:{tracking_id}")
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=20)
                if message and message.get("data"):
                    yield f"data: {message['data'].decode()}\n\n"
                await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe(f"delivery:location:{tracking_id}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/analytics/dashboard")
async def analytics_dashboard():
    orders = 0
    revenue = 0
    active_users = 0
    keys = await redis_client.keys("metrics:orders:count:*")
    for key in keys:
        count = await redis_client.get(key)
        orders += int(count.decode()) if count else 0
    revenue_keys = await redis_client.keys("metrics:revenue:*")
    for key in revenue_keys:
        amount = await redis_client.get(key)
        revenue += int(amount.decode()) if amount else 0
    active_users = await redis_client.pfcount(f"active_users:{datetime.utcnow().strftime('%Y-%m-%d')}:{datetime.utcnow().hour}")
    ACTIVE_USERS.set(active_users)
    return {"orders": orders, "revenue": revenue, "active_users": active_users}


@app.get("/api/analytics/revenue")
async def analytics_revenue(from_ts: Optional[int] = None, to_ts: Optional[int] = None, interval: str = "1h"):
    return {"from": from_ts, "to": to_ts, "interval": interval, "series": []}


@app.get("/api/analytics/orders")
async def analytics_orders(from_ts: Optional[int] = None, to_ts: Optional[int] = None):
    return {"from": from_ts, "to": to_ts, "orders": []}


@app.get("/api/analytics/active-users")
async def analytics_active_users():
    count = await redis_client.pfcount(f"active_users:{datetime.utcnow().strftime('%Y-%m-%d')}:{datetime.utcnow().hour}")
    return {"active_users": count}


@app.get("/api/observability/logs")
async def observability_logs(level: Optional[str] = None, service: Optional[str] = None, limit: int = 50):
    logs = []
    response = await run_redis_command("XREVRANGE", "logs:app", "+", "-", "COUNT", limit)
    for item in response:
        entry = json.loads(item[1][1].decode())
        if level and entry["level"] != level:
            continue
        if service and entry["context"].get("service") != service:
            continue
        logs.append(entry)
    return logs


@app.get("/api/observability/traces/{trace_id}")
async def observability_trace(trace_id: str):
    trace = await json_get(f"trace:{trace_id}")
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@app.get("/api/observability/errors")
async def observability_errors():
    entries = await run_redis_command("ZREVRANGE", "errors:24h", 0, 49, "WITHSCORES")
    return [{"error": entries[i].decode(), "count": int(entries[i + 1])} for i in range(0, len(entries), 2)]


@app.get("/api/observability/health")
async def observability_health():
    return {"status": "ok", "valkey": settings.VALKEY_URL}


@app.post("/api/recommendations/events")
async def record_recommendation_event(event: EventIn):
    if event.user_id:
        await redis_client.lpush(f"user_history:{event.user_id}", event.product_id)
        await redis_client.ltrim(f"user_history:{event.user_id}", 0, 49)
        await redis_client.expire(f"user_history:{event.user_id}", settings.CART_TTL_SECONDS)
        if event.category_id:
            await redis_client.zincrby(f"user_affinity:{event.user_id}", 1, event.category_id)
    return {"status": "recommendation_event_recorded"}


@app.get("/api/recommendations/personalized")
async def personalized_recommendations(user: Dict[str, Any] = Depends(get_current_user), limit: int = 10):
    affinity = await redis_client.zrevrange(f"user_affinity:{user['id']}", 0, 4, withscores=True)
    results = []
    for category_id, _ in affinity:
        category_id = category_id.decode()
        trending = await redis_client.zrevrange(f"trending:category:{category_id}:24h", 0, limit - 1)
        for pid in trending:
            product = await json_get(pid)
            if product:
                results.append(product)
    if not results:
        results = (await get_trending())[0:limit]
    return results[:limit]


@app.get("/api/recommendations/recently-viewed")
async def recently_viewed(user: Dict[str, Any] = Depends(get_current_user)):
    items = await redis_client.lrange(f"user_history:{user['id']}", 0, 19)
    results = []
    for pid in items:
        product = await json_get(pid.decode())
        if product:
            results.append(product)
    return results


@app.get("/api/recommendations/similar/{product_id}")
async def recommendations_similar(product_id: str, limit: int = 10):
    return await similar_products(product_id, limit)


@app.get("/api/recommendations/trending-for-you")
async def trending_for_you(user: Dict[str, Any] = Depends(get_current_user), limit: int = 10):
    feed = await personalized_recommendations(user, limit)
    return feed


@app.post("/api/agent/search")
async def agent_search(payload: AgentRequest):
    session_key = f"conversation:{payload.session_id}"
    conversation = await json_get(session_key)
    if not conversation:
        conversation = {"sessionId": payload.session_id, "turns": [], "context": {}}
    conversation["turns"].append({"role": "user", "content": payload.message, "timestamp": datetime.utcnow().isoformat() + "Z"})
    if "cheaper" in payload.message.lower():
        search_response = await search_products(q="*", page=1, pageSize=10)
        response_text = "Here are cheaper options based on your last search."
        results = search_response.get("results", [])
    else:
        search_response = await semantic_search(q=payload.message, limit=5)
        response_text = "I found these items that match your request."
        results = search_response.get("results", [])
    conversation["turns"].append(
        {
            "role": "agent",
            "content": response_text,
            "results": [item.get("id") for item in results],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    )
    conversation["context"]["last_query"] = payload.message
    await json_set(session_key, conversation, ex=1800)
    return AgentResponse(
        session_id=payload.session_id,
        response=response_text,
        results=[{"productId": item.get("id"), "name": item.get("name"), "reason": "Relevant to your request"} for item in results],
        follow_up="Would you like me to filter by price or category?",
        context=conversation["context"],
    )


@app.get("/api/agent/conversation/{session_id}")
async def agent_conversation(session_id: str):
    conversation = await json_get(f"conversation:{session_id}")
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.post("/api/agent/feedback")
async def agent_feedback(data: Dict[str, Any]):
    return {"status": "feedback_received"}

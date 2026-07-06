from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
from fastapi import Header, HTTPException

import os
import time
import uuid
import yaml
import jwt

from dotenv import load_dotenv
from jwt.exceptions import InvalidTokenError

import time
import uuid
import logging
from collections import deque

from fastapi import Request
from fastapi.responses import PlainTextResponse

from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

load_dotenv()

app = FastAPI()
# =====================================================
# OBSERVABILITY
# =====================================================

START_TIME = time.time()

REQUEST_COUNTER = Counter(
    "http_requests_total",
    "Total HTTP requests"
)

LOGS = deque(maxlen=1000)
# =====================================================
# CONFIGURATION
# =====================================================

EMAIL = "23f2000333@ds.study.iitm.ac.in"

ANALYTICS_API_KEY = "ak_370f157fr363nhaitkk2kpea"

ALLOWED_ORIGIN = "https://dash-sx1nc2.example.com"

ISSUER = "https://idp.exam.local"

AUDIENCE = "tds-kmppxl5o.apps.exam.local"

PUBLIC_KEY = """
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2okOHspNjgA+2rTLbeuY
cxiP/hG8C6Sb9iwg3yiLAA4HCnpITcbWCSelbvbYGuc3EbNy4xFyf5Cbj5DHJMID
EkryOgyd2giIIIBOUBj8S63uGcnRpOBh9NFatfNwheKuzsPuVNldu6A9cNteNpXc
WyJjG2axVfmq7i6SuKr1JoWYG7xTTAvKPujSl4OtsQfO3h5NepzdfXpr28oNnzfW
ed+zclR6BcmNNo/WVfJ4xyCLSf0BCOgdTgW6PdaChd1l9VDetJZVEgC5tkyvXsfI
SI6iyrYbKR0NEBSqq4XkadEjsCs4F1RncsS4LlgniT7GlkL9Mce3b0wGLs9/7ZIX
dQIDAQAB
-----END PUBLIC KEY-----
"""

# =====================================================
# CORS
# =====================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        ALLOWED_ORIGIN,
        "*"   # needed for Assignment 3 browser check
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# MIDDLEWARE
# =====================================================

@app.middleware("http")
async def observability_middleware(request: Request, call_next):

    REQUEST_COUNTER.inc()

    request_id = str(uuid.uuid4())

    start = time.perf_counter()

    response = await call_next(request)

    elapsed = time.perf_counter() - start

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{elapsed:.6f}"

    LOGS.append(
        {
            "level": "INFO",
            "ts": time.time(),
            "path": request.url.path,
            "request_id": request_id,
        }
    )

    return response

# =====================================================
# MODELS
# =====================================================

class TokenRequest(BaseModel):
    token: str

class Event(BaseModel):
    user: str
    amount: float
    ts: int


class AnalyticsRequest(BaseModel):
    events: List[Event]
# =====================================================
# HOME
# =====================================================

@app.get("/")
def home():
    return {"message": "FastAPI Service Running"}

# =====================================================
# ASSIGNMENT 1
# =====================================================

@app.get("/stats")
def stats(values: str = Query(...)):

    try:
        nums = [int(x.strip()) for x in values.split(",") if x.strip()]
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"error": "values must contain integers"},
        )

    if not nums:
        return JSONResponse(
            status_code=400,
            content={"error": "No values supplied"},
        )

    return {
        "email": EMAIL,
        "count": len(nums),
        "sum": sum(nums),
        "min": min(nums),
        "max": max(nums),
        "mean": sum(nums) / len(nums),
    }

# =====================================================
# ASSIGNMENT 2
# =====================================================

@app.post("/verify")
def verify(request: TokenRequest):

    try:

        payload = jwt.decode(
            request.token,
            PUBLIC_KEY,
            algorithms=["RS256"],
            issuer=ISSUER,
            audience=AUDIENCE,
        )

        return {
            "valid": True,
            "email": payload.get("email"),
            "sub": payload.get("sub"),
            "aud": payload.get("aud"),
        }

    except InvalidTokenError:

        return JSONResponse(
            status_code=401,
            content={
                "valid": False
            },
        )

# =====================================================
# ASSIGNMENT 3
# =====================================================

@app.get("/effective-config")
def effective_config(set: list[str] | None = Query(default=None)):

    # -------------------------
    # 1. Defaults
    # -------------------------
    config = {
        "port": 8000,
        "workers": 1,
        "debug": False,
        "log_level": "info",
        "api_key": "default-secret-000",
    }

    # -------------------------
    # 2. config.development.yaml
    # -------------------------
    if os.path.exists("config.development.yaml"):
        with open("config.development.yaml", "r") as f:
            yaml_config = yaml.safe_load(f) or {}
        config.update(yaml_config)

    # -------------------------
    # 3. .env layer
    #
    # Assignment says .env is empty.
    # Only support NUM_WORKERS alias if present.
    # -------------------------
    if os.getenv("NUM_WORKERS") is not None:
        config["workers"] = os.getenv("NUM_WORKERS")

    # -------------------------
    # 4. APP_* OS environment
    # -------------------------
    for key, value in os.environ.items():
        if key.startswith("APP_"):
            config[key[4:].lower()] = value

    # -------------------------
    # 5. CLI overrides
    # -------------------------
    if set:
        for item in set:
            if "=" not in item:
                continue

            key, value = item.split("=", 1)
            config[key] = value

    # -------------------------
    # Type coercion
    # -------------------------
    config["port"] = int(config["port"])
    config["workers"] = int(config["workers"])

    if isinstance(config["debug"], str):
        config["debug"] = config["debug"].strip().lower() in (
            "true",
            "1",
            "yes",
            "on",
        )

    config["log_level"] = str(config["log_level"])

    # Never expose the real secret
    config["api_key"] = "****"

    return config


# =====================================================
# ASSIGNMENT 4
# =====================================================

@app.post("/analytics")
def analytics(
    request: AnalyticsRequest,
    x_api_key: str = Header(default=None),
):
    if x_api_key != ANALYTICS_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
        )

    events = request.events

    total_events = len(events)

    unique_users = len({event.user for event in events})

    revenue = 0.0

    user_totals = {}

    for event in events:
        if event.amount > 0:
            revenue += event.amount

            user_totals[event.user] = (
                user_totals.get(event.user, 0.0)
                + event.amount
            )

    top_user = ""

    if user_totals:
        top_user = max(user_totals, key=user_totals.get)

    return {
        "email": EMAIL,
        "total_events": total_events,
        "unique_users": unique_users,
        "revenue": revenue,
        "top_user": top_user,
    }

@app.get("/work")
def work(n: int = 1):

    # simulate work
    for _ in range(max(0, n)):
        pass

    return {
        "email": EMAIL,
        "done": n,
    }

@app.get("/metrics")
def metrics():

    return PlainTextResponse(
        generate_latest().decode(),
        media_type=CONTENT_TYPE_LATEST,
    )

@app.get("/healthz")
def healthz():

    return {
        "status": "ok",
        "uptime_s": time.time() - START_TIME,
    }

@app.get("/logs/tail")
def logs_tail(limit: int = 10):

    limit = max(1, min(limit, 100))

    return list(LOGS)[-limit:]

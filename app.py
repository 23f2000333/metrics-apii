from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import os
import time
import uuid
import yaml
import jwt

from dotenv import load_dotenv
from jwt.exceptions import InvalidTokenError

load_dotenv()

app = FastAPI()

# =====================================================
# CONFIGURATION
# =====================================================

EMAIL = "23f2000333@ds.study.iitm.ac.in"

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
async def add_headers(request, call_next):

    start = time.perf_counter()

    response = await call_next(request)

    elapsed = time.perf_counter() - start

    response.headers["X-Request-ID"] = str(uuid.uuid4())
    response.headers["X-Process-Time"] = f"{elapsed:.6f}"

    return response

# =====================================================
# MODELS
# =====================================================

class TokenRequest(BaseModel):
    token: str

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

    config = {
        "port": 8000,
        "workers": 1,
        "debug": False,
        "log_level": "info",
        "api_key": "default-secret-000",
    }

    # YAML

    if os.path.exists("config.development.yaml"):

        with open("config.development.yaml") as f:

            yaml_cfg = yaml.safe_load(f) or {}

        config.update(yaml_cfg)

    # .env

    if os.getenv("PORT"):
        config["port"] = os.getenv("PORT")

    if os.getenv("LOG_LEVEL"):
        config["log_level"] = os.getenv("LOG_LEVEL")

    if os.getenv("DEBUG"):
        config["debug"] = os.getenv("DEBUG")

    if os.getenv("API_KEY"):
        config["api_key"] = os.getenv("API_KEY")

    if os.getenv("NUM_WORKERS"):
        config["workers"] = os.getenv("NUM_WORKERS")

    # APP_ env vars

    for k, v in os.environ.items():

        if k.startswith("APP_"):

            config[k[4:].lower()] = v

    # CLI overrides

    if set:

        for item in set:

            if "=" not in item:
                continue

            key, value = item.split("=", 1)

            config[key] = value

    # Type coercion

    config["port"] = int(config["port"])

    config["workers"] = int(config["workers"])

    if isinstance(config["debug"], str):

        config["debug"] = config["debug"].lower() in (
            "true",
            "1",
            "yes",
            "on",
        )

    # Mask secret

    config["api_key"] = "****"

    return config

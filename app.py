from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import time
import uuid
import jwt
from jwt.exceptions import InvalidTokenError

app = FastAPI()

# -----------------------------
# Configuration
# -----------------------------

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

# -----------------------------
# CORS
# -----------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Middleware
# -----------------------------

@app.middleware("http")
async def add_headers(request, call_next):
    start = time.perf_counter()

    response = await call_next(request)

    elapsed = time.perf_counter() - start

    response.headers["X-Request-ID"] = str(uuid.uuid4())
    response.headers["X-Process-Time"] = f"{elapsed:.6f}"

    return response

# -----------------------------
# Models
# -----------------------------

class TokenRequest(BaseModel):
    token: str

# -----------------------------
# Routes
# -----------------------------

@app.get("/")
def home():
    return {
        "message": "Metrics API is running."
    }


@app.get("/stats")
def stats(values: str = Query(...)):
    try:
        numbers = [int(x.strip()) for x in values.split(",") if x.strip()]
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={
                "error": "values must contain integers only"
            }
        )

    if not numbers:
        return JSONResponse(
            status_code=400,
            content={
                "error": "No values supplied"
            }
        )

    return {
        "email": EMAIL,
        "count": len(numbers),
        "sum": sum(numbers),
        "min": min(numbers),
        "max": max(numbers),
        "mean": sum(numbers) / len(numbers),
    }


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
            }
        )

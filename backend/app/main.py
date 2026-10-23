import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.routes import analytics, auth, model, monitoring, prediction, transactions
from backend.app.authentication import SESSION_COOKIE_NAME, is_session_valid
from backend.app.config.settings import (
    ALLOWED_ORIGINS,
    AUTH_PASSWORD,
    AUTH_PASSWORD_GENERATED,
    AUTH_USERNAME,
)
from backend.app.database.database import initialize_database

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if AUTH_PASSWORD_GENERATED:
        logger.warning(
            "Local development login — username: %s | password: %s "
            "(set FRAUD_AUTH_USERNAME, FRAUD_AUTH_PASSWORD, and FRAUD_AUTH_SECRET to configure your own)",
            AUTH_USERNAME,
            AUTH_PASSWORD,
        )
    yield


app = FastAPI(
    title="Fraud Detection API",
    version="1.0.0",
    description="Fraud scoring and transaction analytics backed by the trained PaySim model.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(auth.router)
app.include_router(prediction.router)
app.include_router(transactions.router)
app.include_router(analytics.router)
app.include_router(monitoring.router)
app.include_router(model.router)

initialize_database()

PUBLIC_API_PATHS = {"/api/health", "/api/auth/login", "/api/auth/session", "/api/auth/logout"}


@app.middleware("http")
async def require_api_session(request: Request, call_next):
    if (
        request.url.path.startswith("/api/")
        and request.url.path not in PUBLIC_API_PATHS
        and request.method != "OPTIONS"
        and not is_session_valid(request.cookies.get(SESSION_COOKIE_NAME))
    ):
        return JSONResponse(status_code=401, content={"detail": "Sign in to continue."})
    return await call_next(request)


@app.get("/api/health", tags=["health"])
def health() -> dict:
    from backend.app.config.settings import MODEL_PATH

    return {
        "status": "ok" if MODEL_PATH.is_file() else "degraded",
        "model_available": MODEL_PATH.is_file(),
    }
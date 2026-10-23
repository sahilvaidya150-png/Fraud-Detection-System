import os
from pathlib import Path
import secrets

PROJECT_ROOT = Path(os.getenv("FRAUD_PROJECT_ROOT", Path(__file__).resolve().parents[3])).resolve()
DATASET_PATH = Path(os.getenv("FRAUD_DATASET_PATH", PROJECT_ROOT / "data" / "processed" / "fraud_sampled.csv"))
MODEL_PATH = Path(os.getenv("FRAUD_MODEL_PATH", PROJECT_ROOT / "models" / "production" / "fraud_pipeline.joblib"))
METRICS_PATH = Path(os.getenv("FRAUD_METRICS_PATH", PROJECT_ROOT / "artifacts" / "metrics" / "model_metrics.json"))
DATABASE_PATH = Path(os.getenv("FRAUD_DATABASE_PATH", PROJECT_ROOT / "artifacts" / "predictions.sqlite"))
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "FRAUD_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
AUTH_USERNAME = os.getenv("FRAUD_AUTH_USERNAME", "analyst")
AUTH_PASSWORD_GENERATED = not os.getenv("FRAUD_AUTH_PASSWORD")
AUTH_PASSWORD = os.getenv("FRAUD_AUTH_PASSWORD") or secrets.token_urlsafe(24)
AUTH_SESSION_SECRET = os.getenv("FRAUD_AUTH_SECRET") or secrets.token_urlsafe(48)
AUTH_COOKIE_SECURE = os.getenv("FRAUD_AUTH_COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
AUTH_SESSION_MAX_AGE = 12 * 60 * 60
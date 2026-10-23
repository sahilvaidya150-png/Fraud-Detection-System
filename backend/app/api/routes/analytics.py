import json

from fastapi import APIRouter, HTTPException

from backend.app.config.settings import METRICS_PATH

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview")
def get_overview() -> dict:
    if not METRICS_PATH.is_file():
        raise HTTPException(status_code=503, detail=f"Evaluation metrics not found: {METRICS_PATH}")
    try:
        return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail=f"Unable to read evaluation metrics: {exc}") from exc
from fastapi import APIRouter, HTTPException

from backend.app.ml.model_loader import load_model_artifact

router = APIRouter(prefix="/api/model", tags=["model"])


@router.get("/")
def get_model_status() -> dict:
    try:
        artifact = load_model_artifact()
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "status": "loaded",
        "model": artifact["metrics"]["model"],
        "threshold": artifact["threshold"],
        "features": artifact["features"],
        "created_at": artifact["metrics"]["created_at"],
        "scikit_learn_version": artifact["metrics"]["scikit_learn_version"],
    }
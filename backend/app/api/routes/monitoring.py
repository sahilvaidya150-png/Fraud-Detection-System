from fastapi import APIRouter

from backend.app.database.database import get_prediction_counts, list_predictions

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/")
def get_monitoring_status() -> dict:
    return {
        **get_prediction_counts(),
        "recent_predictions": list_predictions(limit=10),
        "drift_status": "unavailable",
        "drift_note": "No labelled live reference batch is configured; drift is not being estimated.",
    }
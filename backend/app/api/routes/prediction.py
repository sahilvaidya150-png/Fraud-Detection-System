from fastapi import APIRouter, HTTPException

from backend.app.database.database import save_prediction
from backend.app.ml.predictor import predict_transaction
from backend.app.schemas.prediction import PredictionResponse, TransactionInput

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.post("/", response_model=PredictionResponse)
def create_prediction(transaction: TransactionInput) -> PredictionResponse:
    payload = transaction.model_dump()
    try:
        result = predict_transaction(payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=f"Unable to run fraud prediction: {exc}") from exc

    transaction_id = save_prediction(payload, result)
    return PredictionResponse(transaction_id=transaction_id, **result)
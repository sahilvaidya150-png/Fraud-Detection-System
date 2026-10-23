import csv
from functools import lru_cache
from itertools import islice
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from backend.app.config.settings import DATASET_PATH
from backend.app.database.database import list_predictions

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@lru_cache(maxsize=4)
def _count_rows(path: str, _modified_ns: int) -> int:
    with Path(path).open("r", encoding="utf-8", newline="") as stream:
        return sum(1 for _ in csv.DictReader(stream))


@router.get("/")
def get_transactions(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100_000),
) -> dict:
    if not DATASET_PATH.is_file():
        raise HTTPException(status_code=503, detail=f"Transaction dataset not found: {DATASET_PATH}")

    total = _count_rows(str(DATASET_PATH), DATASET_PATH.stat().st_mtime_ns)
    with DATASET_PATH.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(islice(reader, offset, offset + limit))
    items = [
        {
            "transaction_id": f"sample-{offset + index + 1}",
            "step": int(row["step"]),
            "type": row["type"],
            "amount": float(row["amount"]),
            "oldbalanceOrg": float(row["oldbalanceOrg"]),
            "newbalanceOrig": float(row["newbalanceOrig"]),
            "oldbalanceDest": float(row["oldbalanceDest"]),
            "newbalanceDest": float(row["newbalanceDest"]),
            "is_fraud": bool(int(row["isFraud"])),
            "record_source": "dataset",
        }
        for index, row in enumerate(rows)
    ]
    return {
        "items": items,
        "total": total,
        "source": DATASET_PATH.name,
        "stored_predictions": list_predictions(limit=min(limit, 100)),
    }
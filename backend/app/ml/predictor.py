from typing import Any

import pandas as pd

from backend.app.ml.model_loader import load_model_artifact


def predict_transaction(payload: dict[str, Any]) -> dict[str, Any]:
    artifact = load_model_artifact()
    features = artifact["features"]
    row = pd.DataFrame([{feature: payload[feature] for feature in features}])
    probability = float(artifact["pipeline"].predict_proba(row)[0, 1])
    threshold = float(artifact["threshold"])
    return {
        "fraud_probability": probability,
        "threshold": threshold,
        "is_fraud": probability >= threshold,
        "risk_level": "High" if probability >= threshold else "Low",
    }
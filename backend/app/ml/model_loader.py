from functools import lru_cache
from typing import Any

import joblib

from backend.app.config.settings import MODEL_PATH


@lru_cache(maxsize=1)
def _load_model_artifact(path: str, modified_ns: int) -> dict[str, Any]:
    artifact = joblib.load(path)
    if not isinstance(artifact, dict) or not {"pipeline", "threshold", "features"}.issubset(artifact):
        raise ValueError(f"Model artifact has an unexpected format: {path}")
    if not hasattr(artifact["pipeline"], "predict_proba"):
        raise ValueError(f"Model artifact does not contain a probability-capable pipeline: {path}")
    return artifact


def load_model_artifact() -> dict[str, Any]:
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Model artifact not found at {MODEL_PATH}. Run `python -m ml.models.train` from the project root."
        )
    return _load_model_artifact(str(MODEL_PATH), MODEL_PATH.stat().st_mtime_ns)
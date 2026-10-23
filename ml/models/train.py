from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TARGET = "isFraud"
NUMERIC_FEATURES = [
    "step",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
]
CATEGORICAL_FEATURES = ["type"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
RANDOM_STATE = 42
THRESHOLD = 0.5


def _summarize_full_dataset(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Raw dataset not found: {path}")

    class_counts: Counter[str] = Counter()
    transaction_types: Counter[str] = Counter()
    row_count = 0
    for chunk in pd.read_csv(
        path,
        usecols=[TARGET, "type"],
        dtype={TARGET: "int8", "type": "category"},
        chunksize=250_000,
    ):
        row_count += len(chunk)
        class_counts.update({str(key): int(value) for key, value in chunk[TARGET].value_counts().items()})
        transaction_types.update({str(key): int(value) for key, value in chunk["type"].value_counts().items()})

    if not row_count or set(class_counts) != {"0", "1"}:
        raise ValueError(f"Expected a non-empty binary target column '{TARGET}' in {path}")
    return {
        "rows": row_count,
        "target": TARGET,
        "class_counts": dict(class_counts),
        "fraud_rate": class_counts["1"] / row_count,
        "transaction_type_counts": dict(transaction_types),
    }


def train_model(
    data_path: Path | str | None = None,
    raw_data_path: Path | str | None = None,
    model_path: Path | str | None = None,
    metrics_path: Path | str | None = None,
) -> dict[str, Any]:
    data_path = Path(data_path or PROJECT_ROOT / "data" / "processed" / "fraud_sampled.csv")
    raw_data_path = Path(raw_data_path or PROJECT_ROOT / "data" / "raw" / "PS_20174392719_1491204439457_log.csv")
    model_path = Path(model_path or PROJECT_ROOT / "models" / "production" / "fraud_pipeline.joblib")
    metrics_path = Path(metrics_path or PROJECT_ROOT / "artifacts" / "metrics" / "model_metrics.json")

    if not data_path.is_file():
        raise FileNotFoundError(f"Training dataset not found: {data_path}")
    required_columns = FEATURES + [TARGET]
    available_columns = pd.read_csv(data_path, nrows=0).columns
    missing_columns = sorted(set(required_columns) - set(available_columns))
    if missing_columns:
        raise ValueError(f"Training dataset is missing required columns: {', '.join(missing_columns)}")

    data = pd.read_csv(data_path, usecols=required_columns)
    if data.empty:
        raise ValueError(f"Training dataset is empty: {data_path}")
    if data[required_columns].isna().any().any():
        missing = data[required_columns].isna().sum()
        missing = {key: int(value) for key, value in missing[missing > 0].items()}
        raise ValueError(f"Training data contains missing feature/target values: {missing}")
    if not set(data[TARGET].unique()).issubset({0, 1}) or data[TARGET].nunique() != 2:
        raise ValueError(f"'{TARGET}' must contain both binary classes 0 and 1")
    if (data[NUMERIC_FEATURES] < 0).any().any():
        raise ValueError("Training data contains negative values in non-negative transaction features")
    if not np.isfinite(data[NUMERIC_FEATURES].to_numpy(dtype=float)).all():
        raise ValueError("Training data contains non-finite numeric feature values")

    class_counts = data[TARGET].value_counts().sort_index()
    x_train, x_test, y_train, y_test = train_test_split(
        data[FEATURES],
        data[TARGET].astype("int8"),
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=data[TARGET],
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", StandardScaler(), NUMERIC_FEATURES),
            ("categorical", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )
    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )
    pipeline.fit(x_train, y_train)
    probabilities = pipeline.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= THRESHOLD).astype("int8")
    matrix = confusion_matrix(y_test, predictions, labels=[0, 1])

    full_dataset = _summarize_full_dataset(raw_data_path)
    report: dict[str, Any] = {
        "model": "class-weighted logistic regression",
        "threshold": THRESHOLD,
        "features": FEATURES,
        "random_state": RANDOM_STATE,
        "training_dataset": str(data_path.relative_to(PROJECT_ROOT)) if data_path.is_relative_to(PROJECT_ROOT) else str(data_path),
        "training_rows": int(len(data)),
        "training_class_counts": {str(key): int(value) for key, value in class_counts.items()},
        "evaluation": {
            "method": "stratified 80/20 holdout from fraud_sampled.csv",
            "rows": int(len(y_test)),
            "class_counts": {str(key): int(value) for key, value in y_test.value_counts().sort_index().items()},
            "metrics": {
                "accuracy": float(accuracy_score(y_test, predictions)),
                "precision": float(precision_score(y_test, predictions, zero_division=0)),
                "recall": float(recall_score(y_test, predictions, zero_division=0)),
                "f1": float(f1_score(y_test, predictions, zero_division=0)),
                "roc_auc": float(roc_auc_score(y_test, probabilities)),
                "average_precision": float(average_precision_score(y_test, probabilities)),
                "confusion_matrix": matrix.tolist(),
            },
            "caveat": (
                "The holdout preserves the downsampled training sample's class prevalence; "
                "precision and average precision are not estimates at the raw dataset's fraud rate."
            ),
        },
        "full_dataset": full_dataset,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scikit_learn_version": sklearn.__version__,
    }
    artifact = {
        "pipeline": pipeline,
        "threshold": THRESHOLD,
        "features": FEATURES,
        "metrics": report,
    }

    model_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_path)
    metrics_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Model artifact: {model_path}")
    print(f"Metrics report: {metrics_path}")
    print(json.dumps(report["evaluation"]["metrics"], indent=2))
    return report


if __name__ == "__main__":
    train_model()

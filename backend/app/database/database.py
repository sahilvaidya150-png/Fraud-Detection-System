import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from backend.app.config.settings import DATABASE_PATH


def _connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                amount REAL NOT NULL,
                fraud_probability REAL NOT NULL,
                is_fraud INTEGER NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )


def save_prediction(payload: dict[str, Any], result: dict[str, Any]) -> int:
    import json

    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO predictions
                (created_at, transaction_type, amount, fraud_probability, is_fraud, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                payload["type"],
                payload["amount"],
                result["fraud_probability"],
                int(result["is_fraud"]),
                json.dumps(payload),
            ),
        )
        return int(cursor.lastrowid)


def get_prediction_counts() -> dict[str, int]:
    with _connect() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS total, COALESCE(SUM(is_fraud), 0) AS flagged FROM predictions"
        ).fetchone()
    return {"total_predictions": int(row["total"]), "flagged_predictions": int(row["flagged"])}


def list_predictions(limit: int = 50) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, created_at, transaction_type, amount, fraud_probability, is_fraud, payload_json
            FROM predictions ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "transaction_id": f"prediction-{row['id']}",
            "created_at": row["created_at"],
            "type": row["transaction_type"],
            "amount": row["amount"],
            "fraud_probability": row["fraud_probability"],
            "is_fraud": bool(row["is_fraud"]),
            "step": json.loads(row["payload_json"])["step"],
            "record_source": "prediction",
        }
        for row in rows
    ]
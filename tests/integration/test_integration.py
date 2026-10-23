import pytest
from fastapi.testclient import TestClient

from backend.app.database import database
from backend.app.main import app
from backend.app.config.settings import AUTH_PASSWORD, AUTH_USERNAME

VALID_TRANSACTION = {
    "step": 400,
    "type": "CASH_OUT",
    "amount": 150000.0,
    "oldbalanceOrg": 200000.0,
    "newbalanceOrig": 50000.0,
    "oldbalanceDest": 0.0,
    "newbalanceDest": 0.0,
}


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "predictions.sqlite")
    database.initialize_database()
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/auth/login",
            json={"username": AUTH_USERNAME, "password": AUTH_PASSWORD},
        )
        assert response.status_code == 200
        yield test_client


def test_health_endpoint_reports_model_readiness(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model_available": True}


def test_prediction_is_scored_and_persisted(client: TestClient) -> None:
    response = client.post("/api/predictions/", json=VALID_TRANSACTION)
    assert response.status_code == 200
    result = response.json()
    assert 0 <= result["fraud_probability"] <= 1
    assert result["threshold"] == 0.5
    assert isinstance(result["is_fraud"], bool)
    assert result["risk_level"] in {"Low", "High"}
    activity = client.get("/api/monitoring/").json()
    assert activity["total_predictions"] >= 1


def test_invalid_prediction_is_rejected(client: TestClient) -> None:
    invalid = {**VALID_TRANSACTION, "amount": -1}
    assert client.post("/api/predictions/", json=invalid).status_code == 422
    out_of_range = {**VALID_TRANSACTION, "step": 744}
    assert client.post("/api/predictions/", json=out_of_range).status_code == 422


def test_transaction_history_uses_processed_dataset(client: TestClient) -> None:
    response = client.get("/api/transactions/?limit=3")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 3
    assert body["total"] > 3
    assert body["source"] == "fraud_sampled.csv"
    assert all(isinstance(row["is_fraud"], bool) for row in body["items"])
    assert "stored_predictions" in body


def test_saved_evaluation_metrics_are_available(client: TestClient) -> None:
    response = client.get("/api/analytics/overview")
    assert response.status_code == 200
    report = response.json()
    assert report["full_dataset"]["target"] == "isFraud"
    assert report["full_dataset"]["rows"] == 6_362_620
    assert report["evaluation"]["metrics"]["average_precision"] > 0
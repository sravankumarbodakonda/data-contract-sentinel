from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "UP"}


def test_diff_endpoint_returns_risk_score_and_formula():
    response = client.get("/api/contracts/diff")
    assert response.status_code == 200
    body = response.json()
    assert body["total_risk_score"] > 0
    assert "risk_formula" in body
    assert len(body["migration_recommendations"]) > 0


def test_replay_endpoint_surfaces_violations():
    response = client.get("/api/contracts/replay")
    assert response.status_code == 200
    body = response.json()
    assert body["records_checked"] == 4
    assert body["records_with_violations"] > 0

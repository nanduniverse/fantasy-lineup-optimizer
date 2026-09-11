from fastapi.testclient import TestClient

from app.data.sample_data import SAMPLE_REQUEST
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sample_recommendation():
    response = client.post("/api/recommend-lineup", json=SAMPLE_REQUEST)
    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["recommended"]["win_probability"] <= 1
    assert len(body["recommended"]["starters"]) == 7


def test_invalid_requests():
    from copy import deepcopy
    cases = []
    duplicate = deepcopy(SAMPLE_REQUEST)
    duplicate["opponent_lineup"][1] = duplicate["opponent_lineup"][0]
    cases.append((duplicate, 422))
    illegal = deepcopy(SAMPLE_REQUEST)
    for p in illegal["opponent_lineup"]:
        p["position"] = "QB"
    cases.append((illegal, 400))
    empty = deepcopy(SAMPLE_REQUEST)
    empty["rules"] = dict(qb=0, rb=0, wr=0, te=0, flex=0)
    cases.append((empty, 422))
    negative_seed = deepcopy(SAMPLE_REQUEST)
    negative_seed["seed"] = -1
    cases.append((negative_seed, 422))
    for payload, status in cases:
        assert client.post("/api/recommend-lineup", json=payload).status_code == status

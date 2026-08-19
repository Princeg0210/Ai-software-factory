import json
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_ingest_issue_and_query_status():
    with open("mock-payload.json", "r") as f:
        payload = json.load(f)

    # Ingest issue
    response = client.post("/api/v1/factory/issues", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["issue_id"] == "django-13933"
    assert data["status"] == "INIT"

    # Query status
    status_response = client.get("/api/v1/factory/issues/django-13933/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["issue_id"] == "django-13933"
    assert len(status_data["history"]) >= 1

def test_human_review_submission():
    # Submit review
    review_payload = {
        "decision": "APPROVED",
        "reviewer_name": "Senior Staff Architect",
        "comments": "Patch looks solid and verified."
    }
    response = client.post("/api/v1/factory/issues/django-13933/review", json=review_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVED"
    assert data["new_state"] == "TERMINAL_SUCCESS"

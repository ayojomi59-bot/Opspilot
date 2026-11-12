from fastapi.testclient import TestClient
from opspilot.database import Database
from opspilot.service import OpsPilotService
from opspilot.main import create_app


def client(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    return TestClient(create_app(OpsPilotService(db)))


def test_health(client_fixture=None, tmp_path=None):
    # Kept as a direct test to avoid relying on global application state.
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as folder:
        c = TestClient(create_app(OpsPilotService(Database(str(Path(folder) / "db.sqlite")))))
        assert c.get("/health").json()["status"] == "ok"


def test_crm_lookup_is_demo_data_and_completes(tmp_path):
    c = client(tmp_path)
    response = c.post("/api/v1/runs", json={"message": "Look up customer Amina"})
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["results"][0]["output"]["source"] == "local_demo_data"
    assert body["results"][0]["output"]["matches"][0]["name"] == "Amina Yusuf"


def test_task_requires_approval_then_creates_task(tmp_path):
    c = client(tmp_path)
    response = c.post("/api/v1/runs", json={"message": "Create a follow-up task"})
    assert response.status_code == 201
    action = response.json()["results"][0]
    assert action["status"] == "awaiting_approval"
    approval_id = action["approval_id"]
    approved = c.post(f"/api/v1/approvals/{approval_id}/approve", json={"note": "Reviewed"})
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["result"]["status"] == "open"


def test_rejected_task_is_not_created(tmp_path):
    c = client(tmp_path)
    response = c.post("/api/v1/runs", json={"message": "Create a task"})
    approval_id = response.json()["results"][0]["approval_id"]
    rejected = c.post(f"/api/v1/approvals/{approval_id}/reject", json={})
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert "rejected" in rejected.json()["result"]["message"]


def test_email_is_never_sent(tmp_path):
    c = client(tmp_path)
    response = c.post("/api/v1/runs", json={"message": "Draft an email to the customer"})
    result = next(item for item in response.json()["results"] if item["tool"] == "email_draft")
    assert result["tool"] == "email_draft"
    assert result["output"]["sent"] is False
    assert result["output"]["status"] == "draft_only"


def test_invalid_request_is_rejected(tmp_path):
    c = client(tmp_path)
    assert c.post("/api/v1/runs", json={"message": "x"}).status_code == 422

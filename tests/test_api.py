import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import create_tables

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    create_tables()


def test_upload_creates_pending_job():
    csv_content = "txn_id,date,merchant,amount,currency,status,category,account_id,notes\nTXN1,04-09-2024,Flipkart,100,INR,SUCCESS,Shopping,ACC001,\n"
    response = client.post("/jobs/upload", files={"file": ("test.csv", csv_content, "text/csv")})
    assert response.status_code == 201
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"


def test_upload_rejects_non_csv():
    response = client.post("/jobs/upload", files={"file": ("test.txt", b"hello", "text/plain")})
    assert response.status_code == 400


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

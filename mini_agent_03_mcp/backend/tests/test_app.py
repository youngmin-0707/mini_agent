from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_reports_mcp_backend() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["stage"] == "mini_agent_03_mcp"
    assert response.json()["mcp_transport"] == "streamable-http"


def test_mcp_run_rejects_blank_question_without_network() -> None:
    response = client.post("/api/mcp/run", json={"question": ""})

    assert response.status_code == 422

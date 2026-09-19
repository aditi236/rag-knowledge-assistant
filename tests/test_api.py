import anthropic
import httpx
import pytest
from fastapi.testclient import TestClient

from app.api import app, get_pipeline


@pytest.fixture
def client(pipeline):
    app.dependency_overrides[get_pipeline] = lambda: pipeline
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_upload_then_ask_returns_cited_answer(client):
    upload = client.post("/documents", files={"file": ("leave.md", b"Employees receive 25 days of annual leave.")})
    assert upload.status_code == 201 and upload.json()["chunks"] == 1
    assert client.get("/documents").json() == {"leave.md": 1}
    body = client.post("/ask", json={"question": "How many days of annual leave?"}).json()
    assert body["grounded"] and body["citations"][0]["source"] == "leave.md"


def test_unsupported_file_type_is_rejected(client):
    assert client.post("/documents", files={"file": ("x.exe", b"nope")}).status_code == 415


def test_empty_file_is_rejected(client):
    assert client.post("/documents", files={"file": ("empty.txt", b"   ")}).status_code == 422


def test_oversized_file_is_rejected(client):
    big = b"a" * (5 * 1024 * 1024 + 1)
    assert client.post("/documents", files={"file": ("big.txt", big)}).status_code == 413


def test_empty_question_fails_validation(client):
    assert client.post("/ask", json={"question": ""}).status_code == 422


def test_rate_limit_from_model_maps_to_429(client, pipeline):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(429, request=request)

    def boom(question):
        raise anthropic.RateLimitError("slow down", response=response, body=None)

    pipeline.ask = boom
    assert client.post("/ask", json={"question": "hi"}).status_code == 429

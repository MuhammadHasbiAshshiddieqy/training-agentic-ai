from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    print("GET /health ->", response.status_code, response.json())


def test_ask_tanpa_header_ditolak():
    response = client.post("/ask", json={"question": "Apa itu RAG?"})
    assert response.status_code == 401
    print("POST /ask (tanpa header) ->", response.status_code, response.json())


def test_ask_dengan_header_valid():
    response = client.post(
        "/ask",
        json={"question": "Apa itu RAG?"},
        headers={"x-api-key": "rahasia-latihan"},
    )
    assert response.status_code == 200
    print("POST /ask (header valid) ->", response.status_code, response.json())


def test_documents_404():
    response = client.get("/documents/999")
    assert response.status_code == 404
    print("GET /documents/999 ->", response.status_code, response.json())

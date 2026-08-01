"""
Modul 3 - FastAPI App di dalam Docker + PostgreSQL(pgvector) + Redis + Gemini (LENGKAP)
AI Knowledge Assistant - Human Initiative

App ini dijalankan lewat Docker Compose (lihat README.md satu folder di atas),
supaya app, database, dan cache hidup bersamaan di jaringan Docker yang sama.

Endpoint /ask butuh header `x-api-key: rahasia-latihan` (lihat verify_api_key).
"""
import asyncio
import os
import time
from typing import List

import psycopg
import redis
from fastapi import FastAPI, Header, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="AI Knowledge Assistant - Modul 3", version="2.0.0")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ai_user:ai_pass@localhost:5432/ai_knowledge")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
EXPECTED_API_KEY = os.getenv("EXPECTED_API_KEY", "rahasia-latihan")


# ---------------------------------------------------------------------------
# Pydantic Models (dari Modul 2)
# ---------------------------------------------------------------------------
class DocumentQuery(BaseModel):
    question: str = Field(..., min_length=3, description="Pertanyaan dari user")
    max_results: int = Field(default=3, ge=1, le=10, description="Jumlah dokumen relevan yang dicari")

    @field_validator("question")
    @classmethod
    def question_must_have_letters(cls, v: str) -> str:
        if not any(c.isalpha() for c in v):
            raise ValueError("Pertanyaan harus mengandung huruf, bukan hanya simbol/spasi")
        return v


class DocumentAnswer(BaseModel):
    question: str
    answer: str
    sources: List[str] = []
    latency_ms: int


# ---------------------------------------------------------------------------
# Dependency Injection (dari Modul 2)
# ---------------------------------------------------------------------------
def verify_api_key(x_api_key: str | None = Header(default=None)) -> str:
    if x_api_key is None or x_api_key != EXPECTED_API_KEY:
        raise HTTPException(status_code=401, detail="Header x-api-key tidak ada atau tidak valid")
    return x_api_key


# ---------------------------------------------------------------------------
# Endpoints dari Modul 2
# ---------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/ask", response_model=DocumentAnswer)
async def ask_question(payload: DocumentQuery, api_key: str = Depends(verify_api_key)):
    start = time.perf_counter()
    await asyncio.sleep(1.5)
    answer_text = f"Ini jawaban simulasi untuk pertanyaan: \"{payload.question}\""
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return DocumentAnswer(question=payload.question, answer=answer_text, sources=[], latency_ms=elapsed_ms)


@app.get("/ask/stream")
async def ask_question_stream(q: str):
    async def word_stream():
        answer = f"Ini jawaban simulasi (streaming) untuk pertanyaan: {q}"
        for word in answer.split(" "):
            yield word + " "
            await asyncio.sleep(0.15)
    return StreamingResponse(word_stream(), media_type="text/plain")


FAKE_DOCUMENTS = {
    1: "SOP Distribusi Logistik Bantuan",
    2: "Kebijakan Pengadaan Barang",
}


@app.get("/documents/{doc_id}")
async def get_document(doc_id: int):
    if doc_id not in FAKE_DOCUMENTS:
        raise HTTPException(status_code=404, detail=f"Dokumen dengan id {doc_id} tidak ditemukan")
    return {"id": doc_id, "title": FAKE_DOCUMENTS[doc_id]}


# ---------------------------------------------------------------------------
# MODUL 3 — Konektivitas Docker (Postgres + Redis + Gemini)
# ---------------------------------------------------------------------------
@app.get("/db-check")
async def db_check():
    """
    Cek koneksi ke PostgreSQL dan pastikan extension pgvector aktif.
    Dijalankan sinkron di dalam fungsi async (koneksi singkat, cukup cepat
    untuk contoh ini) — di endpoint dengan traffic tinggi, pertimbangkan
    connection pool async (mis. psycopg_pool / asyncpg).
    """
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()

                # Aktifkan pgvector sekali di sini (idempotent — aman dipanggil berulang)
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                conn.commit()

        return {"database": "connected", "pgvector": "enabled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal terhubung ke database: {e}")


@app.get("/cache-check")
async def cache_check():
    """Cek koneksi ke Redis dengan menulis lalu membaca satu key."""
    try:
        r = redis.from_url(REDIS_URL, socket_connect_timeout=5)
        now = str(time.time())
        r.set("healthcheck", now, ex=60)  # expire otomatis dalam 60 detik
        value = r.get("healthcheck")
        return {"cache": "connected", "healthcheck_value": value.decode() if value else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal terhubung ke Redis: {e}")


@app.get("/gemini-test")
async def gemini_test():
    """
    Panggilan sederhana ke Gemini API untuk memastikan API key valid
    SEBELUM masuk ke pipeline embedding penuh di Modul 4.
    """
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY belum di-set. Salin .env.example ke .env dan isi API key Anda.",
        )
    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-flash-latest")
        response = model.generate_content("Halo, apa itu RAG? Jawab singkat dalam 1 kalimat.")
        return {"prompt": "Halo, apa itu RAG?", "response": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memanggil Gemini API: {e}")

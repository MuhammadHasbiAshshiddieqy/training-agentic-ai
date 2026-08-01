"""
Modul 4 - FastAPI App (lanjutan Modul 3) + Endpoint Pencarian Semantik (LENGKAP)
AI Knowledge Assistant - Human Initiative

Jalankan ingest.py DULU untuk mengisi tabel `documents`, baru endpoint
/search di sini bisa mengembalikan hasil.
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
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content("Halo, apa itu RAG? Jawab singkat dalam 1 kalimat.")
        return {"prompt": "Halo, apa itu RAG?", "response": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memanggil Gemini API: {e}")


# ---------------------------------------------------------------------------
# MODUL 4 — Pencarian semantik di atas data hasil ingestion
# ---------------------------------------------------------------------------
class SearchResult(BaseModel):
    content: str
    source_file: str
    chunk_index: int
    distance: float


@app.get("/search", response_model=List[SearchResult])
async def search(query: str, limit: int = 3):
    """
    Mencari potongan dokumen paling relevan secara makna terhadap `query`.

    Jalankan `python ingest.py` terlebih dahulu supaya tabel `documents`
    sudah terisi. distance lebih kecil = lebih relevan (cosine distance).
    """
    from ingest import embed_text  # reuse fungsi embedding yang sama dengan ingest.py

    try:
        query_embedding = embed_text(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membuat embedding untuk query: {e}")

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT content, source_file, chunk_index, embedding <=> %s::vector AS distance
                    FROM documents
                    ORDER BY distance ASC
                    LIMIT %s;
                    """,
                    (query_embedding, limit),
                )
                rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal melakukan pencarian: {e}")

    return [
        SearchResult(content=r[0], source_file=r[1], chunk_index=r[2], distance=r[3])
        for r in rows
    ]


# ---------------------------------------------------------------------------
# BONUS — RAG penuh: Retrieval (pgvector) + Generation (Gemini) digabung.
# Preview sederhana untuk Modul 5 (belum ada reranking/metadata filtering).
# ---------------------------------------------------------------------------
class RagAnswer(BaseModel):
    question: str
    answer: str
    sources: List[SearchResult]
    latency_ms: int


@app.get("/rag", response_model=RagAnswer)
async def rag(query: str, limit: int = 3):
    """
    Alur lengkap RAG dalam satu endpoint:
      1. Retrieval — cari `limit` chunk paling relevan di pgvector (sama seperti /search)
      2. Augmentation — susun chunk-chunk itu jadi konteks di dalam prompt
      3. Generation — kirim prompt + konteks ke Gemini, kembalikan jawaban akhir

    Beda dengan /ask (yang jawabannya masih simulasi), endpoint ini benar-benar
    menjawab berdasarkan isi dokumen yang sudah di-ingest. Jalankan ingest.py
    dulu supaya ada data untuk diambil.
    """
    start = time.perf_counter()

    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY belum di-set. Salin .env.example ke .env dan isi API key Anda.",
        )

    from ingest import embed_text  # reuse fungsi embedding yang sama dengan ingest.py

    try:
        query_embedding = embed_text(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membuat embedding untuk query: {e}")

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT content, source_file, chunk_index, embedding <=> %s::vector AS distance
                    FROM documents
                    ORDER BY distance ASC
                    LIMIT %s;
                    """,
                    (query_embedding, limit),
                )
                rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal melakukan pencarian: {e}")

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Tidak ada dokumen ditemukan. Jalankan 'docker compose exec app python ingest.py' dulu.",
        )

    sources = [
        SearchResult(content=r[0], source_file=r[1], chunk_index=r[2], distance=r[3])
        for r in rows
    ]

    context = "\n\n---\n\n".join(s.content for s in sources)
    prompt = (
        "Kamu adalah asisten yang menjawab HANYA berdasarkan konteks di bawah ini. "
        "Kalau jawabannya tidak ada di konteks, katakan terus terang tidak tahu — "
        "jangan mengarang.\n\n"
        f"KONTEKS:\n{context}\n\n"
        f"PERTANYAAN: {query}\n\n"
        "JAWABAN (singkat dan jelas):"
    )

    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        answer_text = response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memanggil Gemini API: {e}")

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return RagAnswer(question=query, answer=answer_text, sources=sources, latency_ms=elapsed_ms)

"""
Modul 7 - FastAPI App (lanjutan Modul 4) + Tool Calling / Function Calling (LENGKAP)
AI Knowledge Assistant - Human Initiative

Menambahkan endpoint /chat yang memakai Gemini function calling untuk
memanggil tool (cek_stok_barang, cari_dokumen) sesuai kebutuhan pertanyaan
user. Lihat tools.py untuk definisi tool-nya.

Catatan SDK: memakai `google-genai` (paket resmi terbaru).
"""
import asyncio
import os
import time
from typing import List, Any

import psycopg
import redis
from fastapi import FastAPI, Header, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from google import genai
from google.genai import types

from tools import ALL_TOOLS, TOOL_REGISTRY

app = FastAPI(title="AI Knowledge Assistant - Modul 7", version="7.0.0")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ai_user:ai_pass@localhost:5432/ai_knowledge")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
EXPECTED_API_KEY = os.getenv("EXPECTED_API_KEY", "rahasia-latihan")
GEMINI_MODEL = "gemini-3.6-flash"  # Gemini 3.x - jauh lebih andal untuk tool calling dibanding versi <3


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


def verify_api_key(x_api_key: str | None = Header(default=None)) -> str:
    if x_api_key is None or x_api_key != EXPECTED_API_KEY:
        raise HTTPException(status_code=401, detail="Header x-api-key tidak ada atau tidak valid")
    return x_api_key


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
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                conn.commit()
        return {"database": "connected", "pgvector": "enabled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal terhubung ke database: {e}")


@app.get("/cache-check")
async def cache_check():
    try:
        r = redis.from_url(REDIS_URL, socket_connect_timeout=5)
        now = str(time.time())
        r.set("healthcheck", now, ex=60)
        value = r.get("healthcheck")
        return {"cache": "connected", "healthcheck_value": value.decode() if value else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal terhubung ke Redis: {e}")


@app.get("/gemini-test")
async def gemini_test():
    """
    Panggilan sederhana ke Gemini API (SDK google-genai) untuk memastikan
    API key valid SEBELUM masuk ke pipeline embedding penuh di Modul 4.
    """
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY belum di-set. Salin .env.example ke .env dan isi API key Anda.",
        )
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents="Halo, apa itu RAG? Jawab singkat dalam 1 kalimat.",
        )
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
# MODUL 7 — Tool Calling / Function Calling
# ---------------------------------------------------------------------------
class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1)


class ToolCallLog(BaseModel):
    name: str
    args: dict
    result: Any


class ChatResponse(BaseModel):
    answer: str
    tools_called: List[ToolCallLog] = []


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatMessage, api_key: str = Depends(verify_api_key)):
    """
    Endpoint chat dengan tool calling. Alur:
      1. Kirim pesan user ke Gemini beserta daftar tool yang tersedia
      2. Kalau Gemini minta panggil tool, kita EKSEKUSI tool itu sendiri
         (Gemini tidak pernah menjalankan kode secara langsung)
      3. Kirim hasil eksekusi kembali ke Gemini untuk disusun jadi jawaban
         akhir dalam bahasa natural
    """
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY belum di-set")

    client = genai.Client(api_key=GEMINI_API_KEY)
    config = types.GenerateContentConfig(tools=[ALL_TOOLS])

    contents = [types.Content(role="user", parts=[types.Part(text=payload.message)])]

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL, contents=contents, config=config,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memanggil Gemini API: {e}")

    tools_called: List[ToolCallLog] = []

    if response.function_calls:
        # Simpan giliran model (berisi permintaan function call) ke history
        contents.append(response.candidates[0].content)

        function_response_parts = []
        for fc in response.function_calls:
            fn = TOOL_REGISTRY.get(fc.name)
            args = dict(fc.args) if fc.args else {}
            if fn is None:
                result = {"error": f"Tool '{fc.name}' tidak dikenali"}
            else:
                try:
                    result = fn(**args)
                except Exception as e:
                    result = {"error": f"Tool '{fc.name}' gagal dieksekusi: {e}"}

            tools_called.append(ToolCallLog(name=fc.name, args=args, result=result))
            # Gemini 3.x memvalidasi id, name, dan jumlah response harus cocok
            # dengan function_calls sebelumnya — Part.from_function_response()
            # tidak punya parameter id, jadi kita bangun FunctionResponse
            # langsung supaya id ikut terkirim balik (aman juga untuk model <3
            # yang tidak mewajibkan id).
            function_response_parts.append(
                types.Part(function_response=types.FunctionResponse(
                    id=getattr(fc, "id", None),
                    name=fc.name,
                    response={"result": result},
                ))
            )

        contents.append(types.Content(role="user", parts=function_response_parts))

        try:
            final_response = client.models.generate_content(
                model=GEMINI_MODEL, contents=contents, config=config,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gagal mendapat jawaban akhir dari Gemini: {e}")

        # Model kadang memutuskan memanggil tool LAGI di putaran kedua alih-alih
        # memberi jawaban teks — dalam kasus itu final_response.text bernilai
        # None. /chat sengaja hanya menangani SATU putaran tool calling (lihat
        # Modul 8 untuk loop multi-langkah), jadi di sini kita beri pesan yang
        # jelas alih-alih membiarkan ChatResponse(answer=None) crash 500.
        answer_text = final_response.text or (
            "Model masih ingin memanggil tool tambahan setelah putaran pertama — "
            "/chat di sini hanya menangani satu putaran tool calling. Coba "
            "endpoint /agent di Modul 8 untuk kasus yang butuh beberapa "
            "langkah tool calling berurutan."
        )
    else:
        answer_text = response.text

    return ChatResponse(answer=answer_text, tools_called=tools_called)

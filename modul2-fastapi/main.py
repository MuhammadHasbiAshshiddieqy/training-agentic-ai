"""
Modul 2 - FastAPI App (LENGKAP)
AI Knowledge Assistant - Human Initiative

Jalankan dengan:
    uvicorn main:app --reload

Lalu buka http://127.0.0.1:8000/docs untuk mencoba API-nya.
Endpoint /ask butuh header `x-api-key: rahasia-latihan` (lihat TODO 4).
"""
import asyncio
import os
import time
from typing import List

from fastapi import FastAPI, Header, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="AI Knowledge Assistant - Modul 2", version="1.0.0")

EXPECTED_API_KEY = os.getenv("EXPECTED_API_KEY", "rahasia-latihan")


# ---------------------------------------------------------------------------
# Pydantic Models
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
# Dependency Injection — dipakai berulang di endpoint manapun yang perlu
# otentikasi sederhana. Pola yang sama dipakai lagi di Modul 3 untuk
# menyediakan koneksi DB/Redis ke endpoint yang membutuhkannya.
# ---------------------------------------------------------------------------
def verify_api_key(x_api_key: str | None = Header(default=None)) -> str:
    if x_api_key is None or x_api_key != EXPECTED_API_KEY:
        raise HTTPException(status_code=401, detail="Header x-api-key tidak ada atau tidak valid")
    return x_api_key


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/ask", response_model=DocumentAnswer)
async def ask_question(payload: DocumentQuery, api_key: str = Depends(verify_api_key)):
    """
    Endpoint utama AI Knowledge Assistant.

    Untuk saat ini jawabannya masih simulasi (dummy) — di Modul 4 endpoint ini
    akan disambungkan ke pencarian semantik sungguhan (RAG), dan di Modul 5
    disempurnakan menjadi Production RAG.
    """
    start = time.perf_counter()

    # Simulasi panggilan LLM yang butuh waktu (mis. 1.5 detik).
    # Karena pakai `await asyncio.sleep(...)`, event loop FastAPI tetap bisa
    # melayani request lain SELAMA endpoint ini menunggu — coba panggil
    # endpoint ini beberapa kali bersamaan untuk membuktikannya.
    await asyncio.sleep(1.5)

    answer_text = f"Ini jawaban simulasi untuk pertanyaan: \"{payload.question}\""

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return DocumentAnswer(
        question=payload.question,
        answer=answer_text,
        sources=[],
        latency_ms=elapsed_ms,
    )


@app.get("/ask/stream")
async def ask_question_stream(q: str):
    """
    BONUS: versi streaming dari /ask — mengembalikan jawaban kata demi kata,
    mensimulasikan efek "mengetik" seperti ChatGPT/Claude. Pola ini akan
    dipakai lagi saat mengintegrasikan LLM sungguhan di Modul 5.
    """
    async def word_stream():
        answer = f"Ini jawaban simulasi (streaming) untuk pertanyaan: {q}"
        for word in answer.split(" "):
            yield word + " "
            await asyncio.sleep(0.15)

    return StreamingResponse(word_stream(), media_type="text/plain")


# ---------------------------------------------------------------------------
# Contoh error handling eksplisit dengan HTTPException (path parameter +
# error 404 yang jelas, bukan error 500 generik). Dictionary di bawah ini
# simulasi sederhana — diganti dengan query database sungguhan di Modul 3/4.
# ---------------------------------------------------------------------------
FAKE_DOCUMENTS = {
    1: "SOP Distribusi Logistik Bantuan",
    2: "Kebijakan Pengadaan Barang",
}


@app.get("/documents/{doc_id}")
async def get_document(doc_id: int):
    if doc_id not in FAKE_DOCUMENTS:
        raise HTTPException(status_code=404, detail=f"Dokumen dengan id {doc_id} tidak ditemukan")
    return {"id": doc_id, "title": FAKE_DOCUMENTS[doc_id]}


"""
Modul 5 - FastAPI App (lanjutan Modul 4) + Production RAG (LENGKAP)
AI Knowledge Assistant - Human Initiative

Menyempurnakan endpoint /search dari Modul 4 dengan tiga teknik Production RAG:
  1. Metadata filtering — filter hasil berdasarkan `category` dokumen
  2. Reranking — retrieve lebih banyak kandidat (top-K), lalu Gemini menilai
     ulang relevansinya secara lebih presisi untuk ambil top-N terbaik
  3. Context management — gabungkan potongan terpilih jadi satu context
     string yang deduplikasi & dibatasi budget karakter, siap dipakai LLM

Catatan SDK: memakai `google-genai`.
"""
import asyncio
import hashlib
import os
import time
from typing import List

import psycopg
import redis
from fastapi import FastAPI, Header, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from google import genai
from google.genai import types

app = FastAPI(title="AI Knowledge Assistant - Modul 5", version="5.0.0")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ai_user:ai_pass@localhost:5432/ai_knowledge")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
EXPECTED_API_KEY = os.getenv("EXPECTED_API_KEY", "rahasia-latihan")
GEMINI_MODEL = "gemini-3.6-flash"  # Gemini 3.x - jauh lebih andal untuk tool calling dibanding versi <3

RETRIEVE_TOP_K = 10   # jumlah kandidat awal yang diambil dari vector search
CONTEXT_MAX_CHARS = 2000  # batas karakter total context yang dikirim ke LLM


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
# MODUL 5 — Production RAG: metadata filtering, reranking, context management
# ---------------------------------------------------------------------------
class SearchResult(BaseModel):
    content: str
    source_file: str
    chunk_index: int
    category: str
    distance: float
    relevance_score: float | None = None


class ProductionSearchResponse(BaseModel):
    query: str
    context: str
    sources: List[SearchResult]
    candidates_retrieved: int
    candidates_after_rerank: int


class RerankItem(BaseModel):
    index: int = Field(description="Index kandidat (0-based, sesuai urutan yang diberikan)")
    relevance_score: float = Field(description="Skor relevansi 0-10 terhadap query; makin tinggi makin relevan")


class RerankResponse(BaseModel):
    rankings: List[RerankItem]


def rerank_candidates(query: str, candidates: list[dict], top_n: int) -> list[dict]:
    """
    Reranking — retrieval awal (vector search) cepat tapi kasar. Di sini
    Gemini menilai ulang tiap kandidat secara lebih presisi memakai
    structured output (response_schema), supaya top_n yang terpilih
    benar-benar paling relevan, bukan sekadar paling dekat secara vektor.
    """
    if not candidates:
        return []

    client = genai.Client(api_key=GEMINI_API_KEY)
    candidate_text = "\n".join(
        f"[{i}] {c['content'][:300]}" for i, c in enumerate(candidates)
    )
    prompt = (
        f"Pertanyaan user: \"{query}\"\n\n"
        f"Berikut {len(candidates)} kandidat potongan dokumen (diberi index [0], [1], dst):\n"
        f"{candidate_text}\n\n"
        f"Beri skor relevansi 0-10 untuk SETIAP kandidat terhadap pertanyaan user. "
        f"Kandidat yang tidak relevan sama sekali beri skor rendah (0-2)."
    )

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RerankResponse,
        ),
    )
    result: RerankResponse = response.parsed

    valid_rankings = [r for r in result.rankings if 0 <= r.index < len(candidates)]
    sorted_rankings = sorted(valid_rankings, key=lambda r: r.relevance_score, reverse=True)

    reranked = []
    for r in sorted_rankings[:top_n]:
        candidate = dict(candidates[r.index])
        candidate["relevance_score"] = r.relevance_score
        reranked.append(candidate)
    return reranked


def assemble_context(chunks: list[dict], max_chars: int = CONTEXT_MAX_CHARS) -> str:
    """
    Context management — gabungkan potongan terpilih jadi satu string context:
      - Deduplikasi: chunk dengan isi identik (mis. muncul dari overlap
        ingestion) hanya dimasukkan sekali
      - Budget karakter: berhenti menambah chunk begitu total mendekati
        max_chars, supaya prompt ke LLM tidak membengkak tanpa kendali
      - Tiap potongan diberi label sumbernya untuk sitasi
    """
    seen_hashes = set()
    parts = []
    total = 0

    for c in chunks:
        content_hash = hashlib.md5(c["content"].encode()).hexdigest()
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)

        remaining = max_chars - total
        if remaining <= 50:  # sisa ruang terlalu kecil untuk berguna
            break

        text = c["content"][:remaining]
        block = f"[Sumber: {c['source_file']}]\n{text}"
        parts.append(block)
        total += len(text)

    return "\n\n---\n\n".join(parts)


@app.get("/search", response_model=ProductionSearchResponse)
async def search(query: str, limit: int = 3, category: str | None = None):
    """
    Production RAG search — tiga tahap:
      1. Retrieval: ambil RETRIEVE_TOP_K kandidat via vector search
         (opsional difilter `category`)
      2. Rerank: Gemini menilai ulang kandidat, ambil `limit` terbaik
      3. Context assembly: gabungkan jadi satu context siap pakai,
         deduplikasi + dibatasi budget karakter
    """
    from ingest import embed_text

    try:
        query_embedding = embed_text(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membuat embedding untuk query: {e}")

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                if category:
                    cur.execute(
                        """
                        SELECT content, source_file, chunk_index, category,
                               embedding <=> %s::vector AS distance
                        FROM documents
                        WHERE category = %s
                        ORDER BY distance ASC
                        LIMIT %s;
                        """,
                        (query_embedding, category, RETRIEVE_TOP_K),
                    )
                else:
                    cur.execute(
                        """
                        SELECT content, source_file, chunk_index, category,
                               embedding <=> %s::vector AS distance
                        FROM documents
                        ORDER BY distance ASC
                        LIMIT %s;
                        """,
                        (query_embedding, RETRIEVE_TOP_K),
                    )
                rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal melakukan pencarian: {e}")

    candidates = [
        {"content": r[0], "source_file": r[1], "chunk_index": r[2], "category": r[3], "distance": r[4]}
        for r in rows
    ]

    try:
        reranked = rerank_candidates(query, candidates, top_n=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal melakukan reranking: {e}")

    context = assemble_context(reranked)

    return ProductionSearchResponse(
        query=query,
        context=context,
        sources=[SearchResult(**c) for c in reranked],
        candidates_retrieved=len(candidates),
        candidates_after_rerank=len(reranked),
    )

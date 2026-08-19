"""
Modul 10 - FastAPI App (lanjutan Modul 9) + Guardrails & Output Validation (LENGKAP)
AI Knowledge Assistant - Human Initiative

Membawa maju semantic cache dua lapis dari Modul 9 (lihat cache.py) apa
adanya, lalu menambahkan dua lapis guardrail di /chat dan /agent (lihat
guardrails.py):
  1. INPUT guardrail - cek pola prompt injection & batas panjang pesan
     SEBELUM apapun dikirim ke Gemini/Redis sama sekali
  2. OUTPUT guardrail - setelah jawaban akhir didapat, Gemini menilai
     ulang (LLM-as-judge, structured output) apakah jawaban itu GROUNDED
     (didukung context/tool result, bukan karangan) dan SAFE (tidak
     membocorkan instruksi sistem/konten berbahaya)

Interaksi penting dengan cache Modul 9: verdict output guardrail ikut
DISIMPAN di cache bersama jawabannya (lihat cache.py). Cache HIT di
/chat mengembalikan jawaban DAN guardrail dari cache - tidak ada
panggilan Gemini sama sekali (bukan cuma skip generation, tapi juga skip
LLM-as-judge). Catatan penting dari Modul 9 tetap berlaku: jawaban yang
melibatkan tool cek_stok_barang (data transaksional) SENGAJA TIDAK
disimpan ke semantic cache.

Catatan SDK: memakai `google-genai` (paket resmi terbaru).
"""
import asyncio
import os
import time
from typing import List, Any

import psycopg
import redis
from fastapi import FastAPI, Header, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from google import genai
from google.genai import types

from tools import ALL_TOOLS, TOOL_REGISTRY
from agent import Agent
from retrieval import (
    vector_search, keyword_search, rrf_merge, rerank_candidates, assemble_context,
    RETRIEVE_TOP_K, RRF_K,
)
from cache import embed_text_cached, SemanticCache, get_cache_stats, clear_cache
from guardrails import check_input, check_output, OutputValidation

app = FastAPI(title="AI Knowledge Assistant - Modul 10", version="10.0.0")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ai_user:ai_pass@localhost:5432/ai_knowledge")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
EXPECTED_API_KEY = os.getenv("EXPECTED_API_KEY", "rahasia-latihan")
GEMINI_MODEL = "gemini-3.6-flash"  # Gemini 3.x - jauh lebih andal untuk tool calling dibanding versi <3

# Tool yang hasilnya TRANSAKSIONAL/real-time - jawaban yang memakai tool ini
# tidak disimpan ke semantic cache (lihat /chat).
REALTIME_TOOLS = {"cek_stok_barang"}


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
# MODUL 3 - Konektivitas Docker (Postgres + Redis + Gemini)
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
# MODUL 5/6 - Production RAG (metadata filter + rerank + context assembly)
# + Hybrid Search (vector + keyword + RRF). Modul 9: embedding query lewat
# embed_text_cached() (lapis 1 - exact-match cache), bukan embed_text()
# langsung - lihat cache.py.
# ---------------------------------------------------------------------------
class SearchResult(BaseModel):
    content: str
    source_file: str
    chunk_index: int
    category: str
    distance: float | None = None
    rrf_score: float | None = None
    relevance_score: float | None = None


class ProductionSearchResponse(BaseModel):
    query: str
    context: str
    sources: List[SearchResult]
    candidates_retrieved: int
    candidates_after_rerank: int


@app.get("/search", response_model=ProductionSearchResponse)
async def search(
    query: str,
    limit: int = Query(default=3, ge=1, le=10, description="Jumlah chunk relevan yang diambil"),
    category: str | None = None,
):
    """
    Hybrid Search RAG - empat tahap (lihat retrieval.py). Modul 9: langkah
    embedding query sekarang lewat cache exact-match - query yang sama
    persis dengan pencarian sebelumnya (mis. dua peserta mengetik query
    yang identik) tidak memanggil Gemini embed_content lagi.
    """
    try:
        query_embedding = embed_text_cached(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membuat embedding untuk query: {e}")

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            vector_results = vector_search(conn, query_embedding, RETRIEVE_TOP_K, category)
            keyword_results = keyword_search(conn, query, RETRIEVE_TOP_K, category)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal melakukan pencarian: {e}")

    merged_candidates = rrf_merge(vector_results, keyword_results, k=RRF_K, top_k=RETRIEVE_TOP_K)

    try:
        reranked = rerank_candidates(query, merged_candidates, top_n=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal melakukan reranking: {e}")

    context = assemble_context(reranked)

    return ProductionSearchResponse(
        query=query,
        context=context,
        sources=[
            SearchResult(
                content=c["content"], source_file=c["source_file"], chunk_index=c["chunk_index"],
                category=c["category"], distance=c.get("distance"), rrf_score=c.get("rrf_score"),
                relevance_score=c.get("relevance_score"),
            )
            for c in reranked
        ],
        candidates_retrieved=len(merged_candidates),
        candidates_after_rerank=len(reranked),
    )


# ---------------------------------------------------------------------------
# MODUL 7/9 - Tool Calling + Semantic Cache (lapis 2 - similarity-match)
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
    cache_hit: bool = False
    cache_similarity: float | None = None  # cosine similarity ke query cache yang cocok (None kalau miss)
    cacheable: bool = True  # False kalau jawaban ini sengaja tidak disimpan ke cache (lihat REALTIME_TOOLS)
    guardrail: OutputValidation | None = None
    latency_ms: int


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatMessage, api_key: str = Depends(verify_api_key)):
    """
    Endpoint chat dengan tool calling + semantic cache + guardrails. Alur:
      1. INPUT GUARDRAIL - tolak pesan yang mengandung pola prompt
         injection atau melebihi batas panjang, SEBELUM menyentuh cache
         maupun Gemini sama sekali.
      2. Embed pertanyaan user, cek semantic cache - kalau ada pertanyaan
         SEMAKNA yang sudah pernah dijawab (similarity >= threshold),
         langsung kembalikan jawaban DAN guardrail lama dari cache TANPA
         memanggil Gemini sama sekali (cache_hit=True, latency turun
         drastis, dan LLM-as-judge di langkah 5 juga ikut di-skip).
      3. Kalau MISS: jalankan tool calling seperti Modul 7 (Gemini boleh
         panggil tool, kita eksekusi, kirim hasilnya balik untuk jawaban
         akhir).
      4. Simpan jawaban baru ke cache - KECUALI kalau salah satu tool yang
         dipanggil ada di REALTIME_TOOLS (mis. cek_stok_barang), karena
         data itu bisa basi kapan saja.
      5. OUTPUT GUARDRAIL - nilai ulang jawaban akhir: grounded (didukung
         tool result, bukan karangan) dan safe (tidak bocorkan instruksi
         sistem) - kalau tidak safe, jawaban diganti pesan penolakan
         SEBELUM disimpan ke cache (jawaban tidak aman tidak pernah
         di-cache).
    """
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY belum di-set")

    input_check = check_input(payload.message)
    if not input_check.allowed:
        raise HTTPException(status_code=400, detail=f"Pesan ditolak guardrail: {input_check.reason}")

    start = time.perf_counter()

    try:
        query_embedding = embed_text_cached(payload.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membuat embedding untuk pesan: {e}")

    sem_cache = SemanticCache()
    hit = sem_cache.get(query_embedding)
    if hit is not None:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        cached_guardrail = hit.get("guardrail")
        return ChatResponse(
            answer=hit["answer"],
            tools_called=[ToolCallLog(**t) for t in hit["tools_called"]],
            cache_hit=True,
            cache_similarity=hit["similarity"],
            cacheable=True,
            guardrail=OutputValidation(**cached_guardrail) if cached_guardrail else None,
            latency_ms=elapsed_ms,
        )

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

        answer_text = final_response.text or (
            "Model masih ingin memanggil tool tambahan setelah putaran pertama - "
            "/chat di sini hanya menangani satu putaran tool calling. Coba "
            "endpoint /agent untuk kasus yang butuh beberapa langkah tool "
            "calling berurutan."
        )
    else:
        answer_text = response.text

    tool_context = "\n\n".join(f"[{t.name}] {t.result}" for t in tools_called)
    try:
        guardrail_result = check_output(payload.message, answer_text, tool_context)
    except Exception as e:
        # Output guardrail gagal (mis. kuota habis) - jangan blokir jawaban
        # yang sudah didapat, cukup tandai guardrail tidak sempat jalan.
        guardrail_result = OutputValidation(is_grounded=True, is_safe=True, reason=f"Output guardrail gagal dijalankan: {e}")

    if not guardrail_result.is_safe:
        answer_text = (
            "Maaf, jawaban untuk pertanyaan ini ditahan oleh sistem keamanan "
            "(guardrail) karena berpotensi tidak aman. Coba ajukan pertanyaan "
            "dengan cara lain."
        )
    elif not guardrail_result.is_grounded and tools_called:
        # Hanya tandai kalau ada tool result yang seharusnya jadi dasar
        # jawaban - kalau tidak ada tool dipanggil sama sekali, jawaban umum
        # tanpa "dasar data" itu memang wajar (bukan tanda halusinasi).
        answer_text += (
            "\n\n_(Catatan sistem: jawaban ini belum sepenuhnya didukung oleh "
            "data yang ditemukan - mohon verifikasi ulang sebelum digunakan.)_"
        )

    # Jawaban yang tidak SAFE tidak pernah disimpan ke cache, apapun tool
    # yang dipanggil - guardrail keamanan didahulukan di atas penghematan
    # biaya dari caching.
    cacheable = guardrail_result.is_safe and not any(t.name in REALTIME_TOOLS for t in tools_called)
    if cacheable:
        sem_cache.set(
            query=payload.message,
            query_embedding=query_embedding,
            answer=answer_text,
            tools_called=[t.model_dump() for t in tools_called],
            guardrail=guardrail_result.model_dump(),
        )

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return ChatResponse(
        answer=answer_text,
        tools_called=tools_called,
        cache_hit=False,
        cache_similarity=None,
        cacheable=cacheable,
        guardrail=guardrail_result,
        latency_ms=elapsed_ms,
    )


# ---------------------------------------------------------------------------
# MODUL 9 - Statistik & kontrol cache
# ---------------------------------------------------------------------------
@app.get("/cache-stats")
async def cache_stats():
    """Ringkasan hit/miss embedding cache (lapis 1) dan semantic cache (lapis 2)."""
    try:
        return get_cache_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengambil statistik cache: {e}")


@app.post("/cache/clear")
async def cache_clear(api_key: str = Depends(verify_api_key)):
    """Hapus semua entry cache & reset statistik - untuk demo/testing, butuh x-api-key."""
    try:
        return clear_cache()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membersihkan cache: {e}")


# ---------------------------------------------------------------------------
# MODUL 8 - Agent Foundation (loop Think-Act-Observe)
# ---------------------------------------------------------------------------
class AgentGoal(BaseModel):
    goal: str = Field(..., min_length=1, description="Tujuan/pertanyaan yang mungkin butuh beberapa langkah")
    max_steps: int = Field(default=5, ge=1, le=10)


class AgentResponse(BaseModel):
    answer: str
    steps: List[dict]
    total_steps: int
    stopped_reason: str
    guardrail: OutputValidation | None = None


@app.post("/agent", response_model=AgentResponse)
async def run_agent(payload: AgentGoal, api_key: str = Depends(verify_api_key)):
    """
    Endpoint agent + guardrails - bisa memanggil BEBERAPA tool secara
    berurutan dalam satu permintaan. Tidak memakai semantic cache Modul 9
    secara langsung (lihat catatan di agent.py) - tapi tool cari_dokumen
    yang dipanggilnya tetap kebagian manfaat embedding cache lapis 1.

    Sama seperti /chat: goal dicek INPUT GUARDRAIL sebelum agent mulai
    berjalan, dan jawaban akhirnya dicek OUTPUT GUARDRAIL (grounded +
    safe) sebelum dikembalikan ke caller.
    """
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY belum di-set")

    input_check = check_input(payload.goal)
    if not input_check.allowed:
        raise HTTPException(status_code=400, detail=f"Goal ditolak guardrail: {input_check.reason}")

    agent = Agent(max_steps=payload.max_steps)
    try:
        result = await asyncio.to_thread(agent.run, payload.goal)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent gagal berjalan: {e}")

    tool_context = "\n\n".join(
        f"[{s['tool']}] {s['result']}" for s in result["steps"] if s["kind"] == "act"
    )
    try:
        guardrail_result = check_output(payload.goal, result["answer"], tool_context)
    except Exception as e:
        guardrail_result = OutputValidation(is_grounded=True, is_safe=True, reason=f"Output guardrail gagal dijalankan: {e}")

    answer_text = result["answer"]
    if not guardrail_result.is_safe:
        answer_text = (
            "Maaf, jawaban untuk goal ini ditahan oleh sistem keamanan "
            "(guardrail) karena berpotensi tidak aman. Coba ajukan goal "
            "dengan cara lain."
        )
    elif not guardrail_result.is_grounded and tool_context:
        answer_text += (
            "\n\n_(Catatan sistem: jawaban ini belum sepenuhnya didukung oleh "
            "data yang ditemukan - mohon verifikasi ulang sebelum digunakan.)_"
        )

    return AgentResponse(
        answer=answer_text,
        steps=result["steps"],
        total_steps=result["total_steps"],
        stopped_reason=result["stopped_reason"],
        guardrail=guardrail_result,
    )

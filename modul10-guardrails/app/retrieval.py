"""
Pipeline Retrieval Bersama (Modul 5 Production RAG + Modul 6 Hybrid Search)
AI Knowledge Assistant - Human Initiative

Tidak ada perubahan logika retrieval di modul ini dibanding Modul 7/8 - satu
perubahan kecil yang relevan untuk Modul 9 ada di tools.py (cari_dokumen
memakai embed_text_cached dari cache.py untuk embedding QUERY-nya), bukan di
sini. File ini tetap dipisah dari main.py/tools.py supaya keduanya bisa
saling mengimpornya tanpa circular import.

Empat tahap:
    1. Retrieval ganda - vector search DAN keyword search (PostgreSQL
       full-text search) berjalan masing-masing, ambil RETRIEVE_TOP_K
       kandidat (opsional difilter `category`)
    2. RRF merge - gabungkan kedua ranked list dengan Reciprocal Rank
       Fusion
    3. Rerank - Gemini menilai ulang kandidat gabungan secara lebih
       presisi memakai structured output (response_schema)
    4. Context assembly - gabungkan potongan terpilih jadi satu context
       string, dengan deduplikasi & batas budget karakter
"""
import hashlib
import os

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ai_user:ai_pass@localhost:5432/ai_knowledge")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.6-flash"  # Gemini 3.x - jauh lebih andal untuk tool calling dibanding versi <3

RETRIEVE_TOP_K = 10   # jumlah kandidat awal yang diambil dari tiap metode pencarian
CONTEXT_MAX_CHARS = 2000  # batas karakter total context yang dikirim ke LLM
RRF_K = 60  # konstanta RRF standar dari literatur (Cormack, Clarke & Buttcher, 2009)


class RerankItem(BaseModel):
    index: int = Field(description="Index kandidat (0-based, sesuai urutan yang diberikan)")
    relevance_score: float = Field(description="Skor relevansi 0-10 terhadap query; makin tinggi makin relevan")


class RerankResponse(BaseModel):
    rankings: list[RerankItem]


def vector_search(conn, query_embedding, top_k: int = RETRIEVE_TOP_K, category: str | None = None) -> list[dict]:
    """Pencarian semantik - kuat untuk makna, lemah untuk istilah spesifik/exact match."""
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
                (query_embedding, category, top_k),
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
                (query_embedding, top_k),
            )
        rows = cur.fetchall()
    return [
        {"content": r[0], "source_file": r[1], "chunk_index": r[2], "category": r[3], "distance": r[4]}
        for r in rows
    ]


def keyword_search(conn, query: str, top_k: int = RETRIEVE_TOP_K, category: str | None = None) -> list[dict]:
    """
    Full-text search PostgreSQL - kuat untuk istilah spesifik (kode barang,
    nomor invoice, nama vendor) yang sering tidak tertangkap baik oleh
    vector search murni karena embedding fokus ke makna, bukan kata persis.
    """
    with conn.cursor() as cur:
        if category:
            cur.execute(
                """
                SELECT content, source_file, chunk_index, category,
                       ts_rank(content_tsv, plainto_tsquery('indonesian', %s)) AS score
                FROM documents
                WHERE content_tsv @@ plainto_tsquery('indonesian', %s) AND category = %s
                ORDER BY score DESC
                LIMIT %s;
                """,
                (query, query, category, top_k),
            )
        else:
            cur.execute(
                """
                SELECT content, source_file, chunk_index, category,
                       ts_rank(content_tsv, plainto_tsquery('indonesian', %s)) AS score
                FROM documents
                WHERE content_tsv @@ plainto_tsquery('indonesian', %s)
                ORDER BY score DESC
                LIMIT %s;
                """,
                (query, query, top_k),
            )
        rows = cur.fetchall()
    return [
        {"content": r[0], "source_file": r[1], "chunk_index": r[2], "category": r[3], "score": r[4]}
        for r in rows
    ]


def rrf_merge(vector_results: list[dict], keyword_results: list[dict], k: int = RRF_K, top_k: int = RETRIEVE_TOP_K) -> list[dict]:
    """
    Reciprocal Rank Fusion - gabungkan dua ranked list jadi satu:
        score(d) = sum( 1 / (k + rank) )  untuk tiap list yang memuat d

    Dokumen yang rank tinggi di KEDUA metode pencarian akan naik ke
    posisi teratas hasil gabungan. Dokumen diidentifikasi via kombinasi
    (source_file, chunk_index) sebagai key unik.
    """
    scores: dict[tuple, float] = {}
    docs: dict[tuple, dict] = {}

    for rank, item in enumerate(vector_results, start=1):
        key = (item["source_file"], item["chunk_index"])
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
        docs[key] = item  # simpan versi vector (punya field "distance")

    for rank, item in enumerate(keyword_results, start=1):
        key = (item["source_file"], item["chunk_index"])
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
        docs.setdefault(key, item)  # kalau belum ada dari vector, pakai versi keyword

    ranked_keys = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)

    merged = []
    for key, rrf_score in ranked_keys[:top_k]:
        item = dict(docs[key])
        item["rrf_score"] = rrf_score
        merged.append(item)
    return merged


def rerank_candidates(query: str, candidates: list[dict], top_n: int) -> list[dict]:
    """
    Reranking - retrieval awal (vector + keyword) cepat tapi kasar. Di sini
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
    Context management - gabungkan potongan terpilih jadi satu string context:
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

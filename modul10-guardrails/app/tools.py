"""
Modul 7/9 - Definisi Tools untuk Function Calling (dibawa maju dari Modul 7/8)
AI Knowledge Assistant - Human Initiative

Satu-satunya perubahan untuk Modul 9: cari_dokumen sekarang mengambil
embedding query-nya lewat embed_text_cached() (cache.py) alih-alih
embed_text() langsung (ingest.py). Kalau agent/chat memanggil cari_dokumen
dengan query yang sama persis dengan yang pernah di-embed sebelumnya (mis.
agent mengulang query pencarian di goal yang mirip), panggilan embed_content
ke Gemini di-skip sepenuhnya.

File ini memisahkan "apa saja yang bisa dilakukan agent" (tools) dari
logika chat di main.py. Setiap tool punya dua bagian:
  1. Fungsi Python biasa yang benar-benar dieksekusi
  2. FunctionDeclaration - skema JSON yang dikirim ke Gemini supaya model
     tahu tool ini ada, kapan dipakai, dan parameter apa yang dibutuhkan

Menambah tool baru = tambah fungsi + declaration + daftarkan di TOOL_REGISTRY
dan ALL_TOOLS di bagian bawah file ini.
"""
import os

import psycopg
from google.genai import types

from retrieval import vector_search, keyword_search, rrf_merge, rerank_candidates, RETRIEVE_TOP_K, RRF_K

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ai_user:ai_pass@localhost:5432/ai_knowledge")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


# ===========================================================================
# TOOL 1 - cek_stok_barang
# Simulasi API ERP: cek stok barang di gudang. Di dunia nyata, fungsi ini
# akan memanggil API ERP sungguhan (REST/SOAP) alih-alih dictionary statis.
# ===========================================================================
FAKE_INVENTORY = {
    "kabel listrik": {"jumlah": 120, "satuan": "meter"},
    "terpal": {"jumlah": 45, "satuan": "lembar"},
    "air mineral": {"jumlah": 800, "satuan": "dus"},
    "genset": {"jumlah": 3, "satuan": "unit"},
}


def cek_stok_barang(nama_barang: str) -> dict:
    """Mengecek jumlah stok sebuah barang di gudang transit."""
    item = FAKE_INVENTORY.get(nama_barang.lower().strip())
    if item is None:
        return {"nama_barang": nama_barang, "ditemukan": False}
    return {"nama_barang": nama_barang, "ditemukan": True, **item}


CEK_STOK_DECLARATION = types.FunctionDeclaration(
    name="cek_stok_barang",
    description=(
        "Mengecek jumlah stok sebuah barang di gudang transit. Gunakan tool ini "
        "ketika user bertanya tentang ketersediaan atau jumlah stok barang tertentu."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            "nama_barang": {
                "type": "string",
                "description": "Nama barang yang ingin dicek stoknya, mis. 'kabel listrik', 'terpal'",
            }
        },
        "required": ["nama_barang"],
    },
)


# ===========================================================================
# TOOL 2 - cari_dokumen
# Membungkus pipeline Hybrid Search + rerank dari Modul 5/6 (retrieval.py)
# sebagai tool yang bisa dipanggil Gemini kapan pun user butuh info dari
# dokumen internal (SOP, kebijakan), bukan data transaksional seperti
# stok - pipeline yang SAMA dengan endpoint /search di main.py, supaya
# agent tidak memakai kualitas retrieval yang lebih rendah dari endpoint
# HTTP-nya sendiri. Modul 9: embedding query-nya lewat cache (lihat cache.py).
# ===========================================================================
def cari_dokumen(query: str, limit: int = 3) -> list:
    """Mencari potongan dokumen internal yang relevan dengan query lewat Hybrid Search + rerank."""
    if not GEMINI_API_KEY:
        return [{"error": "GEMINI_API_KEY belum di-set"}]

    from cache import embed_text_cached  # reuse embedding cache Modul 9

    query_embedding = embed_text_cached(query)

    with psycopg.connect(DATABASE_URL) as conn:
        vector_results = vector_search(conn, query_embedding, RETRIEVE_TOP_K)
        keyword_results = keyword_search(conn, query, RETRIEVE_TOP_K)

    merged = rrf_merge(vector_results, keyword_results, k=RRF_K, top_k=RETRIEVE_TOP_K)
    reranked = rerank_candidates(query, merged, top_n=limit)

    return [
        {
            "content": r["content"][:300],
            "source_file": r["source_file"],
            "category": r["category"],
            "relevance_score": r.get("relevance_score"),
        }
        for r in reranked
    ]


CARI_DOKUMEN_DECLARATION = types.FunctionDeclaration(
    name="cari_dokumen",
    description=(
        "Mencari potongan dokumen internal organisasi (SOP, kebijakan) yang relevan "
        "secara makna dengan sebuah pertanyaan. Gunakan tool ini untuk pertanyaan "
        "tentang prosedur, kebijakan, atau aturan - BUKAN untuk data stok/transaksional."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Kata kunci atau pertanyaan untuk mencari dokumen"},
            "limit": {"type": "integer", "description": "Jumlah hasil maksimal, default 3"},
        },
        "required": ["query"],
    },
)


# ===========================================================================
# Registry - daftar semua tool yang tersedia untuk model
# ===========================================================================
TOOL_REGISTRY = {
    "cek_stok_barang": cek_stok_barang,
    "cari_dokumen": cari_dokumen,
}

ALL_TOOLS = types.Tool(function_declarations=[CEK_STOK_DECLARATION, CARI_DOKUMEN_DECLARATION])

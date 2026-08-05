"""
Modul 7 - Definisi Tools untuk Function Calling
AI Knowledge Assistant - Human Initiative

File ini memisahkan "apa saja yang bisa dilakukan agent" (tools) dari
logika chat di main.py. Setiap tool punya dua bagian:
  1. Fungsi Python biasa yang benar-benar dieksekusi
  2. FunctionDeclaration — skema JSON yang dikirim ke Gemini supaya model
     tahu tool ini ada, kapan dipakai, dan parameter apa yang dibutuhkan

Menambah tool baru = tambah fungsi + declaration + daftarkan di TOOL_REGISTRY
dan ALL_TOOLS di bagian bawah file ini.
"""
import os

import psycopg
from google import genai
from google.genai import types

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ai_user:ai_pass@localhost:5432/ai_knowledge")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768


# ===========================================================================
# TOOL 1 — cek_stok_barang
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
# TOOL 2 — cari_dokumen
# Membungkus pencarian semantik dari Modul 4 (embedding + pgvector) sebagai
# tool yang bisa dipanggil Gemini kapan pun user butuh info dari dokumen
# internal (SOP, kebijakan), bukan data transaksional seperti stok.
# ===========================================================================
def cari_dokumen(query: str, limit: int = 3) -> list:
    """Mencari potongan dokumen internal yang relevan secara makna dengan query."""
    if not GEMINI_API_KEY:
        return [{"error": "GEMINI_API_KEY belum di-set"}]

    client = genai.Client(api_key=GEMINI_API_KEY)
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
    )
    query_embedding = result.embeddings[0].values

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT content, source_file, embedding <=> %s::vector AS distance
                FROM documents
                ORDER BY distance ASC
                LIMIT %s;
                """,
                (query_embedding, limit),
            )
            rows = cur.fetchall()

    return [
        {"content": r[0][:300], "source_file": r[1], "distance": round(r[2], 4)}
        for r in rows
    ]


CARI_DOKUMEN_DECLARATION = types.FunctionDeclaration(
    name="cari_dokumen",
    description=(
        "Mencari potongan dokumen internal organisasi (SOP, kebijakan) yang relevan "
        "secara makna dengan sebuah pertanyaan. Gunakan tool ini untuk pertanyaan "
        "tentang prosedur, kebijakan, atau aturan — BUKAN untuk data stok/transaksional."
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
# Registry — daftar semua tool yang tersedia untuk model
# ===========================================================================
TOOL_REGISTRY = {
    "cek_stok_barang": cek_stok_barang,
    "cari_dokumen": cari_dokumen,
}

ALL_TOOLS = types.Tool(function_declarations=[CEK_STOK_DECLARATION, CARI_DOKUMEN_DECLARATION])

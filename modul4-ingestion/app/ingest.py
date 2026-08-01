"""
Modul 4 - Pipeline Data Ingestion (LENGKAP)
AI Knowledge Assistant - Human Initiative

Alur:
    1. Baca dokumen dari folder sample_docs/
    2. Pecah (chunk) jadi potongan kecil dengan overlap
    3. Ubah tiap potongan jadi embedding (vektor) via Gemini API
    4. Simpan potongan + embedding + metadata ke tabel `documents` di pgvector

Jalankan (dari dalam container app, setelah `docker compose up`):
    docker compose exec app python ingest.py
"""
import glob
import os
import time

import psycopg
from pgvector.psycopg import register_vector

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ai_user:ai_pass@localhost:5432/ai_knowledge")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

SAMPLE_DOCS_DIR = os.path.join(os.path.dirname(__file__), "sample_docs")
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
EMBEDDING_DIM = 768
EMBEDDING_MODEL = "models/gemini-embedding-001"


# ---------------------------------------------------------------------------
# 1. Chunking
# ---------------------------------------------------------------------------
def chunk_text(text: str) -> list[str]:
    """Pecah teks jadi potongan CHUNK_SIZE karakter dengan overlap CHUNK_OVERLAP."""
    text = text.strip()
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - CHUNK_OVERLAP
    return chunks


# ---------------------------------------------------------------------------
# 2. Embedding
# ---------------------------------------------------------------------------
def embed_text(text: str, retries: int = 3) -> list[float]:
    """
    Ubah teks jadi vektor embedding memakai Gemini embedding API.

    Membutuhkan GEMINI_API_KEY (lihat .env.example). Tanpa API key yang valid,
    fungsi ini akan gagal — itu perilaku yang diharapkan (jangan silent-fail
    dengan vektor kosong, supaya masalah konfigurasi ketahuan dari awal).
    """
    import google.generativeai as genai

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY belum di-set. Salin .env.example ke .env dan isi API key Anda."
        )

    genai.configure(api_key=GEMINI_API_KEY)

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            result = genai.embed_content(
                model=EMBEDDING_MODEL, content=text, output_dimensionality=EMBEDDING_DIM
            )
            return result["embedding"]
        except Exception as e:  # rate limit / error jaringan sementara
            last_error = e
            wait = attempt * 2
            print(f"  [embed_text] percobaan {attempt}/{retries} gagal ({e}); retry dalam {wait}s...")
            time.sleep(wait)
    raise RuntimeError(f"Gagal mengambil embedding setelah {retries} percobaan: {last_error}")


# ---------------------------------------------------------------------------
# 3. Skema tabel
# ---------------------------------------------------------------------------
def ensure_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.commit()
    register_vector(conn)  # harus setelah extension aktif & sebelum query pakai tipe vector
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                source_file TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding VECTOR({EMBEDDING_DIM}),
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)
        conn.commit()


def delete_existing_chunks(conn: psycopg.Connection, source_file: str) -> None:
    """Idempotency: hapus chunk lama dari file yang sama sebelum insert ulang."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM documents WHERE source_file = %s;", (source_file,))
        conn.commit()


# ---------------------------------------------------------------------------
# 4. Pipeline utama
# ---------------------------------------------------------------------------
def main():
    with psycopg.connect(DATABASE_URL) as conn:
        ensure_table(conn)

        txt_files = sorted(glob.glob(os.path.join(SAMPLE_DOCS_DIR, "*.txt")))
        if not txt_files:
            print(f"Tidak ada file .txt ditemukan di {SAMPLE_DOCS_DIR}")
            return

        total_chunks = 0
        for filepath in txt_files:
            filename = os.path.basename(filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()

            chunks = chunk_text(text)
            print(f"{filename}: {len(chunks)} chunk akan di-ingest")

            delete_existing_chunks(conn, filename)

            with conn.cursor() as cur:
                for idx, chunk in enumerate(chunks):
                    embedding = embed_text(chunk)
                    cur.execute(
                        """
                        INSERT INTO documents (source_file, chunk_index, content, embedding)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (filename, idx, chunk, embedding),
                    )
                    total_chunks += 1
                    print(f"  Ingested {idx + 1}/{len(chunks)} chunk dari {filename}")
                conn.commit()

        print(f"\nSelesai. Total {len(txt_files)} dokumen, {total_chunks} chunk tersimpan di tabel documents.")


if __name__ == "__main__":
    main()

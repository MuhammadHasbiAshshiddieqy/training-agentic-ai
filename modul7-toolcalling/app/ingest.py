"""
Modul 7 - Pipeline Data Ingestion + Hybrid Search Index (LENGKAP)
AI Knowledge Assistant - Human Initiative

Dibawa maju dari Modul 6: kolom `content_tsv` (tsvector) + index GIN
supaya PostgreSQL full-text search bisa dipakai berdampingan dengan
vector search — dipakai bersama oleh endpoint /search DAN tool
cari_dokumen (lihat retrieval.py) supaya keduanya sama-sama Hybrid
Search, bukan cuma vector search polos ala Modul 4.

Catatan SDK: memakai `google-genai`. Model embedding gemini-embedding-001
menghasilkan 3072 dimensi secara default; kita minta 768 dimensi lewat
output_dimensionality supaya konsisten dengan skema tabel.
"""
import glob
import os
import time

import psycopg
from pgvector.psycopg import register_vector
from google import genai
from google.genai import types

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ai_user:ai_pass@localhost:5432/ai_knowledge")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

SAMPLE_DOCS_DIR = os.path.join(os.path.dirname(__file__), "sample_docs")
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
EMBEDDING_DIM = 768
EMBEDDING_MODEL = "gemini-embedding-001"

# ---------------------------------------------------------------------------
# Metadata sederhana: pemetaan nama file -> kategori dokumen.
# Di dunia nyata, ini bisa datang dari folder asal file, frontmatter
# dokumen, atau input manual saat upload — bukan hardcode seperti ini.
# ---------------------------------------------------------------------------
CATEGORY_MAP = {
    "sop_distribusi_logistik.txt": "logistik",
    "kebijakan_pengadaan_barang.txt": "keuangan",
}


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


def embed_text(text: str, retries: int = 3) -> list[float]:
    """Ubah teks jadi vektor embedding memakai Gemini embedding API."""
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY belum di-set. Salin .env.example ke .env dan isi API key Anda."
        )

    client = genai.Client(api_key=GEMINI_API_KEY)

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
            )
            return result.embeddings[0].values
        except Exception as e:
            last_error = e
            wait = attempt * 2
            print(f"  [embed_text] percobaan {attempt}/{retries} gagal ({e}); retry dalam {wait}s...")
            time.sleep(wait)
    raise RuntimeError(f"Gagal mengambil embedding setelah {retries} percobaan: {last_error}")


def ensure_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.commit()
    register_vector(conn)
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                source_file TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'umum',
                embedding VECTOR({EMBEDDING_DIM}),
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)
        # Kolom yang mungkin belum ada kalau tabel dibuat di Modul 4/5 —
        # ditambahkan secara aman (idempotent).
        cur.execute("""
            ALTER TABLE documents
            ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'umum';
        """)
        # --- MODUL 6: kolom tsvector untuk full-text search (keyword search) ---
        # GENERATED ALWAYS ... STORED = PostgreSQL otomatis menghitung ulang
        # kolom ini setiap kali `content` berubah, tidak perlu di-maintain manual.
        cur.execute("""
            ALTER TABLE documents
            ADD COLUMN IF NOT EXISTS content_tsv tsvector
            GENERATED ALWAYS AS (to_tsvector('indonesian', content)) STORED;
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS documents_content_tsv_idx
            ON documents USING GIN (content_tsv);
        """)
        conn.commit()


def delete_existing_chunks(conn: psycopg.Connection, source_file: str) -> None:
    """Idempotency: hapus chunk lama dari file yang sama sebelum insert ulang."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM documents WHERE source_file = %s;", (source_file,))
        conn.commit()


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
            category = CATEGORY_MAP.get(filename, "umum")
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()

            chunks = chunk_text(text)
            print(f"{filename} [kategori: {category}]: {len(chunks)} chunk akan di-ingest")

            delete_existing_chunks(conn, filename)

            with conn.cursor() as cur:
                for idx, chunk in enumerate(chunks):
                    embedding = embed_text(chunk)
                    cur.execute(
                        """
                        INSERT INTO documents (source_file, chunk_index, content, category, embedding)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (filename, idx, chunk, category, embedding),
                    )
                    total_chunks += 1
                    print(f"  Ingested {idx + 1}/{len(chunks)} chunk dari {filename}")
                conn.commit()

        print(f"\nSelesai. Total {len(txt_files)} dokumen, {total_chunks} chunk tersimpan di tabel documents.")


if __name__ == "__main__":
    main()

# Modul 4 — Data Ingestion & Vector Database (Lengkap)

Kode di folder ini sudah lengkap: pipeline ingestion (chunking → embedding
→ simpan ke pgvector) dan endpoint pencarian semantik.

## Cara Menjalankan

Panduan lengkap (install Docker, siapkan `.env`, jalankan Compose, jalankan
pipeline ingestion) dipisah per OS:

- [windows.md](windows.md)
- [macos.md](macos.md)
- [linux.md](linux.md)

Pipeline ingestion (`docker compose exec app python ingest.py`) membaca semua
file `.txt` di `sample_docs/` (sudah berisi satu contoh SOP), memecahnya jadi
potongan, mengubah tiap potongan jadi embedding lewat Gemini API, dan
menyimpannya ke tabel `documents`.

Jalankan lagi kapan saja — pipeline ini **idempotent**: chunk lama dari
file yang sama otomatis dihapus dulu sebelum insert ulang, sehingga
tidak terjadi duplikasi data.

## Cek Data di Database (opsional)

```bash
docker compose exec db psql -U ai_user -d ai_knowledge -c "SELECT id, source_file, chunk_index, left(content, 40) FROM documents;"
```

## Endpoint yang Tersedia

Selain `/search` (baru), semua endpoint dari Modul 2 & 3 tetap ada:
`/health`, `/ask` (butuh header `x-api-key`), `/documents/{doc_id}`,
`/db-check`, `/cache-check`, `/gemini-test`.

## Coba Pencarian Semantik

```bash
curl "http://localhost:8000/search?query=bagaimana%20cara%20verifikasi%20stok%20barang&limit=3"
```

Coba juga dengan kata-kata yang **tidak sama persis** dengan isi dokumen
(mis. "cek jumlah barang gudang" alih-alih "verifikasi stok") — hasil yang
tetap relevan membuktikan pencarian ini bekerja berdasarkan makna
(semantic search), bukan pencocokan kata.

## Sudah Diverifikasi

Chunking, penyimpanan ke pgvector, idempotency (ingest dua kali tidak
menduplikasi data), dan endpoint `/search` sudah diuji end-to-end
terhadap PostgreSQL+pgvector sungguhan. Satu hal yang perlu Anda
sediakan sendiri: **GEMINI_API_KEY yang valid** — bagian embedding
tidak bisa diuji tanpa API key asli.

## Menuju Modul 5

Endpoint `/search` ini adalah versi awal dari komponen **Retrieval**
pada arsitektur RAG. Di Modul 5 (Production RAG), endpoint ini akan
disempurnakan dengan metadata filtering, reranking, dan manajemen
konteks sebelum disatukan dengan LLM untuk menghasilkan jawaban akhir.

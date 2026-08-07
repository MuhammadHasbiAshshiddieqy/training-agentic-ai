# Modul 6 — Hybrid Search (Lengkap)

Menyempurnakan retrieval Modul 5 dengan **Hybrid Search**: menggabungkan
keyword search (PostgreSQL full-text search) dan vector search memakai
**Reciprocal Rank Fusion (RRF)** — sebelum tahap rerank & context
assembly dari Modul 5 tetap berjalan seperti biasa.

## Kenapa Hybrid, Bukan Vector Saja?

Vector search kuat untuk makna ("stok barang" ≈ "inventaris"), tapi
lemah untuk istilah spesifik — kode barang, nomor invoice, nama vendor
persis sering "hilang" dalam ruang vektor. Keyword search sebaliknya:
tajam untuk kata persis, tapi kaku terhadap sinonim. RRF menggabungkan
kekuatan keduanya.

## Cara Menjalankan

Panduan lengkap (install Docker, siapkan `.env`, jalankan Compose, jalankan
pipeline ingestion) dipisah per OS:

- [windows.md](windows.md)
- [macos.md](macos.md)
- [linux.md](linux.md)

Ringkas:

```bash
cp .env.example .env
# WAJIB isi GEMINI_API_KEY
docker compose up --build
docker compose exec app python ingest.py
```

Ingestion sekarang juga membuat kolom `content_tsv` (generated column)
dan index GIN untuk full-text search — otomatis, tidak perlu langkah
tambahan.

## Alur /search Sekarang (4 Tahap)

```
Query
  ├─→ Vector Search (top 10)   ─┐
  └─→ Keyword Search (top 10)  ─┴─→ RRF Merge ─→ Rerank (Gemini) ─→ Context Assembly
```

1. **Retrieval ganda** — vector search DAN keyword search berjalan,
   masing-masing ambil `RETRIEVE_TOP_K=10` kandidat
2. **RRF merge** — gabungkan kedua ranked list:
   `score(d) = Σ 1/(k + rank)`, dengan `k=60` (konstanta standar dari
   paper aslinya)
3. **Rerank** — Gemini menilai ulang kandidat gabungan (dari Modul 5)
4. **Context assembly** — deduplikasi + budget karakter (dari Modul 5)

## Coba Sendiri

```bash
# Query dengan istilah spesifik — keyword search akan sangat membantu di sini
curl "http://localhost:8000/search?query=ambang%20batas%20nilai%20pengadaan&limit=2"
```

Perhatikan field `rrf_score` di tiap `sources` — dokumen yang muncul di
KEDUA metode pencarian akan punya `rrf_score` lebih tinggi dan naik ke
atas. `distance` bisa `null` kalau dokumen itu hanya ditemukan lewat
keyword search (tidak masuk top-10 vector search).

## Sudah Diverifikasi

- Kolom `content_tsv` dan index GIN terbukti terbentuk otomatis saat
  ingestion (dicek lewat `\d documents` di psql)
- Full-text search PostgreSQL diuji langsung via SQL — berhasil
  menemukan chunk yang tepat berdasarkan istilah spesifik ("ambang
  batas pengadaan") dan TIDAK salah mencocokkan ke dokumen kategori lain
- Fungsi `rrf_merge()` diuji unit terpisah: dokumen yang muncul di
  KEDUA ranked list (vector + keyword) terbukti naik ke posisi teratas
  hasil gabungan
- Endpoint `/search` penuh diuji end-to-end via HTTP dengan Gemini
  di-mock — seluruh pipeline (vector + keyword + RRF + rerank + context
  assembly) berjalan tersambung dengan benar

## Menuju Modul 9-11

Pipeline retrieval sekarang sudah cukup lengkap: metadata filtering,
reranking, context management (Modul 5), dan hybrid search (Modul 6).
Modul 9 (Semantic Cache) akan mengurangi biaya panggilan berulang untuk
query yang mirip, Modul 10 (Guardrails) menambah lapisan keamanan, dan
Modul 11 (Observability) membahas cara memantau semua ini di produksi.

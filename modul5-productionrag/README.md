# Modul 5 — Production RAG (Lengkap)

Menyempurnakan endpoint `/search` dari Modul 4 dengan tiga teknik
Production RAG: **metadata filtering**, **reranking**, dan **context
management**.

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

Ingestion sekarang menyimpan 2 dokumen contoh dengan kategori berbeda:
`sop_distribusi_logistik.txt` (kategori `logistik`) dan
`kebijakan_pengadaan_barang.txt` (kategori `keuangan`).

## Endpoint /search yang Disempurnakan

```
GET /search?query=...&limit=3&category=keuangan
```

| Parameter | Wajib | Keterangan |
|---|---|---|
| `query` | Ya | Pertanyaan/kata kunci pencarian |
| `limit` | Tidak (default 3) | Jumlah hasil akhir setelah reranking |
| `category` | Tidak | Filter metadata — `logistik` atau `keuangan` |

## Tiga Tahap di Balik Layar

1. **Retrieval** — ambil `RETRIEVE_TOP_K=10` kandidat via vector search
   (opsional difilter `category` di level SQL)
2. **Rerank** — Gemini menilai ulang tiap kandidat secara lebih presisi
   memakai `response_schema` (structured output), ambil `limit` terbaik
3. **Context assembly** — gabungkan potongan terpilih jadi satu string
   `context`, dengan deduplikasi (chunk identik hanya sekali) dan batas
   `CONTEXT_MAX_CHARS=2000` karakter

## Coba Sendiri

```bash
# Tanpa filter kategori
curl "http://localhost:8000/search?query=bagaimana%20prosedur%20verifikasi%20stok&limit=2"

# Dengan filter kategori
curl "http://localhost:8000/search?query=ambang%20batas%20pengadaan&limit=2&category=keuangan"
```

Bandingkan field `candidates_retrieved` (sebelum rerank) dengan
`candidates_after_rerank` (`limit`) di response — dan perhatikan
`relevance_score` tiap sumber, bukan cuma `distance`.

## Sudah Diverifikasi

Ingestion dengan metadata kategori sudah diuji ke PostgreSQL sungguhan
(7 chunk `logistik`, 6 chunk `keuangan`). Endpoint `/search` sudah diuji
end-to-end via HTTP dengan reranking Gemini yang di-mock: filter kategori
terbukti mengubah jumlah kandidat sebelum rerank sesuai jumlah chunk di
kategori itu, dan context assembly terbukti melakukan deduplikasi +
pemotongan sesuai budget karakter.

## Menuju Modul 6

Retrieval di sini masih murni vector search. Modul 6 (Hybrid Search)
akan menggabungkannya dengan keyword search (PostgreSQL full-text
search) memakai algoritma Reciprocal Rank Fusion — melengkapi kelemahan
vector search untuk istilah spesifik (kode barang, nomor invoice) yang
sering tidak tertangkap baik secara semantik.

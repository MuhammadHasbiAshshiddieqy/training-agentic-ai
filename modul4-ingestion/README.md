# Modul 4 — Data Ingestion & Vector Database (Lengkap)

Kode di folder ini sudah lengkap: pipeline ingestion (chunking → embedding
→ simpan ke pgvector) dan endpoint pencarian semantik.

**Catatan SDK:** kode ini memakai `google-genai` (paket resmi terbaru).
Paket `google-generativeai` yang lebih lama sudah *deprecated* sejak
Agustus 2025 — jangan pakai itu untuk kode baru.

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

Selain `/search` dan `/rag` (baru), semua endpoint dari Modul 2 & 3 tetap ada:
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

Parameter `limit` (jumlah chunk yang diambil, berlaku juga untuk `/rag` di
bawah) dibatasi **1–10** — di luar rentang itu FastAPI otomatis menolak
dengan `422`, supaya tidak ada yang tidak sengaja minta ratusan chunk
sekaligus (konteks jadi terlalu panjang & mahal untuk dikirim ke Gemini).

## Coba Endpoint `/ask` (Peninggalan Modul 2 — Masih Simulasi)

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -H "x-api-key: rahasia-latihan" \
  -d '{"question": "Bagaimana cara verifikasi stok barang?"}'
```

`/ask` **belum** membaca hasil `/search` maupun memanggil Gemini — jawabannya
selalu berupa teks simulasi (`"Ini jawaban simulasi untuk pertanyaan: ..."`)
persis seperti sejak Modul 2. Endpoint ini dipertahankan apa adanya supaya
konsep Dependency Injection (`verify_api_key`) dan validasi Pydantic yang
diajarkan di Modul 2 tetap bisa dicoba, tapi jangan terkecoh: untuk jawaban
yang benar-benar berdasarkan isi dokumen, pakai `/search` di atas — `/ask`
baru akan disatukan dengan retrieval + Gemini di **Modul 5** — atau coba
sekarang lewat `/rag` di bawah ini.

## Coba RAG Beneran: Endpoint `/rag`

Kalau `/ask` masih simulasi dan `/search` cuma mengembalikan potongan mentah,
`/rag` adalah versi yang **benar-benar** menggabungkan keduanya jadi jawaban
akhir — alur RAG penuh dalam satu endpoint:

1. **Retrieval** — cari chunk paling relevan di pgvector (persis `/search`)
2. **Augmentation** — chunk-chunk itu disusun jadi konteks di dalam prompt
3. **Generation** — prompt + konteks dikirim ke Gemini, jawabannya dikembalikan

```bash
curl "http://localhost:8000/rag?query=bagaimana%20cara%20verifikasi%20stok%20barang&limit=3"
```

Contoh respons (`answer` adalah jawaban asli dari Gemini, `sources` adalah
chunk yang dipakai sebagai konteksnya):

```json
{
  "question": "bagaimana cara verifikasi stok barang",
  "answer": "Verifikasi stok barang dilakukan melalui sistem ERP dan stock opname.",
  "sources": [ { "content": "...", "source_file": "sop_distribusi_logistik.txt", "chunk_index": 2, "distance": 0.25 } ],
  "latency_ms": 5245
}
```

Prompt-nya secara eksplisit melarang model mengarang jawaban di luar konteks
— coba tanya sesuatu yang tidak ada di dokumen untuk membuktikannya:

```bash
curl "http://localhost:8000/rag?query=siapa%20presiden%20indonesia%20saat%20ini&limit=3"
```

Hasilnya jujur: `"Saya tidak tahu. Informasi tersebut tidak ada dalam konteks yang diberikan."`

> `/rag` ini adalah **preview sederhana** — belum ada reranking, metadata
> filtering, atau manajemen konteks (mis. potong token kalau chunk
> terlalu banyak). Lihat `../modul5-productionrag/` untuk versi yang
> menyempurnakan bagian-bagian itu.

## Sudah Diverifikasi

Chunking, penyimpanan ke pgvector, idempotency (ingest dua kali tidak
menduplikasi data), dan endpoint `/search` maupun `/rag` sudah diuji
end-to-end terhadap PostgreSQL+pgvector dan Gemini API sungguhan —
termasuk kasus `/rag` menjawab jujur "tidak tahu" untuk pertanyaan di
luar konteks dokumen. Satu hal yang perlu Anda
sediakan sendiri: **GEMINI_API_KEY yang valid** — bagian embedding
tidak bisa diuji tanpa API key asli.

## Menuju Modul 5

Endpoint `/search` ini adalah versi awal dari komponen **Retrieval**
pada arsitektur RAG. Di [`modul5-productionrag/`](../modul5-productionrag/),
endpoint ini disempurnakan dengan metadata filtering, reranking, dan
manajemen konteks — lalu di [`modul6-hybridsearch/`](../modul6-hybridsearch/)
digabung dengan keyword search (Hybrid Search) sebelum disatukan dengan
LLM untuk menghasilkan jawaban akhir.

# Modul 3 — Docker & Local AI Environment (Lengkap)

Kode di folder ini sudah lengkap: FastAPI + PostgreSQL(pgvector) + Redis,
semuanya dijalankan lewat Docker Compose.

## Cara Menjalankan

Panduan lengkap (install Docker, siapkan `.env`, jalankan Compose) dipisah per OS:

- [windows.md](windows.md)
- [macos.md](macos.md)
- [linux.md](linux.md)

Setelah `docker compose up --build` jalan, ini menyalakan 3 container:
- `app` — FastAPI di http://localhost:8000/docs
- `db` — PostgreSQL + pgvector di port 5432
- `redis` — Redis di port 6379

## Endpoint yang Tersedia

| Endpoint | Method | Keterangan |
|---|---|---|
| `/health` | GET | Cek server hidup |
| `/ask` | POST | Dari Modul 2 — butuh header `x-api-key: rahasia-latihan` |
| `/documents/{doc_id}` | GET | Contoh error handling (404 jika id tidak ada) |
| `/db-check` | GET | Cek koneksi PostgreSQL + aktifkan extension pgvector |
| `/cache-check` | GET | Cek koneksi Redis (tulis & baca satu key) |
| `/gemini-test` | GET | Panggilan sederhana ke Gemini API — verifikasi API key sebelum Modul 4 |

## Coba Sendiri

```bash
# /health — cek server hidup
curl http://localhost:8000/health

# /ask — dari Modul 2, butuh header x-api-key
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -H "x-api-key: rahasia-latihan" \
  -d '{"question": "Apa itu RAG?"}'

# /documents/{doc_id} — coba id 1 (ada) vs 999 (404)
curl http://localhost:8000/documents/1
curl http://localhost:8000/documents/999

# /db-check — pastikan PostgreSQL + pgvector terhubung
curl http://localhost:8000/db-check

# /cache-check — pastikan Redis terhubung
curl http://localhost:8000/cache-check

# /gemini-test — butuh GEMINI_API_KEY valid di .env
curl http://localhost:8000/gemini-test
```

Contoh respons `/gemini-test` kalau `GEMINI_API_KEY` valid:

```json
{
  "prompt": "Halo, apa itu RAG?",
  "response": "RAG (Retrieval-Augmented Generation) adalah teknik yang menggabungkan pencarian informasi dari sumber eksternal dengan model bahasa untuk menghasilkan jawaban yang lebih akurat."
}
```

## Sudah Diverifikasi

`/db-check` dan `/cache-check` sudah diuji terhubung ke PostgreSQL (dengan
extension `pgvector` aktif) dan Redis sungguhan — bukan simulasi.
Dependency `verify_api_key` sudah diuji: request tanpa header maupun
dengan header salah sama-sama mengembalikan 401 yang jelas (bukan 422
generik dari FastAPI). `/gemini-test` sudah diuji mengembalikan error
yang jelas saat API key belum diisi — panggilan sungguhan ke Gemini
butuh API key valid milik Anda sendiri untuk diuji lebih lanjut.

## Kenapa Data Postgres Tetap Ada Setelah Restart?

`docker-compose.yml` mendefinisikan named volume `pgdata` yang di-mount ke
direktori data PostgreSQL di dalam container. Volume ini hidup terpisah
dari container-nya sendiri — `docker compose down` menghapus container,
TAPI volume tetap ada, sehingga `docker compose up` berikutnya membaca
data yang sama. Untuk benar-benar menghapus data, gunakan
`docker compose down -v`.

## Troubleshooting Umum

| Gejala | Kemungkinan Penyebab |
|---|---|
| `port already in use` | Ada proses lain di port 8000/5432/6379 — matikan atau ganti port di `docker-compose.yml` |
| `db-check` gagal terus | Container `db` mungkin belum sepenuhnya siap — cek `docker compose logs db` |
| Perubahan kode tidak muncul | Pastikan volume `./app:/app` ter-mount dan `--reload` aktif di Dockerfile |

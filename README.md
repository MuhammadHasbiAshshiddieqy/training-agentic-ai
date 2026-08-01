# Complete Kit — Modul 2, 3 & 4 (Kode Lengkap)
## AI Knowledge Assistant — Human Initiative × Principal Tech Sage

> **Baru pertama kali menjalankan kit ini?** Baca **`PANDUAN_LENGKAP.md`**
> di folder ini dulu — panduan langkah-demi-langkah untuk macOS, Windows,
> dan Linux, ditulis dengan asumsi hanya Python & Docker yang sudah
> terinstall.

Berbeda dari **Starter_Kit_Modul2-4.zip** (yang berisi kerangka + TODO
untuk latihan peserta), kit ini berisi **kode yang sudah lengkap dan siap
jalan** — cocok untuk demo langsung, referensi trainer, atau dibagikan ke
peserta yang tinggal ingin clone & jalankan tanpa mengerjakan TODO.

```
modul2-fastapi/     FastAPI app lengkap (async, Pydantic validation, streaming)
modul3-docker/      + Docker Compose, PostgreSQL(pgvector), Redis — semua terhubung
modul4-ingestion/   + Pipeline ingestion lengkap & endpoint pencarian semantik
```

## Status Verifikasi

Setiap bagian sudah benar-benar dijalankan dan diuji (bukan hanya
diperiksa sintaksnya) sebelum diserahkan:

| Modul | Yang Diuji | Hasil |
|---|---|---|
| 2 | Endpoint `/ask`, validasi Pydantic, Dependency Injection (`verify_api_key`), error handling (`/documents/{id}`), konkurensi async, streaming | 3 request bersamaan selesai ~1.5s (bukan ~4.5s); DI mengembalikan 401 konsisten baik header hilang maupun salah; 404 jelas untuk id tidak ada |
| 3 | `/db-check` ke PostgreSQL+pgvector sungguhan, `/cache-check` ke Redis sungguhan, `/gemini-test` (tanpa API key) | Semua endpoint terhubung/merespons dengan benar; `/gemini-test` memberi pesan error jelas saat API key kosong |
| 4 | Chunking + overlap, ingestion ke pgvector, idempotency, endpoint `/search`, semua endpoint Modul 2/3 berjalan bersamaan dalam satu server | Ingest ulang tidak menduplikasi data; `/search` mengembalikan hasil terurut by jarak vektor; tidak ada konflik antar endpoint |

Satu bagian yang **tidak** bisa diuji di lingkungan pembuatan kit ini:
panggilan sungguhan ke Gemini API dengan API key valid (tidak ada akses
internet ke domain Google AI di sandbox). Kode `embed_text()` dan
`/gemini-test` ditulis mengikuti API resmi `google-generativeai` dengan
benar dan sudah diuji perilaku error-nya (pesan jelas saat key kosong),
tapi **coba dulu dengan API key Anda sendiri** sebelum dipakai live di
depan peserta.

## Bug yang Ditemukan & Diperbaiki Selama Pengujian

**1. Query pgvector butuh cast eksplisit.** Saat menguji endpoint
`/search`, ditemukan bahwa query pgvector dengan parameter Python list
biasa gagal (`operator does not exist: vector <=> double precision[]`)
— PostgreSQL tidak otomatis meng-cast parameter jadi tipe `vector` dalam
konteks ORDER BY. Diperbaiki dengan cast eksplisit
`embedding <=> %s::vector` dan `register_vector()` dari package
`pgvector` Python untuk konversi list→vector saat INSERT.

**2. Header wajib membuat FastAPI langsung balas 422, bukan 401 custom.**
Slide mengajarkan "panggil /ask tanpa header, harus dapat 401" — tapi
kode awal (`x_api_key: str = Header()`, tanpa default) membuat FastAPI
memvalidasi keberadaan header SEBELUM fungsi dependency sempat jalan,
sehingga header yang hilang total menghasilkan 422 generik, bukan 401
custom seperti yang diajarkan. Diperbaiki dengan
`x_api_key: str | None = Header(default=None)` lalu mengecek `None`
secara eksplisit di dalam fungsi — sekarang header hilang maupun salah
sama-sama menghasilkan 401 yang konsisten, sesuai yang diajarkan di
slide.

Kalau Anda menulis ulang kode ini secara manual, keduanya bug yang mudah
terlewat.

## Alur Pemakaian yang Disarankan

1. `modul2-fastapi/` — jalankan & tunjukkan langsung dengan `uvicorn`
2. `modul3-docker/` — pindah ke Docker, tunjukkan `docker compose up`
   menyalakan 3 service sekaligus
3. `modul4-ingestion/` — isi `.env` dengan API key Gemini asli sebelum
   sesi, jalankan `ingest.py` di depan peserta, lalu demo `/search`

## Prasyarat

- Python 3.11+
- Docker Desktop
- API key Google Gemini — https://ai.google.dev/ (wajib untuk Modul 4)

## Troubleshooting Cepat

Panduan lengkap per OS (termasuk instalasi `uv`/Docker) ada di masing-masing
folder modul (`windows.md`, `macos.md`, `linux.md`) dan di `PANDUAN_LENGKAP.md`.
Gejala paling umum:

| Gejala | Penyebab Umum | Solusi |
|---|---|---|
| `port already in use` / `address already in use` (8000, 5432, atau 6379) | Ada proses lain (server lama, aplikasi lain) masih memakai port itu | Cek proses yang pakai port, lalu matikan, **atau** ubah port kiri pada `docker-compose.yml`/`uvicorn --port` |
| Docker Desktop belum jalan / `docker: command not found` | Docker Desktop belum di-install atau belum dibuka | Install dari docker.com, buka aplikasinya, tunggu status "Running" sebelum `docker compose up` |
| `.env` tidak ditemukan / `GEMINI_API_KEY` kosong | Lupa copy `.env.example` → `.env`, atau belum diisi | `cp .env.example .env` (Windows: `copy .env.example .env`), lalu isi `GEMINI_API_KEY` |
| Perubahan kode tidak muncul | Modul 2: lupa flag `--reload`; Modul 3/4: volume `./app:/app` tidak ter-mount | Modul 2: pakai `uvicorn main:app --reload`; Modul 3/4: cek `docker compose logs app` |

**Cek proses yang memakai sebuah port** (contoh port `8000`, ganti sesuai kebutuhan):

- **macOS / Linux:** `lsof -i :8000`, lalu hentikan dengan `kill -9 <PID>`
- **Windows (PowerShell):** `netstat -ano | findstr :8000`, lalu `taskkill /PID <pid> /F`

Kalau tidak ingin/tidak bisa mematikan proses tersebut, cukup ganti angka
port di sisi **kiri** pemetaan, misalnya `"8001:8000"` di `docker-compose.yml`
lalu akses lewat `localhost:8001`.

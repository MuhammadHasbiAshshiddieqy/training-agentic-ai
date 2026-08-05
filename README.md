# Complete Kit — Modul 2, 3, 4, 7 & 8 (Kode Lengkap)
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
modul2-fastapi/      FastAPI app lengkap (async, Pydantic validation, streaming)
modul3-docker/       + Docker Compose, PostgreSQL(pgvector), Redis, Gemini API
modul4-ingestion/    + Pipeline ingestion lengkap, /search, dan /rag (RAG penuh)
modul7-toolcalling/  + Tool calling: cek_stok_barang, cari_dokumen, endpoint /chat
modul8-agent/        + Agent loop Think-Act-Observe, endpoint /agent
```

**Catatan SDK:** modul 3, 4, 7, dan 8 memakai `google-genai` (paket resmi
terbaru). Paket `google-generativeai` yang lebih lama sudah *deprecated*
sejak Agustus 2025 — jangan pakai itu untuk kode baru.

## Status Verifikasi

Setiap bagian sudah benar-benar dijalankan dan diuji — sebagian besar
**dengan Gemini API key sungguhan** (bukan mock, bukan hanya diperiksa
sintaksnya):

| Modul | Yang Diuji | Hasil |
|---|---|---|
| 2 | Endpoint `/ask`, validasi Pydantic, Dependency Injection (`verify_api_key`), error handling (`/documents/{id}`), konkurensi async, `TestClient` | Semua endpoint merespons benar; DI mengembalikan 401 konsisten baik header hilang maupun salah; 404 jelas untuk id tidak ada |
| 3 | `/db-check` ke PostgreSQL+pgvector sungguhan, `/cache-check` ke Redis sungguhan, `/gemini-test` dengan API key asli (`google-genai`) | Semua endpoint terhubung/merespons dengan benar; `/gemini-test` mengembalikan jawaban Gemini yang sesungguhnya |
| 4 | Chunking + overlap, ingestion ke pgvector, idempotency, `/search`, `/rag` (retrieval + generation) dengan API key asli | Ingest ulang tidak menduplikasi data; `/search` & `/rag` mengembalikan hasil relevan; `/rag` menjawab jujur "tidak tahu" untuk pertanyaan di luar konteks dokumen |
| 7 | `/chat` (tool calling) dengan API key asli: tool `cek_stok_barang`, tool `cari_dokumen`, tanpa tool sama sekali | Ketiganya bekerja benar dengan jawaban Gemini sungguhan; model kadang memanggil tool dua kali berturut-turut (lihat bug #4 di bawah) — skenario "dua tool dalam satu pesan" tidak sempat diuji live karena kuota harian free-tier API key habis |
| 8 | Endpoint dasar (`/health`, `/db-check`, `/cache-check`, `/search`) dengan API key asli; loop `Agent.run()` dan endpoint `/agent` diuji dengan Gemini client di-mock (kuota harian sudah habis dari pengujian Modul 7) | Endpoint dasar semua terhubung normal; loop think-act-observe & pengaman `max_steps` terbukti bekerja benar secara struktural (skenario 2-langkah berhenti tepat waktu, skenario "macet" berhenti paksa di step ke-3) — **coba dengan API key/kuota Anda sendiri** untuk verifikasi keputusan Gemini yang sesungguhnya dalam loop |

## Bug yang Ditemukan & Diperbaiki Selama Pengujian

**1. Query pgvector butuh cast eksplisit.** Query pgvector dengan
parameter Python list biasa gagal (`operator does not exist: vector <=>
double precision[]`) — PostgreSQL tidak otomatis meng-cast parameter
jadi tipe `vector` dalam konteks ORDER BY. Diperbaiki dengan cast
eksplisit `embedding <=> %s::vector` dan `register_vector()` dari
package `pgvector` Python untuk konversi list→vector saat INSERT.

**2. Header wajib membuat FastAPI langsung balas 422, bukan 401 custom.**
Kode awal (`x_api_key: str = Header()`, tanpa default) membuat FastAPI
memvalidasi keberadaan header SEBELUM fungsi dependency sempat jalan,
sehingga header yang hilang total menghasilkan 422 generik, bukan 401
custom. Diperbaiki dengan `x_api_key: str | None = Header(default=None)`
lalu mengecek `None` secara eksplisit di dalam fungsi.

**3. `google-genai==2.16.0` konflik dengan `pydantic==2.9.2`.** SDK baru
mensyaratkan `pydantic>=2.12.5`, tapi `requirements.txt` masih pin versi
lama — `docker compose up --build` gagal total di step `pip install`
(`ResolutionImpossible`). Bug ini tidak pernah ketahuan sampai benar-benar
di-build dengan akses internet. Diperbaiki dengan menaikkan `pydantic` ke
`2.13.4` di modul 3, 4, 7, dan 8.

**4. `/chat` (Modul 7) crash 500 kalau model minta tool call KEDUA
kalinya.** Setelah tool pertama dieksekusi dan hasilnya dikirim balik,
model kadang memutuskan untuk memanggil tool lagi (query pencarian yang
disempurnakan) alih-alih langsung memberi jawaban teks — dalam kasus itu
`final_response.text` bernilai `None`, dan `ChatResponse(answer=None)`
melempar `pydantic.ValidationError` mentah sebagai 500 tanpa pesan jelas.
Karena `/chat` memang sengaja dirancang cuma satu putaran (loop
multi-langkah ada di `/agent` Modul 8), diperbaiki dengan fallback pesan
yang jelas: `answer_text = final_response.text or "Model masih ingin
memanggil tool tambahan..."` — bukan meniadakan skenarionya, tapi
membuatnya gagal dengan anggun.

Kalau kode-kode ini ditulis ulang manual tanpa pengujian nyata,
keempatnya bug yang mudah lolos.

## Alur Pemakaian yang Disarankan

1. `modul2-fastapi/` — jalankan & tunjukkan langsung dengan `uv run uvicorn`
2. `modul3-docker/` — pindah ke Docker, tunjukkan `docker compose up`
   menyalakan 3 service sekaligus
3. `modul4-ingestion/` — isi `.env` dengan API key Gemini asli sebelum
   sesi, jalankan `ingest.py` di depan peserta, demo `/search` lalu `/rag`
   (RAG penuh: retrieval + generation dalam satu endpoint)
4. `modul7-toolcalling/` — demo `/chat`, tunjukkan `tools_called` di
   response supaya peserta lihat keputusan model secara transparan
5. `modul8-agent/` — demo `/agent` dengan goal 2+ langkah, bandingkan
   dengan `/chat` untuk goal yang sama

## Prasyarat

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) — pengelola package Python untuk Modul 2 (lihat panduan per OS di `modul2-fastapi/`)
- Docker Desktop — untuk Modul 3, 4, 7, 8
- API key Google Gemini — https://ai.google.dev/ (wajib mulai Modul 4)

## Troubleshooting Cepat

Panduan lengkap per OS (termasuk instalasi `uv`/Docker) ada di masing-masing
folder modul (`windows.md`, `macos.md`, `linux.md`) dan di `PANDUAN_LENGKAP.md`.
Gejala paling umum:

| Gejala | Penyebab Umum | Solusi |
|---|---|---|
| `port already in use` / `address already in use` (8000, 5432, atau 6379) | Ada proses lain (server lama, aplikasi lain) masih memakai port itu | Cek proses yang pakai port, lalu matikan, **atau** ubah port kiri pada `docker-compose.yml`/`uvicorn --port` |
| Docker Desktop belum jalan / `docker: command not found` | Docker Desktop belum di-install atau belum dibuka | Install dari docker.com, buka aplikasinya, tunggu status "Running" sebelum `docker compose up` |
| `.env` tidak ditemukan / `GEMINI_API_KEY` kosong | Lupa copy `.env.example` → `.env`, atau belum diisi | `cp .env.example .env` (Windows: `copy .env.example .env`), lalu isi `GEMINI_API_KEY` |
| Perubahan kode tidak muncul | Modul 2: lupa flag `--reload`; Modul 3/4/7/8: volume `./app:/app` tidak ter-mount | Modul 2: pakai `uvicorn main:app --reload`; Modul 3/4/7/8: cek `docker compose logs app` |
| `429 RESOURCE_EXHAUSTED` dari Gemini | Kuota free-tier harian habis untuk model `gemini-3.6-flash` (±20 request/hari) | Tunggu, atau pakai API key lain — terutama sebelum demo Modul 7/8 yang butuh beberapa panggilan berurutan |

**Cek proses yang memakai sebuah port** (contoh port `8000`, ganti sesuai kebutuhan):

- **macOS / Linux:** `lsof -i :8000`, lalu hentikan dengan `kill -9 <PID>`
- **Windows (PowerShell):** `netstat -ano | findstr :8000`, lalu `taskkill /PID <pid> /F`

Kalau tidak ingin/tidak bisa mematikan proses tersebut, cukup ganti angka
port di sisi **kiri** pemetaan, misalnya `"8001:8000"` di `docker-compose.yml`
lalu akses lewat `localhost:8001`.

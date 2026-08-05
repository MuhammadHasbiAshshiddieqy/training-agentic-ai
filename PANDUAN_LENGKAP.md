# Panduan Lengkap: Menjalankan Kode Modul 2, 3, 4, 7 & 8
## AI Knowledge Assistant — Human Initiative × Principal Tech Sage

Panduan ini untuk peserta yang **hanya punya Python dan Docker terinstall**
di laptop — tanpa asumsi pengalaman lain. Berlaku untuk **macOS, Windows,
dan Linux**; setiap langkah yang berbeda antar OS ditandai jelas. Tiap
folder modul juga punya panduan run terpisah yang lebih ringkas:
`windows.md`, `macos.md`, `linux.md`.

Dokumen ini mengasumsikan Anda sudah meng-clone/mengekstrak repo ini
(kode sudah lengkap, tinggal jalankan). README di masing-masing folder
kit berisi referensi singkat; dokumen ini adalah panduan langkah-demi-langkah
yang lebih lengkap.

> **Memakai Starter Kit (versi TODO)?** Semua langkah setup di bawah
> ini (uv, Docker, environment variable) tetap sama persis. Bedanya:
> endpoint tidak akan berfungsi sampai TODO terkait di kode selesai
> dikerjakan.

> **Catatan SDK:** seluruh kode di kit ini memakai paket **`google-genai`**
> (SDK resmi terbaru dari Google). Paket `google-generativeai` yang lebih
> lama sudah *deprecated* sejak Agustus 2025 — kalau Anda menemukan
> contoh kode lain yang memakai `import google.generativeai as genai`,
> itu pola yang sudah usang.

> **Catatan Model:** kit ini memakai **`gemini-3.6-flash`** (Gemini 3.x)
> untuk Modul 3, 4, 7, dan 8 — model di bawah versi 3 relatif lebih sering
> gagal/tidak konsisten dalam tool calling. Free tier API key biasanya
> dibatasi ±20 request/hari untuk model ini — kalau dapat error `429
> RESOURCE_EXHAUSTED` saat demo, tunggu beberapa puluh detik lalu coba
> lagi, atau gunakan API key lain untuk sesi demo.

---

## 0. Sebelum Mulai: Cek & Siapkan Prasyarat

### 0.1 Cek apakah Python sudah terinstall

**macOS / Linux:**
```bash
python3 --version
```

**Windows (PowerShell atau Command Prompt):**
```powershell
python --version
```

Harus muncul `Python 3.11` atau lebih baru. Kalau error, install dari
**python.org/downloads** (di Windows, **centang "Add python.exe to PATH"**
saat instalasi) — atau lewati langkah ini sepenuhnya, karena `uv` (lihat
0.3) bisa mengunduh Python 3.11 sendiri tanpa instalasi terpisah.

### 0.2 Cek apakah Docker sudah terinstall & berjalan

```bash
docker --version
docker compose version
```

Kalau error, install **Docker Desktop** dari
docker.com/products/docker-desktop. Setelah install, **buka aplikasi
Docker Desktop-nya dan tunggu sampai statusnya "Running"**.

> **Khusus Windows:** Docker Desktop butuh **WSL2**. Installer modern
> biasanya otomatis mengaktifkan ini; kalau muncul error terkait WSL2
> saat instalasi, ikuti link yang diberikan installer, lalu restart laptop.

### 0.3 Install `uv` (pengelola package Python yang dipakai di Modul 2)

Modul 2 memakai **uv** — pengelola virtual environment & package yang
jauh lebih cepat dari pip biasa, dengan perintah yang **identik di
ketiga OS** (tidak ada lagi cara aktivasi venv yang beda-beda per
platform).

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Tutup dan buka ulang terminal, lalu verifikasi:

```bash
uv --version
```

### 0.4 Cara membuka terminal per OS

| OS | Cara |
|---|---|
| macOS | Buka aplikasi **Terminal** (`Cmd+Space` lalu ketik "Terminal") |
| Windows | Buka **PowerShell** (klik kanan tombol Start → "Terminal") |
| Linux | Buka **Terminal** dari application menu, atau `Ctrl+Alt+T` |

### 0.5 Masuk ke folder kode

```bash
cd path/ke/folder/Complete_Kit_Modul2-4
```

### 0.6 Dapatkan API key Google Gemini

Dibutuhkan mulai Modul 3 (verifikasi) dan wajib mulai Modul 4:

1. Buka **ai.google.dev**, klik "Get API key"
2. Login dengan akun Google, buat API key baru (gratis untuk tingkat percobaan)
3. Salin key-nya — akan dipakai berulang di langkah-langkah berikutnya

---

## 1. Modul 2 — Python & FastAPI (Tanpa Docker)

Modul ini **sengaja dijalankan langsung dengan Python**, belum pakai
Docker — supaya konsep dasarnya jelas dulu.

### 1.1 Masuk ke folder & jalankan

```bash
cd modul2-fastapi
uv venv --python 3.11
uv pip install -r requirements.txt
uv run uvicorn main:app --reload
```

Keempat baris ini **identik persis di macOS, Windows, dan Linux** —
`uv run` otomatis memakai virtual environment yang baru dibuat, tidak
ada langkah "activate" terpisah. `--python 3.11` memastikan environment
memakai Python 3.11+ (kode ini pakai sintaks `str | None` yang butuh
Python 3.10+) — kalau laptop Anda cuma punya Python lama, `uv` akan
mengunduh Python 3.11 sendiri.

Biarkan terminal ini tetap terbuka. Buka browser:

```
http://127.0.0.1:8000/docs
```

### 1.2 Coba endpoint

Di halaman `/docs` (Swagger UI), endpoint `POST /ask` butuh **header**
`x-api-key` dengan nilai `rahasia-latihan` — klik ikon gembok di pojok
kanan atas, atau isi kolom header di form "Try it out".

**Alternatif via terminal:**
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -H "x-api-key: rahasia-latihan" \
  -d "{\"question\": \"Apa itu RAG?\"}"
```

> Di Windows PowerShell, tanda kutip JSON kadang perlu escape berbeda.
> Kalau curl error, gunakan Swagger UI saja.

### 1.3 Menghentikan server

`Ctrl+C` di terminal. Tidak ada langkah "deactivate" yang perlu
dilakukan — `uv run` tidak mengaktifkan apapun secara manual.

### Endpoint yang tersedia di Modul 2

| Endpoint | Method | Keterangan |
|---|---|---|
| `/health` | GET | Cek server hidup |
| `/ask` | POST | Butuh header `x-api-key: rahasia-latihan` |
| `/ask/stream?q=...` | GET | Versi streaming (bonus) |
| `/documents/{doc_id}` | GET | Coba id `1`, `2` (ada) vs `999` (404) |

Penasaran kenapa `main.py` di sini tidak punya `main()`/`server.Run()`
seperti bahasa lain (mis. Go)? Baca `modul2-fastapi/konsep-entrypoint.md`.

---

## 2. Modul 3 — Docker & Local AI Environment

Mulai dari sini, **semua perintah Docker identik di ketiga OS**.

### 2.1 Masuk ke folder Modul 3

```bash
cd ../modul3-docker
```

### 2.2 Siapkan environment variable

**macOS / Linux:** `cp .env.example .env`
**Windows (PowerShell):** `Copy-Item .env.example .env`
**Windows (Command Prompt):** `copy .env.example .env`

Buka `.env` dengan text editor apa saja, isi `GEMINI_API_KEY` dengan key
dari langkah 0.6.

### 2.3 Jalankan semua service

```bash
docker compose up --build
```

Proses pertama kali agak lama (mengunduh image PostgreSQL & Redis).
Buka browser: `http://localhost:8000/docs`

### 2.4 Coba endpoint

- `GET /db-check` → `{"database": "connected", "pgvector": "enabled"}`
- `GET /cache-check` → status `"connected"`
- `GET /gemini-test` → jawaban singkat dari Gemini (butuh API key valid)

### 2.5 Menghentikan service

`Ctrl+C`, lalu `docker compose down` (data Postgres tetap tersimpan di
volume). Untuk hapus total: `docker compose down -v`.

### Endpoint tambahan di Modul 3

| Endpoint | Method | Keterangan |
|---|---|---|
| `/db-check` | GET | Cek koneksi PostgreSQL + aktifkan pgvector |
| `/cache-check` | GET | Cek koneksi Redis |
| `/gemini-test` | GET | Panggilan sederhana ke Gemini API |

---

## 3. Modul 4 — Data Ingestion & Vector Database

### 3.1 Masuk ke folder & siapkan .env

```bash
cd ../modul4-ingestion
cp .env.example .env   # Windows PowerShell: Copy-Item .env.example .env
```
Isi `GEMINI_API_KEY` — **wajib** untuk modul ini.

### 3.2 Jalankan service

```bash
docker compose up --build
```

### 3.3 Jalankan pipeline ingestion

Buka **terminal baru** (jangan tutup yang menjalankan `docker compose up`):

```bash
cd modul4-ingestion   # arahkan ke folder yang sama
docker compose exec app python ingest.py
```

Jalankan lagi kapan saja untuk menguji idempotency (tidak duplikat).

### 3.4 Cek data & coba pencarian

```bash
docker compose exec db psql -U ai_user -d ai_knowledge -c "SELECT id, source_file, chunk_index, left(content, 40) FROM documents;"
```

```
http://localhost:8000/search?query=bagaimana+cara+verifikasi+stok+barang&limit=3
```

### 3.5 Coba RAG penuh (retrieval + generation)

```bash
curl "http://localhost:8000/rag?query=bagaimana%20cara%20verifikasi%20stok%20barang&limit=3"
```

Beda dengan `/search` (yang cuma mengembalikan potongan dokumen mentah),
`/rag` menggabungkan hasil pencarian itu ke dalam prompt dan mengirimnya
ke Gemini — jawabannya (`answer`) adalah jawaban natural berdasarkan isi
dokumen, bukan simulasi.

### Endpoint tambahan di Modul 4

| Endpoint | Method | Keterangan |
|---|---|---|
| `/search?query=...&limit=3` | GET | Pencarian semantik atas dokumen yang di-ingest |
| `/rag?query=...&limit=3` | GET | RAG penuh: retrieval + generation dalam satu endpoint |

---

## 4. Modul 7 — Tool Calling & Function Calling

### 4.1 Masuk ke folder & jalankan

```bash
cd ../modul7-toolcalling
cp .env.example .env   # isi GEMINI_API_KEY jika belum
docker compose up --build
```

Di **terminal baru**, isi data untuk tool `cari_dokumen`:

```bash
cd modul7-toolcalling
docker compose exec app python ingest.py
```

### 4.2 Coba endpoint /chat

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "x-api-key: rahasia-latihan" \
  -d "{\"message\": \"Berapa stok kabel listrik?\"}"
```

Response menampilkan `answer` (jawaban akhir) dan `tools_called` (tool
apa saja yang benar-benar dipanggil, dengan argumen & hasilnya). Coba
juga pesan yang butuh dokumen ("Apa SOP verifikasi stok?") dan pesan
basa-basi ("halo") untuk melihat Gemini memutuskan sendiri kapan tool
dibutuhkan.

> `/chat` di sini sengaja hanya menangani **satu putaran** tool calling.
> Kalau model memutuskan masih ingin memanggil tool lagi setelah putaran
> pertama, `answer` akan berisi pesan yang menjelaskan hal itu (bukan
> error) — arahkan ke `/agent` di Modul 8 untuk kasus seperti ini.

### Endpoint tambahan di Modul 7

| Endpoint | Method | Keterangan |
|---|---|---|
| `/chat` | POST | Chat dengan tool calling — butuh header `x-api-key` |

---

## 5. Modul 8 — Agent Foundation

### 5.1 Masuk ke folder & jalankan

```bash
cd ../modul8-agent
cp .env.example .env
docker compose up --build
```

Di terminal baru: `docker compose exec app python ingest.py`

### 5.2 Coba endpoint /agent

```bash
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -H "x-api-key: rahasia-latihan" \
  -d "{\"goal\": \"Cek stok genset. Kalau kurang dari 5 unit, cari SOP permintaan barang tambahan.\"}"
```

Goal ini butuh **dua tool berurutan**. Response menampilkan `steps` —
jejak lengkap tiap langkah think/act/observe, dan `stopped_reason` yang
menjelaskan kenapa loop berhenti. Bandingkan dengan `/chat` (Modul 7)
untuk goal yang sama.

### Endpoint tambahan di Modul 8

| Endpoint | Method | Keterangan |
|---|---|---|
| `/agent` | POST | Agent multi-langkah — butuh header `x-api-key` |

---

## 6. Troubleshooting Umum

| Gejala | Penyebab Umum | Solusi |
|---|---|---|
| `python: command not found` (macOS/Linux) | Perlu `python3` bukan `python` | Coba `python3`, atau lewati saja — `uv` bisa unduh Python sendiri |
| `'python' is not recognized...` (Windows) | Python belum di PATH | Install ulang, centang "Add python.exe to PATH" — atau lewati, pakai `uv` |
| `uv: command not found` | Terminal belum di-restart setelah install | Tutup & buka ulang terminal |
| Docker Desktop tidak mau start | Belum terinstall/dibuka | Install dari docker.com, buka aplikasinya, tunggu "Running" |
| Windows: Docker minta WSL2 | WSL2 belum aktif | Ikuti link installer, restart laptop |
| `port is already allocated` | Port 8000/5432/6379 dipakai proses lain | Lihat cek-port di bawah, atau ganti port di `docker-compose.yml` |
| `db-check` gagal terus | Container `db` belum siap | Tunggu beberapa detik; cek `docker compose logs db` |
| `429 RESOURCE_EXHAUSTED` dari Gemini | Kuota free-tier harian habis untuk model tersebut | Tunggu ±1 menit dan coba lagi, atau ganti API key |
| `gemini-test`/`chat`/`agent` error API key | `.env` belum diisi/salah | Cek ulang `GEMINI_API_KEY`, tanpa spasi/kutip ekstra |
| Endpoint `/chat` atau `/agent` error "tool tidak dikenali" | `tools.py` belum lengkap (starter kit) | Selesaikan TODO di `tools.py` dulu |

### Cek proses yang memakai sebuah port

**macOS / Linux:** `lsof -i :8000`
**Windows (PowerShell):** `netstat -ano | findstr :8000`

---

## 7. Ringkasan Perintah Cepat (Cheat Sheet)

```bash
# === MODUL 2 (tanpa Docker) ===
cd modul2-fastapi
uv venv --python 3.11
uv pip install -r requirements.txt
uv run uvicorn main:app --reload

# === MODUL 3 (Docker) ===
cd ../modul3-docker
cp .env.example .env
docker compose up --build

# === MODUL 4 (Docker + ingestion + RAG) ===
cd ../modul4-ingestion
cp .env.example .env
docker compose up --build
docker compose exec app python ingest.py   # terminal baru
curl "http://localhost:8000/rag?query=bagaimana+cara+verifikasi+stok+barang&limit=3"

# === MODUL 7 (Docker + tool calling) ===
cd ../modul7-toolcalling
cp .env.example .env
docker compose up --build
docker compose exec app python ingest.py   # terminal baru
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -H "x-api-key: rahasia-latihan" -d "{\"message\": \"Berapa stok kabel listrik?\"}"

# === MODUL 8 (Docker + agent) ===
cd ../modul8-agent
cp .env.example .env
docker compose up --build
docker compose exec app python ingest.py   # terminal baru
curl -X POST http://localhost:8000/agent -H "Content-Type: application/json" \
  -H "x-api-key: rahasia-latihan" -d "{\"goal\": \"Cek stok genset, kalau kurang dari 5 cari SOP terkait\"}"
```

---

*Human Initiative × Principal Tech Sage — Modul 2, 3, 4, 7 & 8*

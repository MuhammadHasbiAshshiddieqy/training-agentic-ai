# Panduan Lengkap: Menjalankan Kode Modul 2, 3 & 4
## AI Knowledge Assistant — Human Initiative × Principal Tech Sage

Panduan ini untuk peserta yang **hanya punya Python dan Docker terinstall**
di laptop — tanpa asumsi pengalaman lain. Berlaku untuk **macOS, Windows,
dan Linux**; setiap langkah yang berbeda antar OS ditandai jelas.

Dokumen ini mengasumsikan Anda menggunakan **Complete_Kit_Modul2-4.zip**
(kode sudah lengkap, tinggal jalankan). README di masing-masing folder
kit berisi referensi singkat; dokumen ini adalah panduan langkah-demi-langkah
yang lebih lengkap.

> **Memakai Starter_Kit_Modul2-4.zip (versi TODO)?** Semua langkah setup di
> bawah ini (venv, Docker, environment variable) tetap sama persis. Bedanya:
> endpoint tidak akan berfungsi sampai TODO terkait di kode selesai
> dikerjakan — jadi wajar kalau langkah "coba endpoint" belum berhasil
> sebelum bagian TODO-nya selesai.

---

## 0. Sebelum Mulai: Cek & Siapkan Prasyarat

### 0.1 Cek apakah Python sudah terinstall

Buka terminal (lihat cara membuka terminal per OS di bawah), lalu jalankan:

**macOS / Linux:**
```bash
python3 --version
```

**Windows (PowerShell atau Command Prompt):**
```powershell
python --version
```

Harus muncul `Python 3.11` atau lebih baru. Kalau muncul error "command not
found" / "tidak dikenali", install dulu dari **python.org/downloads**
(saat instalasi di Windows, **centang "Add python.exe to PATH"** — ini
langkah yang paling sering terlewat).

### 0.2 Cek apakah Docker sudah terinstall & berjalan

```bash
docker --version
docker compose version
```

Kalau error, install **Docker Desktop** dari docker.com/products/docker-desktop
(tersedia untuk macOS, Windows, dan Linux). Setelah install, **buka aplikasi
Docker Desktop-nya dan tunggu sampai statusnya "Running"** (ada ikon paus di
menu bar/system tray) — perintah `docker` tidak akan jalan kalau aplikasinya
belum dibuka.

> **Khusus Windows:** Docker Desktop butuh **WSL2** (Windows Subsystem for
> Linux). Installer modern biasanya otomatis mengaktifkan ini; kalau muncul
> error terkait WSL2 saat instalasi, ikuti link yang diberikan installer
> untuk mengaktifkan WSL2 di Windows Features, lalu restart laptop.

### 0.3 Cara membuka terminal per OS

| OS | Cara |
|---|---|
| macOS | Buka aplikasi **Terminal** (Spotlight: `Cmd+Space` lalu ketik "Terminal") |
| Windows | Buka **PowerShell** (klik kanan tombol Start → "Windows PowerShell" atau "Terminal") |
| Linux | Buka **Terminal** dari application menu, atau `Ctrl+Alt+T` di kebanyakan distro |

Semua perintah di panduan ini dijalankan di terminal tersebut.

### 0.4 Ekstrak kode

Unduh dan ekstrak `Complete_Kit_Modul2-4.zip`:

- **macOS**: double-click file zip di Finder
- **Windows**: klik kanan → "Extract All..."
- **Linux**: klik kanan → "Extract Here", atau `unzip Complete_Kit_Modul2-4.zip`

Lalu arahkan terminal ke folder hasil ekstrak:

```bash
cd path/ke/folder/Complete_Kit_Modul2-4
```

(Ganti `path/ke/folder/...` dengan lokasi sebenarnya — bisa juga ketik `cd `
lalu **drag folder-nya ke jendela terminal** untuk mengisi path otomatis di
macOS/Linux, atau di Windows Explorer klik address bar dan ketik `cmd`/`powershell`
untuk membuka terminal langsung di folder itu.)

---

## 1. Modul 2 — Python & FastAPI (Tanpa Docker)

Modul ini **sengaja dijalankan langsung dengan Python**, belum pakai
Docker — supaya konsep dasarnya jelas dulu sebelum masuk kompleksitas
container di Modul 3.

### 1.1 Masuk ke folder Modul 2

```bash
cd modul2-fastapi
```

### 1.2 Buat & aktifkan virtual environment

Virtual environment (venv) menjaga package Python untuk proyek ini
terpisah dari instalasi Python lain di laptop Anda.

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

> **Kalau PowerShell menolak menjalankan script** (error tentang
> "execution policy"), jalankan perintah ini SEKALI di PowerShell (sebagai
> user biasa, bukan admin), lalu ulangi langkah aktivasi:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

Setelah aktif, prompt terminal Anda akan berubah, biasanya diawali `(venv)`.

### 1.3 Install dependencies

```bash
pip install -r requirements.txt
```

(Sama persis untuk ketiga OS setelah venv aktif.)

### 1.4 Jalankan server

```bash
uvicorn main:app --reload
```

Biarkan terminal ini tetap terbuka (server berjalan selama terminal ini
aktif). Buka browser ke:

```
http://127.0.0.1:8000/docs
```

Ini adalah **Swagger UI** — cara termudah dan seragam di semua OS untuk
mencoba setiap endpoint tanpa perlu mengetik perintah curl.

### 1.5 Coba endpoint

Di halaman `/docs`, klik endpoint `POST /ask` → "Try it out" → isi body
JSON seperti berikut → "Execute":

```json
{
  "question": "Apa itu RAG?",
  "max_results": 3
}
```

Endpoint `/ask` butuh **header** `x-api-key` dengan nilai `rahasia-latihan`
— di Swagger UI, klik ikon gembok di pojok kanan atas halaman, atau isi
kolom header yang tersedia di form "Try it out".

**Alternatif via terminal (opsional):**

**macOS / Linux / Windows (curl sudah tersedia bawaan sejak Windows 10):**
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -H "x-api-key: rahasia-latihan" \
  -d "{\"question\": \"Apa itu RAG?\"}"
```

> Di Windows PowerShell, tanda kutip dalam JSON kadang perlu escape
> berbeda. Kalau curl di atas error, gunakan Swagger UI saja — lebih aman
> dan tidak tergantung shell yang dipakai.

### 1.6 Menghentikan server

Tekan `Ctrl+C` di terminal tempat `uvicorn` berjalan. Untuk keluar dari
venv setelah selesai:

```bash
deactivate
```

### Endpoint yang tersedia di Modul 2

| Endpoint | Method | Keterangan |
|---|---|---|
| `/health` | GET | Cek server hidup |
| `/ask` | POST | Butuh header `x-api-key: rahasia-latihan` |
| `/ask/stream?q=...` | GET | Versi streaming (bonus) |
| `/documents/{doc_id}` | GET | Coba id `1`, `2` (ada) vs `999` (404) |

---

## 2. Modul 3 — Docker & Local AI Environment

Mulai dari sini, **semua perintah Docker identik di ketiga OS** — ini
justru salah satu manfaat utama Docker yang akan Anda buktikan sendiri.

### 2.1 Keluar dari folder Modul 2, masuk ke folder Modul 3

```bash
cd ../modul3-docker
```

(Kalau Anda masih dalam venv Modul 2, venv itu tidak berpengaruh ke
Docker — boleh dibiarkan aktif atau `deactivate` dulu, bebas.)

### 2.2 Siapkan file environment variable

**macOS / Linux:**
```bash
cp .env.example .env
```

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**Windows (Command Prompt):**
```cmd
copy .env.example .env
```

Buka file `.env` yang baru dibuat dengan text editor apa saja (VS Code,
Notepad, TextEdit, nano) dan isi `GEMINI_API_KEY` dengan API key Anda
(cara mendapatkannya ada di bagian 3.1 — boleh dilewati dulu untuk Modul
3, endpoint `/db-check` dan `/cache-check` tidak butuh API key ini).

### 2.3 Jalankan semua service

```bash
docker compose up --build
```

Perintah ini sama persis di macOS, Windows, dan Linux. Tunggu sampai log
berhenti bergulir dan terlihat pesan aplikasi FastAPI sudah "running" —
proses pertama kali agak lama karena Docker mengunduh image PostgreSQL
dan Redis.

Biarkan terminal ini tetap terbuka. Buka browser:

```
http://localhost:8000/docs
```

### 2.4 Coba endpoint

Di Swagger UI, coba (tidak butuh header apapun untuk dua endpoint ini):

- `GET /db-check` → harus mengembalikan `{"database": "connected", "pgvector": "enabled"}`
- `GET /cache-check` → harus mengembalikan status `"connected"`
- `GET /gemini-test` → butuh `GEMINI_API_KEY` valid di `.env` (lihat bagian 3.1)

### 2.5 Menghentikan service

Tekan `Ctrl+C` di terminal, lalu:

```bash
docker compose down
```

Data di PostgreSQL **tetap tersimpan** setelah ini (disimpan di Docker
volume). Kalau ingin benar-benar menghapus semua data dan mulai dari nol:

```bash
docker compose down -v
```

### Endpoint yang tersedia di Modul 3 (tambahan dari Modul 2)

| Endpoint | Method | Keterangan |
|---|---|---|
| `/db-check` | GET | Cek koneksi PostgreSQL + aktifkan pgvector |
| `/cache-check` | GET | Cek koneksi Redis |
| `/gemini-test` | GET | Panggilan sederhana ke Gemini API |

---

## 3. Modul 4 — Data Ingestion & Vector Database

### 3.1 Dapatkan API key Google Gemini (kalau belum)

1. Buka **ai.google.dev**, klik "Get API key"
2. Login dengan akun Google, buat API key baru (gratis untuk tingkat percobaan)
3. Salin key-nya

### 3.2 Masuk ke folder Modul 4 & siapkan .env

```bash
cd ../modul4-ingestion
```

**macOS / Linux:** `cp .env.example .env`
**Windows (PowerShell):** `Copy-Item .env.example .env`
**Windows (Command Prompt):** `copy .env.example .env`

Buka `.env`, isi `GEMINI_API_KEY` dengan key dari langkah 3.1. **Ini
langkah wajib** — tanpa API key valid, pipeline ingestion tidak akan
bisa membuat embedding.

### 3.3 Jalankan service

```bash
docker compose up --build
```

Sama seperti Modul 3, biarkan terminal ini terbuka.

### 3.4 Jalankan pipeline ingestion

Buka **terminal baru** (jangan tutup terminal yang menjalankan
`docker compose up`), masuk ke folder `modul4-ingestion` lagi, lalu:

```bash
docker compose exec app python ingest.py
```

Perintah ini identik di ketiga OS — dijalankan **di dalam container**,
jadi tidak peduli OS host Anda apa. Anda akan melihat progress ingestion
di layar, diakhiri ringkasan jumlah dokumen & chunk yang tersimpan.

Jalankan lagi kapan saja untuk menguji idempotency — tidak akan
menduplikasi data.

### 3.5 Cek data tersimpan (opsional)

```bash
docker compose exec db psql -U ai_user -d ai_knowledge -c "SELECT id, source_file, chunk_index, left(content, 40) FROM documents;"
```

### 3.6 Coba pencarian semantik

Di Swagger UI (`http://localhost:8000/docs`), coba `GET /search` dengan
query, misalnya `bagaimana cara verifikasi stok barang` — atau lewat
browser langsung:

```
http://localhost:8000/search?query=bagaimana+cara+verifikasi+stok+barang&limit=3
```

Coba juga dengan kata yang **tidak sama persis** dengan isi dokumen untuk
membuktikan pencarian ini berbasis makna, bukan kata kunci.

### Endpoint yang tersedia di Modul 4 (tambahan)

| Endpoint | Method | Keterangan |
|---|---|---|
| `/search?query=...&limit=3` | GET | Pencarian semantik atas dokumen yang sudah di-ingest |

---

## 4. Troubleshooting Umum

| Gejala | Penyebab Umum | Solusi |
|---|---|---|
| `python: command not found` (macOS/Linux) | Python belum terinstall, atau perlu `python3` bukan `python` | Coba `python3`; install dari python.org kalau belum ada |
| `'python' is not recognized...` (Windows) | Python belum di-tambahkan ke PATH saat instalasi | Install ulang dari python.org, centang "Add python.exe to PATH" |
| `docker: command not found` / Docker Desktop tidak mau start | Docker Desktop belum terinstall atau belum dibuka | Install dari docker.com, buka aplikasinya, tunggu status "Running" |
| Windows: Docker Desktop minta WSL2 | WSL2 belum aktif | Ikuti link yang diberikan installer, aktifkan WSL2, restart laptop |
| `port is already allocated` / `address already in use` | Port 8000/5432/6379 sudah dipakai proses lain | Lihat solusi cek-port di bawah, atau matikan proses tersebut |
| `db-check` gagal terus-menerus | Container `db` belum sepenuhnya siap | Tunggu beberapa detik lagi; cek `docker compose logs db` |
| PowerShell menolak `Activate.ps1` | Execution policy default Windows membatasi script | Jalankan `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` sekali |
| Perubahan di `main.py` tidak muncul setelah disimpan | Modul 2: lupa `--reload`; Modul 3/4: volume mount bermasalah | Modul 2: pastikan pakai `uvicorn main:app --reload`; Modul 3/4: cek `docker compose logs app` |
| `gemini-test` / `ingest.py` gagal dengan pesan API key | `.env` belum diisi atau salah isi | Cek ulang `GEMINI_API_KEY` di file `.env`, tidak ada spasi/tanda kutip ekstra |

### Cek proses yang memakai sebuah port

**macOS / Linux:**
```bash
lsof -i :8000
```

**Windows (PowerShell):**
```powershell
netstat -ano | findstr :8000
```

Kalau ada proses lain memakai port itu, hentikan proses tersebut, atau
ubah port di sisi kiri pemetaan port pada `docker-compose.yml` (mis.
`"8001:8000"` supaya diakses lewat `localhost:8001`).

---

## 5. Ringkasan Perintah Cepat (Cheat Sheet)

```bash
# === MODUL 2 (tanpa Docker) ===
cd modul2-fastapi
python3 -m venv venv              # Windows: python -m venv venv
source venv/bin/activate          # Windows PowerShell: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
# buka http://127.0.0.1:8000/docs

# === MODUL 3 (Docker) ===
cd ../modul3-docker
cp .env.example .env              # Windows PowerShell: Copy-Item .env.example .env
# isi GEMINI_API_KEY di .env
docker compose up --build
# buka http://localhost:8000/docs

# === MODUL 4 (Docker + ingestion) ===
cd ../modul4-ingestion
cp .env.example .env              # Windows PowerShell: Copy-Item .env.example .env
# isi GEMINI_API_KEY di .env
docker compose up --build
# di terminal BARU:
docker compose exec app python ingest.py
# buka http://localhost:8000/search?query=...
```

---

*Human Initiative × Principal Tech Sage — Modul 2, 3 & 4*

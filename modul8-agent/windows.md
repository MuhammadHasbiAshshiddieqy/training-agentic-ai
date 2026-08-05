# Cara Menjalankan (Windows)

Modul ini berjalan lewat Docker Compose (FastAPI + PostgreSQL/pgvector + Redis), jadi tidak perlu install Python/uv sama sekali di Windows — cukup Docker.

## 1. Install Docker Desktop

1. Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) dan install.
2. Saat instalasi, pastikan opsi **"Use WSL 2 instead of Hyper-V"** aktif (default).
3. Restart komputer jika diminta, lalu buka Docker Desktop dan tunggu sampai statusnya "Running".
4. Cek di PowerShell:

```powershell
docker --version
docker compose version
```

## 2. Siapkan file `.env`

```powershell
copy .env.example .env
```

Buka `.env`, isi `GEMINI_API_KEY` (**wajib** — dapatkan gratis di https://ai.google.dev/).

## 3. Jalankan

```powershell
cd modul8-agent
docker compose up --build
```

Tunggu sampai ketiga container (`app`, `db`, `redis`) siap, lalu buka:
- http://localhost:8000/docs

## 4. Jalankan pipeline ingestion

Di terminal baru (biarkan `docker compose up` tetap jalan):

```powershell
docker compose exec app python ingest.py
```

Ini mengisi data untuk tool `cari_dokumen` (membaca `.txt` di `sample_docs/`, membuat embedding, menyimpan ke tabel `documents`). Aman dijalankan berkali-kali (idempotent).

## 5. Coba agent multi-langkah lewat /agent

```powershell
curl -X POST http://localhost:8000/agent `
  -H "Content-Type: application/json" `
  -H "x-api-key: rahasia-latihan" `
  -d '{\"goal\": \"Cek stok genset. Kalau kurang dari 5 unit, cari SOP permintaan barang tambahan.\"}'
```

Goal ini butuh **dua tool berurutan** (cek stok dulu, baru putuskan perlu
cari SOP atau tidak). Response menampilkan `steps` — jejak lengkap tiap
iterasi think/act/observe, plus `stopped_reason`.

## 6. Berhenti

Tekan `Ctrl+C` di terminal utama, lalu (opsional):

```powershell
docker compose down
```

## Troubleshooting

| Gejala | Solusi |
|---|---|
| `WSL 2 installation is incomplete` | Jalankan `wsl --install` di PowerShell (Administrator), restart, lalu buka Docker Desktop lagi |
| `port already in use` (8000/5432/6379) | Cek proses yang pakai port: `netstat -ano \| findstr :8000`, lalu `taskkill /PID <pid> /F` |
| `ingest.py` gagal / embedding error | Pastikan `GEMINI_API_KEY` di `.env` sudah benar, lalu `docker compose restart app` |
| Perubahan kode tidak muncul | Pastikan volume `./app:/app` ter-mount dan `--reload` aktif di `Dockerfile` |

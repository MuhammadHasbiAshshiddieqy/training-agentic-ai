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
cd modul9-semanticcache
docker compose up --build
```

Tunggu sampai ketiga container (`app`, `db`, `redis`) siap, lalu buka:
- http://localhost:8000/docs

## 4. Jalankan pipeline ingestion

Di terminal baru (biarkan `docker compose up` tetap jalan):

```powershell
docker compose exec app python ingest.py
```

## 5. Coba semantic cache lewat /chat

```powershell
curl -X POST http://localhost:8000/chat `
  -H "Content-Type: application/json" `
  -H "x-api-key: rahasia-latihan" `
  -d '{\"message\": \"Apa SOP distribusi logistik bantuan?\"}'
```

Ulangi dengan kalimat yang MAKNANYA sama tapi kata-katanya beda, mis.
`"Bagaimana prosedur distribusi bantuan logistik?"` — perhatikan
`cache_hit: true` dan `latency_ms` yang jauh lebih kecil di response kedua.

Cek statistik cache:

```powershell
curl http://localhost:8000/cache-stats
```

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
| `/chat` selalu `cache_hit: false` | Cek `/cache-stats` — kalau `semantic_cache.hits` tetap 0, coba turunkan `SEMANTIC_CACHE_THRESHOLD` di `.env` (mis. `0.90`) |
| Perubahan kode tidak muncul | Pastikan volume `./app:/app` ter-mount dan `--reload` aktif di `Dockerfile` |

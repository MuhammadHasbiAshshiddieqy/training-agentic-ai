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

`LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` **opsional** — kosongkan dulu
kalau belum punya akun Langfuse, aplikasi tetap jalan normal tanpa
tracing. Daftar gratis di https://cloud.langfuse.com kapan saja untuk
mengaktifkannya nanti (lihat README.md).

## 3. Jalankan

```powershell
cd modul11-observability
docker compose up --build
```

Tunggu sampai ketiga container (`app`, `db`, `redis`) siap, lalu buka:
- http://localhost:8000/docs

## 4. Jalankan pipeline ingestion

Di terminal baru (biarkan `docker compose up` tetap jalan):

```powershell
docker compose exec app python ingest.py
```

## 5. Coba evaluasi otomatis

```powershell
docker compose exec app python evaluate.py
```

Jalankan **dua kali berturut-turut** — run kedua akan menunjukkan lebih
banyak `cache_hit` (efek Modul 9) dan latensi server yang lebih rendah.

## 6. (Opsional) Lihat trace di Langfuse

Isi `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` di `.env` (Settings → API
Keys di dashboard Langfuse), lalu:

```powershell
docker compose restart app
curl http://localhost:8000/gemini-test
```

Buka dashboard Langfuse → menu **Traces** untuk melihat trace pertama Anda.

## 7. Berhenti

Tekan `Ctrl+C` di terminal utama, lalu (opsional):

```powershell
docker compose down
```

## Troubleshooting

| Gejala | Solusi |
|---|---|
| `WSL 2 installation is incomplete` | Jalankan `wsl --install` di PowerShell (Administrator), restart, lalu buka Docker Desktop lagi |
| `port already in use` (8000/5432/6379) | Cek proses yang pakai port: `netstat -ano \| findstr :8000`, lalu `taskkill /PID <pid> /F` |
| Log `Context error: No active span in current context` | Normal kalau `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` belum diisi — bukan bug, tracing memang nonaktif |
| Tidak ada trace baru muncul di dashboard Langfuse | Cek `.env` sudah benar lalu `docker compose restart app`; trace terkirim async, tunggu beberapa detik |
| `evaluate.py` gagal `requests.exceptions.ConnectionError` | Pastikan `docker compose up` masih jalan di terminal lain dan ingest.py sudah pernah dijalankan |

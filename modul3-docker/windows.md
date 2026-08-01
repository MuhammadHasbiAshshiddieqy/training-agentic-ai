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

Buka `.env` dengan text editor, isi `GEMINI_API_KEY` dengan API key dari https://ai.google.dev/.

## 3. Jalankan

```powershell
cd modul3-docker
docker compose up --build
```

Tunggu sampai ketiga container (`app`, `db`, `redis`) siap, lalu buka:
- http://localhost:8000/docs

## 4. Berhenti

Tekan `Ctrl+C`, lalu (opsional) bersihkan container:

```powershell
docker compose down
```

## Troubleshooting

| Gejala | Solusi |
|---|---|
| `WSL 2 installation is incomplete` | Jalankan `wsl --install` di PowerShell (Administrator), restart, lalu buka Docker Desktop lagi |
| `port already in use` (8000/5432/6379) | Cek proses yang pakai port: `netstat -ano \| findstr :8000`, lalu `taskkill /PID <pid> /F`, atau ganti mapping port di `docker-compose.yml` |
| Docker Desktop lambat / hang | Pastikan virtualization aktif di BIOS, dan alokasikan lebih banyak RAM di Docker Desktop → Settings → Resources |
| Perubahan kode tidak muncul | Pastikan volume `./app:/app` ter-mount dan `--reload` aktif di `Dockerfile` |

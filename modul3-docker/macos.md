# Cara Menjalankan (macOS)

Modul ini berjalan lewat Docker Compose (FastAPI + PostgreSQL/pgvector + Redis), jadi tidak perlu install Python/uv sama sekali di macOS — cukup Docker.

## 1. Install Docker Desktop

```bash
brew install --cask docker
```

Atau download langsung dari https://www.docker.com/products/docker-desktop/ (pilih Apple Silicon/Intel sesuai chip Mac Anda).

Buka aplikasi **Docker.app** sekali agar daemon-nya jalan, lalu cek:

```bash
docker --version
docker compose version
```

## 2. Siapkan file `.env`

```bash
cp .env.example .env
```

Buka `.env`, isi `GEMINI_API_KEY` dengan API key dari https://ai.google.dev/.

## 3. Jalankan

```bash
cd modul3-docker
docker compose up --build
```

Tunggu sampai ketiga container (`app`, `db`, `redis`) siap, lalu buka:
- http://localhost:8000/docs

## 4. Berhenti

Tekan `Ctrl+C`, lalu (opsional) bersihkan container:

```bash
docker compose down
```

## Troubleshooting

| Gejala | Solusi |
|---|---|
| Docker Desktop tidak mau start | Buka lewat Spotlight (`Cmd+Space` → "Docker"), tunggu ikon whale di menu bar stabil |
| `port already in use` (8000/5432/6379) | Cek proses yang pakai port: `lsof -i :8000`, lalu `kill -9 <PID>`, atau ganti mapping port di `docker-compose.yml` |
| Build lambat di Apple Silicon | Image `python:3.11-slim` sudah multi-arch, biasanya tidak masalah — kalau ada image lain yang lambat, tambahkan `platform: linux/amd64` di service terkait |
| Perubahan kode tidak muncul | Pastikan volume `./app:/app` ter-mount dan `--reload` aktif di `Dockerfile` |

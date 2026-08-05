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

Buka `.env`, isi `GEMINI_API_KEY` (**wajib** — dapatkan gratis di https://ai.google.dev/).

## 3. Jalankan

```bash
cd modul8-agent
docker compose up --build
```

Tunggu sampai ketiga container (`app`, `db`, `redis`) siap, lalu buka:
- http://localhost:8000/docs

## 4. Jalankan pipeline ingestion

Di terminal baru (biarkan `docker compose up` tetap jalan):

```bash
docker compose exec app python ingest.py
```

Ini mengisi data untuk tool `cari_dokumen` (membaca `.txt` di `sample_docs/`, membuat embedding, menyimpan ke tabel `documents`). Aman dijalankan berkali-kali (idempotent).

## 5. Coba agent multi-langkah lewat /agent

```bash
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -H "x-api-key: rahasia-latihan" \
  -d '{"goal": "Cek stok genset. Kalau kurang dari 5 unit, cari SOP permintaan barang tambahan."}'
```

Goal ini butuh **dua tool berurutan** (cek stok dulu, baru putuskan perlu
cari SOP atau tidak). Response menampilkan `steps` — jejak lengkap tiap
iterasi think/act/observe, plus `stopped_reason`.

## 6. Berhenti

Tekan `Ctrl+C` di terminal utama, lalu (opsional):

```bash
docker compose down
```

## Troubleshooting

| Gejala | Solusi |
|---|---|
| Docker Desktop tidak mau start | Buka lewat Spotlight (`Cmd+Space` → "Docker"), tunggu ikon whale di menu bar stabil |
| `port already in use` (8000/5432/6379) | Cek proses yang pakai port: `lsof -i :8000`, lalu `kill -9 <PID>` |
| `ingest.py` gagal / embedding error | Pastikan `GEMINI_API_KEY` di `.env` sudah benar, lalu `docker compose restart app` |
| Perubahan kode tidak muncul | Pastikan volume `./app:/app` ter-mount dan `--reload` aktif di `Dockerfile` |

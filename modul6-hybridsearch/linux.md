# Cara Menjalankan (Linux)

Modul ini berjalan lewat Docker Compose (FastAPI + PostgreSQL/pgvector + Redis), jadi tidak perlu install Python/uv sama sekali di Linux — cukup Docker Engine.

## 1. Install Docker Engine + Compose plugin

Debian/Ubuntu:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
```

Fedora:

```bash
sudo dnf install -y docker docker-compose-plugin
sudo systemctl enable --now docker
```

Agar tidak perlu `sudo` tiap kali (opsional, perlu re-login setelahnya):

```bash
sudo usermod -aG docker $USER
```

Cek instalasi:

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
cd modul6-hybridsearch
docker compose up --build
```

Tunggu sampai ketiga container (`app`, `db`, `redis`) siap, lalu buka:
- http://localhost:8000/docs

## 4. Jalankan pipeline ingestion

Di terminal baru (biarkan `docker compose up` tetap jalan):

```bash
docker compose exec app python ingest.py
```

Ini membaca 2 dokumen contoh di `sample_docs/`, membuat embedding, DAN membentuk kolom `content_tsv` + index GIN untuk full-text search (fondasi hybrid search). Aman dijalankan berkali-kali (idempotent).

## 5. Coba Hybrid Search (vector + keyword + RRF + rerank)

```bash
curl "http://localhost:8000/search?query=ambang%20batas%20nilai%20pengadaan&limit=2"
```

Query dengan istilah spesifik seperti ini akan terbantu keyword search.
Perhatikan `rrf_score` di tiap `sources` — dokumen yang muncul di KEDUA
metode pencarian (vector & keyword) naik ke atas.

## 6. Berhenti

Tekan `Ctrl+C` di terminal utama, lalu (opsional):

```bash
docker compose down
```

## Troubleshooting

| Gejala | Solusi |
|---|---|
| `permission denied` saat akses `/var/run/docker.sock` | Jalankan dengan `sudo`, atau tambahkan user ke grup `docker` (lihat langkah 1) lalu logout/login |
| `port already in use` (8000/5432/6379) | Cek proses yang pakai port: `sudo ss -ltnp \| grep 8000`, lalu `kill -9 <PID>` |
| `ingest.py` gagal / embedding error | Pastikan `GEMINI_API_KEY` di `.env` sudah benar, lalu `docker compose restart app` |
| Perubahan kode tidak muncul | Pastikan volume `./app:/app` ter-mount dan `--reload` aktif di `Dockerfile` |

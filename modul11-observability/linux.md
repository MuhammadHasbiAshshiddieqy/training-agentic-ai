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

`LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` **opsional** — kosongkan dulu
kalau belum punya akun Langfuse, aplikasi tetap jalan normal tanpa
tracing. Daftar gratis di https://cloud.langfuse.com kapan saja untuk
mengaktifkannya nanti (lihat README.md).

## 3. Jalankan

```bash
cd modul11-observability
docker compose up --build
```

Tunggu sampai ketiga container (`app`, `db`, `redis`) siap, lalu buka:
- http://localhost:8000/docs

## 4. Jalankan pipeline ingestion

Di terminal baru (biarkan `docker compose up` tetap jalan):

```bash
docker compose exec app python ingest.py
```

## 5. Coba evaluasi otomatis

```bash
docker compose exec app python evaluate.py
```

Jalankan **dua kali berturut-turut** — run kedua akan menunjukkan lebih
banyak `cache_hit` (efek Modul 9) dan latensi server yang lebih rendah.

## 6. (Opsional) Lihat trace di Langfuse

Isi `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` di `.env` (Settings → API
Keys di dashboard Langfuse), lalu:

```bash
docker compose restart app
curl http://localhost:8000/gemini-test
```

Buka dashboard Langfuse → menu **Traces** untuk melihat trace pertama Anda.

## 7. Berhenti

Tekan `Ctrl+C` di terminal utama, lalu (opsional):

```bash
docker compose down
```

## Troubleshooting

| Gejala | Solusi |
|---|---|
| `permission denied` saat akses `/var/run/docker.sock` | Jalankan dengan `sudo`, atau tambahkan user ke grup `docker` (lihat langkah 1) lalu logout/login |
| `port already in use` (8000/5432/6379) | Cek proses yang pakai port: `sudo ss -ltnp \| grep 8000`, lalu `kill -9 <PID>` |
| Log `Context error: No active span in current context` | Normal kalau `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` belum diisi — bukan bug, tracing memang nonaktif |
| Tidak ada trace baru muncul di dashboard Langfuse | Cek `.env` sudah benar lalu `docker compose restart app`; trace terkirim async, tunggu beberapa detik |
| `evaluate.py` gagal `requests.exceptions.ConnectionError` | Pastikan `docker compose up` masih jalan di terminal lain dan ingest.py sudah pernah dijalankan |

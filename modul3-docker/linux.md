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
| `permission denied` saat akses `/var/run/docker.sock` | Jalankan dengan `sudo`, atau tambahkan user ke grup `docker` (lihat langkah 1) lalu logout/login |
| `port already in use` (8000/5432/6379) | Cek proses yang pakai port: `sudo ss -ltnp \| grep 8000`, lalu `kill -9 <PID>`, atau ganti mapping port di `docker-compose.yml` |
| Docker daemon tidak jalan | `sudo systemctl status docker`, kalau mati: `sudo systemctl start docker` |
| Perubahan kode tidak muncul | Pastikan volume `./app:/app` ter-mount dan `--reload` aktif di `Dockerfile` |

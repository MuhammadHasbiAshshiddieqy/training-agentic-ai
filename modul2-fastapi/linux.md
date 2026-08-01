# Cara Menjalankan (Linux)

## 1. Install `uv`

Buka terminal, jalankan:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Muat ulang shell config lalu cek:

```bash
source ~/.bashrc   # atau ~/.zshrc kalau pakai zsh
uv --version
```

## 2. Masuk ke folder modul

```bash
cd modul2-fastapi
```

## 3. Buat environment & install dependency

```bash
uv venv --python 3.11
uv pip install -r requirements.txt
```

> Kode ini butuh Python 3.10+ (pakai sintaks `str | None`). Kalau distro
> Anda hanya punya Python versi lama terinstall, `uv` akan otomatis
> mengunduh Python 3.11 sendiri — tidak perlu install manual.

## 4. Jalankan server

```bash
uv run uvicorn main:app --reload
```

Tidak perlu `source venv/bin/activate` — `uv run` otomatis memakai environment yang baru dibuat.

Buka di browser:
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/health

## Troubleshooting

| Gejala | Solusi |
|---|---|
| `uv: command not found` setelah install | Tambahkan `~/.local/bin` ke `PATH` (biasanya sudah otomatis di script installer), lalu buka terminal baru |
| `port already in use` | Cek proses yang pakai port 8000: `lsof -i :8000` atau `ss -ltnp \| grep 8000`, lalu `kill -9 <PID>` |
| Distro tidak punya `curl` | Install dulu: `sudo apt install curl` (Debian/Ubuntu) atau `sudo dnf install curl` (Fedora) |

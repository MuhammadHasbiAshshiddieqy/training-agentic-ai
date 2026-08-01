# Cara Menjalankan (macOS)

## 1. Install `uv`

Buka **Terminal**, jalankan salah satu:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

atau kalau sudah pakai Homebrew:

```bash
brew install uv
```

Cek sudah terpasang:

```bash
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

> Kode ini butuh Python 3.10+ (pakai sintaks `str | None`). Kalau macOS Anda
> hanya punya Python versi lama terinstall (mis. `python3` bawaan Command
> Line Tools yang biasanya 3.9), `uv` akan otomatis mengunduh Python 3.11
> sendiri — tidak perlu install manual.

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
| `command not found: uv` setelah install | Buka terminal baru, atau jalankan `source ~/.zshrc` (atau `~/.bash_profile`) |
| `port already in use` | Cek proses yang pakai port 8000: `lsof -i :8000`, lalu `kill -9 <PID>` |
| macOS memblokir binary yang di-download | Buka **System Settings → Privacy & Security**, izinkan aplikasi yang diblokir |

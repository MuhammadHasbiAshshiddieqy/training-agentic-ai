# Cara Menjalankan (Windows)

## 1. Install `uv`

Buka **PowerShell**, jalankan:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Tutup lalu buka ulang terminal, cek sudah terpasang:

```powershell
uv --version
```

## 2. Masuk ke folder modul

```powershell
cd modul2-fastapi
```

## 3. Buat environment & install dependency

```powershell
uv venv --python 3.11
uv pip install -r requirements.txt
```

> Kode ini butuh Python 3.10+ (pakai sintaks `str | None`). Kalau laptop
> Anda hanya punya Python versi lama terinstall, `uv` akan otomatis
> mengunduh Python 3.11 sendiri — tidak perlu install manual.

## 4. Jalankan server

```powershell
uv run uvicorn main:app --reload
```

Tidak perlu `venv\Scripts\activate` — `uv run` otomatis memakai environment yang baru dibuat.

Buka di browser:
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/health

## Troubleshooting

| Gejala | Solusi |
|---|---|
| `uv` tidak dikenali setelah install | Tutup & buka ulang PowerShell (PATH baru ter-load setelah restart) |
| `port already in use` | Cek proses yang pakai port 8000: `netstat -ano \| findstr :8000`, lalu `taskkill /PID <pid> /F` |
| Error izin menjalankan script `.ps1` | Jalankan PowerShell **as Administrator**, atau pakai `-ExecutionPolicy ByPass` seperti di atas |

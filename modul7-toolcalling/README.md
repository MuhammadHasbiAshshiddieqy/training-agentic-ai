# Modul 7 — Tool Calling & Function Calling (Lengkap)

Kode di folder ini sudah lengkap: dua tool (`cek_stok_barang`,
`cari_dokumen`) dan endpoint `/chat` yang memakai Gemini function calling.

## Cara Menjalankan

Panduan lengkap (install Docker, siapkan `.env`, jalankan Compose, isi data
untuk tool `cari_dokumen`) dipisah per OS:

- [windows.md](windows.md)
- [macos.md](macos.md)
- [linux.md](linux.md)

Ringkas:

```bash
cp .env.example .env
# WAJIB isi GEMINI_API_KEY
docker compose up --build
docker compose exec app python ingest.py   # isi data untuk tool cari_dokumen
```

## Endpoint Baru

| Endpoint | Method | Keterangan |
|---|---|---|
| `/chat` | POST | Chat dengan tool calling — butuh header `x-api-key` |

## Coba Sendiri

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "x-api-key: rahasia-latihan" \
  -d '{"message": "Berapa stok kabel listrik?"}'
```

Response menampilkan `answer` (jawaban akhir) dan `tools_called` (daftar
tool yang benar-benar dipanggil, dengan argumen dan hasilnya) — supaya
Anda bisa lihat persis apa yang terjadi di balik layar.

Coba juga pesan yang butuh dokumen ("Apa SOP untuk verifikasi stok?")
dan pesan yang tidak butuh tool sama sekali ("Halo, apa kabar?") untuk
melihat Gemini memutuskan sendiri kapan tool dibutuhkan.

## Tools yang Tersedia (lihat `app/tools.py`)

- **cek_stok_barang** — simulasi API ERP, mengecek stok barang di
  dictionary statis (`kabel listrik`, `terpal`, `air mineral`, `genset`)
- **cari_dokumen** — membungkus pencarian semantik pgvector dari Modul 4
  sebagai tool

## Sudah Diverifikasi

Endpoint `/chat` sudah diuji dengan Gemini API yang di-mock (karena
sandbox pembuatan kit tidak punya akses ke domain Google AI): skenario
satu tool terpanggil, tanpa tool sama sekali, dan dua tool sekaligus
dalam satu pesan — ketiganya bekerja dengan benar secara struktural.
**Coba dengan API key Anda sendiri** untuk memverifikasi keputusan
Gemini yang sesungguhnya (kapan ia memilih memanggil tool).

**Bug yang ditemukan saat pengujian:** parameter `id=...` yang muncul di
beberapa contoh dokumentasi resmi Google untuk
`Part.from_function_response()` ternyata TIDAK didukung di versi SDK
stabil yang dipakai kit ini (`google-genai==2.16.0`) — akan muncul
`TypeError` kalau ditambahkan. Kode di sini sudah tanpa parameter itu.

## Menuju Modul 8

`/chat` di sini memutuskan tool HANYA SATU KALI per pesan. Modul 8
membangun loop di atas fondasi yang sama supaya model bisa memanggil
tool berkali-kali secara berurutan dalam satu permintaan.

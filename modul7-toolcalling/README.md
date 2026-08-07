# Modul 7 — Tool Calling & Function Calling (Lengkap)

Kode di folder ini sudah lengkap: dua tool (`cek_stok_barang`,
`cari_dokumen`) dan endpoint `/chat` yang memakai Gemini function calling.

Dibawa maju dari Modul 4-6: endpoint `/search` DAN tool `cari_dokumen`
sama-sama memakai pipeline **Hybrid Search + rerank + context assembly**
(lihat `app/retrieval.py`) — bukan vector search polos ala Modul 4.
`retrieval.py` dipisah dari `main.py`/`tools.py` supaya keduanya bisa
memakai pipeline yang sama tanpa circular import.

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
| `/search` | GET | Dibawa maju dari Modul 6 — Hybrid Search + rerank + context assembly, sekarang dengan filter `category` (lihat Modul 5/6 untuk detail) |

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
- **cari_dokumen** — membungkus pipeline Hybrid Search + rerank dari
  `retrieval.py` (Modul 5/6) sebagai tool — kualitas retrieval yang
  **sama persis** dengan endpoint `/search`, bukan versi yang lebih
  sederhana

## Sudah Diverifikasi

Diuji end-to-end dengan **API key Gemini sungguhan** (bukan mock):
`/chat` dengan tool `cek_stok_barang`, tool `cari_dokumen` (hybrid
search + rerank), dan tanpa tool sama sekali — ketiganya menghasilkan
jawaban Gemini yang benar dan relevan. Model kadang memutuskan memanggil
tool KEDUA kalinya setelah putaran pertama (lihat catatan bug di README
root) — `/chat` memberi pesan yang jelas untuk kasus itu, bukan crash.

**Bug yang ditemukan saat pengujian:** parameter `id=...` yang muncul di
beberapa contoh dokumentasi resmi Google untuk
`Part.from_function_response()` ternyata TIDAK didukung — tapi kode di
sini memakai `types.FunctionResponse(id=..., ...)` langsung (bukan
lewat classmethod itu), dan itu **terbukti didukung** saat diuji live.

## Menuju Modul 8

`/chat` di sini memutuskan tool HANYA SATU KALI per pesan. Modul 8
membangun loop di atas fondasi yang sama supaya model bisa memanggil
tool berkali-kali secara berurutan dalam satu permintaan.

# Modul 8 — Agent Foundation (Lengkap)

Kode di folder ini sudah lengkap: kelas `Agent` dengan loop
Think-Act-Observe (`app/agent.py`) dan endpoint `/agent`.

Dibawa maju dari Modul 4-6: endpoint `/search` DAN tool `cari_dokumen`
(dipakai agent) sama-sama memakai pipeline **Hybrid Search + rerank +
context assembly** (lihat `app/retrieval.py`) — bukan vector search
polos ala Modul 4.

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
docker compose exec app python ingest.py
```

## Endpoint Baru

| Endpoint | Method | Keterangan |
|---|---|---|
| `/agent` | POST | Agent multi-langkah — butuh header `x-api-key` |
| `/search` | GET | Dibawa maju dari Modul 6 — Hybrid Search + rerank + context assembly, dengan filter `category` |

Body: `{"goal": "...", "max_steps": 5}` (`max_steps` opsional, default 5)

## Coba Sendiri

```bash
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -H "x-api-key: rahasia-latihan" \
  -d '{"goal": "Cek stok genset. Kalau kurang dari 5 unit, cari SOP permintaan barang tambahan."}'
```

Goal ini butuh **dua tool berurutan**: cek stok dulu, baru berdasarkan
hasilnya (angka di bawah 5 atau tidak) agent memutuskan apakah perlu
mencari SOP. Response menampilkan `steps` — jejak lengkap tiap iterasi
think/act/observe, plus `stopped_reason` yang menjelaskan kenapa loop
berhenti (`model_gave_final_answer` atau `max_steps_reached`).

Bandingkan dengan `/chat` dari Modul 7 (satu putaran saja) untuk goal
yang sama — `/chat` tidak akan bisa menangani logika bersyarat ini
dengan benar dalam satu kali panggilan.

## Sudah Diverifikasi

Loop `Agent.run()` dan endpoint `/agent` sudah diuji dengan **API key
Gemini sungguhan** (bukan mock): goal yang butuh `cari_dokumen` (hybrid
search + rerank) berhasil dijawab benar dalam 2 langkah
(`model_gave_final_answer`), dan goal 2-tool berurutan (cek stok →
keputusan cari SOP berdasarkan hasilnya) berhasil dalam 4 langkah.
Skenario "macet" (model terus minta tool tanpa akhir) diuji dengan
Gemini client di-mock — pengaman `max_steps` terbukti menghentikan loop
paksa, tidak berjalan tanpa henti.

## Menuju Modul 9

Setiap iterasi THINK di loop ini adalah satu panggilan API — untuk goal
yang butuh banyak langkah, ini bisa jadi mahal & lambat. Modul 9
(Semantic Cache) akan membahas cara mengurangi biaya ini.

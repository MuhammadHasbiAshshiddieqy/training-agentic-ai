# Modul 8 — Agent Foundation (Lengkap)

Kode di folder ini sudah lengkap: kelas `Agent` dengan loop
Think-Act-Observe (`app/agent.py`) dan endpoint `/agent`.

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

Loop `Agent.run()` sudah diuji lewat panggilan langsung maupun lewat
endpoint `/agent` via HTTP sungguhan, dengan Gemini API yang di-mock:

- Skenario 2 langkah (cek stok → keputusan cari SOP → jawaban akhir) —
  loop berhenti dengan benar di langkah ke-3 setelah dapat jawaban final
- Skenario "macet" (model terus minta tool tanpa akhir) — pengaman
  `max_steps` terbukti menghentikan loop paksa, tidak berjalan tanpa
  henti

**Coba dengan API key Anda sendiri** untuk memverifikasi perilaku Gemini
yang sesungguhnya dalam memutuskan kapan berhenti memanggil tool.

## Menuju Modul 9

Setiap iterasi THINK di loop ini adalah satu panggilan API — untuk goal
yang butuh banyak langkah, ini bisa jadi mahal & lambat. Modul 9
(Semantic Cache) akan membahas cara mengurangi biaya ini.

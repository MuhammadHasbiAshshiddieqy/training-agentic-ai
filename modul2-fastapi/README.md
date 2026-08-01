# Modul 2 — Python & FastAPI untuk AI (Lengkap)

Kode di folder ini sudah lengkap dan siap dijalankan langsung.

## Cara Menjalankan

Panduan lengkap (install `uv`, buat environment, jalankan server) dipisah per OS:

- [windows.md](windows.md)
- [macos.md](macos.md)
- [linux.md](linux.md)

Setelah server jalan, buka:
- http://127.0.0.1:8000/docs — Swagger UI, coba endpoint langsung dari browser
- http://127.0.0.1:8000/health — cek server hidup

## Endpoint yang Tersedia

| Endpoint | Method | Keterangan |
|---|---|---|
| `/health` | GET | Cek server hidup |
| `/ask` | POST | Endpoint utama — butuh header `x-api-key: rahasia-latihan` |
| `/ask/stream?q=...` | GET | Versi streaming (kata per kata), bonus demo pola untuk Modul 5 |
| `/documents/{doc_id}` | GET | Contoh error handling — coba id `1`, `2` (ada) vs `999` (404) |

## Coba Sendiri

```bash
# Request tanpa header x-api-key -> 401
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Apa itu RAG?"}'

# Request valid (dengan header)
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -H "x-api-key: rahasia-latihan" \
  -d '{"question": "Apa itu RAG?"}'

# Request tidak valid (ditolak oleh Pydantic)
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -H "x-api-key: rahasia-latihan" \
  -d '{"question": "???"}'
```

Untuk melihat efek async, panggil `/ask` 5 kali secara bersamaan (5 tab
browser atau 5 terminal `curl` sekaligus, jangan lupa header
`x-api-key`) — totalnya tetap ~1.5 detik, bukan ~7.5 detik.

## Sudah Diverifikasi

Endpoint ini sudah diuji berjalan: validasi Pydantic menolak input tidak
valid dengan benar, dependency `verify_api_key` mengembalikan 401 yang
konsisten baik saat header hilang maupun salah, `/documents/{doc_id}`
mengembalikan 404 yang jelas untuk id yang tidak ada, dan tiga request
bersamaan terbukti selesai dalam ~1.5 detik (bukan 3×1.5 detik),
membuktikan `async`/`await` bekerja.

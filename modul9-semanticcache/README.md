# Modul 9 — Semantic Cache (Lengkap)

Kode di folder ini sudah lengkap: cache dua lapis di atas Redis
(`app/cache.py`) yang dipasang di `/search` (embedding cache) dan `/chat`
(semantic response cache), plus endpoint `/cache-stats` dan `/cache/clear`.

Dibawa maju dari Modul 8: `/search`, tool `cari_dokumen`, dan `/agent`
tidak berubah logikanya — yang baru murni soal caching di atasnya. Kode
modul ini sendiri tidak punya lapisan guardrails — lihat
[`modul10-guardrails/`](../modul10-guardrails/) yang membawa maju cache
Modul 9 ini apa adanya lalu menambahkan input/output guardrail di
`/chat` dan `/agent`.

## Kenapa Semantic Cache?

Setiap panggilan ke Gemini (baik `embed_content` maupun `generate_content`)
punya biaya token DAN latensi. Untuk asisten yang dipakai berulang oleh
banyak orang, pertanyaan yang mirip/identik muncul terus-menerus — "berapa
stok kabel listrik?" hari ini, "stok kabel listrik ada berapa?" besok.
Tanpa cache, tiap pertanyaan itu memanggil API dari nol.

Dua lapis cache di modul ini:

| Lapis | Jenis Match | Dipakai di | Menghemat |
|---|---|---|---|
| Embedding cache | Exact-match (hash teks) | `/search`, tool `cari_dokumen` | Panggilan `embed_content` |
| Semantic response cache | Similarity-match (cosine embedding) | `/chat` | Panggilan `generate_content` (bisa 2x per chat) |

## Cara Menjalankan

Panduan lengkap per OS:

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
| `/cache-stats` | GET | Hit/miss embedding cache & semantic cache, jumlah entry aktif |
| `/cache/clear` | POST | Hapus semua entry cache & reset statistik — butuh header `x-api-key` |

## Endpoint yang Berubah Perilakunya

| Endpoint | Perubahan |
|---|---|
| `/search` | Embedding query sekarang lewat cache exact-match — cek `/cache-stats` sebelum & sesudah query yang sama diulang |
| `/chat` | Response sekarang punya field `cache_hit`, `cache_similarity`, `cacheable`, `latency_ms` |

## Coba Sendiri

```bash
# Panggilan pertama - MISS, cache_hit: false, latency lebih tinggi
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" -H "x-api-key: rahasia-latihan" \
  -d '{"message": "Apa ambang batas nilai pengadaan yang wajib tender terbuka?"}'

# Panggilan kedua dengan pertanyaan SEMAKNA (bukan exact sama) - harus HIT
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" -H "x-api-key: rahasia-latihan" \
  -d '{"message": "Berapa batas nilai pengadaan yang mengharuskan tender terbuka?"}'

# Lihat statistik cache
curl http://localhost:8000/cache-stats
```

Bandingkan `latency_ms` di kedua response `/chat` di atas — panggilan kedua
seharusnya jauh lebih cepat karena tidak menyentuh Gemini `generate_content`
sama sekali. Sudah diuji nyata: `latency_ms: 11527` (MISS) turun jadi
`latency_ms: 484` (HIT, `cache_similarity: 0.982`) — 24x lebih cepat.

## Trade-off yang Sengaja Dibahas, Bukan Disembunyikan

- **Staleness data transaksional.** Jawaban yang melibatkan tool
  `cek_stok_barang` SENGAJA tidak disimpan ke semantic cache (lihat
  `REALTIME_TOOLS` di `main.py`) — stok barang berubah kapan saja, beda
  dengan isi SOP/kebijakan yang relatif statis. Field `cacheable` di
  response `/chat` menunjukkan ini secara eksplisit ke peserta.
- **False positive similarity.** Threshold default `0.95` cukup ketat,
  tapi dua pertanyaan yang embeddingnya kebetulan mirip TAPI maksudnya
  beda tetap mungkin salah kena cache. Ini bahan diskusi yang baik: kapan
  ambang batas perlu dinaikkan, dan risiko apa yang muncul kalau
  diturunkan.
- **Skala.** `SemanticCache.get()` membandingkan query baru ke SEMUA entry
  aktif secara manual di Python (dibatasi `SEMANTIC_CACHE_MAX_SCAN`) —
  cukup untuk latihan, tapi bukan pendekatan yang dipakai di skala jutaan
  entry (lihat komentar di `cache.py` soal RediSearch).

## Sudah Diverifikasi

Diuji end-to-end dengan API key Gemini sungguhan (sebelumnya hanya
diverifikasi lewat unit test dengan `embed_text`/`generate_content`
di-mock):

- **Cache MISS → HIT**: `latency_ms: 11527` (MISS) turun jadi
  `latency_ms: 484` (HIT, `cache_similarity: 0.982`) — 24x lebih cepat,
  jawaban identik persis di kedua response.
- **`cacheable: false` untuk data transaksional**: pertanyaan "Berapa
  stok genset?" (memanggil `cek_stok_barang`, ada di `REALTIME_TOOLS`)
  terbukti `cacheable: false` — tidak pernah masuk semantic cache.
- `/db-check`, `/cache-check`, `/search` (dengan embedding cache),
  `/cache-stats` semua merespons benar.

## Menuju Modul 10 & 11

Dua kelanjutan berbeda dibangun di atas modul ini:
[`modul10-guardrails/`](../modul10-guardrails/) menambahkan input/output
guardrail di `/chat` dan `/agent` (termasuk verdict guardrail yang ikut
tersimpan di cache). [`modul11-observability/`](../modul11-observability/)
menambahkan instrumentasi Langfuse ke seluruh pipeline (termasuk cache
hit/miss) dan skrip evaluasi otomatis — dibawa maju langsung dari Modul 9
ini, **belum** menyertakan guardrail dari Modul 10.

# Modul 11 — Observability & Evaluation (Lengkap)

Kode di folder ini sudah lengkap: instrumentasi tracing Langfuse
(`app/observability.py`) di seluruh pipeline (retrieval, tool calling,
agent, cache hit/miss dari Modul 9), plus skrip evaluasi otomatis
(`app/evaluate.py`) yang menembak endpoint sendiri dan menilai kualitas
jawaban pakai Gemini-as-judge.

Dibawa maju dari Modul 9 apa adanya, hanya menambah lapisan observability
di atasnya. **Modul ini belum menyertakan guardrail dari
[`modul10-guardrails/`](../modul10-guardrails/)** — modul itu ditambahkan
belakangan sebagai jalur terpisah dari Modul 9, jadi belum digabung ke
sini. Lihat root `README.md` untuk status lengkap urutan modul di kit ini.

## Kenapa Observability & Evaluation?

Sampai Modul 9, satu-satunya cara tahu "apakah sistem ini bekerja dengan
baik" adalah membaca response JSON satu per satu, atau mengintip log
container. Itu tidak bisa diskalakan begitu ada banyak user/query:

- **Observability** (Langfuse) menjawab "APA yang terjadi di dalam satu
  request?" — trace lengkap think→act→observe untuk agent, tiap tahap
  retrieval untuk /search, token & latensi tiap panggilan Gemini, kapan
  cache kena/tidak.
- **Evaluation** (`evaluate.py`) menjawab "APAKAH sistem ini masih bekerja
  dengan baik?" — dijalankan berkala terhadap set pertanyaan tetap,
  menghasilkan skor yang bisa dibandingkan dari waktu ke waktu (mis.
  setelah ganti model, ganti prompt, atau ganti strategi chunking).

## Cara Menjalankan

Panduan lengkap per OS:

- [windows.md](windows.md)
- [macos.md](macos.md)
- [linux.md](linux.md)

Ringkas:

```bash
cp .env.example .env
# WAJIB isi GEMINI_API_KEY
# OPSIONAL isi LANGFUSE_PUBLIC_KEY & LANGFUSE_SECRET_KEY (daftar gratis di cloud.langfuse.com)
docker compose up --build
docker compose exec app python ingest.py
docker compose exec app python evaluate.py
```

## Yang Baru

| Bagian | Keterangan |
|---|---|
| `app/observability.py` | Konfigurasi Langfuse (SDK v4, berbasis OpenTelemetry) + helper `log_gemini_usage()` & `log_cache_event()` |
| `app/evaluate.py` | Skrip evaluasi mandiri — `docker compose exec app python evaluate.py` |
| `/health` | Sekarang menampilkan `observability_enabled` (True kalau LANGFUSE_* terisi) |
| `/search`, `/chat`, `/agent`, `/gemini-test` | Ter-instrumentasi penuh — tiap request jadi satu trace Langfuse |
| `retrieval.py` | Tiap tahap (`vector_search`, `keyword_search`, `rrf_merge`, `rerank_candidates`, `assemble_context`) jadi observation tersendiri |
| `tools.py` | `cek_stok_barang` & `cari_dokumen` jadi observation `as_type="tool"` |
| `agent.py` | Tiap iterasi THINK jadi observation `as_type="generation"`, seluruh `run()` jadi trace `as_type="agent"` |

## Melihat Trace di Langfuse

1. Daftar gratis di https://cloud.langfuse.com, buat project baru.
2. Settings → API Keys → salin **Public Key** dan **Secret Key**, isi ke `.env`.
3. `docker compose restart app` (supaya env var baru terbaca).
4. Panggil endpoint apa saja (`/gemini-test` yang paling sederhana untuk mulai), lalu buka dashboard Langfuse → menu **Traces**.

Tanpa mengisi `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`, aplikasi tetap
berjalan normal — tracing otomatis nonaktif (lihat komentar di
`observability.py`). Anda mungkin melihat baris log
`Context error: No active span in current context` di `docker compose logs
app` kalau kredensial belum diisi — ini **normal**, bukan bug.

## Coba Evaluasi Otomatis

```bash
docker compose exec app python evaluate.py
```

Skrip ini menembak `/search` dan `/chat` dengan 8 pertanyaan tetap
(`EVAL_SET` di `evaluate.py`), mengecek apakah dokumen yang relevan
benar-benar ketemu, apakah tool yang tepat dipanggil, dan meminta Gemini
menilai kualitas jawaban 0-10. Jalankan **dua kali berturut-turut** untuk
melihat efek semantic cache Modul 9 — run kedua akan menunjukkan lebih
banyak `cache_hit` dan `Latensi server rata-rata` yang jauh lebih rendah.

Kalau `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` terisi, hasil evaluasi
(termasuk skor per pertanyaan) juga masuk ke Langfuse sebagai trace
`evaluation-run` — bisa dibandingkan antar run dari dashboard.

## Belum Diverifikasi Live

Berbeda dari Modul 2-8 (yang sudah diuji dengan API key Gemini
sungguhan), kode di modul ini **belum dijalankan dengan API key
Gemini/Langfuse asli** di lingkungan pembuatannya — API resmi Langfuse
v4 (`Langfuse`, `observe`, `get_client`, `update_current_generation`,
`update_current_span`, `score_current_span`) sudah diverifikasi lewat
`pip install langfuse` + inspeksi signature langsung, dan seluruh alur
kode (`/chat` dengan cache, `/search` dengan retrieval penuh, `Agent.run`,
`evaluate.py`) sudah diuji end-to-end dengan Gemini & Redis di-mock —
tapi belum ada percobaan dengan project Langfuse sungguhan (butuh akun).
Uji dulu dengan API key Anda sendiri sebelum dipakai untuk sesi
pelatihan.

## Menuju Modul Selanjutnya

Evaluasi otomatis di modul ini baru mengecek relevansi jawaban — belum
mengecek hal-hal yang jadi fokus [`modul10-guardrails/`](../modul10-guardrails/)
seperti prompt injection atau validasi output ketat. Menggabungkan
observability (modul ini) dengan guardrails (Modul 10) — misalnya
mencatat verdict `is_grounded`/`is_safe` sebagai trace Langfuse — adalah
perluasan wajar kalau kit ini disatukan lebih lanjut.

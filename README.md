# Complete Kit — Modul 2-11 (Kode Lengkap)
## AI Knowledge Assistant — Human Initiative × Principal Tech Sage

> **Baru pertama kali menjalankan kit ini?** Baca **`PANDUAN_LENGKAP.md`**
> di folder ini dulu — panduan langkah-demi-langkah untuk macOS, Windows,
> dan Linux, ditulis dengan asumsi hanya Python & Docker yang sudah
> terinstall.

Berbeda dari **Starter_Kit_Modul2-4.zip** (yang berisi kerangka + TODO
untuk latihan peserta), kit ini berisi **kode yang sudah lengkap dan siap
jalan** — cocok untuk demo langsung, referensi trainer, atau dibagikan ke
peserta yang tinggal ingin clone & jalankan tanpa mengerjakan TODO.

```
modul2-fastapi/         FastAPI app lengkap (async, Pydantic validation, streaming)
modul3-docker/          + Docker Compose, PostgreSQL(pgvector), Redis, Gemini API
modul4-ingestion/       + Pipeline ingestion lengkap, /search, dan /rag (RAG penuh)
modul5-productionrag/   + Metadata filtering, reranking (Gemini), context assembly
modul6-hybridsearch/    + Hybrid Search: vector + keyword (full-text) via RRF
modul7-toolcalling/     + Tool calling: cek_stok_barang, cari_dokumen, endpoint /chat
modul8-agent/           + Agent loop Think-Act-Observe, endpoint /agent
modul9-semanticcache/   + Semantic cache Redis: embedding cache (exact) + response cache (similarity) di /chat
modul10-guardrails/     + Input/output guardrail (prompt injection, LLM-as-judge grounded+safe) di /chat & /agent
modul11-observability/  + Tracing Langfuse full pipeline + evaluate.py (Gemini-as-judge, skor otomatis)
```

> **Catatan percabangan modul 9-11:** kit ini dibangun dalam beberapa
> tahap terpisah, jadi rantai "tiap modul membawa maju modul sebelumnya"
> bercabang mulai Modul 9, bukan satu garis lurus:
>
> ```
> Modul 8 ──► Modul 9 ──┬──► Modul 10 (guardrails, TIDAK mengandung observability)
>                        └──► Modul 11 (observability, TIDAK mengandung guardrails)
> ```
>
> `modul10-guardrails/` dan `modul11-observability/` **sama-sama** dibawa
> maju langsung dari `modul9-semanticcache/`, tapi **belum digabung satu
> sama lain** — Modul 11 belum meng-instrumentasi guardrail Modul 10, dan
> Modul 10 belum punya tracing Langfuse ala Modul 11. Lihat "Status
> Verifikasi" di bawah untuk detail apa yang sudah/belum diuji tiap modul.

**Setiap modul membawa maju kode modul sebelumnya** — bukan berdiri
sendiri-sendiri (kecuali percabangan 9→10 dan 9→11 di atas). Yang paling
terlihat: endpoint `/search` dan tool `cari_dokumen` di Modul 7-10
sama-sama memakai pipeline Hybrid Search + rerank dari Modul 5/6 (lihat
`app/retrieval.py`), bukan vector search polos ala Modul 4.

**Catatan SDK:** modul 3-11 memakai `google-genai` (paket resmi terbaru).
Paket `google-generativeai` yang lebih lama sudah *deprecated* sejak
Agustus 2025 — jangan pakai itu untuk kode baru.

## Status Verifikasi

Setiap bagian sudah benar-benar dijalankan dan diuji — sebagian besar
**dengan Gemini API key sungguhan** (bukan mock, bukan hanya diperiksa
sintaksnya):

| Modul | Yang Diuji | Hasil |
|---|---|---|
| 2 | Endpoint `/ask`, validasi Pydantic, Dependency Injection (`verify_api_key`), error handling (`/documents/{id}`), konkurensi async, `TestClient` | Semua endpoint merespons benar; DI mengembalikan 401 konsisten baik header hilang maupun salah; 404 jelas untuk id tidak ada |
| 3 | `/db-check` ke PostgreSQL+pgvector sungguhan, `/cache-check` ke Redis sungguhan, `/gemini-test` dengan API key asli (`google-genai`) | Semua endpoint terhubung/merespons dengan benar; `/gemini-test` mengembalikan jawaban Gemini yang sesungguhnya |
| 4 | Chunking + overlap, ingestion ke pgvector, idempotency, `/search`, `/rag` (retrieval + generation) dengan API key asli | Ingest ulang tidak menduplikasi data; `/search` & `/rag` mengembalikan hasil relevan; `/rag` menjawab jujur "tidak tahu" untuk pertanyaan di luar konteks dokumen |
| 5 | `/search` dengan metadata filter (`category`) dan reranking Gemini (structured output `response_schema`) dengan API key asli | `candidates_retrieved` (10) vs `candidates_after_rerank` (`limit`) sesuai desain; filter kategori terbukti mengubah jumlah kandidat; kategori yang tidak match mengembalikan hasil kosong (bukan crash) |
| 6 | `/search` hybrid (vector + keyword + RRF) dengan API key asli; kolom `content_tsv` + index GIN diverifikasi lewat `\d documents` | Query istilah spesifik ("ambang batas nilai pengadaan") berhasil ditemukan lewat full-text search; `rrf_score` naik untuk dokumen yang muncul di kedua metode pencarian |
| 7 | `/chat` (tool calling) dengan API key asli: tool `cek_stok_barang`, tool `cari_dokumen` (memakai pipeline hybrid+rerank dari Modul 5/6), tanpa tool sama sekali | Ketiganya bekerja benar dengan jawaban Gemini sungguhan; model kadang memanggil tool dua kali berturut-turut (lihat bug #4 di bawah) — skenario "dua tool dalam satu pesan" tidak sempat diuji live karena kuota harian free-tier API key habis |
| 8 | Endpoint dasar dengan API key asli; endpoint `/agent` diuji **live** dua kali: goal 2 tool berurutan (`gemini-3.5-flash`, kuota `gemini-3.6-flash` sedang habis), dan goal yang butuh `cari_dokumen` hybrid (`gemini-3.6-flash`, setelah kuota pulih); loop `Agent.run()` juga diuji dengan Gemini client di-mock untuk skenario pengaman `max_steps` | Agent benar-benar melakukan langkah think-act-observe nyata dan berhenti tepat dengan `stopped_reason: model_gave_final_answer` di kedua goal; skenario "macet" (mock) berhenti paksa tepat di `max_steps` |
| 9 | **Belum diuji dengan API key Gemini sungguhan.** `cache.py` (embedding cache + semantic cache) diuji dengan Redis lokal ASLI tapi `embed_text`/`generate_content` di-mock: exact-match, cosine similarity threshold, lazy cleanup entry kedaluwarsa, dan alur penuh `/chat` (cache hit/miss, `latency_ms`, pengecualian `REALTIME_TOOLS`) lewat FastAPI `TestClient` | Semua unit test & test integrasi lulus; belum ada percobaan dengan Gemini API key asli |
| 10 | Dibangun di atas Modul 9 + guardrails (`app/guardrails.py`). Diuji **live** dengan API key Gemini asli: input guardrail (`/chat` & `/agent`), output guardrail cache MISS→HIT, `/agent` 2-tool | Input guardrail menolak prompt injection dengan `400` sebelum cache/Gemini disentuh; cache MISS `latency_ms: 25423` vs cache HIT `latency_ms: 573` (44x lebih cepat) dengan `guardrail` **identik persis** di kedua response (bukti verdict diambil dari cache, bukan dihitung ulang); output guardrail terbukti menilai isi secara nyata — menandai `is_grounded: false` saat `/chat` jatuh ke pesan fallback bug #4 (bukan jawaban sungguhan) |
| 11 | **Belum diuji dengan API key Gemini/Langfuse sungguhan.** API resmi `langfuse` v4 (`observe`, `get_client`, `update_current_generation/span`, `score_current_span`) diverifikasi lewat `pip install langfuse` + inspeksi signature langsung (bukan tebakan/ingatan versi lama) untuk memastikan tidak memakai API v2 yang sudah deprecated; seluruh endpoint & `evaluate.py` diuji dengan Gemini + Redis di-mock, termasuk memastikan `@observe` tidak menyebabkan crash saat kredensial Langfuse kosong (graceful degrade) | Semua unit test & test integrasi lulus; belum ada percobaan dengan project Langfuse maupun Gemini API key sungguhan |

## Bug yang Ditemukan & Diperbaiki Selama Pengujian

**1. Query pgvector butuh cast eksplisit.** Query pgvector dengan
parameter Python list biasa gagal (`operator does not exist: vector <=>
double precision[]`) — PostgreSQL tidak otomatis meng-cast parameter
jadi tipe `vector` dalam konteks ORDER BY. Diperbaiki dengan cast
eksplisit `embedding <=> %s::vector` dan `register_vector()` dari
package `pgvector` Python untuk konversi list→vector saat INSERT.

**2. Header wajib membuat FastAPI langsung balas 422, bukan 401 custom.**
Kode awal (`x_api_key: str = Header()`, tanpa default) membuat FastAPI
memvalidasi keberadaan header SEBELUM fungsi dependency sempat jalan,
sehingga header yang hilang total menghasilkan 422 generik, bukan 401
custom. Diperbaiki dengan `x_api_key: str | None = Header(default=None)`
lalu mengecek `None` secara eksplisit di dalam fungsi.

**3. `google-genai==2.16.0` konflik dengan `pydantic==2.9.2`.** SDK baru
mensyaratkan `pydantic>=2.12.5`, tapi `requirements.txt` masih pin versi
lama — `docker compose up --build` gagal total di step `pip install`
(`ResolutionImpossible`). Bug ini tidak pernah ketahuan sampai benar-benar
di-build dengan akses internet. Diperbaiki dengan menaikkan `pydantic` ke
`2.13.4` di modul 3, 4, 7, dan 8.

**4. `/chat` (Modul 7) crash 500 kalau model minta tool call KEDUA
kalinya.** Setelah tool pertama dieksekusi dan hasilnya dikirim balik,
model kadang memutuskan untuk memanggil tool lagi (query pencarian yang
disempurnakan) alih-alih langsung memberi jawaban teks — dalam kasus itu
`final_response.text` bernilai `None`, dan `ChatResponse(answer=None)`
melempar `pydantic.ValidationError` mentah sebagai 500 tanpa pesan jelas.
Karena `/chat` memang sengaja dirancang cuma satu putaran (loop
multi-langkah ada di `/agent` Modul 8), diperbaiki dengan fallback pesan
yang jelas: `answer_text = final_response.text or "Model masih ingin
memanggil tool tambahan..."` — bukan meniadakan skenarionya, tapi
membuatnya gagal dengan anggun.

**5. Modul 7/8 masih tertinggal di retrieval ala Modul 4.** Kit sumber
(termasuk versi trainer aslinya) tidak pernah membawa maju peningkatan
retrieval dari Modul 5 (metadata filter + rerank) dan Modul 6 (hybrid
search) ke `/search` dan tool `cari_dokumen` di Modul 7/8 — keduanya
masih vector search polos. Diperbaiki dengan memisahkan pipeline
retrieval ke `app/retrieval.py` (dipakai bersama oleh `main.py` dan
`tools.py` supaya tidak circular import), lalu mengganti `/search` dan
`cari_dokumen` di Modul 7 & 8 untuk memakainya — sekarang tool yang
dipanggil agent punya kualitas retrieval yang sama dengan endpoint
HTTP-nya sendiri.

Kalau kode-kode ini ditulis ulang manual tanpa pengujian nyata,
kelimanya bug/celah yang mudah lolos.

## Alur Pemakaian yang Disarankan

1. `modul2-fastapi/` — jalankan & tunjukkan langsung dengan `uv run uvicorn`
2. `modul3-docker/` — pindah ke Docker, tunjukkan `docker compose up`
   menyalakan 3 service sekaligus
3. `modul4-ingestion/` — isi `.env` dengan API key Gemini asli sebelum
   sesi, jalankan `ingest.py` di depan peserta, demo `/search` lalu `/rag`
   (RAG penuh: retrieval + generation dalam satu endpoint)
4. `modul5-productionrag/` — demo `/search` dengan `category` dan
   bandingkan `candidates_retrieved` vs `candidates_after_rerank`
5. `modul6-hybridsearch/` — demo `/search` dengan query istilah spesifik
   (mis. nominal rupiah), tunjukkan `rrf_score` di response
6. `modul7-toolcalling/` — demo `/chat`, tunjukkan `tools_called` di
   response supaya peserta lihat keputusan model secara transparan
7. `modul8-agent/` — demo `/agent` dengan goal 2+ langkah, bandingkan
   dengan `/chat` untuk goal yang sama
8. `modul9-semanticcache/` — demo `/chat` dua kali dengan pertanyaan
   SEMAKNA (bukan exact sama), tunjukkan `cache_hit: true` & `latency_ms`
   yang turun drastis di panggilan kedua, cek `/cache-stats`
9. `modul10-guardrails/` (cabang dari Modul 9) — demo input guardrail
   menolak prompt injection dengan `400`, lalu tunjukkan field
   `guardrail` di response `/chat` sama-sama muncul di cache MISS
   maupun HIT
10. `modul11-observability/` (cabang lain dari Modul 9, paralel dengan
    Modul 10) — demo trace di dashboard Langfuse untuk
    `/chat`/`/search`/`/agent`, lalu jalankan `evaluate.py` dua kali
    berturut-turut untuk lihat skor + efek cache pada latensi rata-rata

## Prasyarat

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) — pengelola package Python untuk Modul 2 (lihat panduan per OS di `modul2-fastapi/`)
- Docker Desktop — untuk Modul 3-11
- API key Google Gemini — https://ai.google.dev/ (wajib mulai Modul 4)
- Akun Langfuse (opsional, gratis) — https://cloud.langfuse.com (untuk melihat trace sungguhan di Modul 11; tanpa ini modul tetap jalan normal tanpa tracing)

## Troubleshooting Cepat

Panduan lengkap per OS (termasuk instalasi `uv`/Docker) ada di masing-masing
folder modul (`windows.md`, `macos.md`, `linux.md`) dan di `PANDUAN_LENGKAP.md`.
Gejala paling umum:

| Gejala | Penyebab Umum | Solusi |
|---|---|---|
| `port already in use` / `address already in use` (8000, 5432, atau 6379) | Ada proses lain (server lama, aplikasi lain) masih memakai port itu | Cek proses yang pakai port, lalu matikan, **atau** ubah port kiri pada `docker-compose.yml`/`uvicorn --port` |
| Docker Desktop belum jalan / `docker: command not found` | Docker Desktop belum di-install atau belum dibuka | Install dari docker.com, buka aplikasinya, tunggu status "Running" sebelum `docker compose up` |
| `.env` tidak ditemukan / `GEMINI_API_KEY` kosong | Lupa copy `.env.example` → `.env`, atau belum diisi | `cp .env.example .env` (Windows: `copy .env.example .env`), lalu isi `GEMINI_API_KEY` |
| Perubahan kode tidak muncul | Modul 2: lupa flag `--reload`; Modul 3-11: volume `./app:/app` tidak ter-mount | Modul 2: pakai `uvicorn main:app --reload`; Modul 3-11: cek `docker compose logs app` |
| `429 RESOURCE_EXHAUSTED` dari Gemini | Kuota free-tier harian habis untuk model `gemini-3.6-flash` (±20 request/hari) | Tunggu, atau pakai API key lain — terutama sebelum demo Modul 7/8 yang butuh beberapa panggilan berurutan |

**Cek proses yang memakai sebuah port** (contoh port `8000`, ganti sesuai kebutuhan):

- **macOS / Linux:** `lsof -i :8000`, lalu hentikan dengan `kill -9 <PID>`
- **Windows (PowerShell):** `netstat -ano | findstr :8000`, lalu `taskkill /PID <pid> /F`

Kalau tidak ingin/tidak bisa mematikan proses tersebut, cukup ganti angka
port di sisi **kiri** pemetaan, misalnya `"8001:8000"` di `docker-compose.yml`
lalu akses lewat `localhost:8001`.

"""
Modul 11 - Observability & Evaluation (Langfuse)
AI Knowledge Assistant - Human Initiative

Instrumentasi tracing lewat Langfuse (SDK v4, berbasis OpenTelemetry) untuk
seluruh pipeline: retrieval (vector/keyword search, rerank), tool calling,
loop agent, DAN cache hit/miss dari Modul 9 - supaya efek semantic cache
bisa DIUKUR di dashboard Langfuse (trace, latency, token cost per request),
bukan cuma dirasakan dari field `latency_ms` di response.

Cara pakai di file lain:
    from observability import observe, get_client, log_gemini_usage, log_cache_event

    @observe(as_type="tool", name="cek_stok_barang")
    def cek_stok_barang(...):
        ...

Kenapa "opsional, bukan wajib"? Kalau LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY
belum diisi di .env, Langfuse SDK otomatis membuat client yang "disabled" -
setiap panggilan @observe / get_client().update_current_*() tetap berjalan
tanpa melempar exception (cuma ada log peringatan "No active span in
current context" di console, aman diabaikan). Jadi kit ini tetap bisa
dipakai tanpa akun Langfuse, persis seperti modul lain yang punya fallback
saat kredensial belum diisi.

PENTING (sudah diverifikasi lewat percobaan lokal): jangan bikin instance
`Langfuse(...)` secara manual di sini dan berharap @observe/get_client()
otomatis memakainya - keduanya TIDAK terhubung. SDK v4 mengambil konfigurasi
LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY/LANGFUSE_HOST langsung dari
environment variable secara internal saat get_client()/@observe pertama kali
dipanggil. Karena itu file ini SENGAJA tidak instansiasi Langfuse() manual.

Daftar gratis: https://cloud.langfuse.com (atau self-host, lihat
https://langfuse.com/self-hosting) - isi LANGFUSE_PUBLIC_KEY & LANGFUSE_SECRET_KEY
di .env untuk mengaktifkan tracing sungguhan.
"""
import os

from langfuse import observe, get_client  # noqa: F401  (observe/get_client di re-export dari sini)

LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

LANGFUSE_ENABLED = bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)


def log_gemini_usage(model: str, response, extra_metadata: dict | None = None) -> None:
    """
    Catat token usage dari sebuah response google-genai (usage_metadata) ke
    observation Langfuse yang sedang aktif. HARUS dipanggil di DALAM fungsi
    yang didekorasi @observe(as_type="generation") - kalau tidak ada span
    aktif, panggilan ini di-skip diam-diam (lihat docstring modul).
    """
    usage = getattr(response, "usage_metadata", None)
    usage_details = None
    if usage is not None:
        usage_details = {
            "input": usage.prompt_token_count or 0,
            "output": usage.candidates_token_count or 0,
            "total": usage.total_token_count or 0,
        }
    get_client().update_current_generation(
        model=model,
        output=getattr(response, "text", None),
        usage_details=usage_details,
        metadata=extra_metadata,
    )


def log_cache_event(layer: str, hit: bool, similarity: float | None = None) -> None:
    """
    Catat hit/miss cache Modul 9 sebagai metadata di span Langfuse yang
    sedang aktif - supaya trace di dashboard menunjukkan jelas: request ini
    kena cache atau tidak, dan seberapa mirip (khusus semantic cache).

    layer: "embedding" (Lapis 1, exact-match) atau "semantic" (Lapis 2).
    """
    get_client().update_current_span(
        metadata={"cache_layer": layer, "cache_hit": hit, "cache_similarity": similarity},
    )


def flush() -> None:
    """
    Pastikan semua trace yang masih di buffer terkirim sebelum proses
    berhenti. Server FastAPI yang long-running TIDAK perlu memanggil ini
    (SDK mengirim trace secara periodik di background thread) - tapi
    skrip pendek seperti evaluate.py WAJIB memanggilnya sebelum keluar,
    kalau tidak sebagian trace terakhir bisa hilang.
    """
    get_client().flush()

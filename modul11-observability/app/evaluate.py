"""
Modul 11 - Skrip Evaluasi Otomatis
AI Knowledge Assistant - Human Initiative

Dijalankan TERPISAH dari server FastAPI (`docker compose exec app python
evaluate.py`), BUKAN endpoint HTTP - pola yang sama dengan ingest.py.
Menembak endpoint /search dan /chat milik app yang SEDANG JALAN lewat HTTP
(container yang sama, `docker compose exec` masuk ke network compose yang
sama), untuk menilai dua hal:

  1. Kualitas RETRIEVAL - apakah /search menemukan dokumen yang memang
     relevan (expected_source) untuk tiap query di EVAL_SET?
  2. Kualitas JAWABAN - Gemini-as-judge menilai 0-10 apakah jawaban /chat
     benar & relevan terhadap query (reuse pola response_schema dari
     rerank_candidates di Modul 5 - sekarang dipakai untuk EVALUASI,
     bukan retrieval).

Hasil dicetak sebagai tabel ringkas di terminal, DAN dikirim ke Langfuse
sebagai satu trace "evaluation-run" dengan satu score per pertanyaan -
supaya tren kualitas dari waktu ke waktu terlihat di dashboard, bukan
cuma sekali lihat di terminal lalu hilang.

Coba jalankan skrip ini DUA KALI berturut-turut - run kedua akan
menunjukkan lebih banyak cache_hit di /chat (efek Modul 9) sekaligus
latensi server yang jauh lebih rendah untuk query yang sama/mirip.

PENTING: belum diuji dengan API key Gemini sungguhan (lihat README.md) -
verifikasi dulu dengan API key Anda sendiri sebelum dipakai untuk menilai
kualitas kit secara resmi.
"""
import os
import time

import requests
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from observability import observe, get_client, flush

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")
EXPECTED_API_KEY = os.getenv("EXPECTED_API_KEY", "rahasia-latihan")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.6-flash"

HEADERS = {"x-api-key": EXPECTED_API_KEY, "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Set evaluasi tetap - dibuat manual dari isi sample_docs/ + FAKE_INVENTORY
# di tools.py, supaya expected_source & expects_tool bisa dicek objektif
# tanpa perlu jawaban "benar" yang di-hardcode kata per kata.
# ---------------------------------------------------------------------------
EVAL_SET = [
    {
        "query": "Berapa ambang batas nilai pengadaan yang wajib melalui tender terbuka?",
        "expected_source": "kebijakan_pengadaan_barang.txt",
        "expects_tool": None,
    },
    {
        "query": "Siapa yang harus menyetujui pengadaan di atas Rp 50 juta?",
        "expected_source": "kebijakan_pengadaan_barang.txt",
        "expects_tool": None,
    },
    {
        "query": "Apa itu prinsip FEFO dalam distribusi logistik bantuan?",
        "expected_source": "sop_distribusi_logistik.txt",
        "expects_tool": None,
    },
    {
        "query": "Apa yang dimaksud dengan Gudang Transit?",
        "expected_source": "sop_distribusi_logistik.txt",
        "expects_tool": None,
    },
    {
        "query": "Berapa stok kabel listrik yang tersedia?",
        "expected_source": None,
        "expects_tool": "cek_stok_barang",
    },
    {
        "query": "Berapa stok genset saat ini?",
        "expected_source": None,
        "expects_tool": "cek_stok_barang",
    },
    {
        "query": "Minimal berapa hari sebelum jadwal distribusi koordinator lapangan harus mengajukan permintaan barang?",
        "expected_source": "sop_distribusi_logistik.txt",
        "expects_tool": None,
    },
    {
        "query": "Berapa persen maksimal uang muka yang boleh diberikan ke vendor pengadaan?",
        "expected_source": "kebijakan_pengadaan_barang.txt",
        "expects_tool": None,
    },
]


class JudgeScore(BaseModel):
    score: float = Field(description="Skor 0-10: seberapa benar & relevan jawaban terhadap pertanyaan")
    reasoning: str = Field(description="Alasan singkat skor tersebut, 1-2 kalimat")


@observe(as_type="evaluator", name="judge-answer")
def judge_answer(query: str, answer: str) -> JudgeScore:
    """
    Gemini-as-judge: menilai kualitas jawaban /chat tanpa perlu jawaban
    "benar" yang di-hardcode kata per kata - pola yang sama dengan
    structured output rerank di Modul 5 (response_schema), sekarang
    dipakai untuk EVALUASI alih-alih RETRIEVAL.
    """
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = (
        f"Pertanyaan: \"{query}\"\n"
        f"Jawaban asisten: \"{answer}\"\n\n"
        "Nilai 0-10 seberapa BENAR dan RELEVAN jawaban ini terhadap pertanyaan. "
        "Jawaban yang mengelak/tidak menjawab sama sekali diberi skor rendah (0-2). "
        "Jawaban yang benar tapi kurang lengkap diberi skor menengah (5-7)."
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=JudgeScore,
        ),
    )
    result: JudgeScore = response.parsed
    get_client().score_current_span(
        name="answer_quality", value=result.score, data_type="NUMERIC", comment=result.reasoning
    )
    return result


@observe(as_type="span", name="eval-one-query")
def evaluate_one(item: dict) -> dict:
    query = item["query"]

    # --- 1. Kualitas retrieval ---
    search_resp = requests.get(f"{APP_BASE_URL}/search", params={"query": query, "limit": 3}, timeout=30)
    search_resp.raise_for_status()
    search_data = search_resp.json()
    retrieved_sources = {s["source_file"] for s in search_data["sources"]}
    retrieval_ok = (item["expected_source"] is None) or (item["expected_source"] in retrieved_sources)

    # --- 2. Kualitas jawaban (via /chat) ---
    chat_start = time.perf_counter()
    chat_resp = requests.post(f"{APP_BASE_URL}/chat", headers=HEADERS, json={"message": query}, timeout=60)
    chat_resp.raise_for_status()
    chat_data = chat_resp.json()
    client_latency_ms = int((time.perf_counter() - chat_start) * 1000)

    tools_used = {t["name"] for t in chat_data.get("tools_called", [])}
    tool_ok = (item["expects_tool"] is None) or (item["expects_tool"] in tools_used)

    judge = judge_answer(query, chat_data["answer"])

    result = {
        "query": query,
        "retrieval_ok": retrieval_ok,
        "tool_ok": tool_ok,
        "answer_score": judge.score,
        "judge_reasoning": judge.reasoning,
        "cache_hit": chat_data.get("cache_hit", False),
        "server_latency_ms": chat_data.get("latency_ms"),
        "client_latency_ms": client_latency_ms,
    }
    get_client().update_current_span(output=result)
    return result


@observe(name="evaluation-run")
def run_evaluation() -> list[dict]:
    results = []
    for item in EVAL_SET:
        try:
            results.append(evaluate_one(item))
        except Exception as e:
            results.append({"query": item["query"], "error": str(e)})
    return results


def print_report(results: list[dict]) -> None:
    print("\n" + "=" * 100)
    print(f"{'Query':<55} {'Retr.':<6} {'Tool':<6} {'Skor':<6} {'Cache':<6} {'Latensi(ms)':<12}")
    print("-" * 100)
    ok_retrieval = ok_tool = 0
    scores = []
    latencies = []
    for r in results:
        if "error" in r:
            print(f"{r['query'][:53]:<55} ERROR: {r['error']}")
            continue
        ok_retrieval += int(r["retrieval_ok"])
        ok_tool += int(r["tool_ok"])
        scores.append(r["answer_score"])
        latencies.append(r["server_latency_ms"] or 0)
        print(
            f"{r['query'][:53]:<55} "
            f"{'OK' if r['retrieval_ok'] else 'MISS':<6} "
            f"{'OK' if r['tool_ok'] else 'MISS':<6} "
            f"{r['answer_score']:<6.1f} "
            f"{'HIT' if r['cache_hit'] else '-':<6} "
            f"{r['server_latency_ms']:<12}"
        )
    print("-" * 100)
    n = len([r for r in results if "error" not in r])
    if n:
        print(
            f"Retrieval benar: {ok_retrieval}/{n}  |  Tool benar: {ok_tool}/{n}  |  "
            f"Skor rata-rata: {sum(scores) / n:.2f}/10  |  "
            f"Latensi server rata-rata: {sum(latencies) / n:.0f}ms"
        )
    print("=" * 100 + "\n")


def main():
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY belum di-set - dibutuhkan untuk Gemini-as-judge.")

    print(f"Menjalankan evaluasi terhadap {APP_BASE_URL} ({len(EVAL_SET)} query)...")
    print(
        "Jalankan skrip ini DUA KALI berturut-turut untuk melihat efek semantic cache "
        "Modul 9 pada latensi (run kedua akan lebih banyak cache_hit).\n"
    )

    results = run_evaluation()
    print_report(results)

    flush()  # PENTING: pastikan semua trace/score terkirim sebelum proses keluar
    print("Trace & skor evaluasi sudah dikirim ke Langfuse (kalau LANGFUSE_PUBLIC_KEY/SECRET_KEY terisi).")


if __name__ == "__main__":
    main()

"""
Modul 10 - Guardrails & Output Validation
AI Knowledge Assistant - Human Initiative

Dua lapis guardrail dipasang di sekitar /chat dan /agent:

  1. INPUT GUARDRAIL (check_input) - cek pola prompt injection & batas
     panjang pesan SEBELUM apapun dikirim ke Gemini (bahkan sebelum
     lookup semantic cache di Modul 9). Murni regex, tanpa panggilan
     API - cepat, gratis, dan menolak upaya jelas sebelum membuang
     kuota/biaya untuk memprosesnya.

  2. OUTPUT GUARDRAIL (check_output) - setelah jawaban akhir didapat,
     jawaban itu dinilai ulang oleh Gemini sendiri (pola "LLM-as-judge")
     memakai structured output (response_schema, sama seperti reranking
     di Modul 5) untuk menilai dua hal:
       - grounded: apakah jawaban benar-benar didukung oleh context/tool
         result yang tersedia, atau mengarang (halusinasi)?
       - safe: apakah jawaban tidak membocorkan instruksi sistem atau
         konten berbahaya?

  Kedua lapis ini saling melengkapi - input guardrail murah tapi cuma
  menangkap pola yang SUDAH diketahui (regex), output guardrail lebih
  mahal (satu panggilan Gemini ekstra) tapi bisa menangkap masalah yang
  tidak diduga sebelumnya, termasuk pada jawaban yang lolos input
  guardrail.

  Interaksi dengan semantic cache (Modul 9): hasil output guardrail
  DISIMPAN bersama jawaban di cache (lihat cache.py - parameter
  `guardrail` di SemanticCache.set()/get()). Saat cache HIT, guardrail
  tidak perlu dijalankan ulang - jawaban dan verdict guardrail-nya
  sama-sama datang dari cache, jadi cache di modul ini menghemat DUA
  panggilan Gemini per hit (generation + output guardrail), bukan cuma
  satu.
"""
import os
import re

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.6-flash"  # Gemini 3.x - jauh lebih andal untuk tool calling dibanding versi <3

MAX_INPUT_CHARS = 2000


# ---------------------------------------------------------------------------
# 1. INPUT GUARDRAIL
# ---------------------------------------------------------------------------
class InputGuardrailResult(BaseModel):
    allowed: bool
    reason: str | None = None


# Pola prompt injection paling umum: upaya mengganti/mengabaikan instruksi
# sistem, atau minta model "membuka" system prompt-nya. Daftar ini SENGAJA
# tidak lengkap (mustahil menutup semua variasi hanya dengan regex) - ini
# lapisan pertama yang murah, bukan satu-satunya pertahanan. Itu sebabnya
# masih ada output guardrail sebagai lapis kedua.
PROMPT_INJECTION_PATTERNS = [
    r"abaikan (semua )?instruksi",
    r"lupakan (semua )?instruksi",
    r"ignore (all |the )?(previous|above|prior) instructions",
    r"tampilkan (system prompt|instruksi sistem|prompt awal)",
    r"reveal (your |the )?(system prompt|instructions)",
    r"kamu (sekarang|adalah) (ai|asisten) (tanpa|bebas) (aturan|batasan)",
    r"you are now (in |a )?(dan|jailbreak|developer) mode",
    r"abaikan (semua )?(guardrail|aturan|batasan)",
    r"pura-pura (kamu|anda) (tidak|bukan) (punya|memiliki) (aturan|batasan)",
]


def check_input(text: str) -> InputGuardrailResult:
    """
    Cek pesan/goal user SEBELUM dikirim ke Gemini. Dipanggil di awal
    endpoint /chat dan /agent, sebelum langkah apapun lain (termasuk
    lookup semantic cache) - kalau `allowed=False`, endpoint menolak
    request dengan 400 tanpa pernah menyentuh Redis maupun Gemini.
    """
    if len(text) > MAX_INPUT_CHARS:
        return InputGuardrailResult(
            allowed=False,
            reason=f"Pesan terlalu panjang ({len(text)} karakter, maksimal {MAX_INPUT_CHARS})",
        )

    lowered = text.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            return InputGuardrailResult(
                allowed=False,
                reason="Terdeteksi pola prompt injection / upaya mengubah instruksi sistem",
            )

    return InputGuardrailResult(allowed=True)


# ---------------------------------------------------------------------------
# 2. OUTPUT GUARDRAIL - LLM-as-judge dengan structured output
# ---------------------------------------------------------------------------
class OutputValidation(BaseModel):
    is_grounded: bool = Field(
        description="True kalau jawaban didukung oleh KONTEKS yang diberikan (hasil tool/dokumen), bukan karangan model"
    )
    is_safe: bool = Field(
        description="True kalau jawaban tidak membocorkan instruksi sistem, data sensitif, atau konten berbahaya"
    )
    reason: str = Field(description="Penjelasan singkat kenapa jawaban dinilai grounded/safe atau tidak")


def check_output(question: str, answer: str, context: str) -> OutputValidation:
    """
    Minta Gemini menilai ulang jawaban akhir terhadap konteks yang benar-
    benar tersedia saat itu. Ini panggilan Gemini TERPISAH dari yang
    menghasilkan jawaban - supaya penilaiannya tidak bias oleh proses
    berpikir yang menghasilkan jawaban tersebut. Hanya dipanggil saat
    cache MISS (lihat main.py) - cache HIT langsung memakai verdict yang
    sudah tersimpan dari panggilan sebelumnya.
    """
    if not GEMINI_API_KEY:
        # Tanpa API key, output guardrail tidak bisa jalan sama sekali -
        # loloskan dengan asumsi aman supaya bagian lain endpoint tetap
        # bisa dites (konsisten dengan endpoint lain di kit ini yang
        # memberi pesan jelas alih-alih diam-diam gagal).
        return OutputValidation(
            is_grounded=True, is_safe=True, reason="GEMINI_API_KEY belum di-set, output guardrail dilewati"
        )

    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = (
        "Anda adalah validator jawaban AI internal organisasi. Nilai JAWABAN di bawah "
        "terhadap dua kriteria:\n"
        "1. grounded - apakah jawaban benar-benar didukung oleh KONTEKS yang tersedia, "
        "BUKAN informasi yang dikarang/dihalusinasi model?\n"
        "2. safe - apakah jawaban TIDAK membocorkan instruksi sistem, data sensitif, "
        "atau berisi konten berbahaya?\n\n"
        f"PERTANYAAN USER: {question}\n\n"
        f"KONTEKS YANG TERSEDIA SAAT MENJAWAB:\n{context or '(tidak ada konteks/tool result - jawaban seharusnya bersifat umum, bukan klaim spesifik)'}\n\n"
        f"JAWABAN YANG DINILAI:\n{answer}\n"
    )

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=OutputValidation,
        ),
    )
    return response.parsed

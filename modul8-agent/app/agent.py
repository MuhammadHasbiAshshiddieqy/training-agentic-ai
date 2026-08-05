"""
Modul 8 - Agent Foundation: Loop Think-Act-Observe
AI Knowledge Assistant - Human Initiative

Modul 7 membangun tool calling untuk SATU keputusan (model boleh pilih 0
atau lebih tool, lalu langsung jawab). Modul 8 membangun AGENT — model
yang boleh THINK -> ACT -> OBSERVE berkali-kali secara berurutan sebelum
memberi jawaban akhir, memakai hasil observasi sebelumnya untuk memutuskan
langkah berikutnya.

Contoh kasus yang butuh loop, bukan satu kali panggilan:
  "Cek stok terpal, dan kalau kurang dari 50, cari SOP permintaan barang
  tambahan." — agent harus cek stok DULU, baru MEMUTUSKAN apakah perlu
  mencari SOP berdasarkan hasilnya.

Menggunakan tool yang sama dari Modul 7 (tools.py) — agent hanya
menambahkan LOOP dan DECISION LAYER di atasnya.
"""
import os

from google import genai
from google.genai import types

from tools import ALL_TOOLS, TOOL_REGISTRY

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.6-flash"  # Gemini 3.x - jauh lebih andal untuk tool calling dibanding versi <3

SYSTEM_INSTRUCTION = (
    "Anda adalah asisten AI Human Initiative. Jawab pertanyaan user dengan "
    "memanggil tool yang tersedia bila perlu. Jika sudah punya cukup info "
    "untuk menjawab, berikan jawaban akhir dalam bahasa natural TANPA "
    "memanggil tool lagi."
)


class AgentStep:
    """Satu langkah dalam trace agent — untuk transparansi & debugging."""
    def __init__(self, step_number: int, kind: str, detail: dict):
        self.step_number = step_number
        self.kind = kind  # "think" | "act" | "observe" | "final_answer"
        self.detail = detail

    def to_dict(self) -> dict:
        return {"step": self.step_number, "kind": self.kind, **self.detail}


class Agent:
    """
    Agent minimalis dengan loop Think-Act-Observe.

    Fondasi ini SENGAJA ditulis manual (bukan memakai framework agent besar)
    supaya setiap bagian loop terlihat jelas: kapan model "berpikir", kapan
    tool dieksekusi, dan bagaimana keputusan berhenti diambil.
    """

    def __init__(self, max_steps: int = 5):
        self.max_steps = max_steps
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.config = types.GenerateContentConfig(
            tools=[ALL_TOOLS],
            system_instruction=SYSTEM_INSTRUCTION,
            # Google merekomendasikan thinking_level medium/high untuk agent
            # otonom dengan tool calling & multi-step reasoning — level rendah
            # cenderung membuat model berhenti memanggil tool terlalu dini.
            thinking_config=types.ThinkingConfig(thinking_level="high"),
        )

    def run(self, goal: str) -> dict:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY belum di-set")

        contents = [types.Content(role="user", parts=[types.Part(text=goal)])]
        trace: list[AgentStep] = []

        for step_number in range(1, self.max_steps + 1):
            # ---- THINK ----
            # Model melihat seluruh history (goal + hasil observe sebelumnya)
            # dan memutuskan: panggil tool lagi, atau sudah cukup untuk jawab?
            response = self.client.models.generate_content(
                model=GEMINI_MODEL, contents=contents, config=self.config,
            )
            trace.append(AgentStep(step_number, "think", {
                "wants_tool_call": bool(response.function_calls),
            }))

            # ---- DECISION LAYER ----
            # Kalau model TIDAK minta tool lagi, response.text adalah
            # jawaban akhir — hentikan loop di sini.
            if not response.function_calls:
                trace.append(AgentStep(step_number, "final_answer", {"answer": response.text}))
                return {
                    "answer": response.text,
                    "steps": [s.to_dict() for s in trace],
                    "total_steps": step_number,
                    "stopped_reason": "model_gave_final_answer",
                }

            # ---- ACT ----
            contents.append(response.candidates[0].content)
            function_response_parts = []
            for fc in response.function_calls:
                fn = TOOL_REGISTRY.get(fc.name)
                args = dict(fc.args) if fc.args else {}
                if fn is None:
                    result = {"error": f"Tool '{fc.name}' tidak dikenali"}
                else:
                    try:
                        result = fn(**args)
                    except Exception as e:
                        result = {"error": f"Tool '{fc.name}' gagal dieksekusi: {e}"}

                trace.append(AgentStep(step_number, "act", {
                    "tool": fc.name, "args": args, "result": result,
                }))
                # Gemini 3.x memvalidasi id, name, dan jumlah response harus
                # cocok dengan function_calls sebelumnya.
                function_response_parts.append(
                    types.Part(function_response=types.FunctionResponse(
                        id=getattr(fc, "id", None),
                        name=fc.name,
                        response={"result": result},
                    ))
                )

            # ---- OBSERVE ----
            # Hasil tool ditambahkan ke history — akan dilihat model di
            # iterasi THINK berikutnya untuk memutuskan langkah selanjutnya.
            contents.append(types.Content(role="user", parts=function_response_parts))
            trace.append(AgentStep(step_number, "observe", {
                "added_to_history": len(function_response_parts),
            }))

        # Safety guard: kalau sampai di sini, agent belum juga memberi
        # jawaban akhir setelah max_steps — hentikan paksa supaya tidak
        # berputar tanpa henti (dan tidak menghabiskan kuota API).
        return {
            "answer": (
                "Maaf, saya belum bisa menyelesaikan permintaan ini dalam "
                f"{self.max_steps} langkah. Coba pecah pertanyaan jadi lebih spesifik."
            ),
            "steps": [s.to_dict() for s in trace],
            "total_steps": self.max_steps,
            "stopped_reason": "max_steps_reached",
        }

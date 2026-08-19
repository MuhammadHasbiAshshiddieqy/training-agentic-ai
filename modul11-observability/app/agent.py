"""
Modul 8/9/11 - Agent Foundation: Loop Think-Act-Observe
AI Knowledge Assistant - Human Initiative

Modul 11: seluruh run() jadi satu trace Langfuse (as_type="agent"), dengan
setiap iterasi THINK sebagai generation anak (token usage tercatat lewat
log_gemini_usage) dan setiap ACT otomatis punya anak-span dari tool yang
dipanggil (lihat @observe di tools.py). Hasilnya: satu trace di dashboard
Langfuse menunjukkan SELURUH perjalanan satu goal - think -> act -> observe
berkali-kali - lengkap dengan latensi & token tiap langkahnya.

Tidak ada perubahan LOGIKA loop dari Modul 8. Catatan yang masih relevan:
semantic cache Modul 9 SENGAJA tidak dipasang di sini (lihat komentar di
Modul 9) - riwayat percakapan agent nyaris selalu unik antar goal, beda
dengan /chat yang sering menerima pertanyaan berulang/mirip.
"""
import os

from google import genai
from google.genai import types

from tools import ALL_TOOLS, TOOL_REGISTRY
from observability import observe, get_client, log_gemini_usage

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.6-flash"  # Gemini 3.x - jauh lebih andal untuk tool calling dibanding versi <3

SYSTEM_INSTRUCTION = (
    "Anda adalah asisten AI Human Initiative. Jawab pertanyaan user dengan "
    "memanggil tool yang tersedia bila perlu. Jika sudah punya cukup info "
    "untuk menjawab, berikan jawaban akhir dalam bahasa natural TANPA "
    "memanggil tool lagi."
)


class AgentStep:
    """Satu langkah dalam trace agent (versi aplikasi kita sendiri, terpisah dari trace Langfuse) - untuk transparansi & debugging di response API."""
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
            # otonom dengan tool calling & multi-step reasoning - level rendah
            # cenderung membuat model berhenti memanggil tool terlalu dini.
            thinking_config=types.ThinkingConfig(thinking_level="high"),
        )

    @observe(as_type="generation", name="agent-think")
    def _think(self, contents, step_number: int):
        """Satu panggilan Gemini generate_content - dipisah jadi method sendiri supaya jadi satu observation "generation" per iterasi THINK di Langfuse."""
        response = self.client.models.generate_content(
            model=GEMINI_MODEL, contents=contents, config=self.config,
        )
        log_gemini_usage(GEMINI_MODEL, response, extra_metadata={"step": step_number})
        return response

    @observe(as_type="agent", name="agent-run")
    def run(self, goal: str) -> dict:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY belum di-set")

        get_client().update_current_span(metadata={"max_steps": self.max_steps})

        contents = [types.Content(role="user", parts=[types.Part(text=goal)])]
        trace: list[AgentStep] = []

        for step_number in range(1, self.max_steps + 1):
            # ---- THINK ----
            response = self._think(contents, step_number)
            trace.append(AgentStep(step_number, "think", {
                "wants_tool_call": bool(response.function_calls),
            }))

            # ---- DECISION LAYER ----
            if not response.function_calls:
                trace.append(AgentStep(step_number, "final_answer", {"answer": response.text}))
                get_client().update_current_span(
                    output={"stopped_reason": "model_gave_final_answer", "total_steps": step_number}
                )
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
                function_response_parts.append(
                    types.Part(function_response=types.FunctionResponse(
                        id=getattr(fc, "id", None),
                        name=fc.name,
                        response={"result": result},
                    ))
                )

            # ---- OBSERVE ----
            contents.append(types.Content(role="user", parts=function_response_parts))
            trace.append(AgentStep(step_number, "observe", {
                "added_to_history": len(function_response_parts),
            }))

        # Safety guard: kalau sampai di sini, agent belum juga memberi
        # jawaban akhir setelah max_steps - hentikan paksa.
        get_client().update_current_span(
            output={"stopped_reason": "max_steps_reached", "total_steps": self.max_steps}
        )
        return {
            "answer": (
                "Maaf, saya belum bisa menyelesaikan permintaan ini dalam "
                f"{self.max_steps} langkah. Coba pecah pertanyaan jadi lebih spesifik."
            ),
            "steps": [s.to_dict() for s in trace],
            "total_steps": self.max_steps,
            "stopped_reason": "max_steps_reached",
        }

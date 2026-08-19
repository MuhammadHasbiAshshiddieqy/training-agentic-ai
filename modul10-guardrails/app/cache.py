"""
Modul 9/10 - Semantic Cache (Redis), dibawa maju dari Modul 9 apa adanya
AI Knowledge Assistant - Human Initiative

Satu-satunya perubahan untuk Modul 10: SemanticCache.set()/get() sekarang
juga menyimpan verdict output guardrail (lihat guardrails.py) bersama
jawabannya - cache HIT tidak perlu memanggil LLM-as-judge lagi untuk
menilai ulang jawaban yang SAMA yang sudah pernah dinilai sebelumnya.

Dua lapis cache di atas Redis, keduanya demi mengurangi panggilan Gemini
API yang mahal & lambat (baik untuk embedding maupun generation):

  1. Embedding cache (exact-match) - teks yang PERSIS sama tidak perlu
     di-embed ulang. Dipakai di /search dan tool cari_dokumen, yang
     sering menerima query yang mirip/berulang dari peserta latihan.

  2. Semantic response cache (similarity-match) - pertanyaan yang
     MAKNANYA mirip (bukan cuma persis sama) dengan pertanyaan yang
     sudah pernah dijawab akan dapat jawaban dari cache, tanpa
     memanggil Gemini generate_content lagi. Dipakai di /chat.

Kenapa bukan RediSearch / vector index Redis? Supaya kit ini tetap jalan
di atas image `redis:7-alpine` biasa yang sudah dipakai sejak Modul 3
(tidak perlu ganti ke redis-stack). Untuk skala latihan (puluhan-ratusan
entry cache), similarity dihitung manual di sisi Python - cukup cepat dan
jauh lebih mudah dipahami peserta pemula dibanding index vektor khusus.
Untuk skala production sungguhan dengan jutaan entry cache, pertimbangkan
RediSearch (vector index bawaan Redis) alih-alih scan manual seperti ini.
"""
import hashlib
import json
import math
import os
import time
import uuid

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

EMBED_CACHE_TTL_SECONDS = int(os.getenv("EMBED_CACHE_TTL_SECONDS", "86400"))       # 24 jam
SEMANTIC_CACHE_TTL_SECONDS = int(os.getenv("SEMANTIC_CACHE_TTL_SECONDS", "3600"))  # 1 jam
SEMANTIC_CACHE_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.95"))    # 0-1, makin tinggi makin ketat
SEMANTIC_CACHE_MAX_SCAN = int(os.getenv("SEMANTIC_CACHE_MAX_SCAN", "500"))         # batas entry dibandingkan per lookup

EMBED_PREFIX = "embcache:"
SEMANTIC_ENTRY_PREFIX = "semcache:entry:"
SEMANTIC_INDEX_KEY = "semcache:index"
STATS_KEY = "cache:stats"  # hash: embed_hits, embed_misses, semantic_hits, semantic_misses

_redis_client: "redis.Redis | None" = None


def get_redis() -> redis.Redis:
    """Singleton koneksi Redis - dipakai ulang, bukan connect baru tiap request."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity murni Python (tanpa numpy) - cukup untuk skala latihan."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# LAPIS 1 - Embedding cache (exact-match, key = hash teks)
# ---------------------------------------------------------------------------
def embed_text_cached(text: str) -> list[float]:
    """
    Bungkus ingest.embed_text() dengan cache exact-match di Redis. Teks yang
    sama persis (mis. query "apa itu RAG?" diketik ulang oleh peserta
    berbeda, atau query yang sama dipanggil lagi lewat /search) tidak perlu
    memanggil Gemini embed_content lagi.
    """
    from ingest import embed_text  # import lokal - hindari circular import saat startup

    r = get_redis()
    key = EMBED_PREFIX + hashlib.sha256(text.strip().lower().encode()).hexdigest()

    cached = r.get(key)
    if cached is not None:
        r.hincrby(STATS_KEY, "embed_hits", 1)
        return json.loads(cached)

    r.hincrby(STATS_KEY, "embed_misses", 1)
    embedding = embed_text(text)
    r.set(key, json.dumps(embedding), ex=EMBED_CACHE_TTL_SECONDS)
    return embedding


# ---------------------------------------------------------------------------
# LAPIS 2 - Semantic response cache (similarity-match)
# ---------------------------------------------------------------------------
class SemanticCache:
    """
    Cache jawaban akhir /chat berdasarkan KEMIRIPAN MAKNA pertanyaan, bukan
    exact match. "Berapa stok kabel listrik?" dan "Stok kabel listrik ada
    berapa?" seharusnya kena cache yang sama walau teksnya beda.
    """

    def __init__(self, threshold: float = SEMANTIC_CACHE_THRESHOLD, ttl: int = SEMANTIC_CACHE_TTL_SECONDS):
        self.threshold = threshold
        self.ttl = ttl
        self.r = get_redis()

    def get(self, query_embedding: list[float]) -> dict | None:
        """
        Cari entry cache dengan similarity >= threshold terhadap query_embedding.
        Mengembalikan entry (dict) kalau HIT, None kalau MISS. Sekalian
        membersihkan id yang sudah kedaluwarsa dari index (lazy cleanup) -
        entry-nya sendiri sudah hilang duluan lewat TTL Redis, di sini kita
        cuma menyapu id yatim yang masih nyangkut di index SET.
        """
        entry_ids = list(self.r.smembers(SEMANTIC_INDEX_KEY))[:SEMANTIC_CACHE_MAX_SCAN]

        best_entry = None
        best_score = 0.0
        for entry_id in entry_ids:
            raw = self.r.get(SEMANTIC_ENTRY_PREFIX + entry_id)
            if raw is None:
                self.r.srem(SEMANTIC_INDEX_KEY, entry_id)
                continue
            entry = json.loads(raw)
            score = _cosine_similarity(query_embedding, entry["embedding"])
            if score > best_score:
                best_score = score
                best_entry = entry

        if best_entry is not None and best_score >= self.threshold:
            self.r.hincrby(STATS_KEY, "semantic_hits", 1)
            return {**best_entry, "similarity": round(best_score, 4)}

        self.r.hincrby(STATS_KEY, "semantic_misses", 1)
        return None

    def set(
        self,
        query: str,
        query_embedding: list[float],
        answer: str,
        tools_called: list,
        guardrail: dict | None = None,
    ) -> None:
        """
        Simpan jawaban baru ke cache, sekalian daftarkan id-nya ke index.

        `guardrail` (Modul 10) - verdict output guardrail (is_grounded,
        is_safe, reason) ikut disimpan bersama jawabannya, supaya cache
        HIT tidak perlu memanggil Gemini lagi untuk menilai ulang jawaban
        yang SAMA yang sudah pernah dinilai aman sebelumnya.
        """
        entry_id = uuid.uuid4().hex
        entry = {
            "query": query,
            "embedding": query_embedding,
            "answer": answer,
            "tools_called": tools_called,
            "guardrail": guardrail,
            "created_at": time.time(),
        }
        self.r.set(SEMANTIC_ENTRY_PREFIX + entry_id, json.dumps(entry), ex=self.ttl)
        self.r.sadd(SEMANTIC_INDEX_KEY, entry_id)
        # Index sendiri jangan sampai hidup abadi kalau semua entry-nya sudah expired.
        self.r.expire(SEMANTIC_INDEX_KEY, self.ttl)


def get_cache_stats() -> dict:
    """Ringkasan hit/miss kedua lapis cache, dipakai endpoint /cache-stats."""
    r = get_redis()
    raw = r.hgetall(STATS_KEY)
    embed_hits = int(raw.get("embed_hits", 0))
    embed_misses = int(raw.get("embed_misses", 0))
    semantic_hits = int(raw.get("semantic_hits", 0))
    semantic_misses = int(raw.get("semantic_misses", 0))

    def hit_rate(hits: int, misses: int) -> float:
        total = hits + misses
        return round(hits / total, 4) if total else 0.0

    return {
        "embedding_cache": {
            "hits": embed_hits,
            "misses": embed_misses,
            "hit_rate": hit_rate(embed_hits, embed_misses),
        },
        "semantic_cache": {
            "hits": semantic_hits,
            "misses": semantic_misses,
            "hit_rate": hit_rate(semantic_hits, semantic_misses),
            "active_entries": r.scard(SEMANTIC_INDEX_KEY),
            "threshold": SEMANTIC_CACHE_THRESHOLD,
        },
    }


def clear_cache() -> dict:
    """Hapus semua entry cache (embedding + semantic) & reset statistik. Untuk demo/testing."""
    r = get_redis()
    deleted = 0
    for prefix in (EMBED_PREFIX, SEMANTIC_ENTRY_PREFIX):
        cursor = 0
        while True:
            cursor, keys = r.scan(cursor=cursor, match=f"{prefix}*", count=200)
            if keys:
                deleted += r.delete(*keys)
            if cursor == 0:
                break
    r.delete(SEMANTIC_INDEX_KEY)
    r.delete(STATS_KEY)
    return {"deleted_keys": deleted}

import hashlib, random
import ingest

def fake_embed(text, retries=3):
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
    rnd = random.Random(seed)
    return [rnd.uniform(-1, 1) for _ in range(768)]

ingest.embed_text = fake_embed

import uvicorn
import main
uvicorn.run(main.app, host="127.0.0.1", port=8133)

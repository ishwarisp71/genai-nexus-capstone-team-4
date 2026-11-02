import json
from helpdesk.ingest import build_chunks
from helpdesk.search import build_embeddings

chunks = build_chunks()
with open("index/chunks.json", "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=1)
print(f"Saved {len(chunks)} chunks to index/chunks.json")

build_embeddings()
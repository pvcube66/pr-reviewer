"""Local vector memory: ChromaDB + naive chunking. No API key needed."""
from __future__ import annotations
import chromadb

_client: chromadb.PersistentClient | None = None

def get_client(path: str = "./.chroma"):
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=path)
    return _client

def chunk(text: str, size: int = 2000, overlap: int = 200) -> list[str]:
    out, i = [], 0
    while i < len(text):
        out.append(text[i : i + size])
        i += size - overlap
    return [c for c in out if c.strip()]

def _col_name(repo: str) -> str:
    safe = "".join(c if c.isalnum() or c in "._-" else "-" for c in repo).strip("-_.")
    return f"repo-{safe or 'default'}"[:512]

def index_diff(repo: str, diff: str) -> int:
    col = get_client().get_or_create_collection(_col_name(repo))
    chunks = chunk(diff)
    if not chunks:
        return 0
    base = col.count()
    col.add(ids=[f"{base+i}" for i in range(len(chunks))], documents=chunks)
    return len(chunks)

def retrieve(diff: str, repo: str = "default", k: int = 5) -> str:
    try:
        col = get_client().get_collection(_col_name(repo))
    except Exception:
        return ""
    if col.count() == 0:
        return ""
    res = col.query(query_texts=[diff[:2000]], n_results=min(k, col.count()))
    docs = (res.get("documents") or [[]])[0]
    return "\n---\n".join(docs)

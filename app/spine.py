"""Local JSONL event spine. Tiger-compatible schema.
Each line: {ts, type, repo, pr, ...}. Swap writer for Tiger insert later.
"""
from __future__ import annotations
import json
import os
import time

SPINE_PATH = os.getenv("EVENT_SPINE_PATH", "./agent_events.jsonl")

def emit(type: str, **fields) -> dict:
    from .security import mask
    safe = {k: (mask(v) if isinstance(v, str) else v) for k, v in fields.items()}
    evt = {"ts": time.time(), "type": type, **safe}
    try:
        with open(SPINE_PATH, "a") as f:
            f.write(json.dumps(evt) + "\n")
    except OSError:
        pass
    return evt

def demo():
    e = emit("demo.ping", repo="x", pr=1)
    assert e["type"] == "demo.ping"
    print("spine OK")

if __name__ == "__main__":
    demo()

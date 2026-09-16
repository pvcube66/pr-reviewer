"""Versioned prompt registry. PROMPT_VERSION selects prompts/<ver>/ (default v1)."""
from __future__ import annotations
import os
from pathlib import Path

def _dir() -> Path:
    ver = os.getenv("PROMPT_VERSION", "v1")
    return Path(__file__).resolve().parent.parent / "prompts" / ver

def load(role: str) -> str:
    return (_dir() / f"{role}.md").read_text().strip()

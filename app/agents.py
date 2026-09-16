"""4 specialists + aggregator on Groq. Sequential + backoff = free-tier safe."""
from __future__ import annotations
import asyncio
import json
import os

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from .prompts import load as load_prompt

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
_llm = None
_fails = 0
_open_until = 0.0

def get_llm():
    global _llm
    if _llm is None:
        _llm = ChatGroq(model=MODEL, temperature=0)
    return _llm

class Finding(BaseModel):
    severity: str = Field(pattern="^(info|minor|major|critical)$")
    file: str = ""
    line: int = 0
    issue: str = ""
    rationale: str = ""
    confidence: float = 0.5

SYS = (
    "Return ONLY a JSON array, no prose. Each item: "
    '{"severity":"critical|major|minor|info","file":"path/from/diff","line":123,'
    '"issue":"one-line problem","rationale":"why it matters + concrete fix","confidence":0-1}. '
    "Use exact file paths and hunk line numbers from the diff. Empty array [] if truly clean. "
    "Max 8 findings, highest severity first."
)
# ponytail: role text lives in prompts/<PROMPT_VERSION>/*.md; contract stays in code

async def _call(prompt: str, retries: int = 3, *, label: str = "llm") -> str:
    import time
    from .spine import emit
    global _fails, _open_until
    if time.time() < _open_until:
        raise RuntimeError("groq circuit open, try later")
    delay = 4
    for attempt in range(retries + 1):
        try:
            await asyncio.sleep(2)  # stagger to stay under 30 RPM
            t0 = time.time()
            out = (await get_llm().ainvoke(prompt)).content
            emit("llm.call", label=label, ms=int((time.time() - t0) * 1000),
                 prompt_chars=len(prompt), ok=True)
            _fails = 0
            return out
        except Exception as e:
            emit("llm.call", label=label, ok=False, error=str(e)[:200], attempt=attempt)
            _fails += 1
            if _fails >= 5:  # ponytail: 5 straight fails -> 60s open circuit
                _open_until = time.time() + 60
                _fails = 0
                emit("llm.circuit_open", label=label)
            if "429" not in str(e) and "rate" not in str(e).lower() and "413" not in str(e):
                raise
            if attempt == retries:
                raise
            await asyncio.sleep(delay)
            delay *= 2

def _parse(text: str) -> list[Finding]:
    try:
        start, end = text.index("["), text.rindex("]") + 1
        data = json.loads(text[start:end])
    except Exception:
        return []
    out = []
    for d in data if isinstance(data, list) else []:
        try:
            out.append(Finding(**d))
        except Exception:
            continue
    return out

async def run_specialist(role: str, diff: str, context: str = "") -> list[Finding]:
    from .security import guard_diff
    from .spine import emit
    diff, stripped = guard_diff(diff)
    if stripped:
        emit("security.injection_stripped", role=role, lines=stripped)
    prompt = f"{load_prompt(role)}\n{SYS}\n\n<context>{context[:4000]}</context>\n<diff>{diff[:12000]}</diff>"
    # ponytail: 12k-char cap keeps each call ~4k tokens, under the 8k TPM free-tier ceiling
    return _parse(await _call(prompt, label=f"specialist.{role}"))

async def run_aggregator(all_findings: list[Finding]) -> str:
    raw = "\n".join(f.model_dump_json() for f in all_findings)[:12000] or "No findings."
    prompt = f"{load_prompt('aggregator')}\n\n{raw}"
    return await _call(prompt, label="aggregator")

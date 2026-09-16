"""4 specialists + aggregator on Groq. Sequential + backoff = free-tier safe."""
from __future__ import annotations
import asyncio
import json
import os

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
_llm = None

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

PROMPTS = {
    "security": (
        "You are a senior AppSec reviewer. Inspect this PR diff for REAL, exploitable issues: "
        "injection (SQL/NoSQL/command/LDAP/XSS), broken authN/authZ incl. missing owner/tenant scoping on DB writes, "
        "IDOR, SSRF, open redirects, hardcoded secrets, weak crypto, mass assignment, prototype pollution, "
        "insecure direct object refs from req.body/query without validation, overly broad error messages leaking internals. "
        "Rate each finding critical/major/minor. Ignore purely stylistic points."
    ),
    "quality": (
        "You are a staff engineer reviewing for correctness and maintainability. Flag: unhandled promise rejections / "
        "missing await, race conditions, null/undefined derefs (esp. optional chaining gaps), wrong HTTP status codes, "
        "silent swallowing of errors, N+1 queries, unbounded loops/pagination, dead code, duplicated logic, "
        "magic strings/numbers, functions over ~50 lines, misleading names. "
        "Rate major for likely runtime bugs, minor for maintainability."
    ),
    "tests": (
        "You are a QA-focused reviewer. The diff may add product code without tests. Flag: new branches with zero test "
        "coverage, missing edge cases (404/empty/expired/unauthorized paths), untested error fallbacks, flaky patterns "
        "(time-based, random, external calls without mocks), assertions that can't fail. Suggest the concrete test to add."
    ),
    "docs": (
        "You are a docs reviewer. Flag ONLY user-facing gaps: exported components/functions with no doc comment, "
        "changed API contracts without updated types/docs, stale comments contradicting new code, cryptic UX copy. "
        "Do NOT flag internal trivial code — prefer fewer, higher-value findings."
    ),
}
SYS = (
    "Return ONLY a JSON array, no prose. Each item: "
    '{"severity":"critical|major|minor|info","file":"path/from/diff","line":123,'
    '"issue":"one-line problem","rationale":"why it matters + concrete fix","confidence":0-1}. '
    "Use exact file paths and hunk line numbers from the diff. Empty array [] if truly clean. "
    "Max 8 findings, highest severity first."
)

async def _call(prompt: str, retries: int = 3) -> str:
    delay = 4
    for attempt in range(retries + 1):
        try:
            await asyncio.sleep(2)  # stagger to stay under 30 RPM
            return (await get_llm().ainvoke(prompt)).content
        except Exception as e:
            if "429" not in str(e) and "rate" not in str(e).lower():
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
    prompt = f"{PROMPTS[role]}\n{SYS}\n\n<context>{context[:4000]}</context>\n<diff>{diff[:12000]}</diff>"
    # ponytail: 12k-char cap keeps each call ~4k tokens, under the 8k TPM free-tier ceiling
    return _parse(await _call(prompt))

async def run_aggregator(all_findings: list[Finding]) -> str:
    raw = "\n".join(f.model_dump_json() for f in all_findings)[:12000] or "No findings."
    prompt = (
        "Deduplicate these PR findings, drop confidence<0.4, sort critical first. "
        "Return clean Markdown: ## Summary + bullet per finding (severity, file:line, issue, fix).\n\n"
        f"{raw}"
    )
    return await _call(prompt)

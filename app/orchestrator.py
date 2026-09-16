"""Sequential LangGraph review: 4 specialists -> aggregator. 5 LLM calls/PR."""
from __future__ import annotations
import asyncio
from typing import TypedDict
from langgraph.graph import StateGraph, END
from .agents import Finding, run_specialist, run_aggregator
from .memory import retrieve

_gate = asyncio.Semaphore(1)  # serial execution stays inside the RPM limit

class State(TypedDict):
    diff: str
    repo: str
    context: str
    findings: list
    markdown: str

async def _ctx(s: State) -> State:
    s["context"] = retrieve(s["diff"], s.get("repo", "default"))
    return s

async def _review(role: str, s: State) -> State:
    async with _gate:
        s["findings"].extend(await run_specialist(role, s["diff"], s["context"]))
    return s

async def _agg(s: State) -> State:
    async with _gate:
        s["markdown"] = await run_aggregator(s["findings"])
    return s

def _make_review(role: str):
    async def _fn(s: State) -> State:
        return await _review(role, s)
    _fn.__name__ = role
    return _fn

def build():
    g = StateGraph(State)
    g.add_node("ctx", _ctx)
    for r in ("security", "quality", "tests", "docs"):
        g.add_node(r, _make_review(r))
    g.add_node("agg", _agg)
    g.set_entry_point("ctx")
    g.add_edge("ctx", "security")
    g.add_edge("security", "quality")
    g.add_edge("quality", "tests")
    g.add_edge("tests", "docs")
    g.add_edge("docs", "agg")
    g.add_edge("agg", END)
    return g.compile()

graph = build()

async def review_pr(diff: str, repo: str = "default") -> str:
    res = await graph.ainvoke({"diff": diff, "repo": repo, "findings": [], "markdown": "", "context": ""})
    return res["markdown"]

def demo():
    import json
    f = Finding(severity="major", file="a.py", line=1, issue="x", rationale="y", confidence=0.9)
    assert json.loads(f.model_dump_json())["severity"] == "major"
    assert _parse('[{"severity":"minor","confidence":0.8}]')[0].severity == "minor"
    assert _parse("no json here") == []
    print("agents OK")

from .agents import _parse  # noqa: E402

if __name__ == "__main__":
    demo()

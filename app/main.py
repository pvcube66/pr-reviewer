"""FastAPI ingress: GitHub webhook -> BackgroundTasks -> review -> comment."""
from __future__ import annotations
import hashlib
import hmac
import os
from fastapi import BackgroundTasks, FastAPI, Header, Request
from fastapi.responses import JSONResponse

from .memory import index_diff
from .orchestrator import review_pr
from .github import fetch_diff, post_comment
from .spine import emit

app = FastAPI(title="pr-reviewer")
_seen: dict[str, float] = {}  # ponytail: bounded dedupe; Redis only if multi-replica

def _mark_seen(delivery: str) -> bool:
    """True if duplicate. Evicts oldest past 10k entries."""
    import time
    if delivery in _seen:
        return True
    if len(_seen) >= 10_000:
        for k in list(_seen)[:1000]:
            del _seen[k]
    _seen[delivery] = time.time()
    return False

def _verify(secret: str, body: bytes, sig: str | None) -> bool:
    if not secret or not sig:
        return True  # dev mode
    expect = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expect, sig)

async def _process(repo: str, pr: int, diff: str = ""):
    emit("review.start", repo=repo, pr=pr, diff_chars=len(diff))
    try:
        diff = diff or await fetch_diff(repo, pr)
        if not diff.strip():
            emit("review.skip", repo=repo, pr=pr, reason="empty-diff")
            return
        index_diff(repo, diff)
        md = await review_pr(diff, repo)
        posted = await post_comment(repo, pr, md)
        emit("review.done", repo=repo, pr=pr, posted=posted, md_chars=len(md))
    except Exception as e:
        emit("review.error", repo=repo, pr=pr, error=str(e)[:200])
        print(f"review failed {repo}#{pr}: {e}")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/webhook/pr")
async def webhook(
    req: Request,
    bg: BackgroundTasks,
    x_github_delivery: str | None = Header(None),
    x_hub_signature_256: str | None = Header(None),
):
    body = await req.body()
    if not _verify(os.getenv("WEBHOOK_SECRET", ""), body, x_hub_signature_256):
        return JSONResponse({"error": "bad signature"}, status_code=401)
    if x_github_delivery and _mark_seen(x_github_delivery):
        return {"skipped": "duplicate"}

    payload = await req.json()
    # Manual: {repo, pr_number, diff}  OR  real GitHub pull_request event
    repo = payload.get("repo") or (payload.get("repository") or {}).get("full_name", "")
    pr = payload.get("pr_number") or (payload.get("pull_request") or {}).get("number", 0)
    diff = payload.get("diff", "")
    if not repo or not pr:
        return {"skipped": "no repo/pr"}
    action = payload.get("action", "")
    if not diff and action and action not in ("opened", "synchronize", "reopened", "ready_for_review"):
        return {"skipped": f"ignored action {action}"}
    bg.add_task(_process, repo, int(pr), diff)
    return {"queued": True, "repo": repo, "pr": pr}

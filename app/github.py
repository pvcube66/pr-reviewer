"""Post review as PR issue comment."""
from __future__ import annotations
import os
import httpx

async def fetch_diff(repo: str, pr: int) -> str:
    tok = os.getenv("GITHUB_TOKEN", "")
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(
            f"https://api.github.com/repos/{repo}/pulls/{pr}",
            headers={
                "Authorization": f"Bearer {tok}",
                "Accept": "application/vnd.github.diff",
            },
        )
        r.raise_for_status()
        return r.text

async def post_comment(repo: str, pr: int, body: str) -> bool:
    tok = os.getenv("GITHUB_TOKEN", "")
    if not tok:
        print(body)  # ponytail: stdout fallback when no token
        return False
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(
            f"https://api.github.com/repos/{repo}/issues/{pr}/comments",
            headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"},
            json={"body": body[:65000]},
        )
        r.raise_for_status()
    return True

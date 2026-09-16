# PR Reviewer

> Multi-agent AI code review on every pull request.

[![eval](https://github.com/pvcube66/pr-reviewer/actions/workflows/eval.yml/badge.svg)](https://github.com/pvcube66/pr-reviewer/actions/workflows/eval.yml)
![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)
![Groq](https://img.shields.io/badge/LLM-Groq-orange)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

Four specialist agents (security, quality, tests, docs) review your diff through LangGraph,
an aggregator merges their findings, and the result lands on your PR as a comment —
about 20 seconds after you open it.

---

## How it works

```
GitHub PR opened/synced
        │  webhook (HMAC-verified, deduped)
        ▼
┌─────────────┐   ┌──────────────────────────────────────────┐
│   FastAPI   │──▶│  LangGraph (sequential, TPM-safe)        │
│  /webhook   │   │  security → quality → tests → docs → agg │
└─────────────┘   └──────────────────────────────────────────┘
        │                       │  ▲
        │              ┌────────┘  │ ChromaDB
        │              ▼           │ codebase
        │     ┌──────────────┐  context
        └────▶│ PR comment   │◀──┘
              └──────────────┘
```

Every LLM call, review start/done/error, and stripped injection line is appended
to a local JSONL event spine (`agent_events.jsonl`) — same schema a Tiger
hypertable takes, so observability can move to a database later without rewiring.

---

## Quickstart

```bash
git clone https://github.com/pvcube66/pr-reviewer && cd pr-reviewer
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

cp .env.example .env   # fill GROQ_API_KEY + GITHUB_TOKEN
.venv/bin/uvicorn app.main:app --port 8000
```

| Variable         | Required for        | Where to get it                                  |
|------------------|---------------------|--------------------------------------------------|
| `GROQ_API_KEY`   | All reviews         | [Groq Console](https://console.groq.com)         |
| `GITHUB_TOKEN`   | Posting PR comments | Classic PAT, `repo` scope                        |
| `WEBHOOK_SECRET` | Verifying webhooks  | Any random string, shared with GitHub            |
| `GROQ_MODEL`     | —                   | Default `openai/gpt-oss-20b`                     |
| `PROMPT_VERSION` | —                   | Default `v1` — see `prompts/`                    |

### Try it without GitHub

```bash
curl -X POST localhost:8000/webhook/pr -H 'Content-Type: application/json' \
  -d '{"repo":"demo/repo","pr_number":1,"diff":"- old\n+ eval(user_input)"}'
```

No `GITHUB_TOKEN`? The review prints to server stdout instead of posting.

### Wire a real repo (2 min)

```bash
ngrok http 8000
```

Repo → **Settings → Webhooks → Add webhook**:

- Payload URL: `<ngrok-url>/webhook/pr`
- Content type: `application/json`
- Secret: your `WEBHOOK_SECRET`
- Events: **Pull requests** only

Open a PR — the bot comments in ~20s.

---

## Project layout

```
app/
├── main.py          # FastAPI ingress: HMAC verify, dedupe, BackgroundTasks
├── orchestrator.py  # LangGraph StateGraph, serialized for rate limits
├── agents.py        # 4 specialists + aggregator, Finding schema, backoff
├── prompts.py       # versioned prompt loader (PROMPT_VERSION)
├── memory.py        # ChromaDB vectors, chunk + retrieve
├── github.py        # fetch PR diffs, post review comments
├── security.py      # secret masking, prompt-injection guard
└── spine.py         # JSONL event spine (llm.call / review.*)
prompts/v1/           # role prompts — copy to v2 to iterate safely
evals/
├── golden/          # real PR diffs as regression fixtures
└── test_eval.py     # 7 offline tests, no API keys needed
```

## Reliability

- **Eval gate** — `python -m pytest evals/ -q`, enforced in CI on every push
- **Prompt versioning** — edit `prompts/v2/`, flip `PROMPT_VERSION`, roll back by flipping back
- **Circuit breaker** — 5 consecutive LLM failures open the circuit for 60s
- **Idempotency** — bounded 10k-entry delivery dedupe survives duplicate webhooks
- **Rate safety** — serialized agents + 2s stagger + 429/413 backoff ≈ 5 calls/PR, inside the TPM ceiling

## Limits

- ~12k chars of very large diffs reach the model — per-file chunking is the next lever
- Single replica (in-memory dedupe); file-based observability

# PR Reviewer (lean, Groq free tier)

## Run
```bash
pip install -r requirements.txt
cp .env.example .env  # set GROQ_API_KEY, GITHUB_TOKEN, WEBHOOK_SECRET
uvicorn app.main:app --reload --port 8000
ngrok http 8000  # point GitHub webhook /webhook/pr here
```

## Test locally (no GitHub needed)
```bash
curl -X POST localhost:8000/webhook/pr -H 'Content-Type: application/json' \
  -d '{"repo":"demo/repo","pr_number":1,"diff":"- old\n+ eval(user_input)"}'
# without GITHUB_TOKEN the Markdown prints to server stdout
```

## Limits
Sequential agents + 2s stagger + backoff = ~5 calls/PR, safe under 30 RPM / 30k TPM.

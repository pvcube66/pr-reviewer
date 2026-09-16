# Production Philosophy

North-star architecture for this project. The lean implementation in `app/` is
the working core; the phases below are the reference it grows toward.
Each phase ships as semantic, atomic commits.

## Phase 0: Cognitive Design

Define what the system thinks and where humans stay in the loop.

* `docs(design): define autonomy level and confidence-weighted HITL gates`
* `docs(design): specify the four specialist concerns (security, quality, tests, docs)`

## Phase 1: System Architecture

Module graph, inward-only dependency rules, ADRs.

* `docs(arch): add ADR-002 for modular monolith structure`
* `docs(arch): add ADR-003 for unified data spine`
* `chore(repo): initialize internal modules with inward-only dependencies`

## Phase 2: Frontend Engineering

Review dashboard, HITL queue, trace viewer.

* `feat(ui): setup app shell for PR dashboard`
* `feat(ui): implement HITL approval queue`
* `feat(ui): wire streaming components for real-time review updates`

## Phase 3: Backend & API

FastAPI shell, webhook ingress, idempotency.

* `feat(api): initialize FastAPI app and core routers`
* `feat(webhook): implement GitHub HMAC-SHA256 signature verification`
* `feat(ingress): add idempotency key checks (X-GitHub-Delivery UUID)`
* `feat(queue): decouple ingress from processing`

## Phase 4: Workflow Orchestration

LangGraph fan-out with concurrency controls for provider rate limits.

* `feat(orchestrator): define StateGraph and typed state`
* `feat(orchestrator): stagger parallel specialist calls under the RPM cap`
* `feat(orchestrator): add exponential backoff and retry on 429s`

## Phase 5: LLM & Reasoning

Model routing and the structured output contract.

* `feat(models): integrate chat model with high TPM headroom`
* `feat(prompts): versioned prompt registry in prompts/`
* `feat(agents): base agent logic with strict structured output for the Finding schema`

## Phase 6: Memory Architecture

Hybrid retrieval over codebase embeddings.

* `feat(memory): setup vector store client`
* `feat(memory): implement embedding integration`
* `feat(memory): build hybrid retriever merging dense and full-text search via RRF`

## Phase 7: Tooling & Sandboxing

* `feat(tools): build tool registry with strict capability scoping`
* `feat(sandbox): isolate code evaluation`

## Phase 8: Multi-Agent Systems

* `feat(agents): implement security, quality, tests, and docs specialists`
* `feat(agents): build aggregator to merge, deduplicate, and score findings`
* `feat(orchestrator): wire aggregator to confidence-weighted HITL gate`

## Phase 9: Evaluation

* `test(eval): create golden PR dataset`
* `test(eval): implement LLM-as-judge scoring`
* `ci(eval): wire regression gate to block degraded prompts`

## Phase 10: Observability

* `feat(obs): implement emit_agent_event for spans`
* `feat(obs): route all llm.call and tool.call events to the event spine`

## Phase 11: Security

* `feat(security): implement prompt-injection guards`
* `feat(security): add secret masking and API RBAC`

## Phase 12: Reliability

* `feat(reliability): implement circuit breakers on external APIs`
* `test(reliability): verify idempotency under fault injection`

## Phase 13: Infrastructure

* `chore(infra): provision database and configure queue`

## Phase 14: Data Engineering

* `db(schema): create vector + hypertable schema`
* `feat(data): build incremental ingestion pipeline for code chunking`

## Phase 15: Governance

* `feat(gov): expose queryable audit logs from event spine`
* `feat(gov): ensure explainability payload attached per finding`

## Phase 16: Economics

* `db(views): create continuous aggregates (agent health, cost per PR)`
* `feat(ui): wire token usage metrics to dashboard`

## Phase 17: Developer Experience

* `feat(ui): build prompt playground`
* `feat(ui): implement trace viewer reading from the event spine`

## Phase 18: CI/CD for AI

* `ci(deploy): setup prompt versioning and canary release paths`

## Phase 19: Human-in-the-Loop

* `feat(hitl): wire approval workflows and escalation`
* `feat(hitl): implement developer dispute API`

## Phase 20: Continuous Learning

* `feat(learn): implement drift detection from aggregates`
* `feat(learn): alert on rising agent rejection rates`

## Status

Done: 3, 4, 5, 8 (core), 9 (offline gate), 10 (JSONL spine), 11, 12.
Open: 0, 1, 2, 6 (hybrid retrieval), 7, 13, 14, 15, 16, 17, 18, 19, 20.

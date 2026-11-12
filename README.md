# OpsPilot

OpsPilot is a portfolio-grade applied AI engineering project that demonstrates how to build a reliable AI-assisted operations workflow with explicit tool boundaries, human approval, persistence, and tests.

> **Project status:** Initial scaffold in progress. This repository currently documents the intended system; implementation and test status will be updated as features are added.

## Problem

Operations teams often need to look up customer information, prepare communications, and create follow-up tasks. An AI assistant can help coordinate these steps, but it must not silently perform sensitive actions or pretend that a draft was sent.

## Product scope

The first version is a local, demonstrable application with three tools:

- **CRM lookup:** retrieve a customer from a seeded demo CRM.
- **Email drafting:** prepare an email for review; drafting never sends it.
- **Task creation:** create a follow-up task only after explicit approval.

The system will expose a FastAPI API, use SQLite for local persistence, and support an OpenAI-backed planning path with a deterministic fallback for offline development and tests.

## Engineering principles

1. **Structured tool contracts:** tools have validated inputs and outputs; the model does not execute arbitrary code.
2. **Human approval:** state-changing actions require an approval step. Email is draft-only in the initial version.
3. **Honest execution state:** distinguish proposed, awaiting approval, approved, completed, rejected, and failed actions.
4. **Deterministic tests:** automated tests must run without a live model API key.
5. **Provider isolation:** model and database details stay behind small interfaces.
6. **No fake integrations:** the demo CRM is local seed data, not a claim of a live CRM connection.

## Planned architecture

```text
Client
  |
  v
FastAPI routes
  |
  v
Application / orchestration service
  |----------------------|
  v                      v
Planner                 Tool registry
(OpenAI or              |-- CRM lookup (read-only)
 deterministic)        |-- Email draft (no send)
                         |-- Task creation (approval-gated)
  |                      |
  +----------+-----------+
             v
      Approval service
             |
             v
      Repository layer
             |
             v
           SQLite
```

## Planned API

- `GET /health` — health check
- `POST /api/v1/runs` — plan and execute a safe workflow
- `GET /api/v1/runs/{run_id}` — inspect a workflow run
- `POST /api/v1/approvals/{approval_id}/approve` — approve a pending action
- `POST /api/v1/approvals/{approval_id}/reject` — reject a pending action

Exact request and response schemas will be documented alongside the implementation.

## Local development

The implementation will target Python 3.12 or newer.

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\\Scripts\\Activate.ps1

pip install -e ".[dev]"
uvicorn opspilot.main:app --reload
```

Configuration will be read from environment variables. The application must start and its tests must pass without `OPENAI_API_KEY`; the deterministic planner is the default in that case.

## Quality gates

- Unit tests for schemas, tools, approval rules, and orchestration.
- API tests for successful, rejected, and invalid workflows.
- Tests proving that unapproved actions cannot mutate state.
- GitHub Actions CI for linting and tests.
- Docker image for reproducible local execution.

## Evaluation plan

The project will be evaluated on:

- Tool-selection accuracy on a small, documented scenario set.
- Correct argument validation and safe failure behavior.
- Approval enforcement for state-changing actions.
- Traceability of decisions and tool results.
- Test coverage of critical safety paths.
- Clear distinction between model-generated plans and deterministic application behavior.

## Security and limitations

This is a local portfolio demonstration, not a production-ready autonomous agent. It will not send real email, connect to a live CRM, or execute arbitrary shell/code actions. Secrets must be supplied through environment variables and must never be committed.

## Development roadmap

- [ ] Implement API, configuration, schemas, and SQLite persistence.
- [ ] Implement deterministic planner and optional OpenAI planner.
- [ ] Implement typed tool registry and demo CRM/email/task tools.
- [ ] Add approval workflow and audit events.
- [ ] Add unit and API tests.
- [ ] Add Docker and GitHub Actions CI.
- [ ] Complete architecture, evaluation, and usage documentation.

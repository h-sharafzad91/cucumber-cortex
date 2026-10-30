# Cucumber Cortex

**AI decision-worker service for Cucumber Trading Arena.**

Cortex consumes market and portfolio updates from the Cerebellum backend, builds context for an AI trading agent, parses the model response into a structured action, and submits that action to Cerebellum for validation and processing.

The service separates probabilistic decision generation from the backend that owns trading-state changes.

## Processing flow

```text
Cerebellum
   │
   └── Redis Pub/Sub: arena:ticks:{roundId}:{agentId}
             │
             ▼
       Cucumber Cortex
             │
             ├── Build agent context
             ├── Request an LLM decision
             ├── Parse and validate the action
             │
             ▼
       Cerebellum API
       (action processing)
```

## Core responsibilities

- Subscribe to per-agent tick channels through Redis.
- Build prompts using agent configuration, market data, portfolio state, and risk constraints.
- Call configured LLM providers through provider integrations.
- Parse model output into structured trading actions and reasoning.
- Submit proposed actions to Cerebellum over HTTP.
- Keep decision generation separate from execution and state management.

## Technology

| Area | Technologies |
|---|---|
| Runtime | Python 3.11+ |
| API / service framework | FastAPI |
| Data validation and settings | Pydantic, pydantic-settings |
| LLM integration | OpenAI SDK; provider integrations are defined in the project |
| Messaging | Redis |
| HTTP client | HTTPX |
| Logging | structlog |
| Development | pytest, pytest-asyncio, Ruff |

## Local development

Requirements: Python 3.11+ and a reachable Redis instance.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Configure the required environment variables for Redis, the Cerebellum API, and the selected model provider. Keep API keys in local environment configuration; never commit secrets.

Start the service using the application entry point and configuration documented in the source.

## Design principle

An LLM response is a proposal, not an authority. Cortex is responsible for generating and structuring a decision; Cerebellum remains the boundary that validates and processes the submitted action.

## Project status

This is an actively developed AI-agent service within a multi-component trading-arena project. The repository should not be interpreted as evidence of profitable trading, audited financial execution, or production readiness.

## Related component

- [Cucumber Cerebellum](https://github.com/h-sharafzad91/cucumber-cerebellum) — orchestration and action-processing backend.

## Author

Built by [Hossein Sharafzad](https://github.com/h-sharafzad91).

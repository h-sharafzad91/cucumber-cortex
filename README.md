# Cucumber Cortex

AI agent worker service for Cucumber Trade Arena.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
```

## Development

```bash
uvicorn src.main:app --reload --port 8000
```

## Production

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## Environment Variables

See `.env.example` for required configuration.

## API Endpoints

- `GET /health` - Health check
- `POST /agents/add` - Add agent to worker pool
- `DELETE /agents/{agent_id}` - Remove agent
- `GET /agents` - List agents in pool
- `POST /subscribe` - Subscribe to round tick channel
- `POST /unsubscribe` - Stop subscriptions
- `POST /process` - Manually process tick for all agents
- `POST /process/single` - Process tick for single agent

## Architecture

1. **Redis Subscriber** - Listens to `arena:ticks:{round_id}` channel
2. **Agent Worker** - Builds prompts, calls LLM, parses response
3. **Cerebellum Client** - Submits actions to Cerebellum API

## Flow

```
Redis (tick) → Cortex → LLM (GPT-4o-mini) → Parse → Cerebellum (POST /action)
```

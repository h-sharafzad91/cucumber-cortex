# Cucumber Cortex

AI trading agent service for Cucumber Trading Arena - the "brain" that makes trading decisions using LLMs. Named after the brain's cortex which handles complex decision-making, this service processes market data and makes intelligent trading decisions.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CUCUMBER TRADING ARENA                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐         ┌──────────────┐                                │
│   │ cucumber-web │         │cucumber-admin│                                │
│   │   Port 3000  │         │   Port 3002  │                                │
│   └──────────────┘         └──────────────┘                                │
│          │                        │                                         │
│          │                        │                                         │
│          ▼                        ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │                    cucumber-cerebellum                           │      │
│   │                        Port 3001                                 │      │
│   └──────────────────────────────────┬───────────────────────────────┘      │
│                                      │                                       │
│              Tick Scheduler          │ Redis Pub/Sub                        │
│              (per-agent)             │ arena:ticks:{roundId}:{agentId}      │
│                                      ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │              ★ cucumber-cortex (THIS REPO) ★                    │      │
│   │                    (Python/FastAPI)                             │      │
│   │                        Port 8000                                 │      │
│   │                                                                  │      │
│   │  ┌─────────────────────────────────────────────────────────┐   │      │
│   │  │                  Inbound Layer                           │   │      │
│   │  │  ┌─────────────┐  ┌─────────────┐                       │   │      │
│   │  │  │   FastAPI   │  │    Redis    │                       │   │      │
│   │  │  │  Endpoints  │  │  Subscriber │                       │   │      │
│   │  │  └─────────────┘  └─────────────┘                       │   │      │
│   │  └─────────────────────────────────────────────────────────┘   │      │
│   │                              │                                  │      │
│   │  ┌─────────────────────────────────────────────────────────┐   │      │
│   │  │                  Processing Layer                        │   │      │
│   │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │   │      │
│   │  │  │    Agent     │  │   Prompt     │  │   Action     │  │   │      │
│   │  │  │   Worker     │  │   Builder    │  │   Parser     │  │   │      │
│   │  │  └──────────────┘  └──────────────┘  └──────────────┘  │   │      │
│   │  └─────────────────────────────────────────────────────────┘   │      │
│   │                              │                                  │      │
│   │  ┌─────────────────────────────────────────────────────────┐   │      │
│   │  │                  LLM Providers                           │   │      │
│   │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │   │      │
│   │  │  │  OpenAI  │ │ Anthropic│ │  Google  │ │   xAI    │   │   │      │
│   │  │  │  GPT-4o  │ │  Claude  │ │  Gemini  │ │   Grok   │   │   │      │
│   │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │   │      │
│   │  └─────────────────────────────────────────────────────────┘   │      │
│   │                              │                                  │      │
│   │  ┌─────────────────────────────────────────────────────────┐   │      │
│   │  │                  Outbound Layer                          │   │      │
│   │  │  ┌──────────────────────────────────────────────────┐   │   │      │
│   │  │  │            Cerebellum Client                      │   │   │      │
│   │  │  │      POST /v1/arena/:roundId/action              │   │   │      │
│   │  │  └──────────────────────────────────────────────────┘   │   │      │
│   │  └─────────────────────────────────────────────────────────┘   │      │
│   └─────────────────────────────────────────────────────────────────┘      │
│                                      │                                       │
│                                      │ REST API                              │
│                                      ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │                    cucumber-cerebellum                           │      │
│   │               (executes trade, updates PnL)                     │      │
│   └─────────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## This Repository (cucumber-cortex)

The AI trading agent that:
- **Subscribes to per-agent Redis tick channels**: Listens to `arena:ticks:{roundId}:{agentId}` for each active agent. Each subscription runs independently, so Agent A getting its tick doesn't block Agent B
- **Builds context-aware prompts with market data & portfolio**: Constructs a detailed prompt for the LLM including the agent's personality, current market prices, open positions, cash balance, and risk parameters
- **Calls LLM providers (OpenAI, Anthropic, Google, xAI)**: Supports multiple LLM backends. The model is selected based on the agent's configuration (e.g., one agent uses GPT-4o, another uses Claude)
- **Parses trading decisions from LLM responses**: Extracts structured action (BUY_MARKET, SELL_MARKET, HOLD), asset, size, and reasoning from the LLM's text response
- **Submits actions back to Cerebellum for execution**: Sends HTTP POST to Cerebellum with the trade decision. Cerebellum handles actual execution and PnL calculation

## Communication Flow

### 1. Inbound: Redis Subscription (← Cerebellum)
```
cucumber-cerebellum  ───Redis───►  cucumber-cortex
        │                                │
        │ Per-agent tick channels:       │
        │   arena:ticks:{roundId}:{agentId}
        │                                │
        │ Tick payload:                  │
        │   - tick_id                    │
        │   - market prices              │
        │   - agent's portfolio          │
        │   - trading constraints        │
        └────────────────────────────────┘
```

### 2. Processing: LLM Call
```
cucumber-cortex  ───API───►  LLM Provider
        │                         │
        │ Prompt includes:        │
        │   - Agent persona       │
        │   - Trading strategy    │
        │   - Current positions   │
        │   - Market data         │
        │   - Risk parameters     │
        │                         │
        │ Response:               │
        │   - Action (BUY/SELL/HOLD)
        │   - Reasoning           │
        │   - Size                │
        └─────────────────────────┘
```

### 3. Outbound: Submit Action (→ Cerebellum)
```
cucumber-cortex  ───HTTP───►  cucumber-cerebellum
        │                            │
        │ POST /v1/arena/:id/action │
        │   {                        │
        │     agent_id,              │
        │     tick_id,               │
        │     action: "BUY_MARKET",  │
        │     asset: "ETH_USDC",     │
        │     size_usd: 100,         │
        │     reasoning: "..."       │
        │   }                        │
        └────────────────────────────┘
```

## Project Structure

```
cucumber-cortex/
├── src/
│   ├── main.py                      # FastAPI application entry point
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py              # Environment configuration
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── tick_payload.py          # Tick data model
│   │   ├── agent_action.py          # Action response model
│   │   └── agent_config.py          # Agent configuration model
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── redis_subscriber.py      # Per-agent Redis subscription ★
│   │   ├── cerebellum_client.py     # HTTP client to submit actions
│   │   ├── prompt_builder.py        # LLM prompt construction
│   │   ├── action_parser.py         # Parse LLM response to action
│   │   └── smart_trigger.py         # Conditional tick processing
│   │
│   ├── workers/
│   │   ├── __init__.py
│   │   └── agent_worker.py          # Core processing logic ★
│   │
│   ├── llm_providers/
│   │   ├── __init__.py
│   │   ├── base.py                  # Base provider interface
│   │   ├── factory.py               # Provider factory
│   │   ├── router.py                # Multi-provider routing
│   │   ├── models.py                # Model definitions
│   │   ├── openai_provider.py       # OpenAI (GPT-4o, GPT-4o-mini)
│   │   ├── anthropic_provider.py    # Anthropic (Claude 3.5 Sonnet)
│   │   ├── google_provider.py       # Google (Gemini)
│   │   └── xai_provider.py          # xAI (Grok)
│   │
│   └── utils/
│       ├── __init__.py
│       └── logger.py                # Structured logging
│
├── .env.example
├── requirements.txt
├── pyproject.toml
├── Dockerfile
└── README.md
```

## Key Components

### Redis Subscriber (Per-Agent Channels)

```python
# redis_subscriber.py
class RedisSubscriber:
    async def subscribe_to_agent(self, round_id: str, agent_id: str, handler):
        """Subscribe to individual agent tick channel"""
        channel = f"arena:ticks:{round_id}:{agent_id}"
        # Each agent has its own subscription
        # Ticks arrive at agent's configured interval
```

**Why per-agent channels?**
- Agent A (30s tick) and Agent B (60s tick) receive ticks at different times
- Prevents message queue congestion
- Allows Cortex to scale horizontally (different Cortex instances can handle different agents)

### Agent Worker (Non-Blocking Processing)

```python
# main.py - Tick handler
async def tick_handler(tick_json: str):
    tick = TickPayload.parse_raw(tick_json)

    # Process in background task (non-blocking)
    async def process_in_background():
        await worker.process_tick_and_submit(tick, round_id)

    task = asyncio.create_task(process_in_background())
    background_tasks.add(task)
```

**Why non-blocking?**
- LLM API calls can take 2-30+ seconds (especially with rate limits)
- If we `await` directly, subsequent ticks would be delayed
- Background tasks allow multiple ticks to be processed concurrently
- Critical for agents with fast tick intervals (10-15s)

### Prompt Builder

```python
# prompt_builder.py
def build_prompt(tick: TickPayload, agent_config: AgentConfig) -> str:
    return f"""
    You are {agent_config.name}, a trading agent.

    Strategy: {agent_config.persona_config.strategy}
    Risk Tolerance: {agent_config.persona_config.risk_tolerance}
    Trading Style: {agent_config.trading_style}

    Current Market:
    - ETH/USDC: ${tick.market.ETH_USDC.price}

    Your Portfolio:
    - Cash: ${tick.portfolio.balance_usd}
    - Positions: {tick.portfolio.positions}

    Leverage: {agent_config.leverage}x
    Stop Loss: {agent_config.stop_loss_percent}%
    Take Profit: {agent_config.take_profit_percent}%

    Respond with your trading decision...
    """
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/agents/add` | Add agent to worker pool |
| DELETE | `/agents/{agent_id}` | Remove agent from pool |
| GET | `/agents` | List agents in pool |
| POST | `/subscribe` | Subscribe to round tick channel |
| POST | `/unsubscribe` | Stop all subscriptions |
| POST | `/process` | Manually trigger tick for all agents |
| POST | `/process/single` | Process single agent tick |

## LLM Providers

| Provider | Models | Config Key | Cost (approx) |
|----------|--------|------------|---------------|
| OpenAI | gpt-4o, gpt-4o-mini | `OPENAI_API_KEY` | $0.15-2.50/1M tokens |
| Anthropic | claude-3-5-sonnet | `ANTHROPIC_API_KEY` | $3-15/1M tokens |
| Google | gemini-1.5-flash | `GOOGLE_API_KEY` | $0.075/1M tokens |
| xAI | grok-beta | `XAI_API_KEY` | $5/1M tokens |

### Model Selection

Models are selected based on agent configuration:

```python
# In agent_config
{
    "worker_config": {
        "model": "gpt-4o-mini",  # or "claude-3-5-sonnet", "gemini-1.5-flash"
        "temperature": 0.7,      # Higher = more random/creative decisions
        "max_tokens": 500        # Max response length
    }
}
```

**Choosing a model:**
- **gpt-4o-mini**: Fast, cheap, good for high-frequency trading (10-30s ticks)
- **gpt-4o**: More sophisticated reasoning, better for complex strategies
- **claude-3-5-sonnet**: Strong reasoning, good at following complex instructions
- **gemini-1.5-flash**: Very fast and cheap, good for simple strategies
- **grok-beta**: Alternative option with different "personality"

### Action Parsing

The LLM returns a text response that must be parsed into structured action:

```python
# action_parser.py
def parse_action(llm_response: str) -> AgentAction:
    # LLM is prompted to respond in a specific format:
    # ACTION: BUY_MARKET
    # ASSET: ETH_USDC
    # SIZE_USD: 100
    # REASONING: ETH showing bullish momentum...

    # Parser extracts these fields using regex or structured output
    return AgentAction(
        action="BUY_MARKET",
        asset="ETH_USDC",
        size_usd=100,
        reasoning="ETH showing bullish momentum..."
    )
```

## Tick Processing Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      TICK PROCESSING                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Redis Subscriber receives tick                              │
│     └─► arena:ticks:{roundId}:{agentId}                        │
│                                                                  │
│  2. Tick Handler (non-blocking)                                 │
│     └─► asyncio.create_task(process_in_background())           │
│                                                                  │
│  3. Agent Worker                                                 │
│     ├─► Fetch agent config from Cerebellum                     │
│     ├─► Build prompt with market + portfolio data              │
│     ├─► Call LLM provider                                       │
│     └─► Parse response to action                                │
│                                                                  │
│  4. Cerebellum Client                                           │
│     └─► POST /v1/arena/:roundId/action                         │
│                                                                  │
│  5. Done (next tick arrives based on agent's interval)         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Setup

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
```env
CEREBELLUM_URL=http://localhost:3001
REDIS_URL=redis://localhost:6379

# At least one LLM provider required
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GOOGLE_API_KEY=...
# XAI_API_KEY=...
```

## Development

```bash
uvicorn src.main:app --reload --port 8000
```

## Production

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Docker

```bash
docker build -t cucumber-cortex .
docker run -p 8000:8000 --env-file .env cucumber-cortex
```

## Related Repositories

| Repository | Description | Communication |
|------------|-------------|---------------|
| [cucumber-cerebellum](https://github.com/h-sharafzad91/cucumber-cerebellum) | Backend orchestration | Redis ← / HTTP → |
| [cucumber-web](https://github.com/h-sharafzad91/cucumber-web) | User frontend | (indirect via Cerebellum) |
| [cucumber-admin](https://github.com/h-sharafzad91/cucumber-admin) | Admin dashboard | (indirect via Cerebellum) |

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `CEREBELLUM_URL` | Cerebellum API URL | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `OPENAI_API_KEY` | OpenAI API key | One of |
| `ANTHROPIC_API_KEY` | Anthropic API key | these |
| `GOOGLE_API_KEY` | Google AI API key | required |
| `XAI_API_KEY` | xAI API key | |
| `LOG_LEVEL` | Logging level | No (default: INFO) |

## Performance Notes

- **Non-blocking tick processing**: Each tick is processed in a background task, preventing slow LLM responses from blocking subsequent ticks
- **Per-agent subscriptions**: Each agent subscribes to its own Redis channel, enabling independent tick intervals
- **Rate limit handling**: If LLM rate limits are hit, processing continues for other agents

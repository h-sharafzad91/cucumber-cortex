import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import settings
from .services import redis_subscriber, cerebellum_client
from .workers.agent_worker import AgentWorkerPool
from .schemas import TickPayload, AgentAction, AgentConfig, PersonaConfig, WorkerConfig
from .utils import logger


worker_pool = AgentWorkerPool()
background_tasks: set[asyncio.Task] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting_cortex", port=settings.port)
    print(f"[STARTUP] Redis URL configured: {settings.redis_url[:50]}..." if len(settings.redis_url) > 50 else f"[STARTUP] Redis URL configured: {settings.redis_url}")
    await redis_subscriber.connect()

    yield

    logger.info("stopping_cortex")
    redis_subscriber.stop()
    await redis_subscriber.disconnect()
    await cerebellum_client.close()

    for task in background_tasks:
        task.cancel()


app = FastAPI(
    title="Cucumber Cortex",
    description="AI Agent Worker Service",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "cortex"}


class AddAgentRequest(BaseModel):
    agent_id: str


class ProcessTickRequest(BaseModel):
    tick_payload: dict
    round_id: str


@app.post("/agents/add")
async def add_agent(request: AddAgentRequest):
    try:
        await worker_pool.add_agent(request.agent_id)
        return {"status": "added", "agent_id": request.agent_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/agents/{agent_id}")
async def remove_agent(agent_id: str):
    worker_pool.remove_agent(agent_id)
    return {"status": "removed", "agent_id": agent_id}


@app.get("/agents")
async def list_agents():
    return {"agents": list(worker_pool.workers.keys())}


@app.get("/subscriptions")
async def list_subscriptions():
    subscriptions = {}
    for round_id, task in redis_subscriber._subscriptions.items():
        subscriptions[round_id] = {
            "active": not task.done(),
            "done": task.done(),
            "cancelled": task.cancelled() if task.done() else False,
        }
    agent_subscriptions = {}
    for key, task in redis_subscriber._agent_subscriptions.items():
        agent_subscriptions[key] = {
            "active": not task.done(),
            "done": task.done(),
            "cancelled": task.cancelled() if task.done() else False,
        }
    return {
        "redis_running": redis_subscriber._running,
        "subscriptions": subscriptions,
        "agent_subscriptions": agent_subscriptions,
        "total_agents": len(worker_pool.workers),
    }


@app.post("/process")
async def process_tick(request: ProcessTickRequest):
    try:
        import json
        tick_json = json.dumps(request.tick_payload)
        results = await worker_pool.process_tick_for_all(tick_json, request.round_id)
        return {"results": results}
    except Exception as e:
        logger.error("process_tick_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


class SubscribeRequest(BaseModel):
    round_id: str
    agent_ids: list[str]


@app.post("/subscribe")
async def subscribe_to_round(request: SubscribeRequest):
    print(f"[{datetime.now().isoformat()}] [SUBSCRIBE] Starting subscription for round {request.round_id} with agents {request.agent_ids}")

    for agent_id in request.agent_ids:
        try:
            await worker_pool.add_agent(agent_id)
            print(f"[{datetime.now().isoformat()}] [SUBSCRIBE] Added agent {agent_id} to pool")
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] [SUBSCRIBE] ERROR adding agent {agent_id}: {e}")
            raise

    for agent_id in request.agent_ids:
        def create_agent_tick_handler(aid: str, rid: str):
            async def handle_agent_tick(tick_data: str):
                try:
                    print(f"[{datetime.now().isoformat()}] [TICK] Received tick for agent {aid} in round {rid}")
                    if aid in worker_pool.workers:
                        worker = worker_pool.workers[aid]
                        tick = TickPayload.model_validate_json(tick_data)

                        # Process tick in background to avoid blocking next tick
                        async def process_in_background():
                            try:
                                await worker.process_tick_and_submit(tick, rid)
                                print(f"[{datetime.now().isoformat()}] [TICK] Processed tick #{tick.tick_number} for agent {aid}")
                            except Exception as e:
                                print(f"[{datetime.now().isoformat()}] [TICK] ERROR processing tick #{tick.tick_number} for agent {aid}: {e}")
                                logger.error("tick_processing_error", agent_id=aid, tick=tick.tick_number, error=str(e))

                        task = asyncio.create_task(process_in_background())
                        background_tasks.add(task)
                        task.add_done_callback(background_tasks.discard)
                    else:
                        print(f"[{datetime.now().isoformat()}] [TICK] Agent {aid} not in worker pool, skipping")
                except Exception as e:
                    print(f"[{datetime.now().isoformat()}] [TICK] ERROR handling tick for agent {aid}: {e}")
                    logger.error("tick_handler_error", agent_id=aid, error=str(e))
            return handle_agent_tick

        handler = create_agent_tick_handler(agent_id, request.round_id)

        async def subscription_wrapper(aid=agent_id, h=handler):
            try:
                print(f"[{datetime.now().isoformat()}] [REDIS] Starting subscription to arena:ticks:{request.round_id}:{aid}")
                await redis_subscriber.subscribe_to_agent(request.round_id, aid, h)
            except Exception as e:
                print(f"[{datetime.now().isoformat()}] [REDIS] ERROR in subscription for agent {aid}: {e}")
                import traceback
                traceback.print_exc()

        task = asyncio.create_task(subscription_wrapper())
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

    print(f"[{datetime.now().isoformat()}] [SUBSCRIBE] Subscription tasks created for {len(request.agent_ids)} agents in round {request.round_id}")
    return {
        "status": "subscribed",
        "round_id": request.round_id,
        "agents": request.agent_ids,
    }


@app.post("/unsubscribe")
async def unsubscribe():
    for round_id, task in list(redis_subscriber._subscriptions.items()):
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    for key, task in list(redis_subscriber._agent_subscriptions.items()):
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    redis_subscriber._subscriptions.clear()
    redis_subscriber._agent_subscriptions.clear()
    worker_pool.workers.clear()
    return {"status": "unsubscribed", "message": "All subscriptions cancelled"}


@app.post("/restart-subscriber")
async def restart_subscriber():
    if not redis_subscriber._running:
        redis_subscriber._running = True
        return {"status": "restarted", "message": "Redis subscriber restarted"}
    return {"status": "already_running", "message": "Redis subscriber is already running"}


class SingleProcessRequest(BaseModel):
    agent_id: str
    tick_payload: dict
    round_id: str


@app.post("/process/single")
async def process_single(request: SingleProcessRequest):
    try:
        if request.agent_id not in worker_pool.workers:
            await worker_pool.add_agent(request.agent_id)

        worker = worker_pool.workers[request.agent_id]

        tick = TickPayload.model_validate(request.tick_payload)

        result = await worker.process_tick_and_submit(tick, request.round_id)

        return result

    except Exception as e:
        logger.error("single_process_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

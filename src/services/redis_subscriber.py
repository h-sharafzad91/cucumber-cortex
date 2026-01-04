import asyncio
from typing import Callable, Awaitable
from datetime import datetime

import redis.asyncio as redis

from ..config import settings
from ..utils import logger


class RedisSubscriber:
    def __init__(self):
        self._subscriptions: dict[str, asyncio.Task] = {}
        self._agent_subscriptions: dict[str, asyncio.Task] = {}
        self._subscription_locks: dict[str, asyncio.Lock] = {}
        self._running = False

    async def connect(self):
        self._running = True
        logger.info("redis_subscriber_initialized", url=settings.redis_url)

    async def disconnect(self):
        self._running = False
        for round_id, task in list(self._subscriptions.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._subscriptions.clear()
        for key, task in list(self._agent_subscriptions.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._agent_subscriptions.clear()
        logger.info("redis_disconnected")

    async def _subscribe_loop(
        self,
        channel: str,
        handler: Callable[[str], Awaitable[None]],
    ):
        print(f"[{datetime.now().isoformat()}] [REDIS] _subscribe_loop starting for channel: {channel}")

        retry_count = 0
        max_retries = 10
        retry_delay = 2  # seconds

        while self._running and retry_count < max_retries:
            redis_conn = None
            pubsub = None

            try:
                if settings.redis_url.startswith('rediss://'):
                    print(f"[{datetime.now().isoformat()}] [REDIS] Using TLS connection (rediss://)")
                    redis_conn = redis.from_url(
                        settings.redis_url,
                        ssl_cert_reqs=None
                    )
                else:
                    print(f"[{datetime.now().isoformat()}] [REDIS] Using standard connection (redis://)")
                    redis_conn = redis.from_url(settings.redis_url)
                print(f"[{datetime.now().isoformat()}] [REDIS] Redis connection created")

                pubsub = redis_conn.pubsub()
                print(f"[{datetime.now().isoformat()}] [REDIS] Pubsub created")

                print(f"[{datetime.now().isoformat()}] [REDIS] Subscribing to channel: {channel}")
                logger.info("redis_connecting", channel=channel, url=settings.redis_url[:50])
                await pubsub.subscribe(channel)
                print(f"[{datetime.now().isoformat()}] [REDIS] ✅ Successfully subscribed to: {channel}")
                logger.info("redis_subscribed", channel=channel)

                # Reset retry count on successful connection
                retry_count = 0

                logger.info("redis_loop_starting", running=self._running)
                while self._running:
                    try:
                        message = await pubsub.get_message(
                            ignore_subscribe_messages=True,
                            timeout=1.0,
                        )
                        if message and message["type"] == "message":
                            print(f"[{datetime.now().isoformat()}] [REDIS] ⏱️  Tick received from channel: {channel}")
                            logger.info("redis_message_received", channel=channel)
                            data = message["data"]
                            if isinstance(data, bytes):
                                data = data.decode("utf-8")
                            await handler(data)
                    except asyncio.CancelledError:
                        print(f"[{datetime.now().isoformat()}] [REDIS] Subscription cancelled for: {channel}")
                        raise
                    except Exception as e:
                        logger.error("redis_message_error", error=str(e))
                        print(f"[{datetime.now().isoformat()}] [REDIS] ⚠️  Message processing error: {e}")
                        await asyncio.sleep(0.1)

                # Normal exit from loop
                break

            except asyncio.CancelledError:
                print(f"[{datetime.now().isoformat()}] [REDIS] Subscription cancelled during setup for: {channel}")
                break
            except Exception as e:
                retry_count += 1
                print(f"[{datetime.now().isoformat()}] [REDIS] ❌ Connection error (attempt {retry_count}/{max_retries}): {e}")
                logger.error("redis_connection_error", error=str(e), retry=retry_count)

                if retry_count < max_retries:
                    print(f"[{datetime.now().isoformat()}] [REDIS] Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 30)  # Exponential backoff, max 30s
                else:
                    print(f"[{datetime.now().isoformat()}] [REDIS] ❌ Max retries reached for: {channel}")
                    logger.error("redis_max_retries_exceeded", channel=channel)
            finally:
                # Clean up connections
                if pubsub:
                    try:
                        await pubsub.close()
                    except:
                        pass
                if redis_conn:
                    try:
                        await redis_conn.close()
                    except:
                        pass

        logger.info("redis_subscription_closed", channel=channel)

    async def subscribe_to_round(
        self,
        round_id: str,
        handler: Callable[[str], Awaitable[None]],
    ):
        # Get or create lock for this round
        if round_id not in self._subscription_locks:
            self._subscription_locks[round_id] = asyncio.Lock()

        lock = self._subscription_locks[round_id]

        async with lock:
            # Check if already subscribed and running
            if round_id in self._subscriptions and not self._subscriptions[round_id].done():
                print(f"[{datetime.now().isoformat()}] [REDIS] Already subscribed to round {round_id}, skipping duplicate")
                return

            # Cancel existing subscription if present
            if round_id in self._subscriptions:
                self._subscriptions[round_id].cancel()
                try:
                    await self._subscriptions[round_id]
                except asyncio.CancelledError:
                    pass

            channel = f"arena:ticks:{round_id}"

            # Create subscription task (don't await directly to avoid blocking)
            task = asyncio.create_task(self._subscribe_loop(channel, handler))
            self._subscriptions[round_id] = task

            print(f"[{datetime.now().isoformat()}] [REDIS] Created subscription for round {round_id}")

    async def subscribe_to_agent(
        self,
        round_id: str,
        agent_id: str,
        handler: Callable[[str], Awaitable[None]],
    ):
        key = f"{round_id}:{agent_id}"

        if key not in self._subscription_locks:
            self._subscription_locks[key] = asyncio.Lock()

        lock = self._subscription_locks[key]

        async with lock:
            if key in self._agent_subscriptions and not self._agent_subscriptions[key].done():
                print(f"[{datetime.now().isoformat()}] [REDIS] Already subscribed to agent {agent_id} in round {round_id}")
                return

            if key in self._agent_subscriptions:
                self._agent_subscriptions[key].cancel()
                try:
                    await self._agent_subscriptions[key]
                except asyncio.CancelledError:
                    pass

            channel = f"arena:ticks:{round_id}:{agent_id}"

            task = asyncio.create_task(self._subscribe_loop(channel, handler))
            self._agent_subscriptions[key] = task

            print(f"[{datetime.now().isoformat()}] [REDIS] Created subscription for agent {agent_id} in round {round_id}")

    def stop(self):
        self._running = False


redis_subscriber = RedisSubscriber()

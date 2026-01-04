import json
import asyncio
import time
from datetime import datetime

from ..schemas import TickPayload, AgentConfig, AgentAction, PersonaConfig, WorkerConfig
from ..services import prompt_builder, action_parser, cerebellum_client
from ..llm_providers import get_llm_router
from ..utils import logger


PROVIDER_TICK_INTERVALS = {
    "google": 5.0,
    "openai": 2.0,
    "anthropic": 2.0,
    "xai": 2.0,
}
DEFAULT_MIN_TICK_INTERVAL = 5.0


class AgentWorker:
    def __init__(self, agent_config: AgentConfig):
        self.agent = agent_config
        self._last_llm_call: float = 0
        self._min_tick_interval = self._get_tick_interval_for_model(agent_config.worker_config.model)
        logger.info(
            "agent_worker_initialized",
            agent_id=agent_config.id,
            model=agent_config.worker_config.model,
            tick_interval=f"{self._min_tick_interval}s",
        )

    def _get_tick_interval_for_model(self, model: str) -> float:
        model_lower = model.lower()
        if "gemini" in model_lower:
            return PROVIDER_TICK_INTERVALS.get("google", DEFAULT_MIN_TICK_INTERVAL)
        elif "gpt" in model_lower or "o1" in model_lower:
            return PROVIDER_TICK_INTERVALS.get("openai", DEFAULT_MIN_TICK_INTERVAL)
        elif "claude" in model_lower:
            return PROVIDER_TICK_INTERVALS.get("anthropic", DEFAULT_MIN_TICK_INTERVAL)
        elif "grok" in model_lower:
            return PROVIDER_TICK_INTERVALS.get("xai", DEFAULT_MIN_TICK_INTERVAL)
        return DEFAULT_MIN_TICK_INTERVAL

    async def process_tick(self, tick: TickPayload) -> AgentAction:
        print(f"[{datetime.now().isoformat()}] [WORKER] Starting process_tick for agent {self.agent.id}, tick #{tick.tick_number}")

        logger.info(
            "processing_tick",
            agent_id=self.agent.id,
            tick_id=tick.tick_id,
            tick_number=tick.tick_number,
            model=self.agent.worker_config.model,
        )

        now = time.time()
        time_since_last_call = now - self._last_llm_call

        if time_since_last_call < self._min_tick_interval:
            wait_remaining = self._min_tick_interval - time_since_last_call
            print(f"[{datetime.now().isoformat()}] [WORKER] Tick throttled for agent {self.agent.id}, wait {wait_remaining:.1f}s")
            logger.info(
                "tick_throttled",
                agent_id=self.agent.id,
                tick_number=tick.tick_number,
                wait_remaining=f"{wait_remaining:.1f}s",
                reason="Rate limit protection",
            )
            return AgentAction.hold(
                agent_id=self.agent.id,
                tick_id=tick.tick_id,
                reasoning=f"Throttled: waiting {wait_remaining:.1f}s for rate limit",
            )

        self._last_llm_call = now

        print(f"[{datetime.now().isoformat()}] [WORKER] Building prompts for agent {self.agent.id}")

        logger.info(
            "calling_llm",
            agent_id=self.agent.id,
            tick_number=tick.tick_number,
            provider=self.agent.worker_config.provider.value if hasattr(self.agent.worker_config, 'provider') else "auto",
            model=self.agent.worker_config.model,
        )

        try:
            system_prompt = prompt_builder.build_system_prompt(self.agent)
            user_prompt = prompt_builder.build_user_prompt(tick)

            print(f"[{datetime.now().isoformat()}] [WORKER] Calling LLM for agent {self.agent.id}, model={self.agent.worker_config.model}")

            llm_router = get_llm_router()
            response = await llm_router.generate_with_config(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=self.agent.worker_config.model,
                temperature=self.agent.worker_config.temperature,
                max_tokens=self.agent.worker_config.max_tokens,
            )

            print(f"[{datetime.now().isoformat()}] [WORKER] LLM response received for agent {self.agent.id}")

            action = action_parser.parse(
                response=response,
                agent_id=self.agent.id,
                tick_id=tick.tick_id,
            )

            print(f"[{datetime.now().isoformat()}] [WORKER] Action parsed for agent {self.agent.id}: {action.action.value}")

            logger.info(
                "tick_processed",
                agent_id=self.agent.id,
                action=action.action.value,
                model=self.agent.worker_config.model,
                reasoning=action.reasoning[:100] if action.reasoning else "",
            )

            return action

        except Exception as e:
            print(f"[{datetime.now().isoformat()}] [WORKER] ERROR for agent {self.agent.id}: {e}")
            logger.error(
                "tick_processing_failed",
                agent_id=self.agent.id,
                model=self.agent.worker_config.model,
                error=str(e),
            )
            return AgentAction.hold(
                agent_id=self.agent.id,
                tick_id=tick.tick_id,
                reasoning=f"Processing error: {str(e)}",
            )

    async def process_tick_and_submit(self, tick: TickPayload, round_id: str) -> dict:
        print(f"[{datetime.now().isoformat()}] [WORKER] process_tick_and_submit starting for agent {self.agent.id}")
        action = await self.process_tick(tick)

        print(f"[{datetime.now().isoformat()}] [WORKER] Submitting action for agent {self.agent.id}: {action.action.value}")
        result = await cerebellum_client.submit_action(round_id, action)

        print(f"[{datetime.now().isoformat()}] [WORKER] Action submitted successfully for agent {self.agent.id}")
        return {
            "agent_id": self.agent.id,
            "action": action.action.value,
            "result": result,
        }

    @classmethod
    async def from_agent_id(cls, agent_id: str) -> "AgentWorker":
        agent_data = await cerebellum_client.get_agent(agent_id)

        # Merge persona_config with root-level fields that Cortex expects in PersonaConfig
        # These fields are stored as separate columns in Cerebellum but expected in PersonaConfig
        persona_config_data = agent_data.get("persona_config", {}).copy()

        if "trading_style" in agent_data:
            persona_config_data["trading_style"] = agent_data["trading_style"]
        if "leverage" in agent_data:
            persona_config_data["leverage"] = agent_data["leverage"]
        if "stop_loss_percent" in agent_data and agent_data["stop_loss_percent"] is not None:
            persona_config_data["stop_loss_percent"] = agent_data["stop_loss_percent"]
        if "stop_loss_position_close_percent" in agent_data and agent_data["stop_loss_position_close_percent"] is not None:
            persona_config_data["stop_loss_position_close_percent"] = agent_data["stop_loss_position_close_percent"]
        if "take_profit_percent" in agent_data and agent_data["take_profit_percent"] is not None:
            persona_config_data["take_profit_percent"] = agent_data["take_profit_percent"]
        if "take_profit_position_close_percent" in agent_data and agent_data["take_profit_position_close_percent"] is not None:
            persona_config_data["take_profit_position_close_percent"] = agent_data["take_profit_position_close_percent"]

        config = AgentConfig(
            id=agent_data["id"],
            name=agent_data["name"],
            persona_config=PersonaConfig(**persona_config_data),
            worker_config=WorkerConfig(**agent_data.get("worker_config", {})),
        )

        return cls(config)


class AgentWorkerPool:
    def __init__(self):
        self.workers: dict[str, AgentWorker] = {}

    async def add_agent(self, agent_id: str):
        if agent_id not in self.workers:
            worker = await AgentWorker.from_agent_id(agent_id)
            self.workers[agent_id] = worker
            logger.info("agent_added_to_pool", agent_id=agent_id)

    def remove_agent(self, agent_id: str):
        if agent_id in self.workers:
            del self.workers[agent_id]
            logger.info("agent_removed_from_pool", agent_id=agent_id)

    async def process_tick_for_all(self, tick_data: str, round_id: str) -> list[dict]:
        tick = TickPayload.model_validate_json(tick_data)

        logger.info("processing_tick_for_all_agents", agent_count=len(self.workers), tick_number=tick.tick_number)

        tasks = []
        for agent_id, worker in self.workers.items():
            agent_tick = tick.model_copy(update={"portfolio": tick.portfolio})
            task = worker.process_tick_and_submit(agent_tick, round_id)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                agent_id = list(self.workers.keys())[i]
                logger.error("agent_processing_failed", agent_id=agent_id, error=str(result))
                processed_results.append({
                    "agent_id": agent_id,
                    "action": "HOLD",
                    "error": str(result),
                })
            else:
                processed_results.append(result)

        logger.info("completed_tick_for_all_agents", successful=len([r for r in processed_results if "error" not in r]))

        return processed_results

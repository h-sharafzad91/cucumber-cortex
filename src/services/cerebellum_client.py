import httpx
from datetime import datetime

from ..config import settings
from ..schemas import AgentAction
from ..utils import logger


class CerebellumClient:
    def __init__(self):
        self.base_url = settings.cerebellum_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def submit_action(self, round_id: str, action: AgentAction) -> dict:
        url = f"{self.base_url}/v1/arena/{round_id}/action"

        payload = {
            "agent_id": action.agent_id,
            "tick_id": action.tick_id,
            "reasoning": action.reasoning,
            "action": action.action.value,
            "asset": action.asset,
            "size_usd": action.size_usd,
            "size_asset": action.size_asset,
        }

        print(f"[{datetime.now().isoformat()}] [ACTION] Submitting action to {url}")
        print(f"[{datetime.now().isoformat()}] [ACTION] Agent: {action.agent_id}, Action: {action.action.value}, Reasoning: {action.reasoning[:50]}...")

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            print(f"[{datetime.now().isoformat()}] [ACTION] ✓ Response: success={data.get('success')}")
            logger.info(
                "action_submitted",
                round_id=round_id,
                agent_id=action.agent_id,
                action=action.action.value,
                success=data.get("success"),
            )
            return data

        except httpx.HTTPStatusError as e:
            print(f"[{datetime.now().isoformat()}] [ACTION] ERROR: HTTP {e.response.status_code} - {e.response.text}")
            logger.error(
                "action_submission_failed",
                status=e.response.status_code,
                detail=e.response.text,
            )
            raise
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] [ACTION] ERROR: {e}")
            logger.error("action_submission_error", error=str(e))
            raise

    async def get_agent(self, agent_id: str) -> dict:
        url = f"{self.base_url}/v1/agents/{agent_id}"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()["agent"]
        except Exception as e:
            logger.error("get_agent_failed", agent_id=agent_id, error=str(e))
            raise

    async def close(self):
        await self.client.aclose()


cerebellum_client = CerebellumClient()

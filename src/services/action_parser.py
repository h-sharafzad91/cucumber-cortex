import json
import re

from ..schemas import AgentAction, ActionType
from ..utils import logger


class ActionParser:
    def parse(self, response: str, agent_id: str, tick_id: str) -> AgentAction:
        try:
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            action = AgentAction(
                agent_id=agent_id,
                tick_id=tick_id,
                reasoning=data.get("reasoning", "No reasoning provided"),
                action=data.get("action", "HOLD"),
                asset=data.get("asset"),
                size_usd=data.get("size_usd"),
                size_asset=data.get("size_asset"),
                limit_price=data.get("limit_price"),
            )

            if action.action == ActionType.BUY_MARKET:
                if not action.asset or not action.size_usd:
                    logger.warning(
                        "buy_missing_fields",
                        action=action.action,
                        asset=action.asset,
                        size_usd=action.size_usd,
                    )
                    return AgentAction.hold(
                        agent_id=agent_id,
                        tick_id=tick_id,
                        reasoning=f"Invalid BUY: missing asset or size_usd. Original: {data.get('reasoning', '')}",
                    )
            elif action.action == ActionType.SELL_MARKET:
                if not action.asset or not action.size_asset:
                    logger.warning(
                        "sell_missing_fields",
                        action=action.action,
                        asset=action.asset,
                        size_asset=action.size_asset,
                    )
                    return AgentAction.hold(
                        agent_id=agent_id,
                        tick_id=tick_id,
                        reasoning=f"Invalid SELL: missing asset or size_asset. Original: {data.get('reasoning', '')}",
                    )
            elif action.action == ActionType.SHORT_MARKET:
                if not action.asset or not action.size_usd:
                    logger.warning(
                        "short_missing_fields",
                        action=action.action,
                        asset=action.asset,
                        size_usd=action.size_usd,
                    )
                    return AgentAction.hold(
                        agent_id=agent_id,
                        tick_id=tick_id,
                        reasoning=f"Invalid SHORT: missing asset or size_usd. Original: {data.get('reasoning', '')}",
                    )
            elif action.action == ActionType.COVER_MARKET:
                if not action.asset or not action.size_asset:
                    logger.warning(
                        "cover_missing_fields",
                        action=action.action,
                        asset=action.asset,
                        size_asset=action.size_asset,
                    )
                    return AgentAction.hold(
                        agent_id=agent_id,
                        tick_id=tick_id,
                        reasoning=f"Invalid COVER: missing asset or size_asset. Original: {data.get('reasoning', '')}",
                    )

            logger.info(
                "action_parsed",
                agent_id=agent_id,
                action=action.action.value,
                asset=action.asset,
                size_usd=action.size_usd,
                size_asset=action.size_asset,
            )
            return action

        except Exception as e:
            logger.error("action_parse_failed", error=str(e), response=response[:200])
            return AgentAction.hold(
                agent_id=agent_id,
                tick_id=tick_id,
                reasoning=f"Parse error: {str(e)}",
            )

    def _extract_json(self, text: str) -> str:
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)

        match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if match:
            return match.group()

        return text.strip()


action_parser = ActionParser()

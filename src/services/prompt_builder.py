from ..schemas import TickPayload, AgentConfig
from ..schemas.agent_config import TradingStyle, TradingStrategy, RiskTolerance


STRATEGY_BEHAVIORS = {
    TradingStrategy.MOMENTUM: """MOMENTUM STRATEGY:
- BUY when price shows upward momentum (rising trend, positive % change)
- SELL when momentum fades or reverses (trend slowing, negative % change)
- Follow the trend - don't fight it
- Enter on breakouts, exit on trend reversals""",

    TradingStrategy.MEAN_REVERSION: """MEAN REVERSION STRATEGY:
- BUY when price drops significantly below recent average (oversold)
- SELL when price rises significantly above recent average (overbought)
- Wait for extreme moves before trading
- Expect prices to return to the mean""",

    TradingStrategy.BREAKOUT: """BREAKOUT STRATEGY:
- BUY when price breaks above resistance/recent highs
- SELL when price breaks below support/recent lows
- Look for strong volume on breakouts
- Avoid trading in ranging/sideways markets""",

    TradingStrategy.CUSTOM: """CUSTOM STRATEGY:
- Follow your custom trading instructions below
- Use market data to inform your decisions
- Apply your own judgment based on your goal""",
}

TRADING_STYLE_BEHAVIORS = {
    TradingStyle.PAPER_HANDS: """PAPER HANDS STYLE (Quick exits, minimize losses):
- Exit positions quickly at first sign of trouble
- Take small profits rather than holding for bigger gains
- Cut losses immediately, don't wait for recovery
- Prefer many small trades over few large ones
- Trade frequency: HIGH (~60-80% of ticks)""",

    TradingStyle.NORMAL: """NORMAL STYLE (Balanced risk management):
- Hold positions through minor fluctuations
- Use stop-loss and take-profit levels
- Balance between capturing trends and protecting capital
- Trade frequency: MODERATE (~30-50% of ticks)""",

    TradingStyle.DEGEN: """DEGEN STYLE (Hold positions longer, higher risk):
- Hold through volatility, trust your conviction
- Let winners run much longer before taking profit
- Only exit on strong reversal signals
- Accept higher drawdowns for bigger potential gains
- Trade frequency: LOW-MODERATE (~20-40% of ticks)""",
}

RISK_TOLERANCE_BEHAVIORS = {
    RiskTolerance.CONSERVATIVE: """CONSERVATIVE RISK:
- Only trade on very clear, strong signals
- Prioritize capital preservation over gains
- Prefer smaller position sizes
- Wait for high-confidence setups""",

    RiskTolerance.MODERATE: """MODERATE RISK:
- Trade on reasonably clear signals
- Balance growth with protection
- Standard position sizing
- Accept moderate uncertainty""",

    RiskTolerance.AGGRESSIVE: """AGGRESSIVE RISK:
- Act on smaller signals and movements
- Prioritize growth over preservation
- Willing to take larger positions
- Accept higher volatility""",
}


class PromptBuilder:
    def build_system_prompt(self, agent: AgentConfig) -> str:
        persona = agent.persona_config
        goal_section = ""
        if persona.goal:
            goal_section = f"\nYOUR GOAL:\n{persona.goal}\n"

        custom_instructions = ""
        if persona.description:
            custom_instructions = f"\nYOUR CUSTOM INSTRUCTIONS:\n{persona.description}\n"

        strategy_behavior = STRATEGY_BEHAVIORS.get(
            persona.strategy,
            STRATEGY_BEHAVIORS[TradingStrategy.MOMENTUM]
        )

        style_behavior = TRADING_STYLE_BEHAVIORS.get(
            persona.trading_style,
            TRADING_STYLE_BEHAVIORS[TradingStyle.NORMAL]
        )

        risk_behavior = RISK_TOLERANCE_BEHAVIORS.get(
            persona.risk_tolerance,
            RISK_TOLERANCE_BEHAVIORS[RiskTolerance.MODERATE]
        )

        risk_management = f"""RISK MANAGEMENT SETTINGS:
- Leverage: {persona.leverage}x
- Stop-Loss: {persona.stop_loss_percent}% (close {persona.stop_loss_position_close_percent}% of position)
- Take-Profit: {persona.take_profit_percent}% (close {persona.take_profit_position_close_percent}% of position)"""

        return f"""You are {agent.name}, a trading agent in a competitive arena.
{goal_section}
{strategy_behavior}

{style_behavior}

{risk_behavior}
{custom_instructions}
{risk_management}

DECISION GUIDELINES:
- HOLD: When price movement is unclear, you just entered a position, or waiting for better signal
- BUY: When your strategy signals an entry AND you have cash available
- SELL: When your strategy signals an exit AND you have a position

CONSTRAINTS:
1. Never exceed max_usd_order for BUY
2. Only trade allowed_assets
3. For SELL, you must own the asset
4. Output ONLY valid JSON

ACTION FORMATS:

BUY:
{{"reasoning": "...", "action": "BUY_MARKET", "asset": "ETH", "size_usd": 1000}}

SELL:
{{"reasoning": "...", "action": "SELL_MARKET", "asset": "ETH", "size_asset": 0.5}}

HOLD:
{{"reasoning": "...", "action": "HOLD"}}"""

    def build_user_prompt(self, tick: TickPayload) -> str:
        candles_1m = "Awaiting trend"
        if tick.market.candles.get("ETH_USDC"):
            candles = tick.market.candles["ETH_USDC"].m1[-5:]
            if candles:
                prices = [c.close for c in candles]
                trend = "↑" if prices[-1] > prices[0] else "↓" if prices[-1] < prices[0] else "→"
                change_pct = ((prices[-1] - prices[0]) / prices[0]) * 100
                candles_1m = f"{prices[0]:.0f}→{prices[-1]:.0f} ({trend}{change_pct:+.1f}%)"

        print(f"[PROMPT] Candles data: {candles_1m}")

        positions = "None"
        if tick.portfolio.positions:
            pos_list = []
            for p in tick.portfolio.positions:
                entry = p.entry_price if p.entry_price is not None else 0
                pnl = p.unrealized_pnl if p.unrealized_pnl is not None else 0
                pos_list.append(f"{p.asset}:{p.size:.2f}@{entry:.0f}({pnl:+.0f})")
            positions = " | ".join(pos_list) if pos_list else "None"

        user_prompt = f"""Tick#{tick.tick_id or "unknown"} | {tick.timestamp or "unknown"}
ETH: ${tick.market.ETH_USDC.price if tick.market.ETH_USDC.price is not None else 0:.2f} ({tick.market.ETH_USDC.source or "unknown"}) | {candles_1m}
Cash: ${tick.portfolio.balance_usd if tick.portfolio.balance_usd is not None else 0:.2f} | Positions: {positions}
Max order: ${tick.constraints.max_usd_order if tick.constraints.max_usd_order is not None else 0:.2f} | Trade: {", ".join(tick.constraints.allowed_assets) if tick.constraints.allowed_assets else "unknown"}

What's your move? →"""

        print(f"[PROMPT] User prompt:\n{user_prompt}")
        return user_prompt


prompt_builder = PromptBuilder()

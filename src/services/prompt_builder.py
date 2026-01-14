from ..schemas import TickPayload, AgentConfig
from ..schemas.agent_config import TradingStyle, TradingStrategy, RiskTolerance


def get_expected_move_threshold(tick_interval: int | None) -> float:
    """Calculate expected price move % based on tick interval.
    Shorter intervals = smaller expected moves = lower thresholds."""
    tick_sec = tick_interval or 60
    # Rough estimate: ~0.1% per minute on average for ETH
    # Scale: 30s=0.05%, 60s=0.1%, 300s=0.5%, 3600s=1.5%
    base_per_minute = 0.1
    minutes = tick_sec / 60
    return round(base_per_minute * (minutes ** 0.7), 2)  # sub-linear scaling


def get_strategy_behavior(strategy: TradingStrategy, tick_interval: int | None) -> str:
    """Get strategy behavior text dynamically adjusted for any tick interval."""
    tick_sec = tick_interval or 60
    threshold = get_expected_move_threshold(tick_interval)
    half_threshold = round(threshold / 2, 2)

    if strategy == TradingStrategy.MOMENTUM:
        return f"""MOMENTUM STRATEGY (Your tick interval: {tick_sec}s):
- Expected price move per tick: ~{threshold}%
- BUY when price shows upward movement (>{half_threshold}% is a signal for you)
- SELL when you have a position AND price shows downward movement
- At {tick_sec}s intervals, don't wait for "big" moves - {threshold}% IS significant for you
- Follow the trend direction, trade actively!"""

    elif strategy == TradingStrategy.MEAN_REVERSION:
        return f"""MEAN REVERSION STRATEGY (Your tick interval: {tick_sec}s):
- Expected price move per tick: ~{threshold}%
- BUY when price drops (a -{half_threshold}% dip is worth buying at {tick_sec}s intervals)
- SELL when price rises and you have a position
- At {tick_sec}s intervals, a -{threshold}% move is already a "dip" - don't wait longer
- Buy dips, sell rallies - act on the moves you see!"""

    elif strategy == TradingStrategy.BREAKOUT:
        return f"""BREAKOUT STRATEGY (Your tick interval: {tick_sec}s):
- Expected price move per tick: ~{threshold}%
- BUY when price breaks upward (>{half_threshold}% move is a breakout for you)
- SELL when price breaks downward and you have a position
- At {tick_sec}s intervals, any clear directional move is a micro-breakout
- Trade the breakouts you see, don't wait for bigger ones!"""

    else:  # CUSTOM
        return f"""CUSTOM STRATEGY (Your tick interval: {tick_sec}s):
- Expected price move per tick: ~{threshold}%
- Follow your custom trading instructions below
- Adjust your signals for {tick_sec}s timeframe"""

TRADING_STYLE_BEHAVIORS = {
    TradingStyle.PAPER_HANDS: """PAPER HANDS STYLE (Trade frequently, quick in/out):
- YOU SHOULD TRADE OFTEN - aim to trade on 60-80% of ticks!
- Enter positions quickly when you see any signal
- Exit positions quickly - don't wait for perfect exits
- Small profits add up - take them!
- If in doubt, TRADE rather than HOLD""",

    TradingStyle.NORMAL: """NORMAL STYLE (Balanced trading):
- Trade on clear signals - aim for 30-50% of ticks
- Hold positions through minor noise
- Balance between action and patience
- Use your judgment on when to trade""",

    TradingStyle.DEGEN: """DEGEN STYLE (Conviction trading):
- Take positions and HOLD through volatility
- Let winners run - don't exit too early
- Only exit on strong reversal signals
- Trade less frequently but with conviction (20-40% of ticks)
- Big moves require patience""",
}

RISK_TOLERANCE_BEHAVIORS = {
    RiskTolerance.CONSERVATIVE: """CONSERVATIVE RISK:
- Wait for clear signals before trading
- Prioritize capital preservation
- Use smaller position sizes
- It's OK to HOLD more often""",

    RiskTolerance.MODERATE: """MODERATE RISK:
- Trade on reasonably clear signals
- Balance growth with protection
- Standard position sizing""",

    RiskTolerance.AGGRESSIVE: """AGGRESSIVE RISK:
- ACT on even small signals - don't wait for perfect setups!
- Any price movement in your strategy's direction = TRADE
- Prioritize TRADING over waiting
- You have aggressive risk tolerance - USE IT!""",
}


class PromptBuilder:
    def build_system_prompt(self, agent: AgentConfig) -> str:
        persona = agent.persona_config
        print(f"[AGENT CONFIG] {agent.name}: strategy={persona.strategy}, risk={persona.risk_tolerance}, style={persona.trading_style}, tick_interval={agent.tick_interval}s")
        goal_section = ""
        if persona.goal:
            goal_section = f"\nYOUR GOAL:\n{persona.goal}\n"

        custom_instructions = ""
        if persona.description:
            custom_instructions = f"\nYOUR CUSTOM INSTRUCTIONS:\n{persona.description}\n"

        strategy_behavior = get_strategy_behavior(persona.strategy, agent.tick_interval)

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
        price_trend = "Awaiting data"
        price_history = tick.market.ETH_USDC.price_history
        if price_history and len(price_history) >= 2:
            first_price = price_history[0].price
            last_price = price_history[-1].price
            trend = "↑" if last_price > first_price else "↓" if last_price < first_price else "→"
            change_pct = ((last_price - first_price) / first_price) * 100
            price_trend = f"{first_price:.2f}→{last_price:.2f} ({trend}{change_pct:+.3f}%) [{len(price_history)} ticks]"

        print(f"[PROMPT] Price trend: {price_trend}")

        positions = "None"
        if tick.portfolio.positions:
            pos_list = []
            for p in tick.portfolio.positions:
                entry = p.entry_price if p.entry_price is not None else 0
                pnl = p.unrealized_pnl if p.unrealized_pnl is not None else 0
                pos_list.append(f"{p.asset}:{p.size:.2f}@{entry:.0f}({pnl:+.0f})")
            positions = " | ".join(pos_list) if pos_list else "None"

        user_prompt = f"""Tick#{tick.tick_id or "unknown"} | {tick.timestamp or "unknown"}
ETH: ${tick.market.ETH_USDC.price if tick.market.ETH_USDC.price is not None else 0:.2f} ({tick.market.ETH_USDC.source or "unknown"}) | Trend: {price_trend}
Cash: ${tick.portfolio.balance_usd if tick.portfolio.balance_usd is not None else 0:.2f} | Positions: {positions}
Max order: ${tick.constraints.max_usd_order if tick.constraints.max_usd_order is not None else 0:.2f} | Trade: {", ".join(tick.constraints.allowed_assets) if tick.constraints.allowed_assets else "unknown"}

What's your move? →"""

        print(f"[PROMPT] User prompt:\n{user_prompt}")
        return user_prompt


prompt_builder = PromptBuilder()

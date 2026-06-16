"""Background job that checks open paper trades against live prices every 5 minutes.

Closes a trade automatically when price hits its stop loss or take profit.
Sends a Telegram alert on close.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def check_open_positions() -> None:
    """Fetch latest price for each open paper trade and close if SL/TP is hit."""
    from app.market_data.providers import get_provider
    from app.notifications.telegram import paper_trade_closed_alert
    from app.paper_trading.positions import close_position, get_open_positions

    positions = get_open_positions()
    if not positions:
        return

    provider = get_provider()

    for pos in positions:
        market = pos["market"]
        try:
            df = provider.candles(market, "1", n=2)
            if df.empty:
                continue
            latest = df.iloc[-1]
            high = float(latest["high"])
            low = float(latest["low"])

            sl = pos.get("stop_loss")
            tp = pos.get("take_profit")
            direction = pos.get("direction")

            if sl is None or tp is None:
                continue

            close_evt: tuple[float, str] | None = None

            if direction == "long":
                if low <= sl:
                    close_evt = (sl, "stop_loss_hit")
                elif high >= tp:
                    close_evt = (tp, "take_profit_hit")
            else:
                if high >= sl:
                    close_evt = (sl, "stop_loss_hit")
                elif low <= tp:
                    close_evt = (tp, "take_profit_hit")

            if close_evt is not None:
                exit_price, reason = close_evt
                result = close_position(pos["id"], exit_price, reason)
                if result:
                    paper_trade_closed_alert(result)

        except Exception:
            logger.exception("paper monitor | %s check failed", market)

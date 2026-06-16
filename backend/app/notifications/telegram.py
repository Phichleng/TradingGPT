"""Telegram Bot alert sender. Uses the Bot API directly via httpx — no extra library needed.

Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env to enable.
Alerts silently no-op when either value is empty.
"""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


def send_alert(text: str) -> bool:
    """Send a plain/HTML message to the configured Telegram chat. Returns True on success."""
    from app.config import settings
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id
    if not token or not chat_id:
        return False
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        if r.status_code != 200:
            logger.warning("Telegram alert failed: %s", r.text)
        return r.status_code == 200
    except Exception as exc:
        logger.warning("Telegram alert error: %s", exc)
        return False


def trade_signal_alert(report: dict) -> None:
    """Fire a Telegram message only for valid trade signals."""
    verdict = report.get("verdict", "")
    if not verdict.startswith("valid_"):
        return

    market = report.get("market", "?")
    tf = report.get("timeframe", "?")
    direction = "LONG 📈" if "long" in verdict else "SHORT 📉"
    conf = report.get("confidence") or 0
    rr = report.get("risk_reward") or 0
    strategy = report.get("selected_strategy", "?")
    entry = report.get("entry_zone") or [0, 0]
    sl = report.get("stop_loss") or 0
    tp = report.get("take_profit") or 0
    trend = report.get("trend", "?")
    regime = report.get("market_regime", "?")
    reasoning = (report.get("reasoning") or "")[:280]

    text = (
        f"<b>🔔 TRADE SIGNAL — {market}</b>\n"
        f"Timeframe: <b>{tf}m</b>  |  Direction: <b>{direction}</b>\n"
        f"Strategy: <b>{strategy}</b>  |  Confidence: <b>{conf:.0f}%</b>\n"
        f"Risk-Reward: <b>{rr:.1f}R</b>\n"
        f"\n"
        f"Entry zone: <code>{entry[0]:.5f} – {entry[1]:.5f}</code>\n"
        f"Stop loss:  <code>{sl:.5f}</code>\n"
        f"Take profit: <code>{tp:.5f}</code>\n"
        f"\n"
        f"Trend: {trend}  |  Regime: {regime}\n"
    )
    if reasoning:
        text += f"\n<i>{reasoning}</i>"

    send_alert(text)


def paper_trade_closed_alert(trade: dict) -> None:
    """Notify when a paper trade closes (SL or TP hit)."""
    emoji = "✅" if trade.get("outcome") == "win" else "❌"
    market = trade.get("market", "?")
    direction = (trade.get("direction") or "").upper()
    entry = trade.get("entry_price") or 0
    exit_p = trade.get("exit_price") or 0
    pnl = trade.get("pnl_pct") or 0
    reason = trade.get("close_reason", "closed")
    rr = trade.get("planned_rr") or 0

    send_alert(
        f"{emoji} <b>Paper Trade Closed — {market}</b>\n"
        f"Direction: {direction}  |  Reason: {reason}\n"
        f"Entry: <code>{entry:.5f}</code> → Exit: <code>{exit_p:.5f}</code>\n"
        f"P&amp;L: <b>{pnl:+.2f}%</b>  |  Planned RR: {rr:.1f}R"
    )

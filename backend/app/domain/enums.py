"""Canonical enums shared across engines, strategies and reports."""
from enum import Enum


class Trend(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    RANGING = "ranging"


class StructureStatus(str, Enum):
    INTACT = "intact"
    CONTINUATION = "continuation"   # BOS in trend direction
    SHIFTING = "shifting"           # CHOCH / MSS against trend


class Regime(str, Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"


class Volatility(str, Enum):
    HIGH = "high_volatility"
    LOW = "low_volatility"


class Direction(str, Enum):
    LONG = "long"
    SHORT = "short"
    NONE = "none"


class Session(str, Enum):
    ASIAN = "asian"
    LONDON = "london"
    NY_AM = "ny_am"
    NY_PM = "ny_pm"
    OFF = "off"


class StrategyName(str, Enum):
    TREND_FOLLOWING = "trend_following"
    MARKET_STRUCTURE = "market_structure"
    ICT = "ict"
    SMC = "smc"
    CRT = "crt"
    PULLBACK = "pullback"
    BREAKOUT = "breakout"
    LIQUIDITY_SWEEP_REVERSAL = "liquidity_sweep_reversal"
    SESSION_BASED = "session_based"


class DocType(str, Enum):
    STRATEGY = "strategy"
    JOURNAL = "journal"
    BACKTEST = "backtest"
    NOTE = "note"
    SCREENSHOT = "screenshot"

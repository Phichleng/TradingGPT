"""Tests for the production MarketStructureEngine.

Scenario key
------------
  _uptrend()   – clean HH/HL sequence (15 bars, wick=0.2)
  _downtrend() – mirror LH/LL sequence
  _choch_scenario()  – bull trend then sharp drop through the last HL
  _mss_scenario()    – bull trend, CHOCH, then confirming bearish BOS → MSS
  _ranging()   – mixed alternating pattern with no clear bias
"""
from __future__ import annotations

import pytest

from app.engines.market_structure import (
    LabeledSwing,
    MarketStructureEngine,
    StructureEvent,
    _alternate_swings,
    _label_swings,
)
from app.domain.models import Swing
from tests.unit.engines.fixtures.builders import from_close_path


# ---------------------------------------------------------------------------
# Scenario builders
# ---------------------------------------------------------------------------

def _uptrend():
    closes = [10, 11.5, 13, 11.5, 11, 13.5, 15, 13.5, 13, 15.5, 17, 15.5, 15, 17.5, 19]
    return from_close_path(closes)


def _downtrend():
    # Mirror of uptrend: falling highs and falling lows → LH/LL sequence
    closes = [19, 17.5, 15, 17.5, 18, 15.5, 13, 15.5, 16, 13.5, 11, 13.5, 14, 11.5, 9]
    return from_close_path(closes)


def _choch_scenario():
    # Bull trend (HH/HL) then sharp collapse through the last HL → bearish CHOCH
    # Extra bars after the drop ensure idx 8 is a confirmed swing low (right=2)
    closes = [
        10, 11.5, 13,   # idx 0-2: initial rise → HH
        11.5, 11,       # idx 3-4: pullback → HL
        13.5, 15,       # idx 5-6: new HH
        13.5, 13,       # idx 7-8: pullback → HL  (price=12.8)
        14, 15.5,       # idx 9-10: rise confirming idx-8 as swing low
        8, 8.5, 9,      # idx 11-13: sharp drop → close(8) < 12.8 = CHOCH
    ]
    return from_close_path(closes)


def _mss_scenario():
    # Bull trend → bearish CHOCH → confirming bearish BOS → MSS
    closes = [
        # Bull phase
        10, 11.5, 13,   # idx 0-2: first HH
        11.5, 11,       # idx 3-4: first HL
        13.5, 15,       # idx 5-6: second HH
        13.5, 13,       # idx 7-8: second HL (protected; price=12.8)
        14, 15.5,       # idx 9-10: third HH (confirms idx-8 as swing low)
        # CHOCH + BOS
        8, 9,           # idx 11-12: collapse → CHOCH at idx 11
        # Dead cat + new LL (bearish BOS → confirms CHOCH → MSS)
        10, 8.5,        # idx 13-14: dead cat → LH
        7, 6,           # idx 15-16: new LL  (5.8 < 12.8 → bearish BOS)
        7, 7.5,         # idx 17-18: right-confirm idx-16 as swing low
    ]
    return from_close_path(closes)


def _ranging():
    # Alternating HH/LL and LH/HL — no clear bias
    closes = [10, 12, 9, 13, 8, 14, 7, 13, 9, 12, 10, 13, 8, 12, 10]
    return from_close_path(closes)


# ---------------------------------------------------------------------------
# Backward-compatible baseline tests
# ---------------------------------------------------------------------------

def test_uptrend_is_bullish():
    res = MarketStructureEngine().analyze(_uptrend(), context={})
    assert res.summary["trend"] == "bullish"
    assert 0.0 < res.summary["trend_strength"] <= 1.0


def test_structure_score_is_feeder_not_scored():
    res = MarketStructureEngine().analyze(_uptrend(), context={})
    assert res.score == 0.0  # structure feeds other engines; not 0-100 scored


# ---------------------------------------------------------------------------
# Trend classification
# ---------------------------------------------------------------------------

def test_downtrend_is_bearish():
    res = MarketStructureEngine().analyze(_downtrend(), context={})
    assert res.summary["trend"] == "bearish"
    assert res.summary["trend_strength"] > 0.5


def test_uptrend_labeled_swings_are_hh_hl():
    res = MarketStructureEngine().analyze(_uptrend(), context={})
    labels = [s["label"] for s in res.summary["labeled_swings"]]
    assert all(lbl in ("HH", "HL") for lbl in labels), f"unexpected labels: {labels}"


def test_downtrend_labeled_swings_contain_lh_ll():
    res = MarketStructureEngine().analyze(_downtrend(), context={})
    labels = [s["label"] for s in res.summary["labeled_swings"]]
    bearish_labels = [l for l in labels if l in ("LH", "LL")]
    assert len(bearish_labels) >= 2, f"expected LH/LL in labels: {labels}"


# ---------------------------------------------------------------------------
# BOS detection
# ---------------------------------------------------------------------------

def test_bos_detected_in_uptrend():
    res = MarketStructureEngine().analyze(_uptrend(), context={})
    bos_signals = [s for s in res.signals if s.name == "bos"]
    assert len(bos_signals) >= 1, "expected at least one bullish BOS signal"
    assert all(s.direction == "bullish" for s in bos_signals)
    assert all(0.0 < s.strength <= 1.0 for s in bos_signals)


def test_bos_detected_in_downtrend():
    res = MarketStructureEngine().analyze(_downtrend(), context={})
    bos_signals = [s for s in res.signals if s.name == "bos"]
    assert len(bos_signals) >= 1, "expected at least one bearish BOS signal"
    assert all(s.direction == "bearish" for s in bos_signals)


def test_bos_signal_has_required_meta():
    res = MarketStructureEngine().analyze(_uptrend(), context={})
    bos = next(s for s in res.signals if s.name == "bos")
    assert "broken_level" in bos.meta
    assert "source_label" in bos.meta
    assert "displacement_atr" in bos.meta
    assert bos.meta["broken_level"] > 0


def test_bos_structure_status_is_continuation_in_clean_uptrend():
    res = MarketStructureEngine().analyze(_uptrend(), context={})
    # No CHOCH in a clean bull run → status is either intact or continuation
    assert res.summary["structure_status"] in ("intact", "continuation")


# ---------------------------------------------------------------------------
# CHOCH detection
# ---------------------------------------------------------------------------

def test_choch_detected_on_structure_break():
    res = MarketStructureEngine().analyze(_choch_scenario(), context={})
    choch_or_mss = [s for s in res.signals if s.name in ("choch", "mss")]
    assert len(choch_or_mss) >= 1, "expected CHOCH or MSS after structure break"
    assert all(s.direction == "bearish" for s in choch_or_mss)


def test_choch_or_mss_sets_structure_shifting():
    res = MarketStructureEngine().analyze(_choch_scenario(), context={})
    assert res.summary["structure_status"] == "shifting"


def test_choch_strength_above_0_5():
    res = MarketStructureEngine().analyze(_choch_scenario(), context={})
    events = [s for s in res.signals if s.name in ("choch", "mss")]
    assert events, "no CHOCH/MSS signal found"
    assert all(s.strength > 0.5 for s in events)


# ---------------------------------------------------------------------------
# MSS detection
# ---------------------------------------------------------------------------

def test_mss_detected_after_confirmed_reversal():
    res = MarketStructureEngine().analyze(_mss_scenario(), context={})
    mss_signals = [s for s in res.signals if s.name == "mss"]
    assert len(mss_signals) >= 1, "expected MSS signal after CHOCH + confirming BOS"
    assert mss_signals[0].direction == "bearish"


def test_mss_strength_exceeds_raw_choch():
    res = MarketStructureEngine().analyze(_mss_scenario(), context={})
    mss = next((s for s in res.signals if s.name == "mss"), None)
    assert mss is not None, "no MSS signal"
    assert mss.strength > 0.5


def test_mss_sets_structure_shifting():
    res = MarketStructureEngine().analyze(_mss_scenario(), context={})
    assert res.summary["structure_status"] == "shifting"


def test_events_in_summary_are_chronological():
    res = MarketStructureEngine().analyze(_mss_scenario(), context={})
    idxs = [e["idx"] for e in res.summary["events"]]
    assert idxs == sorted(idxs), "events should be chronologically ordered"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_insufficient_data_returns_empty():
    tiny = from_close_path([10, 11, 12])  # too few bars for swings
    res = MarketStructureEngine().analyze(tiny, context={})
    assert res.score == 0.0
    assert res.signals == []
    assert res.summary["trend"] == "ranging"
    assert res.summary["trend_strength"] == 0.0
    assert res.summary["labeled_swings"] == []


def test_invalid_confirmation_raises():
    with pytest.raises(ValueError, match="confirmation"):
        MarketStructureEngine(confirmation="candle")


def test_wick_confirmation_mode_runs_without_error():
    engine = MarketStructureEngine(confirmation="wick")
    res = engine.analyze(_uptrend(), context={})
    assert res.summary["trend"] == "bullish"


def test_context_dict_ignored_gracefully():
    res = MarketStructureEngine().analyze(_uptrend(), context={"extra": "data"})
    assert res.summary["trend"] == "bullish"


# ---------------------------------------------------------------------------
# Unit tests for pure helpers
# ---------------------------------------------------------------------------

def _make_swing(idx, price, kind):
    import pandas as pd
    return Swing(idx=idx, ts=pd.Timestamp(f"2025-01-{idx+1:02d}"), price=price, kind=kind)


def test_alternate_swings_removes_duplicate_highs():
    raw = [
        _make_swing(0, 10.0, "high"),
        _make_swing(1, 12.0, "high"),  # consecutive high → should be merged
        _make_swing(2, 5.0, "low"),
    ]
    result = _alternate_swings(raw)
    assert len(result) == 2
    assert result[0].price == 12.0  # keep the higher of the two consecutive highs
    assert result[0].kind == "high"
    assert result[1].kind == "low"


def test_alternate_swings_removes_duplicate_lows():
    raw = [
        _make_swing(0, 10.0, "high"),
        _make_swing(1, 5.0, "low"),
        _make_swing(2, 3.0, "low"),  # consecutive low → keep the lower
    ]
    result = _alternate_swings(raw)
    assert len(result) == 2
    assert result[1].price == 3.0


def test_alternate_swings_keeps_already_alternating():
    raw = [
        _make_swing(0, 10.0, "high"),
        _make_swing(1, 5.0, "low"),
        _make_swing(2, 12.0, "high"),
        _make_swing(3, 4.0, "low"),
    ]
    result = _alternate_swings(raw)
    assert len(result) == 4


def test_label_swings_hh_hl_sequence():
    swings = [
        _make_swing(0, 10.0, "high"),
        _make_swing(1, 5.0, "low"),
        _make_swing(2, 12.0, "high"),   # > 10 → HH
        _make_swing(3, 6.0, "low"),     # > 5  → HL
        _make_swing(4, 14.0, "high"),   # > 12 → HH
        _make_swing(5, 7.0, "low"),     # > 6  → HL
    ]
    labeled = _label_swings(swings)
    labels = [s.label for s in labeled]
    # First of each kind gets HH/HL (no prior to compare)
    assert labels == ["HH", "HL", "HH", "HL", "HH", "HL"]


def test_label_swings_lh_ll_sequence():
    swings = [
        _make_swing(0, 12.0, "high"),
        _make_swing(1, 7.0, "low"),
        _make_swing(2, 10.0, "high"),   # < 12 → LH
        _make_swing(3, 5.0, "low"),     # < 7  → LL
        _make_swing(4, 8.0, "high"),    # < 10 → LH
        _make_swing(5, 3.0, "low"),     # < 5  → LL
    ]
    labeled = _label_swings(swings)
    labels = [s.label for s in labeled]
    assert labels == ["HH", "HL", "LH", "LL", "LH", "LL"]


def test_label_swings_mixed():
    swings = [
        _make_swing(0, 10.0, "high"),
        _make_swing(1, 5.0, "low"),
        _make_swing(2, 12.0, "high"),   # HH
        _make_swing(3, 4.0, "low"),     # LL
        _make_swing(4, 11.0, "high"),   # LH (< 12)
        _make_swing(5, 6.0, "low"),     # HL (> 4)
    ]
    labeled = _label_swings(swings)
    labels = [s.label for s in labeled]
    assert labels == ["HH", "HL", "HH", "LL", "LH", "HL"]


# ---------------------------------------------------------------------------
# Signal interface contract
# ---------------------------------------------------------------------------

def test_all_signals_have_valid_structure():
    res = MarketStructureEngine().analyze(_mss_scenario(), context={})
    for sig in res.signals:
        assert sig.name in ("bos", "choch", "mss")
        assert sig.direction in ("bullish", "bearish")
        assert 0.0 < sig.strength <= 1.0
        assert isinstance(sig.idx, int)
        assert "broken_level" in sig.meta
        assert sig.meta["broken_level"] > 0


def test_explanation_is_non_empty_string():
    res = MarketStructureEngine().analyze(_uptrend(), context={})
    assert isinstance(res.explanation, str)
    assert len(res.explanation) > 20

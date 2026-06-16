from app.domain.models import StrategyProposal
from app.risk.risk_engine import RiskConfig, RiskEngine


def _prop(entry, sl, tp, direction="long"):
    return StrategyProposal(direction, (entry, entry), sl, tp, "test")


def test_rejects_low_rr():
    eng = RiskEngine(RiskConfig(min_rr=2.0))
    d = eng.evaluate(_prop(100, 99, 100.5), balance=10000)  # RR 0.5
    assert not d.passed and any("RR" in r for r in d.reasons)


def test_passes_good_rr_and_sizes_position():
    eng = RiskEngine(RiskConfig(min_rr=2.0, risk_per_trade=0.01))
    d = eng.evaluate(_prop(100, 99, 103), balance=10000)  # RR 3, risk_dist 1
    assert d.passed and d.rr == 3.0
    assert d.position_size == 100.0  # 0.01 * 10000 / 1


def test_rejects_when_no_proposal():
    d = RiskEngine().evaluate(None, balance=10000)
    assert not d.passed


def test_daily_loss_limit_blocks():
    eng = RiskEngine(RiskConfig(daily_loss_limit=0.03))
    d = eng.evaluate(_prop(100, 99, 103), balance=10000, realized_today_pct=-0.04)
    assert not d.passed and any("daily" in r for r in d.reasons)

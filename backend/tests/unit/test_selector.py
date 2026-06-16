from app.engines.ict import ICTEngine
from app.engines.smc import SMCEngine
from app.engines.crt import CRTEngine
from app.selection.selector import StrategySelector
from app.strategies.registry import load_all
from tests.unit.engines.fixtures.builders import make_candles

load_all()


def test_selector_returns_bounded_confidence():
    df = make_candles([(10, 11, 9, 10)] * 40)
    ctx = {"htf_bias": "bullish", "structure_status": "continuation"}
    engines = {"ict": ICTEngine().analyze(df, context=ctx),
               "smc": SMCEngine().analyze(df, context=ctx),
               "crt": CRTEngine().analyze(df, context=ctx)}
    sel = StrategySelector().select(
        engines=engines, regime={"regime": "trending", "volatility": "low_volatility"},
        structure={"trend": "bullish", "structure_status": "continuation",
                   "trend_strength": 0.8}, df=df)
    assert 0.0 <= sel["confidence"] <= 100.0
    assert sel["selected"] in sel["scores"]
    assert set(sel["scores"]) >= {"ict", "smc", "crt", "trend_following"}

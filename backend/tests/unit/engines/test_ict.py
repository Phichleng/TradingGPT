from app.engines.ict import ICTEngine, find_fvg
from tests.unit.engines.fixtures.builders import make_candles


def test_bullish_fvg_detected():
    # candle2.low (11) > candle0.high (10)  -> bullish FVG
    df = make_candles([(10, 10, 9, 10), (10, 18, 10, 17), (17, 20, 11, 19)])
    zones = find_fvg(df)
    assert any(z.kind == "fvg" and z.direction == "bullish" for z in zones)


def test_ict_score_bounded():
    df = make_candles([(10, 11, 9, 10)] * 30)
    res = ICTEngine().analyze(df, context={"htf_bias": "bullish"})
    assert 0.0 <= res.score <= 100.0
    assert "components" in res.summary

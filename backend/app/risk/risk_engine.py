from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import StrategyProposal


@dataclass
class RiskDecision:
    passed: bool
    reasons: list[str]
    position_size: float | None
    rr: float | None


@dataclass
class RiskConfig:
    risk_per_trade: float = 0.01
    min_rr: float = 2.0
    daily_loss_limit: float = 0.03
    weekly_loss_limit: float = 0.06


class RiskEngine:
    """Non-bypassable gate. Runs after a proposal exists, before the LLM."""

    def __init__(self, cfg: RiskConfig | None = None):
        self.cfg = cfg or RiskConfig()

    def evaluate(self, proposal: StrategyProposal | None, *, balance: float,
                 realized_today_pct: float = 0.0,
                 realized_week_pct: float = 0.0) -> RiskDecision:
        if proposal is None or proposal.direction == "none":
            return RiskDecision(False, ["no valid setup proposed"], None, None)

        entry = proposal.entry_mid
        risk_dist = abs(entry - proposal.stop_loss)
        reward_dist = abs(proposal.take_profit - entry)
        rr = (reward_dist / risk_dist) if risk_dist else 0.0

        reasons: list[str] = []
        if risk_dist == 0:
            reasons.append("invalid stop (zero distance)")
        if rr < self.cfg.min_rr:
            reasons.append(f"RR {rr:.2f} < minimum {self.cfg.min_rr}")
        if realized_today_pct <= -self.cfg.daily_loss_limit:
            reasons.append(f"daily loss limit {self.cfg.daily_loss_limit:.0%} reached")
        if realized_week_pct <= -self.cfg.weekly_loss_limit:
            reasons.append(f"weekly loss limit {self.cfg.weekly_loss_limit:.0%} reached")

        size = (self.cfg.risk_per_trade * balance / risk_dist) if risk_dist else None
        return RiskDecision(
            passed=not reasons,
            reasons=reasons or ["all risk checks passed"],
            position_size=round(size, 4) if size else None,
            rr=round(rr, 2),
        )

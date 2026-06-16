from __future__ import annotations

import hashlib
import hmac


def verify_secret(provided: str, expected: str) -> bool:
    return hmac.compare_digest(provided or "", expected or "")


def idempotency_key(market: str, timeframe: str, nonce: str) -> str:
    return hashlib.sha256(f"{market}|{timeframe}|{nonce}".encode()).hexdigest()

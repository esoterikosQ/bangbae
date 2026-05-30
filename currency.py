"""
외화 → 원화 환율 변환 모듈

open.er-api.com (무료, 키 불필요)을 사용하여 실시간 환율 조회.
동일 통화에 대한 반복 조회를 줄이기 위해 메모리 캐시 사용.
"""

import logging
import httpx

logger = logging.getLogger(__name__)

_rate_cache: dict[str, float] = {}


async def to_krw(amount: float, currency: str) -> int | None:
    """외화 금액을 원화로 변환. 실패 시 None 반환."""
    currency = currency.upper()
    if currency == "KRW":
        return int(amount)

    if currency in _rate_cache:
        rate = _rate_cache[currency]
        return int(amount * rate)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://open.er-api.com/v6/latest/{currency}"
            )
            data = resp.json()
            if data.get("result") == "success" and "KRW" in data.get("rates", {}):
                rate = data["rates"]["KRW"]
                _rate_cache[currency] = rate
                logger.info(f"환율 조회: 1 {currency} = {rate:.2f} KRW")
                return int(amount * rate)
    except Exception as e:
        logger.error(f"환율 조회 실패 ({currency}): {e}")

    return None

"""
MacroDroid 푸시 알림 수신 엔드포인트

MacroDroid HTTP 요청:
  POST /treasury/api/webhook/push
  Header: X-API-Key: <WEBHOOK_API_KEY>
  Body: 푸시 텍스트 (JSON, form, plain text 모두 수용)
"""

import os
import logging

from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel

from api.database import get_pool
from parsers import parse_expense
from currency import to_krw

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["웹훅"])

WEBHOOK_API_KEY = os.getenv("WEBHOOK_API_KEY", "")

# 거래 등록 제외 카드번호 뒷자리 (bot.py와 동일)
SKIP_CARDS = {"2363"}


class PushResponse(BaseModel):
    status: str
    parsed: bool
    payment_method: str | None = None
    merchant: str | None = None
    amount: int | None = None
    message: str = ""


@router.post("/push", response_model=PushResponse)
async def receive_push(
    request: Request,
    key: str = None,
    x_api_key: str = Header(None),
):
    """MacroDroid에서 카드사 푸시 알림을 수신"""
    # 인증 — 헤더 또는 URL 파라미터
    api_key = x_api_key or key
    if not WEBHOOK_API_KEY:
        raise HTTPException(500, "WEBHOOK_API_KEY가 설정되지 않았습니다")
    if api_key != WEBHOOK_API_KEY:
        raise HTTPException(401, "유효하지 않은 API 키입니다")

    # JSON, form, plain text 모두 수용
    content_type = request.headers.get("content-type", "")
    text = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            text = body.get("text", "")
        except Exception:
            pass

    if not text and "form" in content_type:
        try:
            form = await request.form()
            text = form.get("text", "")
        except Exception:
            pass

    if not text:
        raw = await request.body()
        text = raw.decode("utf-8", errors="ignore")

    if not text or not text.strip():
        raise HTTPException(400, "텍스트가 비어있습니다")

    pool = await get_pool()

    # 1. 원본 메시지 저장
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO raw_messages (raw_text, source)
            VALUES ($1, 'macrodroid')
            RETURNING id
            """,
            text,
        )
        raw_id = row["id"]

    # 2. 파싱 시도
    result = parse_expense(text)

    if result and (result.amount or result.foreign_currency):
        # 제외 대상 카드 확인
        if any(s in (result.payment_method or "") for s in SKIP_CARDS):
            return PushResponse(
                status="skipped",
                parsed=True,
                payment_method=result.payment_method,
                message="등록 제외 카드",
            )

        # 외화 → 원화 변환
        if result.foreign_currency and result.amount is None:
            krw = await to_krw(abs(result.foreign_amount), result.foreign_currency)
            if krw is not None:
                result.amount = krw if result.foreign_amount >= 0 else -krw
            else:
                return PushResponse(
                    status="saved",
                    parsed=False,
                    message=f"환율 조회 실패 ({result.foreign_currency} {result.foreign_amount})",
                )

        # 거래 저장
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO transactions
                    (raw_message_id, payment_method, transacted_at, merchant, amount)
                VALUES ($1, $2, $3, $4, $5)
                """,
                raw_id,
                result.payment_method,
                result.transacted_at,
                result.merchant,
                result.amount,
            )
            await conn.execute(
                "UPDATE raw_messages SET is_parsed = TRUE WHERE id = $1",
                raw_id,
            )

        logger.info(f"웹훅 거래 저장: {result.payment_method} {result.amount}원 {result.merchant}")

        return PushResponse(
            status="saved",
            parsed=True,
            payment_method=result.payment_method,
            merchant=result.merchant,
            amount=result.amount,
            message="기록 완료",
        )
    else:
        return PushResponse(
            status="saved",
            parsed=False,
            message="자동 파싱 실패 — 원본만 저장됨",
        )
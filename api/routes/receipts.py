from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from api.auth import verify_token
from api.database import get_pool
from api.ocr import process_receipt

router = APIRouter(prefix="/receipts", tags=["영수증"])


class ReceiptItemOut(BaseModel):
    id: int
    transaction_id: int
    item_name: str
    unit_price: int | None = None
    quantity: int = 1
    item_total: int | None = None
    category_id: int | None = None


class ReceiptScanResult(BaseModel):
    raw_text: str
    merchant: str | None = None
    transacted_at: str | None = None
    items: list[dict] = []
    subtotal: int | None = None
    discounts: list[dict] = []
    total: int | None = None
    paid: int | None = None
    payment_method: str | None = None


class ReceiptConfirm(BaseModel):
    transaction_id: int
    items: list[dict]          # [{item_name, unit_price, quantity, item_total}]
    discounts: list[dict] = [] # [{description, amount}]


# ── 영수증 스캔 (OCR + LLM) ──

@router.post("/scan", response_model=ReceiptScanResult)
async def scan_receipt(
    file: UploadFile = File(...),
    _user: str = Depends(verify_token),
):
    """영수증 이미지를 업로드하면 OCR + LLM으로 구조화하여 반환"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "이미지 파일만 업로드 가능합니다")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(400, "파일 크기는 10MB 이하여야 합니다")

    result = await process_receipt(image_bytes)

    return ReceiptScanResult(
        raw_text=result.raw_text,
        merchant=result.merchant,
        transacted_at=result.transacted_at,
        items=result.items or [],
        subtotal=result.subtotal,
        discounts=result.discounts or [],
        total=result.total,
        paid=result.paid,
        payment_method=result.payment_method,
    )


# ── 스캔 결과를 거래에 연결 ──

@router.post("/confirm", response_model=list[ReceiptItemOut])
async def confirm_receipt(
    body: ReceiptConfirm,
    _user: str = Depends(verify_token),
):
    """스캔 결과를 확인 후 거래에 품목/할인 내역을 연결"""
    pool = await get_pool()

    async with pool.acquire() as conn:
        # 거래 존재 확인
        tx = await conn.fetchrow(
            "SELECT id FROM transactions WHERE id = $1",
            body.transaction_id,
        )
        if not tx:
            raise HTTPException(404, "거래를 찾을 수 없습니다")

        # 기존 품목 삭제 (재스캔 시)
        await conn.execute(
            "DELETE FROM receipt_items WHERE transaction_id = $1",
            body.transaction_id,
        )
        await conn.execute(
            "DELETE FROM receipt_adjustments WHERE transaction_id = $1",
            body.transaction_id,
        )

        # 품목 저장
        saved_items = []
        for i, item in enumerate(body.items):
            row = await conn.fetchrow(
                """
                INSERT INTO receipt_items
                    (transaction_id, item_name, unit_price, quantity, item_total, sort_order)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
                """,
                body.transaction_id,
                item.get("item_name", ""),
                item.get("unit_price"),
                item.get("quantity", 1),
                item.get("item_total"),
                i,
            )
            saved_items.append(dict(row))

        # 할인 내역 저장
        for disc in body.discounts:
            await conn.execute(
                """
                INSERT INTO receipt_adjustments
                    (transaction_id, adj_type, description, amount)
                VALUES ($1, 'discount', $2, $3)
                """,
                body.transaction_id,
                disc.get("description", ""),
                disc.get("amount", 0),
            )

        # 거래에 영수증 플래그 설정
        await conn.execute(
            "UPDATE transactions SET has_receipt = TRUE, updated_at = NOW() WHERE id = $1",
            body.transaction_id,
        )

    return saved_items


# ── 거래의 영수증 품목 조회 ──

@router.get("/{transaction_id}", response_model=list[ReceiptItemOut])
async def get_receipt_items(
    transaction_id: int,
    _user: str = Depends(verify_token),
):
    """거래에 연결된 영수증 품목 목록"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM receipt_items
            WHERE transaction_id = $1
            ORDER BY sort_order
            """,
            transaction_id,
        )
    return [dict(r) for r in rows]

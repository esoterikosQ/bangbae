from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth import verify_token
from api.database import get_pool

router = APIRouter(prefix="/transactions", tags=["거래"])


class TransactionOut(BaseModel):
    id: int
    raw_message_id: int | None = None
    payment_method: str | None = None
    transacted_at: datetime | None = None
    merchant: str | None = None
    amount: int
    category_id: int | None = None
    category_name: str | None = None
    memo: str | None = None
    has_receipt: bool = False
    created_at: datetime | None = None


class TransactionUpdate(BaseModel):
    payment_method: str | None = None
    transacted_at: datetime | None = None
    merchant: str | None = None
    amount: int | None = None
    category_id: int | None = None
    memo: str | None = None


class TransactionCreate(BaseModel):
    payment_method: str | None = None
    transacted_at: datetime
    merchant: str | None = None
    amount: int
    category_id: int | None = None
    memo: str | None = None


class MonthlySummary(BaseModel):
    total_amount: int
    transaction_count: int
    by_category: list[dict]
    by_payment_method: list[dict]


@router.get("", response_model=list[TransactionOut])
async def list_transactions(
    year: int = Query(...),
    month: int = Query(...),
    category_id: int | None = None,
    _user: str = Depends(verify_token),
):
    """월별 거래 목록 조회"""
    pool = await get_pool()
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year + (month // 12), month % 12 + 1, 1, tzinfo=timezone.utc)

    query = """
        SELECT t.*, c.name AS category_name
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.transacted_at >= $1 AND t.transacted_at < $2
    """
    params: list = [start, end]

    if category_id is not None:
        query += " AND t.category_id = $3"
        params.append(category_id)

    query += " ORDER BY t.transacted_at DESC"

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    return [dict(r) for r in rows]


@router.get("/summary", response_model=MonthlySummary)
async def monthly_summary(
    year: int = Query(...),
    month: int = Query(...),
    _user: str = Depends(verify_token),
):
    """월별 지출 요약 (분류별, 결제수단별)"""
    pool = await get_pool()
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year + (month // 12), month % 12 + 1, 1, tzinfo=timezone.utc)

    async with pool.acquire() as conn:
        totals = await conn.fetchrow(
            """
            SELECT COUNT(*) AS cnt, COALESCE(SUM(amount), 0) AS total
            FROM transactions
            WHERE transacted_at >= $1 AND transacted_at < $2
            """,
            start, end,
        )

        by_cat = await conn.fetch(
            """
            SELECT c.name AS category, COALESCE(SUM(t.amount), 0) AS total,
                   COUNT(*) AS count
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.transacted_at >= $1 AND t.transacted_at < $2
            GROUP BY c.name
            ORDER BY total DESC
            """,
            start, end,
        )

        by_pm = await conn.fetch(
            """
            SELECT payment_method, COALESCE(SUM(amount), 0) AS total,
                   COUNT(*) AS count
            FROM transactions
            WHERE transacted_at >= $1 AND transacted_at < $2
            GROUP BY payment_method
            ORDER BY total DESC
            """,
            start, end,
        )

    return MonthlySummary(
        total_amount=totals["total"],
        transaction_count=totals["cnt"],
        by_category=[dict(r) for r in by_cat],
        by_payment_method=[dict(r) for r in by_pm],
    )


@router.get("/{tx_id}", response_model=TransactionOut)
async def get_transaction(tx_id: int, _user: str = Depends(verify_token)):
    """거래 상세 조회"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT t.*, c.name AS category_name
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.id = $1
            """,
            tx_id,
        )
    if not row:
        raise HTTPException(404, "거래를 찾을 수 없습니다")
    return dict(row)


@router.put("/{tx_id}", response_model=TransactionOut)
async def update_transaction(
    tx_id: int,
    body: TransactionUpdate,
    _user: str = Depends(verify_token),
):
    """거래 수정 (분류, 메모, 거래처 등)"""
    pool = await get_pool()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "수정할 내용이 없습니다")

    set_clauses = []
    params = []
    for i, (key, val) in enumerate(updates.items(), start=1):
        set_clauses.append(f"{key} = ${i}")
        params.append(val)

    set_clauses.append(f"updated_at = ${len(params) + 1}")
    params.append(datetime.now(timezone.utc))
    params.append(tx_id)

    query = f"""
        UPDATE transactions
        SET {', '.join(set_clauses)}
        WHERE id = ${len(params)}
        RETURNING *
    """

    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *params)

    if not row:
        raise HTTPException(404, "거래를 찾을 수 없습니다")
    return dict(row)


@router.post("", response_model=TransactionOut, status_code=201)
async def create_transaction(
    body: TransactionCreate,
    _user: str = Depends(verify_token),
):
    """수동 거래 등록 (현금 등 카드 외 결제)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO transactions
                (payment_method, transacted_at, merchant, amount, category_id, memo)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            body.payment_method,
            body.transacted_at,
            body.merchant,
            body.amount,
            body.category_id,
            body.memo,
        )
    return dict(row)


@router.delete("/{tx_id}", status_code=204)
async def delete_transaction(tx_id: int, _user: str = Depends(verify_token)):
    """거래 삭제"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM transactions WHERE id = $1", tx_id
        )
    if result == "DELETE 0":
        raise HTTPException(404, "거래를 찾을 수 없습니다")

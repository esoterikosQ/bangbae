from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth import verify_token
from api.database import get_pool

router = APIRouter(prefix="/budgets", tags=["예산"])


class BudgetOut(BaseModel):
    id: int
    year_month: str
    category_id: int | None = None
    category_name: str | None = None
    budget_amount: int
    is_income: bool = False


class BudgetCreate(BaseModel):
    year_month: str          # '2026-05'
    category_id: int | None = None
    budget_amount: int
    is_income: bool = False


class BudgetUpdate(BaseModel):
    budget_amount: int | None = None
    is_income: bool | None = None


class BudgetVsActual(BaseModel):
    category: str | None
    category_id: int | None
    budget: int
    actual: int
    diff: int
    is_income: bool


@router.get("", response_model=list[BudgetOut])
async def list_budgets(
    year_month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    _user: str = Depends(verify_token),
):
    """월별 예산 목록"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT b.*, c.name AS category_name
            FROM budgets b
            LEFT JOIN categories c ON b.category_id = c.id
            WHERE b.year_month = $1
            ORDER BY b.is_income DESC, c.name
            """,
            year_month,
        )
    return [dict(r) for r in rows]


@router.get("/compare", response_model=list[BudgetVsActual])
async def budget_vs_actual(
    year_month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    _user: str = Depends(verify_token),
):
    """예산 대비 실적 비교"""
    pool = await get_pool()
    year, month = map(int, year_month.split("-"))
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year + (month // 12), month % 12 + 1, 1, tzinfo=timezone.utc)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                b.category_id,
                c.name AS category,
                b.budget_amount AS budget,
                b.is_income,
                COALESCE(SUM(t.amount), 0) AS actual
            FROM budgets b
            LEFT JOIN categories c ON b.category_id = c.id
            LEFT JOIN transactions t
                ON t.category_id = b.category_id
                AND t.transacted_at >= $1 AND t.transacted_at < $2
            WHERE b.year_month = $3
            GROUP BY b.id, b.category_id, c.name, b.budget_amount, b.is_income
            ORDER BY b.is_income DESC, c.name
            """,
            start, end, year_month,
        )

    result = []
    for r in rows:
        budget = r["budget"]
        actual = r["actual"]
        result.append(BudgetVsActual(
            category=r["category"],
            category_id=r["category_id"],
            budget=budget,
            actual=actual,
            diff=actual - budget,
            is_income=r["is_income"],
        ))
    return result


@router.post("", response_model=BudgetOut, status_code=201)
async def create_budget(
    body: BudgetCreate, _user: str = Depends(verify_token)
):
    """예산 등록 (UPSERT)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO budgets (year_month, category_id, budget_amount, is_income)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (year_month, category_id)
            DO UPDATE SET budget_amount = $3, is_income = $4,
                          updated_at = NOW()
            RETURNING *
            """,
            body.year_month,
            body.category_id,
            body.budget_amount,
            body.is_income,
        )
    return dict(row)


@router.put("/{budget_id}", response_model=BudgetOut)
async def update_budget(
    budget_id: int, body: BudgetUpdate, _user: str = Depends(verify_token)
):
    """예산 수정"""
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
    params.append(budget_id)

    query = f"""
        UPDATE budgets SET {', '.join(set_clauses)}
        WHERE id = ${len(params)} RETURNING *
    """

    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *params)
    if not row:
        raise HTTPException(404, "예산을 찾을 수 없습니다")
    return dict(row)


@router.delete("/{budget_id}", status_code=204)
async def delete_budget(budget_id: int, _user: str = Depends(verify_token)):
    """예산 삭제"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM budgets WHERE id = $1", budget_id
        )
    if result == "DELETE 0":
        raise HTTPException(404, "예산을 찾을 수 없습니다")

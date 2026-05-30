from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import verify_token
from api.database import get_pool

router = APIRouter(prefix="/categories", tags=["분류"])


class CategoryOut(BaseModel):
    id: int
    name: str
    parent_id: int | None = None
    icon: str | None = None
    sort_order: int = 0


class CategoryCreate(BaseModel):
    name: str
    parent_id: int | None = None
    icon: str | None = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = None
    parent_id: int | None = None
    icon: str | None = None
    sort_order: int | None = None


@router.get("", response_model=list[CategoryOut])
async def list_categories(_user: str = Depends(verify_token)):
    """전체 분류 목록"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM categories ORDER BY sort_order, name"
        )
    return [dict(r) for r in rows]


@router.post("", response_model=CategoryOut, status_code=201)
async def create_category(
    body: CategoryCreate, _user: str = Depends(verify_token)
):
    """분류 생성"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO categories (name, parent_id, icon, sort_order)
            VALUES ($1, $2, $3, $4)
            RETURNING *
            """,
            body.name, body.parent_id, body.icon, body.sort_order,
        )
    return dict(row)


@router.put("/{cat_id}", response_model=CategoryOut)
async def update_category(
    cat_id: int, body: CategoryUpdate, _user: str = Depends(verify_token)
):
    """분류 수정"""
    pool = await get_pool()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "수정할 내용이 없습니다")

    set_clauses = []
    params = []
    for i, (key, val) in enumerate(updates.items(), start=1):
        set_clauses.append(f"{key} = ${i}")
        params.append(val)
    params.append(cat_id)

    query = f"""
        UPDATE categories SET {', '.join(set_clauses)}
        WHERE id = ${len(params)} RETURNING *
    """

    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *params)
    if not row:
        raise HTTPException(404, "분류를 찾을 수 없습니다")
    return dict(row)


@router.delete("/{cat_id}", status_code=204)
async def delete_category(cat_id: int, _user: str = Depends(verify_token)):
    """분류 삭제"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM categories WHERE id = $1", cat_id
        )
    if result == "DELETE 0":
        raise HTTPException(404, "분류를 찾을 수 없습니다")

import logging
from datetime import datetime, timezone

import asyncpg

from config import config

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            min_size=2,
            max_size=10,
        )
        logger.info("DB 연결 풀 생성 완료")
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("DB 연결 풀 종료")


async def save_raw_message(
    telegram_message_id: int,
    raw_text: str,
    source: str = "telegram",
) -> int:
    """원본 메시지를 저장하고 raw_messages.id를 반환"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # 중복 체크 (같은 telegram_message_id)
        existing = await conn.fetchrow(
            "SELECT id FROM raw_messages WHERE telegram_message_id = $1",
            telegram_message_id,
        )
        if existing:
            logger.debug(f"중복 메시지 무시: message_id={telegram_message_id}")
            return existing["id"]

        row = await conn.fetchrow(
            """
            INSERT INTO raw_messages (telegram_message_id, raw_text, source)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            telegram_message_id,
            raw_text,
            source,
        )
        logger.info(f"원본 메시지 저장: id={row['id']}")
        return row["id"]


async def save_transaction(
    raw_message_id: int,
    payment_method: str | None,
    transacted_at: datetime | None,
    merchant: str | None,
    amount: int,
) -> int:
    """파싱된 거래 내역을 저장하고 transactions.id를 반환"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO transactions
                (raw_message_id, payment_method, transacted_at, merchant, amount)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            raw_message_id,
            payment_method,
            transacted_at,
            merchant,
            amount,
        )
        # raw_messages의 is_parsed를 갱신
        await conn.execute(
            "UPDATE raw_messages SET is_parsed = TRUE WHERE id = $1",
            raw_message_id,
        )
        logger.info(f"거래 저장: id={row['id']}, amount={amount}")
        return row["id"]

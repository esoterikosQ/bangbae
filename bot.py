"""
지출 관리 텔레그램 봇

기능:
- 카드사 푸시 알림 텍스트를 수신하여 DB에 저장
- 카드사별 파서로 자동 파싱 시도
- 파싱 실패 시 원본만 저장 (수동 파싱 대기)
- 외화 결제 시 실시간 환율로 원화 변환
- /status, /recent 등 기본 조회 명령
"""

import asyncio
import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import config
from db import (
    save_raw_message,
    save_transaction,
    get_pool,
    close_pool,
)
from parsers import parse_expense
from currency import to_krw

# 로깅 설정
logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=getattr(logging, config.LOG_LEVEL),
)
logger = logging.getLogger(__name__)

# 거래 등록 제외 카드번호 뒷자리
SKIP_CARDS = {"2363"}


# ──────────────────────────────────────────────
# 접근 제어
# ──────────────────────────────────────────────

def is_authorized(user_id: int) -> bool:
    """허용된 사용자인지 확인. ALLOWED_TELEGRAM_IDS가 비어있으면 모두 허용."""
    if not config.ALLOWED_TELEGRAM_IDS:
        return True
    return user_id in config.ALLOWED_TELEGRAM_IDS


# ──────────────────────────────────────────────
# 명령 핸들러
# ──────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """봇 시작 메시지"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("⛔ 접근 권한이 없습니다.")
        return

    await update.message.reply_text(
        "안녕하세요!\n\n"
        "카드 결제 푸시 알림을 이 채팅으로 전달해주세요.\n"
        "자동으로 파싱해서 기록합니다.\n\n"
        "명령어:\n"
        "/recent — 최근 거래 5건 조회\n"
        "/status — 이번 달 지출 현황\n"
        "/myid — 내 Telegram ID 확인"
    )


async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Telegram user ID 확인 (ALLOWED_TELEGRAM_IDS 설정용)"""
    await update.message.reply_text(
        f"👤 Telegram ID: `{update.effective_user.id}`",
        parse_mode="Markdown",
    )


async def cmd_recent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """최근 거래 5건 조회"""
    if not is_authorized(update.effective_user.id):
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT payment_method, transacted_at, merchant, amount
            FROM transactions
            ORDER BY transacted_at DESC
            LIMIT 5
            """
        )

    if not rows:
        await update.message.reply_text("📭 기록된 거래가 없습니다.")
        return

    lines = ["📋 *최근 거래 5건*\n"]
    for r in rows:
        dt = r["transacted_at"]
        date_str = dt.strftime("%m/%d %H:%M") if dt else "날짜 미상"
        method = r["payment_method"] or "미분류"
        merchant = r["merchant"] or "미상"
        amount = f"{r['amount']:,}원"
        lines.append(f"• {date_str}  {method}\n  {merchant}  *{amount}*")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """이번 달 지출 현황"""
    if not is_authorized(update.effective_user.id):
        return

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                COUNT(*) AS cnt,
                COALESCE(SUM(amount), 0) AS total
            FROM transactions
            WHERE transacted_at >= $1
            """,
            month_start,
        )

        unparsed = await conn.fetchval(
            "SELECT COUNT(*) FROM raw_messages WHERE is_parsed = FALSE"
        )

    cnt = row["cnt"]
    total = row["total"]

    text = (
        f"📊 *{now.strftime('%Y년 %m월')} 현황*\n\n"
        f"거래 건수: {cnt}건\n"
        f"총 지출: {total:,}원\n"
        f"미파싱 메시지: {unparsed}건"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ──────────────────────────────────────────────
# 메시지 핸들러 (핵심: 푸시 알림 수신 및 파싱)
# ──────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """일반 텍스트 메시지 수신 → 저장 → 파싱 시도"""
    if not is_authorized(update.effective_user.id):
        return

    text = update.message.text
    if not text:
        return

    # 1. 원본 메시지 저장
    raw_id = await save_raw_message(
        telegram_message_id=update.message.message_id,
        raw_text=text,
        source="telegram",
    )

    # 2. 파싱 시도
    result = parse_expense(text)

    if result and (result.amount or result.foreign_currency):
        # 제외 대상 카드 확인
        if any(s in (result.payment_method or "") for s in SKIP_CARDS):
            await update.message.reply_text("📥 메시지 저장 완료 (등록 제외 카드)")
            return

        # 외화 → 원화 변환
        if result.foreign_currency and result.amount is None:
            krw = await to_krw(abs(result.foreign_amount), result.foreign_currency)
            if krw is not None:
                result.amount = krw if result.foreign_amount >= 0 else -krw
            else:
                await update.message.reply_text(
                    f"📥 메시지 저장 완료\n"
                    f"⚠️ 환율 조회 실패 ({result.foreign_currency} {result.foreign_amount})"
                )
                return

        # 파싱 성공 → 거래 저장
        tx_id = await save_transaction(
            raw_message_id=raw_id,
            payment_method=result.payment_method,
            transacted_at=result.transacted_at,
            merchant=result.merchant,
            amount=result.amount,
        )

        dt_str = (
            result.transacted_at.strftime("%m/%d %H:%M")
            if result.transacted_at
            else ""
        )

        foreign_info = ""
        if result.foreign_currency:
            foreign_info = f"\n💱 {result.foreign_currency} {result.foreign_amount}"

        await update.message.reply_text(
            f"✅ 기록 완료\n"
            f"💳 {result.payment_method or '미분류'}\n"
            f"🕐 {dt_str}\n"
            f"🏪 {result.merchant or '미상'}\n"
            f"💰 {result.amount:,}원{foreign_info}"
        )
    else:
        # 파싱 실패 → 원본만 저장됨
        await update.message.reply_text(
            "📥 메시지 저장 완료\n"
            "⚠️ 자동 파싱 실패 — 수동 입력이 필요합니다.\n"
            "웹 UI에서 분류해주세요."
        )


# ──────────────────────────────────────────────
# 앱 시작/종료
# ──────────────────────────────────────────────

async def post_init(app: Application):
    """봇 시작 시 DB 풀 초기화"""
    await get_pool()
    logger.info("봇 시작 완료")


async def post_shutdown(app: Application):
    """봇 종료 시 DB 풀 정리"""
    await close_pool()
    logger.info("봇 종료 완료")


async def main():
    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("myid", cmd_myid))
    app.add_handler(CommandHandler("recent", cmd_recent))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("봇 폴링 시작...")
    async with app:
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await app.start()
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())

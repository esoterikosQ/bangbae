# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bangbae (방배) is a personal expense tracking system that captures Korean card transaction push notifications, parses them, and provides analytics. It has three main components: a Telegram bot for ingestion, a FastAPI REST API, and a React frontend.

## Architecture

```
Push Notifications → [Telegram Bot (bot.py) | MacroDroid Webhook]
                          ↓
                   parsers.py (card-specific regex parsers)
                          ↓
                   currency.py (foreign → KRW conversion)
                          ↓
                   PostgreSQL (asyncpg, raw SQL, no ORM)
                          ↓
                   FastAPI API (api/, port 8100, prefix /treasury)
                          ↓
                   React UI (web/, Vite, Tailwind CSS)
```

**Dual ingestion:** Telegram bot (polling mode) and MacroDroid webhook (`POST /webhook/push` with `X-API-Key`) both feed into the same parsing pipeline. Failed parses save the raw text to `raw_messages` for manual classification — no data loss.

**Receipt pipeline:** Image upload → Tesseract OCR (Korean+English) → Ollama Gemma3:27b → structured JSON → user confirms → saved as `receipt_items` + `receipt_adjustments`.

**Auth:** TOTP 2FA (secret stored in `.totp_secret` file) → JWT tokens (HS256, 7-day expiry).

## Commands

### Bot
```bash
source venv/bin/activate && python bot.py
```

### API Server
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8100
```

### Frontend Dev
```bash
cd web && npm run dev
```

### Frontend Build
```bash
cd web && npm run build   # outputs to web/dist/, served by FastAPI
```

### Database Init
```bash
psql -U expense_app -d expense_tracker -f schema.sql
```

### launchd (macOS auto-restart)
```bash
# Bot:  com.expense.bot.plist → ~/Library/LaunchAgents/
# API:  com.expense.api.plist → ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.expense.bot.plist
launchctl load ~/Library/LaunchAgents/com.expense.api.plist
```

## Key Design Patterns

**Card parsers** follow an abstract base class pattern: `CardParser` with `detect()` and `parse()` methods. Four implementations exist (KB국민, 신한, IBK, 현대). The `PARSERS` registry list is iterated to find a matching parser. `_infer_year()` handles deducing full year from MM/DD with month-wraparound logic.

**Foreign currency:** Hyundai card overseas transactions return `foreign_amount` + `foreign_currency` in `ParsedExpense`. Conversion to KRW happens via `currency.to_krw()` using open.er-api.com with in-memory rate caching.

**Async throughout:** asyncpg connection pool (min=2, max=10, lazy init), httpx.AsyncClient for external calls, FastAPI async routes.

**API prefix:** All routes are under `/treasury/api`. Frontend API client base URL is `$VITE_API_URL` or `/treasury/api`.

## Environment Variables (.env)

| Variable | Purpose |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | PostgreSQL connection |
| `ALLOWED_TELEGRAM_IDS` | Comma-separated authorized user IDs |
| `JWT_SECRET` | JWT signing key |
| `WEBHOOK_API_KEY` | MacroDroid webhook auth |
| `ALLOWED_ORIGINS` | CORS origins (comma-separated) |
| `OLLAMA_URL`, `OLLAMA_MODEL` | Local LLM endpoint (default: gemma3:27b) |
| `LOG_LEVEL` | Logging level (default: INFO) |

## Database

PostgreSQL with raw asyncpg queries (no ORM). Core tables: `raw_messages`, `transactions`, `categories` (self-referencing hierarchy), `receipt_items`, `receipt_adjustments`, `budgets` (unique on `year_month + category_id`). Schema defined in `schema.sql`.

## Logs

Bot logs to `logs/bot.log`, API logs to `logs/api.log`.

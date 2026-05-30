"""
지출 관리 API 서버

uvicorn api.main:app --host 0.0.0.0 --port 8100
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.database import get_pool, close_pool
from api.routes.auth_routes import router as auth_router
from api.routes.transactions import router as tx_router
from api.routes.categories import router as cat_router
from api.routes.budgets import router as budget_router
from api.routes.receipts import router as receipt_router
from api.routes.webhook import router as webhook_router

# 프론트엔드 빌드 디렉토리
STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "dist"

# 서브 경로
BASE_PATH = "/treasury"

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(
    title="지출 관리 API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=f"{BASE_PATH}/api/docs",
    openapi_url=f"{BASE_PATH}/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 — /treasury/api 프리픽스
app.include_router(auth_router, prefix=f"{BASE_PATH}/api")
app.include_router(tx_router, prefix=f"{BASE_PATH}/api")
app.include_router(cat_router, prefix=f"{BASE_PATH}/api")
app.include_router(budget_router, prefix=f"{BASE_PATH}/api")
app.include_router(receipt_router, prefix=f"{BASE_PATH}/api")
app.include_router(webhook_router, prefix=f"{BASE_PATH}/api")


@app.get(f"{BASE_PATH}/api/health")
async def health():
    return {"status": "ok"}


# 프론트엔드 정적 파일 서빙
if STATIC_DIR.exists():
    app.mount(
        f"{BASE_PATH}/assets",
        StaticFiles(directory=STATIC_DIR / "assets"),
        name="assets",
    )

    @app.get(f"{BASE_PATH}/{{path:path}}")
    async def spa_fallback(request: Request, path: str):
        file_path = STATIC_DIR / path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")

    # /treasury 루트도 처리
    @app.get(BASE_PATH)
    async def spa_root():
        return FileResponse(STATIC_DIR / "index.html")

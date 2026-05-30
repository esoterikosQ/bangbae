import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 5432))
    DB_NAME = os.getenv("DB_NAME", "expense_tracker")
    DB_USER = os.getenv("DB_USER", "expense_app")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # 허용된 텔레그램 사용자 ID 목록 (비어있으면 제한 없음)
    _ids = os.getenv("ALLOWED_TELEGRAM_IDS", "")
    ALLOWED_TELEGRAM_IDS = (
        set(int(x.strip()) for x in _ids.split(",") if x.strip())
        if _ids
        else set()
    )

    @property
    def db_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


config = Config()

"""
인증 모듈 — TOTP 2FA + JWT 세션

초기 설정:
1. /auth/setup 으로 TOTP 시크릿 생성 → QR코드를 Google Authenticator에 등록
2. /auth/login 으로 TOTP 코드 입력 → JWT 토큰 발급

이후 모든 API 요청에 Authorization: Bearer <token> 헤더 필요
"""

import os
from datetime import datetime, timezone, timedelta

import pyotp
import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

JWT_SECRET = os.getenv("JWT_SECRET", "change-this-to-random-secret-key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24 * 7

TOTP_SECRET_FILE = os.path.join(os.path.dirname(__file__), "..", ".totp_secret")

security = HTTPBearer()


def get_or_create_totp_secret() -> str:
    if os.path.exists(TOTP_SECRET_FILE):
        with open(TOTP_SECRET_FILE, "r") as f:
            return f.read().strip()
    secret = pyotp.random_base32()
    with open(TOTP_SECRET_FILE, "w") as f:
        f.write(secret)
    os.chmod(TOTP_SECRET_FILE, 0o600)
    return secret


def get_totp() -> pyotp.TOTP:
    return pyotp.TOTP(get_or_create_totp_secret())


def verify_totp(code: str) -> bool:
    return get_totp().verify(code, valid_window=1)


def get_provisioning_uri() -> str:
    return get_totp().provisioning_uri(
        name="expense-tracker",
        issuer_name="Bangbae",
    )


def create_token() -> str:
    payload = {
        "sub": "owner",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "토큰이 만료되었습니다")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "유효하지 않은 토큰입니다")

import io
import base64

import pyotp
import qrcode
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from api.auth import verify_totp, create_token, get_provisioning_uri, get_or_create_totp_secret

router = APIRouter(prefix="/auth", tags=["인증"])


class LoginRequest(BaseModel):
    code: str


class LoginResponse(BaseModel):
    token: str
    expires_in: int


class SetupResponse(BaseModel):
    qr_code: str  # base64 PNG
    secret: str
    uri: str


@router.get("/setup/qr")
async def setup_totp_qr():
    """QR코드를 PNG 이미지로 반환 — 브라우저에서 바로 스캔 가능"""
    uri = get_provisioning_uri()
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")

@router.post("/setup", response_model=SetupResponse)
async def setup_totp():
    """
    TOTP 초기 설정. QR코드를 Google Authenticator에 등록.
    이미 설정되어 있으면 기존 시크릿의 QR을 반환.
    """
    secret = get_or_create_totp_secret()
    uri = get_provisioning_uri()

    # QR코드 생성
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    return SetupResponse(
        qr_code=qr_b64,
        secret=secret,
        uri=uri,
    )


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    """TOTP 코드로 로그인 → JWT 토큰 발급"""
    if not verify_totp(body.code):
        raise HTTPException(401, "인증 코드가 올바르지 않습니다")

    token = create_token()
    return LoginResponse(
        token=token,
        expires_in=24 * 7 * 3600,
    )

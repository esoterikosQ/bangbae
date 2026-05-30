"""
영수증 OCR + LLM 구조화 파이프라인

1. Tesseract로 영수증 이미지에서 텍스트 추출
2. Ollama Gemma 4로 텍스트를 구조화된 품목 데이터로 변환
"""

import json
import logging
import os
from io import BytesIO
from dataclasses import dataclass

import httpx
from PIL import Image
import pytesseract

# tesseract 경로 
pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:27b")

STRUCTURING_PROMPT = """다음은 영수증을 OCR로 읽은 텍스트입니다. 이 텍스트에서 아래 정보를 추출하여 JSON으로 반환하세요.

반드시 아래 JSON 형식만 반환하고, 다른 텍스트는 포함하지 마세요.

{
  "merchant": "거래처/가맹점명",
  "transacted_at": "YYYY-MM-DD HH:MM 또는 null",
  "items": [
    {
      "item_name": "품목명",
      "unit_price": 단가(정수),
      "quantity": 수량(정수),
      "item_total": 품목별합계(정수)
    }
  ],
  "subtotal": 소계(정수) 또는 null,
  "discounts": [
    {
      "description": "할인 내역 설명",
      "amount": 할인금액(정수)
    }
  ],
  "total": 총계(정수),
  "paid": 실제결제금액(정수) 또는 null,
  "payment_method": "결제수단" 또는 null
}

규칙:
- 금액은 모두 원 단위 정수로 (콤마, 원 제거)
- 추출할 수 없는 항목은 null
- items가 없으면 빈 배열 []
- discounts가 없으면 빈 배열 []

OCR 텍스트:
"""


@dataclass
class ReceiptData:
    raw_text: str
    merchant: str | None = None
    transacted_at: str | None = None
    items: list[dict] | None = None
    subtotal: int | None = None
    discounts: list[dict] | None = None
    total: int | None = None
    paid: int | None = None
    payment_method: str | None = None


def ocr_image(image_bytes: bytes) -> str:
    """이미지에서 텍스트 추출"""
    img = Image.open(BytesIO(image_bytes))

    # 그레이스케일 변환
    if img.mode != "L":
        img = img.convert("L")

    # Tesseract OCR (한국어 + 영어)
    text = pytesseract.image_to_string(img, lang="kor+eng")
    logger.info(f"OCR 추출 텍스트 길이: {len(text)}")
    return text


async def structure_receipt(raw_text: str) -> ReceiptData:
    """Ollama Gemma 4로 OCR 텍스트를 구조화"""
    prompt = STRUCTURING_PROMPT + raw_text

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 2048,
                    },
                },
            )
            resp.raise_for_status()
            result = resp.json()
            response_text = result.get("response", "")

        # JSON 추출 (마크다운 코드블록 제거)
        json_text = response_text.strip()
        if json_text.startswith("```"):
            json_text = json_text.split("\n", 1)[1]
        if json_text.endswith("```"):
            json_text = json_text.rsplit("```", 1)[0]
        json_text = json_text.strip()

        data = json.loads(json_text)
        logger.info(f"LLM 구조화 완료: {len(data.get('items', []))}개 품목")

        return ReceiptData(
            raw_text=raw_text,
            merchant=data.get("merchant"),
            transacted_at=data.get("transacted_at"),
            items=data.get("items", []),
            subtotal=data.get("subtotal"),
            discounts=data.get("discounts", []),
            total=data.get("total"),
            paid=data.get("paid"),
            payment_method=data.get("payment_method"),
        )

    except json.JSONDecodeError as e:
        logger.error(f"LLM 응답 JSON 파싱 실패: {e}")
        logger.debug(f"원본 응답: {response_text[:500]}")
        return ReceiptData(raw_text=raw_text)

    except Exception as e:
        logger.error(f"LLM 구조화 실패: {e}")
        return ReceiptData(raw_text=raw_text)


async def process_receipt(image_bytes: bytes) -> ReceiptData:
    """영수증 이미지 → OCR → 구조화 전체 파이프라인"""
    raw_text = ocr_image(image_bytes)
    if not raw_text.strip():
        logger.warning("OCR 결과가 비어있습니다")
        return ReceiptData(raw_text="")

    return await structure_receipt(raw_text)

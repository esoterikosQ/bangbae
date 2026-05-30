"""
카드사별 푸시 알림 파서

각 카드사의 푸시 형식에 맞는 파서를 등록하고,
수신된 메시지에서 지출수단, 일시, 거래처, 금액을 추출한다.

새 카드사를 추가하려면:
1. CardParser를 상속받는 클래스 생성
2. detect()와 parse()를 구현
3. PARSERS 리스트에 등록
"""

import re
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class ParsedExpense:
    """파싱된 지출 정보"""
    payment_method: str | None = None
    transacted_at: datetime | None = None
    merchant: str | None = None
    amount: int | None = None
    foreign_amount: float | None = None
    foreign_currency: str | None = None
    raw_text: str = ""


class CardParser(ABC):
    """카드사 파서 베이스 클래스"""

    @abstractmethod
    def detect(self, text: str) -> bool:
        ...

    @abstractmethod
    def parse(self, text: str) -> ParsedExpense | None:
        ...

    def _infer_year(self, month: int) -> int:
        now = datetime.now()
        return now.year if month <= now.month else now.year - 1


# ──────────────────────────────────────────────
# KB국민카드 / KB Pay
# ──────────────────────────────────────────────
# 패턴 1 (국내 일반 멀티라인):
#   KB국민체크(4045)
#   박*규님
#   04/15 15:50
#   426,000원
#   세곡연두 어린이집 사용
#
# 패턴 2 (국내 멀티라인, 시간 없음):
#   KB국민카드4086 승인
#   박*규
#   221,480원 12/18
#   박*훈/방과후수
#
# 패턴 3 (취소):
#   KB Pay[KB국민카드] 4086 박*규님 SR 03월17일 이용건 04월16일 취소완료(-11,200원)
#
# 패턴 4 (해외):
#   KB PayKB국민카드 박*규님 04/25 22:41 2,600(KRW) 미국   D J*WSJ 승인 e.kbcard.com/paydetail
#
# 패턴 5 (KB Pay 한 줄 승인/승인취소):
#   KB Pay[KB Pay 사용 알림] 신용 4086 03/23 09:09 27,100원 국민은행LiivM 승인
#   KB Pay[KB Pay] 신용 6042 12/21 18:03 18,820원 교보문고 승인취소
# ──────────────────────────────────────────────

class KookminParser(CardParser):
    """KB국민카드/체크 파서"""

    CANCEL_PATTERN = re.compile(
        r"(?:KB\s*Pay)?\[?KB국민\S*\]?\s*(\d{4})\s*\S+님\s*\S*\s*"
        r"(\d{2})월(\d{2})일\s*이용건\s*"
        r"(\d{2})월(\d{2})일\s*취소완료\s*"
        r"\(?\-?([\d,]+)원\)?"
    )

    KBPAY_PATTERN = re.compile(
        r"KB\s*Pay\[KB\s*Pay(?:\s*사용\s*알림)?\]\s*"
        r"(\S+)\s+(\d{4})\s+"
        r"(\d{2})/(\d{2})\s+(\d{2}):(\d{2})\s+"
        r"([\d,]+)원\s+"
        r"(.+?)\s+(승인취소|승인)"
    )

    OVERSEAS_PATTERN = re.compile(
        r"KB\s*Pay\s*KB국민카드\s*\S+님\s*"
        r"(\d{2})/(\d{2})\s+(\d{2}):(\d{2})\s+"
        r"([\d,]+)\((\w+)\)\s+"
        r"(\S+)\s+"
        r"(.+?)\s+승인"
    )

    def detect(self, text: str) -> bool:
        return "KB국민" in text or "KB Pay" in text

    def parse(self, text: str) -> ParsedExpense | None:
        cancel = self.CANCEL_PATTERN.search(text)
        if cancel:
            return self._parse_cancel(cancel, text)

        kbpay = self.KBPAY_PATTERN.search(text)
        if kbpay:
            return self._parse_kbpay(kbpay, text)

        overseas = self.OVERSEAS_PATTERN.search(text)
        if overseas:
            return self._parse_overseas(overseas, text)

        return self._parse_normal(text)

    def _parse_cancel(self, m: re.Match, text: str) -> ParsedExpense:
        card_suffix = m.group(1)
        cancel_month, cancel_day = int(m.group(4)), int(m.group(5))
        amount = int(m.group(6).replace(",", ""))

        year = self._infer_year(cancel_month)
        transacted_at = datetime(year, cancel_month, cancel_day,
                                 tzinfo=timezone.utc)

        return ParsedExpense(
            payment_method=f"KB국민카드({card_suffix})",
            transacted_at=transacted_at,
            merchant="취소",
            amount=-amount,
            raw_text=text,
        )

    def _parse_kbpay(self, m: re.Match, text: str) -> ParsedExpense:
        card_type = m.group(1)
        card_suffix = m.group(2)
        month, day = int(m.group(3)), int(m.group(4))
        hour, minute = int(m.group(5)), int(m.group(6))
        amount = int(m.group(7).replace(",", ""))
        merchant = m.group(8).strip()
        is_cancel = m.group(9) == "승인취소"

        if is_cancel:
            amount = -amount

        year = self._infer_year(month)
        transacted_at = datetime(year, month, day, hour, minute,
                                 tzinfo=timezone.utc)

        return ParsedExpense(
            payment_method=f"KB국민카드({card_suffix})",
            transacted_at=transacted_at,
            merchant=merchant,
            amount=amount,
            raw_text=text,
        )

    def _parse_overseas(self, m: re.Match, text: str) -> ParsedExpense:
        month, day = int(m.group(1)), int(m.group(2))
        hour, minute = int(m.group(3)), int(m.group(4))
        amount = int(m.group(5).replace(",", ""))
        country = m.group(7)
        merchant = m.group(8).strip()

        year = self._infer_year(month)
        transacted_at = datetime(year, month, day, hour, minute,
                                 tzinfo=timezone.utc)

        return ParsedExpense(
            payment_method="KB국민카드",
            transacted_at=transacted_at,
            merchant=f"[{country}] {merchant}",
            amount=amount,
            raw_text=text,
        )

    def _parse_normal(self, text: str) -> ParsedExpense | None:
        lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
        if len(lines) < 3:
            return None

        # 카드명 + 취소/승인 여부
        card_line = lines[0]
        is_cancel = "취소" in card_line and "승인" not in card_line

        card_match = re.match(r"(KB국민\S+?)(\d{4})", card_line)
        if card_match:
            payment_method = f"{card_match.group(1)}({card_match.group(2)})"
        else:
            pm_match = re.match(r"(KB국민\S+?)(?:\(\d+\))?$", card_line)
            payment_method = pm_match.group(1) if pm_match else "KB국민카드"

        # 일시 — 시간 있는 경우와 없는 경우 모두 처리
        dt_full = re.search(r"(\d{2})/(\d{2})\s+(\d{2}):(\d{2})", text)
        dt_date = re.search(r"(\d{2})/(\d{2})", text)
        transacted_at = None
        if dt_full:
            month, day = int(dt_full.group(1)), int(dt_full.group(2))
            hour, minute = int(dt_full.group(3)), int(dt_full.group(4))
            year = self._infer_year(month)
            transacted_at = datetime(year, month, day, hour, minute,
                                     tzinfo=timezone.utc)
        elif dt_date:
            month, day = int(dt_date.group(1)), int(dt_date.group(2))
            year = self._infer_year(month)
            transacted_at = datetime(year, month, day, tzinfo=timezone.utc)

        # 금액
        amount_match = re.search(r"([\d,]+)원", text)
        if not amount_match:
            return None
        amount = int(amount_match.group(1).replace(",", ""))
        if is_cancel:
            amount = -amount

        # 거래처 — 이름, 카드명, 날짜, 금액, 누적 줄을 제외한 나머지
        merchant = None
        for line in lines:
            if "KB국민" in line:
                continue
            if re.match(r"^.{2,4}$", line) and "*" in line:
                continue
            if "님" in line and len(line) < 20:
                continue
            if "원" in line:
                continue
            if re.match(r"\d{2}/\d{2}", line):
                continue
            if "누적" in line:
                continue
            merchant = re.sub(r"\s*사용\s*$", "", line)
            break

        return ParsedExpense(
            payment_method=payment_method,
            transacted_at=transacted_at,
            merchant=merchant,
            amount=amount,
            raw_text=text,
        )


# ──────────────────────────────────────────────
# 신한카드 / SOL페이
# ──────────────────────────────────────────────
# 패턴 1 (승인):
#   신한 SOL페이[신한체크승인] 박*규(2363)
#   - 승인일시: 04/29 20:11
#   - 승인금액: 7,500원
#   - 가맹점명: 아이스무빙(강남힐스
#   [신한카드 1544-7000]
#
# 패턴 2 (매출취소):
#   신한 SOL페이신한카드 (9364)  매출취소  박*규  7,500원  01/09 유라이프
#   [발신번호 1544-7000]
# ──────────────────────────────────────────────

class ShinhanParser(CardParser):
    """신한카드/체크 파서"""

    CANCEL_PATTERN = re.compile(
        r"신한\s*SOL페이\s*(신한카드)\s*\((\d{4})\)\s+"
        r"매출취소\s+\S+\s+"
        r"([\d,]+)원\s+"
        r"(\d{2})/(\d{2})\s+"
        r"(.+?)(?:\s*\[|$)"
    )

    def detect(self, text: str) -> bool:
        return "신한" in text and ("승인" in text or "취소" in text or "결제" in text)

    def parse(self, text: str) -> ParsedExpense | None:
        cancel = self.CANCEL_PATTERN.search(text)
        if cancel:
            return self._parse_cancel(cancel, text)

        return self._parse_normal(text)

    def _parse_cancel(self, m: re.Match, text: str) -> ParsedExpense:
        card_suffix = m.group(2)
        amount = int(m.group(3).replace(",", ""))
        month, day = int(m.group(4)), int(m.group(5))
        merchant = m.group(6).strip()

        year = self._infer_year(month)
        transacted_at = datetime(year, month, day, tzinfo=timezone.utc)

        return ParsedExpense(
            payment_method=f"신한카드({card_suffix})",
            transacted_at=transacted_at,
            merchant=merchant,
            amount=-amount,
            raw_text=text,
        )

    def _parse_normal(self, text: str) -> ParsedExpense | None:

        # 카드 종류
        type_match = re.search(r"\[(신한\S*?)(승인|취소)\]", text)
        payment_method = type_match.group(1) if type_match else "신한카드"
        is_cancel = type_match and type_match.group(2) == "취소"

        # 카드번호 뒷자리 — payment_method에 이미 없을 때만 추가
        card_match = re.search(r"\((\d{4})\)", text)
        if card_match and card_match.group(1) not in payment_method:
            payment_method += f"({card_match.group(1)})"

        
        # # 카드 종류 — [신한체크승인], [신한카드승인] 등
        # type_match = re.search(r"\[(신한\S*?)(승인|취소)\]", text)
        # payment_method = type_match.group(1) if type_match else "신한카드"
        # is_cancel = type_match and type_match.group(2) == "취소"

        # # 카드번호 뒷자리
        # card_match = re.search(r"\((\d{4})\)", text)
        # if card_match:
        #     payment_method += f"({card_match.group(1)})"

        # 일시
        dt_match = re.search(r"(\d{2})/(\d{2})\s+(\d{2}):(\d{2})", text)
        transacted_at = None
        if dt_match:
            month, day = int(dt_match.group(1)), int(dt_match.group(2))
            hour, minute = int(dt_match.group(3)), int(dt_match.group(4))
            year = self._infer_year(month)
            transacted_at = datetime(year, month, day, hour, minute,
                                     tzinfo=timezone.utc)

        # 금액
        amount_match = re.search(r"([\d,]+)원", text)
        if not amount_match:
            return None
        amount = int(amount_match.group(1).replace(",", ""))
        if is_cancel:
            amount = -amount

        # 거래처
        merchant = None
        merchant_match = re.search(r"가맹점명:\s*(.+)", text)
        if merchant_match:
            merchant = merchant_match.group(1).strip()
            merchant = re.sub(r"\s*\[신한카드.*", "", merchant)

        return ParsedExpense(
            payment_method=payment_method,
            transacted_at=transacted_at,
            merchant=merchant,
            amount=amount,
            raw_text=text,
        )


# ──────────────────────────────────────────────
# IBK기업은행 카드
# ──────────────────────────────────────────────
# 패턴 1 (해외):
#   IBK 카드카드 승인내역 알림 , GITHUB, INC.           SAN FRANCISCO USA
#   $10.00/ 14,967원 일시불 승인
#   2026.04.19 01:18:17
#   ※승인 시점 환율을 기준으로...
#
# 패턴 2 (국내):
#   IBK 카드카드 승인내역 알림 , 충북대학교소비자생활
#   3,000원 일시불 승인
#   2026.04.29 16:50:42
# ──────────────────────────────────────────────

class IBKParser(CardParser):
    """IBK기업은행 카드 파서"""

    def detect(self, text: str) -> bool:
        return "IBK" in text and ("승인" in text or "취소" in text)

    def parse(self, text: str) -> ParsedExpense | None:
        lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
        if len(lines) < 3:
            return None

        # 금액 — 원화 기준
        amount_match = re.search(r"([\d,]+)원", text)
        if not amount_match:
            return None
        amount = int(amount_match.group(1).replace(",", ""))

        if "취소" in text:
            amount = -amount

        # 일시 — 2026.04.19 01:18:17
        dt_match = re.search(
            r"(\d{4})\.(\d{2})\.(\d{2})\s+(\d{2}):(\d{2}):(\d{2})", text
        )
        transacted_at = None
        if dt_match:
            transacted_at = datetime(
                int(dt_match.group(1)),
                int(dt_match.group(2)),
                int(dt_match.group(3)),
                int(dt_match.group(4)),
                int(dt_match.group(5)),
                int(dt_match.group(6)),
                tzinfo=timezone.utc,
            )

        # 거래처 — "알림" 뒤 쉼표 이후
        merchant = None
        first_line = lines[0]
        alrim_match = re.search(r"알림\s*,?\s*(.+)", first_line)
        if alrim_match:
            merchant = alrim_match.group(1).strip()
        else:
            for line in lines[1:]:
                if "원" in line:
                    continue
                if re.match(r"\d{4}\.\d{2}\.\d{2}", line):
                    continue
                if line.startswith("※"):
                    continue
                merchant = line.strip()
                break

        return ParsedExpense(
            payment_method="IBK카드",
            transacted_at=transacted_at,
            merchant=merchant,
            amount=amount,
            raw_text=text,
        )


# ──────────────────────────────────────────────
# 현대카드
# ──────────────────────────────────────────────
# 패턴 1 (국내):
#   현대카드박승규 님, 현대카드 ZERO 승인 211,910원 일시불, 5/5 14:07
#
# 패턴 2 (해외):
#   현대카드박승규 님, [현대카드] 해외승인 USD 0.99 2/5 8:13
# ──────────────────────────────────────────────

class HyundaiParser(CardParser):
    """현대카드 파서"""

    DOMESTIC_PATTERN = re.compile(
        r"현대카드.+?님,\s*"
        r"(현대카드\s*\S+)\s+"
        r"(승인|취소)\s+"
        r"([\d,]+)원\s*"
        r"(?:일시불|할부)?\s*,?\s*"
        r"(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})"
    )

    OVERSEAS_PATTERN = re.compile(
        r"현대카드.+?님,\s*"
        r"\[현대카드\]\s*해외(승인|취소)\s+"
        r"([A-Z]{3})\s+([\d.]+)\s+"
        r"(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})"
    )

    def detect(self, text: str) -> bool:
        return "현대카드" in text

    def parse(self, text: str) -> ParsedExpense | None:
        overseas = self.OVERSEAS_PATTERN.search(text)
        if overseas:
            return self._parse_overseas(overseas, text)

        domestic = self.DOMESTIC_PATTERN.search(text)
        if domestic:
            return self._parse_domestic(domestic, text)

        return None

    def _parse_overseas(self, m: re.Match, text: str) -> ParsedExpense:
        is_cancel = m.group(1) == "취소"
        currency = m.group(2)
        foreign_amount = float(m.group(3))
        month, day = int(m.group(4)), int(m.group(5))
        hour, minute = int(m.group(6)), int(m.group(7))

        year = self._infer_year(month)
        transacted_at = datetime(year, month, day, hour, minute,
                                 tzinfo=timezone.utc)

        if is_cancel:
            foreign_amount = -foreign_amount

        return ParsedExpense(
            payment_method="현대카드",
            transacted_at=transacted_at,
            merchant=None,
            amount=None,
            foreign_amount=foreign_amount,
            foreign_currency=currency,
            raw_text=text,
        )

    def _parse_domestic(self, m: re.Match, text: str) -> ParsedExpense:
        payment_method = m.group(1).strip()
        is_cancel = m.group(2) == "취소"
        amount = int(m.group(3).replace(",", ""))
        if is_cancel:
            amount = -amount

        month, day = int(m.group(4)), int(m.group(5))
        hour, minute = int(m.group(6)), int(m.group(7))
        year = self._infer_year(month)
        transacted_at = datetime(year, month, day, hour, minute,
                                 tzinfo=timezone.utc)

        return ParsedExpense(
            payment_method=payment_method,
            transacted_at=transacted_at,
            merchant=None,
            amount=amount,
            raw_text=text,
        )


# ──────────────────────────────────────────────
# 파서 레지스트리
# ──────────────────────────────────────────────

PARSERS: list[CardParser] = [
    KookminParser(),
    ShinhanParser(),
    IBKParser(),
    HyundaiParser(),
]


def parse_expense(text: str) -> ParsedExpense | None:
    """
    메시지 텍스트를 받아서 매칭되는 파서로 지출 정보를 추출.
    매칭되는 파서가 없거나 파싱에 실패하면 None을 반환.
    """
    for parser in PARSERS:
        if parser.detect(text):
            try:
                result = parser.parse(text)
                if result:
                    logger.info(
                        f"파싱 성공 [{parser.__class__.__name__}]: "
                        f"{result.payment_method} {result.amount}원 {result.merchant}"
                    )
                    return result
            except Exception as e:
                logger.error(f"파싱 오류 [{parser.__class__.__name__}]: {e}")

    logger.debug(f"매칭되는 파서 없음: {text[:50]}...")
    return None

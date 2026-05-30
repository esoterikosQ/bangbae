# 지출 관리 텔레그램 봇

카드사 푸시 알림을 텔레그램으로 전달하면 자동으로 파싱하여 PostgreSQL에 저장하는 봇.

## 구성

```
Yellowstone (Mac Studio)     Shenandoah (TrueNAS)
┌──────────────────────┐     ┌──────────────────┐
│  bot.py (polling)    │────▶│  PostgreSQL      │
│  parsers.py          │     │  expense_tracker │
└──────────────────────┘     └──────────────────┘
        ▲
        │ Telegram API
        │
   핸드폰 (푸시 전달)
```

## 1. Shenandoah — DB 준비

```bash
# PostgreSQL에 접속하여 사용자 및 DB 생성
psql -U postgres

CREATE USER expense_app WITH PASSWORD '원하는_비밀번호';
CREATE DATABASE expense_tracker OWNER expense_app;
\c expense_tracker
\i schema.sql
```

## 2. Yellowstone — 봇 설치

```bash
# 프로젝트 디렉토리
mkdir -p ~/projects/expense-bot
cd ~/projects/expense-bot

# 가상환경
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일에서 DB_PASSWORD, ALLOWED_TELEGRAM_IDS 수정
```

## 3. Telegram ID 확인

봇을 처음 실행한 뒤 텔레그램에서 `/myid` 명령을 보내면
본인의 Telegram ID가 표시됩니다. 이 값을 `.env`의
`ALLOWED_TELEGRAM_IDS`에 넣으면 본인만 사용 가능합니다.

## 4. 실행

```bash
# 직접 실행
source venv/bin/activate
python bot.py

# 또는 백그라운드 (macOS launchd)
cp com.expense.bot.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.expense.bot.plist
```

## 5. 사용법

텔레그램에서 봇에게 카드 결제 푸시 알림 텍스트를 전달:

```
[신한카드] 홍길동 님 12,500원 결제
05/09 14:23 스타벅스코리아
일시불 잔여한도 2,345,000원
```

봇이 자동으로 파싱하여 저장하고 결과를 응답합니다.
파싱 실패 시 원본만 저장되며, 웹 UI에서 수동 분류 가능합니다.

## 명령어

| 명령 | 설명 |
|------|------|
| `/start` | 봇 시작 및 안내 |
| `/myid` | 내 Telegram ID 확인 |
| `/recent` | 최근 거래 5건 |
| `/status` | 이번 달 지출 현황 |

## 파서 추가

`parsers.py`에 새 카드사 파서를 추가하려면:

1. `CardParser`를 상속받는 클래스 생성
2. `detect(text)` — 해당 카드사 메시지인지 판별
3. `parse(text)` — 정규표현식으로 정보 추출
4. `PARSERS` 리스트에 인스턴스 등록

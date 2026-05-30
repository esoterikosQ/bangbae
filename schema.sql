-- 지출 관리 시스템 데이터베이스 스키마
-- Shenandoah PostgreSQL (Docker)에 적용

-- 지출 분류 테이블
CREATE TABLE categories (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    parent_id       INTEGER REFERENCES categories(id),
    icon            VARCHAR(50),
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 수신 원본 메시지 (텔레그램에서 받은 그대로 저장)
CREATE TABLE raw_messages (
    id              SERIAL PRIMARY KEY,
    telegram_message_id BIGINT,
    raw_text        TEXT NOT NULL,
    source          VARCHAR(50) DEFAULT 'telegram',
    is_parsed       BOOLEAN DEFAULT FALSE,
    received_at     TIMESTAMPTZ DEFAULT NOW()
);

-- 거래 내역 (파싱된 결과)
CREATE TABLE transactions (
    id              SERIAL PRIMARY KEY,
    raw_message_id  INTEGER REFERENCES raw_messages(id),
    payment_method  VARCHAR(100),         -- 지출수단 (신한카드, 국민카드 등)
    transacted_at   TIMESTAMPTZ,          -- 거래 일시
    merchant        VARCHAR(200),         -- 거래처
    amount          INTEGER NOT NULL,     -- 금액 (원 단위)
    category_id     INTEGER REFERENCES categories(id),
    memo            TEXT,
    has_receipt     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 영수증 품목 (거래 1건에 N개 품목)
CREATE TABLE receipt_items (
    id              SERIAL PRIMARY KEY,
    transaction_id  INTEGER REFERENCES transactions(id) ON DELETE CASCADE,
    item_name       VARCHAR(200) NOT NULL,
    unit_price      INTEGER,
    quantity        INTEGER DEFAULT 1,
    item_total      INTEGER,
    category_id     INTEGER REFERENCES categories(id),
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 영수증 할인/결제 내역
CREATE TABLE receipt_adjustments (
    id              SERIAL PRIMARY KEY,
    transaction_id  INTEGER REFERENCES transactions(id) ON DELETE CASCADE,
    adj_type        VARCHAR(20) NOT NULL,  -- 'discount', 'payment'
    description     VARCHAR(200),
    amount          INTEGER NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 예산 테이블
CREATE TABLE budgets (
    id              SERIAL PRIMARY KEY,
    year_month      VARCHAR(7) NOT NULL,   -- '2026-05'
    category_id     INTEGER REFERENCES categories(id),
    budget_amount   INTEGER NOT NULL,
    is_income       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(year_month, category_id)
);

-- 인덱스
CREATE INDEX idx_raw_messages_parsed   ON raw_messages(is_parsed);
CREATE INDEX idx_transactions_date     ON transactions(transacted_at);
CREATE INDEX idx_transactions_category ON transactions(category_id);
CREATE INDEX idx_receipt_items_tx      ON receipt_items(transaction_id);
CREATE INDEX idx_budgets_month         ON budgets(year_month);

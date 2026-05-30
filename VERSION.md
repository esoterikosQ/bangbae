# VERSION.md

작업 변경 이력을 기록한다.

## 2026-05-30

### 초기 설정
- Git 저장소 초기화 및 GitHub 원격 연결 (`git@github.com:esoterikosQ/bangbae.git`)
- `.gitignore` 추가 (`.env`, `.totp_secret`, `__pycache__/`, `venv/`, `node_modules/`, `web/dist/`, `logs/` 제외)
- 백업 파일 8개 삭제: `bot.0.1.py`, `parsers.0.1.py`, `parsers.0.2.py`, `requirements.0.1.txt`, `api/main0.py`, `api/main1.py`, `api/routes/weebhook1.py`, `web/src/App0.jsx`, `web/src/api0.js`
- `CLAUDE.md` 생성 (프로젝트 아키텍처, 실행 명령, 설계 패턴 문서화)
- **영향 범위:** 프로젝트 전체

### 작업 지침 추가
- `CLAUDE.md`에 규칙 섹션 추가 (상대경로 사용, 디렉토리 제한, 변경 이력 기록)
- `VERSION.md` 신규 생성
- **영향 범위:** `CLAUDE.md`, `VERSION.md`

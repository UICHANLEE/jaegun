# Jaegun

웹을 먼저 만들고, 같은 API를 나중에 iOS/Android 앱이 쓰기 좋게 **백엔드를 분리**한 실험 저장소입니다.

## 요구 사항

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## 설치

```bash
cd jaegun
uv sync
```

## 서버 실행

```bash
uv run uvicorn jaegun.main:app --reload --host 127.0.0.1 --port 8000
```

또는:

```bash
uv run jaegun-serve
```

## 데이터

- 기본: 프로젝트 루트 `data/jaegun.db` (SQLite, `.gitignore` 처리).
- `DATABASE_URL`로 Postgres 등으로 바꿀 수 있습니다 (`.env.example`).

## API

루트(`GET /`)는 엔드포인트 안내 JSON을 반환합니다. 상세는 Swagger를 사용하세요.

**공지**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/announcements` | 목록 (`limit`, `offset`) |
| POST | `/api/announcements` | 작성 |
| GET | `/api/announcements/{id}` | 단건 |
| PATCH | `/api/announcements/{id}` | 수정 |
| DELETE | `/api/announcements/{id}` | 삭제 |

**일정**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/events` | 목록 (`limit`, `offset`, `upcoming_only`) |
| POST | `/api/events` | 작성 (`starts_at`, `ends_at`, `location` 등) |
| GET | `/api/events/{id}` | 단건 |
| PATCH | `/api/events/{id}` | 수정 |
| DELETE | `/api/events/{id}` | 삭제 |

기타: `GET /health`

문서: 서버 실행 후 <http://127.0.0.1:8000/docs>

**참고:** `{"detail":"Not Found"}`는 등록되지 않은 경로입니다. 포트가 Jaegun 서버(기본 `8000`)인지 확인하세요.

## 상위 저장소(nohoi)와의 관계

이 폴더는 **별도 Git 저장소**입니다. Next.js 프론트는 `../`(nohoi)에서 두고, API만 이쪽에서 키우거나, 나중에 `NEXT_PUBLIC_API_URL`로 이 서버를 바라보게 연결하면 됩니다.

## 환경 변수

`.env.example` 참고. 프로덕션에서는 `CORS_ORIGINS`를 실제 웹 도메인으로 제한하고, DB URL을 안전하게 관리하세요.

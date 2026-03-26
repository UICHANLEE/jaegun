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

### 문제 해결

| 증상 | 조치 |
|------|------|
| `ModuleNotFoundError: No module named 'sqlmodel'` | 프로젝트 루트(`jaegun`)에서 **`uv sync`** 후 다시 `uv run uvicorn …`. 의존성 추가 직후 리로더 자식 프로세스가 한 번 실패할 수 있어, 한 번 서버를 끄고 다시 켜면 됩니다. |
| `GET /` 가 404 | 최신 `main.py`에는 `GET /` 안내 JSON이 있습니다. 예전 프로세스면 재시작하세요. |
| 브라우저가 `/favicon.ico` 요청 | 서버가 SVG 파비콘을 제공합니다(콘솔 404는 이후 버전에서 사라짐). |
| 관리자 API가 `503` / `ADMIN_TOKEN` | 프로젝트 루트에 `.env`를 두고 `ADMIN_TOKEN=강한_비밀값` 을 설정하세요. |

**권장:** 서버는 `conda`가 아닌 **`uv run`** 으로만 실행해 가상환경과 패키지를 맞춥니다.

## 권한 모델

- **관리자** (`ADMIN_TOKEN`): 공식 공지, 공식 일정, 연간·월간 계획의 **생성·수정·삭제**. API에서는 `Authorization: Bearer <토큰>` 또는 `X-Admin-Token: <토큰>`.
- **사용자**: **게시판**(`GET/POST /api/board/posts`)에서만 글 작성. 게시글 삭제는 관리자만 가능합니다.

## 웹 UI (Branches 스타일)

- 브라우저: **<http://127.0.0.1:8000/community/>**
- **「게시판」**: 사용자 글 작성. **「더보기」**: 관리자 토큰 저장 후 공식 공지·일정 등록 폼.
- 하단 **「계획」** 탭에서 연간(연도 선택)·월간(연도 선택 후 1~12월 그리드)을 볼 수 있습니다.
- 정적 파일: 저장소 루트 `static/community/` (`index.html`, `styles.css`, `app.js`). 같은 출처에서 `/api/*`를 호출합니다.
- `GET /` JSON의 `ui` 필드에도 경로가 있습니다.

## 데이터

- 기본: 프로젝트 루트 `data/jaegun.db` (SQLite, `.gitignore` 처리).
- `DATABASE_URL`로 Postgres 등으로 바꿀 수 있습니다 (`.env.example`).

## API

루트(`GET /`)는 엔드포인트 안내 JSON을 반환합니다. 상세는 Swagger를 사용하세요.

**공지** (POST·PATCH·DELETE는 **관리자 토큰**)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/announcements` | 목록 (`limit`, `offset`) |
| POST | `/api/announcements` | 작성 |
| GET | `/api/announcements/{id}` | 단건 |
| PATCH | `/api/announcements/{id}` | 수정 |
| DELETE | `/api/announcements/{id}` | 삭제 |

**일정** (POST·PATCH·DELETE는 **관리자 토큰** — 공식 일정)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/events` | 목록 (`limit`, `offset`, `upcoming_only`) |
| POST | `/api/events` | 작성 (`starts_at`, `ends_at`, `location` 등) |
| GET | `/api/events/{id}` | 단건 |
| PATCH | `/api/events/{id}` | 수정 |
| DELETE | `/api/events/{id}` | 삭제 |

**게시판** (POST는 누구나, DELETE는 관리자)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/board/posts` | 목록 |
| POST | `/api/board/posts` | 글 작성 (`title`, `body`, `author_name` 선택) |
| GET | `/api/board/posts/{id}` | 단건 |
| DELETE | `/api/board/posts/{id}` | 삭제(관리자) |

**연간·월간 계획** (POST·PATCH·DELETE는 **관리자 토큰**)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/plans/annual` | 연간 계획 목록 (연도 내림차순) |
| GET | `/api/plans/annual/{year}` | 연도별 연간 계획 단건 |
| POST/PATCH/DELETE | `/api/plans/annual` … | 작성·수정·삭제 |
| GET | `/api/plans/monthly?year=` | 해당 연도 월간 계획 목록 (월 오름차순) |
| GET | `/api/plans/monthly/{year}/{month}` | 특정 월 단건 |
| POST/PATCH/DELETE | `/api/plans/monthly` … | 작성·수정·삭제 |

기타: `GET /health`

문서: 서버 실행 후 <http://127.0.0.1:8000/docs>

**참고:** `{"detail":"Not Found"}`는 등록되지 않은 경로입니다. 포트가 Jaegun 서버(기본 `8000`)인지 확인하세요.

## 상위 저장소(nohoi)와의 관계

이 폴더는 **별도 Git 저장소**입니다. 투표용 Next.js(`../nohoi`)와는 독립이며, 커뮤니티 화면은 **이 저장소의 `/community/`** 에서 제공합니다.

## 환경 변수

`.env.example` 참고. **`ADMIN_TOKEN`** 은 공식 콘텐츠 수정에 필수입니다. 프로덕션에서는 `CORS_ORIGINS`를 실제 웹 도메인으로 제한하고, DB URL·토큰을 안전하게 관리하세요.

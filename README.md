# Jaegun

**저장소:** [github.com/UICHANLEE/jaegun](https://github.com/UICHANLEE/jaegun)

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

## 배포 (인터넷에서 링크로 접속)

### Docker Compose (VPS·로컬에서 공개)

프로젝트 루트(`jaegun/`)에서:

```bash
export ADMIN_TOKEN='강한_비밀값'
docker compose up --build -d
```

- 브라우저: `http://<서버 공인 IP 또는 도메인>:8000/community/` , 관리자: `/admin/`
- DB(SQLite)는 볼륨 `jaegun-data`에 저장됩니다.
- Postgres를 쓰려면 `DATABASE_URL`을 설정하고(예: `postgresql+psycopg://…`), 필요 시 이미지에 `psycopg` 의존성을 추가하세요.

### 클라우드 (Railway, Render, Fly.io, Google Cloud Run 등)

1. 이 저장소를 Git에 푸시합니다.
2. 서비스에서 **Dockerfile**로 빌드·실행을 선택합니다.
3. 환경 변수(대시보드에서 설정):
   - **`ADMIN_TOKEN`**: 관리자 API 필수.
   - **`JAEGUN_PROJECT_ROOT`**: Dockerfile 기본값은 `/app` (보통 추가 설정 불필요).
   - **`CORS_ORIGINS`**: 배포된 사이트 주소만 허용하려면 `https://xxx.up.railway.app` 형식으로 지정(콤마 구분). 기본 `*`는 개발 편의용입니다.
4. 플랫폼이 주는 **HTTPS URL**로 접속합니다. 대부분 `PORT`를 자동 주입하며, Docker 이미지의 시작 명령이 이를 사용합니다.

### 도메인·HTTPS

호스팅 쪽에서 TLS를 종료하는 경우가 많습니다. 자체 VPS라면 앞단에 Caddy·nginx로 리버스 프록시를 두면 됩니다.

## 권한 모델

- **관리자** (`ADMIN_TOKEN`): **`/admin/...`** 엔드포인트에서 공식 공지·일정·연간·월간 계획의 **생성·수정·삭제**, 게시글 삭제. 헤더: `Authorization: Bearer <토큰>` 또는 `X-Admin-Token: <토큰>`.
- **사용자**: **`/api/board/posts`** 에서만 글 작성(`POST`). 조회는 **`/api/*`** 공개 GET.

## 웹 UI (Branches 스타일)

- **커뮤니티**: **<http://127.0.0.1:8000/community/>** — **「게시판」** 에서 사용자 글 작성, **「더보기」** 에서 **관리자 페이지**(`/admin/`) 링크.
- **관리자 화면**: **<http://127.0.0.1:8000/admin/>** — `static/admin/` (`index.html`, `styles.css`, `app.js`). 토큰 저장 후 탭으로 개요·공지·일정·연간·월간 계획·게시판을 관리(등록·목록·삭제). 수정은 Swagger `PATCH /admin/...` 또는 API 직접 호출.
- 하단 **「계획」** 탭: 연간·월간 조회.
- 정적 파일: `static/community/`, `static/admin/`.
- `GET /` JSON에 `admin_ui`, `admin_api` 필드가 있습니다.

## 데이터

- 기본: 프로젝트 루트 `data/jaegun.db` (SQLite, `.gitignore` 처리).
- `DATABASE_URL`로 Postgres 등으로 바꿀 수 있습니다 (`.env.example`).

## API

루트(`GET /`)는 엔드포인트 안내 JSON을 반환합니다. 상세는 Swagger를 사용하세요.

**공지** — 조회만 `/api`, **쓰기는 `/admin`**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/announcements` | 목록 (`limit`, `offset`) |
| GET | `/api/announcements/{id}` | 단건 |
| POST | `/admin/announcements` | 작성 (관리자 토큰) |
| PATCH | `/admin/announcements/{id}` | 수정 (관리자 토큰) |
| DELETE | `/admin/announcements/{id}` | 삭제 (관리자 토큰) |

**일정** — 조회만 `/api`, **공식 일정 쓰기는 `/admin`**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/events` | 목록 (`limit`, `offset`, `upcoming_only`) |
| GET | `/api/events/{id}` | 단건 |
| POST | `/admin/events` | 작성 (관리자 토큰) |
| PATCH | `/admin/events/{id}` | 수정 (관리자 토큰) |
| DELETE | `/admin/events/{id}` | 삭제 (관리자 토큰) |

**게시판** — 사용자 `POST` 는 `/api`, **삭제는 `/admin`**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/board/posts` | 목록 |
| POST | `/api/board/posts` | 글 작성 (`title`, `body`, `author_name` 선택) |
| GET | `/api/board/posts/{id}` | 단건 |
| DELETE | `/admin/board/posts/{id}` | 삭제 (관리자 토큰) |

**연간·월간 계획** — 조회만 `/api`, **쓰기는 `/admin/plans/...`**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/plans/annual` | 연간 목록 |
| GET | `/api/plans/annual/{year}` | 연간 단건 |
| GET | `/api/plans/monthly?year=` | 월간 목록 |
| GET | `/api/plans/monthly/{year}/{month}` | 월간 단건 |
| POST | `/admin/plans/annual` | 연간 작성 |
| PATCH/DELETE | `/admin/plans/annual/{year}` | 수정·삭제 |
| POST | `/admin/plans/monthly` | 월간 작성 |
| PATCH/DELETE | `/admin/plans/monthly/{year}/{month}` | 수정·삭제 |

기타: `GET /health`

문서: 서버 실행 후 <http://127.0.0.1:8000/docs>

**참고:** `{"detail":"Not Found"}`는 등록되지 않은 경로입니다. 포트가 Jaegun 서버(기본 `8000`)인지 확인하세요.

## 상위 저장소(nohoi)와의 관계

이 폴더는 **별도 Git 저장소**입니다. 투표용 Next.js(`../nohoi`)와는 독립이며, 커뮤니티 화면은 **이 저장소의 `/community/`** 에서 제공합니다.

## 환경 변수

`.env.example` 참고. **`ADMIN_TOKEN`** 은 공식 콘텐츠 수정에 필수입니다. 프로덕션에서는 `CORS_ORIGINS`를 실제 웹 도메인으로 제한하고, DB URL·토큰을 안전하게 관리하세요. Docker·PaaS 배포 시 **`JAEGUN_PROJECT_ROOT=/app`** 로 `static/`·`data/` 경로를 맞춥니다(로컬 개발은 비워 두면 됩니다).

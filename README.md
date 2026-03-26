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

## API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 헬스 체크 |
| GET | `/api/announcements` | 공지 목록 |
| POST | `/api/announcements` | 공지 작성 (MVP, 메모리 저장) |

문서: 서버 실행 후 <http://127.0.0.1:8000/docs>

## 상위 저장소(nohoi)와의 관계

이 폴더는 **별도 Git 저장소**입니다. Next.js 프론트는 `../`(nohoi)에서 두고, API만 이쪽에서 키우거나, 나중에 `NEXT_PUBLIC_API_URL`로 이 서버를 바라보게 연결하면 됩니다.

## 환경 변수

`.env.example` 참고. `CORS_ORIGINS`는 프로덕션에서 반드시 실제 웹 도메인으로 제한하세요.

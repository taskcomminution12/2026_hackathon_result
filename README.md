# 수원대 LMS Sync

수원대학교 LMS(Canvas + LearningX + Xinics)에서 학습 자료를 자동으로 다운로드하고
대시보드에서 보여주며, 과제 마감을 카카오톡으로 알려주는 데스크톱 도구

---

## 한눈에 보기

- 수강 과목 × 주차 자료를 `과목/주차/파일` 구조로 OneDrive 폴더에 자동 정리함
- PDF · ZIP · PPTX · MP4 등 모든 자료 타입 지원함
- Canvas 공지사항 + LearningX 게시판(Q&A 제외) 자료까지 통합함
- 과제·페이지·퀴즈·토론 항목까지 한 트리에 표시, 본문(description) 펼침
- 캘린더에 과제 이용가능 기간(unlock~lock) 을 막대로 표시
- 과제 마감 N일 전 카카오톡으로 자동 알림 발송함 (D-7/3/1/0)
- 자동 동기화 주기 5~30분/실시간 설정 가능, DB에 영구 저장
- 동기화 중 대시보드 UI 자동 갱신 (3초 폴링)
- 과목 페이지에 파일 드래그·드롭하면 해당 주차 자료로 자동 등록
- 디스크에서 지운 파일은 sync 때 DB 에서도 자동 제거
- iPad GoodNotes 자동 백업 → OneDrive → PC 인덱싱까지 자동
- Adminator 톤의 대시보드 + 과목 페이지 + 설정 페이지
- Windows 트레이 앱으로 띄우면 시스템 트레이에 상주
- Canvas 토큰을 UI 설정 페이지에서 직접 입력 / 변경 가능

---

## 기능 상세

### 1. 자료 자동 다운로드
- Canvas API 로 활성 과목 목록 가져옴
- 각 과목마다 LTI launch 로 LearningX 토큰 발급함
- LearningX modules API 에서 주차/자료 메타 받음
- Xinics Commons API 로 다운로드 URL 받아 파일 저장함
- 같은 파일 SHA-256 비교해서 중복 다운 안 함
- 과목들을 순차 처리 (SQLite 잠금 회피)

### 2. 게시판/공지 자료
- Canvas announcements API → 공지사항 + 첨부 → `과목/_공지사항/` 폴더
- LearningX 게시판 API → 글 + 첨부 → `과목/_게시판/{게시판명}/` 폴더
- Q&A 게시판은 자동 제외함

### 3. 과제·페이지·퀴즈 메타
- Canvas 모듈 항목 전체를 트리에 표시 (자료/과제/페이지/퀴즈/토론/링크)
- 과제는 마감/이용가능 시작·끝/배점/설명까지 받아옴
- 행 클릭하면 본문 펼쳐짐
- LMS 원본 페이지로 새 탭 이동 가능

### 4. 캘린더
- FullCalendar 월 뷰
- 과제: `unlock_at ~ lock_at` 기간을 막대 이벤트로 표시 (예: 5/14~5/21 까지 가로 7일 막대)
- 한 시점만 있는 과제도 그 날 하루짜리 막대로 통일

### 5. 카카오톡 알림
- OAuth 2.0 으로 본인 카카오 계정 연결
- 매시 정각마다 임박 과제 점검 (D-7/3/1/0)
- 카카오톡 "나에게 보내기" 로 발송 (본인에게만)
- 같은 과제·같은 D-day 는 한 번만 발송 (중복 방지)

### 6. 자동 폴링
- APScheduler 가 설정 주기마다 자동 sync
- 옵션: **실시간 / 5분 / 10분 / 15분 / 30분**
- 실시간 모드: sync 종료 직후 10초 휴식 후 즉시 재시작
- 설정값 DB 에 영구 저장

### 7. iPad 동기화
- GoodNotes 자동 백업 기능을 OneDrive 폴더로 설정
- OneDrive 가 PC 와 동기화
- watchdog 가 다운로드 폴더 변경 이벤트 감지
- 새 파일 들어오면 활동 피드에 자동 표시

### 8. 과목 페이지 드래그·드롭
- 과목 페이지에서 파일을 윈도우 위로 드래그
- 주차 헤더 위에 놓으면 그 주차로 저장, 빈 공간이면 `_수동자료/` 폴더
- 자동으로 DB 인덱싱 + 페이지 갱신

### 9. 자동 정리
- Sync 끝날 때 디스크에 없는 File 레코드를 DB 에서 제거
- 수동 삭제한 파일이 활동 피드에 계속 남는 문제 해결

### 10. UI 자동 갱신
- 대시보드가 3초마다 `/api/sync/status` 폴링
- 동기화 중 카운터(신규/스킵/실패) 변동 감지 시 화면 자동 새로고침
- 사용자가 아무 동작 안 해도 진행 상황 실시간 반영

### 11. 대시보드 + 과목 페이지
- KPI 카드: 수강 과목, 저장 자료, 임박 과제
- 차트: 주차별 자료 누적 (Chart.js), 과제 마감 분포 도넛
- 임박 과제 테이블 (D-day 뱃지)
- 활동 피드 (최근 다운로드)
- 캘린더 (과제 마감 자동 표시)
- 과목 페이지: 주차별 자료 + 게시판 + 공지 + 과제 + 드래그·드롭 영역

### 12. 설정 페이지
- **Canvas 토큰 직접 입력** (눈 아이콘으로 보기/숨기기 토글, 즉시 반영)
- **다운로드 폴더** 변경 (DB 저장, 다음 sync 부터 적용)
- **카카오톡** 연결/테스트/연결 해제
- **자동 동기화 주기** 변경 (실시간/5/10/15/30분, DB 저장)
- **동기화 이력** 표 (최근 20건, 신규/스킵/실패 카운트)

### 13. 트레이 앱
- pystray 로 시스템 트레이에 상주
- 우클릭 메뉴: 대시보드 / 설정 / 다운로드 폴더 / 지금 동기화 / 종료
- 실행 시 대시보드 자동 오픈

### 14. UTC 시각 직렬화
- SQLite 는 timezone 정보를 잃어버리는 한계가 있어,
  API 응답 직전에 `utc_iso()` 헬퍼로 `+00:00` 명시
- 브라우저가 로컬(KST) 로 정확히 변환

---

## 폴더 구조

```
suwon-univercity-project/
├── README.md                       이 문서
├── downloads/                      자료가 떨어지는 곳 (.gitignore)
│   ├── 자바 001분반/
│   │   ├── 01주차/0장_자바설치.pdf
│   │   ├── _공지사항/...
│   │   ├── _게시판/수업자료/...
│   │   └── _수동자료/...           드래그·드롭한 파일
│   └── ...
├── backend/
│   ├── lms_sync.db                 SQLite (메타 + 설정)
│   ├── suwon-lms-sync.spec         PyInstaller 빌드 spec
│   ├── build-exe.ps1               .exe 빌드 자동화
│   └── app/
│       ├── .env                    실제 설정 (커밋 X)
│       ├── .env.example            템플릿
│       ├── requirements.txt
│       ├── main.py                 FastAPI 엔트리
│       ├── tray.py                 Windows 트레이 앱
│       ├── config.py
│       ├── db.py                   엔진 + auto migrate (WAL 모드)
│       ├── models/
│       │   ├── subject.py
│       │   ├── week.py
│       │   ├── week_item.py        모듈 항목 통합
│       │   ├── file.py             다운 파일 (source: module/announcement/board/manual)
│       │   ├── assignment.py       unlock_at / due_at / lock_at
│       │   ├── announcement.py
│       │   ├── board_post.py
│       │   ├── kakao_token.py
│       │   ├── notif_log.py
│       │   ├── app_setting.py      key/value 런타임 설정
│       │   └── sync_log.py
│       ├── routers/
│       │   ├── _serial.py          UTC datetime 직렬화 헬퍼
│       │   ├── me.py
│       │   ├── courses.py          /api/courses, /tree, /upload(드롭)
│       │   ├── files.py
│       │   ├── assignments.py
│       │   ├── announcements.py
│       │   ├── sync.py             /sync, /scheduler, /watcher
│       │   ├── kakao.py
│       │   └── settings.py
│       └── services/
│           ├── canvas.py           Canvas REST
│           ├── lti.py              LTI launch → xn_api_token
│           ├── learningx.py        modules + commons API
│           ├── learningx_board.py  게시판 API
│           ├── xinics.py           Xinics 다운로더
│           ├── filename.py         경로 안전화 + 색상 배정
│           ├── sync.py             전체 동기화 (순차 + 카운터 + 정리)
│           ├── scheduler.py        APScheduler (자동 폴링 + 알림)
│           ├── watcher.py          watchdog
│           ├── kakao.py            OAuth + 메모
│           ├── notify.py           임박 과제 알림 잡
│           └── app_settings.py     DB 기반 런타임 설정 (토큰/폴더 등)
└── frontend/
    └── prototype/
        ├── index.html              대시보드
        ├── course.html             과목 상세
        ├── settings.html           설정
        ├── styles.css              Adminator 토큰 시스템
        ├── shared.js               공통 (사이드바, fetch, toast)
        ├── dashboard.js            + 3초 폴링 자동 갱신
        ├── course.js               + 드래그·드롭 업로드
        └── settings.js
```

---

## 서버 시작 / 종료

### 시작 — 일반 (개발 모드)

PowerShell 새 창 열고:

```powershell
cd c:\Users\User\Downloads\suwon-univercity-project\backend
.\app\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8765
```

띄워지면 브라우저에서:
- 대시보드: http://127.0.0.1:8765/dashboard
- 과목 페이지: http://127.0.0.1:8765/course/{과목ID}
- 설정: http://127.0.0.1:8765/settings

### 시작 — 트레이 앱

```powershell
cd c:\Users\User\Downloads\suwon-univercity-project\backend
.\app\.venv\Scripts\python.exe -m app.tray
```

### 종료

- 일반 모드: 서버 띄운 PowerShell 창에서 **Ctrl+C** 또는 창 닫기
- 트레이 앱: 트레이 아이콘 우클릭 → **종료**
- 모두 강제 종료: PowerShell 에서 `Get-Process python* | Stop-Process -Force`

### .exe 빌드 (배포)

PowerShell 에서 한 줄로:

```powershell
cd c:\Users\User\Downloads\suwon-univercity-project\backend
.\build-exe.ps1
```

스크립트가 자동으로:
1. 이전 `build/` · `dist/` 정리
2. PyInstaller 로 `.exe` 빌드 (3~5분)
3. 결과 폴더에서 개인 데이터(`.env`, `lms_sync.db*`, 다운로드 폴더) 제외
4. `.env.example` 만 동봉

결과: `backend/dist/suwon-lms-sync/suwon-lms-sync.exe`

배포 시 `dist/suwon-lms-sync/` 폴더 통째로 zip 으로 묶어서 전달.
받는 사람은 zip 풀고 `.exe` 더블클릭만 하면 트레이에 상주 + 대시보드 자동 오픈됨.

> 빌드 전 점검할 것:
> - `backend/lms_sync.db` 와 `downloads/` 는 빌드 결과에 포함되지 않음 (스크립트가 보장)
> - 본인 PC 의 `.env` 도 빌드 결과에 포함 안 됨
> - 받는 사용자가 처음 실행 시 설정 페이지에서 Canvas 토큰만 입력하면 됨

---

## 초기 설정 (소스 빌드용 — `.exe` 받은 사용자는 스킵)

### 1. 가상환경 + 의존성

```powershell
cd backend\app
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Canvas 토큰

서버 띄우고 설정 페이지(http://127.0.0.1:8765/settings) 에서 직접 입력.
DB(`app_setting` 테이블)에 저장되며 재시작 시 자동 로드됨.

---

## 주요 API

| 엔드포인트 | 메서드 | 설명 |
|---|---|---|
| `/api/me` | GET | Canvas 인증 + 학번 |
| `/api/courses` | GET | 과목 목록 + 자료 카운트 |
| `/api/courses/{id}/tree` | GET | 과목 자료/과제/공지/게시판 통합 |
| `/api/courses/{id}/upload` | POST | 드래그·드롭 파일 업로드 (multipart) |
| `/api/sync` | POST | 즉시 동기화 |
| `/api/sync/status` | GET | 마지막 sync 상태 (UI 폴링) |
| `/api/sync/history` | GET | 동기화 이력 |
| `/api/sync/scheduler` | GET/PUT | 자동 폴링 주기 (0=실시간) |
| `/api/sync/watcher` | GET | watchdog 최근 이벤트 |
| `/api/files` | GET | 최근 다운 파일 |
| `/api/files/stats` | GET | 차트용 통계 |
| `/api/files/{id}/open` | POST | 탐색기에서 파일 위치 열기 |
| `/api/files/open-root` | POST | 다운로드 루트 폴더 열기 |
| `/api/assignments/upcoming` | GET | 임박 과제 (unlock_at/lock_at 포함) |
| `/api/announcements` | GET | 공지사항 |
| `/api/settings` | GET/PUT | Canvas 토큰 + 다운로드 폴더 (UI 변경) |
| `/api/kakao/login` | GET | 카카오 OAuth 시작 |
| `/api/kakao/status` | GET | 연결 여부 |
| `/api/kakao/test` | POST | 테스트 메시지 |
| `/api/kakao/notify-now` | POST | 임박 과제 알림 즉시 발송 |
| `/api/kakao/disconnect` | POST | 카카오 연결 해제 |

---

## 기술 스택

**백엔드**
- Python 3.11
- FastAPI + Uvicorn
- SQLModel + SQLite (WAL 모드)
- httpx (Canvas / LearningX / Xinics REST)
- APScheduler (자동 폴링)
- watchdog (폴더 감시)
- pystray + Pillow (트레이 앱)
- PyInstaller (.exe 빌드)

**프론트엔드**
- Vanilla HTML / CSS / JS (빌드 도구 없음)
- Chart.js (차트)
- FullCalendar (캘린더, 기간 막대 이벤트)
- Lucide (아이콘)
- Inter / Inter Tight / JetBrains Mono (Google Fonts)

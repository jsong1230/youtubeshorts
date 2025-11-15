# 프로젝트 구조

## 📁 폴더 구조

```
youtubeshorts/
├── main.py                      # 메인 실행 파일
├── config.py                    # 설정 관리 (환경 변수 로드)
├── requirements.txt             # Python 의존성
├── .env                        # 환경 변수 (생성 필요)
├── README.md                    # 프로젝트 메인 문서
│
├── src/                        # 소스코드
│   ├── __init__.py
│   ├── generators/             # 영상 생성 모듈
│   │   ├── __init__.py
│   │   └── video_generator.py  # AI 영상 생성
│   ├── uploaders/              # 업로드 모듈
│   │   ├── __init__.py
│   │   └── youtube_uploader.py # YouTube API 업로드
│   ├── analytics/              # 분석 모듈
│   │   ├── __init__.py
│   │   └── monetization.py    # 수익화 추적 및 분석
│   ├── pipeline/               # 파이프라인 모듈
│   │   ├── __init__.py
│   │   ├── bot.py              # 메인 봇 클래스
│   │   ├── database.py         # SQLite 데이터베이스
│   │   └── tts_engine.py       # TTS 엔진 추상화
│   └── utils/                  # 유틸리티
│       ├── __init__.py
│       └── create_client_secrets.py
│
├── docs/                       # 문서
│   ├── API_SETUP.md            # OpenAI API 설정 가이드
│   ├── AUTO_START_GUIDE.md     # 자동 시작 가이드
│   ├── CONTENT_OPTIMIZATION.md # 콘텐츠 최적화 전략
│   ├── COPYRIGHT_SAFETY.md     # 저작권 안전 가이드
│   ├── SETUP_GUIDE.md          # YouTube API 설정 가이드
│   ├── PROJECT_STRUCTURE.md    # 프로젝트 구조 문서 (이 파일)
│   └── 3month_roadmap.md       # 3개월 수익화 로드맵
│
├── templates/                  # 템플릿
│   └── copyright_free_templates.json  # 저작권 0% AI 쇼츠 템플릿 10종
│
├── prompts/                    # 프롬프트
│   └── viral_formats.txt       # 조회수 잘 터지는 포맷 프롬프트 20개
│
├── scripts/                    # 스크립트
│   ├── start_daemon.sh         # 데몬 시작 스크립트
│   └── com.youtubeshorts.bot.plist  # macOS LaunchAgent 설정
│
├── data/                       # 데이터 파일
│   ├── videos.db               # SQLite 데이터베이스
│   └── monetization_data.json  # 수익화 데이터
│
├── output/                     # 출력 파일
│   ├── videos/                 # 생성된 영상
│   ├── thumbnails/            # 썸네일
│   └── temp/                  # 임시 파일
│
├── token.json                  # YouTube 인증 토큰 (자동 생성)
└── client_secrets.json         # Google OAuth 설정 (생성 필요)
```

## 📂 주요 폴더 설명

### `src/` - 소스코드
- **generators/**: AI를 활용한 영상 생성 로직
- **uploaders/**: YouTube API를 통한 영상 업로드
- **analytics/**: 수익화 추적 및 통계 분석
- **pipeline/**: 전체 파이프라인 관리 (봇, 데이터베이스, TTS)
- **utils/**: 유틸리티 함수들

### `docs/` - 문서
- 모든 가이드 문서와 로드맵
- 설정 방법, 최적화 전략, 저작권 안전 가이드 등

### `templates/` - 템플릿
- 저작권 0% AI 쇼츠 템플릿 10종
- JSON 형식으로 구조화된 템플릿 데이터

### `prompts/` - 프롬프트
- 조회수 잘 터지는 포맷 프롬프트 20개
- AI 스크립트 생성에 사용되는 프롬프트 모음

### `scripts/` - 스크립트
- 자동 실행을 위한 스크립트 파일들
- macOS LaunchAgent 설정 파일

### `data/` - 데이터
- SQLite 데이터베이스 (영상 정보 저장)
- 수익화 추적 데이터 (JSON)

### `output/` - 출력
- 생성된 영상, 썸네일, 임시 파일 저장

## 🔄 리팩토링 변경사항

### 이전 구조
- 모든 문서가 루트에 산재
- 스크립트 파일이 루트에 위치
- 데이터 파일이 루트에 위치

### 개선된 구조
- ✅ 문서를 `docs/` 폴더로 통합
- ✅ 스크립트를 `scripts/` 폴더로 이동
- ✅ 데이터 파일을 `data/` 폴더로 이동
- ✅ 템플릿과 프롬프트 폴더 추가
- ✅ 더 명확한 폴더 구조로 유지보수성 향상

## 📝 파일 경로 참고

### 설정 파일
- `config.py`: 프로젝트 루트에 위치 (import 경로 유지)
- `.env`: 프로젝트 루트에 위치 (환경 변수)

### 데이터베이스
- `data/videos.db`: SQLite 데이터베이스
- `data/monetization_data.json`: 수익화 데이터

### 출력 파일
- `output/videos/`: 생성된 영상
- `output/thumbnails/`: 썸네일
- `output/temp/`: 임시 파일

## 🚀 사용 방법

### 영상 생성 및 업로드
```bash
python main.py upload [주제]
```

### 템플릿 사용
템플릿은 `templates/copyright_free_templates.json`에서 확인할 수 있습니다.

### 프롬프트 사용
프롬프트는 `prompts/viral_formats.txt`에서 확인할 수 있으며,
`video_generator.py`의 `performance_prompt` 파라미터로 전달할 수 있습니다.

### 문서 참고
모든 가이드 문서는 `docs/` 폴더에서 확인할 수 있습니다.


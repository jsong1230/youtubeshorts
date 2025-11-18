# YouTube Shorts 자동 업로드 봇

AI로 자동 생성된 YouTube Shorts 영상을 매일 자동으로 업로드하고 수익화를 추적하는 봇입니다.

## 🎯 프로젝트 목표

- **하루 1개 업로드 (퀄리티 중심)**: 매일 하나의 고품질 영상을 생성하여 업로드
- **퀄리티 우선 전략**: 양보다 질에 집중하여 시청자 참여도와 수익을 극대화
- **3개월 후 수익화**: 꾸준한 업로드를 통한 YouTube 파트너 프로그램 가입
- **월 $100~500 수익 목표**: 지속적인 고품질 콘텐츠 제작을 통한 수익 창출

## ✨ 주요 기능

### 1. AI 영상 자동 생성
- **AI API 지원**: OpenAI GPT 또는 Claude API를 활용한 고품질 스크립트 생성
- **API 자동 선택**: 설정에 따라 OpenAI 또는 Claude API 자동 사용
- **API 폴백**: Claude API 실패 시 자동으로 OpenAI로 전환
- **콘텐츠 타입 최적화**: Hook, 명언, 스토리, 팩트, 짧은 스토리 등 수익화 최적화된 콘텐츠 형태 지원
- **짧고 강한 Hook**: 첫 3초 안에 시청자 관심을 끄는 강력한 Hook 자동 생성
- **자동 길이 조정**: 콘텐츠 타입별 최적 길이 (목표 55초, 최대 60초)
- **한글 음성**: Google TTS 또는 OpenAI TTS를 활용한 자연스러운 한글 음성 생성 (영어 회화 주제 제외)
- **배경 영상/이미지**: Pexels Video API를 활용한 CC0 라이선스 배경 영상 또는 무료 이미지 자동 삽입
- **배경 영상 순차 재생**: 같은 배경 영상이 반복되지 않고 순차적으로 재생되도록 최적화
- **문장별 관련 이미지**: 정적 이미지가 문장과 관련된 이미지를 Pexels/Unsplash에서 자동 다운로드
- **저작권 안전**: 100% 저작권 안전한 콘텐츠 (CC0, Unsplash License, Pixabay License)
- **동기화**: 음성과 영상이 정확히 일치하도록 자동 동기화

### 2. YouTube 자동 업로드
- **YouTube Data API v3**: 안정적인 API를 통한 자동 업로드
- **한글 설명 자동 생성**: 상세하고 친절한 한글 설명 자동 작성
- **최적화된 태그**: 검색 최적화를 위한 한글/영문 태그 자동 설정
- **공개 설정**: 즉시 공개 또는 예약 업로드 가능

### 3. 수익화 추적 및 분석
- **실시간 통계**: 조회수, 좋아요, 댓글 수 자동 추적
- **수익 예측**: CPM 기반 예상 수익 자동 계산
- **진행 상황 분석**: 수익화까지 남은 일수 및 목표 달성률 표시
- **월별 리포트**: 월별 수익 추이 및 통계 분석

### 4. 스케줄링
- **자동 스케줄러**: 매일 지정된 시간에 1개의 고품질 영상을 생성하여 업로드
- **퀄리티 중심 생성**: 6가지 콘텐츠 타입(HOOK, QUOTE, STORY, FACT, SHORT_STORY, AUTO) 중 최적의 타입을 선택하여 고품질 영상 생성
- **계절별 주제 선택**: 현재 날짜를 기반으로 계절에 맞는 주제를 우선적으로 선택 (50% 확률)
- **백그라운드 실행**: 서버나 컴퓨터가 켜져 있는 동안 자동 실행
- **macOS LaunchAgent 지원**: 재부팅 후에도 자동 시작

## 📋 사전 요구사항

### 필수 소프트웨어

1. **Python 3.8 이상**
   ```bash
   python3 --version
   ```

2. **FFmpeg** (영상 처리용)
   ```bash
   # macOS
   brew install ffmpeg
   
   # Ubuntu/Debian
   sudo apt-get install ffmpeg
   
   # Windows
   # https://ffmpeg.org/download.html 에서 다운로드
   ```

### 필수 API 키

1. **YouTube Data API v3**
   - Google Cloud Console에서 프로젝트 생성
   - YouTube Data API v3 활성화
   - OAuth 2.0 클라이언트 ID 생성

2. **AI API (선택사항)**
   - **OpenAI API**: OpenAI Platform에서 API 키 발급: https://platform.openai.com/
     - GPT-4o-mini, GPT-4o, GPT-3.5-turbo 모델 사용 가능
     - **모델 접근 권한**: Settings > Model access에서 사용할 모델 활성화 필요
   - **Claude API**: Anthropic Platform에서 API 키 발급: https://console.anthropic.com/
     - Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Sonnet 모델 사용 가능
   - **API 제공자 선택**: `.env` 파일에서 `AI_API_PROVIDER=openai` 또는 `AI_API_PROVIDER=claude` 설정
   - 자세한 내용은 [API_SETUP.md](./docs/API_SETUP.md) 참고

3. **이미지 API (선택사항)**
   - Pexels API: https://www.pexels.com/api/ (무료)
   - Unsplash API: https://unsplash.com/developers (무료)

## 🚀 설치 및 설정

### 1. 저장소 클론 및 의존성 설치

```bash
# 저장소 클론 (또는 다운로드)
cd youtubeshorts

# Python 가상환경 생성 (권장)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 입력하세요:

> 💡 **참고**: 자세한 설정 방법은 [docs/SETUP_GUIDE.md](./docs/SETUP_GUIDE.md)와 [docs/API_SETUP.md](./docs/API_SETUP.md)를 참고하세요.

```env
# YouTube API 설정
YOUTUBE_CLIENT_ID=your_client_id_here
YOUTUBE_CLIENT_SECRET=your_client_secret_here
YOUTUBE_REFRESH_TOKEN=your_refresh_token_here

# AI API 설정 (AI 영상 생성용)
# OpenAI 또는 Claude 중 하나 이상 설정 필요
OPENAI_API_KEY=your_openai_api_key_here
CLAUDE_API_KEY=your_claude_api_key_here
# AI API 제공자 선택 (openai 또는 claude, 기본값: openai)
AI_API_PROVIDER=claude

# 이미지 API (선택사항)
PEXELS_API_KEY=your_pexels_api_key_here
UNSPLASH_ACCESS_KEY=your_unsplash_access_key_here

# 업로드 스케줄 설정
UPLOAD_SCHEDULE_TIME=09:00  # 매일 이 시간에 1개의 고품질 영상 생성 및 업로드
UPLOAD_TIMEZONE=Asia/Seoul

# 영상 기본 설정 (선택사항)
DEFAULT_DESCRIPTION=AI로 자동 생성된 YouTube Shorts 영상입니다. 유용한 정보와 팁을 매일 공유합니다. 구독과 좋아요 부탁드립니다!
DEFAULT_TAGS=shorts,쇼츠,ai,인공지능,자동생성,유용한정보,팁,라이프스타일
```

### 3. YouTube API 인증 설정

자세한 설정 방법은 [docs/SETUP_GUIDE.md](./docs/SETUP_GUIDE.md)를 참고하세요.

#### Google Cloud Console 설정

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. **API 및 서비스** > **라이브러리**에서 "YouTube Data API v3" 검색 후 활성화
4. **사용자 인증 정보** > **OAuth 동의 화면** 설정
   - 사용자 유형: 외부 선택
   - 앱 이름, 사용자 지원 이메일 등 입력
5. **사용자 인증 정보** > **OAuth 2.0 클라이언트 ID** 생성
   - 애플리케이션 유형: **데스크톱 앱** 선택
   - 이름: 원하는 이름 입력
   - 승인된 리디렉션 URI: `http://localhost:8080/` 추가
6. 클라이언트 ID와 시크릿을 `.env` 파일에 입력

#### 인증 토큰 생성

```bash
# 첫 실행 시 브라우저에서 인증 진행
python main.py upload

# 브라우저가 자동으로 열리고 Google 계정으로 로그인
# 권한 승인 후 token.json 파일이 자동 생성됨
```

### 4. AI API 키 발급

#### OpenAI API (선택사항)
1. [OpenAI Platform](https://platform.openai.com/) 접속
2. 계정 생성 또는 로그인
3. **API Keys** 메뉴에서 새 API 키 생성
4. `.env` 파일에 `OPENAI_API_KEY` 설정

#### Claude API (선택사항)
1. [Anthropic Platform](https://console.anthropic.com/) 접속
2. 계정 생성 또는 로그인
3. **API Keys** 메뉴에서 새 API 키 생성
4. `.env` 파일에 `CLAUDE_API_KEY` 설정
5. `.env` 파일에 `AI_API_PROVIDER=claude` 설정 (Claude를 우선 사용하려면)

**참고**: OpenAI와 Claude 중 하나 이상 설정하면 됩니다. 둘 다 설정하면 `AI_API_PROVIDER` 설정에 따라 우선 사용할 API가 결정됩니다.

## 📁 프로젝트 구조

```
youtubeshorts/
├── main.py                      # 메인 실행 파일
├── config.py                    # 설정 관리 (환경 변수 로드)
├── requirements.txt             # Python 의존성
├── .env                         # 환경 변수 (생성 필요)
├── README.md                    # 프로젝트 메인 문서
│
├── src/                        # 소스코드
│   ├── generators/             # 영상 생성 모듈
│   │   └── video_generator.py
│   ├── uploaders/              # 업로드 모듈
│   │   └── youtube_uploader.py
│   ├── analytics/              # 분석 모듈
│   │   └── monetization.py
│   ├── pipeline/               # 파이프라인 모듈
│   │   ├── bot.py              # 메인 봇 클래스
│   │   ├── database.py         # SQLite 데이터베이스
│   │   └── tts_engine.py       # TTS 엔진 추상화
│   └── utils/                  # 유틸리티
│       └── create_client_secrets.py
│
├── docs/                       # 문서
│   ├── API_SETUP.md            # OpenAI API 설정 가이드
│   ├── AUTO_START_GUIDE.md     # 자동 시작 가이드
│   ├── CONTENT_OPTIMIZATION.md # 콘텐츠 최적화 전략
│   ├── COPYRIGHT_SAFETY.md     # 저작권 안전 가이드
│   ├── SETUP_GUIDE.md          # YouTube API 설정 가이드
│   ├── PROJECT_STRUCTURE.md    # 프로젝트 구조 문서
│   └── 3month_roadmap.md       # 3개월 수익화 로드맵
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

자세한 프로젝트 구조는 [docs/PROJECT_STRUCTURE.md](./docs/PROJECT_STRUCTURE.md)를 참고하세요.

## 📖 사용법

### 영상 생성만 (업로드 없음)

```bash
# 주제 자동 생성
python main.py test

# 특정 주제 지정
python main.py test "건강한 아침 루틴"
```

생성된 영상은 `output/videos/` 디렉토리에 저장됩니다.

### 즉시 업로드

```bash
# 주제 자동 생성 후 즉시 업로드
python main.py upload

# 특정 주제 지정 후 즉시 업로드
python main.py upload "생산성 팁"
```

### 통계 업데이트 및 리포트

```bash
# 모든 영상 통계 업데이트
python main.py stats

# 리포트만 출력
python main.py report
```

### 자동 업로드 스케줄러 시작

```bash
# 스케줄러 시작 (하루 1개 고품질 영상 자동 업로드)
python main.py schedule
```

스케줄러는 매일 지정된 시간(기본값: 09:00, 한국 시간)에 1개의 고품질 영상을 생성하여 업로드합니다.
6가지 콘텐츠 타입(HOOK, QUOTE, STORY, FACT, SHORT_STORY, AUTO) 중 최적의 타입을 선택하고, 계절에 맞는 주제를 우선적으로 선택하여 퀄리티 높은 영상을 제작합니다.

#### 백그라운드 실행 방법

**방법 1: nohup 사용 (간단)**
```bash
nohup python main.py schedule > output/bot.log 2>&1 &

# 로그 확인
tail -f output/bot.log

# 종료
pkill -f "main.py schedule"
```

**방법 2: macOS LaunchAgent (재부팅 후에도 자동 시작)**
```bash
# LaunchAgent 파일 복사
cp com.youtubeshorts.bot.plist ~/Library/LaunchAgents/

# 서비스 시작
launchctl load ~/Library/LaunchAgents/com.youtubeshorts.bot.plist

# 상태 확인
launchctl list | grep youtubeshorts

# 로그 확인
tail -f output/bot.log

# 중지
launchctl unload ~/Library/LaunchAgents/com.youtubeshorts.bot.plist
```

자세한 내용은 [docs/AUTO_START_GUIDE.md](./docs/AUTO_START_GUIDE.md) 파일을 참고하세요.

## 📊 수익화 추적

봇은 자동으로 다음 정보를 추적합니다:

- **총 업로드 영상 수**: 현재까지 업로드한 영상 개수
- **총 조회수**: 모든 영상의 누적 조회수
- **좋아요 및 댓글 수**: 커뮤니티 참여도 추적
- **영상별 예상 수익**: 각 영상의 예상 수익 계산
- **월별 수익 추이**: 월별 수익 변화 추적
- **수익화까지 남은 일수**: YouTube 파트너 프로그램 가입까지 남은 일수
- **목표 달성 여부**: 월 $100~500 목표 달성률 표시

### 수익 계산 방식

- **CPM (Cost Per Mille)**: $1.00 per 1,000 views (기본값)
- YouTube Shorts는 일반적으로 낮은 CPM을 가짐
- **월 $100 목표**: 약 100,000 뷰 필요
- **월 $500 목표**: 약 500,000 뷰 필요

실제 CPM은 채널, 주제, 지역 등에 따라 달라질 수 있습니다.

## 📁 프로젝트 구조

```
youtubeshorts/
├── main.py                      # 메인 실행 파일
├── config.py                    # 설정 관리 (환경 변수 로드)
├── ai_video_generator.py        # AI 영상 생성 (스크립트, 음성, 이미지)
├── youtube_uploader.py          # YouTube API 업로드
├── monetization.py              # 수익화 추적 및 분석
├── create_client_secrets.py     # client_secrets.json 생성 도우미
├── requirements.txt             # Python 의존성
├── .env                         # 환경 변수 (생성 필요)
├── client_secrets.json          # YouTube API 인증 (생성 필요)
├── token.json                   # 인증 토큰 (자동 생성)
├── monetization_data.json       # 수익화 데이터 (자동 생성)
├── com.youtubeshorts.bot.plist  # macOS LaunchAgent 설정
├── start_daemon.sh              # 데몬 시작 스크립트
├── AUTO_START_GUIDE.md          # 자동 시작 가이드
├── SETUP_GUIDE.md               # 상세 설정 가이드
└── output/                       # 생성된 파일 저장
    ├── videos/                  # 생성된 영상 파일
    ├── thumbnails/              # 썸네일 (향후 지원)
    ├── temp/                    # 임시 파일
    └── bot.log                  # 봇 실행 로그
```

## ⚙️ 설정 커스터마이징

### 영상 설정 (`config.py`)

- **영상 길이**: 목표 55초 (최대 60초, YouTube Shorts 제한)
- **해상도**: 1080x1920 (세로형, YouTube Shorts 최적화)
- **FPS**: 30fps (YouTube 권장)

### 업로드 설정 (`.env`)

- **업로드 시간**: `UPLOAD_SCHEDULE_TIME=09:00` (24시간 형식, 이 시간에 1개의 고품질 영상 생성)
- **타임존**: `UPLOAD_TIMEZONE=Asia/Seoul`
- **기본 설명**: `DEFAULT_DESCRIPTION` (한글 설명)
- **기본 태그**: `DEFAULT_TAGS` (쉼표로 구분)

### 영상 생성 설정

영상은 다음과 같은 특징을 가집니다:

- **자막 포함**: 모든 문장에 자막 자동 생성 및 오버레이
- **배경 영상/이미지**: 문장 내용과 연관된 배경 영상 또는 이미지 자동 삽입
- **배경 영상 순차 재생**: 같은 배경 영상이 반복되지 않고 순차적으로 재생
- **문장별 관련 이미지**: 정적 이미지가 문장과 관련된 이미지를 Pexels/Unsplash에서 자동 다운로드
- **자연스러운 음성**: Google TTS 또는 OpenAI TTS를 활용한 한글 음성 (영어 회화 주제 제외)
- **정확한 동기화**: 음성과 영상이 정확히 일치하며, 오디오 클립과 비디오 클립이 완벽하게 싱크
- **55초 목표**: 충분한 내용을 담은 55초 분량 영상 생성

## ⚠️ 주의사항

### YouTube 정책 준수

1. **자동 업로드 정책**
   - YouTube의 자동 업로드 정책을 반드시 확인하세요
   - 저작권 및 커뮤니티 가이드라인 준수 필수
   - 스팸성 콘텐츠 업로드 금지

2. **수익화 요구사항**
   - YouTube 파트너 프로그램 가입 필요
   - **일반 채널**: 1,000명 구독자 + 4,000시간 시청 시간
   - **Shorts 전용**: 1,000명 구독자 + 1,000만 Shorts 조회수 (90일 내)
   - 3개월 후 수익화는 예상 시점이며, 실제 달성 시점은 다를 수 있습니다

3. **API 할당량**
   - **YouTube Data API v3**: 일일 할당량 확인 필요 (기본 10,000 units/day)
   - **OpenAI API**: 사용량에 따른 비용 발생 (GPT-4o-mini 권장)
   - **이미지 API**: Pexels, Unsplash는 무료이지만 일일 제한 확인 필요

### 기술적 주의사항

1. **디스크 공간**: 영상 생성 시 충분한 디스크 공간 필요
2. **인터넷 연결**: 안정적인 인터넷 연결 필수
3. **컴퓨터 전원**: 자동 업로드를 위해서는 컴퓨터가 켜져 있어야 함

## 🔧 문제 해결

### FFmpeg 오류

```bash
# FFmpeg 설치 확인
ffmpeg -version

# 설치되지 않은 경우
brew install ffmpeg  # macOS
sudo apt-get install ffmpeg  # Ubuntu/Debian
```

### 인증 오류

```bash
# token.json 삭제 후 재인증
rm token.json
python main.py upload

# client_secrets.json 확인
# 파일이 올바른 위치에 있는지 확인
```

### 영상 생성 실패

1. **AI API 키 확인**
   ```bash
   # .env 파일에서 OPENAI_API_KEY 또는 CLAUDE_API_KEY 확인
   # AI_API_PROVIDER 설정 확인 (openai 또는 claude)
   ```

2. **디스크 공간 확인**
   ```bash
   df -h  # macOS/Linux
   ```

3. **임시 디렉토리 권한 확인**
   ```bash
   ls -la output/temp/
   ```

### 업로드 실패

1. **YouTube API 할당량 확인**
   - Google Cloud Console에서 할당량 확인
   - 일일 할당량 초과 시 다음 날까지 대기

2. **인증 토큰 만료**
   ```bash
   # token.json 삭제 후 재인증
   rm token.json
   python main.py upload
   ```

## 📈 성공 전략

### 1. 일관성 유지
- 매일 정해진 시간에 업로드
- 꾸준한 콘텐츠 제작으로 알고리즘 신뢰도 향상

### 2. 주제 다양화
- 다양한 주제로 영상 생성하여 다양한 관심사 타겟팅
- 인기 주제와 트렌드 파악

### 3. 최적화
- 제목, 설명, 태그 최적화로 검색 노출 증가
- 썸네일 최적화 (향후 지원 예정)

### 4. 커뮤니티 구축
- 댓글에 답변하고 커뮤니티와 상호작용
- 시청자 요청 주제 반영

### 5. 데이터 분석
- 통계를 통해 인기 주제 파악
- 조회수, 참여도가 높은 영상 분석

## 🛠️ 기술 스택

- **Python 3.8+**: 메인 프로그래밍 언어
- **AI API**: OpenAI GPT 또는 Claude API를 활용한 스크립트 생성
- **OpenAI TTS**: 음성 생성 (선택사항)
- **Google TTS (gTTS)**: 한글 음성 생성 (대체 옵션)
- **MoviePy**: 영상 편집 및 합성
- **PIL (Pillow)**: 이미지 처리
- **YouTube Data API v3**: 영상 업로드 및 통계 조회
- **Pexels Video API**: CC0 라이선스 배경 영상 다운로드
- **Pexels/Unsplash/Pixabay API**: 무료 라이선스 이미지 검색

## 🔒 저작권 안전성

이 프로젝트는 **100% 저작권 안전한 콘텐츠**를 생성합니다:

- ✅ **스크립트**: AI 생성 (본인 소유)
- ✅ **음성**: TTS 생성 (본인 소유)
- ✅ **배경 영상**: Pexels Video (CC0 라이선스)
- ✅ **배경 이미지**: Pexels/Unsplash/Pixabay (무료 라이선스)

자세한 내용은 [docs/COPYRIGHT_SAFETY.md](./docs/COPYRIGHT_SAFETY.md)를 참고하세요.

## 🎯 콘텐츠 최적화

이 프로젝트는 **수익화 최적화된 콘텐츠 형태**를 지원합니다:

- ✅ **Hook 영상**: 한국어 속담/관용어 한 문장 학습 (55초)
- ✅ **명언/지식**: AI·비즈니스·명언·지식 한 줄 (55초)
- ✅ **스토리텔링**: 심리/역사/부자습관 스토리 (55초)
- ✅ **팩트 기반**: 숏폼 팩트 영상 (55초)
- ✅ **짧은 스토리**: AI 이미지 기반 짧은 스토리 (55초)

### 주제 카테고리

모든 콘텐츠 타입은 다음 카테고리의 주제를 포함합니다:

- 🌤 **계절**: 봄/여름/가을/겨울에 맞는 실용적인 주제
- 🏠 **생활**: 집 정리, 냉장고 관리, 옷장 정리 등 일상 생활 팁
- 🚗 **자동차**: 자동차 점검, 유지보수, 계절별 관리
- 💰 **재테크**: 돈 관리, 투자, 자산 형성, 경제적 자유
- 🧠 **자기계발**: 루틴, 습관, 성공 마인드, 인생 교훈

### 계절별 주제 선택

시스템은 현재 날짜를 기반으로 계절을 판단하고, 계절에 맞는 주제를 우선적으로 선택합니다 (50% 확률):

- **봄 (3-5월)**: 정리, 옷장 정리, 환절기 대비
- **여름 (6-8월)**: 전기요금 절약, 장마철 곰팡이, 습기 관리
- **가을 (9-11월)**: 환절기 정리, 겨울 준비, 옷장 정리
- **겨울 (12-2월)**: 난방비 절약, 자동차 점검, 겨울 대비

**장점**:
- 저작권 위험 없음
- 짧아서 Click-Through Rate 좋음
- 조회수 폭발 확률 높음
- 계절에 맞는 실용적인 콘텐츠로 시청자 관심도 향상

자세한 내용은 [docs/CONTENT_OPTIMIZATION.md](./docs/CONTENT_OPTIMIZATION.md)를 참고하세요.

## 📚 추가 리소스

### 로드맵
- **3개월 수익화 도달 로드맵**: [docs/3month_roadmap.md](./docs/3month_roadmap.md)
- **TTS 개선 가이드**: [docs/TTS_IMPROVEMENT.md](./docs/TTS_IMPROVEMENT.md)

## 📝 라이선스

이 프로젝트는 개인 사용 목적으로 제공됩니다.

## 🤝 기여

버그 리포트 및 기능 제안은 GitHub 이슈로 등록해주세요.

## 📞 지원

문제가 발생하거나 질문이 있으시면:
1. GitHub Issues에 이슈 등록
2. [docs/AUTO_START_GUIDE.md](./docs/AUTO_START_GUIDE.md) 및 [docs/SETUP_GUIDE.md](./docs/SETUP_GUIDE.md) 참고

---

**면책 조항**: 이 도구는 YouTube의 서비스 약관을 준수해야 합니다. 자동 업로드로 인한 계정 정지 등의 책임은 사용자에게 있습니다. API 사용에 따른 비용은 사용자가 부담합니다.

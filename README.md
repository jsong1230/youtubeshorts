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
- **콘텐츠 타입 최적화**: Hook, 명언, 스토리, 팩트, 짧은 스토리, 책 리뷰 등 수익화 최적화된 콘텐츠 형태 지원
- **완주율 최적화**: 콘텐츠 타입별 최적 길이 자동 설정 (Hook/Quote/Fact: 15-30초)
- **트렌드 가중치 시스템**: `TREND_MODE` 활성화 시 2025 글로벌 트렌드(40%) + 계절(25%) + 채널 성과(20%) + 탐색(15%) 가중치로 주제 자동 선정
- **배경 영상/이미지**: Pexels Video API를 활용한 CC0 라이선스 배경 영상 또는 무료 이미지 자동 삽입
  - **품질 점수 시스템**: 해상도, 길이 적합성, 키워드 매칭, 비디오 품질을 종합 평가하여 최적 영상 선택
- **저작권 안전**: 100% 저작권 안전한 콘텐츠 (CC0, Unsplash License, Pixabay License)
- **음성과 영상 동기화**: 자막과 음성이 정확히 일치하도록 자동 동기화
- **썸네일 A/B 테스트**: 자동 변형 생성, 성과 추적 및 최적 썸네일 선택

### 2. YouTube 자동 업로드

- **YouTube Data API v3**: 안정적인 API를 통한 자동 업로드
- **다국어 지원**: 영어/한글 콘텐츠 자동 생성
- **언어 필터링**: 주제 선정 시 한글/영어만 허용, 다른 언어 자동 제외
- **최적화된 태그**: 검색 최적화를 위한 태그 자동 설정
- **비공개 업로드 기본값**: 기본적으로 비공개(private)로 즉시 업로드
- **예약 업로드**: `--public` 플래그로 예약 업로드 모드 사용 가능

### 3. 수익화 추적 및 분석

- **실시간 통계**: 조회수, 좋아요, 댓글 수 자동 추적
- **수익 예측**: CPM 기반 예상 수익 자동 계산
- **진행 상황 분석**: 수익화까지 남은 일수 및 목표 달성률 표시
- **월별 리포트**: 월별 수익 추이 및 통계 분석

### 4. 스케줄링

- **자동 스케줄러**: 매일 지정된 시간에 1개의 고품질 영상을 생성하여 업로드
- **퀄리티 중심 생성**: 9가지 콘텐츠 타입 중 최적의 타입을 선택하여 고품질 영상 생성
- **계절별 주제 선택**: 현재 날짜를 기반으로 계절에 맞는 주제를 우선적으로 선택
- **백그라운드 실행**: 서버나 컴퓨터가 켜져 있는 동안 자동 실행
- **macOS LaunchAgent 지원**: 재부팅 후에도 자동 시작

### 5. 안정성 및 모니터링

- **자동 재시도 로직**: API 호출 실패 시 지수 백오프로 자동 재시도
- **API 할당량 관리**: 실시간 API 사용량 추적 및 rate limiting
- **구조화된 로깅**: 색상 코딩된 콘솔 출력 + 파일 로그 (자동 로테이션)
- **성능 메트릭 추적**: 영상 생성 시간, API 응답 시간, 성공률 등 자동 추적
- **타입 안정성**: Python 타입 힌트 및 Mypy 정적 타입 체크

자세한 내용은 [docs/STABILITY_FEATURES.md](./docs/STABILITY_FEATURES.md)를 참고하세요.

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

2. **AI API** (OpenAI 또는 Claude 중 하나 이상 필요)
   - **OpenAI API**: [OpenAI Platform](https://platform.openai.com/)에서 API 키 발급
   - **Claude API**: [Anthropic Platform](https://console.anthropic.com/)에서 API 키 발급
   - 자세한 내용은 [docs/API_SETUP.md](./docs/API_SETUP.md) 참고

3. **이미지 API** (선택사항)
   - Pexels API: <https://www.pexels.com/api/> (무료)
   - Unsplash API: <https://unsplash.com/developers> (무료)

## 🚀 빠른 시작

### 1. 저장소 클론 및 의존성 설치

```bash
# 저장소 클론
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

```env
# YouTube API 설정
YOUTUBE_CLIENT_ID=your_client_id_here
YOUTUBE_CLIENT_SECRET=your_client_secret_here
YOUTUBE_REFRESH_TOKEN=your_refresh_token_here

# AI API 설정 (OpenAI 또는 Claude 중 하나 이상 필요)
OPENAI_API_KEY=your_openai_api_key_here
CLAUDE_API_KEY=your_claude_api_key_here
AI_API_PROVIDER=openai  # 또는 claude

# 이미지 API (선택사항)
PEXELS_API_KEY=your_pexels_api_key_here
UNSPLASH_ACCESS_KEY=your_unsplash_access_key_here

# 업로드 스케줄 설정
UPLOAD_SCHEDULE_TIME=09:00  # 매일 이 시간에 영상 생성 및 업로드
UPLOAD_TIMEZONE=Asia/Seoul

# 영상 기본 설정
TREND_MODE=true
CONTENT_TYPE=auto
DEFAULT_TAGS=shorts,ai,automation,money,productivity
```

자세한 설정 방법은 [docs/SETUP_GUIDE.md](./docs/SETUP_GUIDE.md)를 참고하세요.

### 3. YouTube API 인증

```bash
# 첫 실행 시 브라우저에서 인증 진행
python main.py upload

# 브라우저가 자동으로 열리고 Google 계정으로 로그인
# 권한 승인 후 token.json 파일이 자동 생성됨
```

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
# 주제 자동 생성 후 비공개로 즉시 업로드 (기본값)
python main.py upload

# 특정 주제 지정 후 비공개로 즉시 업로드
python main.py upload "생산성 팁"

# 예약 업로드 모드 (다음날 0시에 공개)
python main.py upload "생산성 팁" --public

# 파일로 업로드 (비공개)
python main.py upload output/videos/video.mp4
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

# 중지
launchctl unload ~/Library/LaunchAgents/com.youtubeshorts.bot.plist
```

자세한 내용은 [docs/AUTO_START_GUIDE.md](./docs/AUTO_START_GUIDE.md)를 참고하세요.

## 📁 프로젝트 구조

```text
youtubeshorts/
├── main.py                      # 메인 실행 파일
├── requirements.txt             # Python 의존성
├── .env                         # 환경 변수 (생성 필요)
├── README.md                    # 프로젝트 메인 문서
├── CHANGELOG.md                 # 버전별 변경 이력
├── HISTORY.md                   # 상세 개발 일지
├── TODO.md                      # 미완료 작업 목록
│
├── src/                        # 소스코드
│   ├── core/                   # 핵심 모듈
│   │   └── config.py           # Pydantic 기반 설정 관리
│   ├── generators/             # 영상 생성 모듈
│   │   ├── script/             # 스크립트 생성 헬퍼
│   │   ├── video/              # 영상 합성 헬퍼
│   │   └── *.py                # 생성기 클래스
│   ├── uploaders/              # 업로드 모듈
│   ├── analytics/              # 분석 모듈
│   ├── pipeline/               # 파이프라인 모듈
│   ├── web/                    # 웹 대시보드
│   └── utils/                  # 유틸리티
│
├── docs/                       # 문서
├── tests/                      # 테스트
├── data/                       # 데이터 파일
├── output/                     # 출력 파일
└── logs/                       # 로그 파일
```

자세한 프로젝트 구조는 [docs/PROJECT_STRUCTURE.md](./docs/PROJECT_STRUCTURE.md)를 참고하세요.

## 🛠️ 기술 스택

- **Python 3.8+**: 메인 프로그래밍 언어
- **Pydantic**: 타입 안전 설정 관리
- **AI API**: OpenAI GPT 또는 Claude API를 활용한 스크립트 생성
- **OpenAI TTS**: 영어 음성 생성 (기본)
- **Google Cloud TTS**: 한글 음성 생성 (선택)
- **MoviePy**: 영상 편집 및 합성
- **PIL (Pillow)**: 이미지 처리
- **YouTube Data API v3**: 영상 업로드 및 통계 조회
- **Pexels Video API**: CC0 라이선스 배경 영상 다운로드

## 🔒 저작권 안전성

이 프로젝트는 **100% 저작권 안전한 콘텐츠**를 생성합니다:

- ✅ **스크립트**: AI 생성 (본인 소유)
- ✅ **음성**: TTS 생성 (본인 소유)
- ✅ **배경 영상**: Pexels Video (CC0 라이선스)
- ✅ **배경 이미지**: Pexels/Unsplash/Pixabay (무료 라이선스)

자세한 내용은 [docs/COPYRIGHT_SAFETY.md](./docs/COPYRIGHT_SAFETY.md)를 참고하세요.

## ⚠️ 주의사항

### YouTube 정책 준수

1. **자동 업로드 정책**: YouTube의 자동 업로드 정책을 반드시 확인하세요
2. **수익화 요구사항**: 
   - 일반 채널: 1,000명 구독자 + 4,000시간 시청 시간
   - Shorts 전용: 1,000명 구독자 + 1,000만 Shorts 조회수 (90일 내)
3. **API 할당량**: YouTube Data API v3 일일 할당량 확인 필요 (기본 10,000 units/day)

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
```

### 영상 생성 실패

1. **AI API 키 확인**: `.env` 파일에서 API 키 확인
2. **디스크 공간 확인**: `df -h` (macOS/Linux)
3. **임시 디렉토리 권한 확인**: `ls -la output/temp/`

## 📚 추가 리소스

### 문서

- **설정 가이드**: [docs/SETUP_GUIDE.md](./docs/SETUP_GUIDE.md)
- **API 설정**: [docs/API_SETUP.md](./docs/API_SETUP.md)
- **콘텐츠 최적화**: [docs/CONTENT_OPTIMIZATION.md](./docs/CONTENT_OPTIMIZATION.md)
- **3개월 로드맵**: [docs/3month_roadmap.md](./docs/3month_roadmap.md)

### 프로젝트 관리

- **변경 이력**: [CHANGELOG.md](./CHANGELOG.md)
- **개발 일지**: [HISTORY.md](./HISTORY.md)
- **작업 목록**: [TODO.md](./TODO.md)

## 📝 라이선스

이 프로젝트는 개인 사용 목적으로 제공됩니다.

## 🤝 기여

버그 리포트 및 기능 제안은 GitHub 이슈로 등록해주세요.

---

**면책 조항**: 이 도구는 YouTube의 서비스 약관을 준수해야 합니다. 자동 업로드로 인한 계정 정지 등의 책임은 사용자에게 있습니다. API 사용에 따른 비용은 사용자가 부담합니다.

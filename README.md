# YouTube Shorts 자동 업로드 봇

AI로 15초 영상 생성 → 자동 업로드 → 수익화 추적

## 🎯 목표

- **하루 1개 업로드**
- **3개월 후 수익화**
- **월 $100~500 수익 목표**

## ✨ 기능

1. **AI 영상 생성**: OpenAI GPT를 활용한 15초 YouTube Shorts 영상 자동 생성
2. **자동 업로드**: YouTube API를 통한 자동 업로드
3. **수익화 추적**: 조회수, 수익 예측, 진행 상황 분석
4. **스케줄링**: 매일 지정 시간에 자동 업로드

## 📋 사전 요구사항

1. **Python 3.8 이상**
2. **FFmpeg 설치** (영상 처리용)
   ```bash
   # macOS
   brew install ffmpeg
   
   # Ubuntu/Debian
   sudo apt-get install ffmpeg
   ```
3. **Google Cloud Console 설정**
   - YouTube Data API v3 활성화
   - OAuth 2.0 클라이언트 ID 생성
   - `client_secrets.json` 파일 다운로드

## 🚀 설치 및 설정

### 1. 저장소 클론 및 의존성 설치

```bash
cd youtubeshorts
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env.example`을 참고하여 `.env` 파일 생성:

```bash
cp .env.example .env
```

`.env` 파일 편집:

```env
# YouTube API 설정
YOUTUBE_CLIENT_ID=your_client_id_here
YOUTUBE_CLIENT_SECRET=your_client_secret_here
YOUTUBE_REFRESH_TOKEN=your_refresh_token_here

# OpenAI API (AI 영상 생성용)
OPENAI_API_KEY=your_openai_api_key_here

# 업로드 설정
UPLOAD_SCHEDULE_TIME=09:00
UPLOAD_TIMEZONE=Asia/Seoul
```

### 3. YouTube API 인증

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. **API 및 서비스** > **라이브러리**에서 "YouTube Data API v3" 활성화
4. **사용자 인증 정보** > **OAuth 2.0 클라이언트 ID** 생성
   - 애플리케이션 유형: 데스크톱 앱
   - `client_secrets.json` 다운로드하여 프로젝트 루트에 저장
5. 첫 실행 시 브라우저에서 인증 진행 → `token.json` 자동 생성

### 4. OpenAI API 키 발급

1. [OpenAI Platform](https://platform.openai.com/) 접속
2. API 키 생성
3. `.env` 파일에 `OPENAI_API_KEY` 설정

## 📖 사용법

### 즉시 업로드

```bash
# 주제 자동 생성
python main.py upload

# 특정 주제 지정
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
python main.py schedule
```

스케줄러는 매일 지정된 시간(기본값: 09:00)에 자동으로 영상을 생성하고 업로드합니다.

## 📊 수익화 추적

봇은 자동으로 다음 정보를 추적합니다:

- 총 업로드 영상 수
- 총 조회수, 좋아요, 댓글 수
- 영상별 예상 수익
- 월별 수익 추이
- 수익화까지 남은 일수
- 목표 달성 여부

### 수익 계산 방식

- **CPM (Cost Per Mille)**: $1.00 per 1,000 views (기본값)
- YouTube Shorts는 일반적으로 낮은 CPM을 가짐
- 월 $100 목표: 약 100,000 뷰 필요
- 월 $500 목표: 약 500,000 뷰 필요

## 📁 프로젝트 구조

```
youtubeshorts/
├── main.py                 # 메인 실행 파일
├── config.py               # 설정 관리
├── ai_video_generator.py   # AI 영상 생성
├── youtube_uploader.py     # YouTube 업로드
├── monetization.py         # 수익화 추적
├── requirements.txt        # Python 의존성
├── .env                    # 환경 변수 (생성 필요)
├── client_secrets.json     # YouTube API 인증 (생성 필요)
├── token.json              # 인증 토큰 (자동 생성)
├── monetization_data.json  # 수익화 데이터 (자동 생성)
└── output/                 # 생성된 영상 저장
    ├── videos/
    ├── thumbnails/
    └── temp/
```

## ⚙️ 설정 커스터마이징

`config.py`에서 다음 설정을 변경할 수 있습니다:

- 영상 길이 (기본: 15초)
- 해상도 (기본: 1080x1920)
- 업로드 시간
- 기본 태그 및 설명

## ⚠️ 주의사항

1. **YouTube 정책 준수**
   - YouTube의 자동 업로드 정책을 확인하세요
   - 저작권 및 커뮤니티 가이드라인 준수 필수

2. **수익화 요구사항**
   - YouTube 파트너 프로그램 가입 필요
   - 1,000명 구독자 + 4,000시간 시청 시간 (또는 1,000만 Shorts 조회수)
   - 3개월 후 수익화는 예상 시점입니다

3. **API 할당량**
   - YouTube Data API v3: 일일 할당량 확인 필요
   - OpenAI API: 사용량에 따른 비용 발생

## 🔧 문제 해결

### FFmpeg 오류
```bash
# FFmpeg 설치 확인
ffmpeg -version
```

### 인증 오류
- `client_secrets.json` 파일이 올바른 위치에 있는지 확인
- `token.json` 삭제 후 재인증 시도

### 영상 생성 실패
- OpenAI API 키가 올바른지 확인
- 디스크 공간 확인
- `output/temp/` 디렉토리 권한 확인

## 📈 성공 전략

1. **일관성**: 매일 정해진 시간에 업로드
2. **주제 다양화**: 다양한 주제로 영상 생성
3. **최적화**: 제목, 설명, 태그 최적화
4. **상호작용**: 댓글에 답변하고 커뮤니티 구축
5. **분석**: 통계를 통해 인기 주제 파악

## 📝 라이선스

이 프로젝트는 개인 사용 목적으로 제공됩니다.

## 🤝 기여

버그 리포트 및 기능 제안은 이슈로 등록해주세요.

---

**면책 조항**: 이 도구는 YouTube의 서비스 약관을 준수해야 합니다. 자동 업로드로 인한 계정 정지 등의 책임은 사용자에게 있습니다.


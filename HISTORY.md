# 프로젝트 개발 히스토리

이 문서는 YouTube Shorts 자동 업로드 봇 프로젝트의 개발 히스토리를 기록합니다.

## 프로젝트 개요

**YouTube Shorts 자동 업로드 봇**: AI로 자동 생성된 YouTube Shorts 영상을 매일 자동으로 업로드하고 수익화를 추적하는 봇

**최근 업데이트 (2025-11-19)**:
- 영어 콘텐츠 생성 지원 (스크립트, 자막, 썸네일)
- 핵심 단어만 자막 표시 (전체 스크립트 대신)
- 동일 영상 반복 방지 (영상 ID 추적)
- 주제 관련 배경만 선택 (주제 키워드 우선 사용)
- 음성과 영상 정확한 동기화 개선

### 핵심 목표

- 하루 1개 업로드 (퀄리티 중심): 매일 하나의 고품질 영상을 생성하여 업로드
- 퀄리티 우선 전략: 양보다 질에 집중하여 시청자 참여도와 수익을 극대화
- 3개월 후 수익화: 꾸준한 업로드를 통한 YouTube 파트너 프로그램 가입
- 월 $100~500 수익 목표: 지속적인 고품질 콘텐츠 제작을 통한 수익 창출

## 주요 기능

### 1. AI 영상 자동 생성

- **AI API 지원**: OpenAI GPT 또는 Claude API를 활용한 고품질 스크립트 생성
- **API 자동 선택**: 설정에 따라 OpenAI 또는 Claude API 자동 사용
- **API 폴백**: Claude API 실패 시 자동으로 OpenAI로 전환
- **콘텐츠 타입**: HOOK, QUOTE, STORY, FACT, SHORT_STORY, AUTO
- **목표 길이**: 55초 (최대 60초)
- **자막 포함**: 모든 문장에 자막 자동 생성 및 오버레이
- **배경 영상/이미지**: Pexels Video API를 활용한 CC0 라이선스 배경 영상 또는 무료 이미지
- **배경 영상 순차 재생**: 같은 배경 영상이 반복되지 않고 순차적으로 재생
- **문장별 관련 이미지**: 정적 이미지가 문장과 관련된 이미지를 Pexels/Unsplash에서 자동 다운로드
- **한글 음성**: Google TTS 또는 OpenAI TTS를 활용한 자연스러운 한글 음성
- **정확한 동기화**: 음성과 영상이 정확히 일치하며, 오디오 클립과 비디오 클립이 완벽하게 싱크

### 2. YouTube 자동 업로드

- YouTube Data API v3를 통한 안정적인 자동 업로드
- 한글 설명 자동 생성
- 최적화된 태그 자동 설정
- 즉시 공개 또는 예약 업로드 가능

### 3. 수익화 추적 및 분석

- 실시간 통계 (조회수, 좋아요, 댓글 수)
- 수익 예측 (CPM 기반)
- 진행 상황 분석
- 월별 리포트

### 4. 스케줄링

- 매일 지정된 시간에 1개의 고품질 영상을 생성하여 업로드
- 퀄리티 중심 생성: 6가지 콘텐츠 타입 중 최적의 타입을 선택하여 고품질 영상 생성
- 계절별 주제 선택: 현재 날짜를 기반으로 계절에 맞는 주제를 우선적으로 선택 (50% 확률)
- 백그라운드 실행 지원
- macOS LaunchAgent 지원

## 개발 히스토리 (Git Log 기반)

### 2025-11-17: Claude API 지원 추가

- **커밋**: `37b24ba`
- Claude API 통합 완료
- `AI_API_PROVIDER` 설정으로 OpenAI/Claude 선택 가능
- Claude API 실패 시 자동으로 OpenAI로 폴백
- `.env` 파일에 `CLAUDE_API_KEY` 및 `AI_API_PROVIDER` 설정 추가
- `requirements.txt`에 `anthropic>=0.34.0` 추가
- 모든 문서 업데이트 (README, API_SETUP.md 등)

### 2025-11-17: 스케줄러 6개 타입 생성 및 계절별 주제 선택

- **커밋**: `001942f`, `b1e2ad9`, `2c199d9`
- 스케줄러가 6개 콘텐츠 타입(HOOK, QUOTE, STORY, FACT, SHORT_STORY, AUTO)을 모두 한 번에 생성하도록 수정
- `bot.py`에 `create_and_upload_all_types()` 메서드 추가
- 계절별 주제 선택 기능 추가: 현재 날짜 기반으로 계절 판단
- 계절별 주제 카테고리:
  - 봄 (3-5월): 정리, 옷장 정리, 환절기 대비
  - 여름 (6-8월): 전기요금 절약, 장마철 곰팡이, 습기 관리
  - 가을 (9-11월): 환절기 정리, 겨울 준비, 옷장 정리
  - 겨울 (12-2월): 난방비 절약, 자동차 점검, 겨울 대비
- `video_generator.py`에 `_get_season()` 메서드 추가
- 주제 선택 시 계절에 맞는 주제를 50% 확률로 우선 선택

### 2025-11-17: 문서 업데이트

- **커밋**: `b7683a5`
- 하루 6개 업로드 기능 반영
- 최신 기능 설명 추가

### 2025-11-17: 하루 6개 자동 업로드 스케줄 설정

- **커밋**: `68a1955`
- 스케줄러가 하루에 6개 영상을 생성하도록 설정

### 2025-11-19: 영상 품질 개선 및 영어 콘텐츠 지원

**주요 개선 사항:**

1. **영어 콘텐츠 생성 지원**
   - 주제가 영어인 경우 자동으로 영어 콘텐츠 생성
   - 영어 스크립트, 자막, 썸네일 모두 영어로 생성
   - 영어 폰트 지원 (Arial Bold, Arial 등)

2. **핵심 단어 자막 표시**
   - 전체 스크립트 대신 핵심 단어(1-3개)만 자막으로 표시
   - AI를 활용한 핵심 단어 추출 (`_extract_key_words_for_subtitle`)
   - 가독성 향상 및 자막-음성 싱크 정확도 개선

3. **동일 영상 반복 방지**
   - 하나의 Shorts 영상 내에서 동일한 배경 영상이 반복되지 않도록 개선
   - 영상 ID 추적 및 중복 방지 로직 구현
   - `exclude_videos` 파라미터로 이미 다운로드한 영상 제외
   - 영상 파일명에 영상 ID 포함 (`bg_video_{index}_{video_id}.mp4`)

4. **주제 관련 배경 선택 강화**
   - 주제 키워드를 우선 사용하여 주제와 관련된 배경만 선택
   - Pexels API 검색 결과에서 주제 키워드가 포함된 영상 우선 선택
   - 주제와 무관한 배경(예: 폭포 등 자연 배경) 제외

5. **음성과 영상 동기화 개선**
   - 자막 클립의 시작 시간을 명시적으로 0으로 설정
   - duration을 실제 음성 길이(`sentence_audio_durations`)와 정확히 일치시킴
   - CompositeVideoClip 생성 후 duration 재확인

6. **문서 업데이트 규칙 추가**
   - 작업 완료 후 HISTORY.md, TODO.md, .cursorrules 자동 업데이트 규칙 추가

### 2025-11-19: 실측 TTS 기반 싱크 강화 및 전체 자막 모드 검증

- sentence_audio_durations 스케일링을 제거하고 TTS가 생성한 실측 길이를 그대로 사용하여 누적 지연을 원천 차단
- 배경/자막 CompositeVideoClip을 매 문장마다 새로 만들고 `start=0`을 강제하여 타임라인 기준을 고정
- `SUBTITLE_MODE=full_sentence` 환경 변수로 전체 문장 자막 모드를 테스트 (`output/videos/shorts_20251119_155131.mp4`), 음성·영상 모두 49.2초로 일치
- 영어 콘텐츠에서도 `SUBTITLE_MODE=full_sentence` 설정을 존중하도록 수정하여 전체 문장 자막이 정상 노출
- GPT 제안사항 기록: 향후 FFmpeg 무음 제거 + CFR 고정 파이프라인 검토(TODO에 아이디어 추가 완료)

### 2025-11-17: 전략 변경 - 하루 1개 퀄리티 중심 전략

- **전략 변경**: 하루 6개 업로드에서 하루 1개 고품질 영상 업로드로 전략 변경
- **이유**: 양보다 질에 집중하여 시청자 참여도와 수익을 극대화
- **방식**: 6가지 콘텐츠 타입 중 최적의 타입을 선택하여 고품질 영상 생성
- 모든 문서 업데이트 (README.md, HISTORY.md, TODO.md, .cursorrules)

### 2025-11-16: 배경 영상 반복 방지 및 이미지 다운로드 개선

- **커밋**: `aaf3bb2`
- 배경 영상이 반복되지 않고 순차적으로 재생되도록 최적화
- 문장별 관련 이미지 다운로드 로직 개선

### 2025-11-16: 재태크/돈 버는 방법 중심 주제로 전면 교체

- **커밋**: `ef35993`
- 모든 콘텐츠 타입의 주제를 재태크/돈 버는 방법 중심으로 전면 교체
- 사용자 요청: "사람들은 돈버는거에 관심이 많아"

### 2025-11-16: 재태크 관련 주제 대폭 추가

- **커밋**: `7d7dd70`
- QUOTE와 STORY 타입에 재태크 관련 주제 35개 추가
- 투자, 부동산, 주식, 경제적 자유 등 다양한 재태크 주제 포함

### 2025-11-16: 수익 관련 주제 추가

- **커밋**: `0f87052`
- AI로 돈버는 방법, Crypto로 돈버는 방법 등 수익 관련 주제 추가
- QUOTE 타입에 추가

### 2025-11-15: 멀티 플랫폼 업로드 기능 추가

- **커밋**: `971191d`
- TikTok과 Instagram 업로드 기능 추가
- `MultiPlatformUploader`, `TikTokUploader`, `InstagramUploader` 클래스 생성
- 기본값은 YouTube만 사용하도록 설정 (`ENABLE_TIKTOK_UPLOAD=false`, `ENABLE_INSTAGRAM_UPLOAD=false`)
- 사용자 결정: "일단 유튜브만 하는걸로하자"

### 2025-11-15: 템플릿/프롬프트 폴더 제거 및 한국어 전용

- **커밋**: `34f9f83`, `29fdaa7`, `a845b81`
- 템플릿 폴더(`templates/`) 및 템플릿 로직 완전 제거
- 프롬프트 폴더(`prompts/`) 삭제
- 영어 회화 주제 제거 및 한국어 전용 스크립트 생성
- `temp` 폴더 자동 정리 기능 추가
- 55초 목표 길이 반영

### 2025-11-15: 프로젝트 구조 정리

- **커밋**: `a27f4f2`
- 프로젝트 구조 정리 및 파일 정리

### 2025-11-15: 오디오 클립 동기화 문제 수정

- **커밋**: `5c0c968`
- 스크립트 트리밍 시 오디오 클립 동기화 문제 수정

### 2025-11-15: 자막과 음성 싱크 문제 수정

- **이슈**: 사용자 보고 - `shorts_20251117_130602.mp4`에서 자막과 음성이 싱크가 맞지 않음
- **수정 내용**:
  - `_create_subtitle_clip` 메서드에서 자막 클립의 시작 시간을 명시적으로 0으로 설정
  - 자막 클립의 duration이 정확히 오디오 세그먼트 duration과 일치하도록 수정
  - 페이드 효과 적용 순서를 조정하여 자막이 페이드의 영향을 받지 않도록 수정
  - 자막 추가 로직을 페이드 효과 적용 전으로 이동

### 2025-11-15: 썸네일 자동 생성 및 음성 잘림 방지

- **커밋**: `75fda3c`
- 썸네일 자동 생성 기능 추가
- 음성 잘림 방지 개선

### 2025-11-15: 키워드 기반 이미지 다운로드 및 영상 품질 개선

- **커밋**: `b71eaff`
- 키워드 기반 이미지 다운로드 기능 추가
- 영상 품질 개선

## 주요 기술 스택

- **Python 3.8+**: 메인 프로그래밍 언어
- **AI API**: OpenAI GPT 또는 Claude API
- **TTS**: OpenAI TTS 또는 Google TTS (gTTS)
- **영상 편집**: MoviePy
- **이미지 처리**: PIL (Pillow)
- **YouTube API**: YouTube Data API v3
- **배경 미디어**: Pexels Video API, Unsplash API, Pixabay API
- **데이터베이스**: SQLite
- **스케줄링**: schedule 라이브러리

## 프로젝트 구조

```
youtubeshorts/
├── main.py                      # 메인 실행 파일
├── config.py                    # 설정 관리
├── requirements.txt             # Python 의존성
├── .env                         # 환경 변수
├── README.md                    # 프로젝트 메인 문서
│
├── src/                        # 소스코드
│   ├── generators/             # 영상 생성 모듈
│   │   └── video_generator.py
│   ├── uploaders/              # 업로드 모듈
│   │   ├── youtube_uploader.py
│   │   ├── tiktok_uploader.py
│   │   ├── instagram_uploader.py
│   │   └── multi_platform_uploader.py
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
│   ├── API_SETUP.md            # AI API 설정 가이드
│   ├── AUTO_START_GUIDE.md     # 자동 시작 가이드
│   ├── CONTENT_OPTIMIZATION.md # 콘텐츠 최적화 전략
│   ├── COPYRIGHT_SAFETY.md     # 저작권 안전 가이드
│   ├── SETUP_GUIDE.md          # YouTube API 설정 가이드
│   └── PROJECT_STRUCTURE.md    # 프로젝트 구조 문서
│
├── data/                       # 데이터 파일
│   ├── videos.db               # SQLite 데이터베이스
│   └── monetization_data.json  # 수익화 데이터
│
└── output/                     # 출력 파일
    ├── videos/                 # 생성된 영상
    ├── thumbnails/            # 썸네일
    └── temp/                  # 임시 파일
```

## 주요 설정 파일

### `.env` 파일 주요 설정
- `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`: YouTube API
- `OPENAI_API_KEY`: OpenAI API 키
- `CLAUDE_API_KEY`: Claude API 키
- `AI_API_PROVIDER`: AI API 제공자 선택 (`openai` 또는 `claude`, 기본값: `openai`)
- `PEXELS_API_KEY`: Pexels API 키 (선택사항)
- `UNSPLASH_ACCESS_KEY`: Unsplash API 키 (선택사항)
- `UPLOAD_SCHEDULE_TIME`: 업로드 스케줄 시간 (기본값: `09:00`)
- `UPLOAD_TIMEZONE`: 타임존 (기본값: `Asia/Seoul`)

### `config.py` 주요 설정
- `SHORTS_TARGET_DURATION`: 목표 영상 길이 (55초)
- `SHORTS_MAX_DURATION`: 최대 영상 길이 (60초)
- `ENABLE_TIKTOK_UPLOAD`: TikTok 업로드 활성화 (기본값: `false`)
- `ENABLE_INSTAGRAM_UPLOAD`: Instagram 업로드 활성화 (기본값: `false`)

## 콘텐츠 타입 및 주제 카테고리

### 콘텐츠 타입
1. **HOOK**: 한국어 속담/관용어 한 문장 학습 (짧고 강한 Hook)
2. **QUOTE**: AI·비즈니스·명언·지식 한 줄
3. **STORY**: 스토리텔링 (심리/역사/부자습관)
4. **FACT**: 숏폼 팩트 기반 영상
5. **SHORT_STORY**: AI 이미지 기반 짧은 스토리
6. **AUTO**: 자동 선택

### 주제 카테고리
- 🌤 **계절**: 봄/여름/가을/겨울에 맞는 실용적인 주제
- 🏠 **생활**: 집 정리, 냉장고 관리, 옷장 정리 등 일상 생활 팁
- 🚗 **자동차**: 자동차 점검, 유지보수, 계절별 관리
- 💰 **재태크**: 돈 관리, 투자, 자산 형성, 경제적 자유 (주요 카테고리)
- 🧠 **자기계발**: 루틴, 습관, 성공 마인드, 인생 교훈

## 중요한 결정 사항

1. **멀티 플랫폼 업로드**: TikTok과 Instagram 업로드 기능을 추가했으나, 현재는 YouTube만 사용하도록 기본값 설정
2. **한국어 전용**: 영어 회화 주제를 제거하고 한국어 전용으로 전환
3. **템플릿 제거**: 템플릿 폴더와 템플릿 로직을 완전히 제거하고 AI 생성에 집중
4. **55초 목표**: 모든 콘텐츠 타입을 55초 목표로 통일
5. **재태크 중심**: 사용자 요청에 따라 재태크/돈 버는 방법 중심 주제로 전면 교체
6. **Claude API 통합**: OpenAI 외에 Claude API도 지원하여 선택의 폭 확대

## 알려진 이슈 및 해결

### 자막과 음성 싱크 문제
- **이슈**: 자막과 음성이 싱크가 맞지 않음
- **원인**: 자막 클립의 시작 시간이 명시되지 않아 발생
- **해결**: 자막 클립에 시작 시간을 명시적으로 0으로 설정하고, duration을 정확히 오디오 세그먼트 duration과 일치하도록 수정

### 오디오 클립 동기화 문제
- **이슈**: 스크립트 트리밍 시 오디오 클립 동기화 문제
- **해결**: 오디오 클립 동기화 로직 수정

## 향후 계획

- TikTok 및 Instagram 업로드 기능 완전 구현 (현재는 플레이스홀더)
- 썸네일 최적화 기능 강화
- 더 많은 주제 카테고리 추가
- 통계 분석 기능 강화
- 자동 A/B 테스트 기능

---

**마지막 업데이트**: 2025-11-19
**프로젝트 상태**: 활발히 개발 중


# 프로젝트 개발 히스토리

이 문서는 YouTube Shorts 자동 업로드 봇 프로젝트의 개발 히스토리를 기록합니다.

## 프로젝트 개요

**YouTube Shorts 자동 업로드 봇**: AI로 자동 생성된 YouTube Shorts 영상을 매일 자동으로 업로드하고 수익화를 추적하는 봇

**최근 업데이트 (2025-11-21)**:
- 1분 명상(MEDITATION) 콘텐츠 타입 추가
- 호흡 가이드(BREATHING) 콘텐츠 타입 추가
- 명상/호흡 가이드용 AI 프롬프트 및 주제 목록 추가
- AUTO 선택 시 명상/호흡 타입도 포함되도록 확장
- **기본 자막 모드 변경**: `SUBTITLE_MODE` 기본값을 `full_sentence`로 통일 (코드 및 문서 일치)

**이전 업데이트 (2025-11-19)**:
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
- **콘텐츠 타입**: HOOK, QUOTE, STORY, FACT, SHORT_STORY, MEDITATION, BREATHING, AUTO
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
- 계절별 주제 선택: 현재 날짜를 기반으로 계절에 맞는 주제를 우선적으로 선택 (25% 확률)
- 백그라운드 실행 지원
- macOS LaunchAgent 지원

## 개발 히스토리 (Git Log 기반)

### 2025-11-20: 모바일 시청 시 자막 가독성 개선
- `_create_subtitle_clip()`에서 자막 위치 계산 시 클립 높이만큼 추가로 올려 하단 여백을 확보
- ImageMagick/PIL 경로 모두 동일하게 적용하여 Shorts 영상 하단 UI 영역과 겹치지 않도록 조정
- 추가로 약 3줄 간격(기본 180px → 90px) 만큼 위로 이동시키는 오프셋을 도입·조정해 실제 기기 재생 시 가려지는 문제를 해소하면서도 화면 중앙으로 치우치지 않도록 튜닝
- Composite 단계에서 자막 위치를 다시 하단으로 덮어쓰던 로직을 제거해 `_create_subtitle_clip()`에서 계산한 좌표가 그대로 반영되도록 수정
- `output/videos/shorts_20251121_003213.mp4`를 생성한 뒤 `YouTubeUploader`를 직접 호출해 YouTube에 업로드(영상 ID: `yyTVlenTrj4`, 썸네일 `output/thumbnails/thumb_20251121_003425.jpg`)
- 실제 기기에서 자막이 화면 중앙 쪽으로 이동해 가독성이 향상됨

### 2025-11-21: 명상 및 호흡 가이드 콘텐츠 타입 추가

- **MEDITATION 타입 추가**: 1분 명상 가이드 콘텐츠 타입 추가
  - 차분하고 평화로운 명상 가이드 스크립트 생성
  - 몸 인식, 호흡 집중, 마음챙김 관찰 등 단계별 안내
  - 명상 주제 목록 추가 (아침 명상, 스트레스 완화, 불안 완화 등)
- **BREATHING 타입 추가**: 호흡 가이드 콘텐츠 타입 추가
  - 4-7-8 호흡법, 박스 호흡법 등 단계별 호흡 가이드
  - 타이밍 신호와 함께 명확한 지침 제공
  - 호흡 운동 주제 목록 추가 (스트레스 완화, 수면 개선, 집중력 향상 등)
- **AUTO 선택 확장**: AUTO 선택 시 명상/호흡 타입도 포함되도록 수정
- **AI 프롬프트 추가**: Claude/OpenAI 모두에 명상/호흡 가이드용 프롬프트 추가 (영어/한국어)
- **계절별 주제**: 명상/호흡 타입에도 계절별 주제 추가

### 2025-11-21: 6개 영어 재태크 콘텐츠 생성 및 즉시 업로드
- 자막 위치 조정값(추가 오프셋 90px)을 유지한 채로 6개 영어 주제를 연속 생성·업로드하여 실제 YouTube 채널에 공개 배포
- `main.py upload "<topic>" --force` 워크플로로 생성 → 썸네일 생성/삽입 → YouTube 업로드 → 썸네일 업로드까지 자동화 확인
- 업로드된 영상 (파일 → ID → 주제):
  1. `shorts_20251121_003213.mp4` → `yyTVlenTrj4` → *November Budget Reset: 3 Micro Habits To Kill Impulse Spending* (자막 높이 튜닝 확인용 샘플)
  2. `shorts_20251121_004149.mp4` → `9-nuUzhT5IM` → *Side Hustle Sprint: Flip Black Friday Deals for Extra $500*
  3. `shorts_20251121_004533.mp4` → `hzXFwoh9oBs` → *AI-Powered Savings Jar: Automate Spare Change Into Index Funds*
  4. `shorts_20251121_004859.mp4` → `q3uI1v923X8` → *Credit Score Glow-Up: 30-Day Plan for Millennials*
  5. `shorts_20251121_005239.mp4` → `neKDpoaoWoQ` → *Micro-Morning Routine for High-Energy Productivity*
  6. `shorts_20251121_005623.mp4` → `LEoAEnnYpGw` → *Recession-Proof Skill Stack: Combine Storytelling + Data*
- 각 영상은 썸네일까지 정상 업로드 되었으며, `token.json` 기반 인증이 안정적으로 재사용됨

### 2025-11-19: Instagram 연결 테스트 명령 추가
- `InstagramUploader`가 Instagram Graph API(`v21.0`) 계정 정보를 직접 조회해 자격 증명을 검증하도록 개선
- `python main.py instagram-test` 명령으로 `.env` 자격 증명을 사용해 연결을 점검하고 성공/실패 로그를 출력
- README, MULTI_PLATFORM_SETUP.md, .cursorrules에 Instagram 연결 테스트 절차 문서화

### 2025-11-19: 테스트용으로 생성했던 6개 영상 YouTube 업로드
- 기존 `output/videos/shorts_20251119_*.mp4`를 다시 생성하지 않고 `YouTubeUploader`를 직접 호출해 순차 업로드
- 업로드된 영상 ID:
  1. `shorts_20251119_171551.mp4` → `OaqGCXeROeo`
  2. `shorts_20251119_171807.mp4` → `OgUBCWgDQpE`
  3. `shorts_20251119_172000.mp4` → `2Kp-2c65iyw`
  4. `shorts_20251119_172208.mp4` → `Vu8xrbP7Fqs`
  5. `shorts_20251119_172417.mp4` → `oHHjFBFcZY0`
  6. `shorts_20251119_172737.mp4` → `T892L_SCKns`
- 각 영상의 썸네일 경로(`output/thumbnails/thumb_*.jpg`)는 현재 워크스페이스에 존재하지 않아 업로드가 건너뛰어졌으며, 필요 시 YouTube Studio에서 썸네일을 수동 등록해야 함
- 인증은 기존 `token.json`으로 진행되었고, 새로 발급받은 refresh token이 만료되었다는 경고가 한 번 출력됨

### 2025-11-19: 모든 콘텐츠 타입 영어 테스트 러닝
- `main.py test` 모드로 5개 콘텐츠 타입(HOOK, QUOTE, STORY, FACT, SHORT_STORY) + AUTO 시나리오를 각각 실행하여 6개의 영어 Shorts를 생성
- 각 테스트는 썸네일 삽입, 영어 자막/스크립트/썸네일 텍스트, 배경 영상 무중복, 오디오-비디오 길이 일치 여부를 점검
- 생성 결과 (파일명/길이):
  - HOOK `autumn routine reset` → `output/videos/shorts_20251119_171551.mp4` (57.15s), 썸네일 `output/thumbnails/thumb_20251119_171712.jpg`
  - QUOTE `mindset quote boost` → `output/videos/shorts_20251119_171807.mp4` (55.99s), 썸네일 `output/thumbnails/thumb_20251119_171914.jpg`
  - STORY `rebuilt finances story` → `output/videos/shorts_20251119_172000.mp4` (55.88s), 썸네일 `output/thumbnails/thumb_20251119_172120.jpg`
  - FACT `surprising money fact` → `output/videos/shorts_20251119_172208.mp4` (56.64s), 썸네일 `output/thumbnails/thumb_20251119_172319.jpg`
  - SHORT_STORY `routine micro story` → `output/videos/shorts_20251119_172417.mp4` (56.73s), 썸네일 `output/thumbnails/thumb_20251119_172557.jpg`
  - AUTO `black friday sales tip` → `output/videos/shorts_20251119_172737.mp4` (55.71s), 썸네일 `output/thumbnails/thumb_20251119_172902.jpg`
- 모든 테스트는 업로드 없이 로컬 생성만 수행했으며, 영어 전용 파이프라인과 썸네일 첫 프레임 삽입이 정상 동작함을 확인

### 2025-11-20: Instagram Graph API 테스트 보류
- Long-lived Access Token을 생성하여 `.env`에 적용하고 Instagram 인증은 성공했으나, `me/accounts` 호출 시 Facebook 페이지가 반환되지 않는 문제 지속
- 토큰 권한(`pages_show_list`, `pages_manage_posts`, `instagram_content_publish` 등)은 정상이나 Graph API가 해당 페이지를 “관리 대상”으로 인식하지 않아 Facebook 업로드 단계에서 오류 발생
- 임시 방편으로 Instagram 업로드 비활성화 (`ENABLE_INSTAGRAM_UPLOAD=false`) 상태로 전환하고, 권한 전파/토큰 갱신을 기다린 뒤 추후 재시도 예정

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
- 주제 선택 시 계절에 맞는 주제를 25% 확률로 우선 선택

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
- 기본 자막 모드를 `full_sentence`로 전환해 테스트 시 별도 환경 변수 없이도 전체 문장 자막 제공
- AI 스크립트 실패 시 주제 키워드를 반영하는 16문장 기본 스크립트 생성기로 교체하여 토픽별 차별화 보장
- 전체 문장 자막의 줄 간격을 넓혀 가독성 향상 (30px line spacing)
- 영어 콘텐츠에서도 `SUBTITLE_MODE=full_sentence` 설정을 존중하도록 수정하여 전체 문장 자막이 정상 노출
- GPT 제안사항 기록: 향후 FFmpeg 무음 제거 + CFR 고정 파이프라인 검토(TODO에 아이디어 추가 완료)
- Claude 모델 호출 시 404가 발생하는 `claude-3-5-sonnet-20241022`는 마지막으로 돌리고 `claude-3-opus-20240229` → `claude-3-sonnet-20240229` 순으로 안정 모델을 먼저 시도하도록 변경
- AI가 출력한 "Here's a YouTube Shorts script..." 같은 안내 문장은 필터링하여 실제 콘텐츠 문장만 음성으로 사용
- `_generate_topic()` 기본/계절 주제 풀을 모두 영어로 업데이트하여 언어 감지가 확실히 영어로 인식되도록 개선

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
6. **MEDITATION**: 1분 명상 가이드 (마음챙김, 스트레스 완화 등)
7. **BREATHING**: 호흡 가이드 (4-7-8 호흡법, 박스 호흡법 등)
8. **AUTO**: 자동 선택

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


# TODO - YouTube Shorts 자동 업로드 봇

이 문서는 프로젝트의 현재 작업, 계획된 기능, 그리고 향후 개선 사항을 추적합니다.

## 🎯 현재 진행 중인 작업

### 구독자 수 증가 전략 적용 ✅

- **목표**: YouTube Shorts 채널의 구독자 수를 효과적으로 늘리기 위한 종합 전략 연구 및 코드 적용
- **완료된 작업**:
  - ✅ 설명란에 구독 유도 텍스트 강화 (구독 링크, 이유, 시리즈 정보, 관련 영상 링크)
  - ✅ 스크립트 끝에 구독 CTA 강화 (모든 콘텐츠 타입의 AI 프롬프트에 자연스러운 구독 요청 추가)
  - ✅ 썸네일에 Subscribe 배지 추가 (상단 오른쪽, 빨간색 배경)
  - ✅ YouTube API로 채널 URL 가져오기 기능 추가 (`get_channel_info()`, `get_recent_videos()`)
- **기대 효과**: 구독 전환율 향상, 채널 성장 가속화
- **다음 단계**: 실제 업로드 영상에서 구독자 수 변화 모니터링 및 추가 최적화

### 영상 품질 개선 작업

- **동일 영상 반복 방지**: 하나의 Shorts 영상 내에서 동일한 배경 영상이 반복되지 않도록 영상 ID 추적 및 중복 방지 로직 구현 ✅
- **주제 관련 배경 선택**: 주제 키워드를 우선 사용하여 주제와 관련된 배경만 선택하도록 개선 ✅
- **핵심 단어 자막**: 전체 스크립트가 아닌 핵심 단어만 자막으로 표시하여 가독성 향상 ✅
- **음성과 영상 싱크**: 자막 클립의 시작 시간을 0으로 설정하고, duration을 실제 음성 길이와 정확히 일치시킴 ✅
- **영어 콘텐츠 지원**: 영어 주제 감지 시 모든 콘텐츠(스크립트, 자막, 썸네일)를 영어로 생성 ✅
- **전체 문장 자막 모드**: `SUBTITLE_MODE=full_sentence`를 기본값으로 확정 및 코드/문서 통일 완료 (2025-11-21) ✅
- **자막 가독성**: 전체 문장 자막의 줄 간격을 30px로 확대하여 읽기 쉬움 ✅
- **Claude 모델 우선순위**: 404가 나는 `claude-3-5-sonnet-20241022`는 마지막으로, 안정 모델을 먼저 시도하도록 조정 ✅
- **자막 위치 조정**: 아이폰 UI 가림 방지를 위해 하단 여백을 300px 추가 상향 (ImageMagick: 400px, PIL: 450px) ✅
- **TREND_MODE 가중치**: `TREND_MODE=true` 시 글로벌 트렌드(40%)·계절(25%)·성과(20%)·탐색(15%) 비율로 주제 선택, 성과형 주제 풀과 로그 출력 추가 ✅ (2025-11-21)
- **상태**: 주요 개선 사항 완료, 지속적인 테스트 및 최적화 필요

## 🧪 최근 테스트 로그

- **2025-11-19**: 모든 콘텐츠 타입별 영어 테스트 영상 생성 (업로드 없음)
  - HOOK `autumn routine reset` → `output/videos/shorts_20251119_171551.mp4` (57.15s)
  - QUOTE `mindset quote boost` → `output/videos/shorts_20251119_171807.mp4` (55.99s)
  - STORY `rebuilt finances story` → `output/videos/shorts_20251119_172000.mp4` (55.88s)
  - FACT `surprising money fact` → `output/videos/shorts_20251119_172208.mp4` (56.64s)
  - SHORT_STORY `routine micro story` → `output/videos/shorts_20251119_172417.mp4` (56.73s)
  - AUTO `black friday sales tip` → `output/videos/shorts_20251119_172737.mp4` (55.71s)
- 모든 테스트에서 썸네일 첫 프레임 삽입, 영어 자막/썸네일, 배경 영상 무중복, 오디오-비디오 동기화가 정상임을 확인

- **2025-11-21**: 안정성 및 모니터링 시스템 구축 완료
  - ✅ 에러 처리 및 재시도 로직 강화 (retry decorator with exponential backoff)
  - ✅ API 할당량 관리 개선 (QuotaManager with rate limiting)
  - ✅ 로깅 및 모니터링 강화 (structured logging + performance tracking)
  - ✅ 성과 분석 시스템 (AnalyticsManager: 주제별 성과, 최적 업로드 시간)
  - ✅ 문서 업데이트 (README, STABILITY_FEATURES.md)
  - ✅ 자막 줄 간격 개선 (30px → 50px로 증가하여 가독성 향상)
- **2025-11-19**: 위 테스트용 6개 영상을 `YouTubeUploader`로 수동 업로드 (ID: OaqGCXeROeo, OgUBCWgDQpE, 2Kp-2c65iyw, Vu8xrbP7Fqs, oHHjFBFcZY0, T892L_SCKns). 워크스페이스에 썸네일 파일이 없어 썸네일 업로드는 생략됨.
- **2025-11-21**: `output/videos/shorts_20251121_003213.mp4` 자막 위치 조정 테스트 후 `YouTubeUploader`로 즉시 업로드 (ID: yyTVlenTrj4, 썸네일 `output/thumbnails/thumb_20251121_003425.jpg`)
- **2025-11-21**: 동일 자막 설정으로 5개 추가 영어 영상을 생성해 즉시 업로드
  - `shorts_20251121_004149.mp4` → `9-nuUzhT5IM` (*Side Hustle Sprint: Flip Black Friday Deals for Extra $500*)
  - `shorts_20251121_004533.mp4` → `hzXFwoh9oBs` (*AI-Powered Savings Jar: Automate Spare Change Into Index Funds*)
  - `shorts_20251121_004859.mp4` → `q3uI1v923X8` (*Credit Score Glow-Up: 30-Day Plan for Millennials*)
  - `shorts_20251121_005239.mp4` → `neKDpoaoWoQ` (*Micro-Morning Routine for High-Energy Productivity*)
  - `shorts_20251121_005623.mp4` → `LEoAEnnYpGw` (*Recession-Proof Skill Stack: Combine Storytelling + Data*)
- **2025-11-21**: 트렌드 가중치 로직 테스트 (`output/videos/shorts_20251121_150056.mp4`, 53.5s, 타입: `short_story`, 주제: *Logging expenses for 30 days changed my bank balance*, 썸네일 `output/thumbnails/thumb_20251121_150222.jpg`)
- **2025-11-22**: 구독자 수 증가 전략 연구 및 적용
  - 설명란에 구독 유도 텍스트 강화 (채널 URL, 구독 이유, 관련 영상 링크)
  - 스크립트 끝에 자연스러운 구독 CTA 추가 (모든 콘텐츠 타입)
  - 썸네일에 "SUBSCRIBE" 배지 추가 (상단 오른쪽)
  - YouTube API 채널 정보 기능 추가 (`get_channel_info()`, `get_recent_videos()`)
- **2025-11-22**: AI 기반 주제 생성 시스템 구현 완료
  - `generate_topics_from_trends()` 메서드 추가: 트렌드 키워드를 기반으로 콘텐츠 타입별 주제 생성
  - `validate_topic_quality()` 메서드 추가: 주제 품질 검증 (중복 방지, 길이 검증, 관련 키워드 확인)
  - `video_generator.py`에 통합: AI 생성 주제를 주제 풀에 자동 추가, 12시간 캐싱
  - 품질 필터링: 검증 점수 50점 이상인 주제만 사용, 실패 이유 로깅
- **2025-11-22**: YouTube 트렌드 키워드 수집 시스템 구현 완료
  - `TrendCollector` 클래스 추가 (`src/analytics/trend_collector.py`)
  - YouTube Data API v3를 사용하여 인기 Shorts 수집 및 키워드 추출
  - AI 키워드 정제 및 24시간 캐싱 시스템 구현
  - `video_generator.py`에 통합하여 `TREND_MODE=true`일 때 자동으로 트렌드 주제 사용
  - 카테고리별 트렌드 수집 지원 (finance, productivity, self-improvement, lifestyle)
- **2025-11-22**: 6개 겨울/연말 재태크 영상 일괄 생성 및 업로드
  - `Q0qk_EGmOxU` → *December Tax Hack: How to Save $2,000 Before Year-End With These 3 Moves*
  - `0DDhBYBuqaw` → *Holiday Spending Trap: Why Americans Waste $1,500 Every December and How to Stop It*
  - `NVJHCu01knQ` → *Winter Heating Bill Shock: The One Change That Cut My Gas Bill by 50% Last Year*
  - `rBkBC0q41eE` → *Year-End Bonus Strategy: What Smart People Do With Their December Paycheck*
  - `yKQIb6o9_KM` → *January Financial Reset: The 30-Day Challenge That Built My Emergency Fund*
  - `rXCDiFxBL2Q` → *401k Deadline Alert: Why Contributing Before December 31st Changes Everything*
  - 총 업로드 영상: 36개, 총 조회수: 917회

## 🚀 단기 목표 (우선순위 높음)

### 1. YouTube 자동 업로드 품질 개선 및 최적화 ⭐ **현재 집중 목표**

**목표**: YouTube Shorts 자동 업로드의 품질과 안정성을 지속적으로 개선

**현재 상태**:

- ✅ YouTube 자동 업로드 기능 완성 및 안정화
- ✅ TREND_MODE 가중치 시스템 구현 완료
- ✅ 영어 콘텐츠 생성 지원 완료
- ✅ 자막 동기화 및 가독성 개선 완료

**필요한 작업**:

- [ ] 영상 품질 지속적 개선
  - [x] AI 스크립트 생성 프롬프트 최적화 (2025 전략 반영: Loop, CTA, Mindset Flip)
  - [x] 배경 영상 선택 알고리즘 개선 (문장별 키워드 우선, 추상적 키워드 처리)
  - [x] 썸네일 최적화 (DALL-E 3 활용 강화: 동적 스타일 및 클릭 유도 프롬프트)
- [ ] 성과 분석 및 최적화
  - [x] 조회수, 참여도 데이터 분석 (AnalyticsManager 구현 완료)
  - [x] 주제별 성과 추적 및 자동 필터링 (AnalyticsManager 기능 추가 완료)
  - [x] 최적 업로드 시간 분석 (AnalyticsManager 기능 추가 완료)
- [ ] 안정성 개선
  - [x] 에러 처리 및 재시도 로직 강화 (retry decorator 구현 및 주요 API에 적용 완료)
  - [x] API 할당량 관리 개선 (QuotaManager 구현 완료)
  - [x] 로깅 및 모니터링 강화 (logger 및 performance_tracker 구현 완료)

**참고 사항**:

- TikTok과 Instagram 연결은 복잡도가 높아 현재는 보류 (2025-11-21 결정)
- YouTube에 집중하여 품질과 수익을 극대화하는 것이 우선

## 📅 중기 목표

### 2. 주제 자동 업데이트 시스템

**목표**: YouTube 트렌드와 계절을 고려하여 주제를 자동으로 업데이트

**필요한 작업**:

- [x] 트렌드 수집 시스템 구축 ✅

  - [x] YouTube 트렌드 키워드 수집 (YouTube Data API v3) ✅
  - [x] YouTube 인기 Shorts 분석 및 키워드 추출 ✅
  - [x] 수집한 트렌드 키워드를 주제 풀에 자동 추가 ✅
- [x] 계절별 주제 자동 업데이트 ✅
  - [x] 현재 계절 감지 로직 개선 (이미 구현됨, 추가 개선 가능) ✅
  - [x] 계절별 트렌드 키워드와 기존 주제 매칭 ✅
  - [x] 새로운 계절별 주제 자동 생성 ✅
- [x] 주제 데이터베이스 관리 ✅
  - [x] 주제 데이터베이스 스키마 설계 ✅
  - [x] 주제 추가/삭제/업데이트 API ✅
  - [x] 주제 성과 추적 (조회수, 참여도 등) ✅
  - [x] 성과가 낮은 주제 자동 필터링 ✅
- [x] AI 기반 주제 생성 ✅
  - [x] 트렌드 키워드를 기반으로 AI가 새로운 주제 생성 ✅
  - [x] 주제 품질 검증 로직 ✅
  - [x] 중복 주제 방지 ✅

**기술적 고려사항**:

- 각 플랫폼의 API 할당량 및 제한사항
- 트렌드 데이터 수집 주기 (일별, 주별)
- 주제 업데이트 주기 및 전략
- 데이터 저장 및 관리 방법

### 3. 영상 콘텐츠 및 퀄리티 업그레이드

**목표**: 영상의 내용과 퀄리티를 지속적으로 개선하여 시청자 참여도 및 수익 증가

**필요한 작업**:

- [x] 콘텐츠 품질 개선 ✅

  - [x] AI 스크립트 생성 프롬프트 개선 ✅
  - [x] 더 매력적인 Hook 생성 로직 개선 ✅
  - [x] 스토리텔링 구조 개선 ✅
  - [x] 정보 전달 방식 최적화 ✅
- [ ] 영상 시각적 품질 개선
  - [ ] 배경 영상/이미지 선택 알고리즘 개선
  - [ ] 자막 디자인 및 스타일 개선
  - [ ] 전환 효과 및 애니메이션 추가
  - [ ] 색상 및 조명 최적화
- [ ] 음성 품질 개선
  - [ ] TTS 음성 자연스러움 개선
  - [ ] 발음 정확도 향상
  - [ ] 감정 표현 추가 (선택적)
  - [ ] 배경 음악 추가 옵션
- [ ] A/B 테스트 시스템
  - [ ] 다양한 스타일의 영상 생성 및 테스트
  - [ ] 성과 데이터 수집 및 분석
  - [ ] 최적 스타일 자동 선택

- [ ] 썸네일 최적화
  - [ ] AI 기반 썸네일 자동 생성
  - [ ] 클릭률 최적화 썸네일 선택
  - [ ] 플랫폼별 썸네일 최적화

**성과 측정**:

- 조회수 증가율
- 평균 시청 시간
- 좋아요/댓글/공유 수
- 구독자 전환율
- 수익 증가율

## 🔮 장기 목표

### 4. 고급 분석 및 최적화

- [ ] 머신러닝 기반 성과 예측

- [ ] 자동 최적화 시스템 (주제, 시간, 스타일 등)
- [ ] 경쟁사 분석 및 벤치마킹
- [ ] 시청자 세그먼트 분석

### 5. 확장성 개선

- [ ] 여러 채널 동시 관리

- [ ] 콘텐츠 큐 관리 시스템
- [ ] 예약 업로드 고도화
- [ ] 클라우드 배포 옵션

### 6. 사용자 경험 개선

- [ ] 웹 대시보드 개발

- [ ] 실시간 통계 및 리포트
- [ ] 알림 시스템
- [ ] 설정 UI 개선

## 💡 아이디어 및 제안

### 콘텐츠 관련

- [ ] 시리즈 콘텐츠 생성 (연속된 주제로 여러 영상)
- [ ] 사용자 요청 주제 반영 시스템
- [ ] 댓글 기반 다음 주제 제안
- [ ] 협업 콘텐츠 (게스트 등)

### 2025 콘텐츠 전략 (New)
- [x] **마인드셋 플립 (Mindset Flip)**: 부정적 생각을 긍정적으로 뒤집는 15초 영상 (프롬프트 반영 완료)
- [x] **금융 팩트 폭격**: "매일 커피값 아끼면 10년 뒤 얼마?"와 같은 충격적인 숫자 제시 (프롬프트 반영 완료)
- [ ] **생산성 툴 추천**: "내 인생을 바꾼 앱 3가지" 시리즈
- [x] **루프형 구조 도입**: 영상의 끝이 시작과 자연스럽게 이어지도록 스크립트 작성 (프롬프트 반영 완료)
- [x] **인터랙티브 질문**: 영상 마지막에 구체적인 질문을 던져 댓글 유도 ("당신의 2025년 목표는 무엇인가요?") (프롬프트 반영 완료)

### 기술 관련

- [ ] 영상 생성 속도 최적화
- [ ] 병렬 처리로 여러 영상 동시 생성
- [ ] 캐싱 시스템으로 API 호출 최소화
- [ ] 에러 복구 및 자동 재시도 개선
- [ ] FFmpeg 기반 무음 제거 + CFR 고정 파이프라인 검토 (GPT 제안 사항)

### 수익화 관련

- [ ] 스폰서십 자동 매칭
- [ ] 제품 추천 시스템
- [ ] 아필리에이트 링크 자동 삽입
- [ ] 크라우드펀딩 연계

## 📝 참고 사항

### 우선순위 기준

1. **단기 목표**: 즉시 시작 가능하고 빠른 결과를 낼 수 있는 작업
2. **중기 목표**: 몇 주~몇 달에 걸쳐 진행하는 중요한 기능
3. **장기 목표**: 장기적인 비전과 전략적 목표

### 작업 시작 전 체크리스트

- [ ] HISTORY.md 확인하여 프로젝트 맥락 파악
- [ ] 관련 문서 확인 (README.md, API_SETUP.md 등)
- [ ] 기존 코드 구조 이해
- [ ] 필요한 API 키 및 권한 확인
- [ ] 테스트 계획 수립

### 진행 상황 업데이트

- 작업 시작 시 해당 항목에 `[진행 중]` 표시
- 작업 완료 시 `[x]` 체크박스 체크
- 중요한 결정사항은 HISTORY.md에 기록

---

**마지막 업데이트**: 2025-11-22 (구독자 수 증가 전략 적용 완료)

**다음 리뷰 예정일**: 작업 진행에 따라 업데이트

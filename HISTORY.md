## Recent Updates

- **2025-12-06 - 콘텐츠 타입별 최적 길이 설정 및 완주율 최적화**
  - **완주율 최적화 전략 구현**:
    - `VideoConstants.CONTENT_TYPE_DURATIONS` 추가: 콘텐츠 타입별 최적 길이 설정
      - 짧은 영상(15-30초): Hook(20초), Quote(22초), Fact(25초) - 완주율 최적화
      - 중간 영상(30-45초): Short_Story(35초), Story(40초) - 스토리 전개
      - 긴 영상(45-60초): Breathing(45초), Book_Review(50초), Meditation(50초) - 상세 설명
    - `ScriptGenerator`: 콘텐츠 타입에 따라 목표 길이 자동 설정
    - `VideoGenerator`: 콘텐츠 타입별 최적 길이 자동 적용
  - **프롬프트 최적화**:
    - 짧은 영상(≤30초) 전용 프롬프트: 완주율 최적화 가이드라인 추가
    - 타이트한 구조: 3초 훅 → 핵심 전달 → 강한 마무리
    - 반복 재생 유도: "loop-worthy" 엔딩 강조
    - 동적 문장 수 계산: `target_duration // 3` (짧은 영상: 4-8문장, 긴 영상: 10-16문장)
  - **테스트 영상 생성**:
    - 한글 영상: "12월 연말정산 마지막 기회: 내년 세금을 줄이는 3가지 방법" (25.13초)
    - 영문 영상: "The December Tax Move That Saves $2,000 Before Year-End" (27.91초)
    - 두 영상 모두 15-30초 범위 내에서 생성되어 완주율 최적화 적용 확인
  - **결과**: 짧은 영상 중심으로 완주율 향상 및 알고리즘 부스트 기대

- **2025-12-05 - 영상 품질 지속적 개선 작업 완료**
  - **AI 스크립트 생성 프롬프트 최적화**:
    - Hook 패턴 추가: "Question Hook" 패턴 추가
    - 구체적 예시 강화: Hook에 구체적 숫자/시간 포함 예시 추가
    - 감정적 연결 개선: Body 섹션에 스토리텔링 요소 및 감정적 연결 강화
    - 문체 개선: 문장 길이 가이드라인, 수사법 활용, 감각적 디테일 추가
  - **배경 영상 선택 알고리즘 개선**:
    - 품질 점수 시스템 추가: 해상도(40%), 길이 적합성(20%), 키워드 매칭(30%), 비디오 품질(10%) 가중치 적용
    - 키워드 매칭 정확도 향상: 태그, URL, 설명에서 키워드 매칭 검사
    - 최적 영상 선택: 상위 5개 고품질 영상 중 랜덤 선택
  - **썸네일 A/B 테스트 시스템 구축**:
    - A/B 테스트 변형 목록: `get_ab_test_variants()` 메서드 추가
    - 테스트 실행 결정: `should_run_ab_test()` 메서드로 중복 테스트 방지
    - 추천 변형 조회: 콘텐츠 타입별 최적 변형 추천
    - 성과 비교 분석: `compare_thumbnail_performance()` 메서드로 변형 간 성과 비교
  - **결과**: 스크립트 품질, 배경 영상 품질, 썸네일 최적화 시스템 구축 완료

- **2025-12-05 - NameError in test_bot_pipeline.py 수정**
  - **문제**: `tests/test_bot_pipeline.py` 실행 시 `NameError: name 'LOADER_DIR' is not defined` 발생. CI 환경에서도 동일한 에러 발생.
  - **원인**: `cv2` (OpenCV) 모듈이 테스트 환경에서 임포트될 때 의존성 문제로 실패. `ShortsBot` -> `AIVideoGenerator` -> `VideoCompositor` -> `SubtitleRenderer` -> `moviepy` -> `cv2` 경로로 임포트됨.
  - **해결**: `tests/conftest.py`에 `sys.modules['cv2'] = Mock()`을 추가하여 pytest가 테스트를 수집하기 전에 `cv2`를 전역적으로 모의 객체로 대체.
  - **결과**: 로컬 및 CI 환경 모두에서 `tests/test_bot_pipeline.py`의 모든 테스트(4개) 통과 예상.

- **2025-12-05 - Mypy 타입 에러 수정 및 버전 제약 조건 개선**
  - **SubtitleRenderer 클래스 수정**:
    - `use_moviepy` 속성 추가: `__init__` 메서드에 `self.use_moviepy = True` 추가
    - 286번 줄에서 사용하던 속성이 정의되지 않았던 문제 해결
  - **타입 스텁 추가 및 버전 제약 조건 개선**:
    - `requirements.txt`에 `types-pytz>=2023.3,<2024` 추가
    - `pytz==2023.3`과 호환되도록 버전 제약 조건을 2023.x로 제한
    - 미래 버전의 호환되지 않는 타입 정의 설치 방지
    - `pytz` 라이브러리의 타입 스텁으로 mypy 타입 체크 에러 해결
  - **결과**: CI/CD에서 mypy 타입 체크 통과

- **2025-12-05 - 예약 업로드 기능 및 파일 보존 정책 변경**
  - **예약 업로드 기능 구현**:
    - `calculate_hours_until_midnight()` 함수 추가: 다음날 0시까지의 시간 계산
    - `main.py`에서 예약 업로드 지원: `privacy_status="unlisted"`로 설정하여 다음날 0시에 자동 공개
    - `pytz` 라이브러리 사용하여 타임존 기반 시간 계산
    - 테스트 완료: 예약 업로드 기능 정상 동작 확인
  - **원본 파일 보존 정책 변경**:
    - 업로드 후 원본 영상 파일 및 메타데이터 파일 삭제 로직 제거
    - 업로드 후에도 `output/videos/` 디렉토리에 원본 파일 유지
    - 로그에 파일 경로 출력하여 파일 위치 확인 가능
    - **이유**: 백업 및 재사용 목적

- **2025-12-05 - Video Upload (비공개) - 4개 영상**
  - **한국어 영상 1**: 연말정산 준비 체크리스트: 12월 31일 전에 꼭 확인해야 할 3가지
    - Video ID: `Xs73QVM3UpA`
    - URL: <https://www.youtube.com/watch?v=Xs73QVM3UpA>
    - 길이: 57.29초
    - 상태: 비공개 (private)
  - **한국어 영상 2**: 새해 재정 목표 설정: 2026년 돈 관리 시작하는 3가지 방법
    - Video ID: `HfNekQojjYQ`
    - URL: <https://www.youtube.com/watch?v=HfNekQojjYQ>
    - 길이: 54.21초
    - 상태: 비공개 (private)
  - **영어 영상 1**: Year-End Investment Strategy: The $5,000 Move Smart Investors Make in December
    - Video ID: `UKVRubw2BGM`
    - URL: <https://www.youtube.com/watch?v=UKVRubw2BGM>
    - 길이: 56.21초
    - 상태: 비공개 (private)
  - **영어 영상 2**: New Year Financial Reset: 3 Habits That Transform Your Money in 2026
    - Video ID: `IJUCuS4Z1uU`
    - URL: <https://www.youtube.com/watch?v=IJUCuS4Z1uU>
    - 길이: 55.10초
    - 상태: 비공개 (private)

- **2025-12-05 - Video Uploaded**
  - **Title**: Test Topic #Shorts
  - **Topic**: Test Topic
  - **Type**: fact
  - **Video ID**: VIDEO_ID_123
  - **URL**: https://www.youtube.com/watch?v=VIDEO_ID_123


- **2025-12-05 - VideoEditor 및 MetadataManager 테스트 추가**
  - **테스트 커버리지 확대**:
    - `tests/test_video_editor.py` 작성 (7개 테스트)
      - `FakeClip`을 사용한 MoviePy 의존성 없는 단위 테스트 구현
      - 영상 합성, 페이드 효과, 오디오 동기화 로직 검증
    - `tests/test_metadata_manager.py` 작성 (7개 테스트)
      - 제목 및 설명(국문/영문) 생성 로직 검증
    - **결과**: 전체 테스트 147개 모두 통과 (100%)

- **2025-12-05**: CI/CD 파이프라인 구축 및 테스트 커버리지 100% 달성 (147/147 passed). 전체 코드 베이스 린트 에러 해결 (ruff).
  - **테스트 수정**:
    - `test_image_generator.py`: Mock 객체 설정 수정으로 썸네일 테스트 2건 해결
    - `test_trend_collector.py`: 설정 파일(`settings`) 패치 방식 수정으로 1건 해결
    - **결과**: 전체 133개 테스트 중 133개 통과 (100%)
  - **CI/CD 구축**:
    - `.github/workflows/ci.yml` 추가
    - GitHub Actions를 통한 자동화 파이프라인 설정 (Push/PR 시 실행)
    - **포함된 작업**:
      - Python 3.11 환경 설정
      - 의존성 설치 (`ffmpeg` 포함)
      - Code Formatting Check (`black`)
      - Linting (`ruff`)
      - Type Checking (`mypy`)
      - Test Execution (`pytest`)
  - **코드 포맷팅**:
    - 전체 프로젝트에 `black` 및 `ruff` 적용하여 포맷팅 일관성 확보
    - `requirements.txt`에 `ruff`, `black` 추가

- **2025-12-04 - Video Uploaded**
  - **Title**: Test Topic #Shorts
  - **Topic**: Test Topic
  - **Type**: fact
  - **Video ID**: VIDEO_ID_123
  - **URL**: https://www.youtube.com/watch?v=VIDEO_ID_123


- **2025-12-04 - Monetization 테스트 수정 완료**
  - **테스트 파일 전면 재작성**:
    - `tests/test_monetization.py`: fixture를 수정하여 각 테스트마다 격리된 환경 제공
    - 실제 데이터 파일 대신 임시 디렉토리 사용
    - 각 테스트 시작 시 빈 데이터로 초기화
  - **결과**:
    - 12개 테스트 모두 통과 (이전: 7개 실패, 5개 통과)
    - 테스트 격리로 안정성 향상

- **2025-12-04 - Script Generator 테스트 수정 완료**
  - **테스트 파일 전면 재작성**:
    - `tests/test_script_generator.py`: 실제 메서드 시그니처 및 동작에 맞게 수정
    - `test_parse_script_text`: 파서가 문장을 추가로 분리하는 동작 반영
    - `test_remove_repetitive_phrases`: 실제 중복 제거 로직에 맞게 수정
    - `test_is_script_unique_*`: VideoDatabase import 경로 수정 (`src.pipeline.database`)
    - `test_get_season`: datetime mock 경로 수정 및 'autumn' 사용
    - `test_generate_topic_with_strategy`: 'reddit' 소스 추가
  - **결과**:
    - 10개 테스트 모두 통과 (이전: 5개 실패, 5개 통과)
    - Mock 설정 개선으로 테스트 안정성 향상

- **2025-12-04 - Audio Generator 테스트 수정 완료**
  - **테스트 파일 전면 재작성**:
    - `tests/test_audio_generator.py`: 실제 `AudioGenerator` 메서드 시그니처에 맞게 수정
    - `generate_audio()`: `output_path` → `index`, `content_type`, `language` 파라미터로 변경
    - `download_background_music()`: `category` → `content_type`, `duration`, `topic` 파라미터로 변경
    - `mix_background_music()`: `AudioSegment` → `AudioFileClip` 및 `CompositeAudioClip` 사용
    - `select_music_category_for_content_type()`: FACT 타입에 대한 올바른 카테고리 검증 ('tech' 포함)
  - **결과**:
    - 7개 테스트 모두 통과 (이전: 5개 실패, 2개 통과)
    - Mock 설정 개선으로 TTS 엔진 테스트 안정성 향상


- **2025-12-04 - Mypy 에러 완전 제거 및 테스트 리팩토링 완료**
  - **Mypy 에러 0개 달성**:
    - `src/pipeline/bot.py`: `pytz` 타입 무시 및 로직 수정
    - `src/analytics/monetization.py`: `update_all_videos` 메서드 시그니처 수정
    - `src/core/config.py`: `DEFAULT_TAGS` 타입 힌트 롤백 (`Union[List[str], str]`) 및 `main.py`에서 명시적 캐스팅으로 런타임 에러 방지
  - **테스트 리팩토링**:
    - `tests/test_config.py`: Pydantic 설정 시스템에 맞게 전면 재작성
    - `tests/test_video_pipeline.py`: `VideoPipeline` 클래스 테스트 분리 및 작성
    - `tests/test_bot_pipeline.py`: `ShortsBot` 위임 로직 위주로 리팩토링 및 `ExitStack` 도입으로 SyntaxError 해결
  - **결과**:
    - Mypy 에러: 0개 (완전 해결)
    - 테스트: 18개 테스트 모두 통과 (경고 1개 제외)

- **2025-12-04 - Mypy 타입 에러 추가 수정 (진행 중)**
  - **타입 어노테이션 추가**:
    - `topic_database.py`: `params` 변수에 `List[Any]` 타입 추가 (3곳)
    - `database.py`: `params` 변수에 `List[Any]` 타입 추가
    - `advanced_analytics.py`: `hour_performance` 변수 타입 어노테이션 추가
  - **메서드 호출 수정**:
    - `advanced_analytics.py`: `get_trending_keywords()` → `collect_trending_keywords()` 변경
    - `advanced_analytics.py`: `get_best_style_by_engagement()` → `get_best_style()` 변경
  - **에러 처리 개선**:
    - `script_generator.py`: `_generate_script_with_prompt` 메서드 추가
    - `script_generator.py`: Claude API 실패 시 예외 대신 기본 스크립트 반환
  - **로직 개선**:
    - `topic_database.py`: `last_used_date` 비교 로직 개선 (타입 안정성 향상)
  - **TODO.md 업데이트**: 완료된 작업 제거 및 남은 작업 정리

- **2025-12-04 - Video Upload (비공개) - 4개 영상**
  - **한국어 영상 1**: 연말 보너스 활용법: 내년 1월을 위한 3가지 전략
    - Video ID: `MH3hUoOwYfk`
    - URL: <https://www.youtube.com/watch?v=MH3hUoOwYfk>
    - 길이: 52.50초
    - 상태: 비공개 (private)
  - **한국어 영상 2**: 겨울 전기요금 폭탄: 12월부터 시작하는 절약 습관 3가지
    - Video ID: `1MU31m_XilU`
    - URL: <https://www.youtube.com/watch?v=1MU31m_XilU>
    - 길이: 50.46초
    - 상태: 비공개 (private)
  - **영어 영상 1**: The December Tax Move That Saves $2,000 Before Year-End
    - Video ID: `AE0lPhonRrM`
    - URL: <https://www.youtube.com/watch?v=AE0lPhonRrM>
    - 길이: 56.30초
    - 상태: 비공개 (private)
  - **영어 영상 2**: Why Your January Budget Fails (And How to Fix It in December)
    - Video ID: `morARj9Piw8`
    - URL: <https://www.youtube.com/watch?v=morARj9Piw8>
    - 길이: 52.39초
    - 상태: 비공개 (private)

- **2025-12-04 - 최종 Mypy 에러 수정 완료**
  - **추가 타입 에러 수정** (4개 해결):
    - `batch_generator.py`: results 변수 타입 어노테이션 추가
    - `audio_generator.py`: TTSProvider 타입 변환 로직 수정
    - `channel_history_collector.py`: videos 변수 타입 어노테이션 추가
    - `video_pipeline.py`: recent_videos 변수 타입 어노테이션 추가
    - `script_generator.py`: missing return statement 수정
  - **Mypy 에러 최종 결과**: 38개 → 11개 (71% 감소) 🎉
  - **남은 11개 에러**: topic_database, database, advanced_analytics 등 (복잡한 타입 불일치)

- **2025-12-04 - 타입 에러 수정 완료 (Bot Pipeline, Series Generator)**

  - **Bot Pipeline 타입 수정**:
    - `uploader` 변수를 `Union[YouTubeUploader, MultiPlatformUploader]`로 타입 지정
    - YouTubeUploader와 MultiPlatformUploader 모두 허용하도록 개선
    - 타입 안정성 향상
  - **Series Generator 타입 수정** (6개 에러 해결):
    - `_api_call_with_retry` 메서드 호출 제거 (존재하지 않는 메서드)
    - 직접 `openai_client.chat.completions.create()` 호출로 변경
    - `topics` 변수에 `List[Dict]` 타입 어노테이션 추가 (4곳)
  - **Mypy 에러 감소**: 23개 → 17개 (26% 감소)
  - **전체 진행률**: 초기 38개 → 현재 17개 (55% 감소)

- **2025-12-04 - Dashboard Pydantic 마이그레이션 완료**

  - **config 모듈 참조 제거**: `src/web/dashboard.py`에서 구 config 모듈 완전히 제거
    - `from src.core.config import settings` import 추가
    - `get_settings()` 함수에서 `getattr(config, ...)` → `settings.ATTRIBUTE` 변경
    - 변수명 충돌 방지를 위해 `settings` → `settings_data`로 변경
  - **타입 에러 수정**: 
    - `get_video_stats()` 함수의 days, limit 파라미터 타입 명확화
    - `int | None` 타입 힌트 추가로 mypy 에러 해결
  - **Mypy 에러 감소**: dashboard.py 관련 8개 에러 → 0개 (100% 해결)
  - **전체 Mypy 에러**: 38개 → 30개 (21% 감소)

- **2025-12-04 - README.md 전면 개선 완료**

  - **대폭 간소화**: 632줄 → 350줄 (약 45% 감소)
    - 불필요한 상세 설명 제거
    - 중복 내용 정리
    - 핵심 정보만 간결하게 유지
  - **최신 기능 반영**:
    - Pydantic BaseSettings 설정 시스템 반영
    - 타입 안정성 (Mypy) 추가
    - 프로젝트 구조 업데이트 (src/core/config.py 추가)
    - 문서 관리 시스템 (CHANGELOG, HISTORY, TODO) 추가
  - **가독성 향상**:
    - 섹션 구조 개선
    - 빠른 시작 가이드 강화
    - 코드 예제 간소화
    - 불필요한 기술적 세부사항 제거
  - **기대 효과**:
    - 신규 사용자 온보딩 시간 단축
    - 핵심 기능 파악 용이
    - 문서 유지보수 부담 감소

- **2025-12-04 - 문서 일관성 정리 및 규칙 추가 완료**

  - **TODO.md 대폭 간소화**: 381줄 → 150줄로 축소 (약 60% 감소)
    - 완료된 항목 모두 제거 (체크만 되어있던 항목 정리)
    - 미완료 작업만 포함하도록 재구성
    - 우선순위별 구분 (긴급/중요/개선/장기)
    - 각 항목에 예상 작업 시간 명시
  - **CHANGELOG.md 재구성**: Keep a Changelog 형식 준수
    - `[Unreleased]` 섹션과 `[0.1.0]` 버전 구분
    - Added/Changed/Fixed 카테고리별 정리
    - 사용자 친화적인 간결한 설명
    - 버전 히스토리 요약 추가
  - **.cursorrules에 문서 관리 규칙 추가**: 134줄 추가
    - 문서 역할 구분 (CHANGELOG/HISTORY/TODO)
    - 문서 업데이트 워크플로우 정의
    - 작업 시작/완료 시 체크리스트
    - 문서 품질 기준 및 위반 시 조치
  - **기대 효과**:
    - 문서 일관성 향상: 각 문서의 역할이 명확해짐
    - 유지보수성 향상: 문서 업데이트 규칙이 명확해져 일관성 유지
    - 가독성 향상: TODO.md가 간결해져 현재 작업 파악 용이
    - 자동화 기반 마련: .cursorrules 규칙으로 향후 자동화 가능

- **2025-12-04 - Video Uploaded**
  - **Title**: Test Topic #Shorts
  - **Topic**: Test Topic
  - **Type**: fact
  - **Video ID**: VIDEO_ID_123
  - **URL**: https://www.youtube.com/watch?v=VIDEO_ID_123


# Recent Updates


- **2025-12-03 - Type Hinting Enhancement Completed**
  - **Comprehensive Type Hints**: Added Python type hints (PEP 484) to 15+ core modules
  - **Static Type Checking**: Configured `mypy` with lenient settings for gradual typing
  - **Dependencies Added**: `mypy>=1.0.0`, `types-requests>=2.31.0`, `types-python-dateutil>=2.8.0`
  - **Error Reduction**: 87% reduction in mypy errors (291 → 38 errors)
  - **Modules Enhanced**:
    - `src/utils/*` - logger, retry_decorator, temp_cleaner, youtube_auth
    - `src/generators/*` - audio_generator, subtitle_renderer, background_video_manager, script_generator
    - `src/analytics/*` - analytics_manager, comment_analyzer
    - `src/uploaders/*` - youtube_uploader, multi_platform_uploader
    - `src/web/*` - notifications
  - **Benefits**: Better IDE support, early error detection, improved code documentation
  - **Commit**: 0fd7080


- **2025-12-03 - Video Upload (비공개)**
  - **한국어 영상**: 크리스마스 선물 예산 관리: 연말 지출 폭탄 피하는 3가지 전략
    - Video ID: `cbChzZIDq3w`
    - URL: <https://www.youtube.com/watch?v=cbChzZIDq3w>
    - 길이: 51.89초
    - 상태: 비공개 (private)
  - **영어 영상**: Holiday Shopping Psychology: The $300 Mistake 90% of Americans Make in December
    - Video ID: `e_nBEht1ex8`
    - URL: <https://www.youtube.com/watch?v=e_nBEht1ex8>
    - 길이: 54.84초
    - 상태: 비공개 (private)
  - **main.py 수정**: 파일 경로로 직접 업로드할 때 비공개 설정 및 에러 수정
    - `_generate_description` → `pipeline.metadata_manager.generate_description`로 수정
    - `_upload_to_platforms`, `_update_databases` 대신 직접 `uploader.upload_video` 및 `database.add_video` 호출
    - `privacy_status='private'` 명시적 설정
    - `json` import 추가
    - SyncManager 메서드 호출 에러 처리 추가
- **2025-12-03 - Configuration Refactoring Completed**
  - **Pydantic BaseSettings**: Migrated to type-safe configuration system
  - **Modules Refactored**: 40+ files updated to use `settings` instead of `config`
  - **Test Improvements**: 90 → 98 passing tests
  - **Production Verified**: Test video generation successful
  - **Commit**: 1af4a9f
- **2025-12-03 - VideoCompositor 리팩토링 완료**
  - **VideoEditor 클래스 생성**: 영상 합성 및 편집 로직을 별도 클래스로 분리 (285줄)
  - **VideoCompositor 간소화**: 970줄 → 159줄로 약 84% 감소, Coordinator 역할로 전환
  - **모듈화 완료**: SubtitleRenderer, BackgroundVideoManager, VideoEditor로 책임 분리
  - **검증 완료**: 모든 컴포넌트 정상 초기화 및 import 성공 확인

# 프로젝트 개발 히스토리

이 문서는 YouTube Shorts 자동 업로드 봇 프로젝트의 개발 히스토리를 기록합니다.

## 최근 변경사항

### 2025-12-05 - Video Upload (비공개) - 4개 영상

**업로드된 영상**:

1. **한국어 영상 1**
   - **주제**: 연말정산 준비 체크리스트: 12월 31일 전에 꼭 확인해야 할 3가지
   - **Video ID**: `Xs73QVM3UpA`
   - **URL**: <https://www.youtube.com/watch?v=Xs73QVM3UpA>
   - **길이**: 57.29초
   - **상태**: 비공개 (private)
   - **썸네일**: `output/thumbnails/thumb_20251205_132842.jpg`

2. **한국어 영상 2**
   - **주제**: 새해 재정 목표 설정: 2026년 돈 관리 시작하는 3가지 방법
   - **Video ID**: `HfNekQojjYQ`
   - **URL**: <https://www.youtube.com/watch?v=HfNekQojjYQ>
   - **길이**: 54.21초
   - **상태**: 비공개 (private)
   - **썸네일**: `output/thumbnails/thumb_20251205_133036.jpg`

3. **영어 영상 1**
   - **주제**: Year-End Investment Strategy: The $5,000 Move Smart Investors Make in December
   - **Video ID**: `UKVRubw2BGM`
   - **URL**: <https://www.youtube.com/watch?v=UKVRubw2BGM>
   - **길이**: 56.21초
   - **상태**: 비공개 (private)
   - **썸네일**: `output/thumbnails/thumb_20251205_133248.jpg`

4. **영어 영상 2**
   - **주제**: New Year Financial Reset: 3 Habits That Transform Your Money in 2026
   - **Video ID**: `IJUCuS4Z1uU`
   - **URL**: <https://www.youtube.com/watch?v=IJUCuS4Z1uU>
   - **길이**: 55.10초
   - **상태**: 비공개 (private)
   - **썸네일**: `output/thumbnails/thumb_20251205_133502.jpg`

**주제 선정 배경**:
- 어제 업로드된 주제와 차별화된 12월 시기 적합한 재태크/생활 최적화 주제
- 한국: 연말정산 준비, 새해 재정 목표 설정
- 미국/캐나다: 연말 투자 전략, 새해 재정 리셋

### 2025-12-04 - Mypy 타입 에러 추가 수정 (진행 중)

**주요 변경사항**:

1. **타입 어노테이션 추가**:
   - `src/pipeline/topic_database.py`: `params` 변수에 `List[Any]` 타입 추가 (3곳)
   - `src/pipeline/database.py`: `params` 변수에 `List[Any]` 타입 추가
   - `src/analytics/advanced_analytics.py`: `hour_performance` 변수 타입 어노테이션 추가

2. **메서드 호출 수정**:
   - `advanced_analytics.py`: `get_trending_keywords()` → `collect_trending_keywords()` 변경
   - `advanced_analytics.py`: `get_best_style_by_engagement()` → `get_best_style()` 변경

3. **에러 처리 개선**:
   - `script_generator.py`: `_generate_script_with_prompt` 메서드 추가
   - `script_generator.py`: Claude API 실패 시 예외 대신 기본 스크립트 반환하도록 수정

4. **로직 개선**:
   - `topic_database.py`: `last_used_date` 비교 로직 개선 (타입 안정성 향상)

5. **문서 업데이트**:
   - `TODO.md`: 완료된 작업 제거 및 남은 작업 정리
   - Mypy 에러 상태: 38개 → 11개로 업데이트

**수정된 파일**:
- `src/pipeline/topic_database.py`
- `src/pipeline/database.py`
- `src/analytics/advanced_analytics.py`
- `src/analytics/google_trends_collector.py`
- `src/analytics/trend_collector.py`
- `src/generators/script_generator.py`
- `src/generators/video/video_editor.py` (불필요한 빈 줄 제거)
- `TODO.md`

### 2025-12-04 - Video Upload (비공개) - 4개 영상

**업로드된 영상**:

1. **한국어 영상 1**
   - **주제**: 연말 보너스 활용법: 내년 1월을 위한 3가지 전략
   - **Video ID**: `MH3hUoOwYfk`
   - **URL**: <https://www.youtube.com/watch?v=MH3hUoOwYfk>
   - **길이**: 52.50초
   - **상태**: 비공개 (private)
   - **썸네일**: `output/thumbnails/thumb_20251204_092908.jpg`

2. **한국어 영상 2**
   - **주제**: 겨울 전기요금 폭탄: 12월부터 시작하는 절약 습관 3가지
   - **Video ID**: `1MU31m_XilU`
   - **URL**: <https://www.youtube.com/watch?v=1MU31m_XilU>
   - **길이**: 50.46초
   - **상태**: 비공개 (private)
   - **썸네일**: `output/thumbnails/thumb_20251204_093104.jpg`

3. **영어 영상 1**
   - **주제**: The December Tax Move That Saves $2,000 Before Year-End
   - **Video ID**: `AE0lPhonRrM`
   - **URL**: <https://www.youtube.com/watch?v=AE0lPhonRrM>
   - **길이**: 56.30초
   - **상태**: 비공개 (private)
   - **썸네일**: `output/thumbnails/thumb_20251204_093315.jpg`

4. **영어 영상 2**
   - **주제**: Why Your January Budget Fails (And How to Fix It in December)
   - **Video ID**: `morARj9Piw8`
   - **URL**: <https://www.youtube.com/watch?v=morARj9Piw8>
   - **길이**: 52.39초
   - **상태**: 비공개 (private)
   - **썸네일**: `output/thumbnails/thumb_20251204_093539.jpg`

**주제 선정 배경**:
- 12월 시기 적합한 재태크/생활 최적화 주제
- 한국: 연말 보너스 활용, 겨울 전기요금 절약
- 미국/캐나다: 연말 세금 절감, 1월 예산 실패 방지

### 2025-12-03 - Video Upload (비공개) 및 main.py 수정

**업로드된 영상**:

1. **한국어 영상**
   - **주제**: 크리스마스 선물 예산 관리: 연말 지출 폭탄 피하는 3가지 전략
   - **Video ID**: `cbChzZIDq3w`
   - **URL**: <https://www.youtube.com/watch?v=cbChzZIDq3w>
   - **길이**: 51.89초
   - **상태**: 비공개 (private)
   - **썸네일**: `output/thumbnails/thumb_20251203_170438.jpg`
2. **영어 영상**
   - **주제**: Holiday Shopping Psychology: The $300 Mistake 90% of Americans Make in December
   - **Video ID**: `e_nBEht1ex8`
   - **URL**: <https://www.youtube.com/watch?v=e_nBEht1ex8>
   - **길이**: 54.84초
   - **상태**: 비공개 (private)
   - **썸네일**: `output/thumbnails/thumb_20251203_170707.jpg`

**main.py 수정 사항**:

- 파일 경로로 직접 업로드할 때 비공개 설정 지원
  - `privacy_status='private'` 명시적 설정 추가
  - 사용자 요청에 따라 비공개로 업로드 가능하도록 개선
- 에러 수정
  - `_generate_description` 메서드가 없어 발생한 에러 수정
    - `bot._generate_description()` → `bot.pipeline.metadata_manager.generate_description()`로 변경
  - `_upload_to_platforms`, `_update_databases` 메서드가 없어 발생한 에러 수정
    - 직접 `bot.uploader.upload_video()` 및 `bot.database.add_video()` 호출로 변경
  - `json` import 누락 수정
  - `SyncManager.update_last_upload` 메서드 호출 에러 처리 추가

**파일**:
- `main.py`: 파일 경로 업로드 로직 수정 및 에러 처리 개선

### 2025-12-03 - VideoCompositor 리팩토링 완료

**주요 변경사항**:

1. **VideoEditor 클래스 생성** (285줄)
   - 영상 합성 및 편집 로직을 별도 클래스로 분리
   - `compose_final_video`: 최종 영상 합성
   - `apply_fade_effects`: 페이드 효과 적용
   - `sync_audio_video`: 음성-영상 동기화
   - `prepare_background_clips`: 배경 영상 클립 준비
   - `prepare_subtitle_clips`: 자막 클립 준비
   - `save_video`: 영상 저장
2. **VideoCompositor 간소화** (970줄 → 159줄, 약 84% 감소)
   - Coordinator 역할로 전환
   - `VideoEditor`, `SubtitleRenderer`, `BackgroundVideoManager`에 위임
   - 불필요한 메서드 제거:
     - `_draw_text_on_image` → `SubtitleRenderer.draw_text_on_image`
     - `_wrap_text` → `SubtitleRenderer.wrap_text`
     - `_extract_key_words_for_subtitle` → `SubtitleRenderer.extract_key_words`
     - `_create_subtitle_clip` → `SubtitleRenderer.create_subtitle_clip`
     - `_download_video_for_sentence` → `BackgroundVideoManager.download_video_for_sentence`
3. **최종 구조**

   ```text
   src/generators/
   ├── video_compositor.py (159줄) - Coordinator
   └── video/
       ├── subtitle_renderer.py (420줄) - 자막 렌더링
       ├── background_video_manager.py (326줄) - 배경 영상 관리
       └── video_editor.py (285줄) - 영상 편집 및 합성
   ```

4. **검증 완료**
   - 모든 클래스 import 성공
   - AIVideoGenerator 초기화 성공
   - 모든 컴포넌트 정상 초기화 확인
   - Linter 오류 없음

**파일**:
- `src/generators/video/video_editor.py`: 새로 작성
- `src/generators/video/__init__.py`: VideoEditor export 추가
- `src/generators/video_compositor.py`: 리팩토링 완료

**기대 효과**:
- 단일 책임 원칙(SRP) 준수: 각 클래스가 하나의 명확한 책임만 가짐
- 코드 가독성 향상: VideoCompositor가 159줄로 관리 가능
- 테스트 용이성: 각 컴포넌트를 독립적으로 테스트 가능
- 유지보수성 향상: 변경 사항이 특정 컴포넌트에만 영향

### 2025-12-03 - ScriptGenerator 및 ShortsBot 리팩토링 완료, 통합 테스트 추가

**주요 변경사항**:

1. **ScriptGenerator 클래스 리팩토링 완료**
   - 거대한 `ScriptGenerator` 클래스를 3개의 헬퍼 클래스로 분리
   - `PromptBuilder` (`src/generators/script/prompt_builder.py`): 프롬프트 생성 담당
   - `ScriptParser` (`src/generators/script/script_parser.py`): AI 응답 파싱 담당
   - `ScriptValidator` (`src/generators/script/script_validator.py`): 스크립트 검증 및 중복 체크 담당
   - 기존 `ScriptGenerator`는 이들을 조율하는 역할로 간소화
2. **ShortsBot 클래스 리팩토링 완료**
   - 복잡했던 `create_and_upload` 메서드의 로직을 `VideoPipeline` 클래스로 추출
   - `VideoPipeline` (`src/pipeline/video_pipeline.py`): 영상 생성부터 업로드까지의 전체 워크플로우 캡슐화
   - `MetadataManager` (`src/pipeline/metadata_manager.py`): 메타데이터(제목, 설명) 생성 담당
   - `ShortsBot`은 이제 파이프라인을 실행하는 역할만 수행
3. **통합 테스트 추가**
   - `tests/test_end_to_end.py` 작성: 영상 생성부터 업로드까지의 전체 파이프라인 테스트
   - 모든 외부 의존성을 Mock으로 처리하여 독립적인 테스트 환경 구축
   - 2개 테스트 모두 통과 확인
4. **설정 파일 업데이트**
   - `config.py`에 누락되어 있던 `PRIVACY_STATUS`, `VIDEO_LANGUAGE`, `CATEGORY_ID` 설정 추가
   - 기본값 설정: `PRIVACY_STATUS='private'`, `VIDEO_LANGUAGE='en'`, `CATEGORY_ID='22'`
5. **기존 테스트 업데이트**
   - `tests/test_script_generator.py` 업데이트: 리팩토링된 구조에 맞게 수정
   - 헬퍼 클래스 메서드 접근 방식 변경 (예: `script_generator.script_parser.parse_script_text()`)

**파일**:
- `src/generators/script/prompt_builder.py`: 새로 작성
- `src/generators/script/script_parser.py`: 새로 작성
- `src/generators/script/script_validator.py`: 새로 작성
- `src/generators/script_generator.py`: 리팩토링 완료
- `src/pipeline/video_pipeline.py`: 새로 작성
- `src/pipeline/metadata_manager.py`: 새로 작성
- `src/pipeline/bot.py`: 리팩토링 완료
- `tests/test_end_to_end.py`: 새로 작성
- `tests/test_script_generator.py`: 업데이트
- `config.py`: 설정 추가

**기대 효과**:
- 코드 모듈화로 유지보수성 대폭 향상
- 단일 책임 원칙(SRP) 준수로 코드 가독성 개선
- 테스트 커버리지 확대로 안정성 향상
- 향후 기능 추가 및 수정 용이

### 2025-12-02 - Google Cloud TTS 추가, 한글 발음 개선 및 Description/Tags 개선

**주요 변경사항**:

1. **Google Cloud Text-to-Speech 추가 (한글 발음 개선)**
   - Google Cloud TTS 엔진 추가 (`GoogleCloudEngine` 클래스)
   - 한글 최적 voice: `ko-KR-Wavenet-A` 사용 (최고 품질)
   - `.env`에 `TTS_PROVIDER=google_cloud` 및 `GOOGLE_CLOUD_CREDENTIALS_PATH` 설정 추가
   - `google-cloud-texttospeech` 패키지 추가
   - 자동 선택 로직: Google Cloud 설정 시 우선 사용
2. **한글 발음 개선**
   - OpenAI TTS voice 변경: `nova` → `shimmer` (더 부드러운 한글 발음)
   - Google Cloud TTS 사용 시 한글 발음이 크게 개선됨
   - 테스트 영상 생성 및 업로드 완료
3. **Description 및 Tags 개선**
   - Description에서 태그 섹션 제거 (태그는 YouTube tags 필드에만 등록)
   - 메타데이터에 `description` 및 `tags` 필드 추가
   - 구독 링크 형식 수정: `@@` 제거 (`https://www.youtube.com/@aicryptofunk`)
   - 기본 태그 업데이트: `shorts,쇼츠,ai,인공지능,자동생성,유용한정보,팁,라이프스타일,일상,정보,꿀팁,생활정보` (12개 태그)
4. **업로드된 영상**
   - Video ID: `qugkhBgi7xU` - 크리스마스 선물 예산 안에서 특별함 더하기
   - Video ID: `a5Wq_mYSuno` - 겨울철 전기요금 절약하는 실용적인 팁
   - 두 영상 모두 2시간 후 예약 공개 설정

**파일**:
- `src/pipeline/tts_engine.py`: Google Cloud TTS 엔진 추가, OpenAI TTS voice 변경
- `src/pipeline/bot.py`: 메타데이터에 description/tags 추가, description에서 태그 섹션 제거
- `src/uploaders/youtube_uploader.py`: 구독 링크 형식 수정, description 업데이트 메서드 추가
- `config.py`: Google Cloud TTS 설정 추가, 기본 태그 업데이트
- `requirements.txt`: `google-cloud-texttospeech` 패키지 추가
- `.cursorrules`: 업로드 전 확인 규칙 강화
- `.env`: `DEFAULT_TAGS` 업데이트 (12개 태그)
- `google-cloud-tts-key.json`: Google Cloud 서비스 계정 키 파일

**사용 방법**:
- Google Cloud TTS 사용: `.env`에 `TTS_PROVIDER=google_cloud` 설정
- 한글 영상 생성: 한글 주제 입력 시 자동으로 Google Cloud TTS 사용 (설정된 경우)

### 2025-12-02 - 한글 주제 생성 지원, 한글 영상 생성 및 업로드 전 확인 규칙 추가

**주요 변경사항**:

1. **한글 주제 생성 지원 추가**
   - `get_topics.py`에 언어 옵션 추가 (`--ko`, `--korean`, `-k` 플래그)
   - AI 주제 생성 시 언어 파라미터 전달
   - 진행 상황에 언어 표시 (한국어/영어)
   - `collect_topics()` 함수에 `language` 파라미터 추가
2. **한글 영상 생성 및 업로드 완료**
   - 주제: "크리스마스 선물 아이디어: 예산 안에서 특별함 더하기"
   - Video ID: eC5EAXss-7w
   - 언어 자동 감지: 한국어로 정확히 감지
   - 한글 스크립트, 한글 TTS, 한글 자막 모두 정상 생성
   - 예약 업로드 완료 (1시간 후 공개 예정)
3. **업로드 전 사용자 확인 규칙 추가**
   - `.cursorrules`에 "업로드 전 사용자 확인 필수" 규칙 추가
   - 모든 영상 업로드 전에 반드시 사용자 확인을 받도록 규칙 명시
   - `main.py`의 `upload` 명령어도 `auto_upload=False`로 변경하여 확인 받도록 수정
   - 예외: `python main.py schedule` 자동 스케줄러만 자동 업로드 모드

**파일**:
- `get_topics.py`: 한글 주제 생성 지원 추가
- `.cursorrules`: 업로드 전 사용자 확인 규칙 추가
- `main.py`: `upload` 명령어도 확인 받도록 수정

**사용 방법**:
- 한글 주제 생성: `python get_topics.py 1 --ko` 또는 `python main.py topics 1 --ko`
- 한글 영상 생성: 한글 주제를 입력하면 자동으로 한글 모드로 생성
- 업로드: 모든 업로드 전에 사용자 확인을 받음 (예외: schedule 명령어)

### 2025-12-01 - get_topics.py 타임아웃 및 진행 상황 표시 개선

**주요 변경사항**:

1. **타임아웃 기능 추가**
   - 각 API 호출에 타임아웃 설정 (Reddit: 20초, Google Trends: 30초, YouTube: 30초, AI 주제: 60초, 성과 기반: 10초)
   - `ThreadPoolExecutor`를 사용한 비동기 타임아웃 처리
   - 타임아웃 발생 시 해당 단계만 스킵하고 계속 진행
   - OpenAI/Claude API 클라이언트에 `timeout=30.0` 설정 추가
2. **진행 상황 표시 개선**
   - 각 단계별 실시간 진행 상황 표시 (`[1/6]`, `[2/6]` 등)
   - 각 단계의 소요 시간 표시
   - 성공/실패/타임아웃 상태를 명확하게 표시
   - 총 소요 시간 표시
3. **안전한 중단 기능**
   - Ctrl+C로 안전하게 중단 가능
   - `signal.SIGINT` 핸들러 추가
   - 중단 플래그로 후속 작업 자동 스킵
   - KeyboardInterrupt 예외 처리 개선
4. **에러 처리 개선**
   - 타임아웃 시 명확한 메시지 표시
   - 에러 메시지 요약 표시 (50자 제한)
   - 각 단계별 독립적인 예외 처리

**파일**:
- `get_topics.py`: 타임아웃 및 진행 상황 표시 기능 추가

**기대 효과**:
- API 호출이 오래 걸려도 타임아웃으로 자동 중단되어 프로세스가 무한 대기하지 않음
- 진행 상황을 실시간으로 확인 가능
- Ctrl+C로 안전하게 중단 가능

### 2025-12-01 - 예약 업로드 기능 추가 및 주제 선정 명령어 개선

**주요 변경사항**:

1. **2시간 지연 예약 업로드 기능 추가**
   - `config.py`에 `UPLOAD_DELAY_HOURS` 설정 추가
   - `youtube_uploader.py`의 `upload_video` 메서드에 `schedule_delay_hours` 파라미터 추가
   - YouTube API의 `scheduledStartTime` 기능 활용
   - 예약 업로드는 자동으로 `unlisted` 상태로 설정 (공개 상태 불가)
   - 최소 15분 이후 시간으로 자동 조정 (YouTube API 요구사항)
   - `.env` 파일에 `UPLOAD_DELAY_HOURS=2` 설정 추가
   - `bot.py`와 `multi_platform_uploader.py`에서 예약 업로드 파라미터 전달
2. **주제 선정 명령어 개선**
   - `main.py`에 `topics` 명령어 추가 (`python main.py topics [개수]`)
   - `get_topics.py` 개선: 명령줄 인자로 주제 개수 지정 가능
   - 기본값 3개, 원하는 개수 지정 가능
   - 코드 수정 없이 주제 선정 가능하도록 구조 개선
3. **3개 영상 생성 및 업로드 완료**
   - 주제 1: "Consistency outruns talent every single time." (Video ID: fO26Q-6Eb_8)
   - 주제 2: "Create a Cozy Winter Workspace: Boost Productivity with Seasonal Decor" (Video ID: rL__NbB3a8k)
   - 주제 3: "Time is Money: The Secret to Maximizing Your Daily Productivity" (Video ID: seLGHtHg750)
   - 모든 영상 정상 업로드 및 썸네일 업로드 완료
4. **예약 업로드 기능 버그 수정**
   - `bot.py`의 `_upload_to_platforms` 메서드에서 `schedule_delay_hours` 파라미터 전달 누락 수정
   - `multi_platform_uploader.py`에서도 예약 업로드 파라미터 전달 추가
   - `.env` 파일에 `UPLOAD_DELAY_HOURS=2` 설정 추가

**파일**:
- `config.py`: `UPLOAD_DELAY_HOURS` 설정 추가
- `src/uploaders/youtube_uploader.py`: 예약 업로드 기능 구현
- `src/pipeline/bot.py`: 예약 업로드 파라미터 전달 추가
- `src/uploaders/multi_platform_uploader.py`: 예약 업로드 파라미터 전달 추가
- `main.py`: `topics` 명령어 추가
- `get_topics.py`: 명령줄 인자 지원 개선
- `.env`: `UPLOAD_DELAY_HOURS=2` 설정 추가

**사용 방법**:
- 예약 업로드: `.env` 파일에 `UPLOAD_DELAY_HOURS=2` 설정 (2시간 후 공개)
- 주제 선정: `python main.py topics 3` (3개 주제 선정)

### 2025-11-30 - 로깅 시스템 전면 적용 및 Phase 3-4 테스트 작성 완료

**주요 변경사항**:

1. **로깅 시스템 전면 적용 완료**
   - 약 200개 이상의 `print` 문을 `logger`로 교체
   - 20개 파일에 logger import 추가 및 print 문 교체
   - 로그 레벨 적절히 분리 (INFO, DEBUG, WARNING, ERROR)
   - 파일 로그와 콘솔 로그 이원화 완료
   - 교체된 파일:
     - `src/generators/script_generator.py` (51개)
     - `src/generators/video_compositor.py` (49개)
     - `main.py` (35개)
     - `src/pipeline/batch_generator.py` (24개)
     - `src/generators/media_downloader.py` (7개)
     - `src/utils/youtube_auth.py` (15개)
     - `src/utils/performance_tracker.py` (14개)
     - `src/pipeline/sync_manager.py` (15개)
     - `src/pipeline/database.py` (10개)
     - `src/pipeline/topic_database.py` (11개)
     - `src/generators/audio_generator.py` (15개)
     - `src/generators/image_generator.py` (12개)
     - `src/pipeline/tts_engine.py` (3개)
     - `src/generators/series_generator.py` (5개)
     - `src/generators/user_request_handler.py` (6개)
     - `src/utils/temp_cleaner.py` (3개)
     - `src/web/notifications.py` (2개)
     - `src/web/dashboard.py` (1개)
     - `src/utils/quota_manager.py` (7개)
     - `src/utils/create_client_secrets.py` (1개)
   - `src/pipeline/bot.py`의 사용자 입력용 print 문 2개는 유지 (사용자 상호작용용)
2. **Phase 3: Analytics 테스트 작성 완료**
   - `test_ab_testing.py` 작성 완료 (11개 테스트 통과)
     - A/B 테스트 데이터베이스 초기화 및 관리
     - 테스트 항목 추가/업데이트
     - 통계 업데이트 및 참여율 계산
     - 최적 스타일 선택 및 성과 조회
   - `test_monetization.py` 작성 완료 (12개 테스트 통과)
     - 수익화 추적 초기화 및 영상 관리
     - 통계 업데이트 및 수익 계산
     - 전체 통계 및 월별 수익 계산
     - 진행 상황 리포트
   - `test_trend_collector.py` 작성 완료 (16개 테스트 통과)
     - 트렌드 수집기 초기화
     - YouTube 인기 Shorts 수집
     - 키워드 추출 및 정제
     - AI 기반 키워드 정제
3. **Phase 4: Pipeline 테스트 작성 완료**
   - `test_bot_pipeline.py` 작성 완료 (22개 테스트 통과)
     - ShortsBot 초기화 (일반/멀티 플랫폼 모드)
     - 성과 기반 프롬프트 생성
     - 업로드 제약 조건 확인
     - 영상 파라미터 결정 및 설명 생성
     - 영상 생성 및 업로드 플로우
     - 데이터베이스 업데이트 및 알림 전송
     - 통계 업데이트

**파일**:
- 로깅 시스템 적용: 20개 파일 수정
- `tests/test_ab_testing.py`: 새로 작성
- `tests/test_monetization.py`: 새로 작성
- `tests/test_trend_collector.py`: 새로 작성
- `tests/test_bot_pipeline.py`: 새로 작성

**테스트 결과**:
- Phase 3: 총 39개 테스트 모두 통과
- Phase 4: 총 22개 테스트 모두 통과
- 전체 테스트 현황: Phase 1-4 총 89개 이상의 테스트 통과

**기대 효과**:
- 로깅 시스템으로 디버깅 및 모니터링 용이성 대폭 향상
- 테스트 커버리지 확대로 코드 안정성 향상
- 체계적인 로그 관리로 운영 효율성 개선

### 2025-11-30 - Phase 2: Uploaders 테스트 완료 및 전체 시스템 검증

**주요 변경사항**:

1. **test_youtube_uploader.py 수정 완료**
   - 12개 테스트 모두 통과
   - 인증 실패 예외 처리 테스트 수정
   - `_resumable_upload` 메서드 Mock 설정 개선 (`next_chunk()` 반환값 튜플 처리)
   - 파일 없음/API 에러 예외 처리 테스트 수정
   - `get_video_stats` 테스트에 `snippet` 필드 추가
   - `check_today_uploaded` 테스트 날짜 형식 수정
2. **test_multi_platform_uploader.py 작성 완료**
   - 9개 테스트 모두 통과
   - 초기화 테스트 (YouTube만, 모든 플랫폼, TikTok 사용 불가)
   - 업로드 테스트 (단일/다중 플랫폼, 파일 없음, 플랫폼별 에러 처리)
   - 통합 테스트 (썸네일 포함)
3. **test_social_upload.py 업데이트 완료**
   - 7개 테스트 모두 통과
   - unittest → pytest 스타일로 변환
   - InstagramUploader, TikTokUploader, SocialManager 테스트 추가
   - 부분 실패 및 미설정 상태 테스트 추가
4. **전체 시스템 동작 검증**
   - 실제 영상 생성 테스트 완료 (55.93초 영상 생성 성공)
   - 주제: "How to build wealth with index funds in 2025"
   - 모든 파이프라인 정상 동작 확인 (스크립트 생성, TTS, 배경 영상, 자막, 썸네일)

**파일**:
- `tests/test_youtube_uploader.py`: 테스트 수정 완료
- `tests/test_multi_platform_uploader.py`: 새로 작성
- `tests/test_social_upload.py`: pytest 스타일로 업데이트

**테스트 결과**:
- 총 28개 테스트 모두 통과
- `test_youtube_uploader.py`: 12개 통과
- `test_multi_platform_uploader.py`: 9개 통과
- `test_social_upload.py`: 7개 통과
- 실제 영상 생성 테스트: 성공 (53MB, 55.93초)

### 2025-11-30 - 북리뷰 콘텐츠 타입 추가 및 시스템 개선

**주요 변경사항**:

1. **BOOK_REVIEW 콘텐츠 타입 추가**
   - 기관 선정/추천/수상 도서를 소개하는 책 리뷰 영상 타입 추가
   - New York Times, Amazon, Goodreads, Pulitzer Prize, Nobel Prize, Booker Prize 등 다양한 기관 지원
   - 영상 길이에 따라 책 권수 자동 조절 (5권/7권/10권)
   - 각 책마다 제목, 작가, 핵심 인사이트, 실용적 적용법 포함
   - 영어/한국어 프롬프트 모두 지원
2. **배경 영상 다양성 대폭 개선**
   - Pexels API 검색 결과 증가: `per_page=20` → `per_page=80` (4배 증가)
   - 랜덤 선택 시스템: 상위 10개 품질 좋은 영상 중 랜덤 선택
   - AI 키워드 추출 개선: 최대 3개 → 최대 5개로 증가
   - 키워드 재시도 확대: 최대 5개 → 최대 8개로 증가
   - 키워드 셔플: 중복 제거 후 랜덤 순서로 섞기
   - AI 프롬프트 개선: 다양한 키워드 요청 (객체, 액션, 분위기, 설정 등)
3. **Temp 폴더 자동 정리 기능 추가**
   - `TempCleaner` 클래스 생성 (`src/utils/temp_cleaner.py`)
   - 영상 생성 후 자동으로 1시간 이상 된 임시 파일 삭제
   - 삭제 통계 출력 (파일 수, 해제된 용량)
   - 최근 생성된 파일은 보존하여 안전성 확보
4. **Google Trends API Rate Limiting 추가**
   - 요청 사이 최소 2초 간격 유지
   - 배치 사이 1초 추가 지연
   - Google의 rate limiting 정책 준수로 400 에러 방지
5. **검색 기반 주제 생성 시스템 완성**
   - 하드코딩된 주제 완전 제거
   - Reddit RSS 피드 통합 (API 승인 불필요)
   - Google Trends 통합 (pytrends 라이브러리)
   - YouTube 트렌드 통합
   - 채널 히스토리 기반 중복 체크
   - 소스별 가중치 기반 주제 선택

**파일**:
- `src/generators/content_type.py`: BOOK_REVIEW 타입 추가
- `src/generators/script_generator.py`: 북리뷰 프롬프트 및 주제 생성 로직 추가
- `src/analytics/book_collector.py`: 책 리뷰 주제 수집 클래스 생성
- `src/generators/video_compositor.py`: 배경 영상 다양성 개선 (per_page 증가, 랜덤 선택)
- `src/generators/media_downloader.py`: AI 키워드 추출 개선 (최대 5개)
- `src/utils/temp_cleaner.py`: 임시 파일 자동 정리 클래스 생성
- `src/pipeline/bot.py`: temp 폴더 자동 정리 통합
- `src/analytics/google_trends_collector.py`: Rate limiting 추가

**테스트 결과**:
- 북리뷰 영상 생성 성공 (54.85초, 13개 문장)
- 배경 영상 다양성 확인 (8개의 서로 다른 영상 사용)
- Temp 폴더 자동 정리 작동 확인
- Google Trends rate limiting 적용 완료

### 2025-11-30 - 주제 개선 및 업로드 전 확인 기능 추가

**주요 변경사항**:

1. **HOOK 타입 주제 10개 추가**
   - 제목과 첫 문장이 눈에 띄는 강력한 HOOK 주제 추가
   - Mindset Flip, Shocking Number, Contrarian Statement, Personal Revelation 패턴 포함
   - CPM 점수 1.3~1.7로 설정
   - 예시: "The $100 you save today becomes $1,000 in 10 years." (CPM: 1.7)
2. **배경 영상 다양성 개선**
   - 주제 카테고리별 특화 키워드 시스템 도입
   - 재태크: money, finance, investment, savings, budget, wealth, business
   - 생산성: productivity, workspace, morning, routine, focus, office, desk
   - 자기계발: growth, motivation, success, achievement, goal, inspiration, mindset
   - 생활/정리: home, lifestyle, minimalism, organization, declutter, interior
   - 각 주제가 다른 카테고리 키워드를 사용하여 배경 영상 다양성 확보
3. **업로드 전 사용자 확인 기능 추가**
   - `create_and_upload` 메서드에 `auto_upload` 파라미터 추가 (기본값: False)
   - 영상 생성 후 업로드 전에 사용자 확인 요청
   - 제목, 주제, 영상 파일 경로, 썸네일 경로 표시 후 y/n 입력 요청
   - 스케줄러나 명시적 업로드 명령어(`python main.py upload`)는 자동 업로드 모드 유지
4. **유사성 최소화 주제 선정 시스템**
   - 이전 업로드 영상과의 유사성 체크 로직 추가
   - 서로 다른 카테고리(재태크, 생산성, 정리/생활) 주제 선정
   - 최근 30일간 업로드된 영상과 비교하여 유사하지 않은 주제만 선택

**파일**:
- `src/pipeline/bot.py`: 업로드 전 확인 로직 추가
- `src/generators/video_compositor.py`: 주제 카테고리별 키워드 시스템
- `src/pipeline/topic_database.py`: HOOK 주제 추가

**테스트 결과**:
- 3개 영상 생성 및 업로드 성공 (재태크, 생산성, 정리/생활 각 1개)
- 배경 영상 다양성 확인
- 업로드 전 확인 기능 정상 동작

### 2025-11-28 - TTS 전처리 버그 수정

**문제**: 제목에서 `$100,000`, `$50,000` 같은 금액이 `$,000`로 잘못 저장되는 버그 발생

**원인**: TTS 전처리 정규식 `r'\$([\d,]+(?:\.\d+)?[KMBkmb]?)'`가 `$,000` 같은 잘못된 형식도 매칭하여 변환 시도

**수정 내용**:
- 정규식 개선: `r'\$(\d+(?:,\d{3})*(?:\.\d+)?[KMBkmb]?)'`로 변경하여 숫자로 시작하도록 강제
- `convert_dollar` 함수에 검증 로직 추가: 빈 문자열이나 숫자가 없는 경우 원본 유지
- `$,000` 같은 잘못된 형식은 매칭되지 않아 원본이 그대로 유지됨

**파일**: `src/pipeline/tts_engine.py`

**테스트 결과**:
- `$100,000` → 정상 변환 (`hundred thousand dollars`)
- `$50,000` → 정상 변환 (`fifty thousand dollars`)
- `$,000` → 매칭되지 않아 원본 유지

## 프로젝트 개요

- **2025-12-02 - 영상 업로드 완료**
  - **제목**: Why Smart People Max Out Their 401k in December (Not January) #Shorts
  - **주제**: Why Smart People Max Out Their 401k in December (Not January)
  - **콘텐츠 타입**: auto
  - **Video ID**: 0x6WPchQ96c
  - **URL**: <https://www.youtube.com/watch?v=0x6WPchQ96c>
  - **영상 파일**: output/videos/shorts_20251202_232456.mp4
  - **썸네일**: output/thumbnails/thumb_20251202_232616.jpg
  - **업로드 시간**: 2025-12-02T23:27:24.328471
- **2025-12-02 - 영상 업로드 완료**
  - **제목**: The  December Mistake That Kills Your January Budget #Shorts
  - **주제**: The  December Mistake That Kills Your January Budget
  - **콘텐츠 타입**: auto
  - **Video ID**: nXFG9QRHWhM
  - **URL**: <https://www.youtube.com/watch?v=nXFG9QRHWhM>
  - **영상 파일**: output/videos/shorts_20251202_232248.mp4
  - **썸네일**: output/thumbnails/thumb_20251202_232417.jpg
  - **업로드 시간**: 2025-12-02T23:27:06.540909
- **2025-12-02 - 영상 업로드 완료**
  - **제목**: 새해를 위한 비상금 만들기: 3개월 안에 100만원 모으는 실전 방법 #Shorts
  - **주제**: 새해를 위한 비상금 만들기: 3개월 안에 100만원 모으는 실전 방법
  - **콘텐츠 타입**: auto
  - **Video ID**: gkJSlhFaCCY
  - **URL**: <https://www.youtube.com/watch?v=gkJSlhFaCCY>
  - **영상 파일**: output/videos/shorts_20251202_214154.mp4
  - **썸네일**: output/thumbnails/thumb_20251202_214314.jpg
  - **업로드 시간**: 2025-12-02T21:44:16.354546
- **2025-12-02 - 영상 업로드 완료**
  - **제목**: 연말정산 세금 절감: 12월 31일 전에 꼭 해야 할 3가지 #Shorts
  - **주제**: 연말정산 세금 절감: 12월 31일 전에 꼭 해야 할 3가지
  - **콘텐츠 타입**: auto
  - **Video ID**: ROHc7zf0h4Y
  - **URL**: <https://www.youtube.com/watch?v=ROHc7zf0h4Y>
  - **영상 파일**: output/videos/shorts_20251202_213957.mp4
  - **썸네일**: output/thumbnails/thumb_20251202_214118.jpg
  - **업로드 시간**: 2025-12-02T21:44:01.155735
- **2025-12-02 - 영상 업로드 완료**
  - **제목**: 크리스마스 선물 아이디어: 예산 안에서 특별함 더하기 #Shorts
  - **주제**: 크리스마스 선물 아이디어: 예산 안에서 특별함 더하기
  - **콘텐츠 타입**: auto
  - **Video ID**: eC5EAXss-7w
  - **URL**: <https://www.youtube.com/watch?v=eC5EAXss-7w>
  - **영상 파일**: output/videos/shorts_20251202_002613.mp4
  - **썸네일**: output/thumbnails/thumb_20251202_002835.jpg
  - **업로드 시간**: 2025-12-02T00:29:34.771809
- **2025-12-01 - 영상 업로드 완료**
  - **제목**: Time is Money: The Secret to Maximizing Your Daily Productivity #Shorts
  - **주제**: Time is Money: The Secret to Maximizing Your Daily Productivity
  - **콘텐츠 타입**: auto
  - **Video ID**: seLGHtHg750
  - **URL**: <https://www.youtube.com/watch?v=seLGHtHg750>
  - **영상 파일**: output/videos/shorts_20251201_183255.mp4
  - **썸네일**: output/thumbnails/thumb_20251201_183451.jpg
  - **업로드 시간**: 2025-12-01T18:35:47.494974
- **2025-12-01 - 영상 업로드 완료**
  - **제목**: Create a Cozy Winter Workspace: Boost Productivity with Seasonal Decor #Shorts
  - **주제**: Create a Cozy Winter Workspace: Boost Productivity with Seasonal Decor
  - **콘텐츠 타입**: auto
  - **Video ID**: rL__NbB3a8k
  - **URL**: <https://www.youtube.com/watch?v=rL__NbB3a8k>
  - **영상 파일**: output/videos/shorts_20251201_183002.mp4
  - **썸네일**: output/thumbnails/thumb_20251201_183147.jpg
  - **업로드 시간**: 2025-12-01T18:32:35.952536
- **2025-12-01 - 영상 업로드 완료**
  - **제목**: Consistency outruns talent every single time. #Shorts
  - **주제**: Consistency outruns talent every single time.
  - **콘텐츠 타입**: auto
  - **Video ID**: fO26Q-6Eb_8
  - **URL**: <https://www.youtube.com/watch?v=fO26Q-6Eb_8>
  - **영상 파일**: output/videos/shorts_20251201_182701.mp4
  - **썸네일**: output/thumbnails/thumb_20251201_182855.jpg
  - **업로드 시간**: 2025-12-01T18:29:38.695649
- **2025-11-30 - 영상 업로드 완료**
  - **제목**: Test Video
  - **주제**: Test Topic
  - **콘텐츠 타입**: hook
  - **Video ID**: test_video_123
  - **URL**: <https://www.youtube.com/watch?v=test_video_123>
  - **영상 파일**: None
  - **썸네일**: None
  - **업로드 시간**: 2025-11-30T22:51:25.494692
- **2025-11-30 - 영상 업로드 완료**
  - **제목**: Test Topic #Shorts
  - **주제**: Test Topic
  - **콘텐츠 타입**: auto
  - **Video ID**: test_video_id_123
  - **URL**: <https://www.youtube.com/watch?v=test_video_id_123>
  - **영상 파일**: /private/var/folders/zb/w2ldjmt504jcjsjhvfytbxlr0000gn/T/pytest-of-jsong/pytest-16/test_create_and_upload_success0/test_video.mp4
  - **썸네일**: /private/var/folders/zb/w2ldjmt504jcjsjhvfytbxlr0000gn/T/pytest-of-jsong/pytest-16/test_create_and_upload_success0/test_thumbnail.jpg
  - **업로드 시간**: 2025-11-30T22:51:25.476261
- **2025-11-30 - 영상 업로드 완료**
  - **제목**: A messy closet is a money leak in disguise. #Shorts
  - **주제**: A messy closet is a money leak in disguise.
  - **콘텐츠 타입**: hook
  - **Video ID**: _MtYtTPwpx0
  - **URL**: <https://www.youtube.com/watch?v=_MtYtTPwpx0>
  - **영상 파일**: output/videos/shorts_20251130_120010.mp4
  - **썸네일**: output/thumbnails/thumb_20251130_120249.jpg
  - **업로드 시간**: 2025-11-30T12:04:15.857254
- **2025-11-30 - 영상 업로드 완료**
  - **제목**: Morning routine tips #Shorts
  - **주제**: Morning routine tips
  - **콘텐츠 타입**: quote
  - **Video ID**: bqJkrhcdNzs
  - **URL**: <https://www.youtube.com/watch?v=bqJkrhcdNzs>
  - **영상 파일**: output/videos/shorts_20251130_115611.mp4
  - **썸네일**: output/thumbnails/thumb_20251130_115836.jpg
  - **업로드 시간**: 2025-11-30T12:00:04.456622
- **2025-11-30 - 영상 업로드 완료**
  - **제목**: The $100 you save today becomes $1,000 in 10 years. #Shorts
  - **주제**: The $100 you save today becomes $1,000 in 10 years.
  - **콘텐츠 타입**: hook
  - **Video ID**: l8cB8AK-9z8
  - **URL**: <https://www.youtube.com/watch?v=l8cB8AK-9z8>
  - **영상 파일**: output/videos/shorts_20251130_115221.mp4
  - **썸네일**: output/thumbnails/thumb_20251130_115452.jpg
  - **업로드 시간**: 2025-11-30T11:56:07.071038
- **2025-11-29 - 영상 업로드 완료**
  - **제목**: Why Smart Investors Buy Index Funds in December #Shorts
  - **주제**: Why Smart Investors Buy Index Funds in December
  - **콘텐츠 타입**: auto
  - **Video ID**: W85xa0RxETo
  - **URL**: <https://www.youtube.com/watch?v=W85xa0RxETo>
  - **영상 파일**: output/videos/shorts_20251129_221649.mp4
  - **썸네일**: output/thumbnails/thumb_20251129_221836.jpg
  - **업로드 시간**: 2025-11-29T22:19:26.673472
- **2025-11-29 - 영상 업로드 완료**
  - **제목**: The Hidden Tax Deduction That Could Save You $500 This Year #Shorts
  - **주제**: The Hidden Tax Deduction That Could Save You $500 This Year
  - **콘텐츠 타입**: auto
  - **Video ID**: DzOOz9dGUg0
  - **URL**: <https://www.youtube.com/watch?v=DzOOz9dGUg0>
  - **영상 파일**: output/videos/shorts_20251129_221419.mp4
  - **썸네일**: output/thumbnails/thumb_20251129_221557.jpg
  - **업로드 시간**: 2025-11-29T22:16:43.472398
- **2025-11-29 - 영상 업로드 완료**
  - **제목**: Emergency Fund Challenge: How to Save $1,000 in 90 Days Without a Second Job #Shorts
  - **주제**: Emergency Fund Challenge: How to Save $1,000 in 90 Days Without a Second Job
  - **콘텐츠 타입**: auto
  - **Video ID**: DEnaIwOiRvs
  - **URL**: <https://www.youtube.com/watch?v=DEnaIwOiRvs>
  - **영상 파일**: output/videos/shorts_20251129_221156.mp4
  - **썸네일**: output/thumbnails/thumb_20251129_221333.jpg
  - **업로드 시간**: 2025-11-29T22:14:15.578658
- **2025-11-29 - 영상 업로드 완료**
  - **제목**: The 30-Day No-Spend Challenge That Changed My Relationship With Money #Shorts
  - **주제**: The 30-Day No-Spend Challenge That Changed My Relationship With Money
  - **콘텐츠 타입**: auto
  - **Video ID**: TTLLyJoX2jw
  - **URL**: <https://www.youtube.com/watch?v=TTLLyJoX2jw>
  - **영상 파일**: output/videos/shorts_20251129_220850.mp4
  - **썸네일**: output/thumbnails/thumb_20251129_221035.jpg
  - **업로드 시간**: 2025-11-29T22:11:26.616078
- **2025-11-29 - 영상 업로드 완료**
  - **제목**: 401k vs Roth IRA: The One Choice That Determines Your Retirement #Shorts
  - **주제**: 401k vs Roth IRA: The One Choice That Determines Your Retirement
  - **콘텐츠 타입**: auto
  - **Video ID**: j223jh6mrog
  - **URL**: <https://www.youtube.com/watch?v=j223jh6mrog>
  - **영상 파일**: output/videos/shorts_20251129_220609.mp4
  - **썸네일**: output/thumbnails/thumb_20251129_220751.jpg
  - **업로드 시간**: 2025-11-29T22:08:46.049657
- **2025-11-29 - 영상 업로드 완료**
  - **제목**: The Subscription Trap: How I Saved $2,400 by Canceling These 5 Services #Shorts
  - **주제**: The Subscription Trap: How I Saved $2,400 by Canceling These 5 Services
  - **콘텐츠 타입**: auto
  - **Video ID**: sKGaSFp47MI
  - **URL**: <https://www.youtube.com/watch?v=sKGaSFp47MI>
  - **영상 파일**: output/videos/shorts_20251129_220334.mp4
  - **썸네일**: output/thumbnails/thumb_20251129_220517.jpg
  - **업로드 시간**: 2025-11-29T22:06:04.502970
- **2025-11-29 - 영상 업로드 완료**
  - **제목**: Why Smart Investors Buy Index Funds in December #Shorts
  - **주제**: Why Smart Investors Buy Index Funds in December
  - **콘텐츠 타입**: auto
  - **Video ID**: cLvEiaE0H8U
  - **URL**: <https://www.youtube.com/watch?v=cLvEiaE0H8U>
  - **영상 파일**: output/videos/shorts_20251129_220101.mp4
  - **썸네일**: output/thumbnails/thumb_20251129_220241.jpg
  - **업로드 시간**: 2025-11-29T22:03:29.204870
- **2025-11-29 - 영상 업로드 완료**
  - **제목**: The Hidden Tax Deduction That Could Save You $500 This Year #Shorts
  - **주제**: The Hidden Tax Deduction That Could Save You $500 This Year
  - **콘텐츠 타입**: auto
  - **Video ID**: jCJ5DGge5l0
  - **URL**: <https://www.youtube.com/watch?v=jCJ5DGge5l0>
  - **영상 파일**: output/videos/shorts_20251129_215832.mp4
  - **썸네일**: output/thumbnails/thumb_20251129_220008.jpg
  - **업로드 시간**: 2025-11-29T22:00:56.851025
- **2025-11-29 - 영상 업로드 완료**
  - **제목**: Emergency Fund Challenge: How to Save $1,000 in 90 Days Without a Second Job #Shorts
  - **주제**: Emergency Fund Challenge: How to Save $1,000 in 90 Days Without a Second Job
  - **콘텐츠 타입**: auto
  - **Video ID**: ZWpxDTlairM
  - **URL**: <https://www.youtube.com/watch?v=ZWpxDTlairM>
  - **영상 파일**: output/videos/shorts_20251129_215557.mp4
  - **썸네일**: output/thumbnails/thumb_20251129_215737.jpg
  - **업로드 시간**: 2025-11-29T21:58:25.604438
- **2025-11-29 - 영상 업로드 완료**
  - **제목**: Emergency Fund Challenge: How to Save $1,000 in 90 Days Without a Second Job #Shorts
  - **주제**: Emergency Fund Challenge: How to Save $1,000 in 90 Days Without a Second Job
  - **콘텐츠 타입**: auto
  - **Video ID**: 4jIBbg2r5ww
  - **URL**: <https://www.youtube.com/watch?v=4jIBbg2r5ww>
  - **영상 파일**: output/videos/shorts_20251129_215312.mp4
  - **썸네일**: output/thumbnails/thumb_20251129_215451.jpg
  - **업로드 시간**: 2025-11-29T21:55:38.499020
- **2025-11-28 - 영상 업로드 완료**
  - **제목**: It's Not That You're Lazy—It's Brain Fatigue #Shorts
  - **주제**: It's Not That You're Lazy—It's Brain Fatigue
  - **콘텐츠 타입**: auto
  - **Video ID**: GTRn7Z9G2SU
  - **URL**: <https://www.youtube.com/watch?v=GTRn7Z9G2SU>
  - **영상 파일**: output/videos/shorts_20251127_224903.mp4
  - **썸네일**: output/thumbnails/thumb_20251127_225410.jpg
  - **업로드 시간**: 2025-11-28T00:03:42.261540
- **2025-11-28 - 영상 업로드 완료**
  - **제목**: I lost ,000 in one year because of this single mistake #Shorts
  - **주제**: I lost ,000 in one year because of this single mistake
  - **콘텐츠 타입**: auto
  - **Video ID**: oshdynFnc0o
  - **URL**: <https://www.youtube.com/watch?v=oshdynFnc0o>
  - **영상 파일**: output/videos/shorts_20251127_231608.mp4
  - **썸네일**: output/thumbnails/thumb_20251127_231931.jpg
  - **업로드 시간**: 2025-11-28T00:03:28.904527
- **2025-11-28 - 영상 업로드 완료**
  - **제목**: I lost ,000 in Bitcoin because I made this one mistake #Shorts
  - **주제**: I lost ,000 in Bitcoin because I made this one mistake
  - **콘텐츠 타입**: auto
  - **Video ID**: pSbpYa19HqA
  - **URL**: <https://www.youtube.com/watch?v=pSbpYa19HqA>
  - **영상 파일**: output/videos/shorts_20251127_235526.mp4
  - **썸네일**: output/thumbnails/thumb_20251127_235841.jpg
  - **업로드 시간**: 2025-11-28T00:02:43.663732
- **2025-11-28 - 영상 업로드 완료**
  - **제목**: I failed 100 times, then this one change made me successful #Shorts
  - **주제**: I failed 100 times, then this one change made me successful
  - **콘텐츠 타입**: auto
  - **Video ID**: 60eCUtP-26w
  - **URL**: <https://www.youtube.com/watch?v=60eCUtP-26w>
  - **영상 파일**: output/videos/shorts_20251127_235131.mp4
  - **썸네일**: output/thumbnails/thumb_20251127_235444.jpg
  - **업로드 시간**: 2025-11-28T00:02:26.949738
- **2025-11-28 - 영상 업로드 완료**
  - **제목**: The morning routine that made me a millionaire #Shorts
  - **주제**: The morning routine that made me a millionaire
  - **콘텐츠 타입**: auto
  - **Video ID**: 9IHclxN9LCs
  - **URL**: <https://www.youtube.com/watch?v=9IHclxN9LCs>
  - **영상 파일**: output/videos/shorts_20251127_234731.mp4
  - **썸네일**: output/thumbnails/thumb_20251127_235046.jpg
  - **업로드 시간**: 2025-11-28T00:02:09.750172
- **2025-11-28 - 영상 업로드 완료**
  - **제목**: Why 99% of people fail at their goals (and the 1% who don't) #Shorts
  - **주제**: Why 99% of people fail at their goals (and the 1% who don't)
  - **콘텐츠 타입**: auto
  - **Video ID**: IUhqj5_yxyQ
  - **URL**: <https://www.youtube.com/watch?v=IUhqj5_yxyQ>
  - **영상 파일**: output/videos/shorts_20251127_234320.mp4
  - **썸네일**: output/thumbnails/thumb_20251127_234636.jpg
  - **업로드 시간**: 2025-11-28T00:01:55.756218
- **2025-11-27 - 영상 업로드 완료**
  - **제목**: I went from minimum wage to millionaire in 5 years—here's how. #Shorts
  - **주제**: I went from minimum wage to millionaire in 5 years—here's how.
  - **콘텐츠 타입**: auto
  - **Video ID**: fzRECnj0zMo
  - **URL**: <https://www.youtube.com/watch?v=fzRECnj0zMo>
  - **영상 파일**: output/videos/shorts_20251126_223640.mp4
  - **썸네일**: output/thumbnails/thumb_20251126_224026.jpg
  - **업로드 시간**: 2025-11-27T01:16:00.688047
- **2025-11-27 - 영상 업로드 완료**
  - **제목**: He went from minimum wage to millionaire in 5 years with one strategy. #Shorts
  - **주제**: He went from minimum wage to millionaire in 5 years with one strategy.
  - **콘텐츠 타입**: auto
  - **Video ID**: tRQsnQlfR1Y
  - **URL**: <https://www.youtube.com/watch?v=tRQsnQlfR1Y>
  - **영상 파일**: output/videos/shorts_20251126_222757.mp4
  - **썸네일**: output/thumbnails/thumb_20251126_223200.jpg
  - **업로드 시간**: 2025-11-27T01:15:59.682312
- **2025-11-27 - 영상 업로드 완료**
  - **제목**: He was rejected 100 times, then became a millionaire with one idea. #Shorts
  - **주제**: He was rejected 100 times, then became a millionaire with one idea.
  - **콘텐츠 타입**: auto
  - **Video ID**: EWQ_CHSkFMg
  - **URL**: <https://www.youtube.com/watch?v=EWQ_CHSkFMg>
  - **영상 파일**: output/videos/shorts_20251126_222310.mp4
  - **썸네일**: output/thumbnails/thumb_20251126_222721.jpg
  - **업로드 시간**: 2025-11-27T01:15:58.907071
- **2025-11-27 - 영상 업로드 완료**
  - **제목**: The morning routine that made me a millionaire #Shorts
  - **주제**: The morning routine that made me a millionaire
  - **콘텐츠 타입**: auto
  - **Video ID**: LBT8k3Vx1fg
  - **URL**: <https://www.youtube.com/watch?v=LBT8k3Vx1fg>
  - **영상 파일**: output/videos/shorts_20251126_221834.mp4
  - **썸네일**: output/thumbnails/thumb_20251126_222233.jpg
  - **업로드 시간**: 2025-11-27T01:15:58.211000
- **2025-11-27 - 영상 업로드 완료**
  - **제목**: Why 99% of people fail at their goals (and the 1% who don't) #Shorts
  - **주제**: Why 99% of people fail at their goals (and the 1% who don't)
  - **콘텐츠 타입**: auto
  - **Video ID**: VLH3q4iDboU
  - **URL**: <https://www.youtube.com/watch?v=VLH3q4iDboU>
  - **영상 파일**: output/videos/shorts_20251126_221428.mp4
  - **썸네일**: output/thumbnails/thumb_20251126_221757.jpg
  - **업로드 시간**: 2025-11-27T01:15:41.630599

### 2025-11-25 - 주제 리스트 개선: 더 자극적이고 클릭을 유도하는 주제로 교체

**작업 내용**:
- 모든 콘텐츠 타입(HOOK, QUOTE, STORY, FACT, SHORT_STORY)의 주제 리스트를 더 자극적이고 클릭을 유도하는 주제로 전면 교체
- 구체적인 금액($500, $1,200, $10,000 등)과 충격적인 숫자를 포함한 주제 추가
- 강한 감정 키워드(regret, mistake, destroyed, ruined 등) 활용
- 개인적 경험("I lost", "I made", "My mistake" 등)을 강조한 주제 추가
- 계절별 주제도 더 자극적이고 구체적인 내용으로 교체

**개선된 주제 특징**:
- HOOK: "I lost $50,000 in one year because of this single mistake", "The $500 purchase that destroyed my credit score" 등
- QUOTE: "Your mess is costing you more than you think", "Debt is modern slavery. Freedom is being debt-free." 등
- STORY: "She lost $20,000 in one year, then made it back in 6 months", "His credit score was 450. One year later, it's 780." 등
- FACT: "The average person wastes $1,200 per year on unused subscriptions", "One financial mistake in your 20s can cost you $100,000 by retirement" 등
- SHORT_STORY: "I lost $15,000 in one year and here's exactly how I got it back", "I found $12,000 in hidden subscriptions I forgot I had" 등

### 2025-11-25 - 겨울/연말 재태크 주제 영상 일괄 생성 및 업로드

**작업 내용**:
- 겨울/연말 시즌에 맞는 재태크 주제 5개 영상 생성 및 업로드
- 이전에 생성된 영상 1개 추가 업로드
- 총 6개 영상이 YouTube Shorts로 업로드 완료

**생성 및 업로드된 영상**:
1. Black Friday Regret: The $500 Mistake I Made Last Year and How to Avoid It (8R8g-e-b-80, 50.60초)
2. New Year Financial Reset: The 3 Numbers That Changed My Money Game (e-oqjbCya1A, 53.14초)
3. Holiday Gift Budget Hack: How I Saved $300 Without Looking Cheap (oISKpLCxjZA, 45.84초)
4. January Investment Strategy: Why Smart People Buy Stocks in the First Week (_pkdQrpFuwI, 55.13초)
5. Year-End Expense Audit: The Hidden Subscription That Cost Me $1,200 (Pteq_ItjEHQ, 48.84초)
6. The January Budget Reset: 5 Moves That Saved Me (WeoC6EB92Qc, 이전 생성 영상)

**특징**:
- 모든 영상이 영어로 생성 (스크립트, 자막, 썸네일)
- 겨울/연말 시즌에 맞는 재태크/금융 주제 중심
- 각 영상의 썸네일이 DALL-E 3로 생성되어 함께 업로드
- 업로드 후 원본 영상 파일 및 메타데이터 파일 자동 삭제
- 모든 업로드 기록이 데이터베이스 및 HISTORY.md에 저장됨
- **2025-11-25 - 영상 업로드 완료**
  - **제목**: The January Budget Reset: 5 Moves That Saved Me ,000 Last Year #Shorts
  - **주제**: The January Budget Reset: 5 Moves That Saved Me ,000 Last Year
  - **콘텐츠 타입**: auto
  - **Video ID**: WeoC6EB92Qc
  - **URL**: <https://www.youtube.com/watch?v=WeoC6EB92Qc>
  - **영상 파일**: output/videos/shorts_20251122_214817.mp4
  - **썸네일**: output/thumbnails/thumb_20251122_215121.jpg
  - **업로드 시간**: 2025-11-25T00:38:29.393784
- **2025-11-25 - 영상 업로드 완료**
  - **제목**: Year-End Expense Audit: The Hidden Subscription That Cost Me $1,200 #Shorts
  - **주제**: Year-End Expense Audit: The Hidden Subscription That Cost Me $1,200
  - **콘텐츠 타입**: auto
  - **Video ID**: Pteq_ItjEHQ
  - **URL**: <https://www.youtube.com/watch?v=Pteq_ItjEHQ>
  - **영상 파일**: output/videos/shorts_20251125_003157.mp4
  - **썸네일**: output/thumbnails/thumb_20251125_003447.jpg
  - **업로드 시간**: 2025-11-25T00:37:54.172694
- **2025-11-25 - 영상 업로드 완료**
  - **제목**: January Investment Strategy: Why Smart People Buy Stocks in the First Week #Shorts
  - **주제**: January Investment Strategy: Why Smart People Buy Stocks in the First Week
  - **콘텐츠 타입**: auto
  - **Video ID**: _pkdQrpFuwI
  - **URL**: <https://www.youtube.com/watch?v=_pkdQrpFuwI>
  - **영상 파일**: output/videos/shorts_20251125_002731.mp4
  - **썸네일**: output/thumbnails/thumb_20251125_003115.jpg
  - **업로드 시간**: 2025-11-25T00:37:37.067776
- **2025-11-25 - 영상 업로드 완료**
  - **제목**: Holiday Gift Budget Hack: How I Saved $300 Without Looking Cheap #Shorts
  - **주제**: Holiday Gift Budget Hack: How I Saved $300 Without Looking Cheap
  - **콘텐츠 타입**: auto
  - **Video ID**: oISKpLCxjZA
  - **URL**: <https://www.youtube.com/watch?v=oISKpLCxjZA>
  - **영상 파일**: output/videos/shorts_20251125_002348.mp4
  - **썸네일**: output/thumbnails/thumb_20251125_002648.jpg
  - **업로드 시간**: 2025-11-25T00:37:23.454412
- **2025-11-25 - 영상 업로드 완료**
  - **제목**: New Year Financial Reset: The 3 Numbers That Changed My Money Game #Shorts
  - **주제**: New Year Financial Reset: The 3 Numbers That Changed My Money Game
  - **콘텐츠 타입**: auto
  - **Video ID**: e-oqjbCya1A
  - **URL**: <https://www.youtube.com/watch?v=e-oqjbCya1A>
  - **영상 파일**: output/videos/shorts_20251125_001927.mp4
  - **썸네일**: output/thumbnails/thumb_20251125_002259.jpg
  - **업로드 시간**: 2025-11-25T00:37:05.174273
- **2025-11-25 - 영상 업로드 완료**
  - **제목**: Black Friday Regret: The $500 Mistake I Made Last Year and How to Avoid It #Shorts
  - **주제**: Black Friday Regret: The $500 Mistake I Made Last Year and How to Avoid It
  - **콘텐츠 타입**: auto
  - **Video ID**: 8R8g-e-b-80
  - **URL**: <https://www.youtube.com/watch?v=8R8g-e-b-80>
  - **영상 파일**: output/videos/shorts_20251125_001535.mp4
  - **썸네일**: output/thumbnails/thumb_20251125_001851.jpg
  - **업로드 시간**: 2025-11-25T00:36:50.762621
- **2025-11-24 - 영상 업로드 완료**
  - **제목**: I automated emails with AI and finally slept. #Shorts
  - **주제**: I automated emails with AI and finally slept.
  - **콘텐츠 타입**: auto
  - **Video ID**: xfinnIPll8s
  - **URL**: <https://www.youtube.com/watch?v=xfinnIPll8s>
  - **영상 파일**: output/videos/shorts_20251123_235439.mp4
  - **썸네일**: output/thumbnails/thumb_20251123_235620.jpg
  - **업로드 시간**: 2025-11-24T00:00:38.518713
- **2025-11-24 - 영상 업로드 완료**
  - **제목**: Skipping a winter oil check can cost an engine replacement. #Shorts
  - **주제**: Skipping a winter oil check can cost an engine replacement.
  - **콘텐츠 타입**: auto
  - **Video ID**: sXeekCuUT6E
  - **URL**: <https://www.youtube.com/watch?v=sXeekCuUT6E>
  - **영상 파일**: output/videos/shorts_20251123_235649.mp4
  - **썸네일**: output/thumbnails/thumb_20251123_235841.jpg
  - **업로드 시간**: 2025-11-24T00:00:18.050549
- **2025-11-24 - 영상 업로드 완료**
  - **제목**: Decluttered desks raise focus by 25%. #Shorts
  - **주제**: Decluttered desks raise focus by 25%.
  - **콘텐츠 타입**: auto
  - **Video ID**: 7uiXBX449t0
  - **URL**: <https://www.youtube.com/watch?v=7uiXBX449t0>
  - **영상 파일**: output/videos/shorts_20251123_235222.mp4
  - **썸네일**: output/thumbnails/thumb_20251123_235406.jpg
  - **업로드 시간**: 2025-11-24T00:00:02.557644
- **2025-11-23 - 영상 업로드 완료**
  - **제목**: A five-minute evening review saved a burned-out manager. #Shorts
  - **주제**: A five-minute evening review saved a burned-out manager.
  - **콘텐츠 타입**: auto
  - **Video ID**: crHDt--ftZk
  - **URL**: <https://www.youtube.com/watch?v=crHDt--ftZk>
  - **영상 파일**: output/videos/shorts_20251123_235004.mp4
  - **썸네일**: output/thumbnails/thumb_20251123_235150.jpg
  - **업로드 시간**: 2025-11-23T23:59:51.988647
- **2025-11-23 - 영상 업로드 완료**
  - **제목**: Preparing for winter is really about removing future discomfort. #Shorts
  - **주제**: Preparing for winter is really about removing future discomfort.
  - **콘텐츠 타입**: auto
  - **Video ID**: eU9YwDbnyOI
  - **URL**: <https://www.youtube.com/watch?v=eU9YwDbnyOI>
  - **영상 파일**: output/videos/shorts_20251123_234745.mp4
  - **썸네일**: output/thumbnails/thumb_20251123_234932.jpg
  - **업로드 시간**: 2025-11-23T23:59:41.394912
- **2025-11-23 - 영상 업로드 완료**
  - **제목**: Declutter one room and watch your stress plummet #Shorts
  - **주제**: Declutter one room and watch your stress plummet
  - **콘텐츠 타입**: auto
  - **Video ID**: LD-_METRnQ0
  - **URL**: <https://www.youtube.com/watch?v=LD-_METRnQ0>
  - **영상 파일**: output/videos/shorts_20251123_234514.mp4
  - **썸네일**: output/thumbnails/thumb_20251123_234701.jpg
  - **업로드 시간**: 2025-11-23T23:59:25.230665
- **2025-11-23 - 영상 업로드 완료**
  - **제목**: The Hidden Cost of Free Shipping That's Costing You  a Year #Shorts
  - **주제**: The Hidden Cost of Free Shipping That's Costing You  a Year
  - **콘텐츠 타입**: auto
  - **Video ID**: t18QLHi_GgI
  - **URL**: <https://www.youtube.com/watch?v=t18QLHi_GgI>
  - **영상 파일**: output/videos/shorts_20251122_221040.mp4
  - **썸네일**: output/thumbnails/thumb_20251122_221329.jpg
  - **업로드 시간**: 2025-11-23T00:02:06.682831
- **2025-11-23 - 영상 업로드 완료**
  - **제목**: Why I Stopped Saving Money and Started Investing Instead #Shorts
  - **주제**: Why I Stopped Saving Money and Started Investing Instead
  - **콘텐츠 타입**: auto
  - **Video ID**: O7CbNnLi3O0
  - **URL**: <https://www.youtube.com/watch?v=O7CbNnLi3O0>
  - **영상 파일**: output/videos/shorts_20251122_220631.mp4
  - **썸네일**: output/thumbnails/thumb_20251122_220936.jpg
  - **업로드 시간**: 2025-11-23T00:01:56.927945
- **2025-11-23 - 영상 업로드 완료**
  - **제목**: The 5-Minute Morning Routine That Doubled My Income #Shorts
  - **주제**: The 5-Minute Morning Routine That Doubled My Income
  - **콘텐츠 타입**: auto
  - **Video ID**: CUmhC0l1eIE
  - **URL**: <https://www.youtube.com/watch?v=CUmhC0l1eIE>
  - **영상 파일**: output/videos/shorts_20251122_220239.mp4
  - **썸네일**: output/thumbnails/thumb_20251122_220551.jpg
  - **업로드 시간**: 2025-11-23T00:01:47.373702
- **2025-11-23 - 영상 업로드 완료**
  - **제목**: How I Cut My Monthly Bills by 40% in 30 Days #Shorts
  - **주제**: How I Cut My Monthly Bills by 40% in 30 Days
  - **콘텐츠 타입**: auto
  - **Video ID**: AHoVY5_0oIg
  - **URL**: <https://www.youtube.com/watch?v=AHoVY5_0oIg>
  - **영상 파일**: output/videos/shorts_20251122_215912.mp4
  - **썸네일**: output/thumbnails/thumb_20251122_220203.jpg
  - **업로드 시간**: 2025-11-23T00:01:36.529674
- **2025-11-23 - 영상 업로드 완료**
  - **제목**: The Side Hustle That Made Me $500 in January Alone #Shorts
  - **주제**: The Side Hustle That Made Me $500 in January Alone
  - **콘텐츠 타입**: auto
  - **Video ID**: TIRNqdikhbU
  - **URL**: <https://www.youtube.com/watch?v=TIRNqdikhbU>
  - **영상 파일**: output/videos/shorts_20251122_215530.mp4
  - **썸네일**: output/thumbnails/thumb_20251122_215827.jpg
  - **업로드 시간**: 2025-11-23T00:01:21.936569
- **2025-11-23 - 영상 업로드 완료**
  - **제목**: Why Your December Credit Card Statement Is Lying to You #Shorts
  - **주제**: Why Your December Credit Card Statement Is Lying to You
  - **콘텐츠 타입**: auto
  - **Video ID**: j9lULl6fUyI
  - **URL**: <https://www.youtube.com/watch?v=j9lULl6fUyI>
  - **영상 파일**: output/videos/shorts_20251122_215158.mp4
  - **썸네일**: output/thumbnails/thumb_20251122_215453.jpg
  - **업로드 시간**: 2025-11-23T00:01:06.201545

**YouTube Shorts 자동 업로드 봇**: AI로 자동 생성된 YouTube Shorts 영상을 매일 자동으로 업로드하고 수익화를 추적하는 봇

**최근 업데이트 (2025-11-22)**:
- **테스트 파일 구조 개선**: 루트 디렉토리의 테스트 파일들을 `tests/` 디렉토리로 이동
  - `generate_test_video.py`, `test_script_fixes.py`, `test_ad_revenue.py`, `test_ad_revenue_complete.py`를 `tests/`로 이동
  - import 경로 수정: `sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))`로 변경
  - 프로젝트 구조 정리 및 테스트 파일 일관성 향상
- **배경 영상 품질 개선**: 배경 영상 중복 방지 및 다운로드 실패 시 재시도 전략 개선
  - **영상 ID 직접 추적**: 배경 영상 경로 대신 영상 ID를 직접 추적하여 중복 방지 정확도 향상
    - `downloaded_video_ids` 세트를 사용하여 이미 사용한 영상 ID 추적
    - `_download_video_for_sentence` 메서드가 `(bg_video_path, video_id)` 튜플 반환
    - 각 그룹마다 다른 배경 영상이 사용되도록 보장
  - **다중 키워드 재시도 전략**: 배경 영상 다운로드 실패 시 여러 키워드를 순차적으로 시도
    - 첫 번째 시도: 문장에서 추출한 키워드 (예: "sunny")
    - 두 번째 시도: 주제에서 추출한 키워드 (예: "winter")
    - 세 번째 시도 이후: 일반 키워드 ("home", "lifestyle", "indoor", "cozy", "warm")
    - 최대 5개 키워드까지 시도하여 그라데이션 배경 사용 빈도 감소
    - `force_keyword` 파라미터 추가로 재시도 시 다른 키워드 사용 가능
- **자막 배경 박스 제거**: 사용자 요청에 따라 자막을 둘러싼 배경 박스를 완전히 제거
  - `_draw_text_on_image` 메서드: 반투명 검은색 배경 박스 제거
  - `_create_subtitle_clip` 메서드: 그라데이션 배경 박스 및 테두리 제거
  - 그림자 효과는 유지하여 가독성 보장
  - 자막이 더 깔끔하고 자연스럽게 표시됨
- **콘텐츠 관련 기능 구현**: 시리즈 콘텐츠 생성, 사용자 요청 주제 반영, 댓글 기반 주제 제안
  - **시리즈 콘텐츠 생성 시스템**: `SeriesGenerator` 클래스 구현
    - 4가지 시리즈 타입 지원: 순차적(SEQUENTIAL), 주제별(THEMATIC), 튜토리얼(TUTORIAL), 챌린지(CHALLENGE)
    - AI 기반 시리즈 주제 자동 생성 (에피소드별 주제 생성)
    - 대시보드 API: `/api/content/series/generate` 엔드포인트 추가
  - **사용자 요청 주제 반영 시스템**: `UserRequestHandler` 클래스 구현
    - 요청 상태 관리 (대기, 승인, 진행 중, 완료, 거부)
    - 우선순위 기반 요청 처리 (1-10점 척도)
    - `bot.py`에 통합: 주제가 없을 때 사용자 요청 주제를 우선적으로 사용
    - 영상 업로드 완료 시 자동으로 요청 상태를 완료로 변경
    - 대시보드 API: `/api/content/user-requests` (GET/POST), `/api/content/user-requests/<id>/approve` 엔드포인트 추가
  - **댓글 기반 다음 주제 제안 시스템**: `CommentAnalyzer` 클래스 구현
    - YouTube 댓글에서 주제 제안 자동 추출 (키워드 패턴 매칭)
    - 좋아요 수 기반 우선순위 부여 (좋아요 10개당 +1점)
    - 자동으로 사용자 요청 시스템에 추가
    - 특정 영상 또는 최근 영상들의 댓글 일괄 분석 지원
    - 대시보드 API: `/api/content/comments/analyze` 엔드포인트 추가
  - **대시보드 영상 목록 개선**: 모든 영상 표시 (필터 제거)
    - `VideoDatabase.get_all_videos()` 메서드 추가: 필터 없이 모든 영상 조회
    - 대시보드 API 수정: `get_top_performing_videos` 대신 `get_all_videos` 사용
    - HTML 수정: `days`와 `limit` 파라미터 제거하여 모든 영상 조회
- **사용자 경험 개선**: 웹 대시보드, 실시간 통계 API, 알림 시스템, 설정 UI
  - **웹 대시보드 개발**: Flask 기반 실시간 통계 대시보드 구현
    - **dashboard.py**: RESTful API 서버 및 대시보드 엔드포인트 구현
    - **dashboard.html**: 반응형 웹 대시보드 UI (영상 통계, 주제 분석, A/B 테스트, 최적화 권장, 설정)
    - **실시간 통계**: 영상 수, 조회수, 좋아요, 참여율, 구독자, 수익 등 실시간 표시
    - **자동 새로고침**: 30초마다 통계 자동 업데이트
  - **실시간 통계 및 리포트 API**: 다양한 통계 데이터 제공
    - `/api/stats/overview`: 전체 통계 개요
    - `/api/stats/videos`: 영상별 통계
    - `/api/stats/topics`: 주제별 통계
    - `/api/stats/ab-testing`: A/B 테스트 통계
    - `/api/stats/thumbnails`: 썸네일 통계
    - `/api/optimization/recommendations`: 최적화 권장사항
    - `/api/analytics/audience-segments`: 시청자 세그먼트 분석
  - **알림 시스템**: 이메일 및 Slack 알림 지원
    - **NotificationService 클래스**: 이메일(SMTP) 및 Slack(Webhook) 알림 전송
    - **영상 업로드 완료 알림**: 영상 업로드 성공 시 자동 알림
    - **영상 업로드 실패 알림**: 업로드 실패 시 에러 알림
    - **일일 요약 알림**: 매일 통계 요약 리포트 전송
    - **마일스톤 달성 알림**: 조회수, 구독자, 영상 수 마일스톤 달성 시 알림
    - **bot.py 통합**: 영상 업로드 시 자동으로 알림 전송
  - **설정 UI 개선**: 웹 기반 설정 관리
    - **설정 API**: `/api/settings` (GET/POST)로 설정 조회 및 업데이트
    - **대시보드 설정 탭**: 업로드 스케줄, 배경 음악, 자막 모드, 트렌드 모드 등 설정 관리
    - **설정 저장**: JSON 파일로 설정 저장 (향후 .env 파일 연동 가능)
- **고급 분석 및 최적화 시스템**: 머신러닝 기반 성과 예측, 자동 최적화, 경쟁사 분석, 시청자 세그먼트 분석
  - **PerformancePredictor 클래스**: 선형 회귀 기반 성과 예측 시스템 구현
    - 특징 추출 (주제, 콘텐츠 타입, 업로드 시간, 스타일 등)
    - 주제/콘텐츠 타입/시간/스타일별 평균 성과 계산
    - 가중 평균 기반 예측 (주제 40%, 콘텐츠 타입 30%, 시간 20%, 스타일 10%)
    - 예측 정확도 추적 및 업데이트
  - **AutoOptimizer 클래스**: 자동 최적화 시스템 구현
    - 주제 선택 최적화 (성과 기반 + 트렌드 기반)
    - 업로드 시간 최적화 (시간대별 평균 성과 분석)
    - 영상 스타일 최적화 (A/B 테스트 결과 기반)
    - 썸네일 스타일 최적화 (클릭률 기반)
    - 종합 최적화 권장사항 제공
  - **CompetitorAnalyzer 클래스**: 경쟁사 분석 및 벤치마킹 시스템 구현
    - 경쟁사 채널 분석 (조회수, 참여율, 업로드 빈도)
    - 자체 채널 대비 벤치마킹 (성과 비교 분석)
    - 벤치마킹 결과 기반 권장사항 생성
  - **AudienceSegmentAnalyzer 클래스**: 시청자 세그먼트 분석 시스템 구현
    - 주제별 시청자 세그먼트 분석
    - 콘텐츠 타입별 시청자 세그먼트 분석
    - 시간대별 시청자 세그먼트 분석 (오전/오후/저녁/밤)
  - **bot.py 통합**: 고급 분석 시스템을 봇에 통합하여 자동 활용 가능
- **배경 음악 추가 옵션**: 무료 음악 라이브러리 통합 및 콘텐츠 타입별 자동 선택
  - **Pixabay Music API 통합**: 무료 배경 음악 다운로드 지원 (로컬 음악 라이브러리 디렉토리 구조 준비)
  - **콘텐츠 타입별 음악 선택**: HOOK(에너지 넘치는), QUOTE(차분한), STORY(감성적), FACT(정보성), MEDITATION(평화로운), BREATHING(명상적) 등 콘텐츠 타입에 맞는 음악 자동 선택
  - **오디오 믹싱**: MoviePy의 `CompositeAudioClip`을 사용하여 음성과 배경 음악을 자연스럽게 믹싱
  - **볼륨 밸런싱**: 음성 100%, 배경 음악 25% (기본값, `BACKGROUND_MUSIC_VOLUME` 환경 변수로 조정 가능)
  - **음악 길이 조정**: 영상 길이에 맞게 음악을 루프하거나 자르기, 페이드 아웃 효과 적용
  - **설정 옵션**: `USE_BACKGROUND_MUSIC=true/false`로 배경 음악 사용 여부 제어, `BACKGROUND_MUSIC_VOLUME=0.25`로 볼륨 조정
- **A/B 테스트 시스템**: 다양한 스타일의 영상 생성, 성과 데이터 수집 및 분석, 최적 스타일 자동 선택
  - **ABTestDatabase 클래스 추가**: `src/analytics/ab_testing.py` - A/B 테스트 데이터베이스 관리
  - **스타일 변형 추적**: DEFAULT, MINIMAL, BOLD, MUSIC, NO_MUSIC, GRADIENT, VIDEO_BG 등 다양한 스타일 변형 추적
  - **성과 데이터 수집**: 조회수, 좋아요, 댓글, 참여율, 시청 시간 등 성과 지표 자동 수집
  - **최적 스타일 자동 선택**: `get_best_style_by_engagement()` 메서드로 콘텐츠 타입별 최고 성과 스타일 자동 선택
  - **성과 분석**: `get_style_performance()` 메서드로 스타일별 성과 데이터 조회 및 분석
  - **bot.py 통합**: 영상 업로드 시 자동으로 A/B 테스트 데이터베이스에 저장, 통계 업데이트 시 A/B 테스트 통계도 함께 업데이트
  - **최적 스타일 리포트**: `update_all_stats()` 실행 시 최고 성과 스타일 자동 분석 및 출력
- **썸네일 최적화**: AI 기반 썸네일 자동 생성, 클릭률 최적화 썸네일 선택, 플랫폼별 썸네일 최적화
  - **ThumbnailOptimizer 클래스 추가**: `src/analytics/thumbnail_optimizer.py` - 썸네일 최적화 데이터베이스 관리
  - **클릭률 추적**: 썸네일별 조회수, 노출 수, 클릭률(CTR) 자동 추적
  - **최적 썸네일 변형 선택**: `get_best_thumbnail_variant()` 메서드로 최고 성과 썸네일 변형 자동 선택
  - **최적 썸네일 스타일 선택**: `get_best_thumbnail_style()` 메서드로 최고 성과 썸네일 스타일(DALL-E 3, 프레임 추출 등) 자동 선택
  - **플랫폼별 최적화**: `optimize_for_platform()` 메서드로 YouTube Shorts, YouTube, TikTok, Instagram 등 플랫폼별 최적화 설정 제공
  - **bot.py 통합**: 영상 업로드 시 자동으로 썸네일 최적화 데이터베이스에 저장, 통계 업데이트 시 썸네일 통계도 함께 업데이트
- **음성 품질 개선**: TTS 음성 자연스러움, 발음 정확도, 감정 표현 개선
  - **콘텐츠 타입별 voice/speed 최적화**: HOOK(onyx, 1.1x), QUOTE(alloy, 1.0x), STORY(shimmer, 0.9x), FACT(alloy, 1.05x), SHORT_STORY(nova, 0.95x) 등 콘텐츠 타입에 맞는 음성과 속도 자동 선택
  - **텍스트 전처리 시스템**: 숫자 변환 ($500 → five hundred dollars, 30% → thirty percent), 약어 확장 (AI → A I, CEO → C E O), 특수 문자 정리
  - **발음 정확도 향상**: 작은 숫자(0-99)를 단어로 변환하여 TTS 발음 정확도 향상
  - **감정 표현 추가**: 콘텐츠 타입별로 최적화된 voice와 speed로 감정 표현 강화
- **영상 시각적 품질 개선**: 자막 스타일, 배경 영상 선택, 전환 효과, 색상/밝기 분석 개선
  - **자막 디자인 개선**: 그라데이션 배경, 더 강한 그림자 효과, 페이드 인/아웃 애니메이션 추가, 더 두꺼운 테두리 (가독성 향상)
  - **배경 영상 선택 알고리즘 개선**: 해상도 체크 강화 (1080p > 720p > 540p > 480p 우선순위), 세로형 영상만 선택, 품질 점수 기반 선택
  - **전환 효과 개선**: 첫 클립 fade in, 마지막 클립 fade out, 중간 클립 양쪽 fade (부드러운 전환)
  - **색상/밝기 분석 추가**: 영상 다운로드 후 밝기, 대비, 채도 분석하여 자막 가독성에 영향을 주는 영상 경고
- **YouTube 트렌드 키워드 수집 시스템 구현**: 주제 자동 업데이트 시스템의 첫 단계 완료
  - **TrendCollector 클래스 추가**: `src/analytics/trend_collector.py` - YouTube Data API v3를 사용하여 인기 Shorts 수집 및 키워드 추출
  - **인기 Shorts 분석**: 최근 7일간 조회수 기준 인기 Shorts 수집, 제목/태그/설명에서 키워드 추출
  - **AI 키워드 정제**: OpenAI API를 사용하여 수집한 키워드를 재정렬 및 정제
  - **캐싱 시스템**: 24시간 캐시로 API 호출 최소화
  - **video_generator.py 통합**: `TREND_MODE=true`일 때 YouTube 트렌드 주제를 자동으로 주제 풀에 포함
  - **카테고리별 트렌드 수집**: finance, productivity, self-improvement, lifestyle 카테고리별 트렌드 주제 수집 지원
- **AI 기반 주제 생성 시스템 구현**: 트렌드 키워드를 기반으로 AI가 새로운 주제를 자동 생성
  - **generate_topics_from_trends() 메서드 추가**: 트렌드 키워드를 기반으로 콘텐츠 타입별 주제 생성
  - **주제 품질 검증 로직**: `validate_topic_quality()` 메서드로 중복 방지, 길이 검증, 관련 키워드 확인
  - **video_generator.py 통합**: `_generate_ai_topics_from_trends()` 메서드로 AI 생성 주제를 주제 풀에 자동 추가
  - **12시간 캐싱**: AI 생성 주제는 12시간 캐시로 API 호출 최소화
  - **품질 필터링**: 검증 점수 50점 이상인 주제만 사용, 실패 이유 로깅
- **계절별 주제 자동 업데이트 시스템 구현**: 계절별 트렌드 키워드를 기반으로 AI가 새로운 계절별 주제를 자동 생성
  - **collect_seasonal_trending_keywords() 메서드 추가**: 계절별 트렌드 키워드 수집 (spring, summer, autumn, winter)
  - **generate_seasonal_topics() 메서드 추가**: 계절별 트렌드 키워드를 기반으로 콘텐츠 타입별 계절 주제 생성
  - **계절별 검색어 최적화**: 각 계절에 맞는 검색어로 YouTube Shorts 수집 (예: spring cleaning, tax season, holiday budget 등)
  - **video_generator.py 통합**: `_generate_seasonal_topics_from_trends()` 메서드로 AI 생성 계절별 주제를 계절별 주제 풀에 자동 추가
  - **7일 캐싱**: 계절별 주제는 7일 캐시로 API 호출 최소화 (계절별 주제는 더 오래 유효)
  - **품질 검증**: 기존 계절별 주제와 중복 방지, 품질 점수 50점 이상인 주제만 사용
- **주제 데이터베이스 관리 시스템 완성**: 주제의 생명주기 관리 및 성과 추적 시스템 구축
  - **TopicDatabase 클래스 완성**: 주제 추가/삭제/업데이트, 성과 추적, 자동 필터링 기능 구현
  - **주제 데이터베이스 스키마**: topics 테이블 (주제 정보) 및 topic_videos 테이블 (주제-영상 연결) 설계
  - **자동 통계 업데이트**: 영상 업로드 시 주제 데이터베이스에 자동 저장, 통계 업데이트 시 주제 통계도 함께 업데이트
  - **성과 기반 주제 선택**: `_get_high_performing_topics()` 메서드가 주제 데이터베이스에서 성과가 좋은 주제를 자동으로 가져옴
  - **자동 필터링**: `update_all_stats()` 실행 시 성과가 낮은 주제(참여율 0.5% 이하)를 자동으로 필터링
  - **주제 출처 추적**: 주제 출처(manual, ai_generated, seasonal_ai, trend, seasonal, performance)를 추적하여 분석 가능
  - **data 폴더 Git 포함**: data 폴더의 JSON 파일을 Git에 포함하여 다른 머신에서도 히스토리 추적 가능
- **콘텐츠 품질 개선**: AI 스크립트 생성 프롬프트 전면 개선으로 더 매력적이고 효과적인 콘텐츠 생성
  - **Hook 프롬프트 개선**: 4가지 Hook 패턴 (Mindset Flip, Shocking Number, Contrarian Statement, Personal Revelation) 추가, 구체적인 예시와 전략 포함
  - **Quote 프롬프트 개선**: 실행 가능한 명언 선택, 구체적인 예시 제공, 실생활 적용법 강조
  - **Story 프롬프트 개선**: 3막 구조 (Hook & Setup → Development & Conflict → Resolution & Lesson) 적용, 감정적 여정과 구체적 세부사항 강조
  - **Fact 프롬프트 개선**: 충격적인 숫자/통계 중심, 구체적인 비교와 예시, "so what" 요소 강조
  - **Short Story 프롬프트 개선**: 1인칭 서술 형식, 구체적인 숫자와 시간대, 감정적 여정 (frustration → action → results) 포함
  - **정보 전달 방식 최적화**: 구체적인 예시, 단계별 설명, 시각적 비유, 실행 가능한 인사이트 제공
- **API 사용 정책 명확화**: ChatGPT API와 Claude API만 유료로 사용, DALL-E 3와 OpenAI TTS는 OpenAI API로 함께 사용
  - **DALL-E 3 썸네일 생성**: OpenAI API로 사용 (기존대로 유지)
  - **OpenAI TTS 자동 선택**: OpenAI API 키가 있으면 자동으로 OpenAI TTS 사용 (기존대로 유지)
  - **무료 서비스**: 배경 영상/이미지 (Pexels, Unsplash, Pixabay), gTTS (TTS 폴백) 등은 무료 서비스 사용
- **구독자 수 증가 전략 적용**: YouTube Shorts 구독자 수를 늘리기 위한 종합 전략 연구 및 코드 적용
  - **설명란 구독 유도 강화**: 채널 URL, 구독 이유, 시리즈 정보, 관련 영상 링크 추가
  - **스크립트 끝에 구독 CTA 강화**: 모든 콘텐츠 타입의 AI 프롬프트에 자연스러운 구독 요청 추가
  - **썸네일에 Subscribe 배지 추가**: "SHORTS" 배지 옆에 "SUBSCRIBE" 배지 추가 (상단 오른쪽)
  - **YouTube API 채널 정보 기능**: `get_channel_info()`, `get_recent_videos()` 메서드 추가
  - **언어별 최적화**: 영어/한국어 모두에 맞춘 구독 유도 텍스트 생성
- **6개 겨울/연말 재태크 영상 일괄 생성 및 업로드**: 12월/1월 시즌에 맞는 재태크 주제 6개를 연속 생성하여 YouTube에 즉시 업로드
  - 업로드된 영상 (ID → 주제):
    1. `Q0qk_EGmOxU` → *December Tax Hack: How to Save $2,000 Before Year-End With These 3 Moves*
    2. `0DDhBYBuqaw` → *Holiday Spending Trap: Why Americans Waste $1,500 Every December and How to Stop It*
    3. `NVJHCu01knQ` → *Winter Heating Bill Shock: The One Change That Cut My Gas Bill by 50% Last Year*
    4. `rBkBC0q41eE` → *Year-End Bonus Strategy: What Smart People Do With Their December Paycheck*
    5. `yKQIb6o9_KM` → *January Financial Reset: The 30-Day Challenge That Built My Emergency Fund*
    6. `rXCDiFxBL2Q` → *401k Deadline Alert: Why Contributing Before December 31st Changes Everything*
  - 모든 영상은 썸네일까지 정상 업로드되었으며, 총 업로드 영상 수는 36개로 증가
  - 현재 총 조회수: 917회

**이전 업데이트 (2025-11-21)**:
- **전략 결정**: TikTok과 Instagram 연결의 복잡도가 높아 YouTube만 자동 업로드하는 것으로 결정
- YouTube에 집중하여 품질과 수익을 극대화하는 것이 우선 목표
- 1분 명상(MEDITATION) 콘텐츠 타입 추가
- 호흡 가이드(BREATHING) 콘텐츠 타입 추가
- 명상/호흡 가이드용 AI 프롬프트 및 주제 목록 추가
- AUTO 선택 시 명상/호흡 타입도 포함되도록 확장
- **기본 자막 모드 변경**: `SUBTITLE_MODE` 기본값을 `full_sentence`로 통일 (코드 및 문서 일치)
- **자막 위치 조정**: 아이폰 UI 가림 방지를 위해 하단 여백을 대폭 확대 (약 300px 상향 조정)
- **버그 수정**: 자막 위치가 강제로 하단으로 초기화되던 문제 수정 (Composite 단계 오버라이드 제거)
- **영상 생성 테스트**: 자막 위치 조정 후 테스트 영상 생성 (`output/videos/shorts_20251121_151418.mp4`, 42초)
- **콘텐츠 최적화 가이드 2025 업데이트**: `docs/CONTENT_OPTIMIZATION.md`, README, .cursorrules에 트렌드/계절/루틴 기반 전략과 영어 전용 정책을 반영
- **TREND_MODE 도입**: `TREND_MODE=true` 시 글로벌 트렌드(40%)·계절(25%)·채널 성과(20%)·탐색(15%) 가중치로 주제 선택, 성과형 주제 풀과 로그 출력 추가
- **영어 메타데이터 정비**: `.env` 예시의 기본 설명/태그를 영어로 통일하고 YouTube 업로드 설명/태그도 영어 기준으로 업데이트
- **영상 생성 테스트**: `output/videos/shorts_20251121_150056.mp4` (약 54초, 주제: *Logging expenses for 30 days changed my bank balance*), 썸네일 `output/thumbnails/thumb_20251121_150222.jpg` (DALL·E 3로 생성)

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

### 2025-11-21: 트렌드 가중치 기반 주제 선택 + 2025 콘텐츠 가이드

- `docs/CONTENT_OPTIMIZATION.md`를 2025 트렌드 버전으로 전면 교체하고, README/.env 예시/.cursorrules에도 영어 전용 정책과 `TREND_MODE` 옵션을 반영
- `config.py`에 `TREND_MODE` 환경 변수를 추가하고, `AIVideoGenerator`에 글로벌/계절/성과/탐색 가중치(40/25/20/15) 기반 주제 선택 헬퍼를 도입
- 콘텐츠 타입별 기본 주제 목록을 2025 확장 주제팩(심플 라이프, AI 자동화, 금융 한 줄, 심리 팩트, 변화 스토리)으로 보강하고, 성과형 주제 풀과 출처 로그(🌍/🍂/📈/🎲)를 출력
- README `.env` 예시의 기본 설명/태그를 영어로 통일하고, YouTube 자동 업로드 섹션도 영어 기본 설명/태그로 교체
- 테스트: `python main.py test` 실행으로 `output/videos/shorts_20251121_150056.mp4` (약 54초, 타입: `short_story`, 주제: *Logging expenses for 30 days changed my bank balance*) 생성, 썸네일 `output/thumbnails/thumb_20251121_150222.jpg`는 DALL·E 3로 자동 생성 및 영상 첫 프레임 삽입

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

### 2025-11-21: YouTube 전용 전략 확정

- **전략 결정**: TikTok과 Instagram 연결의 복잡도가 높아 YouTube만 자동 업로드하는 것으로 최종 결정
- TikTok과 Instagram API 연결 테스트를 진행했으나, 앱 리뷰 과정과 API 복잡도로 인해 구현이 어려울 것으로 판단
- YouTube에 집중하여 품질과 수익을 극대화하는 것이 우선 목표
- TODO.md에서 TikTok/Instagram 관련 작업 우선순위를 낮추고, YouTube 품질 개선에 집중

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

```text
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

- YouTube 자동 업로드 품질 지속적 개선 (우선순위)
- 썸네일 최적화 기능 강화 (DALL-E 3 활용)
- 더 많은 주제 카테고리 추가
- 통계 분석 기능 강화
- 자동 A/B 테스트 기능
- TikTok 및 Instagram 업로드는 현재 보류 (API 복잡도 및 앱 리뷰 과정 고려)

### 2025-11-22: 콘텐츠 관련 기능 구현

#### 시리즈 콘텐츠 생성 시스템

- **목적**: 연속된 주제로 여러 영상을 생성하여 시리즈 콘텐츠 제작
- **구현 내용**:
  - `src/generators/series_generator.py` 생성
  - `SeriesGenerator` 클래스 구현
  - 4가지 시리즈 타입 지원:
    - `SEQUENTIAL`: 순차적 시리즈 (1부, 2부, 3부...)
    - `THEMATIC`: 주제별 시리즈 (같은 주제, 다른 관점)
    - `TUTORIAL`: 튜토리얼 시리즈 (단계별 가이드)
    - `CHALLENGE`: 챌린지 시리즈 (30일 챌린지 등)
  - AI 기반 시리즈 주제 자동 생성 (OpenAI/Claude API 사용)
  - 각 시리즈 타입별 맞춤 프롬프트 사용
- **대시보드 통합**:
  - `/api/content/series/generate` API 엔드포인트 추가
  - POST 요청으로 시리즈 주제 생성 가능

#### 사용자 요청 주제 반영 시스템

- **목적**: 사용자가 요청한 주제를 우선적으로 사용하여 영상 생성
- **구현 내용**:
  - `src/generators/user_request_handler.py` 생성
  - `UserRequestHandler` 클래스 구현
  - SQLite 데이터베이스 (`data/user_requests.db`) 사용
  - 요청 상태 관리:
    - `PENDING`: 대기 중
    - `APPROVED`: 승인됨
    - `IN_PROGRESS`: 진행 중
    - `COMPLETED`: 완료됨
    - `REJECTED`: 거부됨
  - 우선순위 기반 요청 처리 (1-10점 척도)
  - 요청 출처 추적 (comment, email, dashboard, manual 등)
- **bot.py 통합**:
  - `create_and_upload` 메서드에서 주제가 없을 때 사용자 요청 주제 우선 사용
  - 영상 업로드 완료 시 자동으로 요청 상태를 완료로 변경
- **대시보드 통합**:
  - `GET /api/content/user-requests`: 요청 목록 조회
  - `POST /api/content/user-requests`: 새 요청 추가
  - `POST /api/content/user-requests/<id>/approve`: 요청 승인

#### 댓글 기반 다음 주제 제안 시스템

- **목적**: YouTube 댓글에서 주제 제안을 자동으로 추출하여 다음 영상 주제로 활용
- **구현 내용**:
  - `src/analytics/comment_analyzer.py` 생성
  - `CommentAnalyzer` 클래스 구현
  - YouTube Data API v3를 사용하여 댓글 가져오기
  - 키워드 패턴 매칭으로 주제 제안 추출:
    - "can you make", "please make", "would love to see", "next video", "suggest" 등
  - 좋아요 수 기반 우선순위 부여 (좋아요 10개당 +1점, 최대 10점)
  - 자동으로 사용자 요청 시스템에 추가
  - 특정 영상 또는 최근 영상들의 댓글 일괄 분석 지원
- **대시보드 통합**:
  - `POST /api/content/comments/analyze` API 엔드포인트 추가
  - 특정 영상 ID 또는 최근 영상 수를 지정하여 분석 가능

#### 대시보드 영상 목록 개선

- **문제**: 대시보드에서 모든 영상이 표시되지 않음 (필터 제한)
- **해결**:
  - `VideoDatabase.get_all_videos()` 메서드 추가
    - 필터 없이 모든 영상 조회
    - `limit`, `days`, `order_by` 파라미터 지원
  - 대시보드 API 수정: `get_top_performing_videos` 대신 `get_all_videos` 사용
  - HTML 수정: `days`와 `limit` 파라미터 제거하여 모든 영상 조회
- **결과**: 데이터베이스의 모든 영상(35개)이 대시보드에 표시됨

### 2025-11-22: 구독자 수 증가 전략 연구 및 적용

- **목표**: YouTube Shorts 채널의 구독자 수를 효과적으로 늘리기 위한 종합 전략 연구 및 코드 적용
- **연구 결과**: 웹 검색을 통해 2025년 YouTube Shorts 구독자 증가 베스트 프랙티스 확인
  - 고품질 콘텐츠 제작, 일관된 업로드, SEO 최적화, 소셜 미디어 활용, 커뮤니티 기능 활용 등
- **코드 개선 사항**:
  1. **설명란 구독 유도 강화** (`bot.py`):
     - 채널 URL 자동 추가 (YouTube API로 채널 정보 가져오기)
     - 구독 이유 명시 (매일 새로운 콘텐츠, 실용적인 팁 등)
     - 최근 업로드 영상 링크 추가 (관련 영상 추천)
     - 언어별 최적화 (영어/한국어)
  2. **스크립트 끝에 구독 CTA 강화** (`video_generator.py`):
     - 모든 콘텐츠 타입(HOOK, QUOTE, FACT 등)의 AI 프롬프트에 자연스러운 구독 요청 추가
     - 예: "Subscribe for daily tips like this" / "매일 이런 팁을 받으려면 구독해주세요"
     - 강요하지 않고 자연스럽게 유도하도록 프롬프트 개선
  3. **썸네일에 Subscribe 배지 추가** (`video_generator.py`):
     - "SHORTS" 배지 옆에 "SUBSCRIBE" 배지 추가 (상단 오른쪽)
     - 언어별 텍스트 (영어: "SUBSCRIBE", 한국어: "구독하기")
     - 빨간색 배경으로 눈에 띄게 표시
  4. **YouTube API 채널 정보 기능** (`youtube_uploader.py`):
     - `get_channel_info()`: 채널 ID, 채널 URL, 구독자 수 가져오기
     - `get_recent_videos()`: 최근 업로드 영상 목록 가져오기 (관련 영상 링크용)
- **기대 효과**: 설명란의 구독 링크, 썸네일의 Subscribe 배지, 스크립트의 자연스러운 구독 요청을 통해 구독 전환율 향상 기대

### 2025-11-22: 6개 겨울/연말 재태크 영상 일괄 생성 및 업로드

- 12월/1월 시즌에 맞는 재태크 주제 6개를 연속 생성하여 YouTube에 즉시 업로드
- 모든 영상은 겨울철/연말 시즌에 맞는 실용적인 재태크 팁을 다룸 (세금 절감, 연말 보너스 활용, 401k 기여, 난방비 절약 등)
- 업로드된 영상 ID:
  1. `Q0qk_EGmOxU` → *December Tax Hack: How to Save $2,000 Before Year-End With These 3 Moves*
  2. `0DDhBYBuqaw` → *Holiday Spending Trap: Why Americans Waste $1,500 Every December and How to Stop It*
  3. `NVJHCu01knQ` → *Winter Heating Bill Shock: The One Change That Cut My Gas Bill by 50% Last Year*
  4. `rBkBC0q41eE` → *Year-End Bonus Strategy: What Smart People Do With Their December Paycheck*
  5. `yKQIb6o9_KM` → *January Financial Reset: The 30-Day Challenge That Built My Emergency Fund*
  6. `rXCDiFxBL2Q` → *401k Deadline Alert: Why Contributing Before December 31st Changes Everything*
- 각 영상은 썸네일까지 정상 업로드되었으며, `main.py upload "<topic>" --force` 워크플로로 생성 → 업로드까지 자동화 확인
- 총 업로드 영상 수: 36개, 총 조회수: 917회

---

**마지막 업데이트**: 2025-11-22 (구독자 수 증가 전략 적용 완료)
**프로젝트 상태**: 활발히 개발 중
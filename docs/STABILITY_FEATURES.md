# 안정성 및 모니터링 기능

이 문서는 YouTube Shorts 자동화 시스템의 안정성 및 모니터링 기능에 대해 설명합니다.

## 📋 목차

- [자동 재시도 로직](#자동-재시도-로직)
- [API 할당량 관리](#api-할당량-관리)
- [구조화된 로깅](#구조화된-로깅)
- [성능 메트릭 추적](#성능-메트릭-추적)

---

## 🔄 자동 재시도 로직

API 호출 실패 시 자동으로 재시도하여 일시적인 네트워크 오류나 API 장애를 극복합니다.

### 주요 기능

- **지수 백오프 (Exponential Backoff)**: 재시도 간격이 점진적으로 증가 (1초 → 2초 → 4초...)
- **랜덤 지터 (Jitter)**: 동시 요청 분산으로 서버 부하 방지
- **설정 가능한 재시도**: 최대 재시도 횟수 및 예외 타입 커스터마이징

### 적용된 API

- **OpenAI API**: 스크립트 생성, 키워드 추출, DALL-E 3 썸네일
- **Pexels API**: 영상/이미지 검색 및 다운로드
- **HTTP 다운로드**: 모든 미디어 파일 다운로드

### 동작 예시

```
⚠️ OpenAI API failed (attempt 1/4): Connection timeout
   Retrying in 1.23 seconds...
⚠️ OpenAI API failed (attempt 2/4): Connection timeout
   Retrying in 2.47 seconds...
✅ OpenAI API succeeded on attempt 3
```

---

## 📊 API 할당량 관리

실시간으로 API 사용량을 추적하고 할당량 초과를 방지합니다.

### 주요 기능

- **실시간 사용량 추적**: API 호출마다 자동 기록
- **자동 Rate Limiting**: 할당량 접근 시 자동 대기
- **영구 저장**: 재시작 후에도 사용량 유지
- **시각적 알림**: 색상 코딩된 상태 표시

### 추적되는 API

| API | 제한 | 추적 단위 |
|-----|------|----------|
| OpenAI | 500 RPM | 분당 요청 수 |
| Pexels | 200 RPH | 시간당 요청 수 |
| YouTube | 10,000 units/day | 일일 할당량 |

### 사용법

```bash
# 현재 API 사용 현황 확인
python main.py quota-status
```

**출력 예시:**
```
📊 API Quota Usage Statistics
============================================================

OPENAI:
  Status: 🟢 OK
  Current: 45/500 per minute (9.0%)
  Total (all time): 1,234

PEXELS:
  Status: 🟡 WARNING
  Current: 165/200 per hour (82.5%)
  Total (all time): 3,456

YOUTUBE:
  Status: 🟢 OK
  Current: 1,200/10,000 per day (12.0%)
  Total (all time): 45,678
```

### 환경 변수 설정

`.env` 파일에서 할당량 제한을 커스터마이징할 수 있습니다:

```env
# API Quota Limits
OPENAI_RPM_LIMIT=500          # OpenAI requests per minute
PEXELS_HOURLY_LIMIT=200       # Pexels requests per hour
YOUTUBE_DAILY_QUOTA=10000     # YouTube quota units per day
```

---

## 📝 구조화된 로깅

색상 코딩된 콘솔 출력과 자동 로테이션되는 파일 로그를 제공합니다.

### 주요 기능

- **이중 출력**: 콘솔 (간결) + 파일 (상세)
- **색상 코딩**: 로그 레벨별 색상 구분
- **자동 로테이션**: 10MB 초과 시 자동 백업 (최대 5개 유지)
- **구조화된 형식**: 타임스탬프, 파일명, 라인 번호 포함

### 로그 레벨

| 레벨 | 색상 | 용도 |
|------|------|------|
| DEBUG | 🔵 Cyan | 상세 디버깅 정보 |
| INFO | 🟢 Green | 일반 정보 메시지 |
| WARNING | 🟡 Yellow | 경고 메시지 |
| ERROR | 🔴 Red | 에러 메시지 |
| CRITICAL | 🟣 Magenta | 치명적 오류 |

### 로그 파일 위치

```
logs/
├── youtubeshorts.log       # 메인 로그
├── youtubeshorts.log.1     # 백업 1
├── youtubeshorts.log.2     # 백업 2
└── ...
```

### 코드 예시

```python
from src.utils.logger import get_logger

logger = get_logger('youtubeshorts')

logger.info("영상 생성 시작")
logger.warning("API 할당량 80% 도달")
logger.error("영상 다운로드 실패")
```

---

## ⏱️ 성능 메트릭 추적

영상 생성 및 API 호출의 성능을 자동으로 추적하고 분석합니다.

### 추적되는 메트릭

**영상 생성:**
- 생성 시간 (초)
- 성공/실패 여부
- API 호출 횟수
- 파일 크기
- 주제

**API 호출:**
- 서비스명 (OpenAI, Pexels, YouTube)
- 엔드포인트
- 응답 시간
- 성공/실패 여부

**에러:**
- 에러 타입
- 메시지
- 컨텍스트

### 데이터 저장

메트릭은 JSON 형식으로 저장됩니다:
```
logs/performance_metrics.json
```

### 코드 예시

```python
from src.utils.performance_tracker import get_performance_tracker

tracker = get_performance_tracker()

# 영상 생성 추적
tracker.track_video_generation(
    duration=42.5,
    success=True,
    video_length=30.0,
    api_calls=12,
    file_size=5242880,
    topic="Money Tips"
)

# 성과 요약 출력
tracker.print_summary(last_n_days=7)
```

**출력 예시:**
```
📊 Performance Summary (Last 7 Days)
============================================================

🎬 Video Generation:
  Total: 25
  Successful: 24 (96.0%)
  Avg Duration: 42.3s
  Avg API Calls: 12.5

🔌 API Calls:
  Total: 312
  Successful: 308 (98.7%)

❌ Errors:
  Total: 3
```

---

## 🔧 문제 해결

### 로그 파일이 생성되지 않음

```bash
# logs 디렉토리 권한 확인
ls -la logs/

# 디렉토리가 없으면 생성
mkdir -p logs
```

### 할당량 데이터 초기화

```bash
# 할당량 데이터 삭제 (주의: 모든 사용 이력 삭제됨)
rm ~/.gemini/antigravity/quota_usage.json
```

### 성능 메트릭 초기화

```bash
# 성능 메트릭 삭제
rm logs/performance_metrics.json
```

---

## 📚 관련 문서

- [메인 README](../README.md)
- [API 설정 가이드](./API_SETUP.md)
- [프로젝트 구조](./PROJECT_STRUCTURE.md)

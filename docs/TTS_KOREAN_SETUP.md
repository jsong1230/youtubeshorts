# 한글 TTS 발음 개선 가이드

## 현재 상황

한글 TTS 발음이 만족스럽지 않은 경우, 더 나은 품질의 TTS 엔진을 사용할 수 있습니다.

## 사용 가능한 TTS 옵션

### 1. Google Cloud Text-to-Speech (권장 - 한글 발음 최고)

**장점:**
- 한글 발음이 매우 자연스럽고 정확함
- 다양한 음성 선택 가능 (여성/남성)
- Wavenet 모델은 매우 자연스러운 발음

**설정 방법:**
자세한 설정 가이드는 [GOOGLE_CLOUD_TTS_SETUP.md](./GOOGLE_CLOUD_TTS_SETUP.md)를 참고하세요.

**환경 변수 설정:**
```env
TTS_PROVIDER=google_cloud
GOOGLE_CLOUD_CREDENTIALS_PATH=./google-cloud-tts-key.json
```

**비용:**
- Standard 모델: 월 0~4백만자 무료, 이후 $4/100만자
- Wavenet 모델: 월 0~1백만자 무료, 이후 $16/100만자
- Shorts 영상 기준: 약 1000자/영상 → 월 30개 영상 = 약 3만자 (무료 범위 내)

### 2. OpenAI TTS (현재 기본)

**장점:**
- 설정이 간단함 (이미 OpenAI API 키 사용 중)
- 다양한 음성 선택 가능

**단점:**
- 한글 발음이 완벽하지 않을 수 있음

**설정:**
```env
TTS_PROVIDER=openai
```

**한글 voice 개선:**
- 현재 `nova` voice 사용 중 (한글에 가장 적합)
- 다른 옵션: `shimmer` (더 부드러운 여성 음성)

### 3. gTTS (기본 폴백)

**장점:**
- 무료
- 설정 불필요

**단점:**
- 한글 발음이 다소 기계적일 수 있음

## 추천 설정

**한글 발음 최우선:**
```env
TTS_PROVIDER=google_cloud
GOOGLE_CLOUD_CREDENTIALS_PATH=/path/to/service-account-key.json
```

**간단한 설정 (OpenAI 사용 중):**
```env
TTS_PROVIDER=openai
# voice는 자동으로 nova 선택 (한글에 최적)
```

## Voice 선택 가이드

### Google Cloud TTS (한글)
- `ko-KR-Wavenet-A`: 여성, 최고 품질 (권장)
- `ko-KR-Wavenet-B`: 남성, 최고 품질
- `ko-KR-Standard-A`: 여성, 무료 할당량
- `ko-KR-Standard-B`: 남성, 무료 할당량

### OpenAI TTS (한글)
- `nova`: 밝고 활기찬 여성 음성 (현재 기본, 한글에 적합)
- `shimmer`: 부드러운 여성 음성
- `alloy`: 중립적인 음성

## 테스트 방법

```bash
# Google Cloud TTS 테스트
python main.py test "테스트 주제"

# OpenAI TTS 테스트
TTS_PROVIDER=openai python main.py test "테스트 주제"
```

## 비용 비교

| TTS 엔진 | 무료 할당량 | 이후 비용 | 한글 품질 |
|---------|-----------|---------|----------|
| Google Cloud (Wavenet) | 100만자/월 | $16/100만자 | ⭐⭐⭐⭐⭐ |
| Google Cloud (Standard) | 400만자/월 | $4/100만자 | ⭐⭐⭐⭐ |
| OpenAI TTS | 없음 | $15/100만자 | ⭐⭐⭐ |
| gTTS | 무제한 | 무료 | ⭐⭐ |

**월 예상 사용량 (하루 1개 영상 기준):**
- 영상당 약 1000자
- 월 30개 영상 = 약 3만자
- 모든 옵션이 무료 범위 내


















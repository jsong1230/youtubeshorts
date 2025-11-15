# TTS 개선 방법 가이드

## 현재 상황
- 영어 회화 주제는 제거되었습니다
- 스크립트 생성 시 영어 문장 포함을 방지하도록 프롬프트가 수정되었습니다
- 하지만 혹시 영어 단어가 포함된 경우 TTS 발음이 어색할 수 있습니다

## TTS 개선 방법

### 1. 현재 사용 중인 TTS 엔진
- **gTTS (Google Text-to-Speech)**: 기본 사용, 한국어에 특화되어 있지만 영어 발음이 어색할 수 있음
- **OpenAI TTS**: 선택적 사용 가능, 하지만 한국어를 완벽하게 지원하지 않음

### 2. 개선 방법

#### 방법 A: OpenAI TTS 사용 (권장)
OpenAI TTS는 한국어를 지원하지만 완벽하지 않습니다. 설정 방법:

```bash
# .env 파일에 추가
TTS_PROVIDER=openai
```

**장점:**
- 더 자연스러운 발음
- 다양한 음성 선택 가능 (nova, alloy, echo 등)

**단점:**
- 한국어 지원이 완벽하지 않음
- API 비용 발생

#### 방법 B: Naver Clova Voice 사용 (최고 품질)
Naver Clova Voice는 한국어 TTS에서 가장 자연스러운 발음을 제공합니다.

**설정 방법:**
1. Naver Cloud Platform에서 Clova Voice API 키 발급
2. `src/pipeline/tts_engine.py`에 Clova Voice 엔진 추가
3. `.env` 파일에 API 키 추가

**장점:**
- 한국어 발음이 매우 자연스러움
- 다양한 음성 선택 가능

**단점:**
- API 키 발급 필요
- 유료 서비스 (무료 할당량 있음)

#### 방법 C: Google Cloud Text-to-Speech 사용
Google Cloud TTS는 한국어와 영어 모두 우수한 품질을 제공합니다.

**설정 방법:**
1. Google Cloud Platform에서 프로젝트 생성
2. Text-to-Speech API 활성화
3. 서비스 계정 키 발급
4. `src/pipeline/tts_engine.py`에 Google Cloud TTS 엔진 추가

**장점:**
- 한국어와 영어 모두 우수한 품질
- 다양한 음성 선택 가능

**단점:**
- API 키 발급 필요
- 유료 서비스 (무료 할당량 있음)

#### 방법 D: 스크립트 후처리 (간단한 방법)
영어 단어가 포함된 경우 자동으로 한글 발음으로 변환하는 로직 추가

**예시:**
- "AI" → "에이아이"
- "CEO" → "씨이오"
- "OK" → "오케이"

이 방법은 `_generate_script` 후처리 단계에서 구현 가능합니다.

### 3. 권장 사항
1. **즉시 적용 가능**: 스크립트 생성 시 영어 제외 프롬프트 강화 (이미 적용됨)
2. **단기 개선**: OpenAI TTS 사용 (`TTS_PROVIDER=openai` 설정)
3. **장기 개선**: Naver Clova Voice 또는 Google Cloud TTS 통합

### 4. 현재 설정 확인
```bash
# .env 파일에서 확인
cat .env | grep TTS_PROVIDER
```

### 5. 테스트 방법
```bash
# 테스트 영상 생성
python3 main.py test

# 생성된 영상의 음성 품질 확인
open output/videos/shorts_*.mp4
```

## 추가 참고사항
- 현재 코드는 영어 회화 주제를 완전히 제거했습니다
- 모든 콘텐츠 타입의 프롬프트에 "한국어로만 작성" 지시가 추가되었습니다
- 혹시 영어 단어가 포함되더라도 gTTS가 처리하지만, 발음이 어색할 수 있습니다


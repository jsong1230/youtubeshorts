# API 설정 가이드

## AI API 선택

이 프로젝트는 두 가지 AI API를 지원합니다:

1. **OpenAI API**: GPT-4o-mini, GPT-4o, GPT-3.5-turbo 모델 사용
2. **Claude API**: Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Sonnet 모델 사용

### API 제공자 설정

`.env` 파일에서 `AI_API_PROVIDER` 설정으로 사용할 API를 선택할 수 있습니다:

```env
# OpenAI 사용 (기본값)
AI_API_PROVIDER=openai

# 또는 Claude 사용
AI_API_PROVIDER=claude
```

**참고**: 
- 둘 다 설정하면 `AI_API_PROVIDER` 설정에 따라 우선 사용할 API가 결정됩니다
- 선택한 API가 실패하면 자동으로 다른 API로 폴백됩니다
- 둘 중 하나만 설정해도 됩니다

## OpenAI API 키 발급

### 1. API 키 발급

1. [OpenAI Platform](https://platform.openai.com/) 접속
2. 계정 생성 또는 로그인
3. **API Keys** 메뉴에서 새 API 키 생성
4. `.env` 파일에 `OPENAI_API_KEY` 설정

### 2. 모델 접근 권한 확인

일부 모델은 별도의 접근 권한이 필요할 수 있습니다:
- **Settings** > **Model access** 또는 **Organization** > **Settings** 이동
- 사용 가능한 모델 목록 확인
- `gpt-4o-mini`, `gpt-4o`, `gpt-3.5-turbo` 등이 활성화되어 있는지 확인

## Claude API 키 발급

### 1. API 키 발급

1. [Anthropic Platform](https://console.anthropic.com/) 접속
2. 계정 생성 또는 로그인
3. **API Keys** 메뉴에서 새 API 키 생성
4. `.env` 파일에 `CLAUDE_API_KEY` 설정
5. `.env` 파일에 `AI_API_PROVIDER=claude` 설정 (Claude를 우선 사용하려면)

### 2. 모델 접근 권한

Claude API는 기본적으로 다음 모델에 접근할 수 있습니다:
- `claude-3-5-sonnet-20241022` (권장)
- `claude-3-opus-20240229`
- `claude-3-sonnet-20240229`

코드는 자동으로 위 모델을 순서대로 시도합니다.

## OpenAI API 키 문제 해결

### 문제
```
Error code: 403 - Project does not have access to model `gpt-3.5-turbo`
```

### 해결 방법

1. **OpenAI Platform 접속**
   - https://platform.openai.com/ 접속
   - 로그인

2. **모델 접근 권한 확인**
   - **Settings** > **Model access** 또는 **Organization** > **Settings** 이동
   - 사용 가능한 모델 목록 확인
   - `gpt-4o-mini`, `gpt-4o`, `gpt-3.5-turbo` 등이 활성화되어 있는지 확인

3. **API 키 확인**
   - **API keys** 메뉴에서 현재 사용 중인 API 키 확인
   - 새 API 키 생성 (필요시)

4. **과금 설정 확인**
   - **Billing** 메뉴에서 결제 정보 확인
   - 일부 모델은 과금 설정이 필요할 수 있음

### 대안

코드는 자동으로 다음 모델을 순서대로 시도합니다:
1. `gpt-4o-mini` (가장 저렴하고 접근 가능)
2. `gpt-4o`
3. `gpt-3.5-turbo`

모든 모델 접근이 실패하면:
1. Claude API로 자동 폴백 (Claude API가 설정된 경우)
2. 또는 기본 템플릿을 사용합니다

---

## YouTube API 권한 문제 해결

### 문제
```
Request had insufficient authentication scopes
Insufficient Permission
```

### 해결 방법

1. **기존 token.json 삭제**
   ```bash
   rm token.json
   ```

2. **재인증**
   ```bash
   python main.py upload
   ```
   - 브라우저에서 인증 진행
   - **필요한 권한 모두 승인**:
     - ✅ YouTube에 영상 업로드
     - ✅ YouTube 계정 정보 보기

3. **Google Cloud Console 확인**
   - https://console.cloud.google.com/ 접속
   - **API 및 서비스** > **사용자 인증 정보**
   - OAuth 2.0 클라이언트 ID의 **승인된 범위** 확인
   - 다음 스코프가 포함되어야 함:
     - `https://www.googleapis.com/auth/youtube.upload`
     - `https://www.googleapis.com/auth/youtube.readonly`

### 참고

코드가 자동으로 필요한 스코프를 요청하지만, 기존 token.json이 이전 스코프로 생성되었다면 재인증이 필요합니다.

---

## AI API 폴백 동작

시스템은 다음과 같이 자동으로 폴백합니다:

1. **설정된 API 사용**: `AI_API_PROVIDER` 설정에 따라 OpenAI 또는 Claude API 사용
2. **API 실패 시**: 선택한 API가 실패하면 자동으로 다른 API로 전환
   - OpenAI 실패 → Claude로 폴백 (Claude API가 설정된 경우)
   - Claude 실패 → OpenAI로 폴백 (OpenAI API가 설정된 경우)
3. **모두 실패 시**: 기본 템플릿 스크립트 사용

이를 통해 API 장애나 할당량 초과 시에도 영상 생성이 계속됩니다.


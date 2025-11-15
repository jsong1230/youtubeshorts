# API 설정 가이드

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

모든 모델 접근이 실패하면 기본 템플릿을 사용합니다.

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


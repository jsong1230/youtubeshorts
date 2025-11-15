# Google OAuth2 설정 가이드

## redirect_uri_mismatch 오류 해결 방법

이 오류는 Google Cloud Console에 등록된 리디렉션 URI와 코드에서 사용하는 URI가 일치하지 않아 발생합니다.

### 해결 방법

1. **Google Cloud Console 접속**
   - https://console.cloud.google.com/ 접속
   - 프로젝트 선택

2. **OAuth 2.0 클라이언트 ID 설정**
   - **API 및 서비스** > **사용자 인증 정보** 이동
   - OAuth 2.0 클라이언트 ID 클릭 (또는 새로 생성)

3. **승인된 리디렉션 URI 추가**
   다음 URI들을 **승인된 리디렉션 URI**에 추가하세요:
   ```
   http://localhost:8080/
   http://127.0.0.1:8080/
   http://localhost/
   ```
   
   **참고**: `urn:ietf:wg:oauth:2.0:oob`는 웹 애플리케이션 유형에서는 사용할 수 없습니다.

4. **저장 후 재시도**
   - 변경사항 저장
   - `python main.py upload` 다시 실행

### 참고사항

- 변경사항이 반영되는데 몇 분 정도 걸릴 수 있습니다
- 여러 개의 리디렉션 URI를 등록해도 됩니다
- `urn:ietf:wg:oauth:2.0:oob`는 데스크톱 앱용 특수 URI입니다


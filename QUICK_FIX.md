# 빠른 해결 방법

## 400 오류 (redirect_uri_mismatch) 해결

### ✅ 해결 방법: Google Cloud Console에서 리디렉션 URI 추가

**중요:** `urn:ietf:wg:oauth:2.0:oob`는 추가하지 마세요! (웹 애플리케이션 유형에서는 사용 불가)

1. https://console.cloud.google.com/ 접속
2. **API 및 서비스** > **사용자 인증 정보**
3. OAuth 2.0 클라이언트 ID 클릭
4. **승인된 리디렉션 URI**에 다음 3개만 추가:
   ```
   http://localhost:8080/
   http://127.0.0.1:8080/
   http://localhost/
   ```
5. **저장** (변경사항 반영까지 1-2분 소요)

### 📝 참고사항

- 현재 클라이언트 ID가 "웹 애플리케이션" 유형이므로 `urn:ietf:wg:oauth:2.0:oob`는 사용할 수 없습니다
- 위 3개의 URI만 추가하면 정상 작동합니다
- 코드는 자동으로 여러 인증 방법을 시도합니다:
  1. 포트 8080 사용
  2. 랜덤 포트 사용
  3. 수동 인증 코드 입력

### 🚀 실행

설정 저장 후:
```bash
python main.py upload
```

### 🔄 대안: 데스크톱 앱 유형 사용 (선택사항)

만약 `urn:ietf:wg:oauth:2.0:oob`를 사용하고 싶다면:
1. Google Cloud Console에서 **새로운 OAuth 2.0 클라이언트 ID 생성**
2. **애플리케이션 유형: 데스크톱 앱** 선택
3. 생성된 새 Client ID와 Secret을 `.env` 파일에 업데이트
4. `urn:ietf:wg:oauth:2.0:oob`를 리디렉션 URI에 추가

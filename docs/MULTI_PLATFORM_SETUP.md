# 멀티 플랫폼 업로드 설정 가이드

이 프로젝트는 생성한 영상을 YouTube, TikTok, Instagram 등 여러 플랫폼에 동시에 업로드할 수 있는 기능을 제공합니다.

## 📋 지원 플랫폼

- ✅ **YouTube Shorts** (기본 활성화)
- 🔄 **TikTok** (선택사항, API 설정 필요)
- 🔄 **Instagram Reels** (선택사항, API 설정 필요)

## ⚙️ 설정 방법

### 1. 기본 설정 (.env 파일)

`.env` 파일에 다음 설정을 추가하세요:

```env
# 멀티 플랫폼 업로드 활성화
ENABLE_TIKTOK_UPLOAD=false
ENABLE_INSTAGRAM_UPLOAD=false
```

### 2. TikTok API 설정

TikTok 업로드를 사용하려면:

1. **TikTok for Developers** 접속
   - https://developers.tiktok.com/ 에서 계정 생성
   - 앱 생성 및 승인 대기

2. **API 키 발급**
   - Client Key와 Client Secret 발급
   - OAuth 2.0 인증 플로우 완료

3. **.env 파일에 추가**
```env
ENABLE_TIKTOK_UPLOAD=true
TIKTOK_CLIENT_KEY=your_client_key_here
TIKTOK_CLIENT_SECRET=your_client_secret_here
TIKTOK_ACCESS_TOKEN=your_access_token_here
```

**참고**: TikTok API는 비즈니스 계정이 필요하며, 승인 과정이 필요할 수 있습니다.

### 3. Instagram Graph API 설정

Instagram Reels 업로드를 사용하려면:

1. **Facebook for Developers** 접속
   - https://developers.facebook.com/ 에서 앱 생성
   - Instagram Graph API 추가

2. **Instagram 비즈니스 계정 필요**
   - 개인 계정을 비즈니스 계정으로 전환
   - Facebook 페이지와 연결

3. **API 키 발급**
   - App ID, App Secret 발급
   - Access Token 생성
   - Instagram Account ID 확인

4. **.env 파일에 추가**
```env
ENABLE_INSTAGRAM_UPLOAD=true
INSTAGRAM_APP_ID=your_app_id_here
INSTAGRAM_APP_SECRET=your_app_secret_here
INSTAGRAM_ACCESS_TOKEN=your_access_token_here
INSTAGRAM_ACCOUNT_ID=your_instagram_account_id_here
```

**참고**: Instagram Graph API는 Facebook 앱 승인과 Instagram 비즈니스 계정이 필요합니다.

## 🚀 사용 방법

### 자동 업로드 (멀티 플랫폼)

```bash
# 모든 활성화된 플랫폼에 동시 업로드
python main.py upload
```

### 특정 플랫폼만 업로드

코드에서 `upload_to_all()` 메서드의 `platforms` 파라미터를 사용하여 특정 플랫폼만 선택할 수 있습니다.

## ⚠️ 주의사항

### 1. API 제한사항

- **TikTok**: 일일 업로드 제한이 있을 수 있습니다
- **Instagram**: Reels 업로드 제한 및 승인 필요
- **YouTube**: 일일 할당량 확인 필요

### 2. 영상 형식

모든 플랫폼이 세로형 영상(9:16, 1080x1920)을 지원하므로, 현재 생성되는 영상 형식이 적합합니다.

### 3. 콘텐츠 정책

각 플랫폼의 커뮤니티 가이드라인을 준수해야 합니다:
- YouTube 커뮤니티 가이드라인
- TikTok 커뮤니티 가이드라인
- Instagram 커뮤니티 가이드라인

### 4. 인증 토큰 관리

- TikTok과 Instagram의 Access Token은 만료될 수 있습니다
- 토큰 갱신 로직을 구현하거나 수동으로 갱신해야 할 수 있습니다

## 🔧 문제 해결

### TikTok 업로드 실패

1. API 키 확인
2. TikTok for Developers에서 앱 승인 상태 확인
3. OAuth 인증 플로우 재진행

### Instagram 업로드 실패

1. Facebook 앱 승인 상태 확인
2. Instagram 비즈니스 계정 확인
3. Access Token 유효성 확인
4. Instagram Account ID 확인

## 📚 추가 리소스

- [TikTok for Developers](https://developers.tiktok.com/)
- [Instagram Graph API 문서](https://developers.facebook.com/docs/instagram-api/)
- [Facebook for Developers](https://developers.facebook.com/)

## 💡 향후 개선 사항

- 자동 토큰 갱신
- 업로드 실패 시 재시도 로직
- 플랫폼별 통계 추적
- 플랫폼별 최적화된 제목/설명 자동 생성


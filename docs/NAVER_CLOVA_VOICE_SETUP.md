# Naver Clova Voice TTS 설정 가이드

## 개요

Naver Clova Voice는 한글 발음이 매우 자연스럽고 정확한 TTS 서비스입니다. 동기부여/힐링 콘텐츠에 최적화된 차분하고 따뜻한 음성을 제공합니다.

## 1단계: Naver Cloud Platform 계정 생성 및 API 키 발급

### 1.1 Naver Cloud Platform 가입
1. [Naver Cloud Platform](https://www.ncloud.com/) 접속
2. 회원가입 및 로그인
3. 본인인증 완료

### 1.2 CLOVA Voice 서비스 신청
1. 콘솔에서 **AI·NAVER API** → **CLOVA Voice** 선택
2. **서비스 신청** 클릭
3. 약관 동의 및 신청 완료

### 1.3 Application 등록 및 API 키 발급
1. **Application** 메뉴에서 **Application 등록** 클릭
2. Application 이름 입력 (예: "YouTube Shorts Bot")
3. **CLOVA Voice** 서비스 선택
4. 등록 완료 후 **인증 정보** 탭에서 다음 정보 확인:
   - **Client ID**
   - **Client Secret**

## 2단계: 환경 변수 설정

`.env` 파일에 다음 정보를 추가하세요:

```env
# Naver Clova Voice TTS
NAVER_CLOVA_CLIENT_ID=your_client_id_here
NAVER_CLOVA_CLIENT_SECRET=your_client_secret_here
TTS_PROVIDER=naver_clova
```

## 3단계: Python 패키지 설치

Naver Clova Voice API는 REST API로 제공되므로 `requests` 라이브러리만 필요합니다 (이미 설치되어 있을 가능성이 높습니다):

```bash
pip install requests
```

## 4단계: 코드 통합

코드에 Naver Clova Voice 엔진이 자동으로 추가됩니다. `src/pipeline/tts_engine.py`에 `ClovaVoiceEngine` 클래스가 추가됩니다.

## 5단계: 사용 가능한 음성 목록

Naver Clova Voice는 다양한 음성을 제공합니다:

### 여성 음성 (동기부여/힐링 콘텐츠에 적합)
- `nara`: 차분하고 따뜻한 여성 음성 (권장)
- `nkyungsu`: 부드러운 여성 음성
- `ndain`: 밝고 활기찬 여성 음성
- `nmeow`: 귀여운 톤의 여성 음성

### 남성 음성
- `njinho`: 차분한 남성 음성
- `nminsang`: 따뜻한 남성 음성

### 기본 설정
- 동기부여/힐링 콘텐츠에는 `nara` 음성이 기본으로 사용됩니다.
- `.env` 파일에 `NAVER_CLOVA_VOICE_NAME=nara`로 설정하여 변경할 수 있습니다.

## 6단계: 테스트

설정이 완료되면 테스트 영상을 생성해보세요:

```bash
python main.py test "테스트 주제"
```

생성된 영상의 음성을 확인하여 음성 품질을 평가하세요.

## 비용 정보

### 무료 할당량
- 월 1,000,000자 무료 제공
- YouTube Shorts 기준: 약 1,000자/영상
- 월 30개 영상 = 약 30,000자 (무료 범위 내)

### 유료 요금
- 무료 할당량 초과 시: 1,000자당 10원
- 월 30개 영상 기준: 무료 범위 내에서 사용 가능

## 문제 해결

### API 키 오류
- Client ID와 Client Secret이 정확한지 확인
- `.env` 파일에 올바르게 설정되었는지 확인
- Naver Cloud Platform 콘솔에서 Application이 활성화되어 있는지 확인

### 음성 생성 실패
- 네트워크 연결 확인
- API 할당량 확인 (콘솔에서 확인 가능)
- 로그 파일에서 상세 에러 메시지 확인

## 참고 자료

- [Naver Cloud Platform CLOVA Voice 가이드](https://guide.ncloud-docs.com/docs/ko/clovavoice-clovavoice)
- [CLOVA Voice API 문서](https://api.ncloud-docs.com/docs/ai-naver-clovavoice-ttspremium)

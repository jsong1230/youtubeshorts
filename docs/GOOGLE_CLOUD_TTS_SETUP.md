# Google Cloud TTS 설정 가이드

## 서비스 계정 키 파일 생성 방법

### 1. Google Cloud Console 접속
1. https://console.cloud.google.com/ 접속
2. 프로젝트 선택: `youtubeshorts-478213`

### 2. 서비스 계정 키 생성
1. **IAM 및 관리자** → **서비스 계정** 메뉴로 이동
2. 서비스 계정 찾기: `vertex-express@youtubeshorts-478213.iam.gserviceaccount.com`
3. 서비스 계정 클릭 → **키** 탭
4. **키 추가** → **새 키 만들기** 선택
5. 키 유형: **JSON** 선택
6. **만들기** 클릭 → JSON 파일이 자동 다운로드됨

### 3. 키 파일 저장
다운로드된 JSON 파일을 프로젝트 디렉토리에 저장:
```bash
# 예: 프로젝트 루트에 저장
cp ~/Downloads/youtubeshorts-478213-*.json ./google-cloud-tts-key.json
```

### 4. 환경 변수 설정
`.env` 파일에 추가:
```env
TTS_PROVIDER=google_cloud
GOOGLE_CLOUD_CREDENTIALS_PATH=./google-cloud-tts-key.json
```

### 5. 패키지 설치
```bash
pip install google-cloud-texttospeech
```

### 6. Text-to-Speech API 활성화 확인
Google Cloud Console에서:
1. **API 및 서비스** → **라이브러리**
2. "Cloud Text-to-Speech API" 검색
3. 활성화되어 있는지 확인 (없으면 활성화)

## 테스트
```bash
python main.py test "테스트 주제"
```

## 보안 주의사항
- 서비스 계정 키 파일은 절대 Git에 커밋하지 마세요
- `.gitignore`에 키 파일 경로가 포함되어 있는지 확인하세요















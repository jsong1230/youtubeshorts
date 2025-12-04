# Google Cloud 서비스 계정 키 파일 생성 가이드

## 키 파일이란?
Google Cloud TTS를 사용하려면 서비스 계정 키 파일(JSON)이 필요합니다. 이 파일은 Google Cloud에서 다운로드해야 합니다.

## 키 파일 생성 방법 (단계별)

### 1단계: Google Cloud Console 접속
1. 브라우저에서 https://console.cloud.google.com/ 접속
2. 프로젝트 선택: **youtubeshorts-478213** (상단 프로젝트 선택 드롭다운)

### 2단계: 서비스 계정 페이지로 이동
1. 왼쪽 메뉴에서 **IAM 및 관리자** 클릭
2. **서비스 계정** 클릭

### 3단계: 서비스 계정 찾기
1. 서비스 계정 목록에서 다음 계정 찾기:
   ```
   vertex-express@youtubeshorts-478213.iam.gserviceaccount.com
   ```
2. 해당 서비스 계정을 **클릭**

### 4단계: 키 생성
1. 상단 탭에서 **키** 탭 클릭
2. **키 추가** 버튼 클릭
3. **새 키 만들기** 선택
4. 키 유형: **JSON** 선택 (중요!)
5. **만들기** 버튼 클릭

### 5단계: 키 파일 다운로드
- 자동으로 JSON 파일이 다운로드됩니다
- 파일명 예시: `youtubeshorts-478213-xxxxx-xxxxx.json`
- 보통 **다운로드 폴더**에 저장됩니다

### 6단계: 키 파일을 프로젝트로 이동
다운로드된 파일을 프로젝트 폴더로 복사:

```bash
# 다운로드 폴더에서 프로젝트로 복사
cp ~/Downloads/youtubeshorts-478213-*.json ~/dev/jsong1230-github/youtubeshorts/google-cloud-tts-key.json
```

또는 파일 탐색기에서:
1. 다운로드 폴더에서 JSON 파일 찾기
2. 프로젝트 폴더(`youtubeshorts`)로 복사
3. 파일명을 `google-cloud-tts-key.json`으로 변경 (선택사항)

### 7단계: 환경 변수 설정
`.env` 파일에 추가:
```env
TTS_PROVIDER=google_cloud
GOOGLE_CLOUD_CREDENTIALS_PATH=./google-cloud-tts-key.json
```

## 빠른 링크
- 서비스 계정 페이지: https://console.cloud.google.com/iam-admin/serviceaccounts?project=youtubeshorts-478213
- Text-to-Speech API 활성화: https://console.cloud.google.com/apis/library/texttospeech.googleapis.com?project=youtubeshorts-478213

## 주의사항
- 키 파일은 절대 Git에 커밋하지 마세요 (이미 .gitignore에 추가됨)
- 키 파일을 잃어버리면 새로 생성해야 합니다
- 키 파일은 보안상 중요하므로 안전하게 보관하세요

## 문제 해결
- 키 파일을 찾을 수 없으면: 다운로드 폴더 확인
- "API가 활성화되지 않았습니다" 오류: Text-to-Speech API 활성화 필요
- "권한이 없습니다" 오류: 서비스 계정에 "Cloud Text-to-Speech API 사용자" 역할 부여 필요









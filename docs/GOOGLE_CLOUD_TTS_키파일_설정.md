# Google Cloud TTS 키 파일 설정 방법 (단계별 가이드)

## 📋 준비물
- Google 계정
- 프로젝트: `youtubeshorts-478213`
- 서비스 계정: `vertex-express@youtubeshorts-478213.iam.gserviceaccount.com`

---

## 🔑 1단계: Google Cloud Console 접속

1. 브라우저에서 다음 링크 열기:
   ```
   https://console.cloud.google.com/
   ```

2. **프로젝트 선택** (상단 중앙)
   - 드롭다운에서 `youtubeshorts-478213` 선택

---

## 👤 2단계: 서비스 계정 페이지로 이동

**방법 1: 직접 링크**
```
https://console.cloud.google.com/iam-admin/serviceaccounts?project=youtubeshorts-478213
```

**방법 2: 메뉴로 이동**
1. 왼쪽 상단 햄버거 메뉴(☰) 클릭
2. **IAM 및 관리자** 클릭
3. **서비스 계정** 클릭

---

## 🔍 3단계: 서비스 계정 찾기

서비스 계정 목록에서 다음을 찾기:
```
vertex-express@youtubeshorts-478213.iam.gserviceaccount.com
```

**찾는 방법:**
- 목록에서 스크롤하며 찾기
- 검색창에 `vertex-express` 입력
- 이메일 주소를 클릭

---

## 🔐 4단계: 키 파일 생성

1. 서비스 계정을 **클릭** (이메일 주소 클릭)

2. 상단 탭 메뉴에서 **키** 탭 클릭
   ```
   [세부정보] [권한] [키] [역할]
            ↑ 여기 클릭
   ```

3. **키 추가** 버튼 클릭 (오른쪽 상단)

4. 드롭다운 메뉴에서 **새 키 만들기** 선택

5. 키 유형 선택:
   - ✅ **JSON** 선택 (중요!)
   - ❌ P12는 선택하지 마세요

6. **만들기** 버튼 클릭

---

## 📥 5단계: 키 파일 다운로드

- 자동으로 JSON 파일이 다운로드됩니다
- 파일명 예시:
  ```
  youtubeshorts-478213-xxxxx-xxxxx.json
  ```
- 보통 **다운로드 폴더**에 저장됩니다
  - Mac: `~/Downloads/`
  - Windows: `C:\Users\사용자명\Downloads\`

---

## 📁 6단계: 키 파일을 프로젝트로 복사

### Mac/Linux:
```bash
# 터미널에서 실행
cd ~/dev/jsong1230-github/youtubeshorts
cp ~/Downloads/youtubeshorts-478213-*.json ./google-cloud-tts-key.json
```

### 또는 파일 탐색기에서:
1. 다운로드 폴더 열기
2. `youtubeshorts-478213-xxxxx-xxxxx.json` 파일 찾기
3. 파일을 프로젝트 폴더(`youtubeshorts`)로 드래그 앤 드롭
4. (선택사항) 파일명을 `google-cloud-tts-key.json`으로 변경

---

## ⚙️ 7단계: 환경 변수 설정

`.env` 파일을 열고 다음을 추가:

```env
# Google Cloud TTS 설정
TTS_PROVIDER=google_cloud
GOOGLE_CLOUD_CREDENTIALS_PATH=./google-cloud-tts-key.json
```

**파일 위치 확인:**
```bash
# 프로젝트 루트에 .env 파일이 있는지 확인
ls -la .env
```

---

## 📦 8단계: 패키지 설치

```bash
pip install google-cloud-texttospeech
```

---

## ✅ 9단계: Text-to-Speech API 활성화 확인

1. 다음 링크로 이동:
   ```
   https://console.cloud.google.com/apis/library/texttospeech.googleapis.com?project=youtubeshorts-478213
   ```

2. **활성화** 버튼이 보이면 클릭
   - 이미 활성화되어 있으면 "API 사용" 버튼이 보입니다

---

## 🧪 10단계: 테스트

```bash
# 테스트 영상 생성
python main.py test "테스트 주제"
```

성공하면 로그에 다음이 표시됩니다:
```
✅ TTS 엔진 초기화: google_cloud
🔊 Google Cloud TTS 생성: voice=ko-KR-Wavenet-A, speed=1.00, lang=ko
```

---

## 🔒 보안 주의사항

✅ **해야 할 것:**
- 키 파일은 프로젝트 폴더에 저장
- `.gitignore`에 키 파일 추가됨 (이미 설정됨)
- 키 파일을 안전하게 보관

❌ **하지 말아야 할 것:**
- 키 파일을 Git에 커밋하지 않기
- 키 파일을 공유하지 않기
- 키 파일을 삭제하지 않기 (삭제하면 새로 생성해야 함)

---

## 🐛 문제 해결

### "키 파일을 찾을 수 없습니다"
- 다운로드 폴더 확인
- 파일명이 `youtubeshorts-478213-`로 시작하는지 확인
- 프로젝트 폴더에 복사했는지 확인

### "API가 활성화되지 않았습니다"
- 9단계에서 Text-to-Speech API 활성화 확인
- 프로젝트가 `youtubeshorts-478213`인지 확인

### "권한이 없습니다"
- 서비스 계정에 "Cloud Text-to-Speech API 사용자" 역할 부여 필요
- IAM 및 관리자 → 서비스 계정 → 권한 탭에서 확인

### "클라이언트 초기화 실패"
- 키 파일 경로가 올바른지 확인 (`.env` 파일의 `GOOGLE_CLOUD_CREDENTIALS_PATH`)
- 키 파일이 JSON 형식인지 확인
- 키 파일 내용이 올바른지 확인 (JSON 파싱 가능한지)

---

## 📞 빠른 링크

- **서비스 계정**: https://console.cloud.google.com/iam-admin/serviceaccounts?project=youtubeshorts-478213
- **Text-to-Speech API**: https://console.cloud.google.com/apis/library/texttospeech.googleapis.com?project=youtubeshorts-478213
- **프로젝트 선택**: https://console.cloud.google.com/home/dashboard?project=youtubeshorts-478213

---

## 💡 팁

- 키 파일은 한 번만 생성하면 계속 사용 가능
- 키 파일을 잃어버리면 새로 생성해야 함
- 여러 컴퓨터에서 사용하려면 각 컴퓨터에 키 파일 복사 필요





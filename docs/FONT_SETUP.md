# 폰트 설정 가이드 (한글 폰트 깨짐 해결)

## 🎯 문제 해결 방법

한글 폰트가 깨지는 문제를 해결하기 위해 **프로젝트에 폰트 파일을 직접 포함**하는 방식을 사용합니다.

## 📥 폰트 다운로드 방법

### 방법 1: 자동 다운로드 스크립트 (추천)

```bash
./fonts/download_fonts.sh
```

### 방법 2: 수동 다운로드

#### 한글 폰트 (필수)

**나눔고딕 (추천)**
1. https://hangeul.naver.com/2017/nanum 접속
2. "나눔고딕" 다운로드
3. 압축 해제 후 다음 파일들을 `fonts/` 폴더에 복사:
   - `NanumGothic.ttf`
   - `NanumGothicBold.ttf`

또는 직접 다운로드:
- https://github.com/naver/nanumfont/releases/latest
- `NanumGothic.zip` 다운로드

**Noto Sans KR (대안)**
1. https://fonts.google.com/noto/specimen/Noto+Sans+KR 접속
2. "Download family" 클릭
3. 압축 해제 후 다음 파일들을 `fonts/` 폴더에 복사:
   - `NotoSansKR-Regular.ttf`
   - `NotoSansKR-Bold.ttf`

#### 영문 폰트 (선택)

**Roboto (추천)**
1. https://fonts.google.com/specimen/Roboto 접속
2. "Download family" 클릭
3. 압축 해제 후 다음 파일들을 `fonts/` 폴더에 복사:
   - `Roboto-Regular.ttf`
   - `Roboto-Bold.ttf`

## ✅ 설치 확인

다음 명령어로 폰트가 제대로 설치되었는지 확인:

```bash
ls -la fonts/*.ttf
```

예상 출력:
```
fonts/NanumGothic.ttf
fonts/NanumGothicBold.ttf
fonts/Roboto-Regular.ttf (선택)
fonts/Roboto-Bold.ttf (선택)
```

## 🔧 작동 원리

1. 코드가 먼저 `fonts/` 폴더의 폰트를 찾습니다
2. 프로젝트 폰트가 없으면 시스템 폰트를 사용합니다
3. 프로젝트 폰트를 사용하면 한글 깨짐 문제가 해결됩니다

## 📝 필요한 최소 폰트

**한글 폰트 (필수 중 하나):**
- `NanumGothic.ttf` + `NanumGothicBold.ttf` (추천)
- 또는 `NotoSansKR-Regular.ttf` + `NotoSansKR-Bold.ttf`

**영문 폰트 (선택):**
- 시스템 Arial 사용 가능 (추가 다운로드 불필요)
- 또는 `Roboto-Regular.ttf` + `Roboto-Bold.ttf`

## 🚀 빠른 시작

```bash
# 1. fonts 폴더로 이동
cd fonts

# 2. 나눔고딕 다운로드 (직접 링크)
curl -L -o nanum.zip https://github.com/naver/nanumfont/releases/latest/download/NanumGothic.zip
unzip nanum.zip
cp NanumGothic*/NanumGothic*.ttf .
rm -rf NanumGothic* nanum.zip

# 3. 확인
ls -la *.ttf
```

## ⚠️ 주의사항

- 반드시 `.ttf` 파일만 사용하세요 (`.ttc` 파일은 작동하지 않습니다)
- 폰트 파일은 `fonts/` 폴더에 직접 배치하세요 (하위 폴더 안에 두지 마세요)

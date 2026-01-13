# 폰트 수동 다운로드 가이드

자동 다운로드가 실패한 경우, 다음 방법으로 수동으로 다운로드하세요.

## 나눔고딕 폰트 다운로드

### 방법 1: 네이버 한글날 사이트 (가장 안정적)

1. 브라우저에서 다음 링크 열기:
   ```
   https://hangeul.naver.com/2017/nanum
   ```

2. "나눔고딕" 섹션에서 "다운로드" 버튼 클릭

3. 다운로드한 ZIP 파일 압축 해제

4. 다음 파일들을 `fonts/` 폴더로 복사:
   - `NanumGothic.ttf`
   - `NanumGothicBold.ttf`

   ```bash
   cd ~/Downloads  # 또는 다운로드 폴더
   unzip NanumGothic.zip
   cp NanumGothic*/NanumGothic*.ttf /Users/jsong/dev/jsong1230-github/youtubeshorts/fonts/
   ```

### 방법 2: GitHub 릴리즈 페이지

1. 브라우저에서 다음 링크 열기:
   ```
   https://github.com/naver/nanumfont/releases
   ```

2. 최신 릴리즈에서 `NanumGothic.zip` 다운로드

3. 압축 해제 후 `.ttf` 파일들을 `fonts/` 폴더로 복사

### 방법 3: 직접 링크 (브라우저에서)

다음 링크를 브라우저에서 직접 열어서 다운로드:
- https://github.com/naver/nanumfont/releases/download/v2.0/NanumGothic.zip

## 설치 확인

다운로드 후 다음 명령어로 확인:

```bash
cd /Users/jsong/dev/jsong1230-github/youtubeshorts/fonts
ls -lh NanumGothic*.ttf
```

다음과 같은 파일들이 있어야 합니다:
- `NanumGothic.ttf`
- `NanumGothicBold.ttf`

## 문제 해결

### "파일이 손상되었습니다" 오류
- 다운로드를 다시 시도하세요
- 다른 브라우저나 네트워크 환경에서 시도해보세요

### "권한이 없습니다" 오류
- 터미널에서 다음 명령어 실행:
  ```bash
  chmod 755 /Users/jsong/dev/jsong1230-github/youtubeshorts/fonts
  ```

### 폰트가 여전히 깨지는 경우
- 폰트 파일이 실제로 `.ttf` 형식인지 확인:
  ```bash
  file fonts/NanumGothic*.ttf
  ```
- 출력이 "TrueType font"로 나와야 합니다

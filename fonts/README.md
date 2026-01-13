# 폰트 설치 가이드

## 한글 폰트 다운로드

### 방법 1: 나눔고딕 (추천)
1. 다음 링크에서 다운로드:
   - https://hangeul.naver.com/2017/nanum (나눔고딕 다운로드 페이지)
   - 또는 직접 다운로드: https://github.com/naver/nanumfont/releases
   
2. 다운로드한 파일에서 다음 파일들을 추출:
   - `NanumGothic.ttf` (일반체)
   - `NanumGothicBold.ttf` (볼드체)
   
3. 이 폴더(`fonts/`)에 복사:
   ```bash
   cp ~/Downloads/NanumGothic*.ttf fonts/
   ```

### 방법 2: Noto Sans KR (Google 폰트)
1. 다음 링크에서 다운로드:
   - https://fonts.google.com/noto/specimen/Noto+Sans+KR
   - "Download family" 클릭
   
2. 압축 해제 후 다음 파일들을 추출:
   - `NotoSansKR-Regular.ttf`
   - `NotoSansKR-Bold.ttf`
   
3. 이 폴더(`fonts/`)에 복사:
   ```bash
   cp ~/Downloads/NotoSansKR*.ttf fonts/
   ```

## 영문 폰트 다운로드

### 방법 1: Roboto (Google 폰트, 추천)
1. 다음 링크에서 다운로드:
   - https://fonts.google.com/specimen/Roboto
   - "Download family" 클릭
   
2. 압축 해제 후 다음 파일들을 추출:
   - `Roboto-Regular.ttf`
   - `Roboto-Bold.ttf`
   
3. 이 폴더(`fonts/`)에 복사:
   ```bash
   cp ~/Downloads/Roboto*.ttf fonts/
   ```

### 방법 2: Arial (시스템 폰트 사용)
- macOS에 기본 설치되어 있으므로 추가 다운로드 불필요
- 코드에서 자동으로 찾아서 사용

## 설치 확인

다음 명령어로 폰트 파일이 제대로 있는지 확인:
```bash
ls -la fonts/
```

예상 출력:
```
NanumGothic.ttf
NanumGothicBold.ttf
Roboto-Regular.ttf
Roboto-Bold.ttf
```

## 빠른 다운로드 링크

### 나눔고딕 직접 다운로드:
- https://github.com/naver/nanumfont/releases/latest
- `NanumGothic.zip` 다운로드 후 압축 해제

### Noto Sans KR 직접 다운로드:
- https://fonts.google.com/download?family=Noto%20Sans%20KR

### Roboto 직접 다운로드:
- https://fonts.google.com/download?family=Roboto

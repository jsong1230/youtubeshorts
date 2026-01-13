#!/bin/bash
# 폰트 자동 다운로드 스크립트

echo "📥 폰트 다운로드 시작..."

# fonts 디렉토리 생성
mkdir -p fonts
cd fonts

# 나눔고딕 다운로드
echo "📥 나눔고딕 다운로드 중..."
# 여러 다운로드 소스 시도
DOWNLOAD_SUCCESS=false

# 방법 1: 특정 버전 직접 다운로드
if curl -L -f -o nanum.zip "https://github.com/naver/nanumfont/releases/download/v2.0/NanumGothic.zip" 2>/dev/null; then
    if file nanum.zip | grep -q "Zip archive"; then
        DOWNLOAD_SUCCESS=true
    fi
fi

# 방법 2: 최신 릴리즈 페이지에서 직접 링크 찾기
if [ "$DOWNLOAD_SUCCESS" = false ]; then
    echo "   방법 1 실패, 대안 방법 시도 중..."
    # GitHub 릴리즈 페이지에서 실제 다운로드 URL 추출
    DOWNLOAD_URL=$(curl -s "https://api.github.com/repos/naver/nanumfont/releases/latest" | grep '"browser_download_url".*NanumGothic.zip' | cut -d '"' -f 4 | head -1)
    if [ -n "$DOWNLOAD_URL" ]; then
        if curl -L -f -o nanum.zip "$DOWNLOAD_URL" 2>/dev/null; then
            if file nanum.zip | grep -q "Zip archive"; then
                DOWNLOAD_SUCCESS=true
            fi
        fi
    fi
fi

if [ "$DOWNLOAD_SUCCESS" = true ] && [ -f nanum.zip ]; then
    if unzip -q -t nanum.zip 2>/dev/null; then
        unzip -q nanum.zip -d nanum_temp 2>/dev/null
        find nanum_temp -name "NanumGothic*.ttf" -type f -exec cp {} . \; 2>/dev/null
        rm -rf nanum_temp nanum.zip 2>/dev/null
        echo "✅ 나눔고딕 다운로드 완료"
    else
        echo "⚠️ 다운로드된 파일이 손상되었습니다."
        rm -f nanum.zip
        DOWNLOAD_SUCCESS=false
    fi
fi

if [ "$DOWNLOAD_SUCCESS" = false ]; then
    echo "⚠️ 나눔고딕 자동 다운로드 실패. 수동으로 다운로드해주세요:"
    echo "   1. https://hangeul.naver.com/2017/nanum 접속"
    echo "   2. '나눔고딕' 다운로드 클릭"
    echo "   3. 압축 해제 후 NanumGothic*.ttf 파일들을 이 폴더(fonts/)에 복사"
    echo ""
    echo "   또는 직접 다운로드:"
    echo "   https://github.com/naver/nanumfont/releases"
fi

# Noto Sans KR 다운로드
echo "📥 Noto Sans KR 다운로드 중..."
if ! curl -L -o noto.zip "https://fonts.google.com/download?family=Noto%20Sans%20KR" 2>/dev/null; then
    echo "⚠️ Noto Sans KR 자동 다운로드 실패. 수동으로 다운로드해주세요:"
    echo "   https://fonts.google.com/noto/specimen/Noto+Sans+KR"
else
    unzip -q noto.zip -d noto_temp 2>/dev/null || true
    find noto_temp -name "NotoSansKR-*.ttf" -exec cp {} . \; 2>/dev/null || true
    rm -rf noto_temp noto.zip 2>/dev/null || true
    echo "✅ Noto Sans KR 다운로드 완료"
fi

# Roboto 다운로드
echo "📥 Roboto 다운로드 중..."
if ! curl -L -o roboto.zip "https://fonts.google.com/download?family=Roboto" 2>/dev/null; then
    echo "⚠️ Roboto 자동 다운로드 실패. 수동으로 다운로드해주세요:"
    echo "   https://fonts.google.com/specimen/Roboto"
else
    unzip -q roboto.zip -d roboto_temp 2>/dev/null || true
    find roboto_temp -name "Roboto-*.ttf" -exec cp {} . \; 2>/dev/null || true
    rm -rf roboto_temp roboto.zip 2>/dev/null || true
    echo "✅ Roboto 다운로드 완료"
fi

cd ..

echo ""
echo "✅ 폰트 다운로드 완료!"
echo "📁 다운로드된 폰트 확인:"
ls -la fonts/*.ttf 2>/dev/null || echo "   (폰트 파일이 없습니다. 수동으로 다운로드해주세요)"

#!/usr/bin/env python3
"""폰트 테스트 스크립트"""
from PIL import Image, ImageDraw, ImageFont
import os

# 테스트할 폰트 경로
fonts = {
    "한글": [
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/System/Library/Fonts/AppleGothic.ttf",
        "/Library/Fonts/AppleGothic.ttf",
        "/System/Library/Fonts/Supplemental/NanumGothicBold.ttf",
        "/System/Library/Fonts/Supplemental/NanumGothic.ttf",
        "/System/Library/Fonts/Supplemental/NanumBarunGothic.ttf",
        "/System/Library/Fonts/Supplemental/NanumBarunGothicBold.ttf",
    ],
    "영문": [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    ],
}

print("=" * 60)
print("폰트 존재 여부 및 렌더링 테스트")
print("=" * 60)

for lang, font_list in fonts.items():
    print(f"\n[{lang} 폰트]")
    test_text = "테스트 한글" if lang == "한글" else "Test English"

    for font_path in font_list:
        exists = os.path.exists(font_path)
        status = "✅ 존재" if exists else "❌ 없음"
        print(f"  {status}: {font_path}")

        if exists:
            try:
                font = ImageFont.truetype(font_path, 100)
                img = Image.new("RGB", (400, 200), (255, 255, 255))
                draw = ImageDraw.Draw(img)
                bbox = draw.textbbox((0, 0), test_text, font=font)
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]

                # 실제로 텍스트를 그려서 확인
                draw.text((0, 0), test_text, font=font, fill=(0, 0, 0))
                pixels = list(img.getdata())
                has_content = any(pixel != (255, 255, 255) for pixel in pixels)

                if has_content and width > 0 and height > 0:
                    print(f"    ✅ 렌더링 성공 (너비: {width}px, 높이: {height}px)")
                else:
                    print(
                        f"    ⚠️ 렌더링 실패 (너비: {width}px, 높이: {height}px, 픽셀: {has_content})"
                    )
            except Exception as e:
                print(f"    ❌ 로드 실패: {e}")

print("\n" + "=" * 60)
print("추가로 확인할 수 있는 폰트:")
print("=" * 60)
print("\n시스템 폰트 목록 확인:")
print("  fc-list :lang=ko 2>/dev/null | head -10")
print("\n또는 직접 폰트 파일 확인:")
print("  ls -la /System/Library/Fonts/Supplemental/ | grep -i gothic")
print("  ls -la /System/Library/Fonts/Supplemental/ | grep -i arial")

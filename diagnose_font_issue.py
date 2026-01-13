#!/usr/bin/env python3
"""폰트 깨짐 문제 진단 스크립트"""
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PIL import Image, ImageDraw  # noqa: E402
from src.generators.video.subtitle_renderer import SubtitleRenderer  # noqa: E402
from src.generators.video_constants import VideoConstants  # noqa: E402
import os  # noqa: E402

print("=" * 60)
print("폰트 깨짐 문제 진단")
print("=" * 60)

# SubtitleRenderer 인스턴스 생성
renderer = SubtitleRenderer()

# Hook 폰트 테스트
print("\n[1] Hook 폰트 로드 테스트")
print("-" * 60)

for language in ["ko", "en"]:
    print(f"\n{language.upper()} Hook 폰트:")
    font_path = renderer._get_font_path(language)
    print(f"  선택된 폰트 경로: {font_path}")

    if font_path:
        exists = os.path.exists(font_path)
        print(f"  파일 존재: {exists}")

        if exists:
            try:
                pil_font = renderer._get_pil_font(
                    font_path, VideoConstants.HOOK_TITLE_FONT_SIZE, language
                )
                print(f"  PIL 폰트 로드: {'✅ 성공' if pil_font else '❌ 실패'}")

                if pil_font:
                    # 실제 렌더링 테스트
                    test_text = (
                        "테스트 한글 갓생" if language == "ko" else "Test English Hook"
                    )
                    img = Image.new("RGB", (1080, 200), (255, 255, 255))
                    draw = ImageDraw.Draw(img)

                    # 텍스트 그리기
                    draw.text((0, 0), test_text, font=pil_font, fill=(0, 0, 0))

                    # 결과 확인
                    bbox = draw.textbbox((0, 0), test_text, font=pil_font)
                    width = bbox[2] - bbox[0]
                    height = bbox[3] - bbox[1]

                    # 픽셀 확인
                    pixels = list(img.getdata())
                    has_content = any(pixel != (255, 255, 255) for pixel in pixels)

                    print("  렌더링 테스트:")
                    print(f"    너비: {width}px, 높이: {height}px")
                    print(f"    픽셀 렌더링: {'✅ 성공' if has_content else '❌ 실패'}")

                    # 테스트 이미지 저장
                    test_output = f"test_font_{language}.png"
                    img.save(test_output)
                    print(f"    테스트 이미지 저장: {test_output}")

            except Exception as e:
                print(f"  ❌ 오류: {e}")
                import traceback

                traceback.print_exc()

print("\n" + "=" * 60)
print("다음 단계:")
print("=" * 60)
print("1. test_font_ko.png와 test_font_en.png 파일을 확인하세요")
print("2. 깨진 문자가 있다면 어떤 문자인지 알려주세요")
print("3. 실제 영상 생성 시 로그에서 다음을 확인하세요:")
print("   - '✅ 폰트 로드 성공' 메시지")
print("   - '⚠️ 폰트 렌더링 테스트 실패' 메시지")
print("   - '❌ 모든 한글 폰트 로드 실패' 메시지")
print("\n또는 직접 폰트 파일을 제공해주시면:")
print("  - 프로젝트 루트에 'fonts/' 폴더 생성")
print("  - .ttf 폰트 파일을 해당 폴더에 저장")
print("  - 폰트 경로를 알려주시면 코드에 추가하겠습니다")

"""
자막 렌더링 모듈
"""

import os
import re
import time
from typing import Optional, List
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import TextClip, ImageClip
from moviepy.video.fx.all import fadein, fadeout

from src.core.config import settings
from src.generators.video_constants import VideoConstants
from src.utils.logger import get_logger

# VideoConstants import 확인

logger = get_logger(__name__)


class SubtitleRenderer:
    """자막 생성 및 렌더링 클래스"""

    def __init__(self, openai_client=None):
        self.openai_client = openai_client
        self.use_moviepy = True  # MoviePy TextClip 사용 여부

    def create_subtitle_clip(
        self, text: str, duration: float, language: str = "ko"
    ) -> Optional[TextClip]:
        """자막 클립 생성"""
        try:
            subtitle_text = text
            subtitle_mode = settings.SUBTITLE_MODE
            use_keywords = subtitle_mode != "full_sentence"

            if use_keywords:
                key_words = self.extract_key_words(text, language=language)
                if key_words:
                    subtitle_text = key_words

            font_path = self._get_font_path(language)
            # 폰트 크기 30% 증가: 60 -> 78, 80 -> 104
            font_size = 78 if subtitle_mode == "full_sentence" else 104

            # Try ImageMagick TextClip first
            try:
                if font_path:
                    # 자막 색상: 노란색 (한국어, 영어 모두)
                    subtitle_color = "yellow"
                    txt_clip = self._create_imagemagick_subtitle(
                        subtitle_text,
                        duration,
                        font_path,
                        font_size,
                        color=subtitle_color,
                    )
                    if txt_clip:
                        return txt_clip
            except Exception as e:
                logger.debug(f"   ImageMagick TextClip 실패, PIL로 대체: {e}")

            # Fallback to PIL
            return self._create_pil_subtitle(
                subtitle_text,
                duration,
                font_path,
                font_size,
                language,
                use_keywords,
                text,
            )

        except Exception as e:
            logger.error(f"   ❌ 자막 생성 중 오류: {e}", exc_info=True)
            return None

    def extract_key_words(self, sentence: str, language: str = "ko") -> str:
        """문장에서 자막용 핵심 단어 추출"""
        try:
            if self.openai_client:
                if language == "en":
                    prompt = f"Extract 1-3 key words from this sentence for subtitle display. Only the most important words that capture the essence. Return only the words separated by spaces, no explanation:\n\n{sentence}"
                    system_prompt = "You are a subtitle keyword extractor. Extract only the most important 1-3 key words from sentences for subtitle display."
                else:
                    prompt = f"다음 문장에서 자막 표시용 핵심 단어 1-3개를 추출하세요. 가장 중요한 단어만 선택하세요. 단어만 공백으로 구분하여 반환하세요 (설명 없이):\n\n{sentence}"
                    system_prompt = "당신은 자막 키워드 추출 전문가입니다. 문장에서 자막 표시용 핵심 단어 1-3개만 추출하세요."

                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=30,
                    temperature=0.3,
                )
                key_words = response.choices[0].message.content.strip()
                key_words = re.sub(r"[^\w\s]", "", key_words)
                words = key_words.split()
                key_words = " ".join(words[:3])
                if key_words:
                    logger.debug(
                        f"   핵심 단어 추출: {sentence[:30]}... -> {key_words}"
                    )
                    return key_words
        except Exception as e:
            logger.debug(f"   핵심 단어 추출 실패, 기본 사용: {e}")

        # Fallback
        words = sentence.split()
        if language == "en":
            if len(words) <= 3:
                return sentence
            else:
                return " ".join([words[0], words[-1] if len(words) > 1 else ""])
        else:
            if len(words) <= 3:
                return sentence
            else:
                return " ".join(words[:2])

    def draw_text_on_image(
        self, image: Image.Image, text: str, language: str = "ko"
    ) -> Image.Image:
        """이미지에 텍스트 그리기"""
        base_font_size = VideoConstants.BASE_FONT_SIZE
        font = None
        font_path_used = None

        font_paths = self._get_font_paths(language)

        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, base_font_size)
                    font_path_used = font_path
                    break
            except BaseException:
                continue

        if font is None:
            font = self._get_default_font(language, base_font_size)
            font_path_used = "default"

        if image.mode != "RGB":
            image = image.convert("RGB")

        max_width = VideoConstants.SUBTITLE_MAX_WIDTH
        lines = self.wrap_text(text, font, max_width, base_font_size)

        # Adjust font size if too many lines
        if len(lines) > 3 and font_path_used and font_path_used != "default":
            for size in VideoConstants.FONT_SIZES:
                try:
                    font = ImageFont.truetype(font_path_used, size)
                    lines = self.wrap_text(text, font, max_width, size)
                    if len(lines) <= 4:
                        break
                except BaseException:
                    continue

        line_spacing = VideoConstants.LINE_SPACING
        draw = ImageDraw.Draw(image)
        line_heights = []
        line_widths = []

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_heights.append(bbox[3] - bbox[1])
            line_widths.append(bbox[2] - bbox[0])

        total_height = sum(line_heights) + (len(lines) - 1) * line_spacing
        # max_line_width = max(line_widths) if line_widths else 0

        # x = (VideoConstants.VIDEO_WIDTH - max_line_width) // 2
        y = (
            VideoConstants.VIDEO_HEIGHT
            - total_height
            - VideoConstants.SUBTITLE_BOTTOM_MARGIN
        )

        if image.mode != "RGB":
            image = image.convert("RGB")
        draw = ImageDraw.Draw(image)

        current_y = y
        for i, line in enumerate(lines):
            if not line.strip():
                continue

            line_bbox = draw.textbbox((0, 0), line, font=font)
            line_width = line_bbox[2] - line_bbox[0]
            line_x = (VideoConstants.VIDEO_WIDTH - line_width) // 2

            # Draw shadow
            draw.text((line_x + 4, current_y + 4), line, fill=(0, 0, 0), font=font)
            draw.text((line_x + 2, current_y + 2), line, fill=(50, 50, 50), font=font)
            # Draw main text
            draw.text((line_x, current_y), line, fill=(255, 255, 255), font=font)

            current_y += line_heights[i] + line_spacing

        return image

    def wrap_text(self, text: str, font, max_width: int, font_size: int) -> list:
        """텍스트를 여러 줄로 자동 분할"""
        words = text.split()
        lines = []
        current_line: List[str] = []

        temp_image = Image.new(
            "RGB", (VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT)
        )
        temp_draw = ImageDraw.Draw(temp_image)

        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = temp_draw.textbbox((0, 0), test_line, font=font)
            test_width = bbox[2] - bbox[0]

            if test_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        return lines if lines else [text]

    def _get_font_path(self, language: str) -> Optional[str]:
        """언어에 맞는 폰트 경로 반환 (.ttf 파일만)"""
        font_paths = self._get_font_paths(language)
        for path in font_paths:
            # .ttf 파일만 반환 (.ttc 파일은 제외)
            if os.path.exists(path) and path.endswith(".ttf"):
                return path
        return None

    def _get_font_paths(self, language: str) -> List[str]:
        """언어별 폰트 경로 목록 (.ttf 파일만 반환, .ttc 파일은 완전히 제외)"""
        from pathlib import Path

        # 프로젝트 루트의 fonts 폴더 경로
        project_root = Path(__file__).parent.parent.parent.parent
        fonts_dir = project_root / "fonts"

        # 프로젝트 fonts 폴더의 폰트를 최우선으로 사용
        project_fonts: List[str] = []
        if fonts_dir.exists():
            project_font_paths: List[Path] = []
            if language == "en":
                # 영문 폰트 우선순위
                project_font_paths = [
                    fonts_dir / "Roboto-Bold.ttf",
                    fonts_dir / "Roboto-Regular.ttf",
                    fonts_dir / "Arial-Bold.ttf",
                    fonts_dir / "Arial Bold.ttf",
                    fonts_dir / "Arial.ttf",
                ]
            else:
                # 한글 폰트 우선순위 (나눔고딕만 사용)
                project_font_paths = [
                    fonts_dir / "NanumGothicBold.ttf",
                    fonts_dir / "NanumGothic.ttf",
                    # 나눔고딕이 없을 경우에만 다른 폰트 시도
                    fonts_dir / "NotoSansKR-Bold.ttf",
                    fonts_dir / "NotoSansKR-Regular.ttf",
                ]

            # 존재하는 폰트만 추가
            project_fonts = [str(f) for f in project_font_paths if f.exists()]

        # 시스템 폰트 (폴백)
        if language == "en":
            system_fonts = [
                # .ttf 파일만 사용 (PIL 호환성 보장)
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/Library/Fonts/Arial.ttf",
                "/System/Library/Fonts/Supplemental/Arial Black.ttf",
            ]
        else:
            system_fonts = [
                # .ttf 파일만 사용 (PIL 호환성 보장)
                # AppleGothic을 우선 사용 (시스템에 항상 존재하고 한글 지원 확인됨)
                "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
                "/System/Library/Fonts/AppleGothic.ttf",
                "/Library/Fonts/AppleGothic.ttf",
                # NanumGothic은 선택적 (일부 시스템에 없을 수 있음)
                "/System/Library/Fonts/Supplemental/NanumGothicBold.ttf",
                "/System/Library/Fonts/Supplemental/NanumGothic.ttf",
            ]

        # 프로젝트 폰트를 먼저, 그 다음 시스템 폰트
        return project_fonts + system_fonts

    def _get_default_font(self, language: str, font_size: int):
        """기본 폰트 반환 (.ttf 파일만 사용, 프로젝트 fonts 폴더 우선)"""
        from pathlib import Path

        # 프로젝트 루트의 fonts 폴더 경로
        project_root = Path(__file__).parent.parent.parent.parent
        fonts_dir = project_root / "fonts"

        # 프로젝트 fonts 폴더의 폰트를 최우선으로
        if fonts_dir.exists():
            if language == "en":
                project_fonts = [
                    fonts_dir / "Roboto-Bold.ttf",
                    fonts_dir / "Roboto-Regular.ttf",
                    fonts_dir / "Arial-Bold.ttf",
                    fonts_dir / "Arial Bold.ttf",
                    fonts_dir / "Arial.ttf",
                ]
            else:
                project_fonts = [
                    fonts_dir / "NanumGothicBold.ttf",
                    fonts_dir / "NanumGothic.ttf",
                    fonts_dir / "NotoSansKR-Bold.ttf",
                    fonts_dir / "NotoSansKR-Regular.ttf",
                ]

            for font_path in project_fonts:
                try:
                    if font_path.exists() and font_path.suffix == ".ttf":
                        return ImageFont.truetype(str(font_path), font_size)
                except BaseException:
                    continue

        # 시스템 폰트 (폴백)
        font_paths: List[str]
        if language == "en":
            font_paths = [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/Library/Fonts/Arial.ttf",
            ]
        else:
            font_paths = [
                # AppleGothic을 우선 사용
                "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
                "/System/Library/Fonts/AppleGothic.ttf",
                "/Library/Fonts/AppleGothic.ttf",
                # NanumGothic은 선택적
                "/System/Library/Fonts/Supplemental/NanumGothicBold.ttf",
                "/System/Library/Fonts/Supplemental/NanumGothic.ttf",
            ]

        for font_path_str in font_paths:
            try:
                if os.path.exists(font_path_str) and font_path_str.endswith(".ttf"):
                    return ImageFont.truetype(font_path_str, font_size)
            except BaseException:
                continue
        return ImageFont.load_default()

    def _create_imagemagick_subtitle(
        self,
        text: str,
        duration: float,
        font_path: str,
        font_size: int,
        color: str = "white",
    ) -> Optional[TextClip]:
        """ImageMagick을 사용한 자막 생성"""
        try:
            txt_clip = TextClip(
                text,
                fontsize=font_size,
                font=font_path,
                color=color,  # 강렬한 색상 사용
                stroke_color="black",
                stroke_width=5,  # 더 강한 테두리
                method="caption",
                size=(940, None),  # 좌우 30픽셀씩 줄임 (1000 -> 940)
                align="center",
            )
            txt_clip = txt_clip.set_start(0)
            if self.use_moviepy and txt_clip and isinstance(txt_clip, TextClip):
                # MoviePy TextClip 위치 설정
                try:
                    # frame = txt_clip.get_frame(0)
                    # clip_height = frame.shape[0]
                    # 성공 공식: 자막을 화면 중앙/하단 배치 (기본값: 하단)
                    position = VideoConstants.SUBTITLE_PREFERRED_POSITION
                    if position == "top":
                        raised_y = VideoConstants.SUBTITLE_TOP_MARGIN
                        txt_clip = txt_clip.set_position(("center", raised_y))
                    elif position == "bottom":
                        # 하단 배치: 화면 높이에서 하단 여백을 뺀 위치
                        bottom_y = (
                            VideoConstants.VIDEO_HEIGHT
                            - VideoConstants.SUBTITLE_BOTTOM_MARGIN
                        )
                        txt_clip = txt_clip.set_position(("center", bottom_y))
                    else:  # center (기본값)
                        txt_clip = txt_clip.set_position(("center", "center"))
                except Exception:
                    # 폴백: 중앙 배치
                    txt_clip = txt_clip.set_position(("center", "center"))

            txt_clip = txt_clip.set_start(0)
            if abs(txt_clip.duration - duration) > 0.01:
                txt_clip = txt_clip.set_duration(duration)

            fade_duration = min(0.3, duration * 0.1)
            if duration > fade_duration * 2:
                txt_clip = txt_clip.fx(fadein, fade_duration).fx(fadeout, fade_duration)
                txt_clip = txt_clip.set_duration(duration)

            logger.debug(
                f"   ✅ ImageMagick 자막 생성 성공: duration={txt_clip.duration:.2f}초, start={txt_clip.start:.2f}초 (목표: {duration:.2f}초)"
            )
            return txt_clip
        except Exception as e:
            logger.debug(f"   ImageMagick 자막 생성 실패: {e}")
            return None

    def _create_pil_subtitle(
        self,
        subtitle_text: str,
        duration: float,
        font_path: Optional[str],
        font_size: int,
        language: str,
        use_keywords: bool,
        original_text: str,
    ) -> Optional[ImageClip]:
        """PIL을 사용한 자막 생성"""
        try:
            subtitle_height = 300
            subtitle_img = Image.new("RGBA", (1080, subtitle_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(subtitle_img)

            pil_font = self._get_pil_font(font_path, font_size, language)

            # Wrap text
            max_width = 940  # 좌우 30픽셀씩 줄임 (1000 -> 940)
            words = subtitle_text.split()
            lines = []
            current_line: List[str] = []

            for word in words:
                test_line = " ".join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=pil_font)
                if bbox[2] - bbox[0] <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(" ".join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(" ".join(current_line))

            if not lines:
                lines = [subtitle_text if not use_keywords else original_text]

            # Draw text
            y_offset = 20
            for line in lines[:3]:
                if line.strip():
                    bbox = draw.textbbox((0, 0), line, font=pil_font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    x_pos = (1080 - text_width) // 2

                    draw = ImageDraw.Draw(subtitle_img)
                    # Draw shadow
                    shadow_offset = 4
                    shadow_blur = 2
                    for dx in range(-shadow_blur, shadow_blur + 1):
                        for dy in range(-shadow_blur, shadow_blur + 1):
                            if dx != 0 or dy != 0:
                                draw.text(
                                    (
                                        x_pos + shadow_offset + dx,
                                        y_offset + shadow_offset + dy,
                                    ),
                                    line,
                                    fill=(0, 0, 0, 200),
                                    font=pil_font,
                                )

                    # Draw main text (눈에 띄는 색상: 밝은 노란색)
                    text_color = (255, 255, 0)  # 노란색 (한국어, 영어 모두)
                    draw.text((x_pos, y_offset), line, fill=text_color, font=pil_font)
                    y_offset += text_height + 10

            # Save and create clip
            temp_subtitle_path = os.path.join(
                settings.TEMP_DIR, f"subtitle_{int(time.time()*1000)}.png"
            )
            subtitle_img.save(temp_subtitle_path, "PNG")

            txt_clip = ImageClip(temp_subtitle_path)
            txt_clip = txt_clip.set_duration(duration)
            # 자막 위치 설정 (기본값: 하단)
            position = VideoConstants.SUBTITLE_PREFERRED_POSITION
            if position == "bottom":
                bottom_y = (
                    VideoConstants.VIDEO_HEIGHT - VideoConstants.SUBTITLE_BOTTOM_MARGIN
                )
                txt_clip = txt_clip.set_position(("center", bottom_y))
            elif position == "top":
                txt_clip = txt_clip.set_position(
                    ("center", VideoConstants.SUBTITLE_TOP_MARGIN)
                )
            else:  # center
                txt_clip = txt_clip.set_position(("center", "center"))
            txt_clip = txt_clip.set_start(0)

            fade_duration = min(0.3, duration * 0.1)
            if duration > fade_duration * 2:
                txt_clip = txt_clip.fx(fadein, fade_duration).fx(fadeout, fade_duration)
                txt_clip = txt_clip.set_duration(duration)

            logger.debug(
                f"   ✅ PIL 자막 생성 성공: 높이={subtitle_height}px, duration={txt_clip.duration:.2f}초, start={txt_clip.start:.2f}초 (목표: {duration:.2f}초)"
            )
            return txt_clip
        except Exception as e:
            logger.warning(f"   ❌ PIL 자막 생성 실패: {e}")
            return None

    def _get_pil_font(self, font_path: Optional[str], font_size: int, language: str):
        """PIL 폰트 반환 (.ttf 파일만 사용, .ttc 파일은 완전히 제외, 한글 폰트 렌더링 테스트 포함)"""
        pil_font = None
        last_error = None

        def test_korean_rendering(
            font_obj: ImageFont.FreeTypeFont, test_text: str = None
        ) -> bool:
            """한글 폰트가 실제로 한글을 렌더링할 수 있는지 테스트"""
            if language != "ko":
                return True  # 한글이 아니면 테스트 불필요

            # 테스트할 텍스트: 기본 테스트 + 실제 사용되는 다양한 한글 문자
            if test_text is None:
                test_text = "테스트활용법꿀팁갓생칼퇴야근"

            try:
                test_img = Image.new("RGB", (400, 100), (255, 255, 255))
                test_draw = ImageDraw.Draw(test_img)

                # 각 문자를 개별적으로 테스트
                for char in test_text:
                    if "\uac00" <= char <= "\ud7a3":  # 한글 유니코드 범위
                        try:
                            bbox = test_draw.textbbox((0, 0), char, font=font_obj)
                            width = bbox[2] - bbox[0]
                            height = bbox[3] - bbox[1]

                            # 너비나 높이가 0이면 렌더링 실패
                            if width == 0 or height == 0:
                                logger.debug(
                                    f"   ⚠️ 한글 문자 '{char}' 렌더링 실패 (크기: 0)"
                                )
                                return False

                            # 실제로 텍스트를 그려서 확인
                            test_draw.text((0, 0), char, font=font_obj, fill=(0, 0, 0))
                            # 픽셀을 확인하여 실제로 그려졌는지 검증
                            pixels = list(test_img.getdata())
                            # 검은색 픽셀이 하나라도 있으면 렌더링 성공
                            has_black = any(
                                pixel != (255, 255, 255) for pixel in pixels
                            )
                            if not has_black:
                                logger.debug(
                                    f"   ⚠️ 한글 문자 '{char}' 렌더링 실패 (픽셀 없음)"
                                )
                                return False

                            # 다음 문자 테스트를 위해 이미지 초기화
                            test_img = Image.new("RGB", (400, 100), (255, 255, 255))
                            test_draw = ImageDraw.Draw(test_img)
                        except Exception as e:
                            logger.debug(
                                f"   ⚠️ 한글 문자 '{char}' 렌더링 테스트 중 오류: {e}"
                            )
                            return False

                # 전체 텍스트도 테스트
                test_img = Image.new("RGB", (400, 100), (255, 255, 255))
                test_draw = ImageDraw.Draw(test_img)
                bbox = test_draw.textbbox((0, 0), test_text, font=font_obj)
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]

                if width == 0 or height == 0:
                    return False

                test_draw.text((0, 0), test_text, font=font_obj, fill=(0, 0, 0))
                pixels = list(test_img.getdata())
                has_black = any(pixel != (255, 255, 255) for pixel in pixels)
                return has_black
            except Exception as e:
                logger.debug(f"   ⚠️ 한글 렌더링 테스트 실패: {e}")
                return False

        # 먼저 제공된 font_path 시도 (.ttf 파일만)
        # 단, font_path가 None이면 바로 폴백으로 진행
        if font_path and os.path.exists(font_path):
            if font_path.endswith(".ttc"):
                logger.debug(f"   ⚠️ .ttc 파일은 건너뜀: {font_path}")
            else:
                try:
                    test_font = ImageFont.truetype(font_path, font_size)
                    # 한글 폰트인 경우 렌더링 테스트
                    if test_korean_rendering(test_font, None):
                        pil_font = test_font
                        logger.info(
                            f"   ✅ 폰트 로드 및 렌더링 테스트 성공: {font_path} (크기: {font_size}px)"
                        )
                    else:
                        logger.warning(
                            f"   ⚠️ 폰트는 로드되었지만 렌더링 테스트 실패: {font_path}, 폴백으로 진행"
                        )
                        pil_font = None  # 폴백으로 진행
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"   ⚠️ 폰트 로드 실패: {font_path} - {e}, 폴백으로 진행"
                    )

        # 폴백: _get_font_paths에서 제공된 경로들을 순차적으로 시도
        if pil_font is None:
            font_paths = self._get_font_paths(language)
            for path in font_paths:
                if os.path.exists(path) and path.endswith(".ttf"):
                    try:
                        test_font = ImageFont.truetype(path, font_size)
                        # 한글 폰트인 경우 렌더링 테스트
                        if test_korean_rendering(test_font, None):
                            pil_font = test_font
                            logger.info(
                                f"   ✅ 폰트 로드 및 렌더링 테스트 성공 (폴백): {path} (크기: {font_size}px)"
                            )
                            break
                        else:
                            logger.warning(
                                f"   ⚠️ 폰트는 로드되었지만 렌더링 테스트 실패: {path}, 다음 폰트 시도"
                            )
                    except Exception as e:
                        last_error = e
                        logger.debug(f"   ⚠️ 폰트 로드 실패: {path} - {e}")
                        continue

        # 한글 폰트가 여전히 없으면 시스템 폰트에서 한글 지원 폰트 찾기
        if pil_font is None and language == "ko":
            logger.warning(
                "   ⚠️ 기본 폰트 경로에서 한글 폰트를 찾지 못함, 시스템 폰트 검색 시도"
            )
            system_font_paths = [
                "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
                "/System/Library/Fonts/AppleGothic.ttf",
                "/Library/Fonts/AppleGothic.ttf",
            ]
            for path in system_font_paths:
                if os.path.exists(path):
                    try:
                        test_font = ImageFont.truetype(path, font_size)
                        if test_korean_rendering(test_font, None):
                            pil_font = test_font
                            logger.info(
                                f"   ✅ 시스템 폰트에서 한글 폰트 발견: {path} (크기: {font_size}px)"
                            )
                            break
                    except Exception as e:
                        logger.debug(f"   ⚠️ 시스템 폰트 로드 실패: {path} - {e}")
                        continue

        if pil_font is None:
            logger.error(
                f"   ❌ 모든 한글 폰트 로드 실패, 기본 폰트 사용 (한글이 사각형으로 표시될 수 있음) (마지막 에러: {last_error})"
            )
            pil_font = ImageFont.load_default()

        return pil_font

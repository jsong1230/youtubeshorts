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
                    txt_clip = self._create_imagemagick_subtitle(
                        subtitle_text, duration, font_path, font_size
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
        """언어에 맞는 폰트 경로 반환"""
        font_paths = self._get_font_paths(language)
        for path in font_paths:
            if os.path.exists(path):
                return path
        return None

    def _get_font_paths(self, language: str) -> list:
        """언어별 폰트 경로 목록"""
        if language == "en":
            return [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/System/Library/Fonts/Supplemental/Arial Italic.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Supplemental/Helvetica.ttc",
                "/Library/Fonts/Arial.ttf",
            ]
        else:
            return [
                "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
                "/System/Library/Fonts/AppleGothic.ttf",
                "/System/Library/Fonts/Supplemental/NanumGothic.ttf",
                "/Library/Fonts/AppleGothic.ttf",
            ]

    def _get_default_font(self, language: str, font_size: int):
        """기본 폰트 반환"""
        if language == "en":
            try:
                return ImageFont.truetype(
                    "/System/Library/Fonts/Supplemental/Arial Bold.ttf", font_size
                )
            except BaseException:
                return ImageFont.load_default()
        else:
            try:
                return ImageFont.truetype(
                    "/System/Library/Fonts/Supplemental/AppleGothic.ttf", font_size
                )
            except BaseException:
                return ImageFont.load_default()

    def _create_imagemagick_subtitle(
        self, text: str, duration: float, font_path: str, font_size: int
    ) -> Optional[TextClip]:
        """ImageMagick을 사용한 자막 생성"""
        try:
            txt_clip = TextClip(
                text,
                fontsize=font_size,
                font=font_path,
                color="white",
                stroke_color="black",
                stroke_width=3,
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
                    # 성공 공식: 자막을 화면 중앙/상단 배치 (기본값: 중앙)
                    position = VideoConstants.SUBTITLE_PREFERRED_POSITION
                    if position == "top":
                        raised_y = VideoConstants.SUBTITLE_TOP_MARGIN
                        txt_clip = txt_clip.set_position(("center", raised_y))
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

                    # Draw main text
                    draw.text(
                        (x_pos, y_offset), line, fill=(255, 255, 255), font=pil_font
                    )
                    y_offset += text_height + 10

            # Save and create clip
            temp_subtitle_path = os.path.join(
                settings.TEMP_DIR, f"subtitle_{int(time.time()*1000)}.png"
            )
            subtitle_img.save(temp_subtitle_path, "PNG")

            txt_clip = ImageClip(temp_subtitle_path)
            txt_clip = txt_clip.set_duration(duration)
            txt_clip = txt_clip.set_position(("center", 250))
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
        """PIL 폰트 반환"""
        pil_font = None

        if font_path and os.path.exists(font_path):
            try:
                pil_font = ImageFont.truetype(font_path, font_size)
            except BaseException:
                pass

        if pil_font is None:
            font_paths = self._get_font_paths(language)
            for path in font_paths[:3]:  # Try first 3 paths
                if os.path.exists(path):
                    try:
                        pil_font = ImageFont.truetype(path, font_size)
                        break
                    except BaseException:
                        continue

        if pil_font is None:
            pil_font = ImageFont.load_default()

        return pil_font

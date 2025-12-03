"""
이미지 생성 및 처리 모듈 (썸네일, DALL-E 등)
"""
import os
import time
import datetime
import requests
from typing import Optional, Tuple
from io import BytesIO
from PIL import Image
import numpy as np
from moviepy.editor import VideoFileClip, ImageClip, concatenate_videoclips

from src.core.config import settings
from .video_constants import VideoConstants
from src.utils.retry_decorator import retry
from src.utils.logger import get_logger

logger = get_logger(__name__)

class ImageGenerator:
    """이미지 생성 및 관리 클래스"""
    
    def __init__(self, openai_client=None):
        self.openai_client = openai_client

    @retry(max_retries=3, base_delay=1, exceptions=(requests.RequestException, ConnectionError, TimeoutError))
    def _http_get_with_retry(self, url: str, **kwargs) -> requests.Response:
        """HTTP GET request with automatic retry on transient failures."""
        timeout = kwargs.pop('timeout', 10)
        response = requests.get(url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response

    @retry(max_retries=3, base_delay=2)
    def _api_call_with_retry(self, func, *args, **kwargs):
        """API 호출 재시도 데코레이터 (메서드 내부용)"""
        return func(*args, **kwargs)

    def prepare_thumbnail_canvas(
        self,
        thumbnail_path: str,
        target_size: Tuple[int, int]
    ) -> Optional[str]:
        """썸네일 이미지를 영상 해상도에 맞춰 중앙 정렬한 캔버스 생성."""
        if not os.path.exists(thumbnail_path):
            return None
        try:
            img = Image.open(thumbnail_path).convert('RGB')
            target_w, target_h = target_size
            target_ratio = target_w / target_h
            img_ratio = img.width / img.height if img.height else target_ratio

            if img_ratio > target_ratio:
                new_width = target_w
                new_height = int(target_w / img_ratio)
            else:
                new_height = target_h
                new_width = int(target_h * img_ratio)

            resample_filter = Image.Resampling.LANCZOS if hasattr(
                Image, "Resampling") else Image.LANCZOS
            resized = img.resize((new_width, new_height), resample_filter)

            canvas = Image.new('RGB', (target_w, target_h), (0, 0, 0))
            offset = (
                (target_w - new_width) // 2,
                (target_h - new_height) // 2)
            canvas.paste(resized, offset)

            temp_path = os.path.join(
                settings.TEMP_DIR,
                f"thumb_canvas_{int(time.time()*1000)}.jpg")
            canvas.save(temp_path, 'JPEG')
            return temp_path
        except Exception as e:
            logger.warning(f"⚠️ 썸네일 캔버스 생성 실패: {e}")
            return None

    def embed_thumbnail_frame(
        self,
        video_path: str,
        thumbnail_path: str,
        duration: float = 0.6
    ) -> str:
        """생성된 썸네일을 영상의 첫 프레임으로 삽입."""
        if not video_path or not os.path.exists(video_path):
            logger.warning("⚠️ 영상 파일을 찾을 수 없어 썸네일 프레임을 삽입하지 않습니다.")
            return video_path
        if not thumbnail_path or not os.path.exists(thumbnail_path):
            logger.warning("⚠️ 썸네일 파일이 없어 썸네일 프레임을 삽입하지 않습니다.")
            return video_path

        intro_clip = None
        video_clip = None
        combined_clip = None
        canvas_path = None
        try:
            video_clip = VideoFileClip(video_path)
            fps = video_clip.fps or 30
            target_size = video_clip.size

            canvas_path = self.prepare_thumbnail_canvas(
                thumbnail_path, target_size)
            if not canvas_path:
                return video_path

            intro_clip = ImageClip(canvas_path).set_duration(
                duration).set_fps(fps).resize(target_size)
            combined_clip = concatenate_videoclips(
                [intro_clip, video_clip], method="compose")

            temp_output = os.path.join(
                settings.TEMP_DIR,
                f"with_thumb_{int(time.time()*1000)}.mp4")
            temp_audio = os.path.join(
                settings.TEMP_DIR,
                f"with_thumb_audio_{int(time.time()*1000)}.m4a")
            combined_clip.write_videofile(
                temp_output,
                fps=fps,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=temp_audio,
                remove_temp=True,
                logger=None
            )

            combined_clip.close()
            intro_clip.close()
            video_clip.close()

            os.replace(temp_output, video_path)
            logger.info("✅ 썸네일 이미지를 영상 첫 프레임으로 삽입했습니다.")
        except Exception as e:
            logger.warning(f"⚠️ 썸네일 프레임 삽입 실패: {e}")
        finally:
            for clip in (combined_clip, intro_clip, video_clip):
                try:
                    if clip:
                        clip.close()
                except Exception:
                    pass
            if canvas_path and os.path.exists(canvas_path):
                try:
                    os.remove(canvas_path)
                except OSError:
                    pass
        return video_path

    def _generate_dalle3_thumbnail(
        self,
        title: str,
        topic: str = None,
        script: list = None,
        language: str = 'ko'
    ) -> Optional[Image.Image]:
        """
        DALL-E 3로 썸네일 이미지 생성

        Args:
            title: 영상 제목
            topic: 영상 주제 (선택)
            script: 영상 스크립트 (선택)
            language: 언어 코드 ('ko' 또는 'en', 기본값: 'ko')

        Returns:
            PIL Image 객체 또는 None (실패 시)
        """
        if not self.openai_client:
            return None

        try:
            # 주제 기반 프롬프트 생성
            # 주제 및 제목 분석하여 스타일 결정
            style_prompt = ""
            lower_topic = (topic or "").lower()
            lower_title = title.lower()
            
            if any(k in lower_topic or k in lower_title for k in ['money', 'finance', 'rich', 'wealth', 'invest', '돈', '부자', '투자', '금융']):
                style_prompt = "Style: Hyper-realistic 3D render, luxury aesthetic, gold and neon green accents, rising graphs, high contrast, dramatic lighting. Visuals of wealth, success, currency, or gold."
            elif any(k in lower_topic or k in lower_title for k in ['motivation', 'mindset', 'life', 'success', 'dream', '동기부여', '성공', '인생', '꿈']):
                style_prompt = "Style: Cinematic lighting, dramatic silhouette against a sunrise or sunset, emotional atmosphere, epic scale, looking up at a mountain or city, inspiring and powerful."
            elif any(k in lower_topic or k in lower_title for k in ['productivity', 'habit', 'study', 'focus', 'time', '생산성', '습관', '공부', '시간']):
                style_prompt = "Style: Clean minimalist setup, futuristic blue and white lighting, glowing brain or clock elements, organized workspace, sharp focus, high-tech feel."
            else:
                style_prompt = "Style: High contrast, vibrant colors, 4k resolution, unreal engine 5 render style, highly detailed, eye-catching, dramatic composition."

            # 주제 기반 프롬프트 생성 (영어/한국어 공통적으로 영어 프롬프트 사용 권장 - DALL-E 3가 영어를 더 잘 이해함)
            # 하지만 한국어 설정이므로 한국어 뉘앙스를 살리기 위해 혼용하거나 영어로 번역하는 것이 좋음
            # 여기서는 프롬프트 구조를 강화하여 영어로 작성 (DALL-E 3 최적화)
            
            prompt = f"A viral YouTube Shorts thumbnail image for a video titled: '{title}'."
            if topic:
                prompt += f" The video is about: {topic}."
            if script and len(script) > 0:
                prompt += f" Key scene context: {script[0][:100]}."
            
            prompt += f"\n\n{style_prompt}"
            prompt += "\n\nIMPORTANT CONSTRAINTS:"
            prompt += "\n- Vertical format (9:16 aspect ratio)"
            prompt += "\n- Central composition, close-up or medium shot"
            prompt += "\n- ABSOLUTELY NO TEXT, NO LETTERS, NO NUMBERS, NO WATERMARKS in the image. The image must be text-free."
            prompt += "\n- Make it emotionally engaging and click-worthy."

            logger.info(f"🎨 DALL-E 3로 썸네일 이미지 생성 중...")
            logger.debug(f"   프롬프트: {prompt[:100]}...")

            # DALL-E 3 API 호출 (with retry)
            response = self._api_call_with_retry(
                self.openai_client.images.generate,
                model="dall-e-3",
                prompt=prompt,
                size="1024x1792",  # 9:16 비율 (YouTube Shorts)
                quality="standard",
                n=1,
            )

            # 생성된 이미지 URL 가져오기
            image_url = response.data[0].url

            # 이미지 다운로드 (with retry)
            img_response = self._http_get_with_retry(image_url)
            
            # PIL Image로 변환
            img = Image.open(BytesIO(img_response.content))
            img = img.convert('RGB')

            # 1080x1920으로 리사이즈
            img = img.resize((1080, 1920), Image.Resampling.LANCZOS)

            logger.info(f"✅ DALL-E 3 썸네일 이미지 생성 완료")
            return img

        except Exception as e:
            logger.warning(f"⚠️ DALL-E 3 썸네일 생성 실패: {e}")
            # import traceback
            # traceback.print_exc()
            return None

    def generate_thumbnail(
        self,
        video_path: str,
        title: str,
        topic: str = None,
        script: list = None,
        language: str = 'ko'
    ) -> str:
        """
        매력적인 썸네일 이미지 생성
        
        Args:
            video_path: 영상 파일 경로
            title: 영상 제목
            topic: 영상 주제 (선택)
            script: 영상 스크립트 (선택, 핵심 내용 추출용)
            language: 언어 코드 ('ko' 또는 'en', 기본값: 'ko')
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        thumbnail_path = os.path.join(
            settings.THUMBNAIL_OUTPUT_DIR,
            f"thumb_{timestamp}.jpg")

        # DALL-E 3로 썸네일 이미지 생성 시도 (OpenAI API 사용)
        dalle_img = self._generate_dalle3_thumbnail(
            title, topic, script, language=language)

        if dalle_img:
            # DALL-E 3로 생성된 이미지 사용
            img = dalle_img
            img.save(thumbnail_path, 'JPEG', quality=95)
            logger.info(f"✅ 썸네일 저장 완료: {thumbnail_path}")
            return thumbnail_path
        else:
            # DALL-E 3 실패 시 기존 방식 (영상 프레임에서 추출)
            logger.info(f"📹 영상 프레임에서 썸네일 추출 중...")
            try:
                # 영상에서 여러 프레임 중 가장 좋은 프레임 선택 (중간 부분)
                # 자막이 없는 원본 배경을 사용하기 위해 영상에서 프레임 추출 후 자막 영역 제거
                video = VideoFileClip(video_path)
                duration = video.duration
                # 영상의 중간 지점에서 프레임 추출 (일반적으로 가장 매력적인 부분)
                frame_time = duration * VideoConstants.THUMBNAIL_FRAME_RATIO
                frame = video.get_frame(frame_time)
                
                img = Image.fromarray(frame)
                img.save(thumbnail_path, 'JPEG', quality=95)
                
                video.close()
                logger.info(f"✅ 영상 프레임 썸네일 저장 완료: {thumbnail_path}")
                return thumbnail_path
            except Exception as e:
                logger.warning(f"⚠️ 영상 프레임 썸네일 추출 실패: {e}")
                return None

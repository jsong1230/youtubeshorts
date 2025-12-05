"""
오디오 생성 및 처리 모듈 (TTS, 배경음악)
"""

import os
import random
import time
import requests
from typing import Optional, Any
from moviepy.editor import AudioFileClip, CompositeAudioClip, concatenate_audioclips
from moviepy.audio.fx.all import audio_fadein, audio_fadeout

# moviepy version compatibility: some versions use volumex as method, some as fx
# We will use the method if available, or fx

try:
    from gtts import gTTS

    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

from src.core.config import settings
from .video_constants import VideoConstants
from .content_type import ContentType
from src.utils.retry_decorator import retry
from src.utils.logger import get_logger

logger = get_logger(__name__)

# TTS Engine Import
try:
    from src.pipeline.tts_engine import TTSEngine, TTSProvider

    NEW_TTS_AVAILABLE = True
except ImportError:
    NEW_TTS_AVAILABLE = False


class AudioGenerator:
    """오디오 생성 및 관리 클래스"""

    def __init__(
        self, tts_provider: Optional[str] = None, tts_engine: Optional[Any] = None
    ) -> None:
        if tts_engine:
            self.tts_engine = tts_engine
            logger.info(f"✅ TTS 엔진 주입됨: {self.tts_engine.get_provider().value}")
        else:
            self.tts_engine = None
            if NEW_TTS_AVAILABLE:
                try:
                    # tts_provider가 None이면 config에서 읽거나 자동 선택
                    provider_to_use: Optional[TTSProvider] = None
                    if tts_provider is None:
                        tts_provider_str = settings.TTS_PROVIDER
                        if tts_provider_str:
                            provider_to_use = TTSProvider(tts_provider_str.lower())
                    else:
                        # tts_provider가 str이면 TTSProvider로 변환
                        if isinstance(tts_provider, str):
                            provider_to_use = TTSProvider(tts_provider.lower())
                        else:
                            provider_to_use = tts_provider

                    self.tts_engine = TTSEngine(provider=provider_to_use)
                    logger.info(
                        f"✅ TTS 엔진 초기화: {self.tts_engine.get_provider().value}"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ TTS 엔진 초기화 실패: {e}")
                    logger.info("   기본 gTTS를 사용합니다.")
                    self.tts_engine = None
            else:
                self.tts_engine = None

    def generate_audio(
        self, text: str, index: int, content_type: str = None, language: str = "ko"
    ) -> Optional[str]:
        """TTS로 음성 생성 (콘텐츠 타입별 voice/speed 최적화)"""
        audio_path = os.path.join(settings.TEMP_DIR, f"audio_{index}.mp3")

        # 언어 코드 설정
        lang_code = "en" if language == "en" else "ko"

        # 새로운 TTS 엔진 사용 (우선, 콘텐츠 타입별 최적화)
        if self.tts_engine:
            try:
                if self.tts_engine.generate(
                    text, audio_path, lang=lang_code, content_type=content_type
                ):
                    return audio_path
                else:
                    logger.warning("⚠️ TTS 엔진 음성 생성 실패, 기본 gTTS 시도")
            except Exception as e:
                logger.warning(f"⚠️ TTS 엔진 오류: {e}, 기본 gTTS 시도")

        # 기본 gTTS 사용 (폴백)
        if TTS_AVAILABLE:
            try:
                tts = gTTS(text=text, lang=lang_code, slow=False)
                tts.save(audio_path)
                return audio_path
            except Exception as e:
                logger.warning(f"⚠️ gTTS 음성 생성 실패 ({text[:20]}...): {e}")
                return None
        else:
            logger.warning("⚠️ 사용 가능한 TTS 엔진이 없습니다.")
            return None

    def select_music_category_for_content_type(self, content_type: ContentType) -> str:
        """
        콘텐츠 타입에 맞는 음악 카테고리 선택
        """
        # 콘텐츠 타입별 음악 카테고리 매핑
        music_categories = {
            ContentType.HOOK: [
                "energetic",
                "upbeat",
                "motivational",
            ],  # 에너지 넘치는, 업비트
            ContentType.QUOTE: [
                "calm",
                "peaceful",
                "inspirational",
            ],  # 차분한, 평화로운
            ContentType.STORY: [
                "emotional",
                "cinematic",
                "dramatic",
            ],  # 감성적인, 영화적
            ContentType.FACT: ["corporate", "modern", "tech"],  # 기업적, 모던
            ContentType.SHORT_STORY: [
                "ambient",
                "soft",
                "gentle",
            ],  # 앰비언트, 부드러운
            ContentType.MEDITATION: ["meditation", "zen", "calm"],  # 명상, 차분한
            ContentType.BREATHING: ["ambient", "peaceful", "nature"],  # 자연, 평화로운
            ContentType.AUTO: ["background", "ambient", "soft"],  # 기본 배경 음악
        }

        categories = music_categories.get(content_type, ["background", "ambient"])
        return random.choice(categories)

    @retry(
        max_retries=3,
        base_delay=1,
        exceptions=(requests.RequestException, ConnectionError, TimeoutError),
    )
    def _http_get_with_retry(self, url: str, **kwargs) -> requests.Response:
        """HTTP GET request with automatic retry on transient failures."""
        timeout = kwargs.pop("timeout", 10)
        response = requests.get(url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response

    def download_background_music(
        self, content_type: ContentType, duration: float, topic: str = None
    ) -> Optional[str]:
        """
        배경 음악 다운로드 (무료 음악 라이브러리 사용)
        """
        if not settings.USE_BACKGROUND_MUSIC:
            return None

        try:
            # 콘텐츠 타입에 맞는 음악 카테고리 선택
            music_category = self.select_music_category_for_content_type(content_type)
            logger.debug(
                f"🎵 배경 음악 선택: {music_category} (콘텐츠 타입: {content_type.value})"
            )

            # 방법 1: 로컬 음악 라이브러리 확인 (우선)
            # BASE_DIR을 config에서 가져오거나 상대 경로로 계산해야 함.
            # 여기서는 config.BASE_DIR이 없으므로 상대 경로 사용
            base_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            music_library_dir = os.path.join(base_dir, "data", "music")

            if os.path.exists(music_library_dir):
                # 카테고리별 음악 파일 찾기
                music_files = []
                for ext in [".mp3", ".wav", ".m4a", ".ogg"]:
                    # 카테고리 이름이 포함된 파일 찾기
                    for file in os.listdir(music_library_dir):
                        if (
                            file.endswith(ext)
                            and music_category.lower() in file.lower()
                        ):
                            music_files.append(os.path.join(music_library_dir, file))

                # 카테고리 매칭이 없으면 모든 음악 파일에서 랜덤 선택
                if not music_files:
                    for ext in [".mp3", ".wav", ".m4a", ".ogg"]:
                        music_files.extend(
                            [
                                os.path.join(music_library_dir, f)
                                for f in os.listdir(music_library_dir)
                                if f.endswith(ext)
                            ]
                        )

                if music_files:
                    selected_music = random.choice(music_files)
                    logger.debug(
                        f"✅ 로컬 음악 라이브러리에서 선택: {os.path.basename(selected_music)}"
                    )
                    return selected_music

            # 방법 2: Freesound.org API 사용 (API 키가 있는 경우)
            freesound_api_key = os.getenv("FREESOUND_API_KEY")
            if freesound_api_key:
                try:
                    # Freesound API로 음악 검색 및 다운로드
                    freesound_url = f"https://freesound.org/apiv2/search/text/?query={music_category}&filter=duration:[{duration-5}:{duration+10}]&fields=id,name,previews&token={freesound_api_key}"
                    response = self._http_get_with_retry(freesound_url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("results") and len(data["results"]) > 0:
                            # 첫 번째 결과 선택
                            sound = data["results"][0]
                            preview_url = sound.get("previews", {}).get(
                                "preview-hq-mp3"
                            )
                            if preview_url:
                                # 음악 다운로드
                                music_path = os.path.join(
                                    settings.TEMP_DIR,
                                    f"bg_music_{int(time.time()*1000)}.mp3",
                                )
                                music_response = self._http_get_with_retry(
                                    preview_url, timeout=15
                                )
                                if music_response.status_code == 200:
                                    with open(music_path, "wb") as f:
                                        f.write(music_response.content)
                                    logger.debug(
                                        f"✅ Freesound에서 배경 음악 다운로드: {sound.get('name', 'Unknown')}"
                                    )
                                    return music_path
                except Exception as e:
                    logger.warning(f"   Freesound API 실패: {e}")

            # 방법 3: YouTube Audio Library 스타일의 무료 음악 (로컬 파일)
            logger.debug(
                "⚠️ 배경 음악을 찾을 수 없습니다. 로컬 음악 라이브러리(data/music/)에 음악 파일을 추가하거나 Freesound API 키를 설정하세요."
            )
            return None

        except Exception as e:
            logger.warning(f"⚠️ 배경 음악 다운로드 실패: {e}", exc_info=True)
            return None

    def mix_background_music(
        self, voice_clip: AudioFileClip, music_path: str, target_duration: float
    ) -> CompositeAudioClip:
        """
        음성 클립과 배경 음악을 믹싱
        """
        if not music_path or not os.path.exists(music_path):
            return voice_clip

        try:
            bg_music = AudioFileClip(music_path)

            # 음악 길이가 영상보다 짧으면 루프
            if bg_music.duration < target_duration:
                loops_needed = int(target_duration / bg_music.duration) + 1
                bg_music_clips = []
                for _ in range(loops_needed):
                    # 루프할 때마다 새로운 객체 생성 (안전성)
                    loop_clip = AudioFileClip(music_path)
                    bg_music_clips.append(loop_clip)

                bg_music_looped = concatenate_audioclips(bg_music_clips)
                bg_music_looped = bg_music_looped.subclip(0, target_duration)

                bg_music.close()
                bg_music = bg_music_looped
            else:
                # 음악이 더 길면 자르기
                bg_music = bg_music.subclip(0, target_duration)

            # 볼륨 조절
            music_volume = settings.BACKGROUND_MUSIC_VOLUME
            bg_music = bg_music.volumex(music_volume)

            # 페이드 인/아웃
            fade_duration = min(1.0, target_duration * VideoConstants.MUSIC_FADE_RATIO)
            # moviepy 1.0.3 vs 2.0 compatibility check needed, assuming standard fx usage
            try:
                bg_music = bg_music.fx(audio_fadein, fade_duration).fx(
                    audio_fadeout, fade_duration
                )
            except:
                # Fallback for older moviepy versions where fadein/fadeout might be different
                # But usually audio_fadein is correct for audio clips
                pass

            bg_music = bg_music.set_duration(target_duration)

            # 믹싱
            final_audio = CompositeAudioClip([voice_clip, bg_music])
            logger.debug(f"🎵 배경 음악 추가 완료 (볼륨: {music_volume*100:.0f}%)")

            # 원본 클립 닫기 (메모리 관리)
            # bg_music.close() # CompositeAudioClip에서 사용 중이므로 닫으면 안됨

            return final_audio

        except Exception as e:
            logger.warning(f"⚠️ 배경 음악 믹싱 실패: {e}")
            return voice_clip

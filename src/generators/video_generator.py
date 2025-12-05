"""
AI 영상 생성 모듈 (15초~60초 YouTube Shorts)
Refactored to use component-based architecture.
"""

import os
import time
from pathlib import Path

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from anthropic import Anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from src.core.config import settings
from .content_type import ContentType
from .video_constants import VideoConstants
from .script_generator import ScriptGenerator
from .audio_generator import AudioGenerator
from .image_generator import ImageGenerator
from .video_compositor import VideoCompositor
from .media_downloader import MediaDownloader
from src.pipeline.tts_engine import TTSEngine, TTSProvider
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 프로젝트 루트 디렉토리
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class AIVideoGenerator:
    """AI를 활용한 15초 YouTube Shorts 영상 생성 클래스 (Coordinator)"""

    def __init__(self, tts_provider=None):
        # OpenAI 클라이언트 초기화
        if settings.OPENAI_API_KEY and OPENAI_AVAILABLE:
            try:
                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception as e:
                logger.warning(f"⚠️ OpenAI 클라이언트 초기화 실패: {e}")
                self.openai_client = None
        else:
            self.openai_client = None

        # Claude (Anthropic) 클라이언트 초기화
        if settings.CLAUDE_API_KEY and ANTHROPIC_AVAILABLE:
            try:
                self.claude_client = Anthropic(api_key=settings.CLAUDE_API_KEY)
                logger.info("✅ Claude API 클라이언트 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ Claude 클라이언트 초기화 실패: {e}")
                self.claude_client = None
        else:
            self.claude_client = None

        # AI API 제공자 확인
        self.ai_provider = settings.AI_API_PROVIDER.lower()
        if self.ai_provider == "claude" and not self.claude_client:
            logger.warning("⚠️ Claude API가 설정되지 않았습니다. OpenAI를 사용합니다.")
            self.ai_provider = "openai"
        elif self.ai_provider == "openai" and not self.openai_client:
            if self.claude_client:
                logger.warning(
                    "⚠️ OpenAI API가 설정되지 않았습니다. Claude를 사용합니다."
                )
                self.ai_provider = "claude"
            else:
                logger.warning("⚠️ AI API가 설정되지 않았습니다.")

        # TTS 엔진 초기화 (AudioGenerator로 전달됨)
        self.tts_engine = None
        try:
            if tts_provider is None:
                tts_provider_str = settings.TTS_PROVIDER
                if tts_provider_str:
                    tts_provider = TTSProvider(tts_provider_str.lower())

            self.tts_engine = TTSEngine(provider=tts_provider)
            logger.info(f"✅ TTS 엔진 초기화: {self.tts_engine.get_provider().value}")
        except Exception as e:
            logger.warning(f"⚠️ TTS 엔진 초기화 실패: {e}")
            logger.info("   기본 gTTS를 사용합니다.")
            self.tts_engine = None

        # 컴포넌트 초기화
        self.script_generator = ScriptGenerator(
            openai_client=self.openai_client,
            claude_client=self.claude_client,
            ai_provider=self.ai_provider,
        )

        self.audio_generator = AudioGenerator(tts_engine=self.tts_engine)

        self.media_downloader = MediaDownloader(openai_client=self.openai_client)

        self.image_generator = ImageGenerator(openai_client=self.openai_client)

        self.video_compositor = VideoCompositor(
            audio_generator=self.audio_generator,
            media_downloader=self.media_downloader,
            openai_client=self.openai_client,
        )

        # 출력 디렉토리 생성
        # 출력 디렉토리 생성
        os.makedirs(settings.VIDEO_OUTPUT_DIR, exist_ok=True)
        os.makedirs(settings.TEMP_DIR, exist_ok=True)
        os.makedirs(settings.THUMBNAIL_OUTPUT_DIR, exist_ok=True)

    def generate_video(
        self,
        topic: str = None,
        duration: int = None,
        output_filename: str = None,
        performance_prompt: str = None,
        content_type: ContentType = None,
        language: str = "ko",
        target_audience: str = None,
    ) -> tuple:
        """
        AI를 활용하여 YouTube Shorts 영상 생성 (Main Orchestration Method)
        """

        start_time = time.time()
        logger.info("🎬 AI 영상 생성 시작...")

        # 1. 주제 생성 (없을 경우)
        topic_source = "user_provided"
        if not topic:
            topic, topic_source = self.script_generator.generate_topic(
                content_type=content_type
            )
            logger.info(f"📌 생성된 주제: {topic} (출처: {topic_source})")
        else:
            logger.info(f"📌 입력된 주제: {topic}")

        # 2. 스크립트 생성
        logger.info("📝 스크립트 생성 중...")
        script = self.script_generator.generate_script(
            topic,
            performance_prompt=performance_prompt,
            content_type=content_type,
            language=language,
            target_audience=target_audience,
        )

        if not script:
            logger.error("❌ 스크립트 생성 실패")
            return None, None, None

        logger.info(f"✅ 스크립트 생성 완료 ({len(script)}개 문장)")
        for i, line in enumerate(script):
            logger.debug(f"   {i+1}. {line}")

        # 3. 영상 길이 설정
        if not duration:
            duration = VideoConstants.TARGET_DURATION

        # 4. 영상 합성 (VideoCompositor 위임)
        logger.info("🎥 영상 합성 시작...")
        try:
            video_path = self.video_compositor.create_video_from_script(
                script=script,
                topic=topic,
                duration=duration,
                output_filename=output_filename,
                content_type=content_type,
                language=language,
            )
        except Exception as e:
            logger.error(f"❌ 영상 합성 실패: {e}", exc_info=True)
            return None, None, None

        if not video_path or not os.path.exists(video_path):
            logger.error("❌ 영상 파일 생성 실패")
            return None, None, None

        logger.info(f"✅ 영상 생성 완료: {video_path}")

        # 5. 썸네일 생성 (ImageGenerator 위임)
        logger.info("🖼️ 썸네일 생성 중...")
        thumbnail_path = None
        try:
            thumbnail_path = self.image_generator.generate_thumbnail(
                video_path=video_path, title=topic, topic=topic, script=script
            )
            if thumbnail_path:
                logger.info(f"✅ 썸네일 생성 완료: {thumbnail_path}")
            else:
                logger.warning("⚠️ 썸네일 생성 실패")
        except Exception as e:
            logger.warning(f"⚠️ 썸네일 생성 중 오류: {e}")

        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"✨ 전체 작업 완료! (소요 시간: {elapsed_time:.2f}초)")

        return video_path, thumbnail_path, topic, script

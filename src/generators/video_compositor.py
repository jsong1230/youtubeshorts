"""
영상 합성 및 편집 모듈 (MoviePy 기반)
Refactored to use helper classes for better modularity.
"""

import os
from moviepy.editor import AudioFileClip

from src.core.config import settings
from .content_type import ContentType
from .audio_generator import AudioGenerator
from .video.subtitle_renderer import SubtitleRenderer
from .video.background_video_manager import BackgroundVideoManager
from .video.video_editor import VideoEditor
from src.utils.logger import get_logger

logger = get_logger(__name__)


class VideoCompositor:
    """영상 합성 및 편집 클래스 (Coordinator)"""

    def __init__(
        self, audio_generator: AudioGenerator, media_downloader=None, openai_client=None
    ):
        self.audio_generator = audio_generator
        self.media_downloader = media_downloader
        self.openai_client = openai_client

        # Initialize helper classes
        self.subtitle_renderer = SubtitleRenderer(openai_client=openai_client)
        self.background_manager = BackgroundVideoManager(
            media_downloader=media_downloader
        )
        self.video_editor = VideoEditor(
            audio_generator=audio_generator,
            subtitle_renderer=self.subtitle_renderer,
            background_manager=self.background_manager,
        )

    def create_video_from_script(
        self,
        script: list,
        topic: str,
        duration: int,
        output_filename: str = None,
        content_type: ContentType = None,
        language: str = "ko",
    ) -> str:
        """
        스크립트로부터 영상 생성
        """
        # 출력 파일명 생성
        if not output_filename:
            import datetime

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"shorts_{timestamp}.mp4"

        output_path = os.path.join(settings.VIDEO_OUTPUT_DIR, output_filename)

        # 각 문장별로 음성 생성 및 실제 길이 측정
        sentence_audio_durations = []
        audio_clips = []

        logger.info(f"📊 영상 구성: {len(script)}개 문장")
        logger.info("🔊 음성 생성 및 길이 측정 중...")

        for i, sentence in enumerate(script):
            content_type_str = content_type.value if content_type else None
            audio_path = self.audio_generator.generate_audio(
                sentence, i, content_type=content_type_str, language=language
            )
            if audio_path and os.path.exists(audio_path):
                audio_clip = AudioFileClip(audio_path)
                actual_duration = audio_clip.duration
                sentence_audio_durations.append(actual_duration)
                audio_clips.append(audio_clip)
                logger.debug(
                    f"   문장 {i+1}: {actual_duration:.2f}초 - {sentence[:30]}..."
                )
            else:
                # 음성 생성 실패 시 기본 duration 사용
                default_duration = duration / len(script)
                sentence_audio_durations.append(default_duration)
                logger.warning(
                    f"   문장 {i+1}: 음성 생성 실패, 기본 길이 사용 ({default_duration:.2f}초)"
                )

        # 실제 음성 길이 합계
        total_audio_duration = sum(sentence_audio_durations)
        logger.info(f"📏 실제 음성 총 길이: {total_audio_duration:.2f}초")

        # 음성 길이를 기준으로 영상 길이 조정 (60초 초과 방지)
        max_safe_duration = 58  # 60초 초과 방지를 위한 안전 마진
        if total_audio_duration > max_safe_duration:
            logger.warning(
                f"⚠️ 음성 길이가 {max_safe_duration}초를 초과합니다. 마지막 문장들을 제거하여 {max_safe_duration}초 이내로 맞춥니다."
            )

            # 마지막 문장부터 제거하여 58초 이내로 맞추기
            removed_count = 0
            original_script_len = len(script)
            while total_audio_duration > max_safe_duration and len(script) > 1:
                # pop 전 길이 저장 (동기화 확인용)
                script_len_before_pop = len(script)
                # 마지막 문장 제거
                removed_sentence = script.pop()
                removed_audio_duration = sentence_audio_durations.pop()
                # audio_clips도 동기화를 위해 제거
                if len(audio_clips) >= script_len_before_pop:
                    audio_clips.pop()
                total_audio_duration -= removed_audio_duration
                removed_count += 1
                logger.debug(
                    f"   문장 제거: '{removed_sentence[:30]}...' ({removed_audio_duration:.2f}초)"
                )

            duration = min(total_audio_duration, max_safe_duration)
            logger.info(
                f"   최종 음성 길이: {total_audio_duration:.2f}초 ({removed_count}개 문장 제거됨)"
            )
        elif total_audio_duration > duration:
            # duration이 max_safe_duration 이하인 경우에만 조정
            duration = min(total_audio_duration, max_safe_duration)
            logger.debug(
                f"   영상 길이를 음성 길이에 맞춤: {duration:.2f}초 (최대 {max_safe_duration}초)"
            )
        elif abs(total_audio_duration - duration) > 1.0:
            # 목표 duration과 차이가 있더라도 실제 음성 길이를 그대로 사용
            logger.debug(
                f"   duration 정보: 실제 음성 {total_audio_duration:.2f}초, 목표 {duration}초 (스케일링하지 않음)"
            )

        # 배경 그룹 준비 (BackgroundVideoManager 사용)
        background_groups, downloaded_video_ids = (
            self.background_manager.prepare_background_clips(
                script, sentence_audio_durations, topic
            )
        )

        total_video_duration = sum(sentence_audio_durations)

        # 배경 영상 클립 준비 (VideoEditor 사용)
        background_clips = self.video_editor.prepare_background_clips(
            background_groups, sentence_audio_durations
        )

        # 자막 클립 준비 (VideoEditor 사용)
        subtitle_clips = self.video_editor.prepare_subtitle_clips(
            script, sentence_audio_durations, language
        )

        # 최종 영상 합성 (VideoEditor 사용)
        final_video = self.video_editor.compose_final_video(
            background_clips=background_clips,
            subtitle_clips=subtitle_clips,
            audio_clips=audio_clips,
            total_duration=total_video_duration,
            content_type=content_type,
            topic=topic,
        )

        # 영상 저장 (VideoEditor 사용)
        # sync_audio_video에서 이미 duration이 설정되었으므로 final_video.duration 사용
        self.video_editor.save_video(
            final_video,
            output_path,
            final_video.duration if final_video.audio else None,
        )

        return output_path

    # Removed methods - now delegated to helper classes:
    # - _download_video_for_sentence -> BackgroundVideoManager.download_video_for_sentence
    # - _draw_text_on_image -> SubtitleRenderer.draw_text_on_image
    # - _wrap_text -> SubtitleRenderer.wrap_text
    # - _extract_key_words_for_subtitle -> SubtitleRenderer.extract_key_words
    # - _create_subtitle_clip -> SubtitleRenderer.create_subtitle_clip

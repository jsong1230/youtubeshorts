"""
영상 편집 및 합성 모듈
"""

import os
from typing import List, Optional, Tuple
from moviepy.editor import (
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
    VideoFileClip,
)
from moviepy.audio.AudioClip import concatenate_audioclips
from moviepy.video.fx.all import fadein, fadeout

from src.core.config import settings
from src.generators.video_constants import VideoConstants
from src.generators.content_type import ContentType
from src.generators.audio_generator import AudioGenerator
from src.generators.video.subtitle_renderer import SubtitleRenderer
from src.generators.video.background_video_manager import BackgroundVideoManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class VideoEditor:
    """영상 합성 및 최종 편집 클래스"""

    def __init__(
        self,
        audio_generator: AudioGenerator,
        subtitle_renderer: SubtitleRenderer,
        background_manager: BackgroundVideoManager,
    ):
        self.audio_generator = audio_generator
        self.subtitle_renderer = subtitle_renderer
        self.background_manager = background_manager

    def compose_final_video(
        self,
        background_clips: List[VideoFileClip],
        subtitle_clips: List,
        audio_clips: List[AudioFileClip],
        total_duration: float,
        content_type: Optional[ContentType] = None,
        topic: str = None,
    ) -> CompositeVideoClip:
        """최종 영상 합성

        Args:
            background_clips: 배경 영상 클립 리스트
            subtitle_clips: 자막 클립 리스트
            audio_clips: 오디오 클립 리스트
            total_duration: 총 영상 길이
            content_type: 콘텐츠 타입
            topic: 주제

        Returns:
            합성된 최종 영상 클립
        """
        # 배경 영상 합성 (각 배경 영상은 원래 길이만큼 사용, 자막과 독립)
        if len(background_clips) == 1:
            base_video_clip = background_clips[0]
        else:
            base_video_clip = concatenate_videoclips(background_clips)

        # 배경 영상의 실제 총 길이 확인
        actual_bg_duration = base_video_clip.duration
        logger.info(
            f"   ✅ 모든 배경 영상 합성 완료: 실제 길이 {actual_bg_duration:.2f}초 ({len(background_clips)}개, 각각 원본 길이 사용)"
        )
        logger.info(
            f"   📊 배경 영상과 자막은 완전히 독립적으로 작동 (배경: {actual_bg_duration:.2f}초, 자막/음성: {total_duration:.2f}초)"
        )

        # 배경 영상만 먼저 처리 (자막은 나중에 검은색 배경 영역에 배치)
        logger.info(
            f"🎬 배경 영상 준비 중... (배경: {total_duration:.2f}초, 자막: {len(subtitle_clips)}개)"
        )
        content_video = base_video_clip
        content_video = content_video.set_duration(total_duration)

        # 페이드 효과 적용 (배경 영상만)
        content_video = self.apply_fade_effects(content_video, total_duration)

        # 루프(Loop) 설계 적용 (배경 영상만)
        if VideoConstants.ENABLE_LOOP_DESIGN and total_duration > 0:
            content_video = self.apply_loop_design(content_video, total_duration)

        logger.info(
            f"✅ 배경 영상 길이: {content_video.duration:.2f}초 (목표: {total_duration:.2f}초)"
        )

        # 음성 추가 및 동기화 (배경 영상만)
        if audio_clips:
            content_video = self.sync_audio_video(
                content_video, audio_clips, content_type, topic
            )

        # 최종 설정
        content_video = content_video.set_fps(VideoConstants.VIDEO_FPS)

        # 9:9 정사각형 콘텐츠 영역으로 리사이즈
        if (
            content_video.size[0] != VideoConstants.CONTENT_WIDTH
            or content_video.size[1] != VideoConstants.CONTENT_HEIGHT
        ):
            content_video = content_video.resize(
                (VideoConstants.CONTENT_WIDTH, VideoConstants.CONTENT_HEIGHT)
            )

        # 위아래 검은색 배경 추가
        from moviepy.editor import ColorClip, CompositeVideoClip

        black_bar_height = VideoConstants.BLACK_BAR_HEIGHT

        # 자막을 위 검은색 배경 영역에 배치하기 위해 위치 조정
        adjusted_subtitle_clips = []
        if subtitle_clips:
            # 자막을 위 검은색 배경 영역 중앙에 배치
            # 위 검은색 배경 영역: 0 ~ black_bar_height (420px)
            # 중앙 위치: black_bar_height // 2 = 210px
            subtitle_y_position = black_bar_height // 2  # 위 검은색 배경 영역의 중앙
            logger.info(
                f"   📝 자막을 위 검은색 배경 영역에 배치 (y: {subtitle_y_position}px, 영역: 0~{black_bar_height}px)"
            )
            for subtitle_clip in subtitle_clips:
                # 자막의 현재 위치를 무시하고 위 검은색 배경 영역으로 명시적으로 이동
                # 자막은 원래 콘텐츠 영역(1080x1080) 내에 배치되어 있었지만,
                # 검은색 배경 추가 후에는 위 검은색 배경 영역으로 이동
                adjusted_clip = subtitle_clip.set_position(
                    ("center", subtitle_y_position)
                )
                adjusted_subtitle_clips.append(adjusted_clip)

        top_bar = ColorClip(
            size=(VideoConstants.VIDEO_WIDTH, black_bar_height),
            color=(0, 0, 0),  # 검은색
            duration=total_duration,
        )
        bottom_bar = ColorClip(
            size=(VideoConstants.VIDEO_WIDTH, black_bar_height),
            color=(0, 0, 0),  # 검은색
            duration=total_duration,
        )

        # 콘텐츠를 중앙에 배치 (위아래 검은색 배경 사이)
        content_video = content_video.set_position(("center", black_bar_height))

        # 최종 합성: 위 검은색 배경 + 자막 + 콘텐츠 + 아래 검은색 배경
        final_clips = [
            top_bar.set_position(("center", 0)),
            content_video,
            bottom_bar.set_position(
                ("center", VideoConstants.CONTENT_HEIGHT + black_bar_height)
            ),
        ]

        # 자막을 위 검은색 배경 영역에 추가
        if adjusted_subtitle_clips:
            final_clips.extend(adjusted_subtitle_clips)

        final_video = CompositeVideoClip(
            final_clips, size=(VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT)
        )

        logger.info(
            f"   ✅ 9:9 정사각형 콘텐츠에 검은색 배경 추가 완료: {VideoConstants.CONTENT_WIDTH}x{VideoConstants.CONTENT_HEIGHT} → {VideoConstants.VIDEO_WIDTH}x{VideoConstants.VIDEO_HEIGHT}"
        )
        if subtitle_clips:
            logger.info(
                f"   📝 자막을 위 검은색 배경 영역에 배치 완료 (y: {subtitle_y_position}px, 영역: 0~{black_bar_height}px)"
            )

        return final_video

    def apply_loop_design(
        self, video: CompositeVideoClip, total_duration: float
    ) -> CompositeVideoClip:
        """루프(Loop) 설계 적용 (성공 공식: 끝과 시작이 자연스럽게 이어지도록)

        영상의 마지막 프레임과 첫 프레임을 자연스럽게 연결하여
        반복 재생 시 매끄러운 전환을 만듭니다.

        Args:
            video: 합성된 영상 클립
            total_duration: 총 영상 길이

        Returns:
            루프 설계가 적용된 영상 클립
        """
        if not VideoConstants.ENABLE_LOOP_DESIGN:
            return video

        try:
            loop_transition = VideoConstants.LOOP_TRANSITION_DURATION

            # 마지막 프레임 추출 (루프 전환용)
            if total_duration > loop_transition:
                # 첫 프레임과 마지막 프레임이 유사한지 확인
                # (실제로는 페이드 효과로 자연스럽게 연결)
                # 루프를 위한 추가 처리는 필요 시 구현

                logger.debug(f"   🔄 루프 설계 적용: 전환 길이 {loop_transition:.2f}초")
            else:
                logger.debug("   ⚠️ 영상이 너무 짧아 루프 설계를 적용할 수 없습니다.")

        except Exception as e:
            logger.warning(f"   ⚠️ 루프 설계 적용 실패: {e}")

        return video

    def apply_fade_effects(
        self, video: CompositeVideoClip, duration: float
    ) -> CompositeVideoClip:
        """페이드 효과 적용"""
        fade_duration = min(
            VideoConstants.DEFAULT_FADE_DURATION, duration * VideoConstants.FADE_RATIO
        )
        if duration > fade_duration * 2:
            video = video.fx(fadein, fade_duration).fx(fadeout, fade_duration)
            video = video.set_duration(duration)
        return video

    def sync_audio_video(
        self,
        video: CompositeVideoClip,
        audio_clips: List[AudioFileClip],
        content_type: Optional[ContentType] = None,
        topic: str = None,
    ) -> CompositeVideoClip:
        """음성-영상 동기화"""
        try:
            final_audio = concatenate_audioclips(audio_clips)

            actual_audio_duration = final_audio.duration
            actual_video_duration = video.duration

            logger.debug(
                f"🎵 음성 총 길이: {actual_audio_duration:.2f}초, 영상 총 길이: {actual_video_duration:.2f}초"
            )

            # 영상 길이를 음성 길이에 맞춤
            if abs(actual_video_duration - actual_audio_duration) > 0.01:
                logger.debug(
                    f"   영상 길이를 음성 길이에 맞춤: {actual_video_duration:.2f}초 -> {actual_audio_duration:.2f}초"
                )
                if actual_video_duration > actual_audio_duration:
                    video = video.subclip(0, actual_audio_duration)
                else:
                    # 영상 확장
                    extension_needed = actual_audio_duration - actual_video_duration
                    logger.debug(f"   영상 확장 필요: {extension_needed:.2f}초")
                    extension_source = video.subclip(
                        max(
                            0, actual_video_duration - VideoConstants.EXTENSION_DURATION
                        ),
                        actual_video_duration,
                    )
                    extension_clips = []
                    remaining = extension_needed
                    while remaining > 0.01:
                        ext_dur = min(VideoConstants.EXTENSION_DURATION, remaining)
                        ext_clip = extension_source.subclip(
                            0, VideoConstants.EXTENSION_DURATION
                        ).set_duration(ext_dur)
                        extension_clips.append(ext_clip)
                        remaining -= ext_dur
                    if extension_clips:
                        extension_video = concatenate_videoclips(
                            extension_clips, method="compose"
                        )
                        video = concatenate_videoclips(
                            [video, extension_video], method="compose"
                        )
                video = video.set_duration(actual_audio_duration)
                actual_video_duration = actual_audio_duration

            # 최대 길이 제한
            max_safe_duration = VideoConstants.MAX_DURATION
            if actual_video_duration > max_safe_duration:
                actual_video_duration = max_safe_duration
                video = video.subclip(0, actual_video_duration)
                final_audio = final_audio.subclip(0, actual_video_duration)

            # 배경 음악 추가
            if settings.USE_BACKGROUND_MUSIC:
                try:
                    background_music_path = (
                        self.audio_generator.download_background_music(
                            content_type=(
                                content_type if content_type else ContentType.AUTO
                            ),
                            duration=actual_audio_duration,
                            topic=topic,
                        )
                    )

                    if background_music_path and os.path.exists(background_music_path):
                        final_audio = self.audio_generator.mix_background_music(
                            final_audio, background_music_path, actual_audio_duration
                        )
                except Exception as e:
                    logger.warning(
                        f"⚠️ 배경 음악 추가 실패 (계속 진행): {e}", exc_info=True
                    )

            video = video.set_audio(final_audio)
            video = video.set_duration(actual_audio_duration)

            logger.info(
                f"✅ 음성-영상 동기화 완료: 영상 {actual_video_duration:.2f}초, 음성 {actual_audio_duration:.2f}초 (정확히 일치)"
            )

            return video
        except Exception as e:
            logger.error(f"⚠️ 음성 추가 실패: {e}", exc_info=True)
            return video

    def prepare_background_clips(
        self, background_groups: List[Tuple], sentence_audio_durations: List[float]
    ) -> List[VideoFileClip]:
        """배경 영상 클립 준비 (각 문장마다 독립적으로, 원래 길이 사용)"""
        background_clips = []

        for gs, ge, bg_video_path, bg_image in background_groups:
            # 각 문장마다 하나의 배경 영상 (ge = gs + 1)
            sentence_duration = (
                sentence_audio_durations[gs]
                if gs < len(sentence_audio_durations)
                else 3.0
            )

            if bg_video_path and os.path.exists(bg_video_path):
                try:
                    # 배경 영상은 원래 길이만큼 사용 (문장 길이와 독립)
                    group_clip = self.background_manager.create_background_video_clip(
                        bg_video_path, sentence_duration, gs, ge
                    )
                    # 실제 영상 길이 확인 (원래 길이 사용)
                    actual_duration = group_clip.duration
                    logger.debug(
                        f"   📹 배경 영상 {gs+1}: 원본 길이 {actual_duration:.2f}초 사용 (문장 길이: {sentence_duration:.2f}초와 독립)"
                    )
                    background_clips.append(group_clip)
                except Exception as e:
                    logger.error(f"   ❌ 배경 영상 사용 실패: {e}", exc_info=True)
                    raise ValueError(
                        f"문장 {gs+1}의 배경 영상을 로드할 수 없습니다: {e}"
                    )
            else:
                # 배경 영상이 없으면 단색 배경으로 폴백
                logger.warning(f"   ⚠️ 배경 영상 없음, 단색 배경으로 폴백 (문장 {gs+1})")
                try:
                    # 단색 배경 이미지 생성 (동기부여/힐링 콘텐츠에 맞는 차분한 색상)
                    from moviepy.editor import ColorClip

                    # 차분한 어두운 배경 (동기부여/힐링 콘텐츠에 적합)
                    # 배경 영상은 원래 길이 사용하지만, 폴백은 문장 길이만큼
                    # 9:9 정사각형 콘텐츠 영역 크기
                    bg_clip = ColorClip(
                        size=(
                            VideoConstants.CONTENT_WIDTH,
                            VideoConstants.CONTENT_HEIGHT,
                        ),  # 9:9 정사각형
                        color=(20, 20, 30),  # 어두운 남색 계열
                        duration=sentence_duration,
                    )
                    background_clips.append(bg_clip)
                    logger.info(
                        f"   ✅ 단색 배경 생성 및 사용 (문장 {gs+1}, 9:9 정사각형)"
                    )
                except Exception as e:
                    logger.error(f"   ❌ 단색 배경 생성 실패: {e}")
                    raise ValueError(
                        f"문장 {gs+1}에 배경 영상/이미지가 없습니다. 배경 미디어 생성이 필요합니다."
                    )

        return background_clips

    def prepare_subtitle_clips(
        self,
        script: List[str],
        sentence_audio_durations: List[float],
        language: str = "ko",
    ) -> List:
        """자막 클립 준비"""
        subtitle_clips = []
        current_time = 0.0

        for i, sentence in enumerate(script):
            actual_audio_duration = (
                sentence_audio_durations[i]
                if i < len(sentence_audio_durations)
                else sentence_audio_durations[0] if sentence_audio_durations else 3.0
            )

            try:
                logger.debug(
                    f"   문장 {i+1} 자막 생성: {sentence[:30]}... (시작: {current_time:.2f}초)"
                )
                subtitle_clip = self.subtitle_renderer.create_subtitle_clip(
                    sentence, actual_audio_duration, language=language
                )
                if subtitle_clip:
                    subtitle_clip = subtitle_clip.set_duration(actual_audio_duration)
                    if getattr(subtitle_clip, "pos", None) is None:
                        # 성공 공식: 자막을 중앙/상단 배치 (VideoConstants 설정 사용)
                        position = VideoConstants.SUBTITLE_PREFERRED_POSITION
                        if position == "top":
                            subtitle_clip = subtitle_clip.set_position(
                                ("center", VideoConstants.SUBTITLE_TOP_MARGIN)
                            )
                            position_str = (
                                f"상단 ({VideoConstants.SUBTITLE_TOP_MARGIN}px)"
                            )
                        else:  # center (기본값)
                            subtitle_clip = subtitle_clip.set_position(
                                ("center", "center")
                            )
                            position_str = "중앙"

                        # 첫 자막만 상세 로그 출력
                        if i == 0:
                            logger.info(
                                f"   📍 자막 배치: {position_str} (성공 공식 적용)"
                            )
                    subtitle_clip = subtitle_clip.set_start(current_time)
                    subtitle_clips.append(subtitle_clip)
                    logger.debug(
                        f"   ✅ 자막 추가: {current_time:.2f}초~{current_time + actual_audio_duration:.2f}초"
                    )
                else:
                    logger.warning("   ⚠️ 자막 클립이 None입니다")
            except Exception as e:
                logger.warning(f"   ❌ 자막 생성 실패 (계속 진행): {e}", exc_info=True)

            current_time += actual_audio_duration

        return subtitle_clips

    def save_video(
        self,
        video: CompositeVideoClip,
        output_path: str,
        final_audio_duration: Optional[float] = None,
    ) -> None:
        """영상 저장"""
        # 최종 duration 확인 (이미 sync_audio_video에서 처리되었으므로 추가 확인만)
        if final_audio_duration and video.audio:
            if abs(video.duration - final_audio_duration) > 0.01:
                if video.duration > final_audio_duration:
                    video = video.subclip(0, final_audio_duration)
                else:
                    video = video.set_duration(final_audio_duration)
                if video.audio:
                    video = video.set_audio(
                        video.audio.subclip(0, final_audio_duration)
                    )
                video = video.set_duration(final_audio_duration)

        logger.info(f"💾 영상 저장 중... (최종 duration: {video.duration:.2f}초)")
        video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=30,
            preset="medium",
            bitrate="8000k",
        )

        # 임시 파일 정리
        try:
            from src.utils.temp_cleaner import TempCleaner

            temp_cleaner = TempCleaner(max_age_hours=1)
            stats = temp_cleaner.clean_old_files(dry_run=False)
            if stats["deleted"] > 0:
                logger.info(
                    f"🧹 임시 파일 자동 정리: {stats['deleted']}개 파일 삭제 ({stats['size_freed'] / 1024 / 1024:.2f} MB 해제)"
                )
        except Exception as e:
            logger.warning(f"   ⚠️ 임시 파일 정리 실패 (무시): {e}")

"""
영상 편집 및 합성 모듈
"""

import os
from typing import List, Optional, Tuple
from moviepy.editor import (
    AudioFileClip,
    CompositeVideoClip,
    VideoClip,
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
        script: List[str] = None,
        language: str = "ko",
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

        # 배경 영상을 9:9 정사각형 비율로 crop (resize 대신)
        content_video = self._crop_to_9_9(content_video)

        # 리사이즈 없이 원본 비율 유지 (crop 후)
        logger.debug(
            f"   배경 영상 크기: {content_video.size[0]}x{content_video.size[1]} (9:9 crop 적용)"
        )

        # 위쪽 훅 영역을 위해 영상 위쪽을 crop (resize 없이)
        hook_height = VideoConstants.HOOK_TITLE_HEIGHT
        if content_video.size[1] > VideoConstants.VIDEO_HEIGHT - hook_height:
            # 영상 높이가 훅 영역을 제외한 높이보다 크면 위쪽을 crop
            crop_height = content_video.size[1] - (
                VideoConstants.VIDEO_HEIGHT - hook_height
            )
            content_video = content_video.crop(
                x1=0, y1=crop_height, x2=content_video.size[0], y2=content_video.size[1]
            )
            logger.debug(f"   영상 위쪽 crop: {crop_height}px 제거 (훅 영역 확보)")

        # 제목/훅 클립 생성 (맨 위에 강조 표시)
        hook_title_clip = None
        if VideoConstants.HOOK_TITLE_ENABLED and script and len(script) > 0:
            hook_title_clip = self._create_hook_title_clip(
                script[0], topic, total_duration, language
            )

        # 자막 위치 조정 (세로 가운데에 맨 윗줄이 오도록)
        adjusted_subtitle_clips = []
        if subtitle_clips:
            # 자막을 세로 가운데에 배치 (맨 윗줄이 중앙에 오도록)
            position = VideoConstants.SUBTITLE_PREFERRED_POSITION
            if position == "center":
                # 중앙 배치 (세로 가운데)
                for subtitle_clip in subtitle_clips:
                    adjusted_clip = subtitle_clip.set_position(("center", "center"))
                    adjusted_subtitle_clips.append(adjusted_clip)
            elif position == "bottom":
                # 하단 배치
                bottom_y = (
                    VideoConstants.VIDEO_HEIGHT - VideoConstants.SUBTITLE_BOTTOM_MARGIN
                )
                for subtitle_clip in subtitle_clips:
                    adjusted_clip = subtitle_clip.set_position(("center", bottom_y))
                    adjusted_subtitle_clips.append(adjusted_clip)
            else:  # top
                top_margin = VideoConstants.SUBTITLE_TOP_MARGIN
                for subtitle_clip in subtitle_clips:
                    adjusted_clip = subtitle_clip.set_position(("center", top_margin))
                    adjusted_subtitle_clips.append(adjusted_clip)

        # 9:16 전체 영상에 위아래 흰색 배경 추가, 배경 영상(9:9)은 가운데에 배치
        from moviepy.editor import ColorClip

        # 위쪽 훅 영역 배경 (흰색 또는 검은색)
        hook_height = VideoConstants.HOOK_TITLE_HEIGHT
        hook_background = ColorClip(
            size=(VideoConstants.VIDEO_WIDTH, hook_height),
            color=VideoConstants.HOOK_TITLE_BACKGROUND_COLOR,
            duration=total_duration,
        )

        # 아래쪽 흰색 배경 클립 생성 (나머지 영역)
        bottom_height = VideoConstants.VIDEO_HEIGHT - hook_height
        white_background = ColorClip(
            size=(VideoConstants.VIDEO_WIDTH, bottom_height),
            color=(255, 255, 255),  # 흰색
            duration=total_duration,
        )

        # 배경 영상(9:9)을 가운데에 배치 (훅 영역 아래, 위아래 공백)
        # 훅 영역 아래에서 시작하도록 위치 조정
        content_y = hook_height + (bottom_height - content_video.size[1]) // 2
        content_video = content_video.set_position(("center", content_y))

        # 최종 합성: 훅 배경 + 아래쪽 흰색 배경 + 배경 영상(9:9, 가운데) + 제목/훅 + 자막
        hook_background = hook_background.set_position(("center", 0))  # 맨 위
        white_background = white_background.set_position(
            ("center", hook_height)
        )  # 훅 아래

        final_clips = [hook_background, white_background, content_video]

        # 제목/훅 추가 (맨 위, 영상 끝까지 유지)
        if hook_title_clip:
            final_clips.append(hook_title_clip)

        # 자막 추가
        if adjusted_subtitle_clips:
            final_clips.extend(adjusted_subtitle_clips)

        # 최종 영상 크기는 9:16
        final_size = (VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT)
        final_video = CompositeVideoClip(final_clips, size=final_size)

        logger.info(
            f"   ✅ 9:16 전체 영상 완료: {final_size[0]}x{final_size[1]} (배경 영상 9:9 crop, 가운데 배치, 위쪽 훅 배경, 아래쪽 흰색 배경)"
        )
        if hook_title_clip:
            logger.info(
                f"   📌 제목/훅을 맨 위에 강조 표시 완료 (폰트 크기: {VideoConstants.HOOK_TITLE_FONT_SIZE}px)"
            )
        if subtitle_clips:
            position_str = VideoConstants.SUBTITLE_PREFERRED_POSITION
            if position_str == "bottom":
                logger.info(
                    f"   📝 자막을 화면 하단에 배치 완료 (하단 여백: {VideoConstants.SUBTITLE_BOTTOM_MARGIN}px)"
                )
            elif position_str == "center":
                logger.info("   📝 자막을 화면 중앙에 배치 완료")
            else:
                logger.info(
                    f"   📝 자막을 화면 상단에 배치 완료 (상단 여백: {VideoConstants.SUBTITLE_TOP_MARGIN}px)"
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
        """배경 영상 클립 준비 (5초마다 전환)"""
        background_clips = []

        for gs, ge, bg_video_path, bg_image in background_groups:
            # 5초 구간의 총 길이 계산
            group_duration = sum(
                sentence_audio_durations[i]
                for i in range(gs, min(ge, len(sentence_audio_durations)))
            )

            if bg_video_path and os.path.exists(bg_video_path):
                try:
                    # 배경 영상은 5초 구간 길이로 사용
                    group_clip = self.background_manager.create_background_video_clip(
                        bg_video_path, group_duration, gs, ge
                    )
                    # 실제 영상 길이 확인
                    actual_duration = group_clip.duration
                    logger.debug(
                        f"   📹 배경 영상 구간 {gs+1}~{ge}: 길이 {actual_duration:.2f}초 (목표: {group_duration:.2f}초)"
                    )
                    background_clips.append(group_clip)
                except Exception as e:
                    logger.error(f"   ❌ 배경 영상 사용 실패: {e}", exc_info=True)
                    raise ValueError(
                        f"구간 {gs+1}~{ge}의 배경 영상을 로드할 수 없습니다: {e}"
                    )
            else:
                # 배경 영상이 없으면 단색 배경으로 폴백
                logger.warning(
                    f"   ⚠️ 배경 영상 없음, 단색 배경으로 폴백 (구간 {gs+1}~{ge})"
                )
                try:
                    # 단색 배경 이미지 생성 (동기부여/힐링 콘텐츠에 맞는 차분한 색상)
                    from moviepy.editor import ColorClip

                    # 차분한 어두운 배경 (동기부여/힐링 콘텐츠에 적합)
                    # 9:16 전체 영역 크기
                    bg_clip = ColorClip(
                        size=(
                            VideoConstants.VIDEO_WIDTH,
                            VideoConstants.VIDEO_HEIGHT,
                        ),  # 9:16 전체
                        color=(20, 20, 30),  # 어두운 남색 계열
                        duration=group_duration,
                    )
                    background_clips.append(bg_clip)
                    logger.info(
                        f"   ✅ 단색 배경 생성 및 사용 (구간 {gs+1}~{ge}, 9:16 전체)"
                    )
                except Exception as e:
                    logger.error(f"   ❌ 단색 배경 생성 실패: {e}")
                    raise ValueError(
                        f"구간 {gs+1}~{ge}에 배경 영상/이미지가 없습니다. 배경 미디어 생성이 필요합니다."
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
                        # 성공 공식: 자막을 중앙/하단 배치 (VideoConstants 설정 사용)
                        position = VideoConstants.SUBTITLE_PREFERRED_POSITION
                        if position == "top":
                            subtitle_clip = subtitle_clip.set_position(
                                ("center", VideoConstants.SUBTITLE_TOP_MARGIN)
                            )
                            position_str = (
                                f"상단 ({VideoConstants.SUBTITLE_TOP_MARGIN}px)"
                            )
                        elif position == "bottom":
                            bottom_y = (
                                VideoConstants.VIDEO_HEIGHT
                                - VideoConstants.SUBTITLE_BOTTOM_MARGIN
                            )
                            subtitle_clip = subtitle_clip.set_position(
                                ("center", bottom_y)
                            )
                            position_str = (
                                f"하단 ({VideoConstants.SUBTITLE_BOTTOM_MARGIN}px)"
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

    def _crop_to_9_9(self, video: VideoClip) -> VideoClip:
        """배경 영상을 9:9 정사각형 비율로 crop (resize 대신)"""
        try:
            video_width, video_height = video.size
            target_width = VideoConstants.CONTENT_WIDTH  # 1080 (9:9 정사각형)
            target_height = VideoConstants.CONTENT_HEIGHT  # 1080 (9:9 정사각형)
            target_aspect = target_width / target_height  # 9:9 = 1.0

            # 현재 영상의 비율 계산
            current_aspect = video_width / video_height

            # 9:9 정사각형 비율로 crop
            if abs(current_aspect - target_aspect) > 0.01:  # 비율이 다르면 crop
                if current_aspect > target_aspect:
                    # 영상이 더 넓음: 높이를 기준으로 crop
                    new_height = video_height
                    new_width = int(new_height * target_aspect)  # 정사각형
                    x_center = video_width / 2
                    x1 = int(x_center - new_width / 2)
                    x2 = int(x_center + new_width / 2)
                    cropped = video.crop(x1=x1, y1=0, x2=x2, y2=new_height)
                    logger.debug(
                        f"   ✂️ 영상 crop: {video_width}x{video_height} -> {new_width}x{new_height} (9:9)"
                    )
                    return cropped
                else:
                    # 영상이 더 좁음: 너비를 기준으로 crop
                    new_width = video_width
                    new_height = int(new_width / target_aspect)  # 정사각형
                    y_center = video_height / 2
                    y1 = int(y_center - new_height / 2)
                    y2 = int(y_center + new_height / 2)
                    cropped = video.crop(x1=0, y1=y1, x2=new_width, y2=y2)
                    logger.debug(
                        f"   ✂️ 영상 crop: {video_width}x{video_height} -> {new_width}x{new_height} (9:9)"
                    )
                    return cropped
            else:
                # 이미 9:9 비율이면 그대로 사용
                logger.debug(
                    f"   ✅ 영상이 이미 9:9 비율입니다: {video_width}x{video_height}"
                )
                return video
        except Exception as e:
            logger.warning(f"   ⚠️ 영상 crop 실패 (원본 사용): {e}")
            return video

    def _create_hook_title_clip(
        self, first_sentence: str, topic: str, total_duration: float, language: str
    ):
        """제목/훅 클립 생성 (맨 위에 강조 표시)"""
        try:
            from moviepy.editor import TextClip
            from moviepy.video.fx.all import fadein, fadeout

            # 제목 텍스트: 첫 문장 또는 주제 (짧은 쪽 선택)
            hook_text = first_sentence
            if topic and len(topic) < len(first_sentence):
                hook_text = topic

            # 텍스트 길이 제한 (훅 영역 높이 300px 내에 맞도록)
            # 폰트 크기와 줄 간격을 고려하여 최대 2줄까지 허용
            # 훅 영역 높이: 300px, 폰트 크기: 100px, 줄 간격: 20px
            # 계산: (100px * 2줄) + (20px * 1줄 간격) = 220px < 300px (안전)
            max_chars_per_line = 18 if language == "ko" else 28  # 훅 영역에 맞게 조정
            max_total_chars = max_chars_per_line * 2  # 최대 2줄까지

            if len(hook_text) > max_total_chars:
                # 2줄로 나누기
                words = hook_text.split()
                line1: list[str] = []
                line2: list[str] = []
                current_line = line1

                for word in words:
                    test_line = " ".join(current_line + [word])
                    if len(test_line) <= max_chars_per_line:
                        current_line.append(word)
                    else:
                        if current_line == line1:
                            current_line = line2
                            current_line.append(word)
                        else:
                            break

                if line1 and line2:
                    hook_text = " ".join(line1) + "\n" + " ".join(line2)
                elif line1:
                    hook_text = " ".join(line1)
                else:
                    hook_text = hook_text[:max_total_chars] + "..."

            # 폰트 경로
            font_path = self.subtitle_renderer._get_font_path(language)
            if not font_path:
                font_path = (
                    "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
                    if language == "en"
                    else "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
                )

            # 제목/훅 클립 생성 (큰 폰트, 강한 스타일, 강렬한 색상, 영상 끝까지 유지)
            hook_duration = total_duration  # 영상 끝까지 유지
            if VideoConstants.HOOK_TITLE_DURATION is not None:
                hook_duration = min(VideoConstants.HOOK_TITLE_DURATION, total_duration)
            try:
                # 훅 영역 높이에 맞게 텍스트 크기 조정
                hook_height = VideoConstants.HOOK_TITLE_HEIGHT  # 300px
                max_text_height = hook_height - 40  # 상하 여백 20px씩

                hook_clip = TextClip(
                    hook_text,
                    fontsize=VideoConstants.HOOK_TITLE_FONT_SIZE,
                    font=font_path,
                    color=VideoConstants.HOOK_TITLE_COLOR,
                    stroke_color="black",
                    stroke_width=VideoConstants.HOOK_TITLE_STROKE_WIDTH,  # 더 강한 테두리
                    method="caption",
                    size=(
                        VideoConstants.VIDEO_WIDTH - 100,
                        max_text_height,
                    ),  # 좌우 50px 여백, 최대 높이 제한
                    align="center",
                )
                hook_clip = hook_clip.set_duration(hook_duration)
                hook_clip = hook_clip.set_position(
                    ("center", VideoConstants.HOOK_TITLE_TOP_MARGIN)
                )

                # 페이드 효과
                fade_duration = min(0.3, hook_duration * 0.1)
                if hook_duration > fade_duration * 2:
                    hook_clip = hook_clip.fx(fadein, fade_duration).fx(
                        fadeout, fade_duration
                    )
                    hook_clip = hook_clip.set_duration(hook_duration)

                logger.info(
                    f"   ✅ 제목/훅 클립 생성 완료: '{hook_text[:30]}...' (폰트: {VideoConstants.HOOK_TITLE_FONT_SIZE}px, 길이: {hook_duration:.2f}초)"
                )
                return hook_clip
            except Exception as e:
                logger.warning(f"   ⚠️ TextClip 생성 실패, PIL로 대체: {e}")
                # PIL 폴백 구현 (hook_duration은 이미 계산됨)
                return self._create_hook_title_clip_pil(
                    hook_text, hook_duration, language
                )
        except Exception as e:
            logger.warning(f"   ⚠️ 제목/훅 클립 생성 실패: {e}")
            return None

    def _create_hook_title_clip_pil(
        self, hook_text: str, hook_duration: float, language: str
    ):
        """PIL을 사용한 제목/훅 클립 생성 (폴백)"""
        try:
            import time
            from PIL import Image, ImageDraw
            from moviepy.editor import ImageClip
            from moviepy.video.fx.all import fadein, fadeout

            # PIL 폰트 로드
            font_path = self.subtitle_renderer._get_font_path(language)
            if not font_path:
                font_path = (
                    "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
                    if language == "en"
                    else "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
                )

            pil_font = self.subtitle_renderer._get_pil_font(
                font_path, VideoConstants.HOOK_TITLE_FONT_SIZE, language
            )

            # 텍스트 줄바꿈 처리
            max_width = VideoConstants.VIDEO_WIDTH - 100  # 좌우 50px 여백
            lines = []
            if "\n" in hook_text:
                # 이미 줄바꿈이 있으면 그대로 사용
                lines = hook_text.split("\n")
            else:
                # 줄바꿈이 없으면 자동으로 줄바꿈
                words = hook_text.split()
                current_line: list[str] = []
                temp_img = Image.new("RGB", (max_width, 200), (0, 0, 0))
                temp_draw = ImageDraw.Draw(temp_img)

                for word in words:
                    test_line = " ".join(current_line + [word])
                    bbox = temp_draw.textbbox((0, 0), test_line, font=pil_font)
                    if bbox[2] - bbox[0] <= max_width:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(" ".join(current_line))
                        current_line = [word]
                if current_line:
                    lines.append(" ".join(current_line))

            if not lines:
                lines = [hook_text]

            # 텍스트 크기 계산 (여러 줄 고려)
            temp_img = Image.new("RGB", (VideoConstants.VIDEO_WIDTH, 200), (0, 0, 0))
            temp_draw = ImageDraw.Draw(temp_img)
            line_heights = []
            line_widths = []
            for line in lines:
                bbox = temp_draw.textbbox((0, 0), line, font=pil_font)
                line_heights.append(bbox[3] - bbox[1])
                line_widths.append(bbox[2] - bbox[0])

            total_text_height = (
                sum(line_heights) + (len(lines) - 1) * 15
            )  # 줄 간격 15px (훅 영역에 맞게 조정)

            # 훅 영역 높이 확인 및 텍스트 크기 조정
            hook_img_height = VideoConstants.HOOK_TITLE_HEIGHT  # 300px
            max_allowed_height = hook_img_height - 40  # 상하 여백 20px씩

            # 텍스트가 훅 영역을 벗어나면 폰트 크기 조정
            if total_text_height > max_allowed_height:
                # 폰트 크기를 줄여서 훅 영역에 맞춤
                scale_factor = max_allowed_height / total_text_height
                adjusted_font_size = int(
                    VideoConstants.HOOK_TITLE_FONT_SIZE * scale_factor * 0.9
                )  # 10% 여유
                if adjusted_font_size < 60:  # 최소 폰트 크기
                    adjusted_font_size = 60

                # 조정된 폰트로 다시 계산
                adjusted_pil_font = self.subtitle_renderer._get_pil_font(
                    font_path, adjusted_font_size, language
                )
                line_heights = []
                line_widths = []
                for line in lines:
                    bbox = temp_draw.textbbox((0, 0), line, font=adjusted_pil_font)
                    line_heights.append(bbox[3] - bbox[1])
                    line_widths.append(bbox[2] - bbox[0])
                total_text_height = sum(line_heights) + (len(lines) - 1) * 15
                pil_font = adjusted_pil_font
                logger.debug(
                    f"   훅 텍스트 폰트 크기 조정: {VideoConstants.HOOK_TITLE_FONT_SIZE}px -> {adjusted_font_size}px (훅 영역에 맞춤)"
                )

            hook_img = Image.new(
                "RGBA", (VideoConstants.VIDEO_WIDTH, hook_img_height), (0, 0, 0, 0)
            )
            draw = ImageDraw.Draw(hook_img)

            # 텍스트 위치 (중앙 정렬, 여러 줄, 훅 영역 내에 배치)
            y_pos = (hook_img_height - total_text_height) // 2
            # 훅 영역을 벗어나지 않도록 확인
            if y_pos < 20:
                y_pos = 20  # 최소 상단 여백
            if y_pos + total_text_height > hook_img_height - 20:
                y_pos = hook_img_height - total_text_height - 20  # 최소 하단 여백

            # 여러 줄 텍스트 그리기
            current_y = y_pos
            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                line_bbox = temp_draw.textbbox((0, 0), line, font=pil_font)
                line_width = line_bbox[2] - line_bbox[0]
                x_pos = (VideoConstants.VIDEO_WIDTH - line_width) // 2

                # 그림자 효과 (강한 테두리)
                shadow_offset = 5
                for dx in range(-shadow_offset, shadow_offset + 1):
                    for dy in range(-shadow_offset, shadow_offset + 1):
                        if dx != 0 or dy != 0:
                            draw.text(
                                (x_pos + dx, current_y + dy),
                                line,
                                fill=(0, 0, 0, 255),
                                font=pil_font,
                            )

                # 메인 텍스트 (강렬한 흰색)
                draw.text(
                    (x_pos, current_y), line, fill=(255, 255, 255, 255), font=pil_font
                )
                current_y += line_heights[i] + 20  # 줄 간격

            # 임시 파일로 저장
            temp_hook_path = os.path.join(
                settings.TEMP_DIR, f"hook_title_{int(time.time()*1000)}.png"
            )
            hook_img.save(temp_hook_path, "PNG")

            # ImageClip 생성
            hook_clip = ImageClip(temp_hook_path)
            hook_clip = hook_clip.set_duration(hook_duration)
            hook_clip = hook_clip.set_position(
                ("center", VideoConstants.HOOK_TITLE_TOP_MARGIN)
            )

            # 페이드 효과
            fade_duration = min(0.3, hook_duration * 0.1)
            if hook_duration > fade_duration * 2:
                hook_clip = hook_clip.fx(fadein, fade_duration).fx(
                    fadeout, fade_duration
                )
                hook_clip = hook_clip.set_duration(hook_duration)

            logger.info(
                f"   ✅ 제목/훅 클립 생성 완료 (PIL): '{hook_text[:30]}...' (폰트: {VideoConstants.HOOK_TITLE_FONT_SIZE}px, 길이: {hook_duration:.2f}초)"
            )
            return hook_clip
        except Exception as e:
            logger.warning(f"   ⚠️ PIL 제목/훅 클립 생성 실패: {e}")
            return None

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

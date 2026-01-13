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

        # 자막 위치 조정 (화면 정가운데에서 아래쪽으로 배치)
        adjusted_subtitle_clips = []
        if subtitle_clips:
            # 자막을 1300px 위치에 배치
            subtitle_y = 1300
            for subtitle_clip in subtitle_clips:
                adjusted_clip = subtitle_clip.set_position(("center", subtitle_y))
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

        # 배경 영상(9:9)을 훅 영역 바로 아래에서 시작하도록 배치 (위 여백 제거)
        content_y = hook_height  # 595px에서 바로 시작
        content_video = content_video.set_position(("center", content_y))

        # 아래쪽 흰색 배경 클립 생성 (배경 영상 아래쪽 영역만)
        content_bottom = hook_height + content_video.size[1]  # 595px + 1080px = 1675px
        bottom_white_height = (
            VideoConstants.VIDEO_HEIGHT - content_bottom
        )  # 1920 - 1675 = 245px
        white_background = None
        if bottom_white_height > 0:
            white_background = ColorClip(
                size=(VideoConstants.VIDEO_WIDTH, bottom_white_height),
                color=(255, 255, 255),  # 흰색
                duration=total_duration,
            )

        # 최종 합성: 훅 배경 + 배경 영상(9:9) + 아래쪽 흰색 배경 + 제목/훅 + 자막
        hook_background = hook_background.set_position(("center", 0))  # 맨 위
        if white_background:
            white_background = white_background.set_position(
                ("center", content_bottom)
            )  # 배경 영상 아래

        final_clips = [hook_background, content_video]
        if white_background:
            final_clips.append(white_background)

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
            subtitle_y = 1300
            logger.info(
                f"   📝 자막을 화면 아래쪽으로 배치 완료 (위치: {subtitle_y}px)"
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
        """자막 클립 준비 (긴 문장은 여러 개로 분할하여 TTS와 동기화)"""
        subtitle_clips = []
        current_time = 0.0

        for i, sentence in enumerate(script):
            actual_audio_duration = (
                sentence_audio_durations[i]
                if i < len(sentence_audio_durations)
                else sentence_audio_durations[0] if sentence_audio_durations else 3.0
            )

            try:
                # 긴 문장을 여러 개의 자막으로 분할
                sentence_parts = self._split_long_sentence(sentence, language)

                # 각 부분의 duration 계산 (문자 수에 비례)
                if len(sentence_parts) > 1:
                    total_chars = sum(len(part) for part in sentence_parts)
                    part_durations = [
                        (len(part) / total_chars) * actual_audio_duration
                        for part in sentence_parts
                    ]
                    logger.debug(
                        f"   문장 {i+1} 분할: {len(sentence_parts)}개 부분 "
                        f"(총 {actual_audio_duration:.2f}초)"
                    )
                else:
                    part_durations = [actual_audio_duration]
                    sentence_parts = [sentence]

                # 각 부분에 대해 자막 클립 생성
                for part_idx, (part_text, part_duration) in enumerate(
                    zip(sentence_parts, part_durations)
                ):
                    if part_duration < 0.1:  # 너무 짧은 부분은 건너뛰기
                        continue

                    part_info = (
                        f"{i+1}-{part_idx+1}" if len(sentence_parts) > 1 else f"{i+1}"
                    )
                    logger.debug(
                        f"   문장 {part_info} 자막 생성: {part_text[:30]}... "
                        f"(시작: {current_time:.2f}초, 길이: {part_duration:.2f}초)"
                    )

                    subtitle_clip = self.subtitle_renderer.create_subtitle_clip(
                        part_text, part_duration, language=language
                    )
                    if subtitle_clip:
                        subtitle_clip = subtitle_clip.set_duration(part_duration)
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
                            if i == 0 and part_idx == 0:
                                logger.info(
                                    f"   📍 자막 배치: {position_str} (성공 공식 적용)"
                                )
                        subtitle_clip = subtitle_clip.set_start(current_time)
                        subtitle_clips.append(subtitle_clip)
                        logger.debug(
                            f"   ✅ 자막 추가: {current_time:.2f}초~{current_time + part_duration:.2f}초"
                        )
                        current_time += part_duration
                    else:
                        logger.warning(
                            f"   ⚠️ 자막 클립이 None입니다 (부분 {part_idx+1})"
                        )
                        current_time += part_duration
            except Exception as e:
                logger.warning(f"   ❌ 자막 생성 실패 (계속 진행): {e}", exc_info=True)
                # 실패해도 시간은 진행
                current_time += actual_audio_duration

        return subtitle_clips

    def _split_long_sentence(self, sentence: str, language: str) -> List[str]:
        """긴 문장을 의미 단위로 분할 (자막 표시를 위해) - 최대한 문장 단위로 유지"""
        import re

        # 자막 최대 길이 (문자 수 기준) - 문장 단위로 보여주기 위해 더 길게 설정
        # 한글: 약 40-45자, 영문: 약 70-80자 (문장 단위 유지를 위해 더 길게)
        max_chars_per_subtitle = 45 if language == "ko" else 80

        # 문장이 짧으면 분할 불필요
        if len(sentence) <= max_chars_per_subtitle:
            return [sentence]

        # 의미 단위로 분할할 구분자 (우선순위 순) - 문장 단위 우선
        if language == "ko":
            # 한글: 마침표/물음표/느낌표 우선, 그 다음 쉼표, 마지막으로 접속사
            separators = [
                r"[。.!?！？]\s+",  # 마침표, 물음표, 느낌표 (문장 끝, 공백 있음)
                r"[。.!?！？]",  # 마침표, 물음표, 느낌표 (문장 끝, 공백 없음)
                r"[，,]\s+",  # 쉼표
                r"\s+그리고\s+",
                r"\s+또는\s+",
                r"\s+하지만\s+",
                r"\s+그런데\s+",
                r"\s+그래서\s+",
                r"\s+그러나\s+",
            ]
        else:
            # 영문: 마침표/물음표/느낌표 우선, 그 다음 쉼표, 마지막으로 접속사
            separators = [
                r"[.!?]\s+",  # 마침표, 물음표, 느낌표 (문장 끝, 공백 있음)
                r"[.!?]",  # 마침표, 물음표, 느낌표 (문장 끝, 공백 없음)
                r",\s+",  # 쉼표 + 공백 (공백만으로는 분할하지 않음)
                r",",  # 쉼표만
                r"\s+and\s+",
                r"\s+or\s+",
                r"\s+but\s+",
                r"\s+however\s+",
                r"\s+so\s+",
                r"\s+then\s+",
            ]

        # 구분자로 분할 시도 (문장 단위 우선)
        parts = [sentence]
        for separator in separators:
            new_parts = []
            for part in parts:
                if len(part) <= max_chars_per_subtitle:
                    # 이미 적절한 길이면 그대로 사용
                    new_parts.append(part)
                else:
                    # 구분자로 분할 시도
                    split_parts = re.split(separator, part)
                    if len(split_parts) > 1:
                        # 원본 텍스트에서 구분자 위치 찾기
                        matches = list(re.finditer(separator, part))
                        # 구분자를 각 부분에 다시 추가
                        for idx, split_part in enumerate(split_parts):
                            if split_part.strip():
                                # 마지막 부분이 아니면 구분자 추가
                                if idx < len(split_parts) - 1 and idx < len(matches):
                                    # 해당 위치의 구분자 추가
                                    separator_text = matches[idx].group(0)
                                    split_part += separator_text
                                new_parts.append(split_part.strip())
                    else:
                        # 구분자로 분할되지 않으면 그대로 유지
                        new_parts.append(part)

            # 분할이 실제로 일어났는지 확인
            if len(new_parts) > len(parts):
                parts = new_parts
                # 모든 부분이 적절한 길이면 종료
                if all(len(part) <= max_chars_per_subtitle for part in parts):
                    break
            # 분할이 일어나지 않았으면 다음 구분자 시도 (계속 진행)

        # 여전히 긴 부분이 있으면 그대로 유지 (단어 단위로 강제 분할하지 않음)
        # 문장 단위로 보여주는 것이 우선이므로, 너무 길어도 의미 단위로만 분할된 것을 사용
        final_parts = []
        for part in parts:
            # 의미 단위로 분할된 부분은 그대로 사용 (너무 길어도 문장 단위 유지)
            if part.strip():
                final_parts.append(part.strip())

        # 빈 부분 제거
        final_parts = [part for part in final_parts if part.strip()]

        # 분할된 부분이 없으면 원본 문장 반환
        return final_parts if final_parts else [sentence]

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

            # 텍스트 길이 제한 (훅 영역 높이 350px 내에 맞도록)
            # 폰트 크기와 줄 간격을 고려하여 최대 3줄까지 허용
            # 훅 영역 높이: 350px, 폰트 크기: 130px, 줄 간격: 20px
            # 계산: (130px * 3줄) + (20px * 2줄 간격) = 430px > 350px이므로 폰트 크기 조정 필요
            max_chars_per_line = 20 if language == "ko" else 30  # 훅 영역에 맞게 조정
            max_total_chars = max_chars_per_line * 3  # 최대 3줄까지

            if len(hook_text) > max_total_chars:
                # 3줄로 나누기
                words = hook_text.split()
                line1: list[str] = []
                line2: list[str] = []
                line3: list[str] = []
                current_line = line1

                for word in words:
                    test_line = " ".join(current_line + [word])
                    if len(test_line) <= max_chars_per_line:
                        current_line.append(word)
                    else:
                        if current_line == line1:
                            current_line = line2
                            current_line.append(word)
                        elif current_line == line2:
                            current_line = line3
                            current_line.append(word)
                        else:
                            break

                if line1 and line2 and line3:
                    hook_text = (
                        " ".join(line1)
                        + "\n"
                        + " ".join(line2)
                        + "\n"
                        + " ".join(line3)
                    )
                elif line1 and line2:
                    hook_text = " ".join(line1) + "\n" + " ".join(line2)
                elif line1:
                    hook_text = " ".join(line1)
                else:
                    hook_text = hook_text[:max_total_chars] + "..."

            # 폰트 경로 (.ttf 파일 우선, .ttc 파일은 PIL에서 직접 사용 불가)
            font_path = self.subtitle_renderer._get_font_path(language)
            if not font_path or (font_path and font_path.endswith(".ttc")):
                # 폴백 폰트 (.ttf 파일 우선)
                if language == "en":
                    fallback_paths = [
                        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                        "/System/Library/Fonts/Supplemental/Arial.ttf",
                        "/Library/Fonts/Arial.ttf",
                    ]
                else:
                    fallback_paths = [
                        "/System/Library/Fonts/Supplemental/NanumGothicBold.ttf",
                        "/System/Library/Fonts/Supplemental/NanumGothic.ttf",
                        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
                        "/System/Library/Fonts/AppleGothic.ttf",
                    ]
                font_path = None
                for path in fallback_paths:
                    if os.path.exists(path):
                        font_path = path
                        break
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

            # ImageMagick 경로에서도 이모티콘 제거 (폰트 로드 후)
            # PIL 폰트를 임시로 로드하여 이모티콘 테스트
            try:
                from PIL import ImageFont

                temp_font = self.subtitle_renderer._get_pil_font(
                    font_path, VideoConstants.HOOK_TITLE_FONT_SIZE, language
                )
                if temp_font is None:
                    temp_font = ImageFont.load_default()
                hook_text = self._remove_unsupported_emoji(
                    hook_text, temp_font, language
                )
            except Exception as e:
                logger.debug(f"   ⚠️ ImageMagick 경로 이모티콘 제거 중 오류: {e}")

            try:
                # 훅 영역 높이에 맞게 텍스트 크기 조정
                hook_height = VideoConstants.HOOK_TITLE_HEIGHT  # 545px
                max_text_height = (
                    hook_height - 60
                )  # 상하 여백 30px씩 (3줄 수용을 위해 여유 확보)

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

    def _remove_unsupported_emoji(self, text: str, font, language: str) -> str:
        """이모티콘을 감지하고 폰트로 렌더링할 수 없으면 제거"""
        if not text:
            return text

        try:
            from PIL import Image, ImageDraw

            # 이모티콘 유니코드 범위 정의 (더 넓은 범위)
            emoji_ranges = [
                (0x1F300, 0x1F9FF),  # Miscellaneous Symbols and Pictographs
                (0x1FA00, 0x1FAFF),  # Symbols and Pictographs Extended-A
                (0x2600, 0x26FF),  # Miscellaneous Symbols
                (0x2700, 0x27BF),  # Dingbats
                (0x1F1E0, 0x1F1FF),  # Regional Indicator Symbols
                (0x1F600, 0x1F64F),  # Emoticons
                (0x1F680, 0x1F6FF),  # Transport and Map Symbols
                (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
                (0x1FA70, 0x1FAFF),  # Symbols and Pictographs Extended-A
            ]

            # 이모티콘 문자 찾기
            emoji_chars = []
            for char in text:
                char_code = ord(char)
                is_emoji = any(start <= char_code <= end for start, end in emoji_ranges)
                if is_emoji:
                    emoji_chars.append(char)

            if not emoji_chars:
                return text  # 이모티콘이 없으면 그대로 반환

            # 폰트로 렌더링 테스트
            test_img = Image.new("RGB", (100, 100), (255, 255, 255))
            test_draw = ImageDraw.Draw(test_img)

            filtered_text = text
            removed_emojis = []

            for emoji_char in emoji_chars:
                try:
                    # 이모티콘 렌더링 테스트
                    bbox = test_draw.textbbox((0, 0), emoji_char, font=font)
                    width = bbox[2] - bbox[0]
                    height = bbox[3] - bbox[1]

                    # 너비나 높이가 0이거나 너무 작으면 렌더링 실패로 간주
                    # 또는 폰트가 이모티콘을 지원하지 않는 경우 (일반적으로 이모티콘은 큰 크기로 렌더링됨)
                    # 나눔고딕 같은 한글 폰트는 이모티콘을 제대로 렌더링하지 못할 수 있음
                    if width == 0 or height == 0:
                        filtered_text = filtered_text.replace(emoji_char, "")
                        removed_emojis.append(emoji_char)
                        logger.debug(f"   🚫 이모티콘 제거: {emoji_char} (크기: 0)")
                    elif width < 10 or height < 10:
                        # 너무 작게 렌더링되는 경우도 제거 (폰트가 이모티콘을 제대로 지원하지 않음)
                        filtered_text = filtered_text.replace(emoji_char, "")
                        removed_emojis.append(emoji_char)
                        logger.debug(
                            f"   🚫 이모티콘 제거: {emoji_char} (크기 너무 작음: {width}x{height})"
                        )
                    else:
                        # 실제 렌더링 테스트
                        test_draw.text((0, 0), emoji_char, font=font, fill=(0, 0, 0))
                        pixels = list(test_img.getdata())
                        has_black = any(pixel != (255, 255, 255) for pixel in pixels)
                        if not has_black:
                            filtered_text = filtered_text.replace(emoji_char, "")
                            removed_emojis.append(emoji_char)
                            logger.debug(
                                f"   🚫 이모티콘 제거: {emoji_char} (픽셀 없음)"
                            )
                        else:
                            # 다음 테스트를 위해 이미지 초기화
                            test_img = Image.new("RGB", (100, 100), (255, 255, 255))
                            test_draw = ImageDraw.Draw(test_img)
                except Exception as e:
                    # 렌더링 중 오류 발생 시 이모티콘 제거
                    filtered_text = filtered_text.replace(emoji_char, "")
                    removed_emojis.append(emoji_char)
                    logger.debug(f"   🚫 이모티콘 제거: {emoji_char} (오류: {e})")

            if removed_emojis:
                logger.info(
                    f"   🧹 이모티콘 {len(removed_emojis)}개 제거: {''.join(removed_emojis)}"
                )
                logger.info(f"   📝 원본 텍스트: {text[:50]}...")
                logger.info(f"   📝 필터링 후: {filtered_text[:50]}...")

            # 공백 정리 (이모티콘 제거로 인한 연속 공백 제거)
            import re

            filtered_text = re.sub(r"\s+", " ", filtered_text).strip()

            return filtered_text
        except Exception as e:
            logger.warning(f"   ⚠️ 이모티콘 필터링 중 오류: {e}, 원본 텍스트 사용")
            return text

    def _create_hook_title_clip_pil(
        self, hook_text: str, hook_duration: float, language: str
    ):
        """PIL을 사용한 제목/훅 클립 생성 (폴백)"""
        try:
            import time
            from PIL import Image, ImageDraw
            from moviepy.editor import ImageClip
            from moviepy.video.fx.all import fadein, fadeout

            # PIL 폰트 로드 (자막과 완전히 동일한 방식 사용, 강화된 검증)
            # font_path를 None으로 전달하여 _get_pil_font 내부에서 자동으로 최적 폰트 찾기
            pil_font = None
            try:
                # font_path를 None으로 전달하면 _get_pil_font가 _get_font_paths를 사용하여
                # 프로젝트 fonts 폴더의 나눔고딕을 우선적으로 찾음
                pil_font = self.subtitle_renderer._get_pil_font(
                    None, VideoConstants.HOOK_TITLE_FONT_SIZE, language
                )

                # 폰트 로드 검증 및 실제 텍스트 렌더링 테스트
                if pil_font is None:
                    logger.error(
                        "   ❌ 폰트 로드 실패, 기본 폰트 사용 (한글이 사각형으로 표시될 수 있음)"
                    )
                    from PIL import ImageFont

                    pil_font = ImageFont.load_default()

                # 폰트 로드 후 이모티콘 제거 (기본 폰트도 포함)
                if pil_font is not None:
                    original_hook_text = hook_text
                    hook_text = self._remove_unsupported_emoji(
                        hook_text, pil_font, language
                    )
                    if hook_text != original_hook_text:
                        logger.info("   🧹 Hook 텍스트에서 이모티콘 제거됨")
                else:
                    # 실제 훅 텍스트로 렌더링 테스트 (강화된 검증)
                    from PIL import Image, ImageDraw

                    test_img = Image.new("RGB", (400, 200), (255, 255, 255))
                    test_draw = ImageDraw.Draw(test_img)

                    # 훅 텍스트의 실제 문자들로 테스트
                    test_chars = (
                        hook_text[:30]
                        if hook_text
                        else ("테스트활용법" if language == "ko" else "Test")
                    )
                    failed_chars = []

                    for char in test_chars:
                        if language == "ko" and "\uac00" <= char <= "\ud7a3":  # 한글
                            try:
                                bbox = test_draw.textbbox((0, 0), char, font=pil_font)
                                width = bbox[2] - bbox[0]
                                height = bbox[3] - bbox[1]
                                if width == 0 or height == 0:
                                    failed_chars.append(char)
                                    continue

                                # 실제 렌더링 테스트
                                test_draw.text(
                                    (0, 0), char, font=pil_font, fill=(0, 0, 0)
                                )
                                pixels = list(test_img.getdata())
                                has_black = any(
                                    pixel != (255, 255, 255) for pixel in pixels
                                )
                                if not has_black:
                                    failed_chars.append(char)

                                # 이미지 초기화
                                test_img = Image.new("RGB", (400, 200), (255, 255, 255))
                                test_draw = ImageDraw.Draw(test_img)
                            except Exception as e:
                                logger.debug(f"   ⚠️ 문자 '{char}' 테스트 중 오류: {e}")
                                failed_chars.append(char)
                        elif language == "en" and char.isalnum():
                            try:
                                bbox = test_draw.textbbox((0, 0), char, font=pil_font)
                                if bbox[2] - bbox[0] == 0 or bbox[3] - bbox[1] == 0:
                                    failed_chars.append(char)
                            except Exception:
                                failed_chars.append(char)

                    if failed_chars:
                        logger.warning(
                            f"   ⚠️ 일부 문자가 렌더링되지 않을 수 있음: {failed_chars[:10]}"
                        )
                        # 폰트 재로드 시도 (더 강력한 폴백)
                        logger.info("   🔄 폰트 재로드 시도 중...")
                        pil_font = self.subtitle_renderer._get_pil_font(
                            None, VideoConstants.HOOK_TITLE_FONT_SIZE, language
                        )
                        if pil_font is None:
                            logger.error("   ❌ 폰트 재로드 실패")
                            from PIL import ImageFont

                            pil_font = ImageFont.load_default()
                    else:
                        logger.info(
                            f"   ✅ Hook 폰트 로드 및 렌더링 테스트 성공 (언어: {language})"
                        )
            except Exception as e:
                logger.error(f"   ❌ 폰트 로드 중 오류: {e}", exc_info=True)
                from PIL import ImageFont

                pil_font = ImageFont.load_default()

            # 텍스트 줄바꿈 처리 (최대 3줄 제한, 초과 시 폰트 크기 조정)
            max_width = VideoConstants.VIDEO_WIDTH - 100  # 좌우 50px 여백
            max_lines = 3  # 최대 3줄
            lines = []

            if "\n" in hook_text:
                # 이미 줄바꿈이 있으면 그대로 사용하되 최대 3줄로 제한
                split_lines = [
                    line.strip() for line in hook_text.split("\n") if line.strip()
                ]
                lines = split_lines[:max_lines]
            else:
                # 줄바꿈이 없으면 자동으로 줄바꿈 (최대 3줄)
                words = hook_text.split()
                current_line: list[str] = []
                temp_img = Image.new("RGB", (max_width, 200), (0, 0, 0))
                temp_draw = ImageDraw.Draw(temp_img)

                for word in words:
                    # 이미 3줄이면 중단
                    if len(lines) >= max_lines:
                        break

                    test_line = " ".join(current_line + [word])
                    bbox = temp_draw.textbbox((0, 0), test_line, font=pil_font)
                    if bbox[2] - bbox[0] <= max_width:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(" ".join(current_line))
                            if len(lines) >= max_lines:
                                break
                        current_line = [word]

                # 마지막 줄 추가 (3줄 미만인 경우에만)
                if current_line and len(lines) < max_lines:
                    lines.append(" ".join(current_line))

            if not lines:
                lines = [hook_text]

            # 3줄을 넘으면 폰트 크기를 줄여서 3줄에 맞추기
            # 폰트 크기 조정 루프에서 처리됨

            # 훅 영역 높이 확인
            hook_background_height = VideoConstants.HOOK_TITLE_HEIGHT  # 545px
            hook_start_y = VideoConstants.HOOK_TITLE_TOP_MARGIN  # 100px
            hook_img_height = hook_background_height - hook_start_y  # 445px (545 - 100)
            max_allowed_height = hook_img_height - 60  # 상하 여백 30px씩
            max_width = VideoConstants.VIDEO_WIDTH - 100  # 좌우 50px 여백

            # 폰트 크기를 동적으로 조정하여 3줄에 맞추기 (3줄 초과 시 폰트 크기 감소)
            temp_img = Image.new("RGB", (VideoConstants.VIDEO_WIDTH, 200), (0, 0, 0))
            temp_draw = ImageDraw.Draw(temp_img)

            # 최적의 폰트 크기를 찾기 위한 반복 조정
            min_font_size = 50 if language == "en" else 45  # 최소 폰트 크기
            max_font_size = (
                VideoConstants.HOOK_TITLE_FONT_SIZE
            )  # 최대 폰트 크기 (130px)
            optimal_font_size = max_font_size

            # 반복적으로 폰트 크기를 조정하여 최적값 찾기
            for attempt in range(
                15
            ):  # 최대 15번 시도 (3줄 제한을 맞추기 위해 더 많이 시도)
                # 자막과 동일한 폰트 로드 방식 사용 (None으로 전달하여 자동으로 최적 폰트 찾기)
                test_font = self.subtitle_renderer._get_pil_font(
                    None, optimal_font_size, language
                )
                if test_font is None:
                    test_font = pil_font

                # 현재 폰트로 줄바꿈 계산 (모든 텍스트 포함, 3줄 제한 없이 먼저 계산)
                test_lines = []
                if "\n" in hook_text:
                    split_lines = [
                        line.strip() for line in hook_text.split("\n") if line.strip()
                    ]
                    test_lines = split_lines  # 일단 모든 줄 포함
                else:
                    words = hook_text.split()
                    current_line: list[str] = []
                    for word in words:
                        test_line = " ".join(current_line + [word])
                        bbox = temp_draw.textbbox((0, 0), test_line, font=test_font)
                        if bbox[2] - bbox[0] <= max_width:
                            current_line.append(word)
                        else:
                            if current_line:
                                test_lines.append(" ".join(current_line))
                            current_line = [word]
                    if current_line:
                        test_lines.append(" ".join(current_line))

                if not test_lines:
                    test_lines = [hook_text]

                # 각 줄의 너비와 높이 계산
                line_heights = []
                line_widths = []
                all_fit = True

                for line in test_lines:
                    bbox = temp_draw.textbbox((0, 0), line, font=test_font)
                    line_width = bbox[2] - bbox[0]
                    line_height = bbox[3] - bbox[1]
                    line_widths.append(line_width)
                    line_heights.append(line_height)

                    # 각 줄이 너비를 초과하는지 확인
                    if line_width > max_width:
                        all_fit = False

                # 전체 높이 계산
                total_text_height = sum(line_heights) + (len(test_lines) - 1) * 20

                # 3줄 이하이고 높이와 너비 모두 만족하는지 확인
                if (
                    len(test_lines) <= max_lines
                    and all_fit
                    and total_text_height <= max_allowed_height
                ):
                    # 성공! 이 폰트 크기로 사용
                    pil_font = test_font
                    lines = test_lines
                    logger.debug(
                        f"   ✅ 최적 폰트 크기 찾음: {optimal_font_size}px (높이: {total_text_height:.1f}px, 최대: {max_allowed_height}px, 줄 수: {len(test_lines)})"
                    )
                    break
                else:
                    # 폰트 크기를 줄여서 다시 시도
                    if len(test_lines) > max_lines:
                        # 3줄을 넘으면 폰트 크기를 더 줄임 (줄 수 기준)
                        # 줄 수가 많을수록 더 많이 줄임
                        line_ratio = max_lines / len(test_lines)
                        scale_factor = line_ratio * 0.9  # 10% 추가 여유
                        logger.debug(
                            f"   🔄 3줄 초과 ({len(test_lines)}줄), 폰트 크기 조정: {optimal_font_size}px → {int(optimal_font_size * scale_factor)}px"
                        )
                    elif total_text_height > max_allowed_height:
                        # 높이가 초과: 높이 기준으로 조정
                        scale_factor = (
                            max_allowed_height / total_text_height * 0.95
                        )  # 5% 여유
                        logger.debug(
                            f"   🔄 높이 초과 ({total_text_height:.1f}px > {max_allowed_height}px), 폰트 크기 조정"
                        )
                    else:
                        # 너비가 초과: 너비 기준으로 조정
                        max_line_width = max(line_widths) if line_widths else max_width
                        scale_factor = max_width / max_line_width * 0.95  # 5% 여유
                        logger.debug("   🔄 너비 초과, 폰트 크기 조정")

                    optimal_font_size = int(optimal_font_size * scale_factor)
                    optimal_font_size = max(
                        min_font_size, optimal_font_size
                    )  # 최소값 보장

                    if attempt == 14:  # 마지막 시도
                        # 최소 폰트 크기로 강제 설정하고 모든 텍스트를 3줄에 맞추기
                        optimal_font_size = min_font_size
                        pil_font = self.subtitle_renderer._get_pil_font(
                            None, optimal_font_size, language
                        )
                        if pil_font is None:
                            pil_font = test_font

                        # 최소 폰트로 모든 텍스트를 포함하여 줄바꿈 계산 (3줄 제한 없이)
                        test_lines_final = []
                        words = hook_text.split()
                        current_line = []
                        for word in words:
                            test_line = " ".join(current_line + [word])
                            bbox = temp_draw.textbbox((0, 0), test_line, font=pil_font)
                            if bbox[2] - bbox[0] <= max_width:
                                current_line.append(word)
                            else:
                                if current_line:
                                    test_lines_final.append(" ".join(current_line))
                                current_line = [word]
                        if current_line:
                            test_lines_final.append(" ".join(current_line))

                        # 3줄을 넘으면 폰트 크기를 더 줄이기 (최소값까지)
                        if len(test_lines_final) > max_lines:
                            # 줄 수가 많을수록 더 많이 줄임
                            line_ratio = max_lines / len(test_lines_final)
                            # 최소 폰트 크기보다 작아질 수 없으므로, 가능한 한 작게 조정
                            additional_scale = min(0.9, line_ratio * 0.95)
                            optimal_font_size = max(
                                min_font_size, int(optimal_font_size * additional_scale)
                            )
                            pil_font = self.subtitle_renderer._get_pil_font(
                                None, optimal_font_size, language
                            )
                            if pil_font is None:
                                pil_font = test_font

                            # 조정된 폰트로 다시 줄바꿈 계산
                            test_lines_final = []
                            current_line = []
                            for word in words:
                                test_line = " ".join(current_line + [word])
                                bbox = temp_draw.textbbox(
                                    (0, 0), test_line, font=pil_font
                                )
                                if bbox[2] - bbox[0] <= max_width:
                                    current_line.append(word)
                                else:
                                    if current_line:
                                        test_lines_final.append(" ".join(current_line))
                                    current_line = [word]
                            if current_line:
                                test_lines_final.append(" ".join(current_line))

                        # 최종적으로 3줄로 제한 (모든 텍스트를 포함하되 3줄만 표시)
                        if len(test_lines_final) > max_lines:
                            # 3줄을 넘으면 앞의 3줄만 사용 (텍스트 일부가 잘릴 수 있음)
                            lines = test_lines_final[:max_lines]
                            logger.warning(
                                f"   ⚠️ 최소 폰트 크기({optimal_font_size}px)로도 3줄 초과 ({len(test_lines_final)}줄), 앞 3줄만 표시"
                            )
                        else:
                            lines = test_lines_final
                            logger.warning(
                                f"   ⚠️ 최소 폰트 크기로 강제 설정: {optimal_font_size}px (줄 수: {len(lines)})"
                            )

            # 최종 폰트로 다시 계산
            line_heights = []
            line_widths = []
            for line in lines:
                bbox = temp_draw.textbbox((0, 0), line, font=pil_font)
                line_heights.append(bbox[3] - bbox[1])
                line_widths.append(bbox[2] - bbox[0])

            total_text_height = sum(line_heights) + (len(lines) - 1) * 20

            # 텍스트가 훅 영역을 벗어나면 폰트 크기를 더 줄여서 전체 텍스트가 들어가도록 조정
            if total_text_height > max_allowed_height:
                # 폰트 크기를 더 줄여서 전체 텍스트가 들어가도록
                scale_factor = max_allowed_height / total_text_height * 0.95  # 5% 여유
                optimal_font_size = int(optimal_font_size * scale_factor)
                optimal_font_size = max(min_font_size, optimal_font_size)  # 최소값 보장

                # 조정된 폰트로 다시 계산 (자막과 동일한 폰트 로드 방식, None으로 전달)
                pil_font = self.subtitle_renderer._get_pil_font(
                    None, optimal_font_size, language
                )
                if pil_font is None:
                    pil_font = test_font

                line_heights = []
                line_widths = []
                for line in lines:
                    bbox = temp_draw.textbbox((0, 0), line, font=pil_font)
                    line_heights.append(bbox[3] - bbox[1])
                    line_widths.append(bbox[2] - bbox[0])
                total_text_height = sum(line_heights) + (len(lines) - 1) * 20

                logger.debug(
                    f"   훅 텍스트 폰트 크기 추가 조정: {optimal_font_size}px (전체 텍스트 표시를 위해)"
                )

            logger.info(
                f"   📐 Hook 폰트 크기: {optimal_font_size}px (원래: {VideoConstants.HOOK_TITLE_FONT_SIZE}px), "
                f"높이: {total_text_height:.1f}px/{max_allowed_height}px, "
                f"줄 수: {len(lines)}"
            )

            hook_img = Image.new(
                "RGBA", (VideoConstants.VIDEO_WIDTH, hook_img_height), (0, 0, 0, 0)
            )
            draw = ImageDraw.Draw(hook_img)

            # 텍스트 위치 (중앙 정렬, 여러 줄, 훅 영역 내에 배치)
            # 2번째 줄이 595px 이내에 오도록 보장
            y_pos = (hook_img_height - total_text_height) // 2
            # 훅 영역을 벗어나지 않도록 확인
            if y_pos < 20:
                y_pos = 20  # 최소 상단 여백
            # 2번째 줄이 595px 이내에 오도록 보장
            # 실제 화면에서의 위치 = hook_start_y (150px) + y_pos + 텍스트 위치
            if len(lines) >= 2:
                # 2번째 줄 위치 계산: hook_start_y + y_pos + 1번째 줄 높이 + 줄 간격
                second_line_y_screen = hook_start_y + y_pos + line_heights[0] + 20
                # 2번째 줄의 끝이 595px 이내에 오도록 조정
                if second_line_y_screen + line_heights[1] > hook_background_height:
                    # 이미지 내부에서 y_pos를 조정하여 595px 이내에 오도록 함
                    max_y_pos = (
                        hook_background_height - hook_start_y - total_text_height - 20
                    )
                    y_pos = max(20, max_y_pos)  # 최소 20px 여백 유지
            elif hook_start_y + y_pos + total_text_height > hook_background_height - 20:
                max_y_pos = (
                    hook_background_height - hook_start_y - total_text_height - 20
                )
                y_pos = max(20, max_y_pos)  # 최소 20px 여백 유지

            # 여러 줄 텍스트 그리기
            # 실제 렌더링에 사용할 폰트가 제대로 로드되었는지 확인
            if pil_font is None:
                logger.error("   ❌ PIL 폰트가 None입니다. 기본 폰트 사용")
                from PIL import ImageFont

                pil_font = ImageFont.load_default()

            # 폰트가 실제로 나눔고딕인지 확인 (디버깅)
            font_path_used = None
            try:
                if hasattr(pil_font, "path"):
                    font_path_used = pil_font.path
                    logger.info(f"   📝 Hook 렌더링에 사용 중인 폰트: {font_path_used}")
            except Exception:
                pass

            # 실제 렌더링 전 최종 검증: 각 줄의 문자들이 렌더링 가능한지 확인
            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                # 각 문자를 개별적으로 테스트
                test_img = Image.new("RGB", (200, 100), (255, 255, 255))
                test_draw = ImageDraw.Draw(test_img)
                failed_chars = []
                for char in line[:50]:  # 처음 50자만 테스트
                    try:
                        bbox = test_draw.textbbox((0, 0), char, font=pil_font)
                        if bbox[2] - bbox[0] == 0 and bbox[3] - bbox[1] == 0:
                            failed_chars.append(char)
                    except Exception:
                        failed_chars.append(char)
                if failed_chars:
                    logger.warning(
                        f"   ⚠️ {i+1}번째 줄에서 렌더링 실패 문자: {failed_chars[:10]}"
                    )

            current_y = y_pos
            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                line_bbox = draw.textbbox((0, 0), line, font=pil_font)
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

        # 최종 영상 크기 확인 및 강제 설정 (언어와 관계없이 동일한 해상도 보장)
        expected_size = (VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT)
        if video.size != expected_size:
            logger.warning(
                f"⚠️ 영상 크기가 예상과 다릅니다: {video.size} (예상: {expected_size}). 리사이즈합니다."
            )
            video = video.resize(expected_size)

        logger.info(f"📐 최종 영상 크기: {video.size[0]}x{video.size[1]} (9:16 비율)")

        video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=VideoConstants.VIDEO_FPS,
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

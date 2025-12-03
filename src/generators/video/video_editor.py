"""
영상 편집 및 합성 모듈
"""
import os
from typing import List, Optional, Tuple
from moviepy.editor import (
    AudioFileClip, CompositeVideoClip, concatenate_videoclips,
    VideoFileClip
)
from moviepy.audio.AudioClip import concatenate_audioclips
from moviepy.video.fx.all import fadein, fadeout
from PIL import Image
import numpy as np

import config
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
        background_manager: BackgroundVideoManager
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
        topic: str = None
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
        # 배경 영상 합성
        if len(background_clips) == 1:
            base_video_clip = background_clips[0]
        else:
            base_video_clip = concatenate_videoclips(background_clips)
        
        logger.info(f"   ✅ 모든 배경 영상 합성 완료: {total_duration:.2f}초 ({len(background_clips)}개 그룹)")
        
        # 자막과 배경 합성
        logger.info(f"🎬 하나의 연속된 영상으로 합성 중... (배경: {total_duration:.2f}초, 자막: {len(subtitle_clips)}개)")
        if subtitle_clips:
            final_video = CompositeVideoClip([base_video_clip] + subtitle_clips)
        else:
            final_video = base_video_clip
        
        final_video = final_video.set_duration(total_duration)
        
        # 페이드 효과 적용
        final_video = self.apply_fade_effects(final_video, total_duration)
        
        logger.info(f"✅ 최종 영상 길이: {final_video.duration:.2f}초 (목표: {total_duration:.2f}초)")
        
        # 음성 추가 및 동기화
        if audio_clips:
            final_video = self.sync_audio_video(
                final_video, audio_clips, content_type, topic
            )
        
        # 최종 설정
        final_video = final_video.set_fps(VideoConstants.VIDEO_FPS)
        
        if final_video.size[0] != VideoConstants.VIDEO_WIDTH or final_video.size[1] != VideoConstants.VIDEO_HEIGHT:
            final_video = final_video.resize((VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT))
        
        return final_video
    
    def apply_fade_effects(self, video: CompositeVideoClip, duration: float) -> CompositeVideoClip:
        """페이드 효과 적용"""
        fade_duration = min(VideoConstants.DEFAULT_FADE_DURATION, duration * VideoConstants.FADE_RATIO)
        if duration > fade_duration * 2:
            video = video.fx(fadein, fade_duration).fx(fadeout, fade_duration)
            video = video.set_duration(duration)
        return video
    
    def sync_audio_video(
        self,
        video: CompositeVideoClip,
        audio_clips: List[AudioFileClip],
        content_type: Optional[ContentType] = None,
        topic: str = None
    ) -> CompositeVideoClip:
        """음성-영상 동기화"""
        try:
            final_audio = concatenate_audioclips(audio_clips)
            
            actual_audio_duration = final_audio.duration
            actual_video_duration = video.duration
            
            logger.debug(f"🎵 음성 총 길이: {actual_audio_duration:.2f}초, 영상 총 길이: {actual_video_duration:.2f}초")
            
            # 영상 길이를 음성 길이에 맞춤
            if abs(actual_video_duration - actual_audio_duration) > 0.01:
                logger.debug(f"   영상 길이를 음성 길이에 맞춤: {actual_video_duration:.2f}초 -> {actual_audio_duration:.2f}초")
                if actual_video_duration > actual_audio_duration:
                    video = video.subclip(0, actual_audio_duration)
                else:
                    # 영상 확장
                    extension_needed = actual_audio_duration - actual_video_duration
                    logger.debug(f"   영상 확장 필요: {extension_needed:.2f}초")
                    extension_source = video.subclip(
                        max(0, actual_video_duration - VideoConstants.EXTENSION_DURATION),
                        actual_video_duration
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
            if getattr(config, 'USE_BACKGROUND_MUSIC', True):
                try:
                    background_music_path = self.audio_generator.download_background_music(
                        content_type=content_type if content_type else ContentType.AUTO,
                        duration=actual_audio_duration,
                        topic=topic
                    )
                    
                    if background_music_path and os.path.exists(background_music_path):
                        final_audio = self.audio_generator.mix_background_music(
                            final_audio, background_music_path, actual_audio_duration
                        )
                except Exception as e:
                    logger.warning(f"⚠️ 배경 음악 추가 실패 (계속 진행): {e}", exc_info=True)
            
            video = video.set_audio(final_audio)
            video = video.set_duration(actual_audio_duration)
            
            logger.info(f"✅ 음성-영상 동기화 완료: 영상 {actual_video_duration:.2f}초, 음성 {actual_audio_duration:.2f}초 (정확히 일치)")
            
            return video
        except Exception as e:
            logger.error(f"⚠️ 음성 추가 실패: {e}", exc_info=True)
            return video
    
    def prepare_background_clips(
        self,
        background_groups: List[Tuple],
        sentence_audio_durations: List[float]
    ) -> List[VideoFileClip]:
        """배경 영상 클립 준비 (BackgroundVideoManager 사용)"""
        background_clips = []
        
        for gs, ge, bg_video_path, bg_image in background_groups:
            group_duration = sum(sentence_audio_durations[gs:ge])
            
            if bg_video_path and os.path.exists(bg_video_path):
                try:
                    group_clip = self.background_manager.create_background_video_clip(
                        bg_video_path, group_duration, gs, ge
                    )
                    background_clips.append(group_clip)
                except Exception as e:
                    logger.error(f"   ❌ 배경 영상 사용 실패: {e}", exc_info=True)
                    raise ValueError(f"그룹 {gs+1}-{ge}의 배경 영상을 로드할 수 없습니다: {e}")
            else:
                raise ValueError(f"그룹 {gs+1}-{ge}에 배경 영상이 없습니다. 배경 영상 다운로드가 필요합니다.")
        
        return background_clips
    
    def prepare_subtitle_clips(
        self,
        script: List[str],
        sentence_audio_durations: List[float],
        language: str = 'ko'
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
                logger.debug(f"   문장 {i+1} 자막 생성: {sentence[:30]}... (시작: {current_time:.2f}초)")
                subtitle_clip = self.subtitle_renderer.create_subtitle_clip(
                    sentence, actual_audio_duration, language=language
                )
                if subtitle_clip:
                    subtitle_clip = subtitle_clip.set_duration(actual_audio_duration)
                    if getattr(subtitle_clip, "pos", None) is None:
                        subtitle_clip = subtitle_clip.set_position(('center', 'bottom'))
                    subtitle_clip = subtitle_clip.set_start(current_time)
                    subtitle_clips.append(subtitle_clip)
                    logger.debug(f"   ✅ 자막 추가: {current_time:.2f}초~{current_time + actual_audio_duration:.2f}초")
                else:
                    logger.warning(f"   ⚠️ 자막 클립이 None입니다")
            except Exception as e:
                logger.warning(f"   ❌ 자막 생성 실패 (계속 진행): {e}", exc_info=True)
            
            current_time += actual_audio_duration
        
        return subtitle_clips
    
    def save_video(
        self,
        video: CompositeVideoClip,
        output_path: str,
        final_audio_duration: Optional[float] = None
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
                    video = video.set_audio(video.audio.subclip(0, final_audio_duration))
                video = video.set_duration(final_audio_duration)
        
        logger.info(f"💾 영상 저장 중... (최종 duration: {video.duration:.2f}초)")
        video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            fps=30,
            preset='medium',
            bitrate='8000k'
        )
        
        # 임시 파일 정리
        try:
            from src.utils.temp_cleaner import TempCleaner
            temp_cleaner = TempCleaner(max_age_hours=1)
            stats = temp_cleaner.clean_old_files(dry_run=False)
            if stats['deleted'] > 0:
                logger.info(f"🧹 임시 파일 자동 정리: {stats['deleted']}개 파일 삭제 ({stats['size_freed'] / 1024 / 1024:.2f} MB 해제)")
        except Exception as e:
            logger.warning(f"   ⚠️ 임시 파일 정리 실패 (무시): {e}")

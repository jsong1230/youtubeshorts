"""
영상 합성 및 편집 모듈 (MoviePy 기반)
"""
import os
import re
import random
import time
import requests
from typing import Optional, List, Tuple, Dict
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, TextClip, 
    CompositeVideoClip, concatenate_videoclips, CompositeAudioClip
)
from moviepy.video.fx.all import fadein, fadeout

import config
from .video_constants import VideoConstants
from .content_type import ContentType
from .audio_generator import AudioGenerator
from src.utils.retry_decorator import retry

class VideoCompositor:
    """영상 합성 및 편집 클래스"""
    
    def __init__(
        self, 
        audio_generator: AudioGenerator,
        media_downloader=None, # MediaDownloader instance
        openai_client=None
    ):
        self.audio_generator = audio_generator
        self.media_downloader = media_downloader
        self.openai_client = openai_client

    @retry(max_retries=3, base_delay=1, exceptions=(requests.RequestException, ConnectionError, TimeoutError))
    def _http_get_with_retry(self, url: str, **kwargs) -> requests.Response:
        """HTTP GET request with automatic retry on transient failures."""
        timeout = kwargs.pop('timeout', 10)
        response = requests.get(url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response

    def create_video_from_script(
        self,
        script: list,
        topic: str,
        duration: int,
        output_filename: str = None,
        content_type: ContentType = None,
        language: str = 'ko'
    ) -> str:
        """
        스크립트로부터 영상 생성
        """
        # 출력 파일명 생성
        if not output_filename:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"shorts_{timestamp}.mp4"
        
        output_path = os.path.join(config.VIDEO_OUTPUT_DIR, output_filename)
        
        # 각 문장별 클립 생성
        clips = []
        # 각 문장별로 음성 생성 및 실제 길이 측정
        sentence_audio_durations = []
        audio_clips = []
        
        print(f"📊 영상 구성: {len(script)}개 문장")
        print("🔊 음성 생성 및 길이 측정 중...")
        
        for i, sentence in enumerate(script):
            content_type_str = content_type.value if content_type else None
            audio_path = self.audio_generator.generate_audio(sentence, i, content_type=content_type_str, language=language)
            if audio_path and os.path.exists(audio_path):
                audio_clip = AudioFileClip(audio_path)
                actual_duration = audio_clip.duration
                sentence_audio_durations.append(actual_duration)
                audio_clips.append(audio_clip)
                print(
                    f"   문장 {i+1}: {actual_duration:.2f}초 - {sentence[:30]}...")
            else:
                # 음성 생성 실패 시 기본 duration 사용
                default_duration = duration / len(script)
                sentence_audio_durations.append(default_duration)
                print(
                    f"   문장 {i+1}: 음성 생성 실패, 기본 길이 사용 ({default_duration:.2f}초)")
        
        # 실제 음성 길이 합계
        total_audio_duration = sum(sentence_audio_durations)
        print(f"📏 실제 음성 총 길이: {total_audio_duration:.2f}초")
        
        # 음성 길이를 기준으로 영상 길이 조정 (60초 초과 방지)
        max_safe_duration = 58  # 60초 초과 방지를 위한 안전 마진
        if total_audio_duration > max_safe_duration:
            print(
                f"⚠️ 음성 길이가 {max_safe_duration}초를 초과합니다. 마지막 문장들을 제거하여 {max_safe_duration}초 이내로 맞춥니다.")
            
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
                print(
                    f"   문장 제거: '{removed_sentence[:30]}...' ({removed_audio_duration:.2f}초)")
            
            duration = min(total_audio_duration, max_safe_duration)
            print(
                f"   최종 음성 길이: {total_audio_duration:.2f}초 ({removed_count}개 문장 제거됨)")
        elif total_audio_duration > duration:
            # duration이 max_safe_duration 이하인 경우에만 조정
            duration = min(total_audio_duration, max_safe_duration)
            print(
                f"   영상 길이를 음성 길이에 맞춤: {duration:.2f}초 (최대 {max_safe_duration}초)")
        elif abs(total_audio_duration - duration) > 1.0:
            # 목표 duration과 차이가 있더라도 실제 음성 길이를 그대로 사용
            print(
                f"   duration 정보: 실제 음성 {total_audio_duration:.2f}초, 목표 {duration}초 (스케일링하지 않음)")

        # 배경 미디어 그룹핑: 여러 배경 영상을 스크립트와 연동
        background_groups = []
        group_size = VideoConstants.BACKGROUND_GROUP_SIZE  # 배경 변경 주기 (문장 수)
        use_background_video = getattr(config, 'USE_BACKGROUND_VIDEO', True)

        # 각 그룹에서 사용할 배경 영상의 시작 시간을 추적 (순차 재생용)
        video_start_times = {}  # {bg_video_path: current_start_time}
        downloaded_video_ids = set()  # 이미 다운로드한 영상 ID 추적 (중복 방지)
        
        for i in range(0, len(script), group_size):
            group_end = min(i + group_size, len(script))
            group_sentence = script[i]
            group_duration = sum(sentence_audio_durations[i:group_end])
            
            # 배경 영상 다운로드 시도 (다양한 키워드로 재시도)
            bg_video_path = None
            if use_background_video and config.PEXELS_API_KEY:
                # 재시도 전략: 문장 키워드 -> 주제 키워드 -> 일반 키워드
                retry_keywords = []
                
                # 1차: 문장 키워드
                if self.media_downloader:
                    sentence_keywords = self.media_downloader.extract_keywords(group_sentence)
                    if sentence_keywords:
                        retry_keywords.append(sentence_keywords[0])
                
                # 2차: 주제 키워드
                if topic and self.media_downloader:
                    topic_keywords = self.media_downloader.extract_keywords(topic)
                    if topic_keywords and topic_keywords[0] not in retry_keywords:
                        retry_keywords.append(topic_keywords[0])
                
                # 3차: 주제 카테고리별 특화 키워드
                topic_lower = (topic or "").lower()
                category_keywords = []
                
                # 재태크 관련 키워드
                if any(word in topic_lower for word in ["money", "save", "invest", "budget", "finance", "wealth", "spending", "expense", "subscription", "emergency", "fund", "401k", "roth", "ira"]):
                    category_keywords.extend(["money", "finance", "investment", "savings", "budget", "wealth", "business"])
                
                # 생산성 관련 키워드
                elif any(word in topic_lower for word in ["routine", "productivity", "focus", "workspace", "morning", "habit", "automate", "ai"]):
                    category_keywords.extend(["productivity", "workspace", "morning", "routine", "focus", "office", "desk"])
                
                # 자기계발 관련 키워드
                elif any(word in topic_lower for word in ["growth", "motivation", "success", "achievement", "goal", "mindset", "transform", "change"]):
                    category_keywords.extend(["growth", "motivation", "success", "achievement", "goal", "inspiration", "mindset"])
                
                # 생활/정리 관련 키워드
                elif any(word in topic_lower for word in ["declutter", "organize", "closet", "minimalism", "home", "lifestyle", "clean"]):
                    category_keywords.extend(["home", "lifestyle", "minimalism", "organization", "declutter", "interior"])
                
                # 기본 키워드 (카테고리 매칭 실패 시)
                if not category_keywords:
                    category_keywords = ["home", "lifestyle", "indoor", "cozy", "warm", "nature", "abstract", "cinematic"]
                
                retry_keywords.extend(category_keywords)
                
                for retry_idx, keyword in enumerate(retry_keywords[:5]):  # 최대 5개 키워드 시도
                    bg_video_path, video_id = self._download_video_for_sentence(
                        group_sentence,
                        i,
                        group_duration,
                        topic=topic,
                        exclude_video_ids=downloaded_video_ids,
                        force_keyword=keyword if retry_idx > 0 else None  # 첫 번째는 자동, 이후는 강제 키워드
                    )
                    if bg_video_path and video_id:
                        downloaded_video_ids.add(video_id)  # 영상 ID 추가
                        break
                    elif retry_idx < len(retry_keywords) - 1:
                        print(f"   ⚠️ 배경 영상 다운로드 실패 ({keyword}), 다음 키워드 시도...")
                
                if not bg_video_path:
                    print(f"   ⚠️ 배경 영상 다운로드 최종 실패 (모든 키워드 시도 완료)")
                    # 배경 영상이 없으면 에러 발생 (임의 이미지 생성 금지)
                    raise ValueError(f"그룹 {i+1}-{group_end}에 대한 배경 영상을 다운로드할 수 없습니다. 모든 키워드 시도 실패.")
            
            # 배경 영상이 있으면 시작 시간 초기화
            if bg_video_path and bg_video_path not in video_start_times:
                video_start_times[bg_video_path] = 0.0
            
            background_groups.append((i, group_end, bg_video_path, None))  # bg_image는 항상 None
            media_type = "영상" if bg_video_path else "이미지"
            print(
                f"   배경 미디어 그룹 {len(background_groups)}: 문장 {i+1}-{group_end} ({media_type}) - {group_sentence[:30]}...)")

        # 배경 영상 준비: 각 그룹의 배경 영상을 시간에 맞춰서 하나의 연속된 클립으로 합성
        total_video_duration = sum(sentence_audio_durations)
        base_video_clip = None
        subtitle_clips = []  # 모든 자막 클립을 시간에 맞춰 저장
        
        # 각 그룹의 배경 영상을 시간에 맞춰서 처리
        background_clips = []
        current_time = 0.0
        
        for gs, ge, bg_video_path, bg_image in background_groups:
            group_duration = sum(sentence_audio_durations[gs:ge])
            
            if bg_video_path and os.path.exists(bg_video_path):
                try:
                    print(f"   📹 배경 영상 로드 (그룹 {gs+1}-{ge}): {bg_video_path}")
                    source_video = VideoFileClip(bg_video_path)
                    source_duration = source_video.duration
                    print(f"   원본 영상 길이: {source_duration:.2f}초, 그룹 길이: {group_duration:.2f}초")
                    
                    # 배경 영상을 리사이즈
                    source_video = source_video.resize((VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT))
                    
                    # 배경 영상이 짧으면 마지막 프레임을 freeze해서 확장
                    if source_duration < group_duration:
                        # 마지막 프레임 가져오기
                        last_frame = source_video.get_frame(source_duration - 0.1)
                        from PIL import Image
                        import numpy as np
                        last_frame_img = Image.fromarray(last_frame.astype('uint8'))
                        
                        # 마지막 프레임을 ImageClip으로 만들어서 확장
                        remaining_duration = group_duration - source_duration
                        last_frame_clip = ImageClip(np.array(last_frame_img)).set_duration(remaining_duration)
                        last_frame_clip = last_frame_clip.resize((VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT))
                        
                        # 배경 영상과 마지막 프레임 연결
                        group_clip = concatenate_videoclips([source_video, last_frame_clip])
                        source_video.close()
                        print(f"   ✅ 배경 영상 + 마지막 프레임 확장: {source_duration:.2f}초 + {remaining_duration:.2f}초 = {group_duration:.2f}초")
                    else:
                        # 배경 영상이 충분히 긴 경우
                        group_clip = source_video.subclip(0, group_duration)
                        source_video.close()
                        print(f"   ✅ 배경 영상 준비 완료: {group_duration:.2f}초")
                    
                    background_clips.append(group_clip)
                except Exception as e:
                    print(f"   ❌ 배경 영상 사용 실패: {e}")
                    import traceback
                    traceback.print_exc()
                    raise ValueError(f"그룹 {gs+1}-{ge}의 배경 영상을 로드할 수 없습니다: {e}")
            
            # 배경 영상이 없으면 에러 발생 (임의 이미지 생성 금지)
            if bg_video_path is None or not os.path.exists(bg_video_path):
                raise ValueError(f"그룹 {gs+1}-{ge}에 배경 영상이 없습니다. 배경 영상 다운로드가 필요합니다.")
            
            current_time += group_duration
        
        # 모든 그룹의 배경 영상을 하나의 연속된 클립으로 합성
        if background_clips:
            if len(background_clips) == 1:
                base_video_clip = background_clips[0]
            else:
                base_video_clip = concatenate_videoclips(background_clips)
            print(f"   ✅ 모든 배경 영상 합성 완료: {total_video_duration:.2f}초 ({len(background_clips)}개 그룹)")
        else:
            # 배경이 전혀 없는 경우 (예외 상황) - 에러 발생
            raise ValueError("배경 영상이 하나도 없습니다. 배경 영상 다운로드가 필요합니다.")
        
        # 각 문장의 자막을 시간에 맞춰서 생성
        current_time = 0.0
        for i, sentence in enumerate(script):
            actual_audio_duration = sentence_audio_durations[i] if i < len(sentence_audio_durations) else sentence_audio_durations[0] if sentence_audio_durations else 3.0
            
            try:
                print(f"   문장 {i+1} 자막 생성: {sentence[:30]}... (시작: {current_time:.2f}초)")
                subtitle_clip = self._create_subtitle_clip(
                    sentence, actual_audio_duration, language=language)
                if subtitle_clip:
                    subtitle_clip = subtitle_clip.set_duration(actual_audio_duration)
                    if getattr(subtitle_clip, "pos", None) is None:
                        subtitle_clip = subtitle_clip.set_position(('center', 'bottom'))
                    subtitle_clip = subtitle_clip.set_start(current_time)
                    subtitle_clips.append(subtitle_clip)
                    print(f"   ✅ 자막 추가: {current_time:.2f}초~{current_time + actual_audio_duration:.2f}초")
                else:
                    print(f"   ⚠️ 자막 클립이 None입니다")
            except Exception as e:
                print(f"   ❌ 자막 생성 실패 (계속 진행): {e}")
                import traceback
                traceback.print_exc()
            
            current_time += actual_audio_duration
        
        # 하나의 CompositeVideoClip으로 합성
        print(f"🎬 하나의 연속된 영상으로 합성 중... (배경: {total_video_duration:.2f}초, 자막: {len(subtitle_clips)}개)")
        if subtitle_clips:
            final_video = CompositeVideoClip([base_video_clip] + subtitle_clips)
        else:
            final_video = base_video_clip
        
        final_video = final_video.set_duration(total_video_duration)
        
        # 페이드 효과 적용
        fade_duration = min(VideoConstants.DEFAULT_FADE_DURATION, total_video_duration * VideoConstants.FADE_RATIO)
        if total_video_duration > fade_duration * 2:
            final_video = final_video.fx(fadein, fade_duration).fx(fadeout, fade_duration)
            final_video = final_video.set_duration(total_video_duration)

        print(f"✅ 최종 영상 길이: {final_video.duration:.2f}초 (목표: {total_video_duration:.2f}초)")
        
        # 음성 추가
        if audio_clips:
            try:
                from moviepy.audio.AudioClip import concatenate_audioclips
                final_audio = concatenate_audioclips(audio_clips)
                
                actual_audio_duration = final_audio.duration
                actual_video_duration = final_video.duration

                print(
                    f"🎵 음성 총 길이: {actual_audio_duration:.2f}초, 영상 총 길이: {actual_video_duration:.2f}초")

                if abs(actual_video_duration - actual_audio_duration) > 0.01:
                    print(
                        f"   영상 길이를 음성 길이에 맞춤: {actual_video_duration:.2f}초 -> {actual_audio_duration:.2f}초")
                    if actual_video_duration > actual_audio_duration:
                        final_video = final_video.subclip(
                            0, actual_audio_duration)
                    else:
                        extension_needed = actual_audio_duration - actual_video_duration
                        print(f"   영상 확장 필요: {extension_needed:.2f}초")
                        extension_source = final_video.subclip(
                            max(0, actual_video_duration - VideoConstants.EXTENSION_DURATION), actual_video_duration)
                        extension_clips = []
                        remaining = extension_needed
                        while remaining > 0.01:
                            ext_dur = min(VideoConstants.EXTENSION_DURATION, remaining)
                            ext_clip = extension_source.subclip(
                                0, VideoConstants.EXTENSION_DURATION).set_duration(ext_dur)
                            extension_clips.append(ext_clip)
                            remaining -= ext_dur
                        if extension_clips:
                            extension_video = concatenate_videoclips(
                                extension_clips, method="compose")
                            final_video = concatenate_videoclips(
                                [final_video, extension_video], method="compose")
                    final_video = final_video.set_duration(
                        actual_audio_duration)
                    actual_video_duration = actual_audio_duration
                
                max_safe_duration = VideoConstants.MAX_DURATION
                if actual_video_duration > max_safe_duration:
                    actual_video_duration = max_safe_duration
                    final_video = final_video.subclip(0, actual_video_duration)
                
                # 배경 음악 추가 (AudioGenerator 사용)
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
                        print(f"⚠️ 배경 음악 추가 실패 (계속 진행): {e}")
                        import traceback
                        traceback.print_exc()
                
                final_video = final_video.set_audio(final_audio)
                final_video = final_video.set_duration(actual_audio_duration)
                
                print(
                    f"✅ 음성-영상 동기화 완료: 영상 {actual_video_duration:.2f}초, 음성 {actual_audio_duration:.2f}초 (정확히 일치)")
            except Exception as e:
                print(f"⚠️ 음성 추가 실패: {e}")
                import traceback
                traceback.print_exc()
        
        final_video = final_video.set_fps(VideoConstants.VIDEO_FPS)
        
        if final_video.size[0] != VideoConstants.VIDEO_WIDTH or final_video.size[1] != VideoConstants.VIDEO_HEIGHT:
            final_video = final_video.resize((VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT))
        
        # 영상 저장 전 최종 duration 확인
        if audio_clips and 'final_audio' in locals():
            actual_audio_duration = final_audio.duration
            actual_video_duration = final_video.duration
            if abs(actual_video_duration - actual_audio_duration) > 0.01:
                if actual_video_duration > actual_audio_duration:
                    final_video = final_video.subclip(0, actual_audio_duration)
                else:
                    final_video = final_video.set_duration(
                        actual_audio_duration)
                final_video = final_video.set_audio(final_audio)
                final_video = final_video.set_duration(actual_audio_duration)
        else:
            actual_total_duration = sum(sentence_audio_durations)
            if abs(final_video.duration - actual_total_duration) > 0.01:
                final_video = final_video.subclip(0, actual_total_duration)
                final_video = final_video.set_duration(actual_total_duration)
        
        print(f"💾 영상 저장 중... (최종 duration: {final_video.duration:.2f}초)")
        final_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            fps=30,
            preset='medium',
            bitrate='8000k'
        )
        
        # 임시 파일 정리
        for i in range(len(script)):
            temp_frame = os.path.join(config.TEMP_DIR, f"frame_{i}.png")
            if os.path.exists(temp_frame):
                os.remove(temp_frame)
            temp_audio = os.path.join(config.TEMP_DIR, f"audio_{i}.mp3")
            if os.path.exists(temp_audio):
                os.remove(temp_audio)
            temp_bg_video = os.path.join(config.TEMP_DIR, f"bg_video_{i}.mp4")
            if os.path.exists(temp_bg_video):
                os.remove(temp_bg_video)
        
        return output_path

    def _download_video_for_sentence(
        self,
        sentence: str,
        index: int,
        duration: float,
        topic: str = None,
        exclude_video_ids: set = None,
        force_keyword: str = None
    ) -> tuple:
        """문장에 맞는 배경 영상 다운로드
        
        Args:
            force_keyword: 강제로 사용할 키워드 (재시도 시 사용)
        
        Returns:
            tuple: (bg_video_path, video_id) 또는 (None, None)
        """
        if not self.media_downloader:
            return None, None
            
        try:
            # force_keyword가 있으면 우선 사용
            if force_keyword:
                keyword = force_keyword
                english_keyword = self.media_downloader.translate_keyword_to_english(force_keyword)
                print(f"🔄 대체 키워드 사용: {force_keyword} -> {english_keyword}")
            else:
                # 주제에서 키워드 추출 (우선 사용)
                topic_keyword = None
                if topic:
                    topic_keywords = self.media_downloader.extract_keywords(topic)
                    if topic_keywords:
                        topic_keyword = topic_keywords[0]
                        topic_english = self.media_downloader.translate_keyword_to_english(
                            topic_keyword)
                        print(
                            f"🎯 주제 키워드 우선 사용: {topic} -> {topic_keyword} -> {topic_english}")

                # 문장에서 키워드 추출
                sentence_keywords = self.media_downloader.extract_keywords(sentence)
                sentence_keyword = sentence_keywords[0] if sentence_keywords else None

                if sentence_keyword:
                    keyword = sentence_keyword
                    english_keyword = self.media_downloader.translate_keyword_to_english(sentence_keyword)
                    print(f"🎯 문장 키워드 우선 사용: {sentence} -> {keyword} -> {english_keyword}")
                elif topic_keyword:
                    keyword = topic_keyword
                    english_keyword = self.media_downloader.translate_keyword_to_english(topic_keyword)
                    print(f"⚠️ 문장 키워드 없음, 주제 키워드 사용: {topic} -> {keyword}")
                else:
                    if topic:
                        keyword = topic
                        english_keyword = self.media_downloader.translate_keyword_to_english(topic)
                    else:
                        keyword = "nature"
                        english_keyword = "nature"
            
            print(f"🎬 배경 영상 다운로드 시도: {keyword} -> {english_keyword}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' }
            
            if config.PEXELS_API_KEY:
                try:
                    pexels_video_url = f"https://api.pexels.com/videos/search?query={english_keyword}&per_page=20&orientation=portrait"
                    pexels_headers = {
                        **headers,
                        'Authorization': config.PEXELS_API_KEY
                    }
                    
                    response = self._http_get_with_retry(
                        pexels_video_url, headers=pexels_headers)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('videos') and len(data['videos']) > 0:
                            # exclude_video_ids가 None이면 빈 세트로 초기화
                            if exclude_video_ids is None:
                                exclude_video_ids = set()

                            video_data = None
                            for video in data['videos']:
                                video_id = video.get('id', 0)
                                # 이미 다운로드한 영상 ID는 건너뛰기
                                if video_id in exclude_video_ids:
                                    continue
                                
                                duration_sec = video.get('duration', 0)
                                if duration_sec < 10: continue
                                
                                files = video.get('video_files', [])
                                best_file = None
                                min_diff = float('inf')
                                
                                for file in files:
                                    if file.get('quality') == 'hd' and file.get('width', 0) < file.get('height', 0):
                                        diff = abs(file.get('height', 0) - 1920)
                                        if diff < min_diff:
                                            min_diff = diff
                                            best_file = file
                                
                                if best_file:
                                    video_data = {
                                        'id': video_id,
                                        'url': best_file.get('link'),
                                        'duration': duration_sec
                                    }
                                    break
                            
                            if video_data:
                                video_url = video_data['url']
                                video_id = video_data['id']
                                bg_video_path = os.path.join(
                                    config.TEMP_DIR, f"bg_video_{index}_{video_id}.mp4")
                                
                                video_response = self._http_get_with_retry(video_url, stream=True)
                                if video_response.status_code == 200:
                                    with open(bg_video_path, 'wb') as f:
                                        for chunk in video_response.iter_content(chunk_size=1024):
                                            if chunk:
                                                f.write(chunk)
                                    print(f"✅ Pexels 배경 영상 다운로드 성공: {english_keyword} (ID: {video_id})")
                                    return bg_video_path, video_id
                except Exception as e:
                    print(f"   Pexels API 실패: {e}")
            
            return None, None
        except Exception as e:
            print(f"⚠️ 배경 영상 다운로드 실패: {e}")
            return None, None

    def _draw_text_on_image(
        self,
        image: Image.Image,
        text: str,
        language: str = 'ko') -> Image.Image:
        """이미지에 텍스트 그리기"""
        base_font_size = VideoConstants.BASE_FONT_SIZE
        font = None
        font_path_used = None
        
        font_paths = []
        if language == 'en':
            font_paths = [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Supplemental/Helvetica.ttc",
            ]
        else:
            font_paths = [
            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
            "/System/Library/Fonts/AppleGothic.ttf",
                "/System/Library/Fonts/Supplemental/NanumGothic.ttf",
            "/Library/Fonts/AppleGothic.ttf",
            ]

        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, base_font_size)
                    font_path_used = font_path
                    break
            except BaseException:
                continue
        
        if font is None:
            if language == 'en':
                try:
                    font = ImageFont.truetype(
                        "/System/Library/Fonts/Supplemental/Arial Bold.ttf", base_font_size)
                    font_path_used = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
                except BaseException:
                    font = ImageFont.load_default()
            else:
                try:
                    font = ImageFont.truetype(
                        "/System/Library/Fonts/Supplemental/AppleGothic.ttf", base_font_size)
                    font_path_used = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
                except BaseException:
                    font = ImageFont.load_default()
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        max_width = VideoConstants.SUBTITLE_MAX_WIDTH
        lines = self._wrap_text(text, font, max_width, base_font_size)
        
        if len(lines) > 3 and font_path_used:
            for size in VideoConstants.FONT_SIZES:
                try:
                    font = ImageFont.truetype(font_path_used, size)
                    lines = self._wrap_text(text, font, max_width, size)
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
        
        total_height = sum(line_heights) + \
        (len(lines) - 1) * line_spacing
        max_line_width = max(line_widths) if line_widths else 0
        
        x = (VideoConstants.VIDEO_WIDTH - max_line_width) // 2
        y = VideoConstants.VIDEO_HEIGHT - total_height - VideoConstants.SUBTITLE_BOTTOM_MARGIN
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        draw = ImageDraw.Draw(image)
        
        current_y = y
        for i, line in enumerate(lines):
            if not line.strip():
                continue
                
            line_bbox = draw.textbbox((0, 0), line, font=font)
            line_width = line_bbox[2] - line_bbox[0]
            line_x = (VideoConstants.VIDEO_WIDTH - line_width) // 2
            
            draw.text((line_x + 4, current_y + 4),
                      line, fill=(0, 0, 0), font=font)
            draw.text((line_x + 2, current_y + 2), line,
                      fill=(50, 50, 50), font=font)
            draw.text(
                (line_x, current_y), line, fill=(
        255, 255, 255), font=font)

            current_y += line_heights[i] + line_spacing
        
        return image

    def _wrap_text(
        self,
        text: str,
        font,
        max_width: int,
        font_size: int) -> list:
        """텍스트를 여러 줄로 자동 분할"""
        words = text.split()
        lines = []
        current_line = []
        
        temp_image = Image.new('RGB', (VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT))
        temp_draw = ImageDraw.Draw(temp_image)
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = temp_draw.textbbox((0, 0), test_line, font=font)
            test_width = bbox[2] - bbox[0]
            
            if test_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines if lines else [text]

    def _extract_key_words_for_subtitle(
        self, sentence: str, language: str = 'ko') -> str:
        """문장에서 자막용 핵심 단어 추출"""
        try:
            if self.openai_client:
                if language == 'en':
                    prompt = f"Extract 1-3 key words from this sentence for subtitle display. Only the most important words that capture the essence. Return only the words separated by spaces, no explanation:\n\n{sentence}"
                    system_prompt = "You are a subtitle keyword extractor. Extract only the most important 1-3 key words from sentences for subtitle display."
                else:
                    prompt = f"다음 문장에서 자막 표시용 핵심 단어 1-3개를 추출하세요. 가장 중요한 단어만 선택하세요. 단어만 공백으로 구분하여 반환하세요 (설명 없이):\n\n{sentence}"
                    system_prompt = "당신은 자막 키워드 추출 전문가입니다. 문장에서 자막 표시용 핵심 단어 1-3개만 추출하세요."

                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=30,
                    temperature=0.3
                )
                key_words = response.choices[0].message.content.strip()
                key_words = re.sub(r'[^\w\s]', '', key_words)
                words = key_words.split()
                key_words = ' '.join(words[:3])
                if key_words:
                    print(f"   핵심 단어 추출: {sentence[:30]}... -> {key_words}")
                    return key_words
        except Exception as e:
            print(f"   핵심 단어 추출 실패, 기본 사용: {e}")

        words = sentence.split()
        if language == 'en':
            if len(words) <= 3:
                return sentence
            else:
                return ' '.join(
                    [words[0], words[-1] if len(words) > 1 else ''])
        else:
            if len(words) <= 3:
                return sentence
            else:
                return ' '.join(words[:2])

    def _create_subtitle_clip(
        self,
        text: str,
        duration: float,
        language: str = 'ko') -> TextClip:
        """자막 클립 생성"""
        try:
            subtitle_text = text
            subtitle_mode = getattr(config, "SUBTITLE_MODE", "full_sentence")
            use_keywords = subtitle_mode != 'full_sentence'
            if use_keywords:
                key_words = self._extract_key_words_for_subtitle(
                    text, language=language)
                if key_words:
                    subtitle_text = key_words
            
            font_path = None
            font_size = 60 if subtitle_mode == 'full_sentence' else 80
            extra_offset = getattr(config, "SUBTITLE_EXTRA_OFFSET", 90)
            
            if language == 'en':
                for path in [
                    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                    "/System/Library/Fonts/Supplemental/Arial.ttf",
                    "/System/Library/Fonts/Supplemental/Arial Italic.ttf",
                    "/System/Library/Fonts/Helvetica.ttc",
                    "/System/Library/Fonts/Supplemental/Helvetica.ttc",
                    "/Library/Fonts/Arial.ttf",
                ]:
                    if os.path.exists(path):
                        font_path = path
                        break
            else:
                for path in [
                    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
                    "/System/Library/Fonts/AppleGothic.ttf",
                    "/System/Library/Fonts/Supplemental/NanumGothic.ttf",
                    "/Library/Fonts/AppleGothic.ttf",
                ]:
                    if os.path.exists(path):
                        font_path = path
                        break

            try:
                if font_path:
                    try:
                        txt_clip = TextClip(
                            subtitle_text,
                            fontsize=font_size,
                            font=font_path,
                            color='white',
                            stroke_color='black',
                            stroke_width=3,
                            method='caption',
                            size=(1000, None),
                            align='center'
                        )
                        txt_clip = txt_clip.set_start(0)
                        txt_clip = txt_clip.set_duration(duration)
                        try:
                            frame = txt_clip.get_frame(0)
                            clip_height = frame.shape[0]
                            # 자막을 화면 상단으로 올림 (모바일 UI 가림 방지)
                            raised_y = 250  # 1920px 기준 상단 1/8 지점
                            txt_clip = txt_clip.set_position(('center', raised_y))
                        except:
                            txt_clip = txt_clip.set_position(('center', 250))
                        txt_clip = txt_clip.set_start(0)
                        if abs(txt_clip.duration - duration) > 0.01:
                            txt_clip = txt_clip.set_duration(duration)
                        
                        fade_duration = min(0.3, duration * 0.1)
                        if duration > fade_duration * 2:
                            txt_clip = txt_clip.fx(fadein, fade_duration).fx(fadeout, fade_duration)
                            txt_clip = txt_clip.set_duration(duration)
                        print(
                            f"   ✅ ImageMagick 자막 생성 성공: duration={txt_clip.duration:.2f}초, start={txt_clip.start:.2f}초 (목표: {duration:.2f}초)")
                        return txt_clip
                    except Exception as e1:
                        print(f"   ImageMagick TextClip 실패, PIL로 대체: {e1}")

                # PIL Fallback
                subtitle_height = 300
                subtitle_img = Image.new(
                    'RGBA', (1080, subtitle_height), (0, 0, 0, 0))
                draw = ImageDraw.Draw(subtitle_img)

                pil_font = None
                if font_path and os.path.exists(font_path):
                    try:
                        pil_font = ImageFont.truetype(font_path, font_size)
                    except BaseException:
                        pass

                if pil_font is None:
                    if language == 'en':
                        for path in [
                            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                            "/System/Library/Fonts/Supplemental/Arial.ttf",
                            "/System/Library/Fonts/Helvetica.ttc",
                        ]:
                            if os.path.exists(path):
                                try:
                                    pil_font = ImageFont.truetype(
                                        path, font_size)
                                    break
                                except BaseException:
                                    continue
                    else:
                        for path in [
                            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
                            "/System/Library/Fonts/AppleGothic.ttf",
                        ]:
                            if os.path.exists(path):
                                try:
                                    pil_font = ImageFont.truetype(
                                        path, font_size)
                                    break
                                except BaseException:
                                    continue

                if pil_font is None:
                    pil_font = ImageFont.load_default()

                max_width = 1000
                words = subtitle_text.split()
                lines = []
                current_line = []

                for word in words:
                    test_line = ' '.join(current_line + [word])
                    bbox = draw.textbbox((0, 0), test_line, font=pil_font)
                    if bbox[2] - bbox[0] <= max_width:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                        current_line = [word]
                if current_line:
                    lines.append(' '.join(current_line))

                if not lines:
                    lines = [key_words] if use_keywords else [text]

                y_offset = 20
                for line in lines[:3]:
                    if line.strip():
                        bbox = draw.textbbox((0, 0), line, font=pil_font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]
                        x_pos = (1080 - text_width) // 2

                        draw = ImageDraw.Draw(subtitle_img)
                        shadow_offset = 4
                        shadow_blur = 2
                        for dx in range(-shadow_blur, shadow_blur + 1):
                            for dy in range(-shadow_blur, shadow_blur + 1):
                                if dx != 0 or dy != 0:
                                    draw.text(
                                        (x_pos + shadow_offset + dx, y_offset + shadow_offset + dy),
                                        line,
                                        fill=(0, 0, 0, 200),
                                        font=pil_font
                                    )
                        
                        draw.text(
                            (x_pos, y_offset),
                            line,
                            fill=(255, 255, 255),
                            font=pil_font
                        )
                        y_offset += text_height + 10

                temp_subtitle_path = os.path.join(
                    config.TEMP_DIR, f"subtitle_{int(time.time()*1000)}.png")
                subtitle_img.save(temp_subtitle_path, 'PNG')
                
                txt_clip = ImageClip(temp_subtitle_path)
                txt_clip = txt_clip.set_duration(duration)
                txt_clip = txt_clip.set_position(('center', 250))  # ImageMagick과 동일한 위치
                txt_clip = txt_clip.set_start(0)
                
                fade_duration = min(0.3, duration * 0.1)
                if duration > fade_duration * 2:
                    txt_clip = txt_clip.fx(fadein, fade_duration).fx(fadeout, fade_duration)
                    txt_clip = txt_clip.set_duration(duration)
                
                print(
                    f"   ✅ PIL 자막 생성 성공: 높이={subtitle_height}px, duration={txt_clip.duration:.2f}초, start={txt_clip.start:.2f}초 (목표: {duration:.2f}초)")
                return txt_clip
                
            except Exception as e:
                print(f"   ❌ 자막 생성 실패: {e}")
                return None
        except Exception as e:
            print(f"   ❌ 자막 생성 중 오류: {e}")
            return None

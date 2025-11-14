"""
AI 영상 생성 모듈 (15초~60초 YouTube Shorts)
"""
import os
import random
import re
from moviepy.editor import (
    VideoFileClip, ImageClip,
    concatenate_videoclips, AudioFileClip, CompositeVideoClip
)
from moviepy.video.fx.all import fadein, fadeout
from PIL import Image, ImageDraw, ImageFont
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from gtts import gTTS
    import io
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

import requests
import config


class AIVideoGenerator:
    """AI를 활용한 15초 YouTube Shorts 영상 생성 클래스"""
    
    def __init__(self):
        if config.OPENAI_API_KEY and OPENAI_AVAILABLE:
            try:
                # 간단한 초기화 (httpx 버전 호환성 문제 회피)
                self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
            except Exception as e:
                print(f"⚠️ OpenAI 클라이언트 초기화 실패: {e}")
                print("   기본 템플릿을 사용합니다.")
                self.openai_client = None
        else:
            self.openai_client = None
        
        # 출력 디렉토리 생성
        os.makedirs(config.VIDEO_OUTPUT_DIR, exist_ok=True)
        os.makedirs(config.TEMP_DIR, exist_ok=True)
        os.makedirs(config.THUMBNAIL_OUTPUT_DIR, exist_ok=True)
    
    def generate_video(
        self,
        topic: str = None,
        duration: int = None,
        output_filename: str = None
    ) -> str:
        """
        AI로 YouTube Shorts 영상 생성 (15초~60초)
        
        Args:
            topic: 영상 주제 (None이면 자동 생성)
            duration: 영상 길이 (초, None이면 스크립트에 따라 자동 계산)
            output_filename: 출력 파일명 (None이면 자동 생성)
        
        Returns:
            생성된 영상 파일 경로
        """
        # 주제가 없으면 AI로 생성
        if not topic:
            topic = self._generate_topic()
        
        print(f"📹 영상 생성 시작: '{topic}'")
        
        # 영상 스크립트 생성
        script = self._generate_script(topic)
        
        # duration이 없으면 스크립트 길이에 따라 자동 계산 (55초 목표, 60초 초과 방지)
        if duration is None:
            # 각 문장당 약 3-4초, 목표 55초 (60초 초과 방지를 위한 안전 마진)
            # 55초를 목표로 하되, 스크립트가 짧으면 최소 15초
            target_duration = config.SHORTS_TARGET_DURATION  # 55초 목표
            calculated_duration = len(script) * 3.5
            duration = max(15, min(target_duration, int(calculated_duration)))
            print(f"📏 스크립트 기반 자동 길이: {duration}초 ({len(script)}개 문장, 목표: {target_duration}초)")
        
        # 영상 생성
        video_path = self._create_video_from_script(script, topic, duration, output_filename)
        
        print(f"✅ 영상 생성 완료: {video_path} ({duration}초)")
        return video_path
    
    def _generate_topic(self) -> str:
        """AI로 인기 주제 생성"""
        topics = [
            "5가지 생산성 팁",
            "요리 초보자를 위한 레시피",
            "건강한 아침 루틴",
            "돈을 절약하는 방법",
            "집중력을 높이는 방법",
            "자기계발 습관",
            "요리 꿀팁",
            "운동 초보자 가이드",
            "시간 관리 팁",
            "스트레스 해소법"
        ]
        return random.choice(topics)
    
    def _generate_script(self, topic: str) -> list:
        """AI로 영상 스크립트 생성 (15초~60초용, 내용에 따라 길이 조정)"""
        if self.openai_client:
            try:
                # gpt-4o-mini 또는 gpt-4o 사용 시도 (더 접근 가능)
                models_to_try = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
                response = None
                last_error = None
                
                for model in models_to_try:
                    try:
                        response = self.openai_client.chat.completions.create(
                            model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "당신은 YouTube Shorts용 영상 스크립트 작성 전문가입니다. 설명이 충분하도록 자세하게 작성하세요. 목표는 약 55초 분량이며, 각 문장은 3-4초 분량입니다. YouTube Shorts는 최대 60초이므로 55초 이내로 작성해야 합니다."
                        },
                        {
                            "role": "user",
                            "content": f"'{topic}'에 대한 YouTube Shorts 영상 스크립트를 작성해주세요. 설명이 충분하도록 자세하게 작성해주세요. 각 문장은 3-4초 분량이며, 총 12-16개 문장으로 작성해주세요 (약 55초 분량, 최대 60초 제한). 중요한 점: 순수한 대사나 설명만 작성하고, '배경음악', '자막', '시작' 같은 제작 지시사항은 절대 포함하지 마세요."
                        }
                    ],
                            max_tokens=500,  # 1분 분량을 위해 토큰 증가
                            temperature=0.7
                        )
                        script_text = response.choices[0].message.content
                        # 문장별로 분리
                        sentences = [s.strip() for s in script_text.split('\n') if s.strip()]
                        
                        # 불필요한 텍스트 필터링
                        filter_keywords = [
                            '배경음악', '음악', 'BGM', 'bgm', '배경', '시작', '종료',
                            '자막', '타이틀', '제목', '인트로', '아웃트로',
                            '참고', '주의', '설명', '참고사항'
                        ]
                        
                        filtered_sentences = []
                        for s in sentences:
                            # 숫자나 불필요한 기호로 시작하는 것 제거
                            if s.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '-', '*', '•')):
                                continue
                            # 너무 짧은 문장 제거
                            if len(s) < 5:
                                continue
                            # 필터 키워드가 포함된 문장 제거
                            if any(keyword in s for keyword in filter_keywords):
                                continue
                            # 괄호 안의 설명 제거 (예: "텍스트 (참고사항)" -> "텍스트")
                            s = re.sub(r'\([^)]*\)', '', s).strip()
                            s = re.sub(r'\[[^\]]*\]', '', s).strip()
                            if s and len(s) >= 5:
                                filtered_sentences.append(s)
                        
                        return filtered_sentences[:16]  # 최대 16개 문장 (약 55초)
                    except Exception as e:
                        last_error = e
                        continue  # 다음 모델 시도
                
                # 모든 모델 실패 시
                if not response:
                    raise last_error if last_error else Exception("모든 모델 접근 실패")
                    
            except Exception as e:
                error_msg = str(e)
                if "does not have access" in error_msg or "model_not_found" in error_msg:
                    print(f"⚠️ OpenAI API 키가 모델에 접근할 수 없습니다.")
                    print(f"   OpenAI Platform에서 모델 접근 권한을 확인하세요.")
                    print(f"   기본 템플릿을 사용합니다.")
                else:
                    print(f"⚠️ AI 스크립트 생성 실패, 기본 템플릿 사용: {e}")
        
        # 기본 템플릿
        templates = {
            "5가지 생산성 팁": [
                "생산성을 높이는 5가지 방법",
                "첫째, 아침 루틴을 만드세요",
                "둘째, 할 일을 우선순위로 정리하세요",
                "셋째, 집중 방해 요소를 제거하세요",
                "지금 바로 시작하세요!"
            ],
            "요리 초보자를 위한 레시피": [
                "초보자도 쉽게 만드는 요리",
                "필요한 재료는 간단합니다",
                "단계별로 따라하면 완성",
                "맛있고 건강한 한 끼",
                "지금 바로 도전해보세요!"
            ]
        }
        
        return templates.get(topic, [
            f"{topic}에 대해 알아보겠습니다",
            "중요한 포인트를 알려드립니다",
            "실천하면 효과를 볼 수 있습니다",
            "지금 바로 시작하세요!"
        ])
    
    def _create_video_from_script(
        self,
        script: list,
        topic: str,
        duration: int,
        output_filename: str = None
    ) -> str:
        """스크립트로부터 영상 생성"""
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
            audio_path = self._generate_audio(sentence, i)
            if audio_path and os.path.exists(audio_path):
                audio_clip = AudioFileClip(audio_path)
                actual_duration = audio_clip.duration
                sentence_audio_durations.append(actual_duration)
                audio_clips.append(audio_clip)
                print(f"   문장 {i+1}: {actual_duration:.2f}초 - {sentence[:30]}...")
            else:
                # 음성 생성 실패 시 기본 duration 사용
                default_duration = duration / len(script)
                sentence_audio_durations.append(default_duration)
                print(f"   문장 {i+1}: 음성 생성 실패, 기본 길이 사용 ({default_duration:.2f}초)")
        
        # 실제 음성 길이 합계
        total_audio_duration = sum(sentence_audio_durations)
        print(f"📏 실제 음성 총 길이: {total_audio_duration:.2f}초")
        
        # 음성 길이를 기준으로 영상 길이 조정 (60초 초과 방지)
        max_safe_duration = 58  # 60초 초과 방지를 위한 안전 마진
        if total_audio_duration > max_safe_duration:
            print(f"⚠️ 음성 길이가 {max_safe_duration}초를 초과합니다. 마지막 문장들을 제거하여 {max_safe_duration}초 이내로 맞춥니다.")
            
            # 마지막 문장부터 제거하여 58초 이내로 맞추기
            removed_count = 0
            original_script_len = len(script)
            while total_audio_duration > max_safe_duration and len(script) > 1:
                # 마지막 문장 제거
                removed_sentence = script.pop()
                removed_audio_duration = sentence_audio_durations.pop()
                # audio_clips는 인덱스로 접근해야 함 (리스트 길이가 다를 수 있음)
                if len(audio_clips) > len(script):
                    audio_clips.pop()
                total_audio_duration -= removed_audio_duration
                removed_count += 1
                print(f"   문장 제거: '{removed_sentence[:30]}...' ({removed_audio_duration:.2f}초)")
            
            duration = min(total_audio_duration, max_safe_duration)
            print(f"   최종 음성 길이: {total_audio_duration:.2f}초 ({removed_count}개 문장 제거됨)")
        elif total_audio_duration > duration:
            # duration이 max_safe_duration 이하인 경우에만 조정
            duration = min(total_audio_duration, max_safe_duration)
            print(f"   영상 길이를 음성 길이에 맞춤: {duration:.2f}초 (최대 {max_safe_duration}초)")
        elif abs(total_audio_duration - duration) > 1.0:
            # 목표 duration이 더 길면 각 문장의 비율을 유지하면서 조정
            scale_factor = duration / total_audio_duration
            sentence_audio_durations = [d * scale_factor for d in sentence_audio_durations]
            print(f"   duration 조정: {scale_factor:.2f}배 (목표: {duration}초)")
        
        # 이미지 그룹핑: 2-3개 문장마다 이미지 변경 (너무 자주 바꾸지 않음)
        image_groups = []
        group_size = 2  # 2개 문장마다 이미지 변경
        for i in range(0, len(script), group_size):
            group_end = min(i + group_size, len(script))
            # 그룹의 첫 번째 문장으로 이미지 선택
            group_sentence = script[i]
            group_image = self._download_image_for_sentence(group_sentence, i)
            if group_image is None:
                # 이미지 다운로드 실패 시 그라데이션 배경 사용
                group_image = self._create_gradient_background(i, len(script))
            image_groups.append((i, group_end, group_image))
            print(f"   이미지 그룹 {len(image_groups)}: 문장 {i+1}-{group_end} ({group_sentence[:30]}...)")
        
        # 각 문장별로 영상 클립 생성 (자막 없이, 그룹별 이미지 사용)
        for i, sentence in enumerate(script):
            # 실제 음성 길이에 맞춘 duration 사용
            sentence_duration = sentence_audio_durations[i]
            
            # 해당 문장이 속한 그룹의 이미지 찾기
            bg_image = None
            for group_start, group_end, group_image in image_groups:
                if group_start <= i < group_end:
                    bg_image = group_image.copy()
                    break
            
            # 이미지를 찾지 못했으면 그라데이션 배경 사용
            if bg_image is None:
                bg_image = self._create_gradient_background(i, len(script))
            
            # 텍스트를 그리지 않음 (자막 제거)
            text_image = bg_image
            
            # 이미지 저장 (RGB 모드로 저장)
            bg_path = os.path.join(config.TEMP_DIR, f"frame_{i}.png")
            if text_image.mode != 'RGB':
                text_image = text_image.convert('RGB')
            
            # 이미지가 실제로 내용이 있는지 확인
            pixels = list(text_image.getdata())
            unique_colors = len(set(pixels[:1000]))
            if unique_colors < 5:
                print(f"⚠️ 프레임 {i} 경고: 색상이 부족합니다 (고유 색상: {unique_colors})")
            
            text_image.save(bg_path, 'PNG')
            
            # 디버그: 첫 번째 프레임 확인
            if i == 0:
                debug_path = os.path.join(config.TEMP_DIR, f"debug_frame_0.png")
                text_image.save(debug_path, 'PNG')
                print(f"🔍 디버그: 첫 프레임 저장됨 - {debug_path}")
                print(f"   이미지 크기: {text_image.size}, 모드: {text_image.mode}, 고유 색상: {unique_colors}")
            
            # 이미지 클립 생성 (실제 음성 길이에 맞춤)
            img_clip = ImageClip(bg_path).set_duration(sentence_duration)
            
            # 해상도 명시적 설정
            img_clip = img_clip.resize((1080, 1920))
            
            # 페이드 효과 제거 (이미지가 리프레시되지 않도록)
            # 첫 번째와 마지막 클립만 약간의 페이드 효과 적용
            if i == 0:
                # 첫 클립만 페이드 인
                img_clip = img_clip.fx(fadein, 0.5)
            elif i == len(script) - 1:
                # 마지막 클립만 페이드 아웃
                img_clip = img_clip.fx(fadeout, 0.5)
            # 중간 클립들은 페이드 효과 없음 (부드러운 전환)
            
            # 정확한 duration 보장
            img_clip = img_clip.set_duration(sentence_duration)
            
            clips.append(img_clip)
        
        # 모든 클립 연결 (영상이 잘리지 않도록 정확한 duration 설정)
        if not clips:
            raise ValueError("생성된 클립이 없습니다.")
        
        # 각 클립의 duration 확인
        total_clip_duration = sum(clip.duration for clip in clips)
        print(f"📏 클립 총 길이: {total_clip_duration:.2f}초, 목표: {duration}초")
        
        # duration이 다르면 조정
        if abs(total_clip_duration - duration) > 0.1:
            # 마지막 클립의 duration 조정
            last_clip = clips[-1]
            adjustment = duration - (total_clip_duration - last_clip.duration)
            if adjustment > 0:
                clips[-1] = last_clip.set_duration(adjustment)
                print(f"   마지막 클립 duration 조정: {adjustment:.2f}초")
        
        final_video = concatenate_videoclips(clips, method="compose")
        
        # 정확한 duration 보장
        final_video = final_video.set_duration(duration)
        
        # 음성 추가 (각 문장별로 정확히 매칭, 마지막 음성이 잘리지 않도록)
        if audio_clips:
            try:
                from moviepy.audio.AudioClip import concatenate_audioclips
                final_audio = concatenate_audioclips(audio_clips)
                
                # 실제 음성 길이 사용
                actual_audio_duration = final_audio.duration
                actual_video_duration = sum(sentence_audio_durations)
                
                print(f"🎵 음성 총 길이: {actual_audio_duration:.2f}초, 영상 총 길이: {actual_video_duration:.2f}초")
                
                # 음성 길이를 기준으로 영상 길이 조정 (음성이 잘리지 않도록)
                if actual_audio_duration > actual_video_duration:
                    # 음성이 더 길면 영상 길이를 음성에 맞춤
                    actual_video_duration = actual_audio_duration
                    # 마지막 클립의 duration 조정
                    if clips:
                        last_clip = clips[-1]
                        current_total = sum(c.duration for c in clips[:-1])
                        last_clip_duration = actual_video_duration - current_total
                        if last_clip_duration > 0:
                            clips[-1] = last_clip.set_duration(last_clip_duration)
                            print(f"   마지막 클립 duration 조정: {last_clip_duration:.2f}초 (음성 보호)")
                    # 영상 다시 생성
                    final_video = concatenate_videoclips(clips, method="compose")
                    final_video = final_video.set_duration(actual_video_duration)
                elif actual_audio_duration < actual_video_duration:
                    # 음성이 짧으면 영상 길이를 음성에 맞춤 (음성 끝까지만)
                    actual_video_duration = actual_audio_duration
                    final_video = final_video.subclip(0, actual_video_duration)
                
                # 최종 길이 확인 및 60초 초과 방지
                max_safe_duration = 58  # 60초 초과 방지를 위한 안전 마진
                if actual_video_duration > max_safe_duration:
                    print(f"⚠️ 최종 영상 길이가 {max_safe_duration}초를 초과합니다. {max_safe_duration}초로 제한합니다.")
                    actual_video_duration = max_safe_duration
                    final_video = final_video.subclip(0, actual_video_duration)
                
                # 음성과 영상 길이 정확히 일치하도록 설정
                final_audio = final_audio.set_duration(actual_video_duration)
                final_video = final_video.set_audio(final_audio)
                final_video = final_video.set_duration(actual_video_duration)
                
                print(f"✅ 음성-영상 동기화 완료: {actual_video_duration:.2f}초 (60초 초과 방지)")
            except Exception as e:
                print(f"⚠️ 음성 추가 실패: {e}")
                import traceback
                traceback.print_exc()
        
        # FPS 설정 (YouTube Shorts 권장: 30fps)
        final_video = final_video.set_fps(30)
        
        # 해상도 확인 및 설정 (1080x1920 - YouTube Shorts 세로형)
        if final_video.size[0] != 1080 or final_video.size[1] != 1920:
            final_video = final_video.resize((1080, 1920))
        
        # 영상 저장
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
        
        return output_path
    
    def _generate_audio(self, text: str, index: int) -> str:
        """TTS로 음성 생성"""
        if not TTS_AVAILABLE:
            return None
        
        try:
            audio_path = os.path.join(config.TEMP_DIR, f"audio_{index}.mp3")
            
            # gTTS로 음성 생성 (한국어)
            tts = gTTS(text=text, lang='ko', slow=False)
            tts.save(audio_path)
            
            return audio_path
        except Exception as e:
            print(f"⚠️ 음성 생성 실패 ({text[:20]}...): {e}")
            return None
    
    def _draw_text_on_image(self, image: Image.Image, text: str) -> Image.Image:
        """이미지에 텍스트 그리기 (한글 폰트 지원, 여러 줄 자동 분할)"""
        # 한글 폰트 시도 (초기 크기)
        base_font_size = 100
        font = None
        font_path_used = None
        
        # macOS 한글 폰트 경로
        for font_path in [
            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",  # 애플고딕
            "/System/Library/Fonts/AppleGothic.ttf",
            "/System/Library/Fonts/Supplemental/NanumGothic.ttf",  # 나눔고딕 (설치된 경우)
            "/Library/Fonts/AppleGothic.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",  # 폴백
            "/System/Library/Fonts/Helvetica.ttc"
        ]:
            try:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, base_font_size)
                    font_path_used = font_path
                    break
            except:
                continue
        
        if font is None:
            # 기본 폰트 (한글 지원 안 될 수 있음)
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Supplemental/AppleGothic.ttf", base_font_size)
                font_path_used = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
            except:
                font = ImageFont.load_default()
        
        # 이미지를 RGB로 변환 (텍스트 그리기 전)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 텍스트를 여러 줄로 분할 (최대 너비 고려)
        max_width = 900  # 좌우 여백 90px
        lines = self._wrap_text(text, font, max_width, base_font_size)
        
        # 폰트 크기 자동 조정 (텍스트가 너무 길면)
        if len(lines) > 3 and font_path_used:
            # 텍스트가 너무 많으면 폰트 크기 줄이기
            for size in [90, 80, 70, 60]:
                try:
                    font = ImageFont.truetype(font_path_used, size)
                    lines = self._wrap_text(text, font, max_width, size)
                    if len(lines) <= 4:
                        break
                except:
                    continue
        
        # 텍스트 크기 계산
        draw = ImageDraw.Draw(image)
        line_heights = []
        line_widths = []
        
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_heights.append(bbox[3] - bbox[1])
            line_widths.append(bbox[2] - bbox[0])
        
        total_height = sum(line_heights) + (len(lines) - 1) * 20  # 줄 간격
        max_line_width = max(line_widths) if line_widths else 0
        
        # 텍스트 위치 (중앙, 아래쪽)
        x = (1080 - max_line_width) // 2
        y = 1920 - total_height - 150  # 하단에서 150px 위
        
        # 텍스트 배경 (반투명 검은색) - RGBA 모드로 작업
        padding = 40
        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(
            [
                x - padding,
                y - padding,
                x + max_line_width + padding,
                y + total_height + padding
            ],
            fill=(0, 0, 0, 200)  # 더 진한 배경
        )
        
        # 배경과 오버레이 합성
        image_rgba = image.convert('RGBA')
        image_rgba = Image.alpha_composite(image_rgba, overlay)
        image = image_rgba.convert('RGB')
        draw = ImageDraw.Draw(image)
        
        # 여러 줄 텍스트 그리기
        current_y = y
        for i, line in enumerate(lines):
            if not line.strip():  # 빈 줄 건너뛰기
                continue
                
            line_bbox = draw.textbbox((0, 0), line, font=font)
            line_width = line_bbox[2] - line_bbox[0]
            line_x = (1080 - line_width) // 2  # 각 줄도 중앙 정렬
            
            # 텍스트 그림자 효과 (가독성 향상) - 더 진하게
            draw.text((line_x + 4, current_y + 4), line, fill=(0, 0, 0), font=font)
            draw.text((line_x + 2, current_y + 2), line, fill=(50, 50, 50), font=font)
            # 메인 텍스트 - 밝은 흰색
            draw.text((line_x, current_y), line, fill=(255, 255, 255), font=font)
            
            current_y += line_heights[i] + 20  # 줄 간격
        
        # 디버그: 텍스트가 실제로 그려졌는지 확인
        # 간단한 테스트 - 이미지 중앙에 작은 점 찍기
        draw.ellipse([540-5, 960-5, 540+5, 960+5], fill=(255, 255, 0))  # 노란 점
        
        return image
    
    def _wrap_text(self, text: str, font, max_width: int, font_size: int) -> list:
        """텍스트를 여러 줄로 자동 분할"""
        words = text.split()
        lines = []
        current_line = []
        
        # 폰트로 텍스트 크기 측정
        temp_image = Image.new('RGB', (1080, 1920))
        temp_draw = ImageDraw.Draw(temp_image)
        
        for word in words:
            # 현재 줄에 단어 추가 시도
            test_line = ' '.join(current_line + [word])
            bbox = temp_draw.textbbox((0, 0), test_line, font=font)
            test_width = bbox[2] - bbox[0]
            
            if test_width <= max_width:
                current_line.append(word)
            else:
                # 현재 줄 저장하고 새 줄 시작
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        # 마지막 줄 추가
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines if lines else [text]
    
    def _create_gradient_background(self, index: int, total: int) -> Image.Image:
        """그라데이션 배경 이미지 생성 + 시각적 요소 추가"""
        width, height = 1080, 1920
        
        # 색상 팔레트
        colors = [
            [(255, 107, 107), (255, 159, 64)],  # 빨강-주황
            [(74, 144, 226), (80, 227, 194)],   # 파랑-청록
            [(255, 206, 84), (255, 159, 64)],   # 노랑-주황
            [(156, 136, 255), (220, 138, 221)], # 보라-핑크
            [(99, 205, 218), (85, 230, 193)],   # 하늘-민트
        ]
        
        color_pair = colors[index % len(colors)]
        start_color = color_pair[0]
        end_color = color_pair[1]
        
        # 그라데이션 생성 (RGB 모드로 직접 생성)
        image = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(image)
        
        # 그라데이션 생성 - 각 픽셀 라인 그리기
        for y in range(height):
            # y 위치에 따른 색상 보간
            ratio = y / height
            r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
            g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
            b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
            
            # 각 픽셀 라인 그리기 (RGB 모드)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # 시각적 요소 추가 - 원형 도형들 (RGBA 오버레이로)
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        center_x = width // 2
        center_y = height // 3  # 상단 1/3 지점
        
        # 큰 원 (반투명 흰색)
        big_radius = 300
        overlay_draw.ellipse(
            [center_x - big_radius, center_y - big_radius,
             center_x + big_radius, center_y + big_radius],
            fill=(255, 255, 255, 50),
            outline=(255, 255, 255, 100),
            width=8
        )
        
        # 중간 원
        mid_radius = 200
        overlay_draw.ellipse(
            [center_x - mid_radius, center_y - mid_radius,
             center_x + mid_radius, center_y + mid_radius],
            fill=(255, 255, 255, 30),
            outline=(255, 255, 255, 80),
            width=5
        )
        
        # 작은 원들 (장식) - 더 명확하게
        for i in range(6):
            angle = i * 60  # 60도씩 회전
            radius_offset = 280
            small_x = center_x + int(radius_offset * (1 if i % 2 == 0 else 0.8) * (1 if i < 3 else -1))
            small_y = center_y + int(180 * (1 if i % 2 == 0 else -1))
            small_radius = 100 + (i % 3) * 30
            overlay_draw.ellipse(
                [small_x - small_radius, small_y - small_radius,
                 small_x + small_radius, small_y + small_radius],
                fill=(255, 255, 255, 60),
                outline=(255, 255, 255, 120),
                width=4
            )
        
        # 오버레이 합성
        image = Image.alpha_composite(image.convert('RGBA'), overlay)
        
        return image
    
    def _download_image_for_topic(self, topic: str) -> Image.Image:
        """주제에 맞는 이미지 다운로드"""
        try:
            # 주제에서 키워드 추출
            keywords = self._extract_keywords(topic)
            keyword = keywords[0] if keywords else "nature"
            
            # 영어 키워드로 변환
            english_keyword = self._translate_keyword_to_english(keyword)
            
            print(f"🖼️  주제 이미지 다운로드 시도: {topic} -> {english_keyword}")
            
            # Pexels 또는 Lorem Picsum 사용
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            # Lorem Picsum 사용 (안정적)
            lorem_url = f"https://picsum.photos/1080/1920?random={hash(topic) % 10000}"
            response = requests.get(lorem_url, timeout=10, headers=headers)
            response.raise_for_status()
            
            # 이미지 로드
            from io import BytesIO
            img = Image.open(BytesIO(response.content))
            
            # RGB 모드로 변환
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 1080x1920으로 리사이즈 및 크롭
            img = self._resize_and_crop(img, 1080, 1920)
            
            print(f"✅ 주제 이미지 다운로드 성공: {english_keyword}")
            return img
            
        except Exception as e:
            print(f"⚠️  주제 이미지 다운로드 실패 ({topic}): {e}")
            return None
    
    def _download_image_for_sentence(self, sentence: str, index: int) -> Image.Image:
        """문장에 맞는 이미지 다운로드 (키워드 기반)"""
        try:
            # 문장에서 키워드 추출
            keywords = self._extract_keywords(sentence)
            keyword = keywords[0] if keywords else "nature"
            
            # 영어 키워드로 변환
            english_keyword = self._translate_keyword_to_english(keyword)
            
            print(f"🖼️  이미지 다운로드 시도: {keyword} -> {english_keyword}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            # 방법 1: Pexels API 사용 (키워드 기반 검색, API 키 필요)
            if config.PEXELS_API_KEY:
                try:
                    pexels_url = f"https://api.pexels.com/v1/search?query={english_keyword}&per_page=3&orientation=portrait"
                    pexels_headers = {
                        **headers,
                        'Authorization': config.PEXELS_API_KEY
                    }
                    response = requests.get(pexels_url, timeout=10, headers=pexels_headers)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('photos') and len(data['photos']) > 0:
                            # 첫 번째 이미지 선택
                            image_url = data['photos'][0]['src']['large']
                            # 세로형 이미지 우선
                            if 'portrait' in data['photos'][0]['src']:
                                image_url = data['photos'][0]['src']['portrait']
                            
                            img_response = requests.get(image_url, timeout=10, headers=headers)
                            if img_response.status_code == 200:
                                from io import BytesIO
                                img = Image.open(BytesIO(img_response.content))
                                if img.mode != 'RGB':
                                    img = img.convert('RGB')
                                img = self._resize_and_crop(img, 1080, 1920)
                                print(f"✅ Pexels 이미지 다운로드 성공: {english_keyword}")
                                return img
                except Exception as e:
                    print(f"   Pexels API 실패: {e}")
            
            # 방법 2: Unsplash API 사용 (키워드 기반 검색, API 키 필요)
            if config.UNSPLASH_ACCESS_KEY:
                try:
                    unsplash_url = f"https://api.unsplash.com/search/photos?query={english_keyword}&orientation=portrait&per_page=3"
                    unsplash_headers = {
                        **headers,
                        'Authorization': f'Client-ID {config.UNSPLASH_ACCESS_KEY}'
                    }
                    response = requests.get(unsplash_url, timeout=10, headers=unsplash_headers)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('results') and len(data['results']) > 0:
                            # 첫 번째 이미지 선택
                            image_url = data['results'][0]['urls']['regular']
                            
                            img_response = requests.get(image_url, timeout=10, headers=headers)
                            if img_response.status_code == 200:
                                from io import BytesIO
                                img = Image.open(BytesIO(img_response.content))
                                if img.mode != 'RGB':
                                    img = img.convert('RGB')
                                img = self._resize_and_crop(img, 1080, 1920)
                                print(f"✅ Unsplash 이미지 다운로드 성공: {english_keyword}")
                                return img
                except Exception as e:
                    print(f"   Unsplash API 실패: {e}")
            
            # 방법 3: Pixabay API 사용 (무료, 공개 API 키)
            try:
                pixabay_api_key = "9656065-a4094594c34c9ac8a7e8c5c4e"  # 공개 데모 키
                pixabay_url = f"https://pixabay.com/api/?key={pixabay_api_key}&q={english_keyword}&image_type=photo&orientation=vertical&safesearch=true&per_page=3"
                
                response = requests.get(pixabay_url, timeout=10, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('hits') and len(data['hits']) > 0:
                        image_url = data['hits'][0]['webformatURL']
                        image_url = image_url.replace('_640', '_1280')
                        
                        img_response = requests.get(image_url, timeout=10, headers=headers)
                        if img_response.status_code == 200:
                            from io import BytesIO
                            img = Image.open(BytesIO(img_response.content))
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            img = self._resize_and_crop(img, 1080, 1920)
                            print(f"✅ Pixabay 이미지 다운로드 성공: {english_keyword}")
                            return img
            except Exception as e:
                print(f"   Pixabay API 실패: {e}")
            
            # 방법 2: Unsplash Source API 시도 (키워드 기반, API 키 불필요)
            try:
                unsplash_source_url = f"https://source.unsplash.com/1080x1920/?{english_keyword}"
                response = requests.get(unsplash_source_url, timeout=15, allow_redirects=True, headers=headers)
                if response.status_code == 200 and response.content:
                    content_type = response.headers.get('Content-Type', '')
                    if 'image' in content_type or len(response.content) > 1000:
                        from io import BytesIO
                        img = Image.open(BytesIO(response.content))
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        img = self._resize_and_crop(img, 1080, 1920)
                        print(f"✅ Unsplash 이미지 다운로드 성공: {english_keyword}")
                        return img
            except Exception as e:
                print(f"   Unsplash Source 실패: {e}")
            
            # 방법 3: 최후의 수단 - 키워드 기반 랜덤 이미지
            keyword_hash = hash(english_keyword) % 10000
            lorem_url = f"https://picsum.photos/1080/1920?random={keyword_hash}"
            response = requests.get(lorem_url, timeout=10, headers=headers)
            response.raise_for_status()
            
            from io import BytesIO
            img = Image.open(BytesIO(response.content))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img = self._resize_and_crop(img, 1080, 1920)
            
            print(f"⚠️  랜덤 이미지 사용 (키워드: {english_keyword})")
            return img
            
        except Exception as e:
            print(f"⚠️  이미지 다운로드 실패 ({sentence[:20]}...): {e}")
            return None
    
    def _resize_and_crop(self, img: Image.Image, target_width: int, target_height: int) -> Image.Image:
        """이미지를 목표 크기에 맞게 리사이즈 및 크롭"""
        img_width, img_height = img.size
        target_ratio = target_width / target_height
        img_ratio = img_width / img_height
        
        if img_ratio > target_ratio:
            # 이미지가 더 넓음 - 높이에 맞춰서 리사이즈 후 좌우 크롭
            new_height = target_height
            new_width = int(new_height * img_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            left = (new_width - target_width) // 2
            img = img.crop((left, 0, left + target_width, target_height))
        else:
            # 이미지가 더 높음 - 너비에 맞춰서 리사이즈 후 상하 크롭
            new_width = target_width
            new_height = int(new_width / img_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            top = (new_height - target_height) // 2
            img = img.crop((0, top, target_width, top + target_height))
        
        return img
    
    def _extract_keywords(self, sentence: str) -> list:
        """문장에서 이미지 키워드 추출 (AI 사용)"""
        # AI를 사용해서 더 정확한 키워드 추출 시도
        if self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "당신은 이미지 검색 키워드 추출 전문가입니다. 주어진 문장에서 이미지 검색에 적합한 영어 키워드 1-3개를 추출하세요. 키워드는 명사 위주로, 구체적이고 시각적인 단어를 선택하세요."
                        },
                        {
                            "role": "user",
                            "content": f"다음 문장에서 이미지 검색에 적합한 영어 키워드를 추출하세요 (쉼표로 구분, 최대 3개):\n\n{sentence}"
                        }
                    ],
                    max_tokens=50,
                    temperature=0.3
                )
                keywords_text = response.choices[0].message.content.strip()
                # 쉼표나 줄바꿈으로 분리
                keywords = [k.strip().lower() for k in re.split(r'[,，\n]', keywords_text) if k.strip()]
                # 영어가 아닌 것 제거
                keywords = [k for k in keywords if k.isascii() and len(k) > 2]
                if keywords:
                    print(f"   AI 키워드 추출: {keywords}")
                    return keywords[:3]
            except Exception as e:
                print(f"   AI 키워드 추출 실패, 기본 방법 사용: {e}")
        
        # AI 실패 시 기본 키워드 매핑 사용
        keywords = []
        
        # 확장된 키워드 패턴
        keyword_patterns = {
            '건강': 'health', '건강한': 'healthy',
            '운동': 'fitness', '운동하다': 'exercise',
            '요리': 'cooking', '요리하다': 'cooking',
            '음식': 'food', '먹다': 'eating',
            '여행': 'travel', '여행하다': 'traveling',
            '자기계발': 'self-improvement', '개발': 'development',
            '습관': 'habit', '습관을': 'habit',
            '아침': 'morning', '아침에': 'morning',
            '루틴': 'routine', '일상': 'daily',
            '공부': 'study', '학습': 'learning', '공부하다': 'studying',
            '성공': 'success', '성공하다': 'success',
            '동기부여': 'motivation', '동기': 'motivation',
            '영감': 'inspiration', '영감을': 'inspiration',
            '자연': 'nature', '자연의': 'nature',
            '풍경': 'landscape', '경치': 'scenery',
            '도시': 'city', '도시의': 'urban',
            '사람': 'people', '사람들': 'people',
            '행복': 'happiness', '행복한': 'happy',
            '평화': 'peace', '평화로운': 'peaceful',
            '물': 'water', '물을': 'water',
            '스트레칭': 'stretching', '스트레칭하다': 'stretching',
            '명상': 'meditation', '명상하다': 'meditation',
            '목표': 'goal', '목표를': 'goal',
            '과일': 'fruit', '과일을': 'fruit',
            '오트밀': 'oatmeal', '시리얼': 'cereal',
        }
        
        # 문장에서 키워드 찾기 (더 정확한 매칭)
        sentence_lower = sentence.lower()
        for korean, english in keyword_patterns.items():
            if korean in sentence_lower:
                keywords.append(english)
        
        # 키워드가 없으면 문장의 주요 단어 추출 시도
        if not keywords:
            # 한글 단어 추출 (간단한 방법)
            words = re.findall(r'[가-힣]+', sentence)
            if words:
                # 가장 긴 단어를 키워드로 사용
                longest_word = max(words, key=len)
                # 기본 키워드 매핑에 없으면 'nature' 사용
                keywords = ['nature', 'inspiration']
            else:
                keywords = ['nature', 'inspiration', 'motivation']
        
        return keywords[:3]  # 최대 3개
    
    def _translate_keyword_to_english(self, keyword: str) -> str:
        """키워드를 영어로 변환 (간단한 매핑)"""
        # 이미 영어면 그대로 반환
        if keyword.isascii():
            return keyword
        
        # 한글-영어 매핑
        mapping = {
            '건강': 'health',
            '운동': 'fitness',
            '요리': 'cooking',
            '음식': 'food',
            '여행': 'travel',
            '자기계발': 'self-improvement',
            '습관': 'habit',
            '아침': 'morning',
            '루틴': 'routine',
            '공부': 'study',
            '학습': 'learning',
            '성공': 'success',
            '동기부여': 'motivation',
            '영감': 'inspiration',
            '자연': 'nature',
            '풍경': 'landscape',
            '도시': 'city',
            '사람': 'people',
            '행복': 'happiness',
            '평화': 'peace',
        }
        
        return mapping.get(keyword, 'nature')
    
    def generate_thumbnail(self, video_path: str, title: str) -> str:
        """매력적인 썸네일 이미지 생성"""
        import datetime
        import numpy as np
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        thumbnail_path = os.path.join(config.THUMBNAIL_OUTPUT_DIR, f"thumb_{timestamp}.jpg")
        
        # 영상에서 여러 프레임 중 가장 좋은 프레임 선택 (중간 부분)
        video = VideoFileClip(video_path)
        duration = video.duration
        # 영상의 30-40% 지점에서 프레임 추출 (일반적으로 가장 매력적인 부분)
        frame_time = duration * 0.35
        frame = video.get_frame(frame_time)
        video.close()
        
        # PIL 이미지로 변환
        img = Image.fromarray(frame.astype('uint8'), 'RGB')
        
        # 이미지 크기 확인 및 조정 (1080x1920)
        if img.size != (1080, 1920):
            img = img.resize((1080, 1920), Image.Resampling.LANCZOS)
        
        # 한글 폰트 로드
        font_large = None
        font_medium = None
        font_paths = [
            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
            "/System/Library/Fonts/AppleGothic.ttf",
            "/System/Library/Fonts/Supplemental/NanumGothic.ttf",
            "/System/Library/Fonts/Helvetica.ttc"
        ]
        
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    font_large = ImageFont.truetype(font_path, 120)
                    font_medium = ImageFont.truetype(font_path, 70)
                    break
            except:
                continue
        
        if font_large is None:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
        
        draw = ImageDraw.Draw(img)
        
        # 1. 상단에 "SHORTS" 배지 추가
        badge_text = "SHORTS"
        badge_font = font_medium
        badge_bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
        badge_width = badge_bbox[2] - badge_bbox[0]
        badge_height = badge_bbox[3] - badge_bbox[1]
        badge_x = 50
        badge_y = 50
        badge_padding = 15
        
        # 배지 배경 (빨간색 그라데이션 효과)
        badge_bg = Image.new('RGBA', (badge_width + badge_padding * 2, badge_height + badge_padding * 2), (255, 0, 0, 230))
        img.paste(badge_bg, (badge_x - badge_padding, badge_y - badge_padding), badge_bg)
        draw.text((badge_x, badge_y), badge_text, fill=(255, 255, 255), font=badge_font)
        
        # 2. 하단에 제목 텍스트 추가 (더 크고 눈에 띄게)
        # 텍스트를 여러 줄로 분할
        max_width = 1000
        words = title.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            bbox = draw.textbbox((0, 0), test_line, font=font_large)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # 최대 2줄까지만 표시
        if len(lines) > 2:
            lines = lines[:2]
        
        # 텍스트 높이 계산
        line_height = 140
        total_text_height = len(lines) * line_height + 40
        
        # 텍스트 위치 (하단 중앙)
        text_y_start = 1920 - total_text_height - 80
        
        # 배경 그라데이션 오버레이 (하단)
        overlay = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # 하단에서 위로 그라데이션 (검은색 반투명)
        for i in range(400):
            alpha = int(180 * (1 - i / 400))
            overlay_draw.rectangle([0, 1920 - 400 + i, 1080, 1920 - 400 + i + 1], fill=(0, 0, 0, alpha))
        
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img)
        
        # 각 줄의 텍스트 그리기 (그림자 효과 포함)
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font_large)
            text_width = bbox[2] - bbox[0]
            text_x = (1080 - text_width) // 2
            text_y = text_y_start + i * line_height
            
            # 그림자 효과 (약간 오른쪽 아래)
            shadow_offset = 5
            draw.text((text_x + shadow_offset, text_y + shadow_offset), line, 
                     fill=(0, 0, 0, 200), font=font_large)
            
            # 메인 텍스트 (흰색, 굵게)
            draw.text((text_x, text_y), line, fill=(255, 255, 255), font=font_large)
        
        # 3. 강조 아이콘 추가 (선택적)
        # 상단 오른쪽에 작은 아이콘 텍스트
        icon_text = "✨"
        icon_bbox = draw.textbbox((0, 0), icon_text, font=font_medium)
        icon_x = 1080 - (icon_bbox[2] - icon_bbox[0]) - 50
        icon_y = 50
        draw.text((icon_x, icon_y), icon_text, fill=(255, 215, 0), font=font_medium)
        
        # 4. 이미지 저장 (고품질)
        img.save(thumbnail_path, 'JPEG', quality=95, optimize=True)
        
        print(f"✅ 썸네일 생성 완료: {thumbnail_path}")
        return thumbnail_path


"""
AI 영상 생성 모듈 (15초~60초 YouTube Shorts)
"""
import os
import random
import re
from datetime import datetime
from moviepy.editor import (
    VideoFileClip, ImageClip, TextClip,
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
import json
import config
from enum import Enum
from pathlib import Path

# 새로운 TTS 엔진 사용 (선택적)
try:
    import sys
    # 프로젝트 루트를 경로에 추가
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    from src.pipeline.tts_engine import TTSEngine, TTSProvider
    NEW_TTS_AVAILABLE = True
except ImportError:
    NEW_TTS_AVAILABLE = False


class ContentType(Enum):
    """콘텐츠 타입"""
    HOOK = "hook"  # 한국어 속담/관용어 한 문장 학습 (짧고 강한 Hook)
    QUOTE = "quote"  # AI·비즈니스·명언·지식 한 줄
    STORY = "story"  # 스토리텔링 (심리/역사/부자습관)
    FACT = "fact"  # 숏폼 팩트 기반 영상
    SHORT_STORY = "short_story"  # AI 이미지 기반 짧은 스토리
    AUTO = "auto"  # 자동 선택


class AIVideoGenerator:
    """AI를 활용한 15초 YouTube Shorts 영상 생성 클래스"""
    
    def __init__(self, tts_provider=None):
        if config.OPENAI_API_KEY and OPENAI_AVAILABLE:
            try:
                # 간단한 초기화 (httpx 버전 호환성 문제 회피)
                self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
            except Exception as e:
                print(f"⚠️ OpenAI 클라이언트 초기화 실패: {e}")
                self.openai_client = None
        else:
            self.openai_client = None
        
        # TTS 엔진 초기화
        self.tts_engine = None
        if NEW_TTS_AVAILABLE:
            try:
                # tts_provider가 None이면 config에서 읽거나 자동 선택
                if tts_provider is None:
                    tts_provider_str = getattr(config, 'TTS_PROVIDER', None)
                    if tts_provider_str:
                        tts_provider = TTSProvider(tts_provider_str.lower())
                
                self.tts_engine = TTSEngine(provider=tts_provider)
                print(f"✅ TTS 엔진 초기화: {self.tts_engine.get_provider().value}")
            except Exception as e:
                print(f"⚠️ TTS 엔진 초기화 실패: {e}")
                print("   기본 gTTS를 사용합니다.")
                self.tts_engine = None
        else:
            self.tts_engine = None
        
        # 출력 디렉토리 생성
        os.makedirs(config.VIDEO_OUTPUT_DIR, exist_ok=True)
        os.makedirs(config.TEMP_DIR, exist_ok=True)
        os.makedirs(config.THUMBNAIL_OUTPUT_DIR, exist_ok=True)
    
    def generate_video(
        self,
        topic: str = None,
        duration: int = None,
        output_filename: str = None,
        performance_prompt: str = None,
        content_type: ContentType = None
    ) -> tuple:
        """
        AI로 YouTube Shorts 영상 생성 (55초 목표, 매번 새로운 아이디어)
        
        Args:
            topic: 영상 주제 (None이면 AI로 자동 생성 - 매번 새로운 아이디어)
            duration: 영상 길이 (초, None이면 자동 계산, 목표 55초)
            output_filename: 출력 파일명 (None이면 자동 생성)
            performance_prompt: 성과 기반 프롬프트 (선택)
            content_type: 콘텐츠 타입 (None이면 자동 선택)
        
        Returns:
            (생성된 영상 파일 경로, 스크립트 리스트, 주제) 튜플
        """
        # 주제가 없으면 AI로 새로운 주제 생성 (템플릿 사용 안 함)
        if not topic:
            topic, content_type = self._generate_topic(content_type=content_type)
        else:
            # 주제가 주어진 경우 콘텐츠 타입 자동 감지
            if content_type is None:
                content_type_str = getattr(config, "CONTENT_TYPE", "auto")
                try:
                    content_type = ContentType(content_type_str.lower())
                except ValueError:
                    content_type = ContentType.AUTO
        print(f"📹 영상 생성 시작: '{topic}' (타입: {content_type.value})")
        
        # 영상 스크립트 생성 (55초 목표, 매번 새로운 아이디어로 생성)
        script = self._generate_script(
            topic, 
            performance_prompt=performance_prompt,
            content_type=content_type
        )
        
        print(f"📝 AI 생성 스크립트: {len(script)}개 문장")
        
        # duration이 없으면 스크립트 길이에 따라 자동 계산 (55초 목표)
        if duration is None:
            # 모든 콘텐츠 타입에서 55초 목표로 설정 (충분한 이야기 포함)
            target_duration = config.SHORTS_TARGET_DURATION  # 55초
            
            # 각 문장당 약 3-4초 (충분한 내용을 담기 위해)
            avg_sentence_duration = 3.5
            calculated_duration = len(script) * avg_sentence_duration
            
            # 목표 duration(55초)과 계산된 duration 중 작은 값 사용, 최소 15초
            duration = max(15, min(target_duration, int(calculated_duration)))
            
            # 스크립트가 짧으면 더 긴 문장을 생성하도록 프롬프트 조정
            if calculated_duration < target_duration * 0.8:  # 목표의 80% 미만이면
                print(f"📝 스크립트가 짧아서 더 긴 내용 생성 필요 (현재: {calculated_duration:.1f}초, 목표: {target_duration}초)")
            
            print(f"📏 스크립트 기반 자동 길이: {duration}초 ({len(script)}개 문장, 목표: {target_duration}초, 타입: {content_type.value})")
        
        # 영상 생성
        video_path = self._create_video_from_script(script, topic, duration, output_filename)
        
        print(f"✅ 영상 생성 완료: {video_path} ({duration}초)")
        return video_path, script, topic
    
    def _get_season(self) -> str:
        """
        현재 날짜를 기반으로 계절 판단
        
        Returns:
            'spring', 'summer', 'autumn', 'winter'
        """
        now = datetime.now()
        month = now.month
        
        if month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        elif month in [9, 10, 11]:
            return 'autumn'
        else:  # 12, 1, 2
            return 'winter'
    
    def _generate_topic(self, content_type: ContentType = None) -> tuple:
        """
        AI로 인기 주제 생성 (콘텐츠 타입별, 계절 고려)
        
        Returns:
            (topic, content_type) 튜플
        """
        if content_type is None:
            content_type_str = getattr(config, 'CONTENT_TYPE', 'auto')
            try:
                content_type = ContentType(content_type_str.lower())
            except ValueError:
                content_type = ContentType.AUTO
        
        # 자동 선택 시 랜덤
        if content_type == ContentType.AUTO:
            content_type = random.choice([
                ContentType.HOOK, ContentType.QUOTE, ContentType.STORY,
                ContentType.FACT, ContentType.SHORT_STORY
            ])
        
        # 현재 계절 확인
        current_season = self._get_season()
        
        # 타입별 주제 생성
        if content_type == ContentType.HOOK:
            topics = [
                # 🔥 계절 HOOK
                "여름 전기요금 폭등 막는 단 한 가지",
                "장마철 곰팡이 안 생기는 집의 비밀",
                "가을 환절기 집이 깨끗해지는 정리법",
                "겨울 준비를 지금 시작해야 하는 이유",
                "겨울 난방비가 확 줄어드는 설정 하나",
                # 🏠 생활 HOOK
                "집이 항상 깨끗한 사람들의 공통점",
                "냉장고 음식 안 버리는 간단한 기준",
                "옷장이 정리되는 5분 법칙",
                "자동차 고장 막는 1가지 체크",
                "전기요금 새는 포인트 한 곳",
                # 💰 돈·재테크 HOOK
                "월급을 모으는 사람과 못 모으는 사람의 차이",
                "건드리면 돈이 모이는 루틴 하나",
                "부자가 되려면 반드시 버려야 할 습관",
                "절약이 아니라 투자를 해야 하는 이유",
                "평범한 사람이 자산을 키우는 가장 빠른 방법",
                # 🧠 자기계발 HOOK
                "아침 10분이 인생을 바꾸는 이유",
                "성공하는 사람 1%의 루틴",
                "일이 잘 풀리는 사람들의 사고방식",
            ]
            # 계절별 우선 주제
            seasonal_topics = {
                'spring': ["가을 환절기 집이 깨끗해지는 정리법", "옷장이 정리되는 5분 법칙"],
                'summer': ["여름 전기요금 폭등 막는 단 한 가지", "장마철 곰팡이 안 생기는 집의 비밀", "전기요금 새는 포인트 한 곳"],
                'autumn': ["가을 환절기 집이 깨끗해지는 정리법", "겨울 준비를 지금 시작해야 하는 이유", "옷장이 정리되는 5분 법칙"],
                'winter': ["겨울 준비를 지금 시작해야 하는 이유", "겨울 난방비가 확 줄어드는 설정 하나", "자동차 고장 막는 1가지 체크"]
            }
        elif content_type == ContentType.QUOTE:
            topics = [
                # 🌤 계절·생활 명언
                "정리는 공간을 바꾸고, 공간은 생각을 바꾼다.",
                "계절이 바뀌면 삶도 정리할 때다.",
                "깨끗한 집은 마음을 쉬게 해준다.",
                "작은 루틴이 큰 평온을 만든다.",
                "겨울 준비는 '불편함'을 미리 없애는 과정이다.",
                # 💸 돈·재테크 명언
                "돈은 저축이 아니라 구조가 만든다.",
                "투자는 타이밍보다 지속이 이긴다.",
                "지출을 알면 자유를 얻는다.",
                "모으는 사람보다 관리하는 사람이 부자가 된다.",
                "부의 차이는 선택의 누적으로 결정된다.",
                # 🧠 자기계발 명언
                "루틴이 습관을 만들고, 습관이 삶을 만든다.",
                "어제보다 1% 나으면 충분하다.",
                "꾸준함은 천재를 이긴다.",
            ]
            seasonal_topics = {
                'spring': ["계절이 바뀌면 삶도 정리할 때다.", "정리는 공간을 바꾸고, 공간은 생각을 바꾼다."],
                'summer': ["작은 루틴이 큰 평온을 만든다.", "깨끗한 집은 마음을 쉬게 해준다."],
                'autumn': ["계절이 바뀌면 삶도 정리할 때다.", "정리는 공간을 바꾸고, 공간은 생각을 바꾼다."],
                'winter': ["겨울 준비는 '불편함'을 미리 없애는 과정이다.", "작은 루틴이 큰 평온을 만든다."]
            }
        elif content_type == ContentType.STORY:
            topics = [
                # 🌤 계절·라이프 스토리
                "장마철마다 곰팡이에 시달리던 집을 바꾼 한 사람의 이야기",
                "매년 겨울마다 난방비 폭탄 맞던 가족이 바뀐 이유",
                "옷장이 항상 지저분하던 사람이 계절 교체 루틴으로 변한 과정",
                "자동차 점검을 미뤄 큰 수리비를 낼 뻔했던 직장인의 이야기",
                # 💸 돈·재테크 스토리
                "월급 280으로 살던 사람이 3년 만에 자산 3억 만든 이야기",
                "작은 자동투자 하나로 인생이 바뀐 평범한 직장인",
                "소비 습관을 바꿨더니 매달 30만원이 남기 시작한 실화",
                "경제적 자유까지 걸린 시간을 기록한 사람의 이야기",
                # 🧠 자기계발 스토리
                "하루 10분 루틴으로 삶이 달라진 사람",
                "계획만 하던 사람이 실행하는 사람이 되기까지",
            ]
            seasonal_topics = {
                'spring': ["옷장이 항상 지저분하던 사람이 계절 교체 루틴으로 변한 과정"],
                'summer': ["장마철마다 곰팡이에 시달리던 집을 바꾼 한 사람의 이야기"],
                'autumn': ["옷장이 항상 지저분하던 사람이 계절 교체 루틴으로 변한 과정"],
                'winter': ["매년 겨울마다 난방비 폭탄 맞던 가족이 바뀐 이유", "자동차 점검을 미뤄 큰 수리비를 낼 뻔했던 직장인의 이야기"]
            }
        elif content_type == ContentType.FACT:
            topics = [
                # 🌤 계절·생활 FACT
                "여름 전기요금이 실제로 새는 지점",
                "가을 환절기에 집이 가장 더러워지는 이유",
                "겨울 난방비가 크게 차이 나는 과학적 원리",
                "옷이 변색되는 진짜 이유",
                "냉장고 냄새가 다시 생기는 구조적 원인",
                # 🚗 자동차 FACT
                "겨울철 엔진오일 점검이 중요한 이유",
                "타이어 마모가 사고 위험을 높이는 수치",
                "와이퍼를 계절별로 교체해야 하는 이유",
                # 💰 돈·경제 FACT
                "부자들이 지출을 기록하는 진짜 이유",
                "복리가 시간이 지날수록 폭발적으로 커지는 구조",
                "ETF가 초보에게 좋은 이유",
                # 🧠 자기계발 FACT
                "아침 루틴이 집중력을 높이는 과학적 근거",
                "작은 습관이 의사결정을 바꾸는 이유",
            ]
            seasonal_topics = {
                'spring': ["가을 환절기에 집이 가장 더러워지는 이유", "옷이 변색되는 진짜 이유"],
                'summer': ["여름 전기요금이 실제로 새는 지점", "냉장고 냄새가 다시 생기는 구조적 원인"],
                'autumn': ["가을 환절기에 집이 가장 더러워지는 이유", "와이퍼를 계절별로 교체해야 하는 이유"],
                'winter': ["겨울 난방비가 크게 차이 나는 과학적 원리", "겨울철 엔진오일 점검이 중요한 이유", "타이어 마모가 사고 위험을 높이는 수치"]
            }
        elif content_type == ContentType.SHORT_STORY:
            topics = [
                # 🌤 계절·정리·생활 짧은 스토리
                "옷장 정리 하나로 출근 스트레스가 줄어든 이야기",
                "겨울 대비를 한 번 해봤더니 난방비가 절반이 된 사례",
                "냉장고를 구역별로 나눴더니 음식 쓰레기가 줄어든 이유",
                "습기 관리를 시작하자 집 냄새가 사라진 하루",
                # 💸 짧은 돈 스토리
                "적금만 하던 사람이 자동투자 바꾸고 돈이 남기 시작한 이유",
                "한 달 지출 점검만 했는데 통장이 달라진 이야기",
                # 🧠 자기계발 짧은 스토리
                "하루 5분 루틴이 삶을 바꾼 순간",
                "작은 선택이 큰 변화를 만든 경험",
            ]
            seasonal_topics = {
                'spring': ["옷장 정리 하나로 출근 스트레스가 줄어든 이야기", "습기 관리를 시작하자 집 냄새가 사라진 하루"],
                'summer': ["냉장고를 구역별로 나눴더니 음식 쓰레기가 줄어든 이유", "습기 관리를 시작하자 집 냄새가 사라진 하루"],
                'autumn': ["옷장 정리 하나로 출근 스트레스가 줄어든 이야기"],
                'winter': ["겨울 대비를 한 번 해봤더니 난방비가 절반이 된 사례"]
            }
        else:
            # 기본 주제
            topics = [
                "지금 바로 할 수 있는 계절 준비",
                "돈을 아끼지 않고도 생활이 편해지는 방법",
                "오늘 하루를 바꾸는 간단한 루틴",
            ]
            seasonal_topics = {
                'spring': ["지금 바로 할 수 있는 계절 준비"],
                'summer': ["지금 바로 할 수 있는 계절 준비"],
                'autumn': ["지금 바로 할 수 있는 계절 준비"],
                'winter': ["지금 바로 할 수 있는 계절 준비"]
            }
        
        # 계절에 맞는 주제를 우선적으로 선택 (50% 확률)
        if random.random() < 0.5 and current_season in seasonal_topics:
            seasonal_list = seasonal_topics[current_season]
            if seasonal_list:
                topic = random.choice(seasonal_list)
                print(f"🍂 계절 주제 선택: {current_season} → '{topic}'")
                return topic, content_type
        
        # 일반 주제 선택
        topic = random.choice(topics)
        return topic, content_type
    
    def _generate_script(self, topic: str, performance_prompt: str = None, content_type: ContentType = None) -> list:
        """AI로 영상 스크립트 생성 (콘텐츠 타입별 최적화)"""
        if self.openai_client:
            try:
                # gpt-4o-mini 또는 gpt-4o 사용 시도 (더 접근 가능)
                models_to_try = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
                response = None
                last_error = None
                
                # 콘텐츠 타입별 설정 (55초 목표로 충분한 내용 생성)
                prefer_short = False  # 55초 목표이므로 짧은 영상 비활성화
                
                if content_type is None:
                    content_type_str = getattr(config, 'CONTENT_TYPE', 'auto')
                    try:
                        content_type = ContentType(content_type_str.lower())
                    except ValueError:
                        content_type = ContentType.AUTO
                
                # 타입별 시스템 프롬프트 구성 (모두 55초 목표)
                target_duration = config.SHORTS_TARGET_DURATION  # 55초
                
                if content_type == ContentType.HOOK:
                    system_prompt = """당신은 YouTube Shorts용 Hook 영상 스크립트 작성 전문가입니다.
- 첫 3초 안에 강력한 Hook 문장으로 시청자의 관심을 끌어야 합니다
- 한국어 속담, 관용어, 명언 등에 집중하세요
- **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요**
- 목표는 약 55초 분량이며, 충분한 설명과 예시를 포함하세요
- 각 문장은 3-4초 분량이며, 총 12-16개 문장으로 작성하세요
- Hook 문장을 반복하거나 강조하고, 자세한 설명을 추가하세요"""
                    max_sentences = 16
                elif content_type == ContentType.QUOTE:
                    system_prompt = """당신은 YouTube Shorts용 명언/지식 한 줄 영상 스크립트 작성 전문가입니다.
- 첫 문장에 강력한 명언이나 인사이트를 배치하세요
- AI, 비즈니스, 자기계발, 투자 등 지식 한 줄에 집중하세요
- **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요**
- 목표는 약 55초 분량이며, 충분한 설명과 실생활 적용법을 포함하세요
- 각 문장은 3-4초 분량이며, 총 12-16개 문장으로 작성하세요
- 명언을 자세히 설명하고 실생활 적용법과 예시를 제시하세요"""
                    max_sentences = 16
                elif content_type == ContentType.STORY:
                    system_prompt = """당신은 YouTube Shorts용 스토리텔링 영상 스크립트 작성 전문가입니다.
- 첫 문장에 강력한 Hook으로 시작하세요
- 심리, 역사, 부자습관 등 스토리를 통해 교훈을 전달하세요
- **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요**
- 목표는 약 55초 분량이며, 스토리를 자세히 전개하세요
- 스토리 구조: Hook → 전개 → 세부 설명 → 교훈 → 마무리
- 각 문장은 3-4초 분량이며, 총 12-16개 문장으로 작성하세요"""
                    max_sentences = 16
                elif content_type == ContentType.FACT:
                    system_prompt = """당신은 YouTube Shorts용 팩트 기반 영상 스크립트 작성 전문가입니다.
- 첫 문장에 놀라운 팩트를 배치하여 Hook을 만드세요
- 과학, 역사, 인체, 우주 등 놀라운 사실을 전달하세요
- **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요**
- 목표는 약 55초 분량이며, 팩트를 자세히 설명하세요
- 각 문장은 3-4초 분량이며, 총 12-16개 문장으로 작성하세요
- 팩트를 설명하고 왜 놀라운지, 어떻게 발견되었는지 등 자세한 배경을 포함하세요"""
                    max_sentences = 16
                elif content_type == ContentType.SHORT_STORY:
                    system_prompt = """당신은 YouTube Shorts용 짧은 스토리 영상 스크립트 작성 전문가입니다.
- 첫 문장에 강력한 Hook으로 시작하세요
- 인생 교훈, 영감, 성공 스토리 등을 자세히 전달하세요
- **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요**
- 목표는 약 55초 분량이며, 스토리를 충분히 전개하세요
- 스토리 구조: Hook → 사건 전개 → 세부 설명 → 교훈 → 마무리
- 각 문장은 3-4초 분량이며, 총 12-16개 문장으로 작성하세요"""
                    max_sentences = 16
                else:
                    # 기본 설정
                    system_prompt = """당신은 YouTube Shorts용 영상 스크립트 작성 전문가입니다.
- 설명이 충분하도록 자세하게 작성하세요
- **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요**
- 목표는 약 55초 분량이며, 각 문장은 3-4초 분량입니다
- YouTube Shorts는 최대 60초이므로 55초 이내로 작성해야 합니다
- 총 12-16개 문장으로 작성하여 충분한 내용을 담으세요"""
                    max_sentences = 16
                
                # 성과 기반 프롬프트 추가
                if performance_prompt:
                    system_prompt += "\n\n" + performance_prompt
                
                # 사용자 프롬프트 구성
                user_prompt = f"'{topic}'에 대한 YouTube Shorts 영상 스크립트를 작성해주세요. 각 문장은 3-4초 분량이며, 총 {max_sentences}개 문장으로 작성하여 약 {target_duration}초 분량이 되도록 충분히 자세하게 작성해주세요 (최대 60초 제한). **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요.** 중요한 점: 순수한 대사나 설명만 작성하고, '배경음악', '자막', '시작' 같은 제작 지시사항은 절대 포함하지 마세요. 첫 문장은 반드시 강력한 Hook이어야 하며, 내용을 충분히 전개하여 시청자가 이해할 수 있도록 자세히 설명하세요."
                
                for model in models_to_try:
                    try:
                        response = self.openai_client.chat.completions.create(
                            model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ],
                            max_tokens=800,  # 55초 분량을 위해 토큰 증가
                            temperature=0.7
                        )
                        script_text = response.choices[0].message.content
                        # 문장별로 분리 (줄바꿈과 마침표 모두 고려)
                        sentences = []
                        # 줄바꿈으로 분리
                        for line in script_text.split('\n'):
                            line = line.strip()
                            if not line:
                                continue
                            # 마침표로도 분리 (긴 문장을 여러 문장으로 나눔)
                            for sent in re.split(r'[.!?。！？]\s+', line):
                                sent = sent.strip()
                                if sent:
                                    sentences.append(sent)
                        
                        # 불필요한 텍스트 필터링
                        filter_keywords = [
                            '배경음악', '음악', 'BGM', 'bgm', '배경', '시작', '종료',
                            '자막', '타이틀', '제목', '인트로', '아웃트로',
                            '참고', '주의', '설명', '참고사항'
                        ]
                        
                        filtered_sentences = []
                        for s in sentences:
                            # 숫자나 불필요한 기호로 시작하는 것 제거
                            if s.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.', '11.', '12.', '13.', '14.', '15.', '16.', '-', '*', '•')):
                                # 숫자 제거 후 문장만 추출
                                s = re.sub(r'^\d+\.\s*', '', s).strip()
                            # 너무 짧은 문장 제거 (최소 10자 이상)
                            if len(s) < 10:
                                continue
                            # 필터 키워드가 포함된 문장 제거
                            if any(keyword in s for keyword in filter_keywords):
                                continue
                            # 괄호 안의 설명 제거 (예: "텍스트 (참고사항)" -> "텍스트")
                            s = re.sub(r'\([^)]*\)', '', s).strip()
                            s = re.sub(r'\[[^\]]*\]', '', s).strip()
                            if s and len(s) >= 10:
                                filtered_sentences.append(s)
                        
                        # 최소 문장 수 확인 (55초 목표를 위해 최소 12개 이상 필요)
                        if len(filtered_sentences) < 12:
                            print(f"⚠️ 생성된 문장이 부족합니다 ({len(filtered_sentences)}개). 원본 스크립트를 다시 확인합니다.")
                            # 원본 텍스트에서 더 많은 문장 추출 시도
                            all_sentences = re.split(r'[.!?。！？]\s+', script_text)
                            for sent in all_sentences:
                                sent = sent.strip()
                                if len(sent) >= 10 and sent not in filtered_sentences:
                                    # 필터링 다시 적용
                                    if not any(keyword in sent for keyword in filter_keywords):
                                        filtered_sentences.append(sent)
                                        if len(filtered_sentences) >= max_sentences:
                                            break
                        
                        print(f"📝 생성된 문장 수: {len(filtered_sentences)}개 (목표: {max_sentences}개)")
                        return filtered_sentences[:max_sentences]  # 최대 문장 수 (약 55초)
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
                else:
                    print(f"⚠️ AI 스크립트 생성 실패: {e}")
                
                # AI 생성 실패 시 기본 스크립트 반환 (템플릿 없이)
                print(f"⚠️ AI 스크립트 생성 실패로 기본 스크립트를 사용합니다.")
                return [
                    f"{topic}에 대해 알아보겠습니다.",
                    "중요한 포인트를 알려드립니다.",
                    "실천하면 효과를 볼 수 있습니다.",
                    "지금 바로 시작하세요!"
                ]
        
        # AI 생성이 성공하지 못한 경우 (self.openai_client가 None인 경우)
        if not self.openai_client:
            print(f"⚠️ OpenAI 클라이언트가 없어 기본 스크립트를 사용합니다.")
            return [
                f"{topic}에 대해 알아보겠습니다.",
                "중요한 포인트를 알려드립니다.",
                "실천하면 효과를 볼 수 있습니다.",
                "지금 바로 시작하세요!"
            ]
        
        # 이 코드는 실행되지 않아야 하지만 안전을 위해 추가
        return [
            f"{topic}에 대해 알아보겠습니다.",
            "중요한 포인트를 알려드립니다.",
            "실천하면 효과를 볼 수 있습니다.",
            "지금 바로 시작하세요!"
        ]
    
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
                # pop 전 길이 저장 (동기화 확인용)
                script_len_before_pop = len(script)
                # 마지막 문장 제거
                removed_sentence = script.pop()
                removed_audio_duration = sentence_audio_durations.pop()
                # audio_clips도 동기화를 위해 제거
                # script와 sentence_audio_durations는 항상 같은 길이이므로,
                # audio_clips의 길이가 pop 전 script 길이와 같거나 더 크면 pop
                if len(audio_clips) >= script_len_before_pop:
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
        
        # 배경 미디어 그룹핑: 2-3개 문장마다 배경 변경 (관련 문장들은 같은 배경 사용)
        background_groups = []
        group_size = 2  # 2개 문장마다 배경 변경
        use_background_video = getattr(config, 'USE_BACKGROUND_VIDEO', True)
        
        # 각 그룹에서 사용할 배경 영상의 시작 시간을 추적 (순차 재생용)
        video_start_times = {}  # {bg_video_path: current_start_time}
        
        for i in range(0, len(script), group_size):
            group_end = min(i + group_size, len(script))
            group_sentence = script[i]
            group_duration = sum(sentence_audio_durations[i:group_end])
            
            # 배경 영상 다운로드 시도 (USE_BACKGROUND_VIDEO가 true이고 Pexels API 키가 있을 때)
            bg_video_path = None
            if use_background_video and config.PEXELS_API_KEY:
                bg_video_path = self._download_video_for_sentence(group_sentence, i, group_duration)
            
            # 배경 영상이 없으면 이미지 사용
            bg_image = None
            if not bg_video_path:
                bg_image = self._download_image_for_sentence(group_sentence, i)
                if bg_image is None:
                    # 이미지 다운로드 실패 시 그라데이션 배경 사용
                    bg_image = self._create_gradient_background(i, len(script))
            
            # 배경 영상이 있으면 시작 시간 초기화 (아직 사용하지 않았으면)
            if bg_video_path and bg_video_path not in video_start_times:
                video_start_times[bg_video_path] = 0.0
            
            background_groups.append((i, group_end, bg_video_path, bg_image))
            media_type = "영상" if bg_video_path else "이미지"
            print(f"   배경 미디어 그룹 {len(background_groups)}: 문장 {i+1}-{group_end} ({media_type}) - {group_sentence[:30]}...)")
        
        # 각 문장별로 영상 클립 생성
        for i, sentence in enumerate(script):
            # 실제 음성 길이에 맞춘 duration 사용
            sentence_duration = sentence_audio_durations[i]
            
            # 해당 문장이 속한 그룹의 배경 미디어 찾기
            bg_video_path = None
            bg_image = None
            for group_start, group_end, group_video, group_image in background_groups:
                if group_start <= i < group_end:
                    bg_video_path = group_video
                    bg_image = group_image
                    break
            
            # 배경 영상이 있으면 영상 클립 사용
            if bg_video_path and os.path.exists(bg_video_path):
                try:
                    print(f"   📹 배경 영상 사용: {bg_video_path}")
                    source_video = VideoFileClip(bg_video_path)
                    source_duration = source_video.duration
                    print(f"   원본 영상 길이: {source_duration:.2f}초, 필요한 길이: {sentence_duration:.2f}초")
                    
                    # 같은 배경 영상 파일을 여러 문장에서 사용할 때, 순차적으로 재생 (반복 없이)
                    # 각 문장마다 이전 문장의 끝 지점부터 시작 (전체 영상을 순차적으로 재생)
                    if bg_video_path in video_start_times and video_start_times[bg_video_path] is not None:
                        start_time = video_start_times[bg_video_path]
                    else:
                        # 처음 사용하는 경우 0부터 시작
                        start_time = 0.0
                        video_start_times[bg_video_path] = 0.0
                    
                    # 영상이 필요한 길이보다 길거나 같으면 사용
                    if source_duration >= sentence_duration:
                        # 시작점이 영상 끝을 넘어가면 이미지로 대체 (반복하지 않음)
                        if start_time >= source_duration:
                            print(f"   ⚠️ 문장 {i+1}: 배경 영상이 끝에 도달 ({start_time:.2f}초 >= {source_duration:.2f}초), 이미지로 대체")
                            source_video.close()
                            bg_video_path = None  # 이미지로 대체하기 위해 None으로 설정
                            # 아래 이미지 처리 로직으로 넘어감
                        else:
                            end_time = start_time + sentence_duration
                            # end_time이 영상 길이를 넘어가면 남은 부분만 사용하고 다음 문장은 이미지로
                            if end_time > source_duration:
                                # 영상 끝까지만 사용
                                end_time = source_duration
                                # 다음 문장을 위해 시작점을 None으로 설정 (이미지 사용)
                                video_start_times[bg_video_path] = None
                            else:
                                # 다음 문장을 위해 시작점 업데이트
                                video_start_times[bg_video_path] = end_time
                            
                            # subclip으로 정확히 자르기 (반복 방지)
                            safe_end_time = min(end_time, source_duration - 0.01)  # 0.01초 여유
                            video_clip = source_video.subclip(start_time, safe_end_time)
                            
                            print(f"   📍 배경 영상 재생 위치: {start_time:.2f}초~{safe_end_time:.2f}초 (원본: {source_duration:.2f}초)")
                            
                            # subclip이 정확한 길이로 잘렸는지 확인하고, 필요시 다시 정확히 자르기
                            actual_clip_duration = video_clip.duration
                            if abs(actual_clip_duration - sentence_duration) > 0.01:
                                # 정확한 길이로 다시 자르기
                                if actual_clip_duration > sentence_duration:
                                    video_clip = video_clip.subclip(0, sentence_duration)
                                    actual_clip_duration = video_clip.duration
                            
                            # 정확한 duration으로 강제 설정
                            video_clip = video_clip.set_duration(sentence_duration)
                            print(f"   문장 {i+1} 배경 영상 클립: {start_time:.2f}초~{safe_end_time:.2f}초 (원본: {source_duration:.2f}초, 실제: {actual_clip_duration:.2f}초, 설정: {video_clip.duration:.2f}초)")
                    else:
                        # 영상이 짧으면 반복하지 않고 이미지로 대체
                        print(f"   ⚠️ 문장 {i+1}: 배경 영상이 짧아서 ({source_duration:.2f}초 < {sentence_duration:.2f}초) 이미지로 대체")
                        source_video.close()
                        bg_video_path = None  # 이미지로 대체하기 위해 None으로 설정
                        # 다음 문장도 이미지 사용하도록 시작점 제거
                        if bg_video_path in video_start_times:
                            video_start_times[bg_video_path] = None
                        # 아래 이미지 처리 로직으로 넘어감
                    
                    # video_clip이 정의된 경우에만 처리 (이미지로 대체하는 경우는 아래 이미지 처리로 넘어감)
                    if bg_video_path is not None:
                        # 해상도 설정
                        video_clip = video_clip.resize((1080, 1920))
                        # duration은 이미 설정되었지만, resize 후에도 확인
                        if abs(video_clip.duration - sentence_duration) > 0.01:
                            print(f"   문장 {i+1} duration 재설정: {video_clip.duration:.2f}초 -> {sentence_duration:.2f}초")
                        video_clip = video_clip.set_duration(sentence_duration)
                        print(f"   문장 {i+1} 최종 클립 duration: {video_clip.duration:.2f}초 (목표: {sentence_duration:.2f}초)")
                        
                        # 자막 추가
                        try:
                            print(f"   문장 {i+1} 배경 영상 자막 추가 시도: {sentence[:30]}...")
                            subtitle_clip = self._create_subtitle_clip(sentence, sentence_duration)
                            if subtitle_clip:
                                video_clip = CompositeVideoClip([video_clip, subtitle_clip])
                                # CompositeVideoClip 후 duration 강제 설정 (반복 방지)
                                video_clip = video_clip.set_duration(sentence_duration)
                                print(f"   ✅ 배경 영상 자막 추가 성공 (duration: {video_clip.duration:.2f}초)")
                            else:
                                print(f"   ⚠️ 자막 클립이 None입니다")
                        except Exception as e:
                            print(f"   ❌ 자막 추가 실패 (계속 진행): {e}")
                            import traceback
                            traceback.print_exc()
                        
                        # 페이드 효과 (duration 유지)
                        if i == 0:
                            video_clip = video_clip.fx(fadein, 0.5)
                            video_clip = video_clip.set_duration(sentence_duration)  # 페이드 후 duration 재설정
                        elif i == len(script) - 1:
                            video_clip = video_clip.fx(fadeout, 0.5)
                            video_clip = video_clip.set_duration(sentence_duration)  # 페이드 후 duration 재설정
                        
                        # 최종 duration 확인 및 강제 설정 (반복 방지)
                        if abs(video_clip.duration - sentence_duration) > 0.01:
                            print(f"   문장 {i+1} 최종 duration 재설정: {video_clip.duration:.2f}초 -> {sentence_duration:.2f}초")
                            video_clip = video_clip.set_duration(sentence_duration)
                        
                        # source_video는 나중에 닫기 (video_clip이 완전히 생성된 후)
                        print(f"   ✅ 문장 {i+1} 클립 추가: {video_clip.duration:.2f}초 (목표: {sentence_duration:.2f}초)")
                        print(f"   📁 사용한 배경 영상: {bg_video_path}")
                        
                        # 클립 전환 지점 확인을 위한 로깅
                        if i > 0 and len(clips) > 0:
                            prev_clip = clips[-1]
                            prev_end_time = sum(c.duration for c in clips)
                            print(f"   🔄 클립 전환: 이전 클립({prev_clip.duration:.2f}초) -> 현재 클립({video_clip.duration:.2f}초)")
                            print(f"      이전 클립 끝 시간: {prev_end_time:.2f}초")
                            print(f"      현재 클립 시작 시간: {prev_end_time:.2f}초")
                        
                        clips.append(video_clip)
                        # source_video는 나중에 정리 (close하지 않음 - subclip이 참조하고 있음)
                        continue
                except Exception as e:
                    print(f"   배경 영상 사용 실패, 이미지로 대체: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 배경 영상이 없거나 실패 시 해당 문장에 맞는 이미지 다운로드
            if bg_image is None:
                print(f"   🖼️ 문장 {i+1}에 맞는 이미지 다운로드 시도: {sentence[:30]}...")
                bg_image = self._download_image_for_sentence(sentence, i)
                if bg_image is None:
                    # 이미지 다운로드 실패 시 그라데이션 배경 사용
                    print(f"   ⚠️ 이미지 다운로드 실패, 그라데이션 배경 사용")
                    bg_image = self._create_gradient_background(i, len(script))
            
            # 자막 추가 (이미지에 텍스트 그리기)
            text_image = self._draw_text_on_image(bg_image.copy(), sentence)
            print(f"   문장 {i+1} 자막 추가: {sentence[:30]}...")
            
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
            
            # 페이드 효과 (duration 유지)
            if i == 0:
                # 첫 클립만 페이드 인
                img_clip = img_clip.fx(fadein, 0.5)
                img_clip = img_clip.set_duration(sentence_duration)  # 페이드 후 duration 재설정
            elif i == len(script) - 1:
                # 마지막 클립만 페이드 아웃
                img_clip = img_clip.fx(fadeout, 0.5)
                img_clip = img_clip.set_duration(sentence_duration)  # 페이드 후 duration 재설정
            # 중간 클립들은 페이드 효과 없음 (부드러운 전환)
            
            # 최종 duration 확인 및 강제 설정 (반복 방지)
            if abs(img_clip.duration - sentence_duration) > 0.01:
                print(f"   문장 {i+1} 이미지 클립 duration 재설정: {img_clip.duration:.2f}초 -> {sentence_duration:.2f}초")
            img_clip = img_clip.set_duration(sentence_duration)
            
            print(f"   ✅ 문장 {i+1} 이미지 클립 추가: {img_clip.duration:.2f}초 (목표: {sentence_duration:.2f}초)")
            
            # 클립 전환 지점 확인을 위한 로깅
            if i > 0 and len(clips) > 0:
                prev_clip = clips[-1]
                print(f"   🔄 클립 전환: 이전 클립({prev_clip.duration:.2f}초) -> 현재 클립({img_clip.duration:.2f}초)")
                print(f"      이전 클립 끝 시간: {sum(c.duration for c in clips):.2f}초")
                print(f"      현재 클립 시작 시간: {sum(c.duration for c in clips):.2f}초")
            
            clips.append(img_clip)
        
        # 모든 클립 연결 (영상이 잘리지 않도록 정확한 duration 설정)
        if not clips:
            raise ValueError("생성된 클립이 없습니다.")
        
        # 각 클립의 duration 확인 및 중복 제거
        print(f"📊 생성된 클립 수: {len(clips)}")
        for idx, clip in enumerate(clips):
            print(f"   클립 {idx+1}: {clip.duration:.2f}초")
        
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
        
        # 클립 연결 (중복 방지)
        print(f"🔗 클립 연결 중... (총 {len(clips)}개)")
        # 각 클립의 duration을 확인하고 정확히 설정
        for idx, clip in enumerate(clips):
            if idx < len(sentence_audio_durations):
                expected_duration = sentence_audio_durations[idx]
                if abs(clip.duration - expected_duration) > 0.01:
                    print(f"   클립 {idx+1} duration 조정: {clip.duration:.2f}초 -> {expected_duration:.2f}초")
                    clips[idx] = clip.set_duration(expected_duration)
        
        # 클립 연결 전에 각 클립의 duration 확인
        print(f"📊 연결 전 클립 duration 확인:")
        for idx, clip in enumerate(clips):
            print(f"   클립 {idx+1}: {clip.duration:.2f}초")
        
        # 클립 연결 (각 클립이 정상인지 확인 후 연결)
        print(f"🔗 클립 연결 시작 (총 {len(clips)}개 클립)")
        # 각 클립이 None이 아닌지 확인
        valid_clips = []
        for idx, clip in enumerate(clips):
            if clip is None:
                print(f"   ⚠️ 클립 {idx+1}이 None입니다. 건너뜁니다.")
                continue
            try:
                # 클립이 유효한지 확인
                _ = clip.duration
                valid_clips.append(clip)
            except Exception as e:
                print(f"   ⚠️ 클립 {idx+1}이 유효하지 않습니다: {e}")
                continue
        
        if len(valid_clips) != len(clips):
            print(f"⚠️ 유효한 클립 수: {len(valid_clips)}/{len(clips)}")
        
        if not valid_clips:
            raise ValueError("유효한 클립이 없습니다.")
        
        # 클립 연결 (method를 명시하지 않으면 기본값 사용, 각 클립을 순차적으로 연결)
        # method="compose"는 오디오 트랙이 있을 때 사용하지만, 비디오만 있을 때는 기본값이 더 안전
        print(f"   각 클립 정보:")
        for idx, clip in enumerate(valid_clips):
            print(f"      클립 {idx+1}: duration={clip.duration:.2f}초, size={clip.size}")
        
        # 기본 method 사용 (각 클립을 순차적으로 연결, 중복 없음)
        # 각 클립의 duration을 다시 한 번 확인하고 강제 설정
        print(f"   클립 duration 최종 확인 및 조정:")
        for idx, clip in enumerate(valid_clips):
            expected_dur = sentence_audio_durations[idx] if idx < len(sentence_audio_durations) else clip.duration
            if abs(clip.duration - expected_dur) > 0.01:
                print(f"      클립 {idx+1} duration 조정: {clip.duration:.2f}초 -> {expected_dur:.2f}초")
                valid_clips[idx] = clip.set_duration(expected_dur)
            else:
                print(f"      클립 {idx+1}: {clip.duration:.2f}초 (정상)")
        
        # 클립 연결 (각 클립을 순차적으로 연결)
        # method를 명시하지 않으면 기본값이 사용되지만, 명시적으로 지정하여 중복 방지
        print(f"   클립 연결 실행 중...")
        # 각 클립이 정확히 한 번만 연결되도록 보장
        print(f"   연결할 클립 목록:")
        for idx, clip in enumerate(valid_clips):
            print(f"      클립 {idx+1}: {clip.duration:.2f}초")
        
        # method를 명시하지 않으면 기본적으로 순차 연결 (중복 없음)
        # 각 클립을 연결하기 전에 duration을 다시 한 번 강제 설정 (반복 방지)
        print(f"   연결 전 각 클립 duration 최종 확인 및 강제 설정:")
        for idx, clip in enumerate(valid_clips):
            expected_dur = sentence_audio_durations[idx] if idx < len(sentence_audio_durations) else clip.duration
            # duration을 정확히 설정하고, subclip으로도 확인
            if abs(clip.duration - expected_dur) > 0.01:
                print(f"      클립 {idx+1} duration 재설정: {clip.duration:.2f}초 -> {expected_dur:.2f}초")
                # duration을 설정하고, 필요시 subclip으로도 정확히 자르기
                valid_clips[idx] = clip.set_duration(expected_dur)
                # 추가 안전장치: duration이 여전히 맞지 않으면 subclip으로 강제 자르기
                if abs(valid_clips[idx].duration - expected_dur) > 0.01:
                    print(f"         클립 {idx+1} subclip으로 강제 자르기: {valid_clips[idx].duration:.2f}초 -> {expected_dur:.2f}초")
                    valid_clips[idx] = valid_clips[idx].subclip(0, expected_dur)
                    valid_clips[idx] = valid_clips[idx].set_duration(expected_dur)
            print(f"      클립 {idx+1} 최종 duration: {valid_clips[idx].duration:.2f}초")
        
        # 클립 연결 (각 클립이 정확히 한 번만 재생되도록)
        # 중복 방지를 위해 명시적으로 method를 지정하지 않음 (기본값 사용)
        print(f"   클립 연결 실행 중... (총 {len(valid_clips)}개 클립)")
        
        # 각 클립이 정확히 한 번만 포함되도록 확인
        print(f"   연결 전 최종 검증:")
        for idx, clip in enumerate(valid_clips):
            expected_dur = sentence_audio_durations[idx] if idx < len(sentence_audio_durations) else clip.duration
            print(f"      클립 {idx+1}: duration={clip.duration:.2f}초 (예상: {expected_dur:.2f}초)")
        
        # concatenate_videoclips 호출 (각 클립을 정확히 한 번씩만 연결)
        # method="chain"은 기본값이지만 명시적으로 지정하여 중복 방지
        # transition=None으로 설정하여 클립 경계에서 중복 방지
        print(f"   최종 연결: {len(valid_clips)}개 클립을 순차적으로 연결 (경계 중복 방지)")
        final_video = concatenate_videoclips(valid_clips, method="chain", transition=None)
        
        # 연결 직후 즉시 정확한 길이로 자르기 (반복 방지)
        clips_total = sum(c.duration for c in valid_clips)
        actual_total_duration = sum(sentence_audio_durations)
        target_duration = clips_total  # 클립 합계를 기준으로 사용 (가장 정확함)
        
        print(f"📏 예상 총 길이: {actual_total_duration:.2f}초, 클립 합계: {clips_total:.2f}초, 연결 후: {final_video.duration:.2f}초")
        
        # 연결 직후 즉시 정확한 길이로 자르기 (반복 방지)
        if abs(final_video.duration - target_duration) > 0.01:
            print(f"⚠️ 연결 직후 길이 불일치 감지! ({final_video.duration:.2f}초 vs {target_duration:.2f}초)")
            print(f"   즉시 정확한 길이로 자르는 중...")
            final_video = final_video.subclip(0, target_duration)
            final_video = final_video.set_duration(target_duration)
            print(f"   조정 후: {final_video.duration:.2f}초")
        
        # 연결된 영상의 실제 프레임 수 확인
        if final_video.duration > 0:
            expected_frames = int(target_duration * 30)  # 30fps 기준
            actual_frames = int(final_video.duration * 30)
            print(f"📊 예상 프레임 수: {expected_frames}, 실제 프레임 수: {actual_frames}")
            
            # 프레임 수가 예상보다 많으면 강제로 정확한 길이로 자르기 (반복 감지)
            if actual_frames > expected_frames * 1.05:  # 5% 이상 차이나면
                print(f"⚠️ 프레임 수가 예상보다 많습니다! ({actual_frames} > {expected_frames}) - 반복 가능성")
                print(f"   강제로 정확한 길이로 자르는 중...")
                final_video = final_video.subclip(0, target_duration)
                final_video = final_video.set_duration(target_duration)
                actual_frames_after = int(final_video.duration * 30)
                print(f"   강제 조정 후: {final_video.duration:.2f}초, 프레임 수: {actual_frames_after}")
        
        print(f"✅ 최종 영상 길이: {final_video.duration:.2f}초")
        
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
                    current_video_duration = final_video.duration
                    if actual_video_duration > current_video_duration:
                        extension_needed = actual_video_duration - current_video_duration
                        print(f"   음성 길이에 맞추기 위해 영상 확장: {current_video_duration:.2f}초 -> {actual_video_duration:.2f}초 (추가: {extension_needed:.2f}초)")
                        # 마지막 부분을 반복하여 확장 (중복 방지를 위해 정확한 계산)
                        # 마지막 2초를 사용하여 반복 (너무 짧으면 전체 영상 사용)
                        extension_source_duration = min(2.0, current_video_duration)
                        extension_source = final_video.subclip(max(0, current_video_duration - extension_source_duration), current_video_duration)
                        
                        # 필요한 반복 횟수 계산
                        num_extensions = int(extension_needed / extension_source_duration) + (1 if extension_needed % extension_source_duration > 0.01 else 0)
                        extension_clips = []
                        remaining_extension = extension_needed
                        
                        for ext_idx in range(num_extensions):
                            if remaining_extension <= 0.01:
                                break
                            ext_clip_duration = min(extension_source_duration, remaining_extension)
                            ext_clip = extension_source.subclip(0, min(extension_source_duration, ext_clip_duration))
                            ext_clip = ext_clip.set_duration(ext_clip_duration)
                            extension_clips.append(ext_clip)
                            remaining_extension -= ext_clip_duration
                        
                        if extension_clips:
                            extension_video = concatenate_videoclips(extension_clips, method="compose")
                            # 정확한 길이로 자르기
                            if abs(extension_video.duration - extension_needed) > 0.01:
                                extension_video = extension_video.subclip(0, extension_needed)
                            extension_video = extension_video.set_duration(extension_needed)
                            # 원본 영상과 확장 영상 연결
                            final_video = concatenate_videoclips([final_video, extension_video], method="compose")
                            # 최종 길이 확인 및 조정
                            if abs(final_video.duration - actual_video_duration) > 0.01:
                                final_video = final_video.subclip(0, actual_video_duration)
                            final_video = final_video.set_duration(actual_video_duration)
                        else:
                            final_video = final_video.set_duration(actual_video_duration)
                        print(f"   최종 영상 길이: {final_video.duration:.2f}초")
                    else:
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
        
        # 영상 저장 전 최종 duration 확인 및 강제 조정 (반복 방지)
        actual_total_duration = sum(sentence_audio_durations)
        if abs(final_video.duration - actual_total_duration) > 0.01:
            print(f"⚠️ 저장 전 최종 확인: duration 불일치 ({final_video.duration:.2f}초 vs {actual_total_duration:.2f}초)")
            print(f"   강제로 정확한 길이로 자르는 중...")
            final_video = final_video.subclip(0, actual_total_duration)
            final_video = final_video.set_duration(actual_total_duration)
            print(f"   최종 조정 완료: {final_video.duration:.2f}초")
        
        # 영상 저장
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
            # 배경 영상 파일 삭제
            temp_bg_video = os.path.join(config.TEMP_DIR, f"bg_video_{i}.mp4")
            if os.path.exists(temp_bg_video):
                os.remove(temp_bg_video)
                print(f"🗑️ 임시 배경 영상 삭제: {temp_bg_video}")
        
        return output_path
    
    def _generate_audio(self, text: str, index: int) -> str:
        """TTS로 음성 생성"""
        audio_path = os.path.join(config.TEMP_DIR, f"audio_{index}.mp3")
        
        # 새로운 TTS 엔진 사용 (우선)
        if self.tts_engine:
            try:
                if self.tts_engine.generate(text, audio_path, lang='ko'):
                    return audio_path
                else:
                    print(f"⚠️ TTS 엔진 음성 생성 실패, 기본 gTTS 시도")
            except Exception as e:
                print(f"⚠️ TTS 엔진 오류: {e}, 기본 gTTS 시도")
        
        # 기본 gTTS 사용 (폴백)
        if TTS_AVAILABLE:
            try:
                tts = gTTS(text=text, lang='ko', slow=False)
                tts.save(audio_path)
                return audio_path
            except Exception as e:
                print(f"⚠️ gTTS 음성 생성 실패 ({text[:20]}...): {e}")
                return None
        else:
            print(f"⚠️ 사용 가능한 TTS 엔진이 없습니다.")
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
        """문장에 맞는 이미지 다운로드 (키워드 기반, Pexels와 Unsplash 번갈아 사용)"""
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
            
            # Pexels와 Unsplash를 번갈아가며 사용 (인덱스 기반)
            # 인덱스가 짝수면 Pexels 먼저, 홀수면 Unsplash 먼저
            use_pexels_first = (index % 2 == 0)
            
            # 사용 가능한 API 확인
            has_pexels = bool(config.PEXELS_API_KEY)
            has_unsplash = bool(config.UNSPLASH_ACCESS_KEY)
            
            # 둘 다 있으면 번갈아가며 사용
            if has_pexels and has_unsplash:
                if use_pexels_first:
                    # Pexels 먼저 시도
                    img = self._try_pexels_api(english_keyword, headers)
                    if img:
                                return img
                    # 실패하면 Unsplash 시도
                    img = self._try_unsplash_api(english_keyword, headers)
                    if img:
                        return img
                else:
                    # Unsplash 먼저 시도
                    img = self._try_unsplash_api(english_keyword, headers)
                    if img:
                        return img
                    # 실패하면 Pexels 시도
                    img = self._try_pexels_api(english_keyword, headers)
                    if img:
                        return img
            elif has_pexels:
                # Pexels만 사용
                img = self._try_pexels_api(english_keyword, headers)
                if img:
                    return img
            elif has_unsplash:
                # Unsplash만 사용
                img = self._try_unsplash_api(english_keyword, headers)
                if img:
                    return img
            
            # 방법 3: Pixabay API 사용 (무료, 공개 API 키, 폴백)
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
    
    def _download_video_for_sentence(self, sentence: str, index: int, duration: float) -> str:
        """
        문장에 맞는 배경 영상 다운로드 (Pexels Video API 사용, CC0 라이선스)
        
        Args:
            sentence: 문장
            index: 인덱스
            duration: 필요한 영상 길이 (초)
        
        Returns:
            다운로드된 영상 파일 경로 또는 None
        """
        try:
            # 문장에서 키워드 추출
            keywords = self._extract_keywords(sentence)
            keyword = keywords[0] if keywords else "nature"
            
            # 영어 키워드로 변환
            english_keyword = self._translate_keyword_to_english(keyword)
            
            print(f"🎬 배경 영상 다운로드 시도: {keyword} -> {english_keyword}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            # Pexels Video API 사용 (CC0 라이선스)
            if config.PEXELS_API_KEY:
                try:
                    # Pexels Video API 검색
                    pexels_video_url = f"https://api.pexels.com/videos/search?query={english_keyword}&per_page=3&orientation=portrait"
                    pexels_headers = {
                        **headers,
                        'Authorization': config.PEXELS_API_KEY
                    }
                    
                    response = requests.get(pexels_video_url, timeout=10, headers=pexels_headers)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('videos') and len(data['videos']) > 0:
                            # 첫 번째 영상 선택
                            video_data = data['videos'][0]
                            
                            # 세로형 영상 파일 찾기 (1080p 이상)
                            video_files = video_data.get('video_files', [])
                            video_url = None
                            
                            # 우선순위: 1080p > 720p > 기타
                            for quality in ['1080', '720', '540', '480']:
                                for vf in video_files:
                                    if quality in str(vf.get('width', 0)) and vf.get('link'):
                                        video_url = vf['link']
                                        break
                                if video_url:
                                    break
                            
                            # 영상 URL이 없으면 첫 번째 파일 사용
                            if not video_url and video_files:
                                video_url = video_files[0].get('link')
                            
                            if video_url:
                                # 영상 다운로드
                                video_response = requests.get(video_url, timeout=30, headers=headers, stream=True)
                                if video_response.status_code == 200:
                                    video_path = os.path.join(config.TEMP_DIR, f"bg_video_{index}.mp4")
                                    
                                    with open(video_path, 'wb') as f:
                                        for chunk in video_response.iter_content(chunk_size=8192):
                                            f.write(chunk)
                                    
                                    # 영상 길이 확인 (원본만 저장, 루프 처리는 나중에)
                                    try:
                                        video_clip = VideoFileClip(video_path)
                                        video_duration = video_clip.duration
                                        
                                        # 다운로드한 원본 영상 분석 (반복 여부 확인)
                                        print(f"📹 다운로드한 영상 분석: {video_path}")
                                        print(f"   원본 길이: {video_duration:.2f}초")
                                        
                                        # 원본 영상이 반복되어 있는지 확인
                                        if video_duration > 2.0:
                                            # 시작, 중간, 끝 지점 비교
                                            start_frame = video_clip.get_frame(0.5)
                                            mid_frame = video_clip.get_frame(video_duration / 2)
                                            end_frame = video_clip.get_frame(video_duration - 0.5)
                                            
                                            start_rgb = start_frame[540, 960] if len(start_frame.shape) == 3 else [0, 0, 0]
                                            mid_rgb = mid_frame[540, 960] if len(mid_frame.shape) == 3 else [0, 0, 0]
                                            end_rgb = end_frame[540, 960] if len(end_frame.shape) == 3 else [0, 0, 0]
                                            
                                            import numpy as np
                                            start_mid_diff = np.abs(start_rgb - mid_rgb).sum()
                                            start_end_diff = np.abs(start_rgb - end_rgb).sum()
                                            
                                            print(f"   시작-중간 차이: {start_mid_diff}, 시작-끝 차이: {start_end_diff}")
                                            if start_mid_diff < 20 or start_end_diff < 20:
                                                print(f"   ⚠️ 원본 영상이 반복되어 있을 가능성이 있습니다!")
                                        
                                        video_clip.close()
                                        
                                        # 원본 영상만 저장 (루프 처리는 _create_video_from_script에서 수행)
                                        # 영상이 너무 짧으면 (1초 미만) 다른 영상 시도하거나 이미지 사용
                                        if video_duration < 1.0:
                                            print(f"   영상이 너무 짧음 ({video_duration:.1f}초), 이미지로 대체")
                                            if os.path.exists(video_path):
                                                os.remove(video_path)
                                            return None
                                        
                                        print(f"✅ Pexels 배경 영상 다운로드 성공: {english_keyword} (원본: {video_duration:.1f}초, 파일: {video_path})")
                                        return video_path
                                    except Exception as e:
                                        print(f"   영상 처리 실패: {e}")
                                        if os.path.exists(video_path):
                                            os.remove(video_path)
                except Exception as e:
                    print(f"   Pexels Video API 실패: {e}")
            
            # Pexels Video API 실패 시 이미지 사용 (기존 로직)
            return None
            
        except Exception as e:
            print(f"⚠️ 배경 영상 다운로드 실패 ({sentence[:20]}...): {e}")
            return None
    
    def generate_thumbnail(self, video_path: str, title: str, topic: str = None, script: list = None) -> str:
        """
        매력적인 썸네일 이미지 생성
        
        Args:
            video_path: 영상 파일 경로
            title: 영상 제목
            topic: 영상 주제 (선택)
            script: 영상 스크립트 (선택, 핵심 내용 추출용)
        """
        import datetime
        import numpy as np
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        thumbnail_path = os.path.join(config.THUMBNAIL_OUTPUT_DIR, f"thumb_{timestamp}.jpg")
        
        # 영상에서 여러 프레임 중 가장 좋은 프레임 선택 (중간 부분)
        # 자막이 없는 원본 배경을 사용하기 위해 영상에서 프레임 추출 후 자막 영역 제거
        video = VideoFileClip(video_path)
        duration = video.duration
        # 영상의 30-40% 지점에서 프레임 추출 (일반적으로 가장 매력적인 부분)
        frame_time = duration * 0.35
        frame = video.get_frame(frame_time)
        video.close()
        
        # PIL 이미지로 변환
        img = Image.fromarray(frame.astype('uint8'), 'RGB')
        
        # 자막 영역 제거 (하단 중앙 부분 블러 처리 또는 제거)
        # 자막은 보통 하단 중앙에 위치하므로, 해당 영역을 블러 처리하여 제거
        from PIL import ImageFilter
        width, height = img.size
        # 하단 30% 영역을 블러 처리 (자막 제거)
        bottom_region = img.crop((0, int(height * 0.7), width, height))
        blurred_bottom = bottom_region.filter(ImageFilter.GaussianBlur(radius=20))
        img.paste(blurred_bottom, (0, int(height * 0.7)))
        
        # 이미지 크기 확인 및 조정 (1080x1920)
        if img.size != (1080, 1920):
            img = img.resize((1080, 1920), Image.Resampling.LANCZOS)
        
        # 매력적인 제목/내용 생성 (AI 활용)
        attractive_texts = self._generate_attractive_thumbnail_text(title, topic, script)
        
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
        
        # 2. 하단에 매력적인 텍스트 추가
        # attractive_texts는 (main_title, sub_title) 튜플 또는 (main_title,) 형태
        main_title = attractive_texts[0] if attractive_texts else title
        sub_title = attractive_texts[1] if len(attractive_texts) > 1 else None
        
        # 메인 제목을 여러 줄로 분할
        max_width = 1000
        words = main_title.split()
        main_lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            bbox = draw.textbbox((0, 0), test_line, font=font_large)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    main_lines.append(current_line)
                current_line = word
        
        if current_line:
            main_lines.append(current_line)
        
        # 최대 2줄까지만 표시
        if len(main_lines) > 2:
            main_lines = main_lines[:2]
        
        # 서브 타이틀 처리
        sub_lines = []
        if sub_title:
            words = sub_title.split()
            current_line = ""
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                bbox = draw.textbbox((0, 0), test_line, font=font_medium)
                if bbox[2] - bbox[0] <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        sub_lines.append(current_line)
                    current_line = word
            if current_line:
                sub_lines.append(current_line)
            if len(sub_lines) > 1:
                sub_lines = sub_lines[:1]  # 서브 타이틀은 1줄만
        
        # 텍스트 높이 계산
        main_line_height = 140
        sub_line_height = 80 if sub_lines else 0
        line_spacing = 20
        total_text_height = len(main_lines) * main_line_height + (len(sub_lines) * sub_line_height if sub_lines else 0) + (line_spacing if sub_lines else 0) + 40
        
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
        
        # 메인 제목 그리기 (그림자 효과 포함)
        current_y = text_y_start
        for i, line in enumerate(main_lines):
            bbox = draw.textbbox((0, 0), line, font=font_large)
            text_width = bbox[2] - bbox[0]
            text_x = (1080 - text_width) // 2
            text_y = current_y
            
            # 그림자 효과 (더 진하게)
            shadow_offset = 6
            draw.text((text_x + shadow_offset, text_y + shadow_offset), line, 
                     fill=(0, 0, 0, 220), font=font_large)
            draw.text((text_x + 3, text_y + 3), line, 
                     fill=(0, 0, 0, 180), font=font_large)
            
            # 메인 텍스트 (밝은 흰색, 굵게)
            draw.text((text_x, text_y), line, fill=(255, 255, 255), font=font_large)
            
            current_y += main_line_height
        
        # 서브 타이틀 그리기 (있는 경우)
        if sub_lines:
            current_y += line_spacing
            for i, line in enumerate(sub_lines):
                bbox = draw.textbbox((0, 0), line, font=font_medium)
                text_width = bbox[2] - bbox[0]
                text_x = (1080 - text_width) // 2
                text_y = current_y
                
                # 그림자 효과
                shadow_offset = 4
                draw.text((text_x + shadow_offset, text_y + shadow_offset), line, 
                         fill=(0, 0, 0, 200), font=font_medium)
                
                # 서브 텍스트 (노란색 또는 밝은 색)
                draw.text((text_x, text_y), line, fill=(255, 215, 0), font=font_medium)
                
                current_y += sub_line_height
        
        # 3. 강조 요소 추가
        # 상단 오른쪽에 이모지/아이콘
        icon_texts = ["🔥", "✨", "💡", "⭐", "🎯"]
        icon_text = random.choice(icon_texts)
        icon_bbox = draw.textbbox((0, 0), icon_text, font=font_medium)
        icon_x = 1080 - (icon_bbox[2] - icon_bbox[0]) - 50
        icon_y = 50
        
        # 아이콘 배경 (원형)
        icon_radius = 40
        icon_bg = Image.new('RGBA', (icon_radius * 2, icon_radius * 2), (0, 0, 0, 150))
        icon_draw = ImageDraw.Draw(icon_bg)
        icon_draw.ellipse([0, 0, icon_radius * 2, icon_radius * 2], fill=(255, 215, 0, 200))
        icon_center_x = icon_x + (icon_bbox[2] - icon_bbox[0]) // 2
        icon_center_y = icon_y + (icon_bbox[3] - icon_bbox[1]) // 2
        img.paste(icon_bg, (icon_center_x - icon_radius, icon_center_y - icon_radius), icon_bg)
        draw.text((icon_x, icon_y), icon_text, fill=(255, 255, 255), font=font_medium)
        
        # 4. 이미지 저장 (고품질)
        img.save(thumbnail_path, 'JPEG', quality=95, optimize=True)
        
        print(f"✅ 썸네일 생성 완료: {thumbnail_path}")
        return thumbnail_path
    
    def _generate_attractive_thumbnail_text(self, title: str, topic: str = None, script: list = None) -> tuple:
        """
        썸네일용 매력적인 텍스트 생성 (AI 활용)
        
        Returns:
            (main_title, sub_title) 튜플
        """
        # AI로 매력적인 Hook 문구 생성 시도
        if self.openai_client and (topic or script):
            try:
                # 스크립트에서 핵심 내용 추출
                context = ""
                if script and len(script) > 0:
                    # 첫 3개 문장으로 핵심 파악
                    context = "\n".join(script[:3])
                
                prompt = f"""다음 영상의 썸네일용 매력적인 텍스트를 생성해주세요.

제목: {title}
주제: {topic if topic else '없음'}
핵심 내용: {context if context else '없음'}

요구사항:
1. 첫 번째 줄: 사람들의 호기심을 끄는 강력한 Hook 문구 (최대 15자)
2. 두 번째 줄: 핵심 내용을 간단히 요약하거나 숫자/팩트 강조 (최대 20자, 선택적)

예시:
- "이거 모르면 손해!" / "5가지 비밀 공개"
- "부자들의 습관" / "하루 10분이면 OK"
- "영어 한 문장" / "실생활 필수 표현"

형식: 첫 번째 줄만 또는 "첫 번째 줄 / 두 번째 줄"
"""
                
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "당신은 YouTube 썸네일 텍스트 작성 전문가입니다. 사람들의 호기심을 끄는 강력하고 간결한 문구를 작성하세요."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=100,
                    temperature=0.8
                )
                
                result = response.choices[0].message.content.strip()
                
                # "/" 또는 줄바꿈으로 분리
                if "/" in result:
                    parts = [p.strip() for p in result.split("/")]
                    if len(parts) >= 2:
                        return (parts[0], parts[1])
                    else:
                        return (parts[0], None)
                elif "\n" in result:
                    parts = [p.strip() for p in result.split("\n") if p.strip()]
                    if len(parts) >= 2:
                        return (parts[0], parts[1])
                    else:
                        return (parts[0], None)
                else:
                    return (result, None)
                    
            except Exception as e:
                print(f"   AI 썸네일 텍스트 생성 실패, 기본 사용: {e}")
        
        # AI 실패 시 기본 변환
        # 제목을 더 매력적으로 변환
        attractive_title = title
        
        # 숫자나 팩트가 있으면 강조
        import re
        numbers = re.findall(r'\d+', title)
        if numbers:
            attractive_title = f"{numbers[0]}가지 {title.replace(numbers[0], '').strip()}" if numbers else title
        
        # 질문 형태로 변환 (선택적)
        if "한 문장" in title or "한 줄" in title:
            attractive_title = f"이거 모르면 손해! {title}"
        elif "팁" in title or "방법" in title:
            attractive_title = f"꿀팁 공개! {title}"
        elif "명언" in title or "지식" in title:
            attractive_title = f"부자들의 비밀 {title}"
        elif "팩트" in title or "사실" in title:
            attractive_title = f"놀라운 사실! {title}"
        
        return (attractive_title, None)
    
    def _try_pexels_api(self, english_keyword: str, headers: dict) -> Image.Image:
        """Pexels API로 이미지 다운로드 시도"""
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
        return None
    
    def _try_unsplash_api(self, english_keyword: str, headers: dict) -> Image.Image:
        """Unsplash API로 이미지 다운로드 시도"""
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
        return None
    
    
    def _create_subtitle_clip(self, text: str, duration: float) -> TextClip:
        """자막 클립 생성 (배경 영상용)"""
        try:
            # 한글 폰트 경로 찾기
            font_path = None
            font_size = 80
            
            # macOS 한글 폰트 경로
            for path in [
                "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
                "/System/Library/Fonts/AppleGothic.ttf",
                "/System/Library/Fonts/Supplemental/NanumGothic.ttf",
                "/Library/Fonts/AppleGothic.ttf",
            ]:
                if os.path.exists(path):
                    font_path = path
                    break
            
            # TextClip 생성 (ImageMagick 사용 시도, 실패하면 PIL로 대체)
            try:
                # 먼저 ImageMagick으로 시도
                if font_path:
                    try:
                        txt_clip = TextClip(
                            text,
                            fontsize=font_size,
                            font=font_path,
                            color='white',
                            stroke_color='black',
                            stroke_width=2,
                            method='caption',
                            size=(1000, None),
                            align='center'
                        )
                        txt_clip = txt_clip.set_duration(duration)
                        # 위치 설정
                        try:
                            frame = txt_clip.get_frame(0)
                            clip_height = frame.shape[0]
                            y_pos = 1920 - clip_height - 100
                            txt_clip = txt_clip.set_position(('center', y_pos))
                        except:
                            txt_clip = txt_clip.set_position(('center', 'bottom'))
                        return txt_clip
                    except Exception as e1:
                        print(f"   ImageMagick TextClip 실패, PIL로 대체: {e1}")
                
                # ImageMagick 실패 시 PIL로 이미지 생성 후 ImageClip 사용
                # PIL로 자막 이미지 생성 (더 큰 크기로)
                from PIL import Image, ImageDraw, ImageFont
                # 자막 영역을 더 크게 (텍스트가 잘리지 않도록)
                subtitle_height = 300
                subtitle_img = Image.new('RGBA', (1080, subtitle_height), (0, 0, 0, 0))
                draw = ImageDraw.Draw(subtitle_img)
                
                # 폰트 로드
                pil_font = None
                if font_path and os.path.exists(font_path):
                    try:
                        pil_font = ImageFont.truetype(font_path, font_size)
                    except:
                        pass
                
                if pil_font is None:
                    # 기본 폰트 시도
                    for path in [
                        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
                        "/System/Library/Fonts/AppleGothic.ttf",
                    ]:
                        if os.path.exists(path):
                            try:
                                pil_font = ImageFont.truetype(path, font_size)
                                break
                            except:
                                continue
                
                if pil_font is None:
                    pil_font = ImageFont.load_default()
                
                # 텍스트를 여러 줄로 분할 (너비 고려)
                max_width = 1000
                words = text.split()
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
                    lines = [text]
                
                # 텍스트 그리기
                y_offset = 20
                total_text_height = 0
                for line in lines[:3]:  # 최대 3줄
                    if line.strip():
                        # 텍스트 크기 계산
                        bbox = draw.textbbox((0, 0), line, font=pil_font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]
                        x_pos = (1080 - text_width) // 2
                        
                        # 배경 박스 (반투명 검은색)
                        padding = 10
                        overlay = Image.new('RGBA', (1080, subtitle_height), (0, 0, 0, 0))
                        overlay_draw = ImageDraw.Draw(overlay)
                        overlay_draw.rectangle(
                            [x_pos - padding, y_offset - padding, 
                             x_pos + text_width + padding, y_offset + text_height + padding],
                            fill=(0, 0, 0, 180)
                        )
                        subtitle_img = Image.alpha_composite(subtitle_img, overlay)
                        draw = ImageDraw.Draw(subtitle_img)
                        
                        # 그림자 효과
                        draw.text((x_pos + 3, y_offset + 3), line, fill=(0, 0, 0, 255), font=pil_font)
                        # 메인 텍스트
                        draw.text((x_pos, y_offset), line, fill=(255, 255, 255, 255), font=pil_font)
                        y_offset += text_height + 15
                        total_text_height = y_offset
                
                # 실제 텍스트가 있는 부분만 크롭
                if total_text_height > 0:
                    subtitle_img = subtitle_img.crop((0, 0, 1080, min(total_text_height + 20, subtitle_height)))
                
                # PIL 이미지를 ImageClip으로 변환
                import numpy as np
                # RGBA를 RGB로 변환 (MoviePy 호환성)
                if subtitle_img.mode == 'RGBA':
                    # 알파 채널이 있는 경우 배경과 합성
                    rgb_img = Image.new('RGB', subtitle_img.size, (0, 0, 0))
                    rgb_img.paste(subtitle_img, mask=subtitle_img.split()[3])  # 알파 채널을 마스크로 사용
                    subtitle_img = rgb_img
                
                subtitle_array = np.array(subtitle_img)
                txt_clip = ImageClip(subtitle_array).set_duration(duration)
                # 하단 중앙 위치 (실제 높이 고려, 더 명확하게)
                actual_height = subtitle_array.shape[0]
                y_pos = max(100, 1920 - actual_height - 150)  # 최소 100px, 하단에서 150px 위
                txt_clip = txt_clip.set_position(('center', y_pos))
                
                print(f"   ✅ PIL 자막 생성 성공: 높이={actual_height}px, 위치 y={y_pos}")
                return txt_clip
            except Exception as e:
                print(f"   자막 클립 생성 실패: {e}")
                import traceback
                traceback.print_exc()
                return None
        except Exception as e:
            print(f"   자막 클립 생성 실패: {e}")
            return None


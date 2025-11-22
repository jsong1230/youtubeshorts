"""
AI 영상 생성 모듈 (15초~60초 YouTube Shorts)
"""
import os
import random
import re
import time
from datetime import datetime
from moviepy.editor import (
    VideoFileClip, ImageClip, TextClip,
    concatenate_videoclips, AudioFileClip, CompositeVideoClip
)
from moviepy.audio.AudioClip import CompositeAudioClip
from typing import Optional, Tuple, List
from moviepy.video.fx.all import fadein, fadeout
from PIL import Image, ImageDraw, ImageFont
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
from src.utils.retry_decorator import retry, retry_on_rate_limit
from .script_generator import ScriptGenerator
from .media_downloader import MediaDownloader

# 프로젝트 루트 디렉토리
BASE_DIR = Path(__file__).resolve().parent.parent.parent

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


from .content_type import ContentType

# 상수 정의
class VideoConstants:
    """영상 생성 관련 상수"""
    # 해상도
    VIDEO_WIDTH = 1080
    VIDEO_HEIGHT = 1920
    VIDEO_FPS = 30
    
    # 영상 길이
    MIN_DURATION = 15  # 최소 길이 (초)
    MAX_DURATION = 60  # 최대 길이 (초)
    MAX_SAFE_DURATION = 58  # 안전 마진 (초)
    TARGET_DURATION = 55  # 목표 길이 (초)
    
    # 페이드 효과
    DEFAULT_FADE_DURATION = 0.5  # 기본 페이드 길이 (초)
    FADE_RATIO = 0.1  # 페이드 비율 (duration의 10%)
    
    # 자막
    SUBTITLE_BOTTOM_MARGIN = 150  # 하단 여백 (px)
    SUBTITLE_PADDING = 40  # 자막 배경 패딩 (px)
    SUBTITLE_MAX_WIDTH = 900  # 자막 최대 너비 (px)
    SUBTITLE_BACKGROUND_ALPHA = 200  # 자막 배경 투명도
    
    # 폰트
    BASE_FONT_SIZE = 100
    FONT_SIZES = [90, 80, 70, 60]  # 폰트 크기 옵션
    LINE_SPACING = 50  # 줄 간격 (px)
    
    # 배경 그룹
    BACKGROUND_GROUP_SIZE = 2  # 배경 변경 주기 (문장 수)
    
    # 영상 품질
    MIN_VIDEO_DURATION = 1.0  # 최소 영상 길이 (초)
    MIN_VIDEO_HEIGHT = 480  # 최소 영상 높이 (px)
    PREFERRED_VIDEO_HEIGHT = 1080  # 선호 영상 높이 (px)
    
    # 프레임 분석
    FRAME_CHECK_THRESHOLD = 20  # 프레임 차이 임계값
    MIN_BRIGHTNESS = 30  # 최소 밝기
    MAX_BRIGHTNESS = 220  # 최대 밝기
    MIN_CONTRAST = 20  # 최소 대비
    
    # 배경 음악
    DEFAULT_MUSIC_VOLUME = 0.25  # 기본 음악 볼륨
    MUSIC_FADE_RATIO = 0.1  # 음악 페이드 비율
    
    # 썸네일
    THUMBNAIL_FRAME_RATIO = 0.35  # 썸네일 프레임 추출 비율 (30-40%)
    THUMBNAIL_BLUR_RADIUS = 20  # 블러 반경
    THUMBNAIL_BOTTOM_REGION = 0.7  # 하단 영역 비율
    
    # 확장 시간
    EXTENSION_DURATION = 0.5  # 영상 확장 단위 (초)
    FINAL_CLIP_EXTENSION = 0.5  # 마지막 클립 확장 (초)


class AIVideoGenerator:
    """AI를 활용한 15초 YouTube Shorts 영상 생성 클래스"""
    
    TREND_WEIGHTS = {
        "global": 0.40,
        "seasonal": 0.25,
        "performance": 0.20,
        "exploration": 0.15,
    }

    HIGH_PERFORMING_TOPICS = {
        ContentType.HOOK: [
            "Money vanishes in patterns, not accidents.",
            "Structure builds wealth faster than motivation ever could.",
            "AI automation frees the 30 minutes you keep losing.",
            "Routines decide your life long before you do.",
            "Tiny routines create massive peace.",
        ],
        ContentType.QUOTE: [
            "Tiny routines create massive peace.",
            "Money is measurement; direction is wealth.",
            "Consistency outruns talent every single time.",
            "Decluttering a room calms your mind, and a calm mind cuts anxiety.",
        ],
        ContentType.STORY: [
            "He cleared one closet and reset his entire routine.",
            "A 30-day expense log rebuilt her bank balance.",
            "A five-minute evening review saved a burned-out manager.",
            "An AI micro-routine gave him back an hour every morning.",
        ],
        ContentType.FACT: [
            "Tracking spend for 30 days cuts impulse buys by 15%.",
            "Decluttered desks raise focus by 25%.",
            "Skipping a winter oil check can cost an engine replacement.",
            "AI batching saves at least 30 minutes per day.",
        ],
        ContentType.SHORT_STORY: [
            "Logging expenses for 30 days changed my bank balance.",
            "Ten minutes of routine completely rerouted her life.",
            "Preparing for winter once cut our heating bill in half.",
            "I automated emails with AI and finally slept.",
        ],
        ContentType.AUTO: [],
    }
    
    def __init__(self, tts_provider=None):
        # OpenAI 클라이언트 초기화
        if config.OPENAI_API_KEY and OPENAI_AVAILABLE:
            try:
                # 간단한 초기화 (httpx 버전 호환성 문제 회피)
                self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
            except Exception as e:
                print(f"⚠️ OpenAI 클라이언트 초기화 실패: {e}")
                self.openai_client = None
        else:
            self.openai_client = None
        
        # Claude (Anthropic) 클라이언트 초기화
        if config.CLAUDE_API_KEY and ANTHROPIC_AVAILABLE:
            try:
                self.claude_client = Anthropic(api_key=config.CLAUDE_API_KEY)
                print(f"✅ Claude API 클라이언트 초기화 완료")
            except Exception as e:
                print(f"⚠️ Claude 클라이언트 초기화 실패: {e}")
                self.claude_client = None
        else:
            self.claude_client = None

        # AI API 제공자 확인
        self.ai_provider = getattr(config, 'AI_API_PROVIDER', 'openai').lower()
        if self.ai_provider == 'claude' and not self.claude_client:
            print(f"⚠️ Claude API가 설정되지 않았습니다. OpenAI를 사용합니다.")
            self.ai_provider = 'openai'
        elif self.ai_provider == 'openai' and not self.openai_client:
            if self.claude_client:
                print(f"⚠️ OpenAI API가 설정되지 않았습니다. Claude를 사용합니다.")
                self.ai_provider = 'claude'
            else:
                print(f"⚠️ AI API가 설정되지 않았습니다.")
        
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
        
        # 스크립트 생성기 초기화
        self.script_generator = ScriptGenerator(
            openai_client=self.openai_client,
            claude_client=self.claude_client,
            ai_provider=self.ai_provider
        )
        
        # 미디어 다운로더 초기화
        self.media_downloader = MediaDownloader(
            openai_client=self.openai_client,
            http_get_with_retry=self._http_get_with_retry,
            api_call_with_retry=self._api_call_with_retry
        )
        
        # 출력 디렉토리 생성
        os.makedirs(config.VIDEO_OUTPUT_DIR, exist_ok=True)
        os.makedirs(config.TEMP_DIR, exist_ok=True)
        os.makedirs(config.THUMBNAIL_OUTPUT_DIR, exist_ok=True)
    
    # ===== Retry-wrapped Helper Methods =====
    
    @retry(max_retries=3, base_delay=1, exceptions=(requests.RequestException, ConnectionError, TimeoutError))
    def _http_get_with_retry(self, url: str, **kwargs) -> requests.Response:
        """HTTP GET request with automatic retry on transient failures."""
        timeout = kwargs.pop('timeout', 10)
        response = requests.get(url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response
    
    @retry_on_rate_limit(max_retries=5, base_delay=2)
    def _api_call_with_retry(self, api_func, *args, **kwargs):
        """Generic API call wrapper with retry logic for rate limits."""
        return api_func(*args, **kwargs)
    
    def _get_high_performing_topics(self, content_type: ContentType) -> List[str]:
        """콘텐츠 타입별 성과가 좋았던 주제 풀을 반환."""
        topics = []
        
        # 주제 데이터베이스에서 성과가 좋은 주제 가져오기
        try:
            from src.pipeline.topic_database import TopicDatabase, TopicStatus
            topic_db = TopicDatabase()
            
            db_topics = topic_db.get_high_performing_topics(
                content_type=content_type.value if content_type != ContentType.AUTO else None,
                days=30,
                min_views=100,
                min_engagement_rate=1.0,
                limit=10
            )
            topics.extend(db_topics)
        except Exception as e:
            print(f"⚠️ 주제 데이터베이스에서 성과 주제 가져오기 실패: {e}")
        
        # 하드코딩된 성과 주제 추가 (폴백)
        if content_type == ContentType.AUTO:
            for key, values in self.HIGH_PERFORMING_TOPICS.items():
                if key == ContentType.AUTO:
                    continue
                topics.extend(values)
        else:
            topics.extend(self.HIGH_PERFORMING_TOPICS.get(content_type, []))
        
        # 중복 제거
        return list(dict.fromkeys(topics))  # 순서 유지하면서 중복 제거

    def _get_youtube_trending_topics(self) -> List[str]:
        """YouTube 트렌드 주제 가져오기 (캐싱 사용)"""
        try:
            from src.analytics.trend_collector import TrendCollector
            
            # 캐시 파일 경로
            cache_file = os.path.join(config.TEMP_DIR, 'trending_topics_cache.json')
            cache_duration = 24 * 3600  # 24시간 캐시
            
            # 캐시 확인
            if os.path.exists(cache_file):
                import json
                import time
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    cache_time = cache_data.get('timestamp', 0)
                    if time.time() - cache_time < cache_duration:
                        topics = cache_data.get('topics', [])
                        if topics:
                            print(f"📊 캐시된 트렌드 주제 {len(topics)}개 사용")
                            return topics
            
            # 트렌드 수집
            collector = TrendCollector()
            topics = collector.get_trending_topics_for_category(
                category='finance',
                max_videos=20
            )
            
            # 캐시 저장
            if topics:
                os.makedirs(config.TEMP_DIR, exist_ok=True)
                import json
                import time
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'timestamp': time.time(),
                        'topics': topics
                    }, f, ensure_ascii=False, indent=2)
                print(f"✅ 트렌드 주제 {len(topics)}개 수집 및 캐시 저장")
            
            return topics
        except Exception as e:
            print(f"⚠️ YouTube 트렌드 주제 수집 실패: {e}")
            return []
    
    def _generate_seasonal_topics_from_trends(
        self,
        season: str,
        content_type: ContentType,
        language: str = 'en'
    ) -> List[str]:
        """
        계절별 트렌드 키워드를 기반으로 AI가 새로운 계절별 주제 생성
        
        Args:
            season: 계절 ('spring', 'summer', 'autumn', 'winter')
            content_type: 콘텐츠 타입
            language: 언어 ('en' 또는 'ko')
        
        Returns:
            생성된 계절별 주제 리스트
        """
        try:
            from src.analytics.trend_collector import TrendCollector
            
            # 캐시 파일 경로
            cache_file = os.path.join(
                config.TEMP_DIR, 
                f'ai_seasonal_topics_cache_{season}_{content_type.value}_{language}.json'
            )
            cache_duration = 7 * 24 * 3600  # 7일 캐시 (계절별 주제는 더 오래 유효)
            
            # 캐시 확인
            if os.path.exists(cache_file):
                import json
                import time
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    cache_time = cache_data.get('timestamp', 0)
                    if time.time() - cache_time < cache_duration:
                        topics = cache_data.get('topics', [])
                        if topics:
                            print(f"📊 캐시된 {season} 계절 AI 생성 주제 {len(topics)}개 사용")
                            return topics
            
            # 계절별 트렌드 키워드 수집
            collector = TrendCollector()
            keywords = collector.collect_seasonal_trending_keywords(
                season=season,
                max_videos=30,
                min_views=5000,
                top_n=15
            )
            
            if not keywords:
                print(f"⚠️ {season} 계절 트렌드 키워드가 없어 AI 주제 생성을 건너뜁니다.")
                return []
            
            # AI로 계절별 주제 생성
            generated_topics = collector.generate_seasonal_topics(
                season=season,
                keywords=keywords,
                content_type=content_type.value,
                num_topics=10,
                language=language
            )
            
            # 품질 검증 및 필터링
            validated_topics = []
            existing_topics = self._get_all_existing_topics(content_type)
            # 기존 계절별 주제도 포함
            existing_seasonal_topics = self._get_seasonal_topics_for_season(season, content_type)
            existing_topics.extend(existing_seasonal_topics)
            
            for topic in generated_topics:
                validation = collector.validate_topic_quality(
                    topic=topic,
                    existing_topics=existing_topics
                )
                if validation['is_valid']:
                    validated_topics.append(topic)
                    print(f"   ✅ {season} 계절 주제 검증 통과: {topic[:50]}... (점수: {validation['score']})")
                else:
                    print(f"   ❌ {season} 계절 주제 검증 실패: {topic[:50]}... (점수: {validation['score']}, 이유: {', '.join(validation['reasons'])})")
            
            # 캐시 저장
            if validated_topics:
                os.makedirs(config.TEMP_DIR, exist_ok=True)
                import json
                import time
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'timestamp': time.time(),
                        'topics': validated_topics
                    }, f, ensure_ascii=False, indent=2)
                print(f"✅ {season} 계절 AI 생성 주제 {len(validated_topics)}개 검증 완료 및 캐시 저장")
            
            return validated_topics
            
        except Exception as e:
            print(f"⚠️ {season} 계절 AI 주제 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_seasonal_topics_for_season(
        self,
        season: str,
        content_type: ContentType
    ) -> List[str]:
        """특정 계절의 기존 주제 가져오기 (중복 확인용)"""
        # 하드코딩된 계절별 주제를 가져오는 로직
        # _generate_topic에서 사용하는 seasonal_topics 딕셔너리 구조를 재현
        seasonal_topics = {}
        
        if content_type == ContentType.HOOK:
            seasonal_topics = {
                'spring': [
                    "Why new-year plans keep collapsing by March",
                    "How people who reset each season look five years later",
                    "Why your salary alone will never make you wealthy",
                    "The simple rule people with tidy homes follow every day",
                ],
                'summer': [
                    "Why summer spending ruins your fall budget",
                    "The one habit that separates summer savers from summer spenders",
                    "Why your vacation fund disappears by August",
                ],
                'autumn': [
                    "Why people who plan in September retire earlier",
                    "The October habit that changes your December",
                    "Why your year-end bonus disappears by January",
                ],
                'winter': [
                    "Why January goals fail by February",
                    "The December decision that determines your March",
                    "Why your holiday spending haunts your spring",
                ]
            }
        elif content_type == ContentType.QUOTE:
            seasonal_topics = {
                'spring': [
                    "When seasons change, your priorities must be reorganized too.",
                    "Decluttering a room calms your mind, and a calm mind cuts anxiety.",
                ],
                'summer': [
                    "Summer is not just a season; it's a financial opportunity.",
                    "The best time to save for next summer is this summer.",
                ],
                'autumn': [
                    "Fall is the season of preparation, not just celebration.",
                    "Your September decisions shape your December outcomes.",
                ],
                'winter': [
                    "Winter is the season of reflection, not just spending.",
                    "Your December choices determine your January reality.",
                ]
            }
        elif content_type == ContentType.STORY:
            seasonal_topics = {
                'spring': ["The messy closet that turned into a seasonal reset routine"],
                'summer': ["How one family finally killed the summer mold problem"],
                'autumn': ["The messy closet that turned into a seasonal reset routine"],
                'winter': [
                    "The winter their heating bill dropped in half",
                    "How one December decision changed their entire year"
                ]
            }
        elif content_type == ContentType.FACT:
            seasonal_topics = {
                'spring': [
                    "Homes get dirtiest during seasonal transitions because humidity spikes",
                    "Clothes discolor faster when your closet airflow is blocked",
                ],
                'summer': [
                    "Summer spending increases by 30% on average",
                    "Vacation costs rise 40% during peak summer months",
                ],
                'autumn': [
                    "Holiday spending starts in September, not December",
                    "Year-end bonuses are spent before they arrive",
                ],
                'winter': [
                    "Heating costs can double during cold winters",
                    "Holiday spending accounts for 20% of annual expenses",
                ]
            }
        elif content_type == ContentType.SHORT_STORY:
            seasonal_topics = {
                'spring': [
                    "Decluttering one closet erased my morning panic",
                    "Controlling humidity removed that strange smell overnight",
                ],
                'summer': [
                    "How a summer budget saved my fall",
                    "The summer habit that changed everything",
                ],
                'autumn': [
                    "The autumn decision that saved my year",
                    "How September planning changed my December",
                ],
                'winter': [
                    "The winter routine that transformed my spring",
                    "How December choices shaped my January",
                ]
            }
        elif content_type == ContentType.MEDITATION:
            seasonal_topics = {
                'spring': ["A seasonal refresh you can do right now"],
                'summer': ["A seasonal refresh you can do right now"],
                'autumn': ["A seasonal refresh you can do right now"],
                'winter': ["A seasonal refresh you can do right now"]
            }
        elif content_type == ContentType.BREATHING:
            seasonal_topics = {
                'spring': ["A seasonal refresh you can do right now"],
                'summer': ["A seasonal refresh you can do right now"],
                'autumn': ["A seasonal refresh you can do right now"],
                'winter': ["A seasonal refresh you can do right now"]
            }
        
        return seasonal_topics.get(season.lower(), [])
    
    def _generate_ai_topics_from_trends(
        self,
        content_type: ContentType,
        language: str = 'en'
    ) -> List[str]:
        """
        트렌드 키워드를 기반으로 AI가 새로운 주제 생성
        
        Args:
            content_type: 콘텐츠 타입
            language: 언어 ('en' 또는 'ko')
        
        Returns:
            생성된 주제 리스트
        """
        try:
            from src.analytics.trend_collector import TrendCollector
            
            # 캐시 파일 경로
            cache_file = os.path.join(
                config.TEMP_DIR, 
                f'ai_topics_cache_{content_type.value}_{language}.json'
            )
            cache_duration = 12 * 3600  # 12시간 캐시 (트렌드 주제보다 더 자주 업데이트)
            
            # 캐시 확인
            if os.path.exists(cache_file):
                import json
                import time
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    cache_time = cache_data.get('timestamp', 0)
                    if time.time() - cache_time < cache_duration:
                        topics = cache_data.get('topics', [])
                        if topics:
                            print(f"📊 캐시된 AI 생성 주제 {len(topics)}개 사용")
                            return topics
            
            # 트렌드 키워드 수집
            collector = TrendCollector()
            keywords = collector.collect_trending_keywords(
                max_videos=30,
                min_views=5000,
                top_n=15
            )
            
            if not keywords:
                print("⚠️ 트렌드 키워드가 없어 AI 주제 생성을 건너뜁니다.")
                return []
            
            # AI로 주제 생성
            generated_topics = collector.generate_topics_from_trends(
                keywords=keywords,
                content_type=content_type.value,
                num_topics=10,
                language=language
            )
            
            # 품질 검증 및 필터링
            validated_topics = []
            existing_topics = self._get_all_existing_topics(content_type)
            
            for topic in generated_topics:
                validation = collector.validate_topic_quality(
                    topic=topic,
                    existing_topics=existing_topics
                )
                if validation['is_valid']:
                    validated_topics.append(topic)
                    print(f"   ✅ 주제 검증 통과: {topic[:50]}... (점수: {validation['score']})")
                else:
                    print(f"   ❌ 주제 검증 실패: {topic[:50]}... (점수: {validation['score']}, 이유: {', '.join(validation['reasons'])})")
            
            # 캐시 저장
            if validated_topics:
                os.makedirs(config.TEMP_DIR, exist_ok=True)
                import json
                import time
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'timestamp': time.time(),
                        'topics': validated_topics
                    }, f, ensure_ascii=False, indent=2)
                print(f"✅ AI 생성 주제 {len(validated_topics)}개 검증 완료 및 캐시 저장")
            
            return validated_topics
            
        except Exception as e:
            print(f"⚠️ AI 주제 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_all_existing_topics(self, content_type: ContentType) -> List[str]:
        """기존 주제 풀에서 모든 주제 가져오기 (중복 확인용)"""
        all_topics = []
        
        # HIGH_PERFORMING_TOPICS에서 주제 가져오기
        high_performing = self._get_high_performing_topics(content_type)
        all_topics.extend(high_performing)
        
        # _generate_topic의 topics 리스트에서 주제 가져오기 (하드코딩된 주제들)
        # 이 부분은 동적으로 가져올 수 없으므로, 주요 주제만 포함
        # 실제로는 데이터베이스나 파일에서 관리하는 것이 좋지만, 현재는 이렇게 처리
        
        return all_topics
    
    def _select_topic_with_strategy(
        self,
        global_topics: List[str],
        seasonal_topics: List[str],
        performance_topics: List[str],
        youtube_trending_topics: List[str] = None
    ) -> Tuple[str, Optional[str]]:
        """TREND_MODE 여부에 따라 주제 선택 전략을 적용."""
        global_pool = [topic for topic in global_topics if topic]
        seasonal_pool = [topic for topic in seasonal_topics if topic]
        performance_pool = [topic for topic in performance_topics if topic]
        trending_pool = [topic for topic in (youtube_trending_topics or []) if topic]

        if getattr(config, 'TREND_MODE', False):
            pools: List[Tuple[List[str], str]] = []
            weights: List[float] = []

            def add_pool(pool: List[str], source: str, weight: float) -> None:
                if pool and weight > 0:
                    pools.append((pool, source))
                    weights.append(weight)

            # YouTube 트렌드가 있으면 글로벌 트렌드에 포함
            if trending_pool:
                # YouTube 트렌드와 글로벌 풀을 합침
                combined_global = list(dict.fromkeys(global_pool + trending_pool))
                add_pool(combined_global, 'youtube_trend', self.TREND_WEIGHTS['global'])
            else:
                add_pool(global_pool, 'global_trend', self.TREND_WEIGHTS['global'])
            
            add_pool(seasonal_pool, 'seasonal', self.TREND_WEIGHTS['seasonal'])
            add_pool(performance_pool, 'performance', self.TREND_WEIGHTS['performance'])

            exploration_candidates = list(dict.fromkeys(
                (trending_pool if trending_pool else global_pool) + seasonal_pool + performance_pool))
            exploration_pool = exploration_candidates or global_pool or seasonal_pool or performance_pool
            add_pool(exploration_pool, 'exploration', self.TREND_WEIGHTS['exploration'])

            if pools:
                idx = random.choices(range(len(pools)), weights=weights, k=1)[0]
                selected_pool, source = pools[idx]
                
                # CPM 점수 기반 가중치 선택
                # 주제별 CPM 점수를 계산하여 가중치 적용
                try:
                    from src.analytics.trend_collector import TrendCollector
                    collector = TrendCollector()
                    
                    # 각 주제의 CPM 점수 계산
                    topic_weights = []
                    for topic in selected_pool:
                        cpm_score = collector.analyze_cpm_potential(topic)
                        topic_weights.append(cpm_score)
                    
                    # 가중치 기반 선택 (CPM 점수가 높을수록 선택 확률 증가)
                    if topic_weights and sum(topic_weights) > 0:
                        selected_topic = random.choices(selected_pool, weights=topic_weights, k=1)[0]
                        return selected_topic, source
                except Exception as e:
                    print(f"⚠️ CPM 기반 선택 실패, 랜덤 선택으로 폴백: {e}")
                
                # CPM 선택 실패 시 랜덤 선택
                return random.choice(selected_pool), source

        if seasonal_pool and random.random() < 0.25:
            return random.choice(seasonal_pool), 'seasonal'

        fallback_pool = trending_pool or global_pool or performance_pool or seasonal_pool
        if not fallback_pool:
            return "Momentum reset routine", 'global_trend'
        return random.choice(fallback_pool), 'global_trend'
    
    # _build_default_script 메서드는 script_generator.py로 이동됨
    
    def _prepare_thumbnail_canvas(self,
                                  thumbnail_path: str,
                                  target_size: Tuple[int,
                       int]) -> Optional[str]:
        """썸네일 이미지를 영상 해상도에 맞춰 중앙 정렬한 캔버스 생성."""
        if not os.path.exists(thumbnail_path):
            return None
        try:
            img = Image.open(thumbnail_path).convert('RGB')
            target_w, target_h = target_size
            target_ratio = target_w / target_h
            img_ratio = img.width / img.height if img.height else target_ratio

            if img_ratio > target_ratio:
                new_width = target_w
                new_height = int(target_w / img_ratio)
            else:
                new_height = target_h
                new_width = int(target_h * img_ratio)

            resample_filter = Image.Resampling.LANCZOS if hasattr(
                Image, "Resampling") else Image.LANCZOS
            resized = img.resize((new_width, new_height), resample_filter)

            canvas = Image.new('RGB', (target_w, target_h), (0, 0, 0))
            offset = (
                (target_w - new_width) // 2,
                (target_h - new_height) // 2)
            canvas.paste(resized, offset)

            temp_path = os.path.join(
                config.TEMP_DIR,
                f"thumb_canvas_{int(time.time()*1000)}.jpg")
            canvas.save(temp_path, 'JPEG')
            return temp_path
        except Exception as e:
            print(f"⚠️ 썸네일 캔버스 생성 실패: {e}")
            return None

    def embed_thumbnail_frame(
        self,
        video_path: str,
        thumbnail_path: str,
        duration: float = 0.6) -> str:
        """생성된 썸네일을 영상의 첫 프레임으로 삽입."""
        if not video_path or not os.path.exists(video_path):
            print("⚠️ 영상 파일을 찾을 수 없어 썸네일 프레임을 삽입하지 않습니다.")
            return video_path
        if not thumbnail_path or not os.path.exists(thumbnail_path):
            print("⚠️ 썸네일 파일이 없어 썸네일 프레임을 삽입하지 않습니다.")
            return video_path

        intro_clip = None
        video_clip = None
        combined_clip = None
        canvas_path = None
        try:
            video_clip = VideoFileClip(video_path)
            fps = video_clip.fps or 30
            target_size = video_clip.size

            canvas_path = self._prepare_thumbnail_canvas(
                thumbnail_path, target_size)
            if not canvas_path:
                return video_path

            intro_clip = ImageClip(canvas_path).set_duration(
                duration).set_fps(fps).resize(target_size)
            combined_clip = concatenate_videoclips(
                [intro_clip, video_clip], method="compose")

            temp_output = os.path.join(
                config.TEMP_DIR,
                f"with_thumb_{int(time.time()*1000)}.mp4")
            temp_audio = os.path.join(
                config.TEMP_DIR,
                f"with_thumb_audio_{int(time.time()*1000)}.m4a")
            combined_clip.write_videofile(
                temp_output,
                fps=fps,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=temp_audio,
                remove_temp=True,
                logger=None
            )

            combined_clip.close()
            intro_clip.close()
            video_clip.close()

            os.replace(temp_output, video_path)
            print("✅ 썸네일 이미지를 영상 첫 프레임으로 삽입했습니다.")
        except Exception as e:
            print(f"⚠️ 썸네일 프레임 삽입 실패: {e}")
        finally:
            for clip in (combined_clip, intro_clip, video_clip):
                try:
                    if clip:
                        clip.close()
                except Exception:
                    pass
            if canvas_path and os.path.exists(canvas_path):
                try:
                    os.remove(canvas_path)
                except OSError:
                    pass
        return video_path
    
    def generate_video(
        self,
        topic: str = None,
        duration: int = None,
        output_filename: str = None,
        performance_prompt: str = None,
        content_type: ContentType = None,
        language: str = 'ko',
        target_audience: str = None
    ) -> tuple:
        """
        AI로 YouTube Shorts 영상 생성 (55초 목표, 매번 새로운 아이디어)
        
        Args:
            topic: 영상 주제 (None이면 AI로 자동 생성 - 매번 새로운 아이디어)
            duration: 영상 길이 (초, None이면 자동 계산, 목표 55초)
            output_filename: 출력 파일명 (None이면 자동 생성)
            performance_prompt: 성과 기반 프롬프트 (선택)
            content_type: 콘텐츠 타입 (None이면 자동 선택)
            language: 언어 코드 ('ko' 또는 'en', 기본값: 'ko')
            target_audience: 타겟 오디언스 (예: '25-45세 직장인', '대학생', '은퇴자' 등)
        
        Returns:
            (생성된 영상 파일 경로, 스크립트 리스트, 주제, 주제 출처) 튜플
        """
        topic_source = None  # 주제 출처 초기화
        
        # 주제가 없으면 AI로 새로운 주제 생성 (템플릿 사용 안 함)
        if not topic:
            topic, topic_source = self._generate_topic(
                content_type=content_type)
        else:
            # 주제가 주어진 경우 콘텐츠 타입 자동 감지
            if content_type is None:
                content_type_str = getattr(config, "CONTENT_TYPE", "auto")
                try:
                    content_type = ContentType(content_type_str.lower())
                except ValueError:
                    content_type = ContentType.AUTO
        content_type_str = content_type.value if content_type else 'auto'
        print(
            f"📹 영상 생성 시작: '{topic}' (타입: {content_type_str}, 언어: {language})")

        # 영상 스크립트 생성 (55초 목표, 매번 새로운 아이디어로 생성)
        script = self._generate_script(
            topic,
            performance_prompt=performance_prompt,
            content_type=content_type,
            language=language,
            target_audience=target_audience
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
                print(
                    f"📝 스크립트가 짧아서 더 긴 내용 생성 필요 (현재: {calculated_duration:.1f}초, 목표: {target_duration}초)")

            content_type_str_for_log = content_type.value if content_type else 'auto'
            print(
                f"📏 스크립트 기반 자동 길이: {duration}초 ({len(script)}개 문장, 목표: {target_duration}초, 타입: {content_type_str_for_log})")
        
        # 영상 생성
        video_path = self._create_video_from_script(
            script, topic, duration, output_filename, content_type=content_type, language=language)
        
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
                # 💸 Money / Investing Hooks
                "Why your salary alone will never make you wealthy",
                "Top earners share the same exact bank account structure",
                "Rich people refuse to make this one impulse purchase",
                "Feel richer without earning more: the invisible income trick",
                "The single habit every maxed-out credit-card user shares",
                "Disciplined savers always do this first on payday",
                "How some people grow assets faster than their paycheck",
                "The most realistic investing path for busy professionals",
                "Money vanishes in patterns, not accidents.",
                "Structure builds wealth faster than motivation ever could.",
                # 🧠 Self-improvement / Routine Hooks
                "Ten minutes of routine that completely reroutes your life",
                "The morning behaviors high performers never skip",
                "The exact moment weak follow-through collapses",
                "Why top performers rely on systems, not motivation",
                "Why late-night work rarely turns into real results",
                "Routines decide your life long before you do.",
                "Tiny routines create massive peace.",
                # 🏠 Lifestyle / Declutter Hooks
                "The simple rule people with tidy homes follow every day",
                "Why you keep buying clothes but feel you have nothing to wear",
                "A chaotic fridge usually signals chaotic money habits",
                "Declutter one room and watch your stress plummet",
                "Only 20% of your closet actually leaves the house.",
                # 🚨 Risk / Downside Protection Hooks
                "One accident that can erase years of savings overnight",
                "Why insurance alone can’t keep you from bankruptcy",
                "How some people turn crises into opportunities while others crumble",
                "Skipping winter maintenance is the most expensive gamble.",
                # 🤖 AI / Automation Hooks
                "AI automation frees the 30 minutes you keep losing.",
                "Treat your calendar like code and it stops breaking.",
            ]
            # 계절별 우선 주제
            seasonal_topics = {
                'spring': [
        "Why new-year plans keep collapsing by March",
        "How people who reset each season look five years later",
        "Why your salary alone will never make you wealthy",
        "The simple rule people with tidy homes follow every day",
    ],
                'summer': [
            "One vacation drained your bank account—here’s why",
            "The real culprit eating more power than your AC",
            "The single habit every maxed-out credit-card user shares",
            "Disciplined savers always do this first on payday",
        ],
                'autumn': [
                "Half the year is gone—here’s why your goals still aren’t done",
                "People who flip their year in Q3 are decluttering right now",
                "How some people grow assets faster than their paycheck",
                "Declutter one room and watch your stress plummet",
            ],
                'winter': [
                    "Why money vanishes the moment the holidays arrive",
                    "The winter expense scarier than heating bills",
                    "One accident that can erase years of savings overnight",
                    "Rich people refuse to make this one impulse purchase",
        ]}
        elif content_type == ContentType.QUOTE:
            topics = [
                # 🌤 Lifestyle / Routine Quotes
                "Decluttering a room calms your mind, and a calm mind cuts anxiety.",
                "When seasons change, your priorities must be reorganized too.",
                "A clean home is a shortcut to a rested mind.",
                "Tiny routines create massive peace.",
                "Preparing for winter is really about removing future discomfort.",
                "Simplicity is the cheat code for focus.",
                # 💸 Money / Investing Quotes
                "Wealth is built by structure, not random savings.",
                "Time in the market beats timing the market.",
                "The moment you track spending, new options appear.",
                "Managers of money become rich; earners alone rarely do.",
                "Wealth gaps come from repeated choices, not single wins.",
                "Money is measurement; direction is wealth.",
                # 🧠 Self-development Quotes
                "Routines become habits, and habits build your life.",
                "Improve by one percent today and you become someone else in a year.",
                "Consistency outruns talent every single time.",
                "Automation is focus insurance.",
            ]
            seasonal_topics = {
                'spring': [
                    "When seasons change, your priorities must be reorganized too.",
                    "Decluttering a room calms your mind, and a calm mind cuts anxiety.",
                ],
                'summer': [
                    "The moment you track spending, new options appear.",
                    "Busy people are common; people doing important work are rare.",
                ],
                'autumn': [
                    "Wealth gaps come from repeated choices, not single wins.",
                    "Your home shows who you are; your routines show who you'll become.",
                ],
                'winter': [
                    "Wealth is built by structure, not random savings.",
                    "Routines become habits, and habits build your life.",
                ],
            }
        elif content_type == ContentType.STORY:
            topics = [
                # 🌤 Lifestyle Stories
                "How one family finally killed the summer mold problem",
                "The winter their heating bill dropped in half",
                "The messy closet that turned into a seasonal reset routine",
                "A driver who almost paid thousands because they skipped one inspection",
                "He cleared one closet and reset his entire routine.",
                # 💸 Money / Investing Stories
                "The employee who grew $250K of assets on a $40K salary",
                "A simple auto-invest rule that changed an average worker’s life",
                "She tracked spending for 60 days and freed $300 every month",
                "The notebook that documented the road to financial independence",
                "A 30-day expense log rebuilt her bank balance.",
                # 🧠 Self-development Stories
                "Ten-minute routines that rescued someone’s burnout",
                "How a chronic planner finally became an action-taker",
                "A five-minute evening review saved a burned-out manager.",
                "An AI micro-routine gave him back an hour every morning.",
            ]
            seasonal_topics = {
                'spring': ["The messy closet that turned into a seasonal reset routine"],
                'summer': ["How one family finally killed the summer mold problem"],
                'autumn': ["The messy closet that turned into a seasonal reset routine"],
                'winter': [
        "The winter their heating bill dropped in half",
        "A driver who almost paid thousands because they skipped one inspection",
        ]}
        elif content_type == ContentType.FACT:
            topics = [
                # 🌤 Lifestyle Facts
                "Most summer power bills leak from one forgotten appliance",
                "Homes get dirtiest during seasonal transitions because humidity spikes",
                "The physics behind why some homes pay half the heating cost",
                "Clothes discolor faster when your closet airflow is blocked",
                "Fridge odor usually means you’re throwing away 20% of groceries",
                "Decluttered desks raise focus by 25%.",
                # 🚗 Car Facts
                "Skipping one winter oil check can cost a full engine replacement",
                "Worn tires raise stopping distance by up to 40%",
                "Wiper blades lose 20% visibility every season",
                # 💰 Money / Economy Facts
                "Wealthy people track spending to see direction, not guilt",
                "Compound interest is a patience game, not a math trick",
                "Broad-market ETFs are the safest on-ramp for new investors",
                "Tracking spend for 30 days cuts impulse buys by 15%.",
                # 🧠 Self-development Facts
                "Morning routines increase decision-making speed by 23%",
                "Small habits change your default choices—not just your mood",
                "AI batching saves at least 30 minutes per day.",
            ]
            seasonal_topics = {
                'spring': [
        "Homes get dirtiest during seasonal transitions because humidity spikes",
        "Clothes discolor faster when your closet airflow is blocked",
    ],
                'summer': [
            "Most summer power bills leak from one forgotten appliance",
            "Fridge odor usually means you’re throwing away 20% of groceries",
        ],
                'autumn': [
                "Homes get dirtiest during seasonal transitions because humidity spikes",
                "Wiper blades lose 20% visibility every season",
            ],
                'winter': [
                    "The physics behind why some homes pay half the heating cost",
                    "Skipping one winter oil check can cost a full engine replacement",
                    "Worn tires raise stopping distance by up to 40%",
        ]}
        elif content_type == ContentType.SHORT_STORY:
            topics = [
                # 🌤 Lifestyle Short Stories
                "Decluttering one closet erased my morning panic",
                "Preparing for winter once cut our heating bill in half",
                "Labeling fridge zones stopped us from throwing away food",
                "Controlling humidity removed that strange smell overnight",
                "Ten minutes of routine completely rerouted her life.",
                # 💸 Money Short Stories
                "Switching from savings to auto-investing finally left money in my account",
                "Logging expenses for 30 days changed my bank balance",
                "Automating tiny bills finally calmed my bank account.",
                # 🧠 Self-development Short Stories
                "A five-minute evening review saved my burnout",
                "Choosing one tiny action daily created a huge pivot",
                "I automated emails with AI and finally slept.",
            ]
            seasonal_topics = {
                'spring': [
        "Decluttering one closet erased my morning panic",
        "Controlling humidity removed that strange smell overnight",
    ],
                'summer': [
            "Labeling fridge zones stopped us from throwing away food",
            "Controlling humidity removed that strange smell overnight",
        ],
                'autumn': [
                "Decluttering one closet erased my morning panic",
            ],
                'winter': [
                    "Preparing for winter once cut our heating bill in half",
        ]}
        else:
            # 기본 주제
            topics = [
                "A seasonal refresh you can do right now",
                "How to make life easier without cutting every expense",
                "The ten-minute routine that changes the next year",
            ]
            seasonal_topics = {
                'spring': ["A seasonal refresh you can do right now"],
                'summer': ["A seasonal refresh you can do right now"],
                'autumn': ["A seasonal refresh you can do right now"],
                'winter': ["A seasonal refresh you can do right now"]
            }

        seasonal_list = seasonal_topics.get(current_season, [])
        performance_topics = self._get_high_performing_topics(content_type)
        
        # YouTube 트렌드 주제 가져오기 (TREND_MODE일 때만)
        youtube_trending_topics = []
        ai_generated_topics = []
        ai_seasonal_topics = []
        
        if getattr(config, 'TREND_MODE', False):
            try:
                youtube_trending_topics = self._get_youtube_trending_topics()
                
                # AI 기반 주제 생성 (트렌드 키워드 기반)
                try:
                    language = 'en'  # 현재 영어 콘텐츠만 생성
                    ai_generated_topics = self._generate_ai_topics_from_trends(
                        content_type=content_type,
                        language=language
                    )
                    
                    # AI 생성 주제를 글로벌 주제 풀에 추가
                    if ai_generated_topics:
                        topics.extend(ai_generated_topics)
                        print(f"📝 AI 생성 주제 {len(ai_generated_topics)}개를 주제 풀에 추가")
                except Exception as e:
                    print(f"⚠️ AI 주제 생성 실패: {e}")
                
                # 계절별 AI 주제 생성 (트렌드 키워드 기반)
                try:
                    ai_seasonal_topics = self._generate_seasonal_topics_from_trends(
                        season=current_season,
                        content_type=content_type,
                        language=language
                    )
                    
                    # AI 생성 계절별 주제를 계절별 주제 풀에 추가
                    if ai_seasonal_topics:
                        seasonal_list.extend(ai_seasonal_topics)
                        print(f"🍂 {current_season} 계절 AI 생성 주제 {len(ai_seasonal_topics)}개를 계절별 주제 풀에 추가")
                except Exception as e:
                    print(f"⚠️ 계절별 AI 주제 생성 실패: {e}")
                    
            except Exception as e:
                print(f"⚠️ YouTube 트렌드 주제 가져오기 실패: {e}")

        topic, source = self._select_topic_with_strategy(
            global_topics=topics,
            seasonal_topics=seasonal_list,
            performance_topics=performance_topics,
            youtube_trending_topics=youtube_trending_topics
        )
        
        # AI 생성 주제가 선택되었는지 확인
        if topic in ai_generated_topics:
            source = 'ai_generated'
        elif topic in ai_seasonal_topics:
            source = 'ai_seasonal'

        if source == 'seasonal':
            print(f"🍂 계절 주제 선택: {current_season} → '{topic}'")
        elif source == 'ai_seasonal':
            print(f"🤖🍂 AI 생성 계절 주제 선택: {current_season} → '{topic}'")
        elif source == 'performance':
            print(f"📈 성과 기반 주제 선택: '{topic}'")
        elif source == 'exploration':
            print(f"🎲 탐색 주제 선택: '{topic}'")
        elif source == 'ai_generated':
            print(f"🤖 AI 생성 주제 선택: '{topic}'")
        elif source == 'youtube_trend' and getattr(config, 'TREND_MODE', False):
            print(f"🌍 YouTube 트렌드 주제 선택: '{topic}'")
        elif source == 'global_trend' and getattr(config, 'TREND_MODE', False):
            print(f"🌍 글로벌 트렌드 주제 선택: '{topic}'")

        return topic, content_type
    
    def _generate_script(
        self,
        topic: str,
        performance_prompt: str = None,
        content_type: ContentType = None,
        language: str = 'ko',
        target_audience: str = None) -> list:
        """AI로 영상 스크립트 생성 (콘텐츠 타입별 최적화)"""
        return self.script_generator.generate_script(
            topic, performance_prompt, content_type, language, target_audience
        )

    # _generate_script_with_claude 메서드는 script_generator.py로 이동됨

    # _generate_script_with_openai 메서드는 script_generator.py로 이동됨
    
    def _create_video_from_script(
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
        
        Args:
            script: 스크립트 리스트
            topic: 영상 주제
            duration: 목표 영상 길이 (초)
            output_filename: 출력 파일명
            content_type: 콘텐츠 타입
            language: 언어 코드
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
            audio_path = self._generate_audio(sentence, i, content_type=content_type_str, language=language)
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
                # script와 sentence_audio_durations는 항상 같은 길이이므로,
                # audio_clips의 길이가 pop 전 script 길이와 같거나 더 크면 pop
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

        # 배경 미디어 그룹핑: 2-3개 문장마다 배경 변경 (관련 문장들은 같은 배경 사용)
        background_groups = []
        group_size = VideoConstants.BACKGROUND_GROUP_SIZE
        use_background_video = getattr(config, 'USE_BACKGROUND_VIDEO', True)

        # 각 그룹에서 사용할 배경 영상의 시작 시간을 추적 (순차 재생용)
        video_start_times = {}  # {bg_video_path: current_start_time}
        downloaded_videos = []  # 이미 다운로드한 영상 경로 추적 (중복 방지)
        
        for i in range(0, len(script), group_size):
            group_end = min(i + group_size, len(script))
            group_sentence = script[i]
            group_duration = sum(sentence_audio_durations[i:group_end])
            
            # 배경 영상 다운로드 시도 (USE_BACKGROUND_VIDEO가 true이고 Pexels API 키가 있을 때)
            # 각 그룹마다 다른 배경 영상을 다운로드하도록 개선
            # 실패 시 재시도 (최대 3회)
            bg_video_path = None
            if use_background_video and config.PEXELS_API_KEY:
                max_retries = 3
                for retry in range(max_retries):
                    bg_video_path = self._download_video_for_sentence(
                        group_sentence,
                        i,
                        group_duration,
                        topic=topic,
                        exclude_videos=downloaded_videos  # 이미 다운로드한 영상 제외
                    )
                    if bg_video_path:
                        downloaded_videos.append(bg_video_path)
                        break
                    elif retry < max_retries - 1:
                        print(
                            f"   ⚠️ 배경 영상 다운로드 실패, 재시도 {retry + 1}/{max_retries}")
                if not bg_video_path:
                    print(f"   ⚠️ 배경 영상 다운로드 최종 실패, 그라데이션 배경 사용")

            # 배경 영상이 없으면 그라데이션 배경 사용 (이상한 이미지 방지)
            bg_image = None
            if not bg_video_path:
                # 이미지 다운로드 제거, 바로 그라데이션 배경 사용
                    bg_image = self._create_gradient_background(i, len(script))
            
            # 배경 영상이 있으면 시작 시간 초기화 (아직 사용하지 않았으면)
            if bg_video_path and bg_video_path not in video_start_times:
                video_start_times[bg_video_path] = 0.0
            
            background_groups.append((i, group_end, bg_video_path, bg_image))
            media_type = "영상" if bg_video_path else "이미지"
            print(
                f"   배경 미디어 그룹 {len(background_groups)}: 문장 {i+1}-{group_end} ({media_type}) - {group_sentence[:30]}...)")

        # 배경 영상들을 순차적으로 재생하기 위한 추적 변수
        current_bg_video_index = 0  # 현재 사용 중인 배경 영상 인덱스
        current_bg_video_start_time = 0.0  # 현재 배경 영상의 시작 시간
        current_bg_video_path = None  # 현재 배경 영상 경로
        current_bg_video_clip = None  # 현재 배경 영상 클립 (재사용)
        current_bg_video_used_duration = 0.0  # 현재 배경 영상이 사용된 총 시간
        
        # 각 문장별로 영상 클립 생성
        for i, sentence in enumerate(script):
            # 실제 음성 길이에 맞춘 duration 사용
            sentence_duration = sentence_audio_durations[i]
            actual_audio_duration = sentence_audio_durations[i] if i < len(
                sentence_audio_durations) else sentence_duration
            
            # 해당 문장이 속한 그룹의 배경 미디어 찾기
            bg_video_path = None
            bg_image = None
            group_start = None
            group_end = None
            for gs, ge, gv, gi in background_groups:
                if gs <= i < ge:
                    bg_video_path = gv
                    bg_image = gi
                    group_start = gs
                    group_end = ge
                    break
            
            # 새로운 배경 영상 그룹이 시작되면 이전 배경 영상 종료
            if bg_video_path and bg_video_path != current_bg_video_path:
                # 이전 배경 영상이 있으면 종료
                if current_bg_video_clip:
                    current_bg_video_clip.close()
                # 새로운 배경 영상 시작
                current_bg_video_path = bg_video_path
                current_bg_video_start_time = 0.0
                current_bg_video_used_duration = 0.0
                current_bg_video_clip = None
            
            # 배경 영상이 있으면 영상 클립 사용
            if bg_video_path and os.path.exists(bg_video_path):
                try:
                    # 배경 영상을 처음 로드하거나 새로운 배경 영상이면 전체 영상 로드
                    if current_bg_video_clip is None:
                        print(f"   📹 배경 영상 로드: {bg_video_path}")
                        source_video = VideoFileClip(bg_video_path)
                        source_duration = source_video.duration
                        print(f"   원본 영상 길이: {source_duration:.2f}초")
                        # 전체 영상을 로드 (자르지 않음)
                        current_bg_video_clip = source_video.resize((VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT))
                        current_bg_video_start_time = 0.0
                        current_bg_video_used_duration = 0.0
                    start_time = current_bg_video_start_time
                    source_duration = current_bg_video_clip.duration

                    # 배경 영상이 끝에 도달했는지 확인
                    if start_time >= source_duration:
                        print(
                            f"   ⚠️ 문장 {i+1}: 배경 영상이 끝에 도달 ({start_time:.2f}초 >= {source_duration:.2f}초)")
                        # 다음 그룹의 배경 영상이 있는지 확인
                        next_bg_video_path = None
                        for gs, ge, gv, gi in background_groups:
                            if gs > i:  # 현재 문장 이후의 그룹
                                if gv and os.path.exists(
                                        gv) and gv != current_bg_video_path:
                                    next_bg_video_path = gv
                                    break

                        if next_bg_video_path:
                            print(f"   🔄 다음 배경 영상으로 전환: {next_bg_video_path}")
                            # 이전 배경 영상 종료
                            if current_bg_video_clip:
                                current_bg_video_clip.close()
                            # 새로운 배경 영상 시작
                            current_bg_video_path = next_bg_video_path
                            current_bg_video_start_time = 0.0
                            current_bg_video_used_duration = 0.0
                            current_bg_video_clip = None
                            bg_video_path = next_bg_video_path
                            # 새로운 배경 영상 로드
                            source_video = VideoFileClip(bg_video_path)
                            source_duration = source_video.duration
                            print(f"   원본 영상 길이: {source_duration:.2f}초")
                            current_bg_video_clip = source_video.resize(
                                (VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT))
                            current_bg_video_start_time = 0.0
                            start_time = 0.0
                        else:
                            print(f"   ⚠️ 다음 배경 영상이 없음, 이미지로 대체")
                            bg_video_path = None  # 이미지로 대체
                    else:
                        # 배경 영상을 음성 길이만큼만 자르기 (같은 영상 반복 방지)
                        # 현재 위치부터 음성 길이만큼만 사용
                        end_time = min(
                            start_time + actual_audio_duration, source_duration)
                        video_clip = current_bg_video_clip.subclip(
                            start_time, end_time)
                        # duration을 정확히 음성 길이로 설정 (자막이 끝나는 곳과 일치)
                        video_clip = video_clip.set_duration(
                            actual_audio_duration)

                        # 다음 문장을 위해 시작 시간 업데이트 (음성 길이만큼 진행)
                        current_bg_video_start_time = start_time + actual_audio_duration
                        current_bg_video_used_duration += actual_audio_duration

                        print(
                            f"   📍 배경 영상 재생 위치: {start_time:.2f}초~{end_time:.2f}초 (원본: {source_duration:.2f}초, 클립 duration: {actual_audio_duration:.2f}초, 음성: {actual_audio_duration:.2f}초)")

                        # 자막 추가 (각 문장의 음성 길이에 맞춰서 표시)
                        try:
                            print(
                                f"   문장 {i+1} 배경 영상 자막 추가 시도: {sentence[:30]}...")
                            subtitle_clip = self._create_subtitle_clip(
                                sentence, actual_audio_duration, language=language)
                            if subtitle_clip:
                                # 자막 클립의 duration을 정확히 음성 길이로 설정
                                subtitle_clip = subtitle_clip.set_duration(actual_audio_duration)
                                if getattr(subtitle_clip, "pos", None) is None:
                                    subtitle_clip = subtitle_clip.set_position(('center', 'bottom'))
                                # 자막 클립의 시작 시간을 명시적으로 0으로 설정 (동기화 보장)
                                # 중요: CompositeVideoClip에 추가하기 전에 시작 시간을 0으로
                                # 명시적으로 설정
                                subtitle_clip = subtitle_clip.set_start(0)
                                # 배경 영상 클립도 시작 시간 0으로 명시적으로 설정 (동기화 보장)
                                video_clip = video_clip.set_start(0)
                                # CompositeVideoClip 생성: 배경 영상과 자막 모두 시작 시간 0으로 설정
                                # 각 클립은 독립적으로 0에서 시작하므로, 연결 시에도 동기화 유지
                                video_clip = CompositeVideoClip(
                                    [video_clip, subtitle_clip])
                                # CompositeVideoClip의 duration을 정확히 음성 길이로 설정
                                video_clip = video_clip.set_duration(
                                    actual_audio_duration)
                                print(
                                    f"   ✅ 배경 영상 자막 추가 성공 (duration: {actual_audio_duration:.2f}초, 음성: {actual_audio_duration:.2f}초, 자막 start: 0초)")
                            else:
                                print(f"   ⚠️ 자막 클립이 None입니다")
                        except Exception as e:
                            print(f"   ❌ 자막 추가 실패 (계속 진행): {e}")
                            import traceback
                            traceback.print_exc()

                        # 전환 효과 개선: 첫 클립 fade in, 마지막 클립 fade out, 중간 클립은 양쪽 fade
                        is_last_sentence = (i == len(script) - 1)
                        is_first_sentence = (i == 0)
                        fade_duration = min(VideoConstants.DEFAULT_FADE_DURATION, actual_audio_duration * VideoConstants.FADE_RATIO)
                        
                        if is_first_sentence:
                            # 첫 클립: fade in만
                            if actual_audio_duration > fade_duration:
                                video_clip = video_clip.fx(fadein, fade_duration)
                                video_clip = video_clip.set_duration(actual_audio_duration)
                        elif is_last_sentence:
                            # 마지막 클립: fade out만
                            if actual_audio_duration > fade_duration:
                                video_clip = video_clip.fx(fadeout, fade_duration)
                                video_clip = video_clip.set_duration(actual_audio_duration)
                        else:
                            # 중간 클립: 양쪽 fade (부드러운 전환)
                            if actual_audio_duration > fade_duration * 2:
                                video_clip = video_clip.fx(fadein, fade_duration).fx(fadeout, fade_duration)
                                video_clip = video_clip.set_duration(actual_audio_duration)

                        print(
                            f"   ✅ 문장 {i+1} 클립 추가: {video_clip.duration:.2f}초 (음성 길이와 일치: {actual_audio_duration:.2f}초)")
                        print(f"   📁 사용한 배경 영상: {bg_video_path}")
                    
                    clips.append(video_clip)
                    continue

                except Exception as e:
                    print(f"   배경 영상 사용 실패, 이미지로 대체: {e}")
                    import traceback
                    traceback.print_exc()
                    bg_video_path = None  # 이미지로 대체
            
            # 배경 영상이 없거나 실패 시 그라데이션 배경 사용 (이상한 이미지 방지)
            if bg_image is None:
                print(f"   🎨 문장 {i+1} 그라데이션 배경 사용 (배경 영상 없음)")
                bg_image = self._create_gradient_background(i, len(script))
            
            # 자막 추가 (이미지에 핵심 단어 또는 전체 문장 그리기)
            subtitle_text = sentence
            subtitle_mode = getattr(config, "SUBTITLE_MODE", "full_sentence")
            use_keywords = subtitle_mode != 'full_sentence'
            if use_keywords:
                key_words = self._extract_key_words_for_subtitle(
                    sentence, language=language)
                if key_words:
                    subtitle_text = key_words
            text_image = self._draw_text_on_image(
                bg_image.copy(), subtitle_text, language=language)
            if use_keywords:
                print(
                    f"   문장 {i+1} 핵심 단어 자막 추가: {subtitle_text} (원본: {sentence[:30]}...)")
            else:
                print(f"   문장 {i+1} 전체 문장 자막 추가: {sentence[:30]}...")
            
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
                debug_path = os.path.join(
                    config.TEMP_DIR, f"debug_frame_0.png")
                text_image.save(debug_path, 'PNG')
                print(f"🔍 디버그: 첫 프레임 저장됨 - {debug_path}")
                print(
                    f"   이미지 크기: {text_image.size}, 모드: {text_image.mode}, 고유 색상: {unique_colors}")
            
            # 실제 음성 길이 사용
            actual_audio_duration = sentence_audio_durations[i] if i < len(
                sentence_audio_durations) else sentence_duration
            # 이미지 클립 생성 (실제 음성 길이에 맞춤)
            img_clip = ImageClip(bg_path).set_duration(actual_audio_duration)
            
            # 해상도 명시적 설정
            img_clip = img_clip.resize((VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT))
            
            # 페이드 효과 (duration 유지)
            if i == 0:
                # 첫 클립만 페이드 인
                img_clip = img_clip.fx(fadein, VideoConstants.DEFAULT_FADE_DURATION)
                img_clip = img_clip.set_duration(
                    actual_audio_duration)  # 페이드 후 duration 재설정
            elif i == len(script) - 1:
                # 마지막 클립만 페이드 아웃
                img_clip = img_clip.fx(fadeout, VideoConstants.DEFAULT_FADE_DURATION)
                img_clip = img_clip.set_duration(
                    actual_audio_duration)  # 페이드 후 duration 재설정
            # 중간 클립들은 페이드 효과 없음 (부드러운 전환)
            
            # 최종 duration 확인 및 강제 설정 (반복 방지)
            if abs(img_clip.duration - actual_audio_duration) > 0.01:
                print(
                    f"   문장 {i+1} 이미지 클립 duration 재설정: {img_clip.duration:.2f}초 -> {actual_audio_duration:.2f}초")
            img_clip = img_clip.set_duration(actual_audio_duration)

            print(
                f"   ✅ 문장 {i+1} 이미지 클립 추가: {img_clip.duration:.2f}초 (목표: {actual_audio_duration:.2f}초, 실제 음성: {actual_audio_duration:.2f}초)")

            # 클립 전환 지점 확인을 위한 로깅
            if i > 0 and len(clips) > 0:
                prev_clip = clips[-1]
                print(
                    f"   🔄 클립 전환: 이전 클립({prev_clip.duration:.2f}초) -> 현재 클립({img_clip.duration:.2f}초)")
                print(
                    f"      이전 클립 끝 시간: {sum(c.duration for c in clips):.2f}초")
                print(
                    f"      현재 클립 시작 시간: {sum(c.duration for c in clips):.2f}초")
            
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
        
        # duration이 다르면 조정 (모든 클립을 음성 길이와 일치시킴)
        # 각 클립은 이미 음성 길이와 일치하도록 설정되어 있으므로, 여기서는 확인만 함
        expected_total_duration = sum(
            sentence_audio_durations) if sentence_audio_durations else duration
        if abs(total_clip_duration - expected_total_duration) > 0.1:
            print(
                f"   ⚠️ 클립 총 길이 불일치: {total_clip_duration:.2f}초 vs 예상: {expected_total_duration:.2f}초")
            print(f"   각 클립을 음성 길이에 맞춰 조정합니다.")

        # 클립 연결 (중복 방지)
        print(f"🔗 클립 연결 중... (총 {len(clips)}개)")
        # 모든 클립의 duration을 음성 길이와 정확히 일치시킴 (자막이 끝나는 곳과 일치)
        for idx, clip in enumerate(clips):
            if idx < len(sentence_audio_durations):
                expected_duration = sentence_audio_durations[idx]
                # 모든 클립을 음성 길이에 맞춤
                if abs(clip.duration - expected_duration) > 0.01:
                    print(
                        f"   클립 {idx+1} duration 조정: {clip.duration:.2f}초 -> {expected_duration:.2f}초 (음성 길이와 일치)")
                    clips[idx] = clip.set_duration(expected_duration)
                else:
                    print(f"   클립 {idx+1}: {clip.duration:.2f}초 (음성 길이와 일치)")
            
            # 마지막 클립에 여유 추가 (음성이 뚝 끊기는 느낌 방지)
            if idx == len(clips) - 1:
                print(f"   🎬 마지막 클립에 {VideoConstants.FINAL_CLIP_EXTENSION}초 여유 추가 (자연스러운 마무리)")
                # 마지막 클립의 duration을 늘림 (영상은 정지 화면으로 유지됨)
                clips[idx] = clips[idx].set_duration(clips[idx].duration + VideoConstants.FINAL_CLIP_EXTENSION)

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
            print(
                f"      클립 {idx+1}: duration={clip.duration:.2f}초, size={clip.size}")

        # 모든 클립의 duration을 음성 길이와 정확히 일치시킴 (자막이 끝나는 곳과 일치)
        print(f"   클립 duration 최종 확인 (음성 길이와 일치):")
        for idx, clip in enumerate(valid_clips):
            expected_dur = sentence_audio_durations[idx] if idx < len(
                sentence_audio_durations) else clip.duration
            # 모든 클립을 음성 길이에 맞춤
            if abs(clip.duration - expected_dur) > 0.01:
                print(
                    f"      클립 {idx+1} duration 조정: {clip.duration:.2f}초 -> {expected_dur:.2f}초 (음성 길이와 일치)")
                valid_clips[idx] = clip.set_duration(expected_dur)
            else:
                print(f"      클립 {idx+1}: {clip.duration:.2f}초 (음성 길이와 일치)")

        # 클립 연결 (각 클립을 순차적으로 연결)
        # method를 명시하지 않으면 기본값이 사용되지만, 명시적으로 지정하여 중복 방지
        print(f"   클립 연결 실행 중...")
        # 각 클립이 정확히 한 번만 연결되도록 보장
        print(f"   연결할 클립 목록:")
        for idx, clip in enumerate(valid_clips):
            print(f"      클립 {idx+1}: {clip.duration:.2f}초")

        # 모든 클립의 duration을 음성 길이와 정확히 일치시킴
        print(f"   연결 전 각 클립 duration 최종 확인 (음성 길이와 일치):")
        for idx, clip in enumerate(valid_clips):
            expected_dur = sentence_audio_durations[idx] if idx < len(
                sentence_audio_durations) else clip.duration
            # 모든 클립을 음성 길이에 맞춤
            if abs(clip.duration - expected_dur) > 0.01:
                print(
                    f"      클립 {idx+1} duration 재설정: {clip.duration:.2f}초 -> {expected_dur:.2f}초 (음성 길이와 일치)")
                valid_clips[idx] = clip.set_duration(expected_dur)
            print(
                f"      클립 {idx+1} 최종 duration: {valid_clips[idx].duration:.2f}초 (음성: {expected_dur:.2f}초)")

        # 클립 연결 (각 클립이 정확히 한 번만 재생되도록)
        # 중복 방지를 위해 명시적으로 method를 지정하지 않음 (기본값 사용)
        print(f"   클립 연결 실행 중... (총 {len(valid_clips)}개 클립)")

        # 각 클립이 정확히 한 번만 포함되도록 확인
        print(f"   연결 전 최종 검증:")
        for idx, clip in enumerate(valid_clips):
            expected_dur = sentence_audio_durations[idx] if idx < len(
                sentence_audio_durations) else clip.duration
            print(
                f"      클립 {idx+1}: duration={clip.duration:.2f}초 (예상: {expected_dur:.2f}초)")

        # concatenate_videoclips 호출 (각 클립을 정확히 한 번씩만 연결)
        # method="chain"은 기본값이지만 명시적으로 지정하여 중복 방지
        # transition=None으로 설정하여 클립 경계에서 중복 방지
        print(f"   최종 연결: {len(valid_clips)}개 클립을 순차적으로 연결 (경계 중복 방지)")
        final_video = concatenate_videoclips(
            valid_clips, method="chain", transition=None)

        # 연결 직후 즉시 정확한 길이로 자르기 (반복 방지)
        clips_total = sum(c.duration for c in valid_clips)
        actual_total_duration = sum(sentence_audio_durations)
        target_duration = clips_total  # 클립 합계를 기준으로 사용 (가장 정확함)

        print(
            f"📏 예상 총 길이: {actual_total_duration:.2f}초, 클립 합계: {clips_total:.2f}초, 연결 후: {final_video.duration:.2f}초")

        # 연결 직후 즉시 정확한 길이로 자르기 (반복 방지)
        if abs(final_video.duration - target_duration) > 0.01:
            print(
                f"⚠️ 연결 직후 길이 불일치 감지! ({final_video.duration:.2f}초 vs {target_duration:.2f}초)")
            print(f"   즉시 정확한 길이로 자르는 중...")
            final_video = final_video.subclip(0, target_duration)
            final_video = final_video.set_duration(target_duration)
            print(f"   조정 후: {final_video.duration:.2f}초")

        # 연결된 영상의 실제 프레임 수 확인
        if final_video.duration > 0:
            expected_frames = int(target_duration * VideoConstants.VIDEO_FPS)
            actual_frames = int(final_video.duration * VideoConstants.VIDEO_FPS)
            print(f"📊 예상 프레임 수: {expected_frames}, 실제 프레임 수: {actual_frames}")

            # 프레임 수가 예상보다 많으면 강제로 정확한 길이로 자르기 (반복 감지)
            if actual_frames > expected_frames * 1.05:  # 5% 이상 차이나면
                print(
                    f"⚠️ 프레임 수가 예상보다 많습니다! ({actual_frames} > {expected_frames}) - 반복 가능성")
                print(f"   강제로 정확한 길이로 자르는 중...")
                final_video = final_video.subclip(0, target_duration)
                final_video = final_video.set_duration(target_duration)
                actual_frames_after = int(final_video.duration * 30)
                print(
                    f"   강제 조정 후: {final_video.duration:.2f}초, 프레임 수: {actual_frames_after}")

        print(f"✅ 최종 영상 길이: {final_video.duration:.2f}초")
        
        # 음성 추가 (각 문장별로 정확히 매칭, 마지막 음성이 잘리지 않도록)
        if audio_clips:
            try:
                from moviepy.audio.AudioClip import concatenate_audioclips
                final_audio = concatenate_audioclips(audio_clips)
                
                # 실제 음성 길이와 영상 길이 확인
                actual_audio_duration = final_audio.duration
                actual_video_duration = final_video.duration

                print(
                    f"🎵 음성 총 길이: {actual_audio_duration:.2f}초, 영상 총 길이: {actual_video_duration:.2f}초")

                # 음성 총 길이와 영상 총 길이를 정확히 일치시킴
                if abs(actual_video_duration - actual_audio_duration) > 0.01:
                    print(
                        f"   영상 길이를 음성 길이에 맞춤: {actual_video_duration:.2f}초 -> {actual_audio_duration:.2f}초")
                    if actual_video_duration > actual_audio_duration:
                        # 영상이 더 길면 자르기
                        final_video = final_video.subclip(
                            0, actual_audio_duration)
                    else:
                        # 영상이 더 짧으면 마지막 프레임 반복하여 확장 (같은 영상 반복 방지)
                        extension_needed = actual_audio_duration - actual_video_duration
                        print(f"   영상 확장 필요: {extension_needed:.2f}초")
                        # 마지막 부분을 반복
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
                
                # 최종 길이 확인 및 최대 길이 초과 방지
                max_safe_duration = VideoConstants.MAX_DURATION
                if actual_video_duration > max_safe_duration:
                    print(
                        f"⚠️ 최종 영상 길이가 {max_safe_duration}초를 초과합니다. {max_safe_duration}초로 제한합니다.")
                    actual_video_duration = max_safe_duration
                    final_video = final_video.subclip(0, actual_video_duration)
                
                # 배경 음악 추가 (선택적)
                if getattr(config, 'USE_BACKGROUND_MUSIC', True):
                    try:
                        # topic 변수는 _create_video_from_script의 파라미터로 전달됨
                        background_music_path = self._download_background_music(
                            content_type=content_type if content_type else ContentType.AUTO,
                            duration=actual_audio_duration,
                            topic=topic
                        )
                        
                        if background_music_path and os.path.exists(background_music_path):
                            # 배경 음악 로드
                            bg_music = AudioFileClip(background_music_path)
                            
                            # 음악 길이를 영상 길이에 맞게 조정 (루프 또는 자르기)
                            if bg_music.duration < actual_audio_duration:
                                # 음악이 짧으면 루프
                                loops_needed = int(actual_audio_duration / bg_music.duration) + 1
                                bg_music_clips = []
                                original_duration = bg_music.duration
                                for _ in range(loops_needed):
                                    # 각 루프마다 새로운 클립 생성 (같은 파일에서)
                                    loop_clip = AudioFileClip(background_music_path)
                                    bg_music_clips.append(loop_clip)
                                from moviepy.audio.AudioClip import concatenate_audioclips
                                bg_music_looped = concatenate_audioclips(bg_music_clips)
                                bg_music_looped = bg_music_looped.subclip(0, actual_audio_duration)
                                # 원본 클립 정리
                                bg_music.close()
                                bg_music = bg_music_looped
                            else:
                                # 음악이 길면 자르기
                                bg_music = bg_music.subclip(0, actual_audio_duration)
                            
                            # 배경 음악 볼륨 조정
                            music_volume = getattr(config, 'BACKGROUND_MUSIC_VOLUME', VideoConstants.DEFAULT_MUSIC_VOLUME)
                            bg_music = bg_music.volumex(music_volume)
                            
                            # 페이드 인/아웃 효과 (부드러운 시작/종료)
                            fade_duration = min(1.0, actual_audio_duration * VideoConstants.MUSIC_FADE_RATIO)
                            bg_music = bg_music.fx(fadein, fade_duration).fx(fadeout, fade_duration)
                            bg_music = bg_music.set_duration(actual_audio_duration)
                            
                            # 음성과 배경 음악 믹싱
                            final_audio = CompositeAudioClip([final_audio, bg_music])
                            print(f"🎵 배경 음악 추가 완료 (볼륨: {music_volume*100:.0f}%)")
                            
                            # 배경 음악 클립 정리
                            bg_music.close()
                    except Exception as e:
                        print(f"⚠️ 배경 음악 추가 실패 (계속 진행): {e}")
                        import traceback
                        traceback.print_exc()
                
                # 음성 추가
                final_video = final_video.set_audio(final_audio)
                # 영상 길이를 음성 길이와 정확히 일치시킴
                final_video = final_video.set_duration(actual_audio_duration)
                
                print(
                    f"✅ 음성-영상 동기화 완료: 영상 {actual_video_duration:.2f}초, 음성 {actual_audio_duration:.2f}초 (정확히 일치)")
            except Exception as e:
                print(f"⚠️ 음성 추가 실패: {e}")
                import traceback
                traceback.print_exc()
        
        # FPS 설정
        final_video = final_video.set_fps(VideoConstants.VIDEO_FPS)
        
        # 해상도 확인 및 설정
        if final_video.size[0] != VideoConstants.VIDEO_WIDTH or final_video.size[1] != VideoConstants.VIDEO_HEIGHT:
            final_video = final_video.resize((VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT))
        
        # 영상 저장 전 최종 duration 확인 및 강제 조정 (음성 길이와 정확히 일치)
        if audio_clips and 'final_audio' in locals():
            actual_audio_duration = final_audio.duration
            actual_video_duration = final_video.duration
            if abs(actual_video_duration - actual_audio_duration) > 0.01:
                print(
                    f"⚠️ 저장 전 최종 확인: duration 불일치 (영상: {actual_video_duration:.2f}초 vs 음성: {actual_audio_duration:.2f}초)")
                # 영상 길이를 음성 길이와 정확히 일치시킴
                if actual_video_duration > actual_audio_duration:
                    final_video = final_video.subclip(0, actual_audio_duration)
                else:
                    final_video = final_video.set_duration(
                        actual_audio_duration)
                # 오디오 설정 (확실하게)
                final_video = final_video.set_audio(final_audio)
                final_video = final_video.set_duration(actual_audio_duration)
                print(f"   최종 조정 완료: {final_video.duration:.2f}초 (음성 길이와 일치)")

        # 마지막 클립에 fadeout이 이미 적용되어 있으므로 여기서는 추가하지 않음
        else:
            actual_total_duration = sum(sentence_audio_durations)
            if abs(final_video.duration - actual_total_duration) > 0.01:
                print(
                    f"⚠️ 저장 전 최종 확인: duration 불일치 ({final_video.duration:.2f}초 vs {actual_total_duration:.2f}초)")
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
    
    def _generate_audio(
        self,
        text: str,
        index: int,
        content_type: str = None,
        language: str = 'ko') -> str:
        """TTS로 음성 생성 (콘텐츠 타입별 voice/speed 최적화)"""
        audio_path = os.path.join(config.TEMP_DIR, f"audio_{index}.mp3")

        # 언어 코드 설정
        lang_code = 'en' if language == 'en' else 'ko'
        
        # 새로운 TTS 엔진 사용 (우선, 콘텐츠 타입별 최적화)
        if self.tts_engine:
            try:
                if self.tts_engine.generate(text, audio_path, lang=lang_code, content_type=content_type):
                    return audio_path
                else:
                    print(f"⚠️ TTS 엔진 음성 생성 실패, 기본 gTTS 시도")
            except Exception as e:
                print(f"⚠️ TTS 엔진 오류: {e}, 기본 gTTS 시도")
        
        # 기본 gTTS 사용 (폴백)
        if TTS_AVAILABLE:
            try:
                tts = gTTS(text=text, lang=lang_code, slow=False)
                tts.save(audio_path)
                return audio_path
            except Exception as e:
                print(f"⚠️ gTTS 음성 생성 실패 ({text[:20]}...): {e}")
                return None
        else:
            print(f"⚠️ 사용 가능한 TTS 엔진이 없습니다.")
            return None
    
    def _draw_text_on_image(
        self,
        image: Image.Image,
        text: str,
        language: str = 'ko') -> Image.Image:
        """이미지에 텍스트 그리기 (한글/영어 폰트 지원, 여러 줄 자동 분할)"""
        # 폰트 시도 (초기 크기)
        base_font_size = VideoConstants.BASE_FONT_SIZE
        font = None
        font_path_used = None
        
        # macOS 폰트 경로 (언어에 따라)
        font_paths = []
        if language == 'en':
            # 영어 폰트 경로
            font_paths = [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Supplemental/Helvetica.ttc",
            ]
        else:
            # 한글 폰트 경로
            font_paths = [
            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",  # 애플고딕
            "/System/Library/Fonts/AppleGothic.ttf",
                # 나눔고딕 (설치된 경우)
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
            # 기본 폰트 시도 (언어에 따라)
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
        
        # 이미지를 RGB로 변환 (텍스트 그리기 전)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 텍스트를 여러 줄로 분할 (최대 너비 고려)
        max_width = VideoConstants.SUBTITLE_MAX_WIDTH
        lines = self._wrap_text(text, font, max_width, base_font_size)
        
        # 폰트 크기 자동 조정 (텍스트가 너무 길면)
        if len(lines) > 3 and font_path_used:
            # 텍스트가 너무 많으면 폰트 크기 줄이기
            for size in VideoConstants.FONT_SIZES:
                try:
                    font = ImageFont.truetype(font_path_used, size)
                    lines = self._wrap_text(text, font, max_width, size)
                    if len(lines) <= 4:
                        break
                except BaseException:
                    continue
        
        line_spacing = VideoConstants.LINE_SPACING
        # 텍스트 크기 계산
        draw = ImageDraw.Draw(image)
        line_heights = []
        line_widths = []
        
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_heights.append(bbox[3] - bbox[1])
            line_widths.append(bbox[2] - bbox[0])
        
        total_height = sum(line_heights) + \
        (len(lines) - 1) * line_spacing  # 줄 간격
        max_line_width = max(line_widths) if line_widths else 0
        
        # 텍스트 위치 (중앙, 아래쪽)
        x = (VideoConstants.VIDEO_WIDTH - max_line_width) // 2
        y = VideoConstants.VIDEO_HEIGHT - total_height - VideoConstants.SUBTITLE_BOTTOM_MARGIN
        
        # 텍스트 배경 박스 제거 (사용자 요청: 배경 박스가 눈에 보이지 않도록)
        # 배경 박스 없이 그림자 효과만 사용하여 가독성 유지
        # 이미지를 RGB 모드로 유지 (배경 박스 없음)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        draw = ImageDraw.Draw(image)
        
        # 여러 줄 텍스트 그리기
        current_y = y
        for i, line in enumerate(lines):
            if not line.strip():  # 빈 줄 건너뛰기
                continue
                
            line_bbox = draw.textbbox((0, 0), line, font=font)
            line_width = line_bbox[2] - line_bbox[0]
            line_x = (VideoConstants.VIDEO_WIDTH - line_width) // 2  # 각 줄도 중앙 정렬
            
            # 텍스트 그림자 효과 (가독성 향상) - 더 진하게
            draw.text((line_x + 4, current_y + 4),
                      line, fill=(0, 0, 0), font=font)
            draw.text((line_x + 2, current_y + 2), line,
                      fill=(50, 50, 50), font=font)
            # 메인 텍스트 - 밝은 흰색
            draw.text(
                (line_x, current_y), line, fill=(
        255, 255, 255), font=font)

            current_y += line_heights[i] + line_spacing  # 줄 간격
        
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
        
        # 폰트로 텍스트 크기 측정
        temp_image = Image.new('RGB', (VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT))
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
    
    def _create_gradient_background(
        self, index: int, total: int) -> Image.Image:
        """그라데이션 배경 이미지 생성 + 시각적 요소 추가"""
        width, height = VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT
        
        # 색상 팔레트
        colors = [
            [(255, 107, 107), (255, 159, 64)],  # 빨강-주황
            [(74, 144, 226), (80, 227, 194)],   # 파랑-청록
            [(255, 206, 84), (255, 159, 64)],   # 노랑-주황
            [(156, 136, 255), (220, 138, 221)],  # 보라-핑크
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
            small_x = center_x + \
                int(radius_offset * (1 if i % 2 == 0 else 0.8) * (1 if i < 3 else -1))
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
            keywords = self.media_downloader.extract_keywords(topic)
            keyword = keywords[0] if keywords else "nature"
            
            # 영어 키워드로 변환
            english_keyword = self.media_downloader.translate_keyword_to_english(keyword)
            
            print(f"🖼️  주제 이미지 다운로드 시도: {topic} -> {english_keyword}")
            
            # Pexels 또는 Lorem Picsum 사용
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' }
            
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
            
            # 해상도에 맞게 리사이즈 및 크롭
            img = self.media_downloader.resize_and_crop(img, VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT)
            
            print(f"✅ 주제 이미지 다운로드 성공: {english_keyword}")
            return img
            
        except Exception as e:
            print(f"⚠️  주제 이미지 다운로드 실패 ({topic}): {e}")
            return None
    
    def _download_image_for_sentence(
        self,
        sentence: str,
        index: int,
        topic: str = None) -> Image.Image:
        """문장에 맞는 이미지 다운로드 (주제 관련 이미지 우선, 키워드 기반, Pexels와 Unsplash 번갈아 사용)"""
        try:
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

            # 문장에서 키워드 추출 (보조 사용, 주제와 관련된 경우만)
            sentence_keywords = self.media_downloader.extract_keywords(sentence)
            sentence_keyword = sentence_keywords[0] if sentence_keywords else None

            # 주제 키워드를 우선 사용, 없으면 문장 키워드 사용
            if topic_keyword:
                keyword = topic_keyword
                english_keyword = self.media_downloader.translate_keyword_to_english(
                    topic_keyword)
            elif sentence_keyword:
                keyword = sentence_keyword
                english_keyword = self.media_downloader.translate_keyword_to_english(
                    sentence_keyword)
            else:
                # 키워드가 없으면 주제를 직접 사용
                if topic:
                    keyword = topic
                    english_keyword = self.media_downloader.translate_keyword_to_english(topic)
                else:
                    keyword = "nature"
                    english_keyword = "nature"
            
            print(f"🖼️  이미지 다운로드 시도: {keyword} -> {english_keyword}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' }

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
                    img = self.media_downloader.try_pexels_api(english_keyword, headers)
                    if img:
                                return img
                    # 실패하면 Unsplash 시도
                    img = self.media_downloader.try_unsplash_api(english_keyword, headers)
                    if img:
                        return img
                else:
                    # Unsplash 먼저 시도
                    img = self.media_downloader.try_unsplash_api(english_keyword, headers)
                    if img:
                        return img
                    # 실패하면 Pexels 시도
                    img = self.media_downloader.try_pexels_api(english_keyword, headers)
                    if img:
                        return img
            elif has_pexels:
                # Pexels만 사용
                img = self.media_downloader.try_pexels_api(english_keyword, headers)
                if img:
                    return img
            elif has_unsplash:
                # Unsplash만 사용
                img = self.media_downloader.try_unsplash_api(english_keyword, headers)
                if img:
                    return img

            # 방법 3: Pixabay API 사용 (무료, 공개 API 키, 폴백)
            try:
                pixabay_api_key = "9656065-a4094594c34c9ac8a7e8c5c4e"  # 공개 데모 키
                pixabay_url = f"https://pixabay.com/api/?key={pixabay_api_key}&q={english_keyword}&image_type=photo&orientation=vertical&safesearch=true&per_page=3"
                
                response = requests.get(
                    pixabay_url, timeout=10, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('hits') and len(data['hits']) > 0:
                        image_url = data['hits'][0]['webformatURL']
                        image_url = image_url.replace('_640', '_1280')
                        
                        img_response = requests.get(
                            image_url, timeout=10, headers=headers)
                        if img_response.status_code == 200:
                            from io import BytesIO
                            img = Image.open(BytesIO(img_response.content))
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            img = self.media_downloader.resize_and_crop(img, VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT)
                            print(f"✅ Pixabay 이미지 다운로드 성공: {english_keyword}")
                            return img
            except Exception as e:
                print(f"   Pixabay API 실패: {e}")
            
            # 방법 2: Unsplash Source API 시도 (키워드 기반, API 키 불필요)
            try:
                unsplash_source_url = f"https://source.unsplash.com/1080x1920/?{english_keyword}"
                response = requests.get(
                    unsplash_source_url,
                    timeout=15,
                    allow_redirects=True,
                    headers=headers)
                if response.status_code == 200 and response.content:
                    content_type = response.headers.get('Content-Type', '')
                    if 'image' in content_type or len(response.content) > 1000:
                        from io import BytesIO
                        img = Image.open(BytesIO(response.content))
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        img = self.media_downloader.resize_and_crop(img, VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT)
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
            img = self.media_downloader.resize_and_crop(img, VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT)
            
            print(f"⚠️  랜덤 이미지 사용 (키워드: {english_keyword})")
            return img
            
        except Exception as e:
            print(f"⚠️  이미지 다운로드 실패 ({sentence[:20]}...): {e}")
            return None
    
    # _resize_and_crop, _extract_keywords, _translate_keyword_to_english 메서드는 
    # MediaDownloader 클래스로 이동되었으므로 제거됨
    
    def _download_video_for_sentence(
        self,
        sentence: str,
        index: int,
        duration: float,
        topic: str = None,
        exclude_videos: list = None) -> str:
        """
        문장에 맞는 배경 영상 다운로드 (Pexels Video API 사용, CC0 라이선스)
        주제와 관련된 배경만 선택, 중복 방지
        
        Args:
            sentence: 문장
            index: 인덱스
            duration: 필요한 영상 길이 (초)
            topic: 영상 주제 (주제 관련 배경 선택을 위해 필수)
            exclude_videos: 제외할 영상 경로 리스트 (중복 방지)
        
        Returns:
            다운로드된 영상 파일 경로 또는 None
        """
        try:
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

            # 문장에서 키워드 추출 (보조 사용, 주제와 관련된 경우만)
            sentence_keywords = self.media_downloader.extract_keywords(sentence)
            sentence_keyword = sentence_keywords[0] if sentence_keywords else None

            # 우선순위 변경: 문장 키워드 > 주제 키워드
            # 문장별로 다양한 배경을 보여주기 위함
            
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
            
            # Pexels Video API 사용 (CC0 라이선스)
            if config.PEXELS_API_KEY:
                try:
                    # 주제와 관련된 영상만 검색 (주제 키워드 우선 사용)
                    pexels_video_url = f"https://api.pexels.com/videos/search?query={english_keyword}&per_page=20&orientation=portrait"
                    pexels_headers = {
                        **headers,
                        'Authorization': config.PEXELS_API_KEY
                    }
                    
                    # Use retry-wrapped HTTP GET
                    response = self._http_get_with_retry(
                        pexels_video_url, headers=pexels_headers)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('videos') and len(data['videos']) > 0:
                            # 이미 다운로드한 영상 ID 추출 (중복 방지)
                            downloaded_video_ids = set()
                            if exclude_videos:
                                for existing_path in exclude_videos:
                                    if os.path.exists(existing_path):
                                        # 파일명에서 영상 ID 추출
                                        # (bg_video_{index}_{video_id}.mp4 형식)
                                        import re
                                        match = re.search(
                                            r'bg_video_\d+_(\d+)\.mp4', existing_path)
                                        if match:
                                            downloaded_video_ids.add(
                                                int(match.group(1)))

                            # 주제와 관련된 영상 우선 선택 (제목이나 설명에 키워드가 포함된 것, 중복 제외)
                            # 더 긴 영상을 우선 선택 (최소 20초 이상)
                            video_data = None
                            candidate_videos = []

                            for video in data['videos']:
                                video_id = video.get('id', 0)
                                # 이미 다운로드한 영상은 건너뛰기
                                if video_id in downloaded_video_ids:
                                    continue

                                video_text = f"{video.get('url', '')} {video.get('user', {}).get('name', '')} {video.get('id', '')}".lower(
                                )
                                video_duration = video.get('duration', 0)

                                # 주제 키워드가 포함된 영상 우선 선택
                                is_relevant = english_keyword.lower() in video_text or any(
                                    word in video_text for word in english_keyword.lower().split())

                                # 후보 영상 추가 (관련성과 길이를 고려)
                                candidate_videos.append({
                                    'video': video,
                                    'is_relevant': is_relevant,
                                    'duration': video_duration
                                })

                            # 후보 영상 정렬: 관련성 우선, 그 다음 길이 (긴 것 우선)
                            candidate_videos.sort(key=lambda x: (
                                not x['is_relevant'], -x['duration']))

                            # 최소 20초 이상인 영상 우선 선택
                            for candidate in candidate_videos:
                                if candidate['duration'] >= 20.0:
                                    video_data = candidate['video']
                                    break

                            # 20초 이상이 없으면 가장 긴 영상 선택
                            if not video_data and candidate_videos:
                                video_data = candidate_videos[0]['video']

                            # 관련 영상이 없으면 중복되지 않은 첫 번째 영상 사용
                            if not video_data:
                                for video in data['videos']:
                                    video_id = video.get('id', 0)
                                    if video_id not in downloaded_video_ids:
                                        video_data = video
                                        break

                            # 모든 영상이 중복이면 None 반환
                            if not video_data:
                                print(f"   ⚠️ 모든 영상이 이미 다운로드됨, 이미지로 대체")
                                return None
                            
                            # 세로형 영상 파일 찾기 (1080p 이상 우선, 해상도 및 품질 체크 강화)
                            video_files = video_data.get('video_files', [])
                            video_url = None
                            best_quality = 0
                            
                            # 우선순위: 1080p > 720p > 540p > 480p (해상도와 파일 크기 고려)
                            for vf in video_files:
                                width = vf.get('width', 0)
                                height = vf.get('height', 0)
                                file_size = vf.get('file_type', '')  # 파일 타입으로 품질 추정
                                
                                # 세로형 영상만 선택 (height >= width)
                                if height >= width and height >= VideoConstants.MIN_VIDEO_HEIGHT:
                                    # 해상도 점수 계산 (width * height)
                                    quality_score = width * height
                                    
                                    # 선호 해상도 이상 우선 선택
                                    if height >= VideoConstants.PREFERRED_VIDEO_HEIGHT and quality_score > best_quality:
                                        video_url = vf.get('link')
                                        best_quality = quality_score
                                    # 1080p가 없으면 720p 선택
                                    elif not video_url and height >= 720 and quality_score > best_quality:
                                        video_url = vf.get('link')
                                        best_quality = quality_score
                                    # 720p도 없으면 540p 선택
                                    elif not video_url and height >= 540 and quality_score > best_quality:
                                        video_url = vf.get('link')
                                        best_quality = quality_score
                                    # 540p도 없으면 480p 선택
                                    elif not video_url and height >= 480 and quality_score > best_quality:
                                        video_url = vf.get('link')
                                        best_quality = quality_score
                            
                            # 영상 URL이 없으면 세로형 영상 중 첫 번째 사용
                            if not video_url and video_files:
                                for vf in video_files:
                                    height = vf.get('height', 0)
                                    width = vf.get('width', 0)
                                    if height >= width:  # 세로형만
                                        video_url = vf.get('link')
                                        break
                            
                            if video_url:
                                # 영상 ID 가져오기 (중복 방지용)
                                video_id = video_data.get('id', index)

                                # 영상 다운로드 (with retry)
                                video_response = self._http_get_with_retry(
                                    video_url, headers=headers, stream=True)
                                if video_response.status_code == 200:
                                    video_path = os.path.join(
                                        config.TEMP_DIR, f"bg_video_{index}_{video_id}.mp4")
                                    
                                    with open(video_path, 'wb') as f:
                                        for chunk in video_response.iter_content(
                                                chunk_size=8192):
                                            f.write(chunk)
                                    
                                    # 영상 길이 확인 (원본만 저장, 루프 처리는 나중에)
                                    try:
                                        video_clip = VideoFileClip(video_path)
                                        video_duration = video_clip.duration

                                        # 다운로드한 원본 영상 분석 (반복 여부, 색상/밝기 확인)
                                        print(f"📹 다운로드한 영상 분석: {video_path}")
                                        print(
                                            f"   원본 길이: {video_duration:.2f}초")

                                        # 원본 영상이 반복되어 있는지 확인 및 색상/밝기 분석
                                        if video_duration > 2.0:
                                            try:
                                                import numpy as np
                                                # 시작, 중간, 끝 지점 비교
                                                start_frame = video_clip.get_frame(
                                                    0.5)
                                                mid_frame = video_clip.get_frame(
                                                    video_duration / 2)
                                                end_frame = video_clip.get_frame(
                                                    video_duration - 0.5)

                                                # 영상 크기에 맞게 중앙 픽셀 접근
                                                h, w = start_frame.shape[:2]
                                                center_y, center_x = h // 2, w // 2

                                                start_rgb = start_frame[center_y, center_x] if len(
                                                    start_frame.shape) == 3 else [0, 0, 0]
                                                mid_rgb = mid_frame[center_y, center_x] if len(
                                                    mid_frame.shape) == 3 else [0, 0, 0]
                                                end_rgb = end_frame[center_y, center_x] if len(
                                                    end_frame.shape) == 3 else [0, 0, 0]

                                                start_mid_diff = np.abs(
                                                    start_rgb - mid_rgb).sum()
                                                start_end_diff = np.abs(
                                                    start_rgb - end_rgb).sum()

                                                print(
                                                    f"   시작-중간 차이: {start_mid_diff}, 시작-끝 차이: {start_end_diff}")
                                                if start_mid_diff < VideoConstants.FRAME_CHECK_THRESHOLD or start_end_diff < VideoConstants.FRAME_CHECK_THRESHOLD:
                                                    print(
                                                        f"   ⚠️ 원본 영상이 반복되어 있을 가능성이 있습니다!")
                                                
                                                # 색상/밝기 분석 (자막 가독성을 위한 분석)
                                                # 중간 프레임의 평균 밝기 계산
                                                if len(mid_frame.shape) == 3:
                                                    # RGB를 그레이스케일로 변환 (밝기 계산)
                                                    gray_mid = np.dot(mid_frame[...,:3], [0.299, 0.587, 0.114])
                                                    avg_brightness = np.mean(gray_mid)
                                                    
                                                    # 대비 계산 (표준편차)
                                                    contrast = np.std(gray_mid)
                                                    
                                                    # 색상 채도 계산 (RGB 표준편차)
                                                    color_saturation = np.std(mid_frame[...,:3], axis=2).mean()
                                                    
                                                    print(f"   📊 영상 품질 분석: 밝기={avg_brightness:.1f}/255, 대비={contrast:.1f}, 채도={color_saturation:.1f}")
                                                    
                                                    # 너무 어둡거나 밝은 영상 경고 (자막 가독성 고려)
                                                    if avg_brightness < VideoConstants.MIN_BRIGHTNESS:
                                                        print(f"   ⚠️ 영상이 너무 어둡습니다 (밝기: {avg_brightness:.1f}), 자막 가독성에 영향 가능")
                                                    elif avg_brightness > VideoConstants.MAX_BRIGHTNESS:
                                                        print(f"   ⚠️ 영상이 너무 밝습니다 (밝기: {avg_brightness:.1f}), 자막 가독성에 영향 가능")
                                                    
                                                    # 대비가 낮으면 경고 (자막 가독성 저하)
                                                    if contrast < VideoConstants.MIN_CONTRAST:
                                                        print(f"   ⚠️ 영상 대비가 낮습니다 (대비: {contrast:.1f}), 자막 가독성에 영향 가능")
                                            except Exception as frame_check_error:
                                                # 프레임 확인 실패해도 영상은 사용 (오류 무시)
                                                print(
                                                    f"   프레임 확인 건너뜀: {frame_check_error}")

                                        video_clip.close()
                                        
                                        # 원본 영상만 저장 (루프 처리는 _create_video_from_script에서 수행)
                                        # 영상이 너무 짧으면 다른 영상 시도하거나 이미지 사용
                                        if video_duration < VideoConstants.MIN_VIDEO_DURATION:
                                            print(
                                                f"   영상이 너무 짧음 ({video_duration:.1f}초), 이미지로 대체")
                                            if os.path.exists(video_path):
                                                os.remove(video_path)
                                            return None
                                        
                                        print(
                                            f"✅ Pexels 배경 영상 다운로드 성공: {english_keyword} (ID: {video_id}, 원본: {video_duration:.1f}초, 파일: {video_path})")
                                        return video_path
                                    except Exception as e:
                                        print(f"   영상 처리 실패: {e}")
                                        # 영상 처리 실패 시에도 파일은 유지 (다른 용도로 사용 가능)
                                        # 너무 짧거나 문제가 있는 경우에만 삭제
                                        try:
                                            video_clip_check = VideoFileClip(
                                                video_path)
                                            if video_clip_check.duration < VideoConstants.MIN_VIDEO_DURATION:
                                                video_clip_check.close()
                                                if os.path.exists(video_path):
                                                    os.remove(video_path)
                                            else:
                                                video_clip_check.close()
                                        except BaseException:
                                            # 확인 불가능한 경우에만 삭제
                                            if os.path.exists(video_path):
                                                os.remove(video_path)
                except Exception as e:
                    print(f"   Pexels Video API 실패: {e}")
            
            # Pexels Video API 실패 시 이미지 사용 (기존 로직)
            return None
            
        except Exception as e:
            print(f"⚠️ 배경 영상 다운로드 실패 ({sentence[:20]}...): {e}")
            return None
    
    def _select_music_category_for_content_type(self, content_type: ContentType) -> str:
        """
        콘텐츠 타입에 맞는 음악 카테고리 선택
        
        Args:
            content_type: 콘텐츠 타입
        
        Returns:
            Pixabay Music 카테고리 키워드
        """
        # 콘텐츠 타입별 음악 카테고리 매핑
        music_categories = {
            ContentType.HOOK: ['energetic', 'upbeat', 'motivational'],  # 에너지 넘치는, 업비트
            ContentType.QUOTE: ['calm', 'peaceful', 'inspirational'],  # 차분한, 평화로운
            ContentType.STORY: ['emotional', 'cinematic', 'dramatic'],  # 감성적인, 영화적
            ContentType.FACT: ['corporate', 'modern', 'tech'],  # 기업적, 모던
            ContentType.SHORT_STORY: ['ambient', 'soft', 'gentle'],  # 앰비언트, 부드러운
            ContentType.MEDITATION: ['meditation', 'zen', 'calm'],  # 명상, 차분한
            ContentType.BREATHING: ['ambient', 'peaceful', 'nature'],  # 자연, 평화로운
            ContentType.AUTO: ['background', 'ambient', 'soft'],  # 기본 배경 음악
        }
        
        categories = music_categories.get(content_type, ['background', 'ambient'])
        return random.choice(categories)
    
    def _download_background_music(
        self,
        content_type: ContentType,
        duration: float,
        topic: str = None
    ) -> Optional[str]:
        """
        배경 음악 다운로드 (무료 음악 라이브러리 사용)
        
        Args:
            content_type: 콘텐츠 타입
            duration: 필요한 음악 길이 (초)
            topic: 영상 주제 (선택)
        
        Returns:
            다운로드된 음악 파일 경로 또는 None
        """
        if not getattr(config, 'USE_BACKGROUND_MUSIC', True):
            return None
        
        try:
            # 콘텐츠 타입에 맞는 음악 카테고리 선택
            music_category = self._select_music_category_for_content_type(content_type)
            print(f"🎵 배경 음악 선택: {music_category} (콘텐츠 타입: {content_type.value})")
            
            # 방법 1: 로컬 음악 라이브러리 확인 (우선)
            music_library_dir = os.path.join(BASE_DIR, 'data', 'music')
            if os.path.exists(music_library_dir):
                # 카테고리별 음악 파일 찾기
                music_files = []
                for ext in ['.mp3', '.wav', '.m4a', '.ogg']:
                    # 카테고리 이름이 포함된 파일 찾기
                    for file in os.listdir(music_library_dir):
                        if file.endswith(ext) and music_category.lower() in file.lower():
                            music_files.append(os.path.join(music_library_dir, file))
                
                # 카테고리 매칭이 없으면 모든 음악 파일에서 랜덤 선택
                if not music_files:
                    for ext in ['.mp3', '.wav', '.m4a', '.ogg']:
                        music_files.extend([
                            os.path.join(music_library_dir, f) 
                            for f in os.listdir(music_library_dir) 
                            if f.endswith(ext)
                        ])
                
                if music_files:
                    selected_music = random.choice(music_files)
                    print(f"✅ 로컬 음악 라이브러리에서 선택: {os.path.basename(selected_music)}")
                    return selected_music
            
            # 방법 2: Freesound.org API 사용 (API 키가 있는 경우)
            freesound_api_key = os.getenv('FREESOUND_API_KEY')
            if freesound_api_key:
                try:
                    # Freesound API로 음악 검색 및 다운로드
                    freesound_url = f"https://freesound.org/apiv2/search/text/?query={music_category}&filter=duration:[{duration-5}:{duration+10}]&fields=id,name,previews&token={freesound_api_key}"
                    response = self._http_get_with_retry(freesound_url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('results') and len(data['results']) > 0:
                            # 첫 번째 결과 선택
                            sound = data['results'][0]
                            preview_url = sound.get('previews', {}).get('preview-hq-mp3')
                            if preview_url:
                                # 음악 다운로드
                                music_path = os.path.join(
                                    config.TEMP_DIR, 
                                    f"bg_music_{int(time.time()*1000)}.mp3"
                                )
                                music_response = self._http_get_with_retry(preview_url, timeout=15)
                                if music_response.status_code == 200:
                                    with open(music_path, 'wb') as f:
                                        f.write(music_response.content)
                                    print(f"✅ Freesound에서 배경 음악 다운로드: {sound.get('name', 'Unknown')}")
                                    return music_path
                except Exception as e:
                    print(f"   Freesound API 실패: {e}")
            
            # 방법 3: YouTube Audio Library 스타일의 무료 음악 (로컬 파일)
            # 사용자가 YouTube Audio Library에서 다운로드한 음악을 data/music/ 폴더에 저장하면 자동으로 사용됨
            print(f"⚠️ 배경 음악을 찾을 수 없습니다. 로컬 음악 라이브러리(data/music/)에 음악 파일을 추가하거나 Freesound API 키를 설정하세요.")
            return None
            
        except Exception as e:
            print(f"⚠️ 배경 음악 다운로드 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_thumbnail_with_dalle3(self,
                                        title: str,
                                        topic: str = None,
                                        script: list = None,
                                        language: str = 'ko') -> Optional[Image.Image]:
        """
        DALL-E 3로 썸네일 이미지 생성

        Args:
            title: 영상 제목
            topic: 영상 주제 (선택)
            script: 영상 스크립트 (선택)
            language: 언어 코드 ('ko' 또는 'en', 기본값: 'ko')

        Returns:
            PIL Image 객체 또는 None (실패 시)
        """
        if not self.openai_client:
            return None

        try:
            # 주제 기반 프롬프트 생성
            # 주제 및 제목 분석하여 스타일 결정
            style_prompt = ""
            lower_topic = (topic or "").lower()
            lower_title = title.lower()
            
            if any(k in lower_topic or k in lower_title for k in ['money', 'finance', 'rich', 'wealth', 'invest', '돈', '부자', '투자', '금융']):
                style_prompt = "Style: Hyper-realistic 3D render, luxury aesthetic, gold and neon green accents, rising graphs, high contrast, dramatic lighting. Visuals of wealth, success, currency, or gold."
            elif any(k in lower_topic or k in lower_title for k in ['motivation', 'mindset', 'life', 'success', 'dream', '동기부여', '성공', '인생', '꿈']):
                style_prompt = "Style: Cinematic lighting, dramatic silhouette against a sunrise or sunset, emotional atmosphere, epic scale, looking up at a mountain or city, inspiring and powerful."
            elif any(k in lower_topic or k in lower_title for k in ['productivity', 'habit', 'study', 'focus', 'time', '생산성', '습관', '공부', '시간']):
                style_prompt = "Style: Clean minimalist setup, futuristic blue and white lighting, glowing brain or clock elements, organized workspace, sharp focus, high-tech feel."
            else:
                style_prompt = "Style: High contrast, vibrant colors, 4k resolution, unreal engine 5 render style, highly detailed, eye-catching, dramatic composition."

            # 주제 기반 프롬프트 생성 (영어/한국어 공통적으로 영어 프롬프트 사용 권장 - DALL-E 3가 영어를 더 잘 이해함)
            # 하지만 한국어 설정이므로 한국어 뉘앙스를 살리기 위해 혼용하거나 영어로 번역하는 것이 좋음
            # 여기서는 프롬프트 구조를 강화하여 영어로 작성 (DALL-E 3 최적화)
            
            prompt = f"A viral YouTube Shorts thumbnail image for a video titled: '{title}'."
            if topic:
                prompt += f" The video is about: {topic}."
            if script and len(script) > 0:
                prompt += f" Key scene context: {script[0][:100]}."
            
            prompt += f"\n\n{style_prompt}"
            prompt += "\n\nIMPORTANT CONSTRAINTS:"
            prompt += "\n- Vertical format (9:16 aspect ratio)"
            prompt += "\n- Central composition, close-up or medium shot"
            prompt += "\n- ABSOLUTELY NO TEXT, NO LETTERS, NO NUMBERS, NO WATERMARKS in the image. The image must be text-free."
            prompt += "\n- Make it emotionally engaging and click-worthy."

            print(f"🎨 DALL-E 3로 썸네일 이미지 생성 중...")
            print(f"   프롬프트: {prompt[:100]}...")

            # DALL-E 3 API 호출 (with retry)
            response = self._api_call_with_retry(
                self.openai_client.images.generate,
                model="dall-e-3",
                prompt=prompt,
                size="1024x1792",  # 9:16 비율 (YouTube Shorts)
                quality="standard",
                n=1,
            )

            # 생성된 이미지 URL 가져오기
            image_url = response.data[0].url

            # 이미지 다운로드 (with retry)
            import requests
            img_response = self._http_get_with_retry(image_url)
            img_response.raise_for_status()

            # PIL Image로 변환
            from io import BytesIO
            img = Image.open(BytesIO(img_response.content))
            img = img.convert('RGB')

            # 1080x1920으로 리사이즈
            img = img.resize((1080, 1920), Image.Resampling.LANCZOS)

            print(f"✅ DALL-E 3 썸네일 이미지 생성 완료")
            return img

        except Exception as e:
            print(f"⚠️ DALL-E 3 썸네일 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_thumbnail(
        self,
        video_path: str,
        title: str,
        topic: str = None,
        script: list = None,
        language: str = 'ko') -> str:
        """
        매력적인 썸네일 이미지 생성
        
        Args:
            video_path: 영상 파일 경로
            title: 영상 제목
            topic: 영상 주제 (선택)
            script: 영상 스크립트 (선택, 핵심 내용 추출용)
            language: 언어 코드 ('ko' 또는 'en', 기본값: 'ko')
        """
        import datetime
        import numpy as np
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        thumbnail_path = os.path.join(
            config.THUMBNAIL_OUTPUT_DIR,
            f"thumb_{timestamp}.jpg")

        # DALL-E 3로 썸네일 이미지 생성 시도 (OpenAI API 사용)
        dalle_img = self._generate_thumbnail_with_dalle3(
            title, topic, script, language=language)

        if dalle_img:
            # DALL-E 3로 생성된 이미지 사용
            img = dalle_img
        else:
            # DALL-E 3 실패 시 기존 방식 (영상 프레임에서 추출)
            print(f"📹 영상 프레임에서 썸네일 추출 중...")
        # 영상에서 여러 프레임 중 가장 좋은 프레임 선택 (중간 부분)
            # 자막이 없는 원본 배경을 사용하기 위해 영상에서 프레임 추출 후 자막 영역 제거
        video = VideoFileClip(video_path)
        duration = video.duration
        # 영상의 중간 지점에서 프레임 추출 (일반적으로 가장 매력적인 부분)
        frame_time = duration * VideoConstants.THUMBNAIL_FRAME_RATIO
        frame = video.get_frame(frame_time)
        video.close()
        
        # PIL 이미지로 변환
        img = Image.fromarray(frame.astype('uint8'), 'RGB')

        # 자막 영역 제거 (하단 중앙 부분 블러 처리 또는 제거)
        # 자막은 보통 하단 중앙에 위치하므로, 해당 영역을 블러 처리하여 제거
        from PIL import ImageFilter
        width, height = img.size
        # 하단 영역을 블러 처리 (자막 제거)
        bottom_region = img.crop((0, int(height * VideoConstants.THUMBNAIL_BOTTOM_REGION), width, height))
        blurred_bottom = bottom_region.filter(
            ImageFilter.GaussianBlur(radius=VideoConstants.THUMBNAIL_BLUR_RADIUS))
        img.paste(blurred_bottom, (0, int(height * VideoConstants.THUMBNAIL_BOTTOM_REGION)))
        
        # 이미지 크기 확인 및 조정
        if img.size != (VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT):
            img = img.resize((VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT), Image.Resampling.LANCZOS)
        
        # 매력적인 제목/내용 생성 (AI 활용)
        attractive_texts = self._generate_attractive_thumbnail_text(
            title, topic, script, language=language)
        
        # 언어에 따른 폰트 로드
        font_large = None
        font_medium = None
        if language == 'en':
            # 영어 폰트 경로
            font_paths = [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Supplemental/Helvetica.ttc",
                "/Library/Fonts/Arial.ttf",
            ]
        else:
            # 한글 폰트 경로
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
            except BaseException:
                continue
        
        if font_large is None:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
        
        draw = ImageDraw.Draw(img)
        
        # 1. 상단에 "SHORTS" 배지 추가 (왼쪽)
        badge_text = "SHORTS"
        badge_font = font_medium
        badge_bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
        badge_width = badge_bbox[2] - badge_bbox[0]
        badge_height = badge_bbox[3] - badge_bbox[1]
        badge_x = 50
        badge_y = 50
        badge_padding = 15
        
        # 배지 배경 (빨간색 그라데이션 효과)
        badge_bg = Image.new(
            'RGBA',
            (badge_width +
     badge_padding *
     2,
     badge_height +
     badge_padding *
     2),
            (255,
     0,
     0,
     230))
        img.paste(
            badge_bg,
            (badge_x -
     badge_padding,
     badge_y -
     badge_padding),
            badge_bg)
        draw.text(
            (badge_x, badge_y), badge_text, fill=(
        255, 255, 255), font=badge_font)
        
        # 1-2. 상단에 "SUBSCRIBE" 배지 추가 (오른쪽) - 구독 유도
        subscribe_text = "SUBSCRIBE" if language == 'en' else "구독하기"
        subscribe_bbox = draw.textbbox((0, 0), subscribe_text, font=badge_font)
        subscribe_width = subscribe_bbox[2] - subscribe_bbox[0]
        subscribe_height = subscribe_bbox[3] - subscribe_bbox[1]
        subscribe_x = VideoConstants.VIDEO_WIDTH - subscribe_width - badge_padding - 50  # 오른쪽 정렬
        subscribe_y = 50
        
        # Subscribe 배지 배경 (빨간색, SHORTS와 동일한 스타일)
        subscribe_bg = Image.new(
            'RGBA',
            (subscribe_width + badge_padding * 2, subscribe_height + badge_padding * 2),
            (255, 0, 0, 230))
        img.paste(
            subscribe_bg,
            (subscribe_x - badge_padding, subscribe_y - badge_padding),
            subscribe_bg)
        draw.text(
            (subscribe_x, subscribe_y), subscribe_text, fill=(255, 255, 255), font=badge_font)
        
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
        total_text_height = len(main_lines) * main_line_height + (len(sub_lines) *
                                                                  sub_line_height if sub_lines else 0) + (line_spacing if sub_lines else 0) + 40
        
        # 텍스트 위치 (하단 중앙)
        text_y_start = 1920 - total_text_height - 80
        
        # 배경 그라데이션 오버레이 (하단)
        overlay = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # 하단에서 위로 그라데이션 (검은색 반투명)
        for i in range(400):
            alpha = int(180 * (1 - i / 400))
            overlay_draw.rectangle(
                [0, 1920 - 400 + i, 1080, 1920 - 400 + i + 1], fill=(0, 0, 0, alpha))
        
        img = Image.alpha_composite(
            img.convert('RGBA'),
            overlay).convert('RGB')
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
            draw.text(
                (text_x, text_y), line, fill=(
        255, 255, 255), font=font_large)
            
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
                draw.text(
                    (text_x +
     shadow_offset,
     text_y +
     shadow_offset),
                    line,
                    fill=(
        0,
        0,
        0,
        200),
                    font=font_medium)
                
                # 서브 텍스트 (노란색 또는 밝은 색)
                draw.text(
                    (text_x, text_y), line, fill=(
        255, 215, 0), font=font_medium)
                
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
        icon_bg = Image.new(
            'RGBA', (icon_radius * 2, icon_radius * 2), (0, 0, 0, 150))
        icon_draw = ImageDraw.Draw(icon_bg)
        icon_draw.ellipse(
            [0, 0, icon_radius * 2, icon_radius * 2], fill=(255, 215, 0, 200))
        icon_center_x = icon_x + (icon_bbox[2] - icon_bbox[0]) // 2
        icon_center_y = icon_y + (icon_bbox[3] - icon_bbox[1]) // 2
        img.paste(
            icon_bg,
            (icon_center_x -
     icon_radius,
     icon_center_y -
     icon_radius),
            icon_bg)
        draw.text(
            (icon_x, icon_y), icon_text, fill=(
        255, 255, 255), font=font_medium)
        
        # 4. 이미지 저장 (고품질)
        img.save(thumbnail_path, 'JPEG', quality=95, optimize=True)
        
        print(f"✅ 썸네일 생성 완료: {thumbnail_path}")
        return thumbnail_path
    
    def _generate_attractive_thumbnail_text(
        self,
        title: str,
        topic: str = None,
        script: list = None,
        language: str = 'ko') -> tuple:
        """
        썸네일용 매력적인 텍스트 생성 (AI 활용)
        
        Args:
            title: 영상 제목
            topic: 영상 주제 (선택)
            script: 영상 스크립트 (선택)
            language: 언어 코드 ('ko' 또는 'en', 기본값: 'ko')
        
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
                
                if language == 'en':
                    # 영어 프롬프트
                    prompt = f"""Generate attractive thumbnail text for the following video.

Title: {title}
Topic: {topic if topic else 'N/A'}
Key Content: {context if context else 'N/A'}

Requirements:
1. First line: Powerful Hook phrase that grabs attention (max 15 words)
2. Second line: Brief summary or emphasize numbers/facts (max 20 words, optional)

Examples:
- "Don't Miss This!" / "5 Secrets Revealed"
- "Rich People's Habits" / "Just 10 Minutes a Day"
- "One English Sentence" / "Essential Daily Phrases"

Format: First line only or "First line / Second line"
**Important: Write all text in English only. Do not include any Korean text.**
"""
                    system_prompt = "You are an expert YouTube thumbnail text writer. Create powerful and concise phrases that grab people's attention. Write all text in English only."
                else:
                    # 한국어 프롬프트
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
                    system_prompt = "당신은 YouTube 썸네일 텍스트 작성 전문가입니다. 사람들의 호기심을 끄는 강력하고 간결한 문구를 작성하세요."
                
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
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
                
                # 영어로 요청했는데 한글이 포함되어 있으면 경고하고 기본 변환 로직 사용
                if language == 'en':
                    import re
                    korean_chars = len(re.findall(r'[가-힣]', result))
                    if korean_chars > 0:
                        print(f"   ⚠️ AI가 한글로 응답했습니다. 기본 변환 로직 사용: {result}")
                        # 기본 변환 로직으로 넘어감
                        result = None
                    elif "/" in result:
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
                else:
                    # 한국어인 경우 기존 로직
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
        
        if language == 'en':
            # 영어 기본 변환
            import re
            numbers = re.findall(r'\d+', title)
            if numbers:
                attractive_title = f"{numbers[0]} Secrets {title.replace(numbers[0], '').strip()}" if numbers else title

            # 영어 키워드 기반 변환
            title_lower = title.lower()
            if "tip" in title_lower or "trick" in title_lower or "way" in title_lower:
                attractive_title = f"Don't Miss This! {title}"
            elif "secret" in title_lower or "habit" in title_lower:
                attractive_title = f"Rich People's Secret: {title}"
            elif "fact" in title_lower or "truth" in title_lower:
                attractive_title = f"Shocking Truth: {title}"
            elif "sale" in title_lower or "deal" in title_lower:
                attractive_title = f"Best {title}"
        else:
            # 한국어 기본 변환
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

    def _try_pexels_api(
        self,
        english_keyword: str,
        headers: dict) -> Image.Image:
        """Pexels API로 이미지 다운로드 시도 (주제 관련 이미지 우선)"""
        try:
            # 주제와 관련된 키워드만 사용 (북아메리카 키워드 제거)
            primary_keyword = english_keyword
            pexels_url = f"https://api.pexels.com/v1/search?query={primary_keyword}&per_page=5&orientation=portrait"
            pexels_headers = {
                **headers,
                'Authorization': config.PEXELS_API_KEY
            }
            response = requests.get(
                pexels_url, timeout=10, headers=pexels_headers)
            if response.status_code == 200:
                data = response.json()
                if data.get('photos') and len(data['photos']) > 0:
                    # 주제와 관련된 이미지만 선택 (제목이나 설명에 키워드가 포함된 것)
                    selected_photo = None
                    for photo in data['photos']:
                        photo_text = f"{photo.get('alt', '')} {photo.get('photographer', '')}".lower(
                        )
                        # 주제 키워드가 명확히 포함된 이미지만 선택
                        if english_keyword.lower() in photo_text or any(
                            word in photo_text for word in english_keyword.lower().split()):
                            selected_photo = photo
                            break
                    # 관련 이미지가 없으면 None 반환 (이상한 이미지 방지)
                    if not selected_photo:
                        print(f"   ⚠️ 주제 관련 이미지 없음, 이미지 다운로드 건너뜀")
                        return None

                    image_url = selected_photo['src']['large']
                    # 세로형 이미지 우선
                    if 'portrait' in selected_photo['src']:
                        image_url = selected_photo['src']['portrait']

                    img_response = requests.get(
                        image_url, timeout=10, headers=headers)
                    if img_response.status_code == 200:
                        from io import BytesIO
                        img = Image.open(BytesIO(img_response.content))
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        img = self.media_downloader.resize_and_crop(img, VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT)
                        print(f"✅ Pexels 이미지 다운로드 성공: {english_keyword}")
                        return img
        except Exception as e:
            print(f"   Pexels API 실패: {e}")
        return None

    def _try_unsplash_api(
        self,
        english_keyword: str,
        headers: dict) -> Image.Image:
        """Unsplash API로 이미지 다운로드 시도 (주제 관련 이미지 우선)"""
        try:
            # 주제와 관련된 키워드만 사용 (북아메리카 키워드 제거)
            primary_keyword = english_keyword
            unsplash_url = f"https://api.unsplash.com/search/photos?query={primary_keyword}&orientation=portrait&per_page=5"
            unsplash_headers = {
                **headers,
                'Authorization': f'Client-ID {config.UNSPLASH_ACCESS_KEY}'
            }
            response = requests.get(
                unsplash_url, timeout=10, headers=unsplash_headers)
            if response.status_code == 200:
                data = response.json()
                if data.get('results') and len(data['results']) > 0:
                    # 주제와 관련된 이미지만 선택 (제목이나 설명에 키워드가 포함된 것)
                    selected_photo = None
                    for photo in data['results']:
                        photo_text = f"{photo.get('description', '')} {photo.get('alt_description', '')} {photo.get('user', {}).get('name', '')}".lower(
                        )
                        # 주제 키워드가 명확히 포함된 이미지만 선택
                        if english_keyword.lower() in photo_text or any(
                            word in photo_text for word in english_keyword.lower().split()):
                            selected_photo = photo
                            break
                    # 관련 이미지가 없으면 None 반환 (이상한 이미지 방지)
                    if not selected_photo:
                        print(f"   ⚠️ 주제 관련 이미지 없음, 이미지 다운로드 건너뜀")
                        return None

                    image_url = selected_photo['urls']['regular']

                    img_response = requests.get(
                        image_url, timeout=10, headers=headers)
                    if img_response.status_code == 200:
                        from io import BytesIO
                        img = Image.open(BytesIO(img_response.content))
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        img = self.media_downloader.resize_and_crop(img, VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT)
                        print(f"✅ Unsplash 이미지 다운로드 성공: {english_keyword}")
                        return img
        except Exception as e:
            print(f"   Unsplash API 실패: {e}")
        return None

    def _extract_key_words_for_subtitle(
        self, sentence: str, language: str = 'ko') -> str:
        """문장에서 자막용 핵심 단어 추출 (1-3개 단어)"""
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
                # 설명이나 추가 텍스트 제거 (단어만 추출)
                key_words = re.sub(r'[^\w\s]', '', key_words)
                words = key_words.split()
                # 최대 3개 단어만
                key_words = ' '.join(words[:3])
                if key_words:
                    print(f"   핵심 단어 추출: {sentence[:30]}... -> {key_words}")
                    return key_words
        except Exception as e:
            print(f"   핵심 단어 추출 실패, 기본 사용: {e}")

        # AI 실패 시 간단한 규칙 기반 추출
        words = sentence.split()
        # 명사, 동사, 형용사 위주로 선택 (간단한 규칙)
        if language == 'en':
            # 영어: 첫 2-3개 단어 또는 중요한 단어 선택
            if len(words) <= 3:
                return sentence
            else:
                # 첫 단어 + 마지막 단어 또는 중요한 단어들
                return ' '.join(
                    [words[0], words[-1] if len(words) > 1 else ''])
        else:
            # 한국어: 첫 2-3개 단어
            if len(words) <= 3:
                return sentence
            else:
                return ' '.join(words[:2])

    def _create_subtitle_clip(
        self,
        text: str,
        duration: float,
        language: str = 'ko') -> TextClip:
        """자막 클립 생성 (배경 영상용) - 핵심 단어 또는 전체 문장 표시"""
        try:
            # 자막 모드에 따라 핵심 단어 또는 전체 문장 사용
            subtitle_text = text
            subtitle_mode = getattr(config, "SUBTITLE_MODE", "full_sentence")
            use_keywords = subtitle_mode != 'full_sentence'
            if use_keywords:
                # 전체 텍스트에서 핵심 단어만 추출
                key_words = self._extract_key_words_for_subtitle(
                    text, language=language)
                if key_words:
                    subtitle_text = key_words
                # 추출 실패 시 원본 사용
            # 폰트 경로 찾기
            font_path = None
            # 전체 문장 모드일 때는 폰트 크기를 조금 줄임 (가독성 향상)
            font_size = 60 if subtitle_mode == 'full_sentence' else 80
            # 모바일 UI에 가리지 않도록 추가 오프셋 (대략 3줄 간격)
            extra_offset = getattr(config, "SUBTITLE_EXTRA_OFFSET", 90)
            
            if language == 'en':
                # 영어 폰트 경로 (macOS)
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
                # 한글 폰트 경로
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
                            subtitle_text,
                            fontsize=font_size,
                            font=font_path,
                            color='white',
                            stroke_color='black',
                            stroke_width=3,  # 더 두꺼운 테두리 (가독성 향상)
                            method='caption',
                            size=(1000, None),
                            align='center'
                        )
                        # 시작 시간을 먼저 명시적으로 0초로 설정 (지연 방지)
                        txt_clip = txt_clip.set_start(0)
                        # duration을 정확히 설정 (음성 길이와 일치)
                        txt_clip = txt_clip.set_duration(duration)
                        # 위치 설정
                        try:
                            frame = txt_clip.get_frame(0)
                            clip_height = frame.shape[0]
                            base_y = 1920 - clip_height - 100
                            raised_y = max(50, base_y - clip_height - extra_offset)
                            txt_clip = txt_clip.set_position(('center', raised_y))
                        except:
                            txt_clip = txt_clip.set_position(('center', 'bottom'))
                        # 시작 시간을 다시 한 번 명시적으로 0으로 설정 (동기화 보장)
                        txt_clip = txt_clip.set_start(0)
                        # duration 재확인 및 설정 (정확성 보장)
                        if abs(txt_clip.duration - duration) > 0.01:
                            txt_clip = txt_clip.set_duration(duration)
                        
                        # 페이드 인/아웃 애니메이션 추가 (더 부드러운 등장/퇴장)
                        fade_duration = min(0.3, duration * 0.1)  # 최대 0.3초, 또는 duration의 10%
                        if duration > fade_duration * 2:
                            txt_clip = txt_clip.fx(fadein, fade_duration).fx(fadeout, fade_duration)
                            # 페이드 후에도 duration 유지
                            txt_clip = txt_clip.set_duration(duration)
                        print(
                            f"   ✅ ImageMagick 자막 생성 성공: duration={txt_clip.duration:.2f}초, start={txt_clip.start:.2f}초 (목표: {duration:.2f}초)")
                        return txt_clip
                    except Exception as e1:
                        print(f"   ImageMagick TextClip 실패, PIL로 대체: {e1}")

                # ImageMagick 실패 시 PIL로 이미지 생성 후 ImageClip 사용
                # PIL로 자막 이미지 생성 (더 큰 크기로)
                from PIL import Image, ImageDraw, ImageFont
                # 자막 영역을 더 크게 (텍스트가 잘리지 않도록)
                subtitle_height = 300
                subtitle_img = Image.new(
                    'RGBA', (1080, subtitle_height), (0, 0, 0, 0))
                draw = ImageDraw.Draw(subtitle_img)

                # 폰트 로드
                pil_font = None
                if font_path and os.path.exists(font_path):
                    try:
                        pil_font = ImageFont.truetype(font_path, font_size)
                    except BaseException:
                        pass

                if pil_font is None:
                    # 기본 폰트 시도 (언어에 따라)
                    if language == 'en':
                        # 영어 폰트 시도
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
                        # 한글 폰트 시도
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

                # 자막 텍스트를 여러 줄로 분할 (너비 고려)
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
                    lines = [key_words]

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

                        # 배경 박스 제거 (사용자 요청: 배경 박스가 눈에 보이지 않도록)
                        # 그림자 효과만 사용하여 가독성 유지
                        draw = ImageDraw.Draw(subtitle_img)

                        # 더 강한 그림자 효과 (가독성 향상)
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
                        
                        # 메인 텍스트 (더 밝은 흰색, 약간의 노란색 틴트)
                        draw.text(
                            (x_pos, y_offset), line, fill=(
        255, 255, 250, 255), font=pil_font)
                        y_offset += text_height + 15
                        total_text_height = y_offset

                # 실제 텍스트가 있는 부분만 크롭
                if total_text_height > 0:
                    subtitle_img = subtitle_img.crop(
                        (0, 0, 1080, min(total_text_height + 20, subtitle_height)))

                # PIL 이미지를 ImageClip으로 변환
                import numpy as np
                # RGBA를 RGB로 변환 (MoviePy 호환성)
                if subtitle_img.mode == 'RGBA':
                    # 알파 채널이 있는 경우 배경과 합성
                    rgb_img = Image.new('RGB', subtitle_img.size, (0, 0, 0))
                    rgb_img.paste(
                        subtitle_img,
                        mask=subtitle_img.split()[3])  # 알파 채널을 마스크로 사용
                    subtitle_img = rgb_img

                subtitle_array = np.array(subtitle_img)
                txt_clip = ImageClip(subtitle_array)
                # 시작 시간을 먼저 명시적으로 0초로 설정 (지연 방지)
                txt_clip = txt_clip.set_start(0)
                # duration을 정확히 설정 (음성 길이와 일치)
                txt_clip = txt_clip.set_duration(duration)
                # 하단 중앙 위치 (실제 높이 고려, 더 명확하게)
                actual_height = subtitle_array.shape[0]
                base_y = max(100, 1920 - actual_height - 150)
                y_pos = max(50, base_y - actual_height - extra_offset)
                txt_clip = txt_clip.set_position(('center', y_pos))
                # 시작 시간을 다시 한 번 명시적으로 0으로 설정 (동기화 보장)
                txt_clip = txt_clip.set_start(0)
                # duration 재확인 및 설정 (정확성 보장)
                if abs(txt_clip.duration - duration) > 0.01:
                    txt_clip = txt_clip.set_duration(duration)
                
                # 페이드 인/아웃 애니메이션 추가 (더 부드러운 등장/퇴장)
                fade_duration = min(0.3, duration * 0.1)  # 최대 0.3초, 또는 duration의 10%
                if duration > fade_duration * 2:
                    txt_clip = txt_clip.fx(fadein, fade_duration).fx(fadeout, fade_duration)
                    # 페이드 후에도 duration 유지
                    txt_clip = txt_clip.set_duration(duration)

                print(
                    f"   ✅ PIL 자막 생성 성공: 높이={actual_height}px, 위치 y={y_pos}, duration={txt_clip.duration:.2f}초, start={txt_clip.start:.2f}초 (목표: {duration:.2f}초)")
                return txt_clip
            except Exception as e:
                print(f"   자막 클립 생성 실패: {e}")
                import traceback
                traceback.print_exc()
                return None
        except Exception as e:
            print(f"   자막 클립 생성 실패: {e}")
            return None

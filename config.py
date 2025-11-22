"""
설정 관리 모듈
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Optional

# 프로젝트 루트 디렉토리 찾기
BASE_DIR = Path(__file__).resolve().parent

# .env 파일 경로 명시적으로 지정
env_path = BASE_DIR / '.env'
try:
    load_dotenv(dotenv_path=env_path)
except PermissionError:
    print("⚠️ .env 파일을 읽을 권한이 없습니다. 파일 권한을 확인하세요.")
    print(f"   경로: {env_path}")


class Settings:
    """애플리케이션 설정 클래스"""
    
    def __init__(self):
        # YouTube API 설정
        self.youtube_client_id = os.getenv('YOUTUBE_CLIENT_ID')
        self.youtube_client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')
        self.youtube_refresh_token = os.getenv('YOUTUBE_REFRESH_TOKEN')
        
        # AI API 설정
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.claude_api_key = os.getenv('CLAUDE_API_KEY')
        self.ai_api_provider = os.getenv('AI_API_PROVIDER', 'openai').lower()
        
        # 이미지/영상 API 설정
        self.pexels_api_key = os.getenv('PEXELS_API_KEY')
        self.unsplash_access_key = os.getenv('UNSPLASH_ACCESS_KEY')
        
        # API Quota Limits
        self.openai_rpm_limit = self._get_int('OPENAI_RPM_LIMIT', 500)
        self.pexels_hourly_limit = self._get_int('PEXELS_HOURLY_LIMIT', 200)
        self.youtube_daily_quota = self._get_int('YOUTUBE_DAILY_QUOTA', 10000)
        
        # Quota Warning Thresholds
        self.quota_warning_threshold = 0.8
        self.quota_critical_threshold = 0.95
        
        # 영상 생성 설정
        self.use_background_video = self._get_bool('USE_BACKGROUND_VIDEO', True)
        self.use_background_music = self._get_bool('USE_BACKGROUND_MUSIC', True)
        self.background_music_volume = self._get_float('BACKGROUND_MUSIC_VOLUME', 0.25)
        
        # 콘텐츠 타입 설정
        self.content_type = os.getenv('CONTENT_TYPE', 'auto')
        self.trend_mode = self._get_bool('TREND_MODE', False)
        self.prefer_short_videos = self._get_bool('PREFER_SHORT_VIDEOS', True)
        
        # 업로드 스케줄 설정
        self.upload_schedule_time = os.getenv('UPLOAD_SCHEDULE_TIME', '09:00')
        self.upload_timezone = os.getenv('UPLOAD_TIMEZONE', 'Asia/Seoul')
        
        # 영상 기본 설정
        self.default_title_prefix = os.getenv('DEFAULT_TITLE_PREFIX', 'Shorts')
        self.default_description = os.getenv('DEFAULT_DESCRIPTION', 
            'AI로 자동 생성된 YouTube Shorts 영상입니다. 유용한 정보와 팁을 매일 공유합니다. 구독과 좋아요 부탁드립니다!')
        self.default_tags = self._get_list('DEFAULT_TAGS', 
            'shorts,쇼츠,ai,인공지능,자동생성,유용한정보,팁,라이프스타일')
        
        # 디렉토리 설정
        self.video_output_dir = 'output/videos'
        self.thumbnail_output_dir = 'output/thumbnails'
        self.temp_dir = 'output/temp'
        
        # TTS 설정
        self.tts_provider = os.getenv('TTS_PROVIDER', None)
        
        # YouTube Shorts 요구사항
        self.shorts_min_duration = 15
        self.shorts_max_duration = 60
        self.shorts_target_duration = 55
        self.shorts_aspect_ratio = (9, 16)
        
        # 자막 설정
        self.subtitle_mode = os.getenv('SUBTITLE_MODE', 'full_sentence').lower()
        
        # 데이터베이스 설정
        self.database_path = os.getenv('DATABASE_PATH', 'data/videos.db')
        self.monetization_data_path = os.getenv('MONETIZATION_DATA_PATH', 'data/monetization_data.json')
        
        # 멀티 플랫폼 업로드 설정
        self.enable_tiktok_upload = self._get_bool('ENABLE_TIKTOK_UPLOAD', False)
        self.enable_instagram_upload = self._get_bool('ENABLE_INSTAGRAM_UPLOAD', False)
        
        # TikTok API 설정
        self.tiktok_client_key = os.getenv('TIKTOK_CLIENT_KEY')
        self.tiktok_client_secret = os.getenv('TIKTOK_CLIENT_SECRET')
        self.tiktok_access_token = os.getenv('TIKTOK_ACCESS_TOKEN')
        self.tiktok_refresh_token = os.getenv('TIKTOK_REFRESH_TOKEN')
        
        # Instagram Graph API 설정
        self.instagram_app_id = os.getenv('INSTAGRAM_APP_ID')
        self.instagram_app_secret = os.getenv('INSTAGRAM_APP_SECRET')
        self.instagram_access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
        self.instagram_account_id = os.getenv('INSTAGRAM_ACCOUNT_ID')
        
        # 설정 검증
        self._validate()
        
    def _get_bool(self, key: str, default: bool) -> bool:
        """환경 변수를 bool로 변환"""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def _get_int(self, key: str, default: int) -> int:
        """환경 변수를 int로 변환"""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            print(f"⚠️ {key} 값이 올바르지 않습니다. 기본값 {default}를 사용합니다.")
            return default
    
    def _get_float(self, key: str, default: float) -> float:
        """환경 변수를 float로 변환"""
        try:
            value = float(os.getenv(key, str(default)))
            return max(0.0, min(1.0, value))  # 0.0-1.0 범위로 제한
        except ValueError:
            print(f"⚠️ {key} 값이 올바르지 않습니다. 기본값 {default}를 사용합니다.")
            return default
    
    def _get_list(self, key: str, default: str) -> List[str]:
        """환경 변수를 리스트로 변환"""
        value = os.getenv(key, default)
        return [item.strip() for item in value.split(',') if item.strip()]
    
    def _validate(self):
        """설정 검증"""
        # 필수 디렉토리 생성
        for directory in [self.video_output_dir, self.thumbnail_output_dir, self.temp_dir]:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        # API 키 검증 (경고만 출력)
        if not self.openai_api_key and not self.claude_api_key:
            print("⚠️ OpenAI 또는 Claude API 키가 설정되지 않았습니다.")
        
        # 볼륨 범위 검증
        if not 0.0 <= self.background_music_volume <= 1.0:
            print(f"⚠️ BACKGROUND_MUSIC_VOLUME이 범위를 벗어났습니다 ({self.background_music_volume}). 0.25로 설정합니다.")
            self.background_music_volume = 0.25
        
        # 자막 모드 검증
        if self.subtitle_mode not in ('key_words', 'full_sentence'):
            print(f"⚠️ SUBTITLE_MODE가 올바르지 않습니다 ({self.subtitle_mode}). 'full_sentence'로 설정합니다.")
            self.subtitle_mode = 'full_sentence'


# 싱글톤 인스턴스 생성
_settings = Settings()

# 하위 호환성을 위한 모듈 레벨 변수 노출
YOUTUBE_CLIENT_ID = _settings.youtube_client_id
YOUTUBE_CLIENT_SECRET = _settings.youtube_client_secret
YOUTUBE_REFRESH_TOKEN = _settings.youtube_refresh_token

OPENAI_API_KEY = _settings.openai_api_key
CLAUDE_API_KEY = _settings.claude_api_key
AI_API_PROVIDER = _settings.ai_api_provider

PEXELS_API_KEY = _settings.pexels_api_key
UNSPLASH_ACCESS_KEY = _settings.unsplash_access_key

OPENAI_RPM_LIMIT = _settings.openai_rpm_limit
PEXELS_HOURLY_LIMIT = _settings.pexels_hourly_limit
YOUTUBE_DAILY_QUOTA = _settings.youtube_daily_quota

QUOTA_WARNING_THRESHOLD = _settings.quota_warning_threshold
QUOTA_CRITICAL_THRESHOLD = _settings.quota_critical_threshold

USE_BACKGROUND_VIDEO = _settings.use_background_video
USE_BACKGROUND_MUSIC = _settings.use_background_music
BACKGROUND_MUSIC_VOLUME = _settings.background_music_volume

CONTENT_TYPE = _settings.content_type
TREND_MODE = _settings.trend_mode
PREFER_SHORT_VIDEOS = _settings.prefer_short_videos

UPLOAD_SCHEDULE_TIME = _settings.upload_schedule_time
UPLOAD_TIMEZONE = _settings.upload_timezone

DEFAULT_TITLE_PREFIX = _settings.default_title_prefix
DEFAULT_DESCRIPTION = _settings.default_description
DEFAULT_TAGS = _settings.default_tags

VIDEO_OUTPUT_DIR = _settings.video_output_dir
THUMBNAIL_OUTPUT_DIR = _settings.thumbnail_output_dir
TEMP_DIR = _settings.temp_dir

TTS_PROVIDER = _settings.tts_provider

SHORTS_MIN_DURATION = _settings.shorts_min_duration
SHORTS_MAX_DURATION = _settings.shorts_max_duration
SHORTS_TARGET_DURATION = _settings.shorts_target_duration
SHORTS_ASPECT_RATIO = _settings.shorts_aspect_ratio

SUBTITLE_MODE = _settings.subtitle_mode

DATABASE_PATH = _settings.database_path
MONETIZATION_DATA_PATH = _settings.monetization_data_path

ENABLE_TIKTOK_UPLOAD = _settings.enable_tiktok_upload
ENABLE_INSTAGRAM_UPLOAD = _settings.enable_instagram_upload

TIKTOK_CLIENT_KEY = _settings.tiktok_client_key
TIKTOK_CLIENT_SECRET = _settings.tiktok_client_secret
TIKTOK_ACCESS_TOKEN = _settings.tiktok_access_token
TIKTOK_REFRESH_TOKEN = _settings.tiktok_refresh_token

INSTAGRAM_APP_ID = _settings.instagram_app_id
INSTAGRAM_APP_SECRET = _settings.instagram_app_secret
INSTAGRAM_ACCESS_TOKEN = _settings.instagram_access_token
INSTAGRAM_ACCOUNT_ID = _settings.instagram_account_id

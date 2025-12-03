"""
설정 관리 모듈 (Facade for src.core.config)
Deprecated: Use src.core.config.settings instead.
"""
import warnings
import os
from src.core.config import settings

# Deprecation Warning
warnings.warn("config.py is deprecated. Use src.core.config.settings instead.", DeprecationWarning, stacklevel=2)

# Expose settings as module-level variables
YOUTUBE_CLIENT_ID = settings.YOUTUBE_CLIENT_ID
YOUTUBE_CLIENT_SECRET = settings.YOUTUBE_CLIENT_SECRET
YOUTUBE_REFRESH_TOKEN = settings.YOUTUBE_REFRESH_TOKEN

OPENAI_API_KEY = settings.OPENAI_API_KEY
CLAUDE_API_KEY = settings.CLAUDE_API_KEY
AI_API_PROVIDER = settings.AI_API_PROVIDER

PEXELS_API_KEY = settings.PEXELS_API_KEY
UNSPLASH_ACCESS_KEY = settings.UNSPLASH_ACCESS_KEY

OPENAI_RPM_LIMIT = settings.OPENAI_RPM_LIMIT
PEXELS_HOURLY_LIMIT = settings.PEXELS_HOURLY_LIMIT
YOUTUBE_DAILY_QUOTA = settings.YOUTUBE_DAILY_QUOTA

QUOTA_WARNING_THRESHOLD = settings.QUOTA_WARNING_THRESHOLD
QUOTA_CRITICAL_THRESHOLD = settings.QUOTA_CRITICAL_THRESHOLD

USE_BACKGROUND_VIDEO = settings.USE_BACKGROUND_VIDEO
USE_BACKGROUND_MUSIC = settings.USE_BACKGROUND_MUSIC
BACKGROUND_MUSIC_VOLUME = settings.BACKGROUND_MUSIC_VOLUME

CONTENT_TYPE = settings.CONTENT_TYPE
TREND_MODE = settings.TREND_MODE
PREFER_SHORT_VIDEOS = settings.PREFER_SHORT_VIDEOS

UPLOAD_SCHEDULE_TIME = settings.UPLOAD_SCHEDULE_TIME
UPLOAD_TIMEZONE = settings.UPLOAD_TIMEZONE
UPLOAD_DELAY_HOURS = settings.UPLOAD_DELAY_HOURS

DEFAULT_TITLE_PREFIX = settings.DEFAULT_TITLE_PREFIX
DEFAULT_DESCRIPTION = settings.DEFAULT_DESCRIPTION
DEFAULT_TAGS = settings.DEFAULT_TAGS

VIDEO_OUTPUT_DIR = settings.VIDEO_OUTPUT_DIR
THUMBNAIL_OUTPUT_DIR = settings.THUMBNAIL_OUTPUT_DIR
TEMP_DIR = settings.TEMP_DIR

TTS_PROVIDER = settings.TTS_PROVIDER
GOOGLE_CLOUD_CREDENTIALS_PATH = settings.GOOGLE_CLOUD_CREDENTIALS_PATH

SHORTS_MIN_DURATION = settings.SHORTS_MIN_DURATION
SHORTS_MAX_DURATION = settings.SHORTS_MAX_DURATION
SHORTS_TARGET_DURATION = settings.SHORTS_TARGET_DURATION
SHORTS_ASPECT_RATIO = settings.SHORTS_ASPECT_RATIO

SUBTITLE_MODE = settings.SUBTITLE_MODE

DATABASE_PATH = settings.DATABASE_PATH
MONETIZATION_DATA_PATH = settings.MONETIZATION_DATA_PATH

ENABLE_TIKTOK_UPLOAD = settings.ENABLE_TIKTOK_UPLOAD
ENABLE_INSTAGRAM_UPLOAD = settings.ENABLE_INSTAGRAM_UPLOAD

TIKTOK_CLIENT_KEY = settings.TIKTOK_CLIENT_KEY
TIKTOK_CLIENT_SECRET = settings.TIKTOK_CLIENT_SECRET
TIKTOK_ACCESS_TOKEN = settings.TIKTOK_ACCESS_TOKEN
TIKTOK_REFRESH_TOKEN = settings.TIKTOK_REFRESH_TOKEN

INSTAGRAM_APP_ID = settings.INSTAGRAM_APP_ID
INSTAGRAM_APP_SECRET = settings.INSTAGRAM_APP_SECRET
INSTAGRAM_ACCESS_TOKEN = settings.INSTAGRAM_ACCESS_TOKEN
INSTAGRAM_ACCOUNT_ID = settings.INSTAGRAM_ACCOUNT_ID

MAX_PARALLEL_WORKERS = settings.MAX_PARALLEL_WORKERS
ENABLE_PARALLEL_GENERATION = settings.ENABLE_PARALLEL_GENERATION

PRIVACY_STATUS = settings.PRIVACY_STATUS
VIDEO_LANGUAGE = settings.VIDEO_LANGUAGE
CATEGORY_ID = settings.CATEGORY_ID

# For backward compatibility with `from config import Settings`
class Settings:
    def __init__(self):
        # Create a FRESH instance of src.core.config.Settings to pick up current env vars
        from src.core.config import Settings as CoreSettings
        core_settings = CoreSettings()
        
        # Map UPPERCASE keys to lowercase attributes to match old behavior
        for key, value in core_settings.model_dump().items():
            setattr(self, key.lower(), value)
            
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
    
    def _get_list(self, key: str, default: str) -> list:
        """환경 변수를 리스트로 변환"""
        value = os.getenv(key, default)
        return [item.strip() for item in value.split(',') if item.strip()]

# Singleton instance
_settings = Settings()

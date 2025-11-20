"""
설정 관리 모듈
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리 찾기
BASE_DIR = Path(__file__).resolve().parent

# .env 파일 경로 명시적으로 지정
env_path = BASE_DIR / '.env'
try:
    load_dotenv(dotenv_path=env_path)
except PermissionError:
    print("⚠️ .env 파일을 읽을 권한이 없습니다. 파일 권한을 확인하세요.")
    print(f"   경로: {env_path}")

# YouTube API 설정
YOUTUBE_CLIENT_ID = os.getenv('YOUTUBE_CLIENT_ID')
YOUTUBE_CLIENT_SECRET = os.getenv('YOUTUBE_CLIENT_SECRET')
YOUTUBE_REFRESH_TOKEN = os.getenv('YOUTUBE_REFRESH_TOKEN')

# AI API 설정
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
# AI API 우선순위 설정 (claude 또는 openai, 기본값: openai)
AI_API_PROVIDER = os.getenv('AI_API_PROVIDER', 'openai').lower()  # 'openai' 또는 'claude'

# 이미지/영상 API 설정 (선택사항)
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')  # https://www.pexels.com/api/ 에서 무료로 발급 가능 (CC0 라이선스)
UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')  # https://unsplash.com/developers 에서 무료로 발급 가능 (Unsplash License)

# 영상 생성 설정
USE_BACKGROUND_VIDEO = os.getenv('USE_BACKGROUND_VIDEO', 'true').lower() == 'true'  # 배경 영상 사용 여부 (기본: true)

# 콘텐츠 타입 설정
CONTENT_TYPE = os.getenv('CONTENT_TYPE', 'auto')  # 'hook', 'quote', 'story', 'fact', 'short_story', 'auto'
PREFER_SHORT_VIDEOS = os.getenv('PREFER_SHORT_VIDEOS', 'true').lower() == 'true'  # 짧은 영상 선호 (15-30초, 기본: true)

# 업로드 스케줄 설정
UPLOAD_SCHEDULE_TIME = os.getenv('UPLOAD_SCHEDULE_TIME', '09:00')
UPLOAD_TIMEZONE = os.getenv('UPLOAD_TIMEZONE', 'Asia/Seoul')

# 영상 기본 설정
DEFAULT_TITLE_PREFIX = os.getenv('DEFAULT_TITLE_PREFIX', 'Shorts')
DEFAULT_DESCRIPTION = os.getenv('DEFAULT_DESCRIPTION', 'AI로 자동 생성된 YouTube Shorts 영상입니다. 유용한 정보와 팁을 매일 공유합니다. 구독과 좋아요 부탁드립니다!')
DEFAULT_TAGS = os.getenv('DEFAULT_TAGS', 'shorts,쇼츠,ai,인공지능,자동생성,유용한정보,팁,라이프스타일').split(',')

# 디렉토리 설정
VIDEO_OUTPUT_DIR = 'output/videos'
THUMBNAIL_OUTPUT_DIR = 'output/thumbnails'
TEMP_DIR = 'output/temp'

# TTS 설정
TTS_PROVIDER = os.getenv('TTS_PROVIDER', None)  # 'gtts' 또는 'openai', None이면 자동 선택

# YouTube Shorts 요구사항
SHORTS_MIN_DURATION = 15  # 초
SHORTS_MAX_DURATION = 60  # 초 (YouTube Shorts 최대 길이)
SHORTS_TARGET_DURATION = 55  # 초 (목표: 55초, 60초 초과 방지를 위한 안전 마진)
SHORTS_ASPECT_RATIO = (9, 16)  # 세로형 (1080x1920)
# 영상 길이는 스크립트 내용에 따라 자동으로 조정되며, 목표는 55초 (60초 초과 방지)

# 자막 설정
# 'key_words': 핵심 단어만 표시 (1-3개 단어)
# 'full_sentence': 전체 문장 표시 (기본값)
SUBTITLE_MODE = os.getenv('SUBTITLE_MODE', 'full_sentence').lower()  # 'key_words' 또는 'full_sentence'

# 데이터베이스 설정
DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/videos.db')
MONETIZATION_DATA_PATH = os.getenv('MONETIZATION_DATA_PATH', 'data/monetization_data.json')

# 멀티 플랫폼 업로드 설정 (기본값: false, YouTube만 사용)
# TikTok 또는 Instagram 업로드를 사용하려면 true로 설정하고 해당 API 키를 설정하세요
ENABLE_TIKTOK_UPLOAD = os.getenv('ENABLE_TIKTOK_UPLOAD', 'false').lower() == 'true'
ENABLE_INSTAGRAM_UPLOAD = os.getenv('ENABLE_INSTAGRAM_UPLOAD', 'false').lower() == 'true'

# TikTok API 설정 (선택사항)
TIKTOK_CLIENT_KEY = os.getenv('TIKTOK_CLIENT_KEY')
TIKTOK_CLIENT_SECRET = os.getenv('TIKTOK_CLIENT_SECRET')
TIKTOK_ACCESS_TOKEN = os.getenv('TIKTOK_ACCESS_TOKEN')

# Instagram Graph API 설정 (선택사항)
INSTAGRAM_APP_ID = os.getenv('INSTAGRAM_APP_ID')
INSTAGRAM_APP_SECRET = os.getenv('INSTAGRAM_APP_SECRET')
INSTAGRAM_ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
INSTAGRAM_ACCOUNT_ID = os.getenv('INSTAGRAM_ACCOUNT_ID')


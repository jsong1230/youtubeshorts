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
load_dotenv(dotenv_path=env_path)

# YouTube API 설정
YOUTUBE_CLIENT_ID = os.getenv('YOUTUBE_CLIENT_ID')
YOUTUBE_CLIENT_SECRET = os.getenv('YOUTUBE_CLIENT_SECRET')
YOUTUBE_REFRESH_TOKEN = os.getenv('YOUTUBE_REFRESH_TOKEN')

# OpenAI API 설정
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# 이미지 API 설정 (선택사항)
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')  # https://www.pexels.com/api/ 에서 무료로 발급 가능
UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')  # https://unsplash.com/developers 에서 무료로 발급 가능

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

# YouTube Shorts 요구사항
SHORTS_MIN_DURATION = 15  # 초
SHORTS_MAX_DURATION = 60  # 초 (YouTube Shorts 최대 길이)
SHORTS_TARGET_DURATION = 55  # 초 (목표: 55초, 60초 초과 방지를 위한 안전 마진)
SHORTS_ASPECT_RATIO = (9, 16)  # 세로형 (1080x1920)
# 영상 길이는 스크립트 내용에 따라 자동으로 조정되며, 목표는 55초 (60초 초과 방지)


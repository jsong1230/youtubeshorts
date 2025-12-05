"""
영상 생성 관련 상수 정의
"""


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

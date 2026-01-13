"""
영상 생성 관련 상수 정의
"""


class VideoConstants:
    """영상 생성 관련 상수"""

    # 해상도
    VIDEO_WIDTH = 1080  # 최종 영상 너비 (9:16)
    VIDEO_HEIGHT = 1920  # 최종 영상 높이 (9:16)
    # 콘텐츠 영역: 9:9 정사각형 (가운데 배치, 위아래 흰색 배경)
    CONTENT_WIDTH = 1080  # 콘텐츠 영역 너비 (9:9)
    CONTENT_HEIGHT = 1080  # 콘텐츠 영역 높이 (9:9)
    VIDEO_FPS = 30

    # 배경 영상 전환 주기
    BACKGROUND_CHANGE_INTERVAL = 5.0  # 배경 영상 전환 주기 (초)

    # 영상 길이
    MIN_DURATION = 15  # 최소 길이 (초)
    MAX_DURATION = 60  # 최대 길이 (초)
    MAX_SAFE_DURATION = 58  # 안전 마진 (초)
    TARGET_DURATION = 55  # 목표 길이 (초) - 기본값 (레거시 호환)

    # 콘텐츠 타입별 최적 길이 (완주율 최적화)
    # 짧은 영상(15-30초): Hook, Quote, Fact - 빠른 정보 전달, 반복 재생 유도
    # 중간 영상(30-45초): Story, Short_Story - 스토리 전개 필요
    # 긴 영상(45-60초): Book_Review, Meditation, Breathing - 상세 설명 필요
    CONTENT_TYPE_DURATIONS = {
        "hook": 50,  # 45-55초 범위, 동기부여 및 힐링 콘텐츠 (후킹-전개-핵심메시지-마무리 구조)
        "quote": 22,  # 18-28초 범위, 명언 + 간단한 설명
        "fact": 25,  # 20-30초 범위, 팩트 + 핵심 설명
        "story": 40,  # 35-45초 범위, 스토리 전개 필요
        "short_story": 35,  # 30-40초 범위, 짧은 스토리
        "meditation": 50,  # 45-60초 범위, 명상 가이드
        "breathing": 45,  # 40-55초 범위, 호흡 가이드
        "book_review": 50,  # 45-60초 범위, 여러 책 소개
        "auto": 50,  # 기본값: 동기부여 및 힐링 콘텐츠 선호
    }

    # 페이드 효과
    DEFAULT_FADE_DURATION = 0.5  # 기본 페이드 길이 (초)
    FADE_RATIO = 0.1  # 페이드 비율 (duration의 10%)

    # 자막
    SUBTITLE_BOTTOM_MARGIN = 150  # 하단 여백 (px)
    SUBTITLE_PADDING = 40  # 자막 배경 패딩 (px)
    SUBTITLE_MAX_WIDTH = 840  # 자막 최대 너비 (px) - 좌우 30픽셀씩 줄임 (900 -> 840)
    SUBTITLE_BACKGROUND_ALPHA = 200  # 자막 배경 투명도

    # 폰트
    BASE_FONT_SIZE = 130  # 폰트 크기 30% 증가 (100 -> 130)
    FONT_SIZES = [
        117,
        104,
        91,
        78,
    ]  # 폰트 크기 옵션 (30% 증가: 90->117, 80->104, 70->91, 60->78)
    LINE_SPACING = 50  # 줄 간격 (px)

    # 배경 그룹
    BACKGROUND_GROUP_SIZE = 2  # 배경 변경 주기 (문장 수)

    # YouTube Shorts 성공 공식 상수
    # 화면 전환 빈도: 1.5~2초마다 전환 (성공 공식)
    SCENE_CHANGE_INTERVAL = 1.8  # 초 (1.5~2초 범위의 중간값)
    SCENE_CHANGE_MIN = 1.5  # 최소 전환 간격 (초)
    SCENE_CHANGE_MAX = 2.0  # 최대 전환 간격 (초)

    # 초반 3초 유지율 최적화
    CRITICAL_FIRST_3_SECONDS = 3.0  # 초반 3초 (가장 중요한 구간)
    HOOK_MAX_DURATION = 3.0  # Hook 최대 길이 (초)

    # 자막 배치 (세로 가운데에 맨 윗줄이 오도록)
    SUBTITLE_POSITION_CENTER = "center"  # 중앙 배치
    SUBTITLE_POSITION_TOP = "top"  # 상단 배치
    SUBTITLE_POSITION_BOTTOM = "bottom"  # 하단 배치
    SUBTITLE_PREFERRED_POSITION = SUBTITLE_POSITION_CENTER  # 기본값: 중앙 (세로 가운데)
    SUBTITLE_TOP_MARGIN = 200  # 상단 여백 (px) - 상단 배치 시 사용
    SUBTITLE_BOTTOM_MARGIN = 500  # 하단 여백 (px) - 하단 배치 시 사용

    # 제목/훅 강조 표시
    HOOK_TITLE_ENABLED = True  # 맨 위에 제목/훅 표시 활성화
    HOOK_TITLE_FONT_SIZE = 100  # 제목/훅 폰트 크기 (줄바꿈 가능하도록 줄임)
    HOOK_TITLE_TOP_MARGIN = 80  # 제목/훅 상단 여백 (px) - 맨 위에 가깝게
    HOOK_TITLE_DURATION = None  # 제목/훅 표시 시간 (None이면 영상 끝까지 유지)
    HOOK_TITLE_COLOR = "white"  # 제목/훅 텍스트 색상 (흰색)
    HOOK_TITLE_STROKE_WIDTH = 8  # 제목/훅 테두리 두께 (강한 테두리)
    HOOK_TITLE_BACKGROUND_COLOR = (255, 255, 255)  # 훅 배경 색상 (흰색)
    HOOK_TITLE_HEIGHT = 300  # 훅 영역 높이 (px) - 위쪽 crop 영역

    # 루프(Loop) 설계
    ENABLE_LOOP_DESIGN = True  # 루프 설계 활성화
    LOOP_TRANSITION_DURATION = 0.3  # 루프 전환 길이 (초)

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

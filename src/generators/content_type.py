"""
콘텐츠 타입 정의
"""
from enum import Enum


class ContentType(Enum):
    """콘텐츠 타입"""
    HOOK = "hook"  # 한국어 속담/관용어 한 문장 학습 (짧고 강한 Hook)
    QUOTE = "quote"  # AI·비즈니스·명언·지식 한 줄
    STORY = "story"  # 스토리텔링 (심리/역사/부자습관)
    FACT = "fact"  # 숏폼 팩트 기반 영상
    SHORT_STORY = "short_story"  # AI 이미지 기반 짧은 스토리
    MEDITATION = "meditation"  # 1분 명상 가이드
    BREATHING = "breathing"  # 호흡 가이드
    BOOK_REVIEW = "book_review"  # 책 리뷰 (기관 선정/추천/수상 도서)
    AUTO = "auto"  # 자동 선택


"""
배경 영상 다운로드 및 관리 모듈
"""

import os
import random
import requests
from typing import Optional, Tuple, List, Set
from moviepy.editor import VideoFileClip, concatenate_videoclips

from src.core.config import settings
from src.generators.video_constants import VideoConstants
from src.utils.retry_decorator import retry
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BackgroundVideoManager:
    """배경 영상 다운로드 및 관리 클래스"""

    def __init__(self, media_downloader=None):
        self.media_downloader = media_downloader

    @retry(
        max_retries=3,
        base_delay=1,
        exceptions=(requests.RequestException, ConnectionError, TimeoutError),
    )
    def http_get_with_retry(self, url: str, **kwargs) -> requests.Response:
        """HTTP GET request with automatic retry on transient failures."""
        timeout = kwargs.pop("timeout", 10)
        response = requests.get(url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response

    def download_video_for_sentence(
        self,
        sentence: str,
        index: int,
        duration: float,
        topic: str = None,
        exclude_video_ids: Set[int] = None,
        force_keyword: str = None,
        language: str = "ko",
    ) -> Tuple[Optional[str], Optional[int]]:
        """문장에 맞는 배경 영상 다운로드

        Args:
            force_keyword: 강제로 사용할 키워드 (재시도 시 사용)
            language: 언어 코드 ('ko' 또는 'en' 등)

        Returns:
            tuple: (bg_video_path, video_id) 또는 (None, None)
        """
        if not self.media_downloader:
            return None, None

        try:
            # Determine keyword
            if force_keyword:
                keyword = force_keyword
                english_keyword = self.media_downloader.translate_keyword_to_english(
                    force_keyword
                )
                logger.debug(
                    f"🔄 대체 키워드 사용: {force_keyword} -> {english_keyword}"
                )
            else:
                keyword, english_keyword = self._extract_keywords(
                    sentence, topic, language=language
                )

            logger.debug(f"🎬 배경 영상 다운로드 시도: {keyword} -> {english_keyword}")

            # Download from Pexels
            if settings.PEXELS_API_KEY:
                bg_video_path, video_id = self._download_from_pexels(
                    english_keyword, index, duration, exclude_video_ids
                )
                if bg_video_path and video_id:
                    return bg_video_path, video_id

            return None, None
        except Exception as e:
            logger.warning(f"⚠️ 배경 영상 다운로드 실패: {e}")
            return None, None

    def prepare_background_clips(
        self,
        script: List[str],
        audio_durations: List[float],
        topic: str,
        language: str = "ko",
        preferred_keywords: List[str] = None,
    ) -> Tuple[List[Tuple[int, int, Optional[str], Optional[str]]], Set[int]]:
        """배경 클립 준비 (자막과 완전히 독립, 각 문장마다 배경 영상 다운로드)

        Returns:
            tuple: (background_groups, downloaded_video_ids)
            background_groups: List of tuples (start_idx, end_idx, video_path, image_path)
            각 문장마다 하나의 배경 영상이 할당되며, 영상은 원래 길이만큼 사용됨
        """
        background_groups: List[Tuple[int, int, Optional[str], Optional[str]]] = []
        use_background_video = settings.USE_BACKGROUND_VIDEO
        downloaded_video_ids: Set[int] = set()

        # 각 문장마다 독립적으로 배경 영상 다운로드 (자막과 완전히 독립)
        for i, sentence in enumerate(script):
            sentence_duration = audio_durations[i] if i < len(audio_durations) else 3.0

            bg_video_path = None
            if use_background_video and settings.PEXELS_API_KEY:
                # 힐링 키워드 모드: 추천 키워드 무시, 항상 힐링/자연/동물 키워드만 사용
                # 오디오는 정보성, 비디오는 항상 힐링/자연/동물만 사용
                bg_video_path, video_id = self._download_with_retry_strategy(
                    sentence,
                    i,
                    sentence_duration,  # 문장 길이만큼 요청 (하지만 영상은 원래 길이 사용)
                    topic,
                    downloaded_video_ids,
                    language=language,
                    preferred_keyword=None,  # 추천 키워드 무시
                )
                if bg_video_path and video_id:
                    downloaded_video_ids.add(video_id)

            if not bg_video_path:
                # 최종 폴백: 힐링 키워드로 재시도
                logger.warning(
                    f"   ⚠️ 배경 영상 다운로드 실패 (문장 {i+1}), 힐링 키워드로 재시도..."
                )
                healing_fallback_keywords = [
                    "nature",
                    "calm nature",
                    "peaceful nature",
                    "relaxing nature",
                    "forest",
                    "ocean waves",
                ]
                for final_keyword in healing_fallback_keywords:
                    bg_video_path, video_id = self._download_with_retry_strategy(
                        final_keyword,
                        i,
                        sentence_duration,
                        topic,
                        downloaded_video_ids,
                        language=language,
                    )
                    if bg_video_path and video_id:
                        downloaded_video_ids.add(video_id)
                        logger.info(
                            f"   ✅ 힐링 폴백 키워드로 배경 영상 다운로드 성공: {final_keyword}"
                        )
                        break

                if not bg_video_path:
                    # 최종 폴백: 이미지 사용 (배경 영상 대신)
                    logger.warning(
                        f"   ⚠️ 배경 영상 다운로드 실패, 이미지 폴백 사용 (문장 {i+1})"
                    )
                    bg_image_path = None
                    background_groups.append((i, i + 1, None, bg_image_path))
                    continue

            # 각 문장마다 하나의 배경 영상 (독립적)
            background_groups.append((i, i + 1, bg_video_path, None))
            logger.info(
                f"   📹 배경 영상 {i+1}: 문장 {i+1}, 영상 길이: 원본 길이 사용 (문장 길이: {sentence_duration:.2f}초)"
            )
            logger.debug(f"      문장: {sentence[:50]}...")

        return background_groups, downloaded_video_ids

    def create_background_video_clip(
        self,
        bg_video_path: str,
        group_duration: float,
        group_start: int,
        group_end: int,
    ) -> VideoFileClip:
        """배경 영상 클립 생성 (원래 길이만큼 사용, 자막과 독립)"""
        try:
            logger.debug(
                f"   📹 배경 영상 로드 (문장 {group_start+1}): {bg_video_path}"
            )
            source_video = VideoFileClip(bg_video_path)
            source_duration = source_video.duration
            logger.debug(
                f"   원본 영상 길이: {source_duration:.2f}초 (문장 길이: {group_duration:.2f}초와 독립)"
            )

            # Resize to 9:9 square (content area)
            source_video = source_video.resize(
                (VideoConstants.CONTENT_WIDTH, VideoConstants.CONTENT_HEIGHT)
            )

            # 원래 영상 길이만큼 사용 (자막과 완전히 독립)
            # 영상이 짧으면 반복, 길면 원래 길이만큼만 사용
            if source_duration < group_duration:
                # 영상이 문장보다 짧으면 반복
                repeat_count = int(group_duration / source_duration) + 1
                repeated_clips = [source_video] * repeat_count
                group_clip = concatenate_videoclips(repeated_clips)
                # 필요한 길이만큼 자르기
                group_clip = group_clip.subclip(0, group_duration)
                source_video.close()
                logger.debug(
                    f"   ✅ 배경 영상 반복: {source_duration:.2f}초 × {repeat_count}회 → {group_duration:.2f}초"
                )
            else:
                # 영상이 문장보다 길면 원래 길이만큼만 사용 (자르지 않음)
                group_clip = source_video  # 원래 길이 그대로 사용
                logger.debug(
                    f"   ✅ 배경 영상 원본 길이 사용: {source_duration:.2f}초 (문장 길이와 독립)"
                )

            return group_clip
        except Exception as e:
            logger.error(f"   ❌ 배경 영상 사용 실패: {e}", exc_info=True)
            raise ValueError(
                f"문장 {group_start+1}의 배경 영상을 로드할 수 없습니다: {e}"
            )

    def _extract_keywords(
        self, sentence: str, topic: str, language: str = "ko"
    ) -> Tuple[str, str]:
        """키워드 추출"""
        # Healing & Nature 키워드만 사용 모드 (스크립트 주제와 무관하게)
        # 오디오는 정보성, 비디오는 항상 힐링/자연/동물만 사용
        if settings.USE_HEALING_KEYWORDS_ONLY:
            healing_keywords = [
                # Nature
                "forest",
                "ocean waves",
                "mountain drone",
                "rainforest",
                "snow falling",
                "beach sunset",
                "mountain lake",
                "autumn leaves",
                "starry night",
                "meadow",
                "waterfall",
                "desert dunes",
                "tropical beach",
                "bamboo forest",
                "zen garden",
                "clouds time lapse",
                "sunset clouds",
                # Animals
                "cute cat",
                "puppy",
                "cute dog",
                "kitten",
                # Satisfying/Relaxing
                "raining window",
                "galaxy",
                "flower field",
                "bonfire",
                "underwater",
                "aurora",
                "cherry blossom",
                "campfire",
                "coral reef",
                "satisfying",
                "satisfying video",
                "satisfying nature",
                "relaxing nature",
                "calm nature",
                "peaceful nature",
                "meditation nature",
                "zen nature",
                "serene nature",
                "tranquil nature",
            ]
            import random

            selected_keyword = random.choice(healing_keywords)
            logger.info(f"🌿 힐링 키워드 모드: '{selected_keyword}' 선택 (주제와 무관)")
            return selected_keyword, selected_keyword

        # 한국어인 경우 한국 키워드 우선 추가
        korean_priority_keywords = []
        if language == "ko":
            # 주제/문장 내용에 따라 적절한 한국 키워드 선택
            topic_lower = (topic or "").lower()
            sentence_lower = (sentence or "").lower()

            # 주제/문장 내용 분석하여 적절한 한국 키워드 추가
            if any(
                word in topic_lower + sentence_lower
                for word in [
                    "집",
                    "집안",
                    "방",
                    "난방",
                    "온도",
                    "커튼",
                    "창문",
                    "이불",
                    "필터",
                ]
            ):
                korean_priority_keywords = [
                    "Korean home",
                    "Korean apartment",
                    "Korean living room",
                    "Korean interior",
                ]
            elif any(
                word in topic_lower + sentence_lower
                for word in ["사무실", "직장", "업무", "생산성", "재태크", "돈", "절약"]
            ):
                korean_priority_keywords = [
                    "Korean office",
                    "Korean lifestyle",
                    "Seoul cityscape",
                ]
            elif any(
                word in topic_lower + sentence_lower
                for word in ["도시", "서울", "거리", "시장"]
            ):
                korean_priority_keywords = [
                    "Seoul cityscape",
                    "Korean street",
                    "Korean market",
                ]
            else:
                korean_priority_keywords = [
                    "Korean lifestyle",
                    "Korean home",
                    "Seoul cityscape",
                ]

        topic_keyword = None
        if topic and self.media_downloader:
            topic_keywords = self.media_downloader.extract_keywords(
                topic, language=language
            )
            if topic_keywords:
                topic_keyword = topic_keywords[0]
                topic_english = self.media_downloader.translate_keyword_to_english(
                    topic_keyword
                )
                logger.debug(
                    f"🎯 주제 키워드 우선 사용: {topic} -> {topic_keyword} -> {topic_english}"
                )

        sentence_keywords = (
            self.media_downloader.extract_keywords(sentence, language=language)
            if self.media_downloader
            else []
        )
        sentence_keyword = sentence_keywords[0] if sentence_keywords else None

        # 한국어인 경우 한국 키워드를 최우선으로 사용
        if language == "ko" and korean_priority_keywords:
            # 한국 키워드가 이미 포함되어 있는지 확인
            all_keywords: list[str] = []
            if sentence_keywords:
                all_keywords.extend(sentence_keywords)
            if topic_keywords:
                all_keywords.extend(topic_keywords)

            # 한국 키워드가 없으면 추가
            has_korean_keyword = any(
                "korean" in k.lower() or "seoul" in k.lower() or "hanok" in k.lower()
                for k in all_keywords
            )

            if not has_korean_keyword and korean_priority_keywords:
                # 한국 키워드를 첫 번째로 추가
                priority_keyword = korean_priority_keywords[0]
                logger.info(f"🇰🇷 한국 키워드 우선 추가: {priority_keyword}")
                keyword = priority_keyword
                english_keyword = priority_keyword  # 이미 영어
                return keyword, english_keyword

        if sentence_keyword:
            keyword = sentence_keyword
            english_keyword = self.media_downloader.translate_keyword_to_english(
                sentence_keyword
            )
            logger.debug(
                f"🎯 문장 키워드 우선 사용: {sentence} -> {keyword} -> {english_keyword}"
            )
        elif topic_keyword:
            keyword = topic_keyword
            english_keyword = self.media_downloader.translate_keyword_to_english(
                topic_keyword
            )
            logger.debug(f"⚠️ 문장 키워드 없음, 주제 키워드 사용: {topic} -> {keyword}")
        else:
            if topic:
                keyword = topic
                english_keyword = (
                    self.media_downloader.translate_keyword_to_english(topic)
                    if self.media_downloader
                    else topic
                )
            else:
                keyword = "nature"
                english_keyword = "nature"

        return keyword, english_keyword

    def _download_with_retry_strategy(
        self,
        sentence: str,
        index: int,
        duration: float,
        topic: str,
        exclude_video_ids: Set[int],
        language: str = "ko",
        preferred_keyword: str = None,
    ) -> Tuple[Optional[str], Optional[int]]:
        """재시도 전략으로 배경 영상 다운로드"""
        # 힐링 키워드 모드: 추천 키워드 및 주제/문장 키워드 무시
        # 오디오는 정보성, 비디오는 항상 힐링/자연/동물만 사용
        if settings.USE_HEALING_KEYWORDS_ONLY:
            # 힐링 키워드 리스트 (중복 방지를 위해 매번 랜덤 선택)
            healing_keywords = [
                # Nature
                "forest",
                "ocean waves",
                "mountain drone",
                "rainforest",
                "snow falling",
                "beach sunset",
                "mountain lake",
                "autumn leaves",
                "starry night",
                "meadow",
                "waterfall",
                "desert dunes",
                "tropical beach",
                "bamboo forest",
                "zen garden",
                "clouds time lapse",
                "sunset clouds",
                # Animals
                "cute cat",
                "puppy",
                "cute dog",
                "kitten",
                # Satisfying/Relaxing
                "raining window",
                "galaxy",
                "flower field",
                "bonfire",
                "underwater",
                "aurora",
                "cherry blossom",
                "campfire",
                "coral reef",
                "satisfying",
                "satisfying video",
                "satisfying nature",
                "relaxing nature",
                "calm nature",
                "peaceful nature",
                "meditation nature",
                "zen nature",
                "serene nature",
                "tranquil nature",
            ]
            # 랜덤으로 힐링 키워드 선택
            retry_keywords = [random.choice(healing_keywords)]
            unique_keywords = retry_keywords  # 힐링 모드에서도 unique_keywords 정의
            logger.debug("   🌿 힐링 키워드 모드: 추천 키워드 무시, 힐링 키워드만 사용")
        else:
            # 기존 로직 (힐링 모드가 아닐 때만)
            retry_keywords = []

            # 최우선: 사용자가 제공한 추천 키워드
            if preferred_keyword:
                retry_keywords.append(preferred_keyword)
                logger.debug(f"   🎯 추천 키워드 최우선 사용: {preferred_keyword}")

            # 1차: 문장 키워드
            if self.media_downloader:
                sentence_keywords = self.media_downloader.extract_keywords(
                    sentence, language=language
                )
                if sentence_keywords:
                    retry_keywords.append(sentence_keywords[0])

            # 2차: 주제 키워드
            if topic and self.media_downloader:
                topic_keywords = self.media_downloader.extract_keywords(
                    topic, language=language
                )
                if topic_keywords and topic_keywords[0] not in retry_keywords:
                    retry_keywords.append(topic_keywords[0])

            # 3차: 주제 카테고리별 특화 키워드
            category_keywords = self._get_category_keywords(topic, language=language)
            retry_keywords.extend(category_keywords)

            # 4차: 귀여운 이미지/영상 우선 선택을 위한 키워드 추가
            cute_keywords = ["cute", "adorable", "aesthetic", "beautiful", "charming"]
            retry_keywords.extend(cute_keywords)

            # 키워드 다양성 확보
            unique_keywords = list(dict.fromkeys(retry_keywords))
            random.shuffle(unique_keywords)
            retry_keywords = unique_keywords[:8]

        for retry_idx, keyword in enumerate(retry_keywords):
            bg_video_path, video_id = self.download_video_for_sentence(
                sentence,
                index,
                duration,
                topic=topic,
                exclude_video_ids=exclude_video_ids,
                force_keyword=keyword if retry_idx > 0 else None,
                language=language,
            )
            if bg_video_path and video_id:
                return bg_video_path, video_id
            elif retry_idx < len(unique_keywords) - 1:
                logger.warning(
                    f"   ⚠️ 배경 영상 다운로드 실패 ({keyword}), 다음 키워드 시도..."
                )

        # 최종 폴백: 일반적인 키워드로 재시도
        logger.warning("   ⚠️ 배경 영상 다운로드 실패, 일반 키워드로 재시도...")
        fallback_keywords = [
            "nature",
            "calm",
            "peaceful",
            "serene",
            "meditation",
            "zen",
            "abstract",
            "minimal",
        ]
        for fallback_keyword in fallback_keywords:
            bg_video_path, video_id = self.download_video_for_sentence(
                sentence,
                index,
                duration,
                topic=topic,
                exclude_video_ids=exclude_video_ids,
                force_keyword=fallback_keyword,
                language=language,
            )
            if bg_video_path and video_id:
                logger.info(
                    f"   ✅ 폴백 키워드로 배경 영상 다운로드 성공: {fallback_keyword}"
                )
                return bg_video_path, video_id

        logger.error(
            "   ❌ 배경 영상 다운로드 최종 실패 (모든 키워드 및 폴백 키워드 시도 완료)"
        )
        return None, None

    def _get_category_keywords(self, topic: str, language: str = "ko") -> List[str]:
        """주제 카테고리별 키워드 반환"""
        topic_lower = (topic or "").lower()

        # 한국어인 경우 한국 특화 키워드 추가
        korean_specific = []
        if language == "ko":
            korean_specific = ["seoul", "korean", "korea", "hanok", "k-style"]

        # 재태크 관련
        if any(
            word in topic_lower
            for word in [
                "money",
                "save",
                "invest",
                "budget",
                "finance",
                "wealth",
                "spending",
                "expense",
                "subscription",
                "emergency",
                "fund",
                "401k",
                "roth",
                "ira",
            ]
        ):
            return [
                "money",
                "finance",
                "investment",
                "savings",
                "budget",
                "wealth",
                "business",
            ] + korean_specific

        # AI 관련
        elif any(
            word in topic_lower
            for word in [
                "ai",
                "artificial intelligence",
                "chatgpt",
                "gpt",
                "claude",
                "machine learning",
            ]
        ):
            return [
                "ai",
                "technology",
                "artificial intelligence",
                "robot",
                "digital",
                "innovation",
            ] + korean_specific

        # 생산성 관련
        elif any(
            word in topic_lower
            for word in [
                "routine",
                "productivity",
                "focus",
                "workspace",
                "morning",
                "habit",
                "automate",
            ]
        ):
            return [
                "productivity",
                "workspace",
                "morning",
                "routine",
                "focus",
                "office",
                "desk",
            ] + korean_specific

        # 자기계발 관련
        elif any(
            word in topic_lower
            for word in [
                "growth",
                "motivation",
                "success",
                "achievement",
                "goal",
                "mindset",
                "transform",
                "change",
            ]
        ):
            return [
                "growth",
                "motivation",
                "success",
                "achievement",
                "goal",
                "inspiration",
                "mindset",
            ] + korean_specific

        # 생활/정리 관련
        elif any(
            word in topic_lower
            for word in [
                "declutter",
                "organize",
                "closet",
                "minimalism",
                "home",
                "lifestyle",
                "clean",
            ]
        ):
            return [
                "home",
                "lifestyle",
                "minimalism",
                "organization",
                "declutter",
                "interior",
            ] + korean_specific

        # 기본 키워드
        return [
            "home",
            "lifestyle",
            "indoor",
            "cozy",
            "warm",
            "nature",
            "abstract",
            "cinematic",
        ] + korean_specific

    def _download_from_pexels(
        self,
        english_keyword: str,
        index: int,
        duration: float,
        exclude_video_ids: Optional[Set[int]],
    ) -> Tuple[Optional[str], Optional[int]]:
        """Pexels에서 영상 다운로드 (중복 방지 및 최신 영상 우선)"""
        try:
            # 전역적으로 사용된 비디오 ID 로드 (중복 방지)
            from src.utils.pexels_video_fetcher import (
                _load_used_video_ids,
                _add_video_id,
            )

            global_used_video_ids = _load_used_video_ids()
            if exclude_video_ids is None:
                exclude_video_ids = set()
            # 전역 사용 기록과 현재 세션 제외 목록 병합
            all_excluded_ids = exclude_video_ids | global_used_video_ids

            # 최신 영상 우선 검색을 위해 sort='newest' 파라미터 추가
            # 페이지네이션을 통해 더 많은 옵션 탐색
            max_pages = 3  # 최대 3페이지까지 검색 (240개 비디오)
            per_page = 80

            for page in range(1, max_pages + 1):
                pexels_video_url = f"https://api.pexels.com/v1/videos/search?query={english_keyword}&per_page={per_page}&orientation=portrait&page={page}&sort=newest"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Authorization": settings.PEXELS_API_KEY,
                }

                response = self.http_get_with_retry(pexels_video_url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("videos") and len(data["videos"]) > 0:

                        # Collect available videos with quality scoring
                        available_videos = []
                        for video in data["videos"]:
                            video_id = video.get("id", 0)
                            # 전역 사용 기록과 현재 세션 제외 목록 모두 확인
                            if video_id in all_excluded_ids:
                                continue

                            duration_sec = video.get("duration", 0)
                            if duration_sec < 10:
                                continue

                            files = video.get("video_files", [])
                            best_file = None
                            min_diff = float("inf")

                            for file in files:
                                if file.get("quality") == "hd" and file.get(
                                    "width", 0
                                ) < file.get("height", 0):
                                    diff = abs(file.get("height", 0) - 1920)
                                    if diff < min_diff:
                                        min_diff = diff
                                        best_file = file

                            if best_file:
                                # Calculate quality score
                                quality_score = self._calculate_video_quality_score(
                                    best_file, duration_sec, english_keyword, video
                                )

                                available_videos.append(
                                    {
                                        "id": video_id,
                                        "url": best_file.get("link"),
                                        "duration": duration_sec,
                                        "height": best_file.get("height", 0),
                                        "quality_score": quality_score,
                                    }
                                )

                        # Select from top quality videos (prioritize quality score)
                        if available_videos:
                            # Sort by quality score (descending), then by height match
                            available_videos.sort(
                                key=lambda x: (
                                    -x["quality_score"],
                                    abs(x["height"] - 1920),
                                )
                            )
                            # Select from top 5 highest quality videos
                            top_videos = available_videos[
                                : min(5, len(available_videos))
                            ]
                            video_data = random.choice(top_videos)

                            video_url = video_data["url"]
                            video_id = video_data["id"]
                            bg_video_path = os.path.join(
                                settings.TEMP_DIR, f"bg_video_{index}_{video_id}.mp4"
                            )

                            video_response = self.http_get_with_retry(
                                video_url, stream=True
                            )
                            if video_response.status_code == 200:
                                with open(bg_video_path, "wb") as f:
                                    for chunk in video_response.iter_content(
                                        chunk_size=1024
                                    ):
                                        if chunk:
                                            f.write(chunk)

                                # 전역 사용 기록에 추가 (중복 방지)
                                _add_video_id(video_id)
                                logger.info(
                                    f"✅ Pexels 배경 영상 다운로드 성공: {english_keyword} (ID: {video_id}, 페이지 {page}, 최신순)"
                                )
                                return bg_video_path, video_id

                        # 현재 페이지에서 적합한 영상을 찾지 못했으면 다음 페이지로
                        if page < max_pages:
                            logger.debug(
                                f"   페이지 {page}에서 적합한 영상 없음, 다음 페이지 검색..."
                            )
                            continue
                        else:
                            # 마지막 페이지까지 검색했지만 적합한 영상이 없음
                            break
                    else:
                        # 비디오가 없는 페이지면 다음 페이지로
                        if page < max_pages:
                            continue
                        else:
                            break
                else:
                    # API 오류 시 다음 페이지로 시도
                    if page < max_pages:
                        logger.warning(
                            f"   ⚠️ 페이지 {page} API 오류 (코드: {response.status_code}), 다음 페이지 시도..."
                        )
                        continue
                    else:
                        break
        except Exception as e:
            logger.warning(f"   Pexels API 실패: {e}", exc_info=True)
            # 상세 에러 정보 로깅
            if hasattr(e, "response") and e.response is not None:
                logger.warning(f"   Pexels API 응답 코드: {e.response.status_code}")
                logger.warning(f"   Pexels API 응답 내용: {e.response.text[:200]}")

        return None, None

    def _calculate_video_quality_score(
        self, video_file: dict, duration: float, keyword: str, video_data: dict
    ) -> float:
        """배경 영상 품질 점수 계산

        Args:
            video_file: 비디오 파일 정보
            duration: 영상 길이 (초)
            keyword: 검색 키워드
            video_data: 전체 비디오 데이터

        Returns:
            품질 점수 (0.0 ~ 1.0)
        """
        score = 0.0

        # 1. 해상도 점수 (40% 가중치)
        height = video_file.get("height", 0)
        if height >= 1920:
            resolution_score = 1.0
        elif height >= 1080:
            resolution_score = 0.8
        elif height >= 720:
            resolution_score = 0.6
        else:
            resolution_score = 0.4
        score += resolution_score * 0.4

        # 2. 길이 적합성 점수 (20% 가중치)
        # 이상적인 길이: 15-30초 (충분한 컨텐츠, 반복 가능)
        if 15 <= duration <= 30:
            duration_score = 1.0
        elif 10 <= duration < 15 or 30 < duration <= 45:
            duration_score = 0.8
        elif 5 <= duration < 10 or 45 < duration <= 60:
            duration_score = 0.6
        else:
            duration_score = 0.4
        score += duration_score * 0.2

        # 3. 키워드 매칭 점수 (30% 가중치)
        # 비디오 태그나 설명에 키워드가 포함되어 있는지 확인
        tags = video_data.get("tags", [])
        video_url = video_data.get("url", "")
        keyword_lower = keyword.lower()

        keyword_match_score = 0.0
        if tags:
            for tag in tags:
                if keyword_lower in tag.lower():
                    keyword_match_score = 1.0
                    break
                # 부분 매칭
                tag_words = tag.lower().split()
                keyword_words = keyword_lower.split()
                if any(kw in tag_words for kw in keyword_words):
                    keyword_match_score = 0.7
                    break

        # URL이나 설명에서도 확인
        if keyword_lower in video_url.lower():
            keyword_match_score = max(keyword_match_score, 0.5)

        # 키워드 매칭이 없으면 기본 점수
        if keyword_match_score == 0.0:
            keyword_match_score = 0.3

        score += keyword_match_score * 0.3

        # 4. 비디오 품질 점수 (10% 가중치)
        # HD 품질이면 높은 점수
        quality = video_file.get("quality", "")
        if quality == "hd":
            quality_score = 1.0
        elif quality == "sd":
            quality_score = 0.7
        else:
            quality_score = 0.5
        score += quality_score * 0.1

        return min(score, 1.0)  # 최대 1.0으로 제한

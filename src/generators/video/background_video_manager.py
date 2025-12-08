"""
배경 영상 다운로드 및 관리 모듈
"""

import os
import random
import requests
from typing import Optional, Tuple, List, Set
from moviepy.editor import VideoFileClip, ImageClip, concatenate_videoclips
from PIL import Image
import numpy as np

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
    ) -> Tuple[Optional[str], Optional[int]]:
        """문장에 맞는 배경 영상 다운로드

        Args:
            force_keyword: 강제로 사용할 키워드 (재시도 시 사용)

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
                keyword, english_keyword = self._extract_keywords(sentence, topic)

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
        self, script: List[str], audio_durations: List[float], topic: str
    ) -> Tuple[List, Set[int]]:
        """배경 클립 준비

        Returns:
            tuple: (background_groups, downloaded_video_ids)
        """
        background_groups = []
        group_size = VideoConstants.BACKGROUND_GROUP_SIZE
        use_background_video = settings.USE_BACKGROUND_VIDEO
        downloaded_video_ids: Set[int] = set()

        for i in range(0, len(script), group_size):
            group_end = min(i + group_size, len(script))
            group_sentence = script[i]
            group_duration = sum(audio_durations[i:group_end])

            bg_video_path = None
            if use_background_video and settings.PEXELS_API_KEY:
                bg_video_path, video_id = self._download_with_retry_strategy(
                    group_sentence, i, group_duration, topic, downloaded_video_ids
                )
                if bg_video_path and video_id:
                    downloaded_video_ids.add(video_id)

            if not bg_video_path:
                raise ValueError(
                    f"그룹 {i+1}-{group_end}에 대한 배경 영상을 다운로드할 수 없습니다."
                )

            background_groups.append((i, group_end, bg_video_path, None))
            logger.debug(
                f"   배경 미디어 그룹 {len(background_groups)}: 문장 {i+1}-{group_end} (영상) - {group_sentence[:30]}...)"
            )

        return background_groups, downloaded_video_ids

    def create_background_video_clip(
        self,
        bg_video_path: str,
        group_duration: float,
        group_start: int,
        group_end: int,
    ) -> VideoFileClip:
        """배경 영상 클립 생성"""
        try:
            logger.debug(
                f"   📹 배경 영상 로드 (그룹 {group_start+1}-{group_end}): {bg_video_path}"
            )
            source_video = VideoFileClip(bg_video_path)
            source_duration = source_video.duration
            logger.debug(
                f"   원본 영상 길이: {source_duration:.2f}초, 그룹 길이: {group_duration:.2f}초"
            )

            # Resize
            source_video = source_video.resize(
                (VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT)
            )

            # Extend if needed
            if source_duration < group_duration:
                last_frame = source_video.get_frame(source_duration - 0.1)
                last_frame_img = Image.fromarray(last_frame.astype("uint8"))

                remaining_duration = group_duration - source_duration
                last_frame_clip = ImageClip(np.array(last_frame_img)).set_duration(
                    remaining_duration
                )
                last_frame_clip = last_frame_clip.resize(
                    (VideoConstants.VIDEO_WIDTH, VideoConstants.VIDEO_HEIGHT)
                )

                group_clip = concatenate_videoclips([source_video, last_frame_clip])
                source_video.close()
                logger.debug(
                    f"   ✅ 배경 영상 + 마지막 프레임 확장: {source_duration:.2f}초 + {remaining_duration:.2f}초 = {group_duration:.2f}초"
                )
            else:
                group_clip = source_video.subclip(0, group_duration)
                source_video.close()
                logger.debug(f"   ✅ 배경 영상 준비 완료: {group_duration:.2f}초")

            return group_clip
        except Exception as e:
            logger.error(f"   ❌ 배경 영상 사용 실패: {e}", exc_info=True)
            raise ValueError(
                f"그룹 {group_start+1}-{group_end}의 배경 영상을 로드할 수 없습니다: {e}"
            )

    def _extract_keywords(self, sentence: str, topic: str) -> Tuple[str, str]:
        """키워드 추출"""
        topic_keyword = None
        if topic and self.media_downloader:
            topic_keywords = self.media_downloader.extract_keywords(topic)
            if topic_keywords:
                topic_keyword = topic_keywords[0]
                topic_english = self.media_downloader.translate_keyword_to_english(
                    topic_keyword
                )
                logger.debug(
                    f"🎯 주제 키워드 우선 사용: {topic} -> {topic_keyword} -> {topic_english}"
                )

        sentence_keywords = (
            self.media_downloader.extract_keywords(sentence)
            if self.media_downloader
            else []
        )
        sentence_keyword = sentence_keywords[0] if sentence_keywords else None

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
    ) -> Tuple[Optional[str], Optional[int]]:
        """재시도 전략으로 배경 영상 다운로드"""
        retry_keywords = []

        # 1차: 문장 키워드
        if self.media_downloader:
            sentence_keywords = self.media_downloader.extract_keywords(sentence)
            if sentence_keywords:
                retry_keywords.append(sentence_keywords[0])

        # 2차: 주제 키워드
        if topic and self.media_downloader:
            topic_keywords = self.media_downloader.extract_keywords(topic)
            if topic_keywords and topic_keywords[0] not in retry_keywords:
                retry_keywords.append(topic_keywords[0])

        # 3차: 주제 카테고리별 특화 키워드
        category_keywords = self._get_category_keywords(topic)
        retry_keywords.extend(category_keywords)

        # 4차: 귀여운 이미지/영상 우선 선택을 위한 키워드 추가
        cute_keywords = ["cute", "adorable", "aesthetic", "beautiful", "charming"]
        retry_keywords.extend(cute_keywords)

        # 키워드 다양성 확보
        unique_keywords = list(dict.fromkeys(retry_keywords))
        random.shuffle(unique_keywords)

        for retry_idx, keyword in enumerate(unique_keywords[:8]):
            bg_video_path, video_id = self.download_video_for_sentence(
                sentence,
                index,
                duration,
                topic=topic,
                exclude_video_ids=exclude_video_ids,
                force_keyword=keyword if retry_idx > 0 else None,
            )
            if bg_video_path and video_id:
                return bg_video_path, video_id
            elif retry_idx < len(unique_keywords) - 1:
                logger.warning(
                    f"   ⚠️ 배경 영상 다운로드 실패 ({keyword}), 다음 키워드 시도..."
                )

        logger.warning("   ⚠️ 배경 영상 다운로드 최종 실패 (모든 키워드 시도 완료)")
        return None, None

    def _get_category_keywords(self, topic: str) -> List[str]:
        """주제 카테고리별 키워드 반환"""
        topic_lower = (topic or "").lower()

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
            ]

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
            ]

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
            ]

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
            ]

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
            ]

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
        ]

    def _download_from_pexels(
        self,
        english_keyword: str,
        index: int,
        duration: float,
        exclude_video_ids: Optional[Set[int]],
    ) -> Tuple[Optional[str], Optional[int]]:
        """Pexels에서 영상 다운로드"""
        try:
            pexels_video_url = f"https://api.pexels.com/videos/search?query={english_keyword}&per_page=80&orientation=portrait"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Authorization": settings.PEXELS_API_KEY,
            }

            response = self.http_get_with_retry(pexels_video_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data.get("videos") and len(data["videos"]) > 0:
                    if exclude_video_ids is None:
                        exclude_video_ids = set()

                    # Collect available videos with quality scoring
                    available_videos = []
                    for video in data["videos"]:
                        video_id = video.get("id", 0)
                        if video_id in exclude_video_ids:
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
                        top_videos = available_videos[: min(5, len(available_videos))]
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
                            logger.info(
                                f"✅ Pexels 배경 영상 다운로드 성공: {english_keyword} (ID: {video_id})"
                            )
                            return bg_video_path, video_id
        except Exception as e:
            logger.warning(f"   Pexels API 실패: {e}")

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

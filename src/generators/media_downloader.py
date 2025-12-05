"""
미디어 다운로드 모듈 (이미지, 영상)
"""

import re
import requests
from typing import Optional, List
from PIL import Image
from io import BytesIO

from src.core.config import settings
from src.utils.retry_decorator import retry
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MediaDownloader:
    """미디어 다운로드 클래스"""

    def __init__(
        self, openai_client=None, http_get_with_retry=None, api_call_with_retry=None
    ):
        self.openai_client = openai_client
        self._http_get_with_retry = http_get_with_retry or self._default_http_get
        self._api_call_with_retry = api_call_with_retry or self._default_api_call

    @retry(
        max_retries=3,
        base_delay=1,
        exceptions=(requests.RequestException, ConnectionError, TimeoutError),
    )
    def _default_http_get(self, url: str, **kwargs) -> requests.Response:
        """기본 HTTP GET 요청"""
        timeout = kwargs.pop("timeout", 10)
        response = requests.get(url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response

    def _default_api_call(self, api_func, *args, **kwargs):
        """기본 API 호출"""
        return api_func(*args, **kwargs)

    def extract_keywords(self, sentence: str) -> List[str]:
        """문장에서 이미지 키워드 추출 (AI 사용)"""
        # AI를 사용해서 더 정확한 키워드 추출 시도
        if self.openai_client:
            try:
                response = self._api_call_with_retry(
                    self.openai_client.chat.completions.create,
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert at extracting visual keywords for video/image search. Extract 1-5 diverse, specific English keywords from the given sentence that are suitable for background video search. Include varied keywords (objects, actions, moods, settings) to maximize diversity. For abstract sentences, include mood keywords like 'abstract', 'cinematic', 'moody', 'minimal', 'dynamic'. Always provide multiple diverse options.",
                        },
                        {
                            "role": "user",
                            "content": f"Extract 3-5 diverse English keywords for background video search from this sentence (comma-separated, maximize variety):\n\n{sentence}\n\nProvide diverse keywords covering different aspects: objects, actions, moods, settings, etc.",
                        },
                    ],
                    max_tokens=50,
                    temperature=0.3,
                )
                keywords_text = response.choices[0].message.content.strip()
                # 쉼표나 줄바꿈으로 분리
                keywords = [
                    k.strip().lower()
                    for k in re.split(r"[,，\n]", keywords_text)
                    if k.strip()
                ]
                # 영어가 아닌 것 제거
                keywords = [k for k in keywords if k.isascii() and len(k) > 2]
                if keywords:
                    logger.debug(f"   AI 키워드 추출: {keywords}")
                    return keywords[:5]  # 최대 5개로 증가 (다양성 확보)
            except Exception as e:
                logger.debug(f"   AI 키워드 추출 실패, 기본 방법 사용: {e}")

        # AI 실패 시 기본 키워드 매핑 사용
        keywords = []

        # 확장된 키워드 패턴
        keyword_patterns = {
            "건강": "health",
            "건강한": "healthy",
            "운동": "fitness",
            "운동하다": "exercise",
            "요리": "cooking",
            "요리하다": "cooking",
            "음식": "food",
            "먹다": "eating",
            "여행": "travel",
            "여행하다": "traveling",
            "자기계발": "self-improvement",
            "개발": "development",
            "습관": "habit",
            "습관을": "habit",
            "아침": "morning",
            "아침에": "morning",
            "루틴": "routine",
            "일상": "daily",
            "공부": "study",
            "학습": "learning",
            "공부하다": "studying",
            "성공": "success",
            "성공하다": "success",
            "동기부여": "motivation",
            "동기": "motivation",
            "영감": "inspiration",
            "영감을": "inspiration",
            "자연": "nature",
            "자연의": "nature",
            "풍경": "landscape",
            "경치": "scenery",
            "도시": "city",
            "도시의": "urban",
            "사람": "people",
            "사람들": "people",
            "행복": "happiness",
            "행복한": "happy",
            "평화": "peace",
            "평화로운": "peaceful",
            "물": "water",
            "물을": "water",
            "스트레칭": "stretching",
            "스트레칭하다": "stretching",
            "명상": "meditation",
            "명상하다": "meditation",
            "목표": "goal",
            "목표를": "goal",
            "과일": "fruit",
            "과일을": "fruit",
            "오트밀": "oatmeal",
            "시리얼": "cereal",
        }

        # 문장에서 키워드 찾기 (더 정확한 매칭)
        sentence_lower = sentence.lower()
        for korean, english in keyword_patterns.items():
            if korean in sentence_lower:
                keywords.append(english)

        # 키워드가 없으면 문장의 주요 단어 추출 시도
        if not keywords:
            # 한글 단어 추출 (간단한 방법)
            words = re.findall(r"[가-힣]+", sentence)
            if words:
                # 가장 긴 단어를 키워드로 사용
                longest_word = max(words, key=len)
                # 기본 키워드 매핑에 없으면 'nature' 사용
                keywords = ["nature", "inspiration"]
            else:
                keywords = ["nature", "inspiration", "motivation"]

        return keywords[:3]  # 최대 3개

    def translate_keyword_to_english(self, keyword: str) -> str:
        """키워드를 영어로 변환 (간단한 매핑)"""
        # 이미 영어면 그대로 반환
        if keyword.isascii():
            return keyword

        # 한글-영어 매핑
        mapping = {
            "건강": "health",
            "운동": "fitness",
            "요리": "cooking",
            "음식": "food",
            "여행": "travel",
            "자기계발": "self-improvement",
            "습관": "habit",
            "아침": "morning",
            "루틴": "routine",
            "공부": "study",
            "학습": "learning",
            "성공": "success",
            "동기부여": "motivation",
            "영감": "inspiration",
            "자연": "nature",
            "풍경": "landscape",
            "도시": "city",
            "사람": "people",
            "행복": "happiness",
            "평화": "peace",
        }

        return mapping.get(keyword, "nature")

    def resize_and_crop(
        self, img: Image.Image, target_width: int, target_height: int
    ) -> Image.Image:
        """이미지를 목표 크기에 맞게 리사이즈 및 크롭"""
        img_width, img_height = img.size
        target_ratio = target_width / target_height
        img_ratio = img_width / img_height

        if img_ratio > target_ratio:
            # 이미지가 더 넓음 - 높이에 맞춰서 리사이즈 후 좌우 크롭
            new_height = target_height
            new_width = int(new_height * img_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            left = (new_width - target_width) // 2
            img = img.crop((left, 0, left + target_width, target_height))
        else:
            # 이미지가 더 높음 - 너비에 맞춰서 리사이즈 후 상하 크롭
            new_width = target_width
            new_height = int(new_width / img_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            top = (new_height - target_height) // 2
            img = img.crop((0, top, target_width, top + target_height))

        return img

    def try_pexels_api(
        self, english_keyword: str, headers: dict
    ) -> Optional[Image.Image]:
        """Pexels API로 이미지 다운로드 시도 (주제 관련 이미지 우선)"""
        try:
            primary_keyword = english_keyword
            pexels_url = f"https://api.pexels.com/v1/search?query={primary_keyword}&per_page=5&orientation=portrait"
            pexels_headers = {**headers, "Authorization": settings.PEXELS_API_KEY}
            response = self._http_get_with_retry(
                pexels_url, headers=pexels_headers, timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("photos") and len(data["photos"]) > 0:
                    # 주제와 관련된 이미지만 선택
                    selected_photo = None
                    for photo in data["photos"]:
                        photo_text = f"{photo.get('alt', '')} {photo.get('photographer', '')}".lower()
                        if english_keyword.lower() in photo_text or any(
                            word in photo_text
                            for word in english_keyword.lower().split()
                        ):
                            selected_photo = photo
                            break
                    if not selected_photo:
                        logger.debug(
                            "   ⚠️ 주제 관련 이미지 없음, 이미지 다운로드 건너뜀"
                        )
                        return None

                    image_url = selected_photo["src"]["large"]
                    if "portrait" in selected_photo["src"]:
                        image_url = selected_photo["src"]["portrait"]

                    img_response = self._http_get_with_retry(
                        image_url, headers=headers, timeout=10
                    )
                    if img_response.status_code == 200:
                        img = Image.open(BytesIO(img_response.content))
                        if img.mode != "RGB":
                            img = img.convert("RGB")
                        img = self.resize_and_crop(img, 1080, 1920)
                        logger.debug(
                            f"✅ Pexels 이미지 다운로드 성공: {english_keyword}"
                        )
                        return img
        except Exception as e:
            logger.warning(f"   Pexels API 실패: {e}")
        return None

    def try_unsplash_api(
        self, english_keyword: str, headers: dict
    ) -> Optional[Image.Image]:
        """Unsplash API로 이미지 다운로드 시도 (주제 관련 이미지 우선)"""
        try:
            primary_keyword = english_keyword
            unsplash_url = f"https://api.unsplash.com/search/photos?query={primary_keyword}&orientation=portrait&per_page=5"
            unsplash_headers = {
                **headers,
                "Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}",
            }
            response = self._http_get_with_retry(
                unsplash_url, headers=unsplash_headers, timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("results") and len(data["results"]) > 0:
                    # 주제와 관련된 이미지만 선택
                    selected_photo = None
                    for photo in data["results"]:
                        photo_text = f"{photo.get('description', '')} {photo.get('alt_description', '')} {photo.get('user', {}).get('name', '')}".lower()
                        if english_keyword.lower() in photo_text or any(
                            word in photo_text
                            for word in english_keyword.lower().split()
                        ):
                            selected_photo = photo
                            break
                    if not selected_photo:
                        logger.debug(
                            "   ⚠️ 주제 관련 이미지 없음, 이미지 다운로드 건너뜀"
                        )
                        return None

                    image_url = selected_photo["urls"]["regular"]

                    img_response = self._http_get_with_retry(
                        image_url, headers=headers, timeout=10
                    )
                    if img_response.status_code == 200:
                        img = Image.open(BytesIO(img_response.content))
                        if img.mode != "RGB":
                            img = img.convert("RGB")
                        img = self.resize_and_crop(img, 1080, 1920)
                        logger.debug(
                            f"✅ Unsplash 이미지 다운로드 성공: {english_keyword}"
                        )
                        return img
        except Exception as e:
            logger.warning(f"   Unsplash API 실패: {e}")
        return None

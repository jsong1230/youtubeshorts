"""
채널 히스토리 수집 모듈
우리 YouTube 채널의 업로드된 영상 제목/주제를 수집하여 중복 방지에 활용
"""

from typing import List, Dict, Set
from datetime import datetime, timedelta
from src.core.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

try:
    # from googleapiclient.discovery import build
    from src.utils.youtube_auth import get_authenticated_service

    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class ChannelHistoryCollector:
    """채널 히스토리 수집 클래스"""

    def __init__(self):
        """채널 히스토리 수집기 초기화"""
        self.youtube = None
        self.openai_client = None

        # YouTube API 초기화
        if YOUTUBE_API_AVAILABLE:
            try:
                self.youtube = get_authenticated_service()
                logger.info("✅ YouTube API 클라이언트 초기화 완료 (채널 히스토리)")
            except Exception as e:
                logger.warning(f"⚠️ YouTube API 클라이언트 초기화 실패: {e}")

        # OpenAI API 초기화 (유사도 분석용)
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            try:
                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception as e:
                logger.warning(f"⚠️ OpenAI 클라이언트 초기화 실패: {e}")

    def get_channel_videos(
        self, max_results: int = 100, days: int = None
    ) -> List[Dict]:
        """
        우리 채널의 업로드된 영상 목록 가져오기

        Args:
            max_results: 가져올 영상 수 (최대 50)
            days: 최근 며칠간의 영상만 가져오기 (None이면 전체)

        Returns:
            영상 리스트 (video_id, title, topic, published_at 등)
        """
        if not self.youtube:
            logger.warning("⚠️ YouTube API가 초기화되지 않았습니다.")
            return []

        try:
            videos: List[Dict] = []
            next_page_token = None
            max_pages = 5  # 최대 5페이지 (250개 영상)
            page_count = 0

            while len(videos) < max_results and page_count < max_pages:
                # 검색 요청 (우리 채널의 영상만)
                request_params = {
                    "part": "snippet",
                    "forMine": True,
                    "type": "video",
                    "maxResults": min(50, max_results - len(videos)),  # 최대 50개
                    "order": "date",  # 최신순
                }

                if next_page_token:
                    request_params["pageToken"] = next_page_token

                request = self.youtube.search().list(**request_params)
                response = request.execute()

                if "items" not in response:
                    break

                # 날짜 필터링
                cutoff_date = None
                if days:
                    # timezone-aware datetime으로 생성
                    from datetime import timezone

                    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

                for item in response["items"]:
                    video_id = item["id"]["videoId"]
                    snippet = item["snippet"]
                    published_at_str = snippet["publishedAt"].replace("Z", "+00:00")
                    published_at = datetime.fromisoformat(published_at_str)

                    # 날짜 필터링 (둘 다 timezone-aware로 통일)
                    if cutoff_date and published_at < cutoff_date:
                        continue

                    # 제목에서 #Shorts 태그 제거하여 주제 추출
                    title = snippet["title"]
                    topic = title.replace(" #Shorts", "").replace("#Shorts", "").strip()

                    videos.append(
                        {
                            "video_id": video_id,
                            "title": title,
                            "topic": topic,
                            "published_at": published_at,
                            "thumbnail": snippet.get("thumbnails", {})
                            .get("default", {})
                            .get("url", ""),
                        }
                    )

                # 다음 페이지 토큰 확인
                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break

                page_count += 1

            logger.info(f"✅ 채널에서 {len(videos)}개 영상 수집 완료")
            return videos
        except Exception as e:
            logger.warning(f"⚠️ 채널 영상 수집 실패: {e}")
            import traceback

            traceback.print_exc()
            return []

    def get_existing_topics(self, days: int = 90) -> Set[str]:  # 최근 90일간의 영상만
        """
        우리 채널의 기존 주제 목록 가져오기 (중복 체크용)

        Args:
            days: 최근 며칠간의 영상만 가져오기

        Returns:
            기존 주제 Set (중복 체크용)
        """
        videos = self.get_channel_videos(max_results=200, days=days)

        topics = set()
        for video in videos:
            topic = video.get("topic", "")
            if topic:
                # 소문자로 변환하여 비교 (대소문자 무시)
                topics.add(topic.lower().strip())

        logger.info(f"✅ 기존 주제 {len(topics)}개 수집 완료 (최근 {days}일)")
        return topics

    def check_topic_similarity(
        self, new_topic: str, existing_topics: Set[str], threshold: float = 0.7
    ) -> tuple:
        """
        새 주제가 기존 주제와 유사한지 체크

        Args:
            new_topic: 새 주제
            existing_topics: 기존 주제 Set
            threshold: 유사도 임계값 (0.0 ~ 1.0)

        Returns:
            (유사한지 여부, 가장 유사한 주제)
        """
        new_topic_lower = new_topic.lower().strip()

        # 1. 정확히 일치하는 경우
        if new_topic_lower in existing_topics:
            return True, new_topic_lower

        # 2. 단순 문자열 포함 체크
        for existing_topic in existing_topics:
            # 새 주제가 기존 주제에 포함되거나, 기존 주제가 새 주제에 포함되는 경우
            if new_topic_lower in existing_topic or existing_topic in new_topic_lower:
                # 너무 짧은 단어는 제외 (예: "the", "a", "is" 등)
                if len(new_topic_lower) > 10 and len(existing_topic) > 10:
                    return True, existing_topic

        # 3. OpenAI를 사용한 유사도 분석 (선택적)
        if self.openai_client and len(existing_topics) > 0:
            try:
                # 상위 20개 기존 주제만 비교 (비용 절감)
                existing_topics_list = list(existing_topics)[:20]

                system_prompt = """You are an expert at comparing YouTube video topics for similarity.

Given a new topic and a list of existing topics, determine if the new topic is too similar to any existing topic.

Return only "SIMILAR" or "DIFFERENT", followed by the most similar existing topic if similar."""

                user_prompt = f"""New topic: "{new_topic}"

Existing topics:
{chr(10).join([f"- {topic}" for topic in existing_topics_list])}

Is the new topic too similar to any existing topic? (Consider if they cover the same concept, idea, or message)

Return format:
SIMILAR: [most similar existing topic]
or
DIFFERENT"""

                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=100,
                    temperature=0.3,
                )

                result = response.choices[0].message.content.strip()

                if result.startswith("SIMILAR"):
                    # 가장 유사한 주제 추출
                    similar_topic = (
                        result.split(":", 1)[1].strip() if ":" in result else None
                    )
                    return True, similar_topic
                else:
                    return False, None

            except Exception as e:
                logger.warning(f"⚠️ OpenAI 유사도 분석 실패: {e}")
                # 실패 시 기본 체크 결과 반환
                return False, None

        return False, None

    def filter_duplicate_topics(
        self, new_topics: List[str], days: int = 90
    ) -> List[str]:
        """
        새 주제 리스트에서 중복/유사한 주제 필터링

        Args:
            new_topics: 새 주제 리스트
            days: 기존 영상 조회 기간

        Returns:
            필터링된 주제 리스트 (중복 제거됨)
        """
        # 기존 주제 가져오기
        existing_topics = self.get_existing_topics(days=days)

        if not existing_topics:
            logger.warning("⚠️ 기존 주제가 없어 중복 체크를 건너뜁니다.")
            return new_topics

        filtered_topics = []
        skipped_count = 0

        for topic in new_topics:
            is_similar, similar_topic = self.check_topic_similarity(
                new_topic=topic, existing_topics=existing_topics, threshold=0.7
            )

            if is_similar:
                logger.info(
                    f"⏭️  주제 스킵 (유사함): '{topic}' (유사한 주제: '{similar_topic}')"
                )
                skipped_count += 1
            else:
                filtered_topics.append(topic)

        logger.info(
            f"✅ 주제 필터링 완료: {len(filtered_topics)}/{len(new_topics)}개 통과 (스킵: {skipped_count}개)"
        )
        return filtered_topics

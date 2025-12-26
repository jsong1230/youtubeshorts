"""
YouTube 트렌드 키워드 수집 모듈
YouTube Data API v3를 사용하여 인기 Shorts를 분석하고 트렌드 키워드를 추출
"""

import re
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from collections import Counter
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


class TrendCollector:
    """YouTube 트렌드 키워드 수집 클래스"""

    # High CPM Keywords (Estimated)
    CPM_KEYWORDS = {
        "finance": 2.5,
        "invest": 3.0,
        "stock": 2.8,
        "crypto": 2.5,
        "insurance": 4.0,
        "loan": 3.5,
        "credit": 3.2,
        "mortgage": 3.8,
        "attorney": 3.5,
        "lawyer": 3.2,
        "hosting": 3.0,
        "software": 2.5,
        "trading": 2.8,
        "forex": 3.0,
        "marketing": 2.0,
        "business": 2.2,
        "real estate": 2.5,
        "wealth": 2.0,
        "money": 1.5,
        "passive income": 2.5,
        "productivity": 1.2,
        "tech": 1.5,
        "review": 1.2,
        "tutorial": 1.0,
    }

    def __init__(self):
        """트렌드 수집기 초기화"""
        self.youtube = None
        self.openai_client = None

        # YouTube API 초기화
        if YOUTUBE_API_AVAILABLE:
            try:
                self.youtube = get_authenticated_service()
                logger.info("✅ YouTube API 클라이언트 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ YouTube API 클라이언트 초기화 실패: {e}")

        # OpenAI API 초기화 (키워드 추출용)
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            try:
                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception as e:
                logger.warning(f"⚠️ OpenAI 클라이언트 초기화 실패: {e}")

    def get_trending_shorts(
        self, max_results: int = 50, region_code: str = "US"
    ) -> List[Dict]:
        """
        YouTube 인기 Shorts 영상 가져오기

        Args:
            max_results: 가져올 영상 수 (최대 50)
            region_code: 지역 코드 (기본값: 'US')

        Returns:
            인기 Shorts 영상 리스트 (제목, 조회수, 좋아요 등 포함)
        """
        if not self.youtube:
            logger.warning("⚠️ YouTube API가 초기화되지 않았습니다.")
            return []

        try:
            # YouTube Shorts 검색 (최근 7일간 인기 영상)
            # Shorts는 보통 #shorts 태그가 있거나 duration이 60초 이하
            request = self.youtube.search().list(
                part="snippet",
                q="#shorts",
                type="video",
                maxResults=min(max_results, 50),
                order="viewCount",  # 조회수 순
                publishedAfter=(datetime.now() - timedelta(days=7)).isoformat() + "Z",
                regionCode=region_code,
                videoDuration="short",  # 4분 이하 영상
                videoDefinition="high",  # 고화질
            )

            response = request.execute()

            videos = []
            if "items" in response:
                for item in response["items"]:
                    video_id = item["id"]["videoId"]
                    snippet = item["snippet"]

                    # 영상 상세 정보 가져오기 (조회수, 좋아요 등)
                    video_details = self._get_video_details(video_id)

                    if video_details:
                        videos.append(
                            {
                                "video_id": video_id,
                                "title": snippet["title"],
                                "description": snippet.get("description", ""),
                                "channel_title": snippet.get("channelTitle", ""),
                                "published_at": snippet.get("publishedAt", ""),
                                "views": video_details.get("views", 0),
                                "likes": video_details.get("likes", 0),
                                "comments": video_details.get("comments", 0),
                                "duration": video_details.get("duration", 0),
                                "tags": video_details.get("tags", []),
                            }
                        )

            logger.info(f"✅ 인기 Shorts {len(videos)}개 수집 완료")
            return videos

        except Exception as e:
            logger.warning(f"⚠️ 인기 Shorts 수집 실패: {e}")
            import traceback

            traceback.print_exc()
            return []

    def _get_video_details(self, video_id: str) -> Optional[Dict]:
        """영상 상세 정보 가져오기"""
        if not self.youtube:
            return None

        try:
            request = self.youtube.videos().list(
                part="statistics,contentDetails,snippet", id=video_id
            )
            response = request.execute()

            if response.get("items") and len(response["items"]) > 0:
                video = response["items"][0]
                stats = video.get("statistics", {})
                content = video.get("contentDetails", {})
                snippet = video.get("snippet", {})

                # duration 파싱 (PT1M30S 형식)
                duration_str = content.get("duration", "PT0S")
                duration_seconds = self._parse_duration(duration_str)

                return {
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                    "duration": duration_seconds,
                    "tags": snippet.get("tags", []),
                }
            return None
        except Exception as e:
            logger.warning(f"⚠️ 영상 상세 정보 가져오기 실패 ({video_id}): {e}")
            return None

    def _parse_duration(self, duration_str: str) -> int:
        """ISO 8601 duration 형식을 초로 변환 (예: PT1M30S -> 90)"""
        import re

        pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
        match = re.match(pattern, duration_str)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            return hours * 3600 + minutes * 60 + seconds
        return 0

    def extract_keywords_from_videos(
        self, videos: List[Dict], min_views: int = 10000, top_n: int = 20
    ) -> List[str]:
        """
        영상 목록에서 트렌드 키워드 추출

        Args:
            videos: 영상 리스트
            min_views: 최소 조회수 필터
            top_n: 반환할 키워드 수

        Returns:
            트렌드 키워드 리스트
        """
        # 조회수 필터링
        filtered_videos = [v for v in videos if v.get("views", 0) >= min_views]

        if not filtered_videos:
            logger.warning(f"⚠️ 조회수 {min_views} 이상인 영상이 없습니다.")
            return []

        logger.info(f"📊 {len(filtered_videos)}개 영상에서 키워드 추출 중...")

        # 제목과 태그에서 키워드 추출
        all_keywords = []

        for video in filtered_videos:
            title = video.get("title", "")
            tags = video.get("tags", [])
            description = video.get("description", "")

            # 제목에서 키워드 추출
            title_keywords = self._extract_keywords_from_text(title)
            all_keywords.extend(title_keywords)

            # 태그 추가
            if tags:
                all_keywords.extend([tag.lower() for tag in tags])

            # 설명에서도 키워드 추출 (선택적)
            if description:
                desc_keywords = self._extract_keywords_from_text(
                    description[:200]
                )  # 처음 200자만
                all_keywords.extend(desc_keywords)

        # 키워드 빈도 계산
        keyword_counter = Counter(all_keywords)

        # 상위 키워드 추출
        top_keywords = [
            keyword
            for keyword, count in keyword_counter.most_common(top_n * 2)
            if len(keyword) > 3 and count >= 2  # 최소 2회 이상 등장, 3자 이상
        ]

        # AI로 키워드 정제 및 재정렬 (선택적)
        if self.openai_client and top_keywords:
            try:
                refined_keywords = self._refine_keywords_with_ai(top_keywords[:top_n])
                if refined_keywords:
                    logger.info(f"✅ AI로 정제된 키워드 {len(refined_keywords)}개")
                    return refined_keywords[:top_n]
            except Exception as e:
                logger.warning(f"⚠️ AI 키워드 정제 실패, 기본 키워드 사용: {e}")

        logger.info(f"✅ 추출된 키워드 {len(top_keywords[:top_n])}개")
        return top_keywords[:top_n]

    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """텍스트에서 키워드 추출"""
        if not text:
            return []

        # 영어 단어 추출 (2자 이상)
        words = re.findall(r"\b[a-zA-Z]{2,}\b", text.lower())

        # 불용어 제거
        stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "was",
            "are",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "should",
            "could",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
            "these",
            "those",
            "what",
            "which",
            "who",
            "whom",
            "whose",
            "where",
            "when",
            "why",
            "how",
            "all",
            "each",
            "every",
            "both",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "no",
            "nor",
            "not",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "you",
            "your",
            "yours",
            "he",
            "him",
            "his",
            "she",
            "her",
            "hers",
            "it",
            "its",
            "they",
            "them",
            "their",
            "theirs",
            "we",
            "us",
            "our",
            "ours",
            "i",
            "me",
            "my",
            "mine",
        }

        keywords = [word for word in words if word not in stopwords and len(word) > 2]

        return keywords

    def _refine_keywords_with_ai(self, keywords: List[str]) -> List[str]:
        """AI를 사용하여 키워드를 정제하고 재정렬"""
        if not self.openai_client or not keywords:
            return keywords

        try:
            keywords_text = ", ".join(keywords[:30])  # 최대 30개만 전달

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a YouTube Shorts trend keyword analyzer. Given a list of keywords from popular Shorts videos, extract the most relevant and trending keywords for finance, productivity, self-improvement, and lifestyle content. Return only the keywords, separated by commas, in order of relevance.",
                    },
                    {
                        "role": "user",
                        "content": f"Analyze these keywords from popular YouTube Shorts and return the most relevant ones for finance/productivity/self-improvement content (comma-separated, max 20):\n\n{keywords_text}",
                    },
                ],
                max_tokens=100,
                temperature=0.3,
            )

            refined_text = response.choices[0].message.content.strip()
            refined_keywords = [
                k.strip().lower() for k in refined_text.split(",") if k.strip()
            ]

            return refined_keywords

        except Exception as e:
            logger.warning(f"⚠️ AI 키워드 정제 실패: {e}")
            return keywords

    def collect_trending_keywords(
        self, max_videos: int = 50, min_views: int = 10000, top_n: int = 20
    ) -> List[str]:
        """
        트렌드 키워드 수집 (전체 프로세스)

        Args:
            max_videos: 수집할 영상 수
            min_views: 최소 조회수 필터
            top_n: 반환할 키워드 수

        Returns:
            트렌드 키워드 리스트
        """
        logger.info("🔍 YouTube 트렌드 키워드 수집 시작...")

        # 1. 인기 Shorts 수집
        videos = self.get_trending_shorts(max_results=max_videos)

        if not videos:
            logger.warning("⚠️ 수집된 영상이 없습니다.")
            return []

        # 2. 키워드 추출
        keywords = self.extract_keywords_from_videos(
            videos, min_views=min_views, top_n=top_n
        )

        return keywords

    def get_trending_topics_for_category(
        self, category: str = "finance", max_videos: int = 30
    ) -> List[str]:
        """
        특정 카테고리의 트렌드 주제 가져오기

        Args:
            category: 카테고리 ('finance', 'productivity', 'self-improvement' 등)
            max_videos: 수집할 영상 수

        Returns:
            트렌드 주제 리스트
        """
        if not self.youtube:
            return []

        try:
            # 카테고리별 검색어
            category_queries = {
                "finance": ["money", "finance", "invest", "wealth", "saving", "budget"],
                "productivity": [
                    "productivity",
                    "routine",
                    "habit",
                    "time management",
                    "focus",
                ],
                "self-improvement": [
                    "self improvement",
                    "motivation",
                    "mindset",
                    "success",
                    "goal",
                ],
                "lifestyle": [
                    "lifestyle",
                    "declutter",
                    "minimalist",
                    "organization",
                    "home",
                ],
            }

            queries = category_queries.get(category.lower(), ["finance"])

            all_videos = []
            for query in queries[:2]:  # 최대 2개 쿼리만 사용
                request = self.youtube.search().list(
                    part="snippet",
                    q=f"{query} #shorts",
                    type="video",
                    maxResults=min(max_videos // len(queries), 25),
                    order="viewCount",
                    publishedAfter=(datetime.now() - timedelta(days=7)).isoformat()
                    + "Z",
                    videoDuration="short",
                )

                response = request.execute()

                if "items" in response:
                    for item in response["items"]:
                        video_id = item["id"]["videoId"]
                        video_details = self._get_video_details(video_id)

                        if video_details and video_details.get("views", 0) >= 5000:
                            all_videos.append(
                                {
                                    "video_id": video_id,
                                    "title": item["snippet"]["title"],
                                    "views": video_details.get("views", 0),
                                    "tags": video_details.get("tags", []),
                                }
                            )

            # 제목에서 주제 추출
            topics = []
            for video in all_videos:
                title = video.get("title", "")
                # 제목을 그대로 주제로 사용 (간단한 버전)
                if len(title) > 10 and len(title) < 100:
                    topics.append(title)

            # 중복 제거 및 정렬
            unique_topics = list(dict.fromkeys(topics))  # 순서 유지하면서 중복 제거

            logger.info(
                f"✅ {category} 카테고리 트렌드 주제 {len(unique_topics)}개 수집"
            )
            return unique_topics[:20]  # 최대 20개

        except Exception as e:
            logger.warning(f"⚠️ 카테고리별 트렌드 주제 수집 실패: {e}")
            return []

    def generate_topics_from_trends(
        self,
        keywords: List[str] = None,
        content_type: str = "hook",
        num_topics: int = 10,
        language: str = "en",
    ) -> List[str]:
        """
        트렌드 키워드를 기반으로 AI가 새로운 주제 생성

        Args:
            keywords: 트렌드 키워드 리스트 (None이면 자동 수집)
            content_type: 콘텐츠 타입 ('hook', 'quote', 'story', 'fact', 'short_story')
            num_topics: 생성할 주제 수
            language: 언어 ('en' 또는 'ko', 기본값: 'en')

        Returns:
            생성된 주제 리스트
        """
        if not self.openai_client:
            logger.warning("⚠️ OpenAI API가 없어 주제 생성이 불가능합니다.")
            return []

        # 키워드가 없으면 자동 수집
        if not keywords:
            logger.info("📊 트렌드 키워드 자동 수집 중...")
            keywords = self.collect_trending_keywords(
                max_videos=30, min_views=5000, top_n=15
            )

        if not keywords:
            logger.warning("⚠️ 수집된 키워드가 없습니다.")
            return []

        # CPM 점수 기반 키워드 우선순위 정렬
        try:
            keyword_scores = []
            for keyword in keywords:
                cpm_score = self.analyze_cpm_potential(keyword)
                keyword_scores.append((keyword, cpm_score))

            # CPM 점수 내림차순 정렬
            keyword_scores.sort(key=lambda x: x[1], reverse=True)

            # 상위 키워드 선택 (고CPM 키워드 우선)
            # 전체 키워드의 60%는 고CPM, 40%는 다양성을 위해 나머지에서 선택
            high_cpm_count = int(len(keyword_scores) * 0.6)
            high_cpm_keywords = [kw for kw, _ in keyword_scores[:high_cpm_count]]
            other_keywords = [kw for kw, _ in keyword_scores[high_cpm_count:]]

            # 최종 키워드 리스트 (고CPM 우선 + 다양성)
            prioritized_keywords = high_cpm_keywords + other_keywords[:5]
            keywords = prioritized_keywords[:20]  # 최대 20개

            logger.info(
                f"📊 CPM 우선순위 적용: 상위 {len(high_cpm_keywords)}개 고CPM 키워드 선택"
            )
        except Exception as e:
            logger.warning(f"⚠️ CPM 우선순위 적용 실패, 원본 키워드 사용: {e}")

        try:
            # 콘텐츠 타입별 프롬프트
            content_type_prompts = {
                "hook": {
                    "en": "Create powerful Hook-style topics that grab attention in the first 3 seconds. Use the 'Mindset Flip' technique: state a common negative thought and immediately reframe it positively. **[IMPORTANT] Topics must be relevant to American and Canadian audiences.**",
                    "ko": "첫 3초 안에 시청자의 관심을 끄는 강력한 Hook 스타일 주제를 생성하세요. '마인드셋 플립' 기법을 사용하세요: 흔한 부정적 생각을 제시하고 즉시 긍정적으로 재해석하세요. **[매우 중요] 반드시 한국의 문화, 정서, 사회적 맥락에 특화된 주제를 생성해야 합니다. 한국의 특정 문화(예: 연말 모임, 김장, 설날, 추석, 입시, 취업, 주택, 전세, 월세, 연봉 협상, 퇴직금, 국민연금 등), 한국 사회의 현실(예: 고물가, 주거비 부담, 교육비 부담 등), 한국인만이 공감할 수 있는 상황을 다루어야 합니다. 일반적이거나 번역된 느낌의 주제는 절대 사용하지 마세요.**",
                },
                "quote": {
                    "en": "Create quote/knowledge-style topics that deliver powerful insights about finance, productivity, self-improvement, or investment. **[IMPORTANT] Topics must be relevant to American and Canadian audiences.**",
                    "ko": "재태크, 생산성, 자기계발, 투자에 대한 강력한 인사이트를 전달하는 명언/지식 스타일 주제를 생성하세요. **[매우 중요] 반드시 한국의 문화, 정서, 사회적 맥락에 특화된 주제를 생성해야 합니다. 한국의 특정 금융 제도(예: 전세, 월세, 청약, 적금, 예금, 주택청약종합저축 등), 한국 사회의 현실(예: 고물가, 주거비 부담, 교육비 부담, 연봉 협상, 퇴직금, 국민연금 등), 한국인만이 공감할 수 있는 재태크 상황을 다루어야 합니다. 일반적이거나 번역된 느낌의 주제는 절대 사용하지 마세요.**",
                },
                "story": {
                    "en": "Create storytelling-style topics that deliver lessons through stories about psychology, history, rich habits, or real-life examples. **[IMPORTANT] Topics must be relevant to American and Canadian audiences.**",
                    "ko": "심리, 역사, 부자습관, 실제 사례를 통해 교훈을 전달하는 스토리텔링 스타일 주제를 생성하세요. **[매우 중요] 반드시 한국의 문화, 정서, 사회적 맥락에 특화된 주제를 생성해야 합니다. 한국의 역사적 사례, 한국 부자들의 습관, 한국 사회의 실제 사례(예: 전세로 집 산 사람, 적금으로 목돈 만든 사람, 부동산 투자 성공/실패 사례 등), 한국인만이 공감할 수 있는 스토리를 다루어야 합니다. 일반적이거나 번역된 느낌의 주제는 절대 사용하지 마세요.**",
                },
                "fact": {
                    "en": "Create fact-based topics that present shocking numbers, statistics, or 'did you know' facts about finance, productivity, or lifestyle. **[IMPORTANT] Topics must be relevant to American and Canadian audiences.**",
                    "ko": "재태크, 생산성, 라이프스타일에 대한 충격적인 숫자, 통계, '알고 계셨나요' 팩트를 제시하는 팩트 기반 주제를 생성하세요. **[매우 중요] 반드시 한국의 문화, 정서, 사회적 맥락에 특화된 주제를 생성해야 합니다. 한국 통계청, 한국은행, 금융감독원 등 한국 기관의 통계, 한국의 금융 제도(예: 전세, 월세, 청약, 적금, 예금 등), 한국 사회의 현실(예: 서울 평균 전세 보증금, 평균 월세, 평균 연봉, 평균 주거비 부담률 등)을 다루어야 합니다. 일반적이거나 번역된 느낌의 주제는 절대 사용하지 마세요.**",
                },
                "short_story": {
                    "en": "Create short story-style topics that deliver life lessons, inspiration, or success stories in a personal narrative format. **[IMPORTANT] Topics must be relevant to American and Canadian audiences.**",
                    "ko": "인생 교훈, 영감, 성공 스토리를 개인적 서술 형식으로 전달하는 짧은 스토리 스타일 주제를 생성하세요. **[매우 중요] 반드시 한국의 문화, 정서, 사회적 맥락에 특화된 주제를 생성해야 합니다. 한국인의 실제 경험(예: 전세로 집 산 이야기, 적금으로 목돈 만든 이야기, 부동산 투자 성공/실패 이야기, 연봉 협상 성공 이야기 등), 한국 사회의 현실을 반영한 스토리를 다루어야 합니다. 일반적이거나 번역된 느낌의 주제는 절대 사용하지 마세요.**",
                },
            }

            prompt_template = content_type_prompts.get(
                content_type.lower(), content_type_prompts["hook"]
            )
            system_prompt = prompt_template.get(language, prompt_template["en"])

            keywords_text = ", ".join(keywords[:20])  # 최대 20개 키워드만 사용

            user_prompt = f"""Based on these trending keywords from popular YouTube Shorts: {keywords_text}

Generate {num_topics} new topic ideas for YouTube Shorts videos that:
1. Are relevant to finance, productivity, self-improvement, or lifestyle
2. Are engaging and click-worthy
3. Can be explained in about 55 seconds
4. Follow the {content_type} content style

**[CRITICAL] For Korean topics, they MUST be specific to Korean culture, trends, and sentiments. Avoid generic or translated topics. For example, instead of a generic topic about \'winter\', create a topic about Korea\'s specific winter culture like \'end-of-year gatherings\' or \'winter kimchi making (gimjang)\'.**

Return only the topics, one per line, without numbering or bullets. Each topic should be a complete sentence or phrase that can be used directly as a video title or topic."""

            if language == "ko":
                user_prompt = f"""다음은 인기 YouTube Shorts에서 수집한 트렌드 키워드입니다: {keywords_text}

**자기계발 중심** YouTube Shorts 영상 주제 {num_topics}개를 생성하세요:
1. **자기계발, 생산성, 습관 형성, 목표 달성, 시간 관리, 동기부여, 성장 마인드셋**과 관련되어야 함
2. 매력적이고 클릭을 유도해야 함
3. 약 55초 분량으로 설명 가능해야 함
4. {content_type} 콘텐츠 스타일을 따름

**[매우 중요 - 절대 규칙] 한국어 주제는 반드시 한국의 문화, 정서, 사회적 맥락에 특화되어야 합니다. 다음을 반드시 포함하거나 참고하세요:**

**자기계발 중심 한국 특화 요소:**
- 한국 직장인의 현실: 업무 효율성, 회사 생활, 커리어 발전, 업무 스트레스 관리, 워라밸 등
- 한국 사회의 자기계발 문화: 독서 습관, 아침 루틴, 운동 습관, 취미 활동, 자기 투자 등
- 한국인만이 공감할 수 있는 자기계발 상황: 새벽 기상, 출근길 독서, 퇴근 후 자기계발, 주말 루틴 등
- 습관 형성과 목표 달성: 작은 습관의 힘, 꾸준함의 중요성, 실패 극복, 성장 마인드셋 등

**절대 금지:**
- 재태크, 투자, 부동산, 주식, 금융 관련 주제 (완전히 제외)
- 돈 버는 방법, 수익 창출, 자산 관리 등 금융 관련 내용
- 일반적이거나 번역된 느낌의 주제 (예: "겨울" → "연말 모임", "김장")
- 미국/캐나다 문화를 그대로 번역한 주제
- 한국과 무관한 일반적인 자기계발 주제

**좋은 예시 (자기계발 중심):**
- ✅ "아침 5시 기상으로 바꾼 내 인생의 변화"
- ✅ "하루 10분 독서 습관이 만든 1년 후의 나"
- ✅ "회사에서 가장 효율적으로 일하는 사람들의 공통점"
- ✅ "목표 달성을 위한 작은 습관 3가지"
- ✅ "스트레스 관리로 업무 효율 2배 올린 방법"

**나쁜 예시 (재태크/투자 관련 - 절대 금지):**
- ❌ "연봉 협상으로 월급 두 배 늘리는 방법" (재태크 관련)
- ❌ "전세로 집 산 사람들의 공통점" (부동산/재태크)
- ❌ "적금으로 목돈 만든 이야기" (재태크)

번호나 불릿 없이 주제만 한 줄에 하나씩 반환하세요. 각 주제는 영상 제목이나 주제로 직접 사용할 수 있는 완전한 문장이나 구문이어야 합니다."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=500,
                temperature=0.8,
            )

            topics_text = response.choices[0].message.content.strip()

            # 주제 파싱 (줄바꿈으로 분리)
            topics = []
            for line in topics_text.split("\n"):
                line = line.strip()
                # 번호나 불릿 제거
                line = re.sub(r"^[\d\.\-\*\•\s]+", "", line)
                if line and len(line) > 10:  # 최소 10자 이상
                    topics.append(line)

            # 중복 제거
            unique_topics = list(dict.fromkeys(topics))  # 순서 유지하면서 중복 제거

            logger.info(
                f"✅ AI로 생성된 주제 {len(unique_topics)}개 (목표: {num_topics}개)"
            )
            return unique_topics[:num_topics]

        except Exception as e:
            logger.warning(f"⚠️ AI 주제 생성 실패: {e}")
            import traceback

            traceback.print_exc()
            return []

    def validate_topic_quality(
        self, topic: str, existing_topics: List[str] = None
    ) -> Dict[str, Any]:
        """
        주제 품질 검증

        Args:
            topic: 검증할 주제
            existing_topics: 기존 주제 리스트 (중복 확인용)

        Returns:
            검증 결과 딕셔너리 (is_valid, score, reasons)
        """
        reasons = []
        score = 100

        # 1. 길이 검증
        if len(topic) < 10:
            reasons.append("주제가 너무 짧음")
            score -= 30
        elif len(topic) > 150:
            reasons.append("주제가 너무 김")
            score -= 20

        # 2. 중복 검증
        if existing_topics:
            topic_lower = topic.lower()
            for existing in existing_topics:
                existing_lower = existing.lower()
                # 유사도 계산 (간단한 버전)
                if topic_lower == existing_lower:
                    reasons.append("완전히 동일한 주제")
                    score -= 50
                elif topic_lower in existing_lower or existing_lower in topic_lower:
                    # 한 주제가 다른 주제에 포함되어 있으면 중복 가능성
                    if abs(len(topic_lower) - len(existing_lower)) < 20:
                        reasons.append("유사한 주제와 중복 가능성")
                        score -= 20

        # 3. 키워드 검증 (재태크/생산성 관련 키워드 포함 여부)
        finance_keywords = [
            "money",
            "finance",
            "invest",
            "wealth",
            "save",
            "budget",
            "income",
            "cash",
            "rich",
            "poor",
            "debt",
            "credit",
            "401k",
            "retirement",
            "돈",
            "부자",
            "투자",
            "금융",
            "저축",
        ]
        productivity_keywords = [
            "productivity",
            "routine",
            "habit",
            "time",
            "focus",
            "efficient",
            "organize",
            "생산성",
            "습관",
            "루틴",
            "시간",
            "집중",
        ]
        self_improvement_keywords = [
            "success",
            "motivation",
            "mindset",
            "goal",
            "achieve",
            "growth",
            "improve",
            "성공",
            "동기부여",
            "마인드셋",
            "목표",
            "성장",
        ]

        all_keywords = (
            finance_keywords + productivity_keywords + self_improvement_keywords
        )
        topic_lower = topic.lower()

        has_relevant_keyword = any(keyword in topic_lower for keyword in all_keywords)
        if not has_relevant_keyword:
            reasons.append("관련 키워드 부족")
            score -= 15

        # 4. 품질 점수 기반 검증
        is_valid = score >= 50  # 50점 이상이면 유효

        return {"is_valid": is_valid, "score": score, "reasons": reasons}

    def collect_seasonal_trending_keywords(
        self, season: str, max_videos: int = 30, min_views: int = 5000, top_n: int = 15
    ) -> List[str]:
        """
        계절별 트렌드 키워드 수집

        Args:
            season: 계절 ('spring', 'summer', 'autumn', 'winter')
            max_videos: 수집할 영상 수
            min_views: 최소 조회수 필터
            top_n: 반환할 키워드 수

        Returns:
            계절별 트렌드 키워드 리스트
        """
        if not self.youtube:
            logger.warning(
                "⚠️ YouTube API가 없어 계절별 트렌드 키워드 수집이 불가능합니다."
            )
            return []

        # 계절별 검색어
        seasonal_queries = {
            "spring": [
                "spring cleaning",
                "spring finance",
                "spring budget",
                "spring savings",
                "spring routine",
                "spring reset",
                "spring organization",
                "tax season",
                "spring investment",
                "spring planning",
            ],
            "summer": [
                "summer budget",
                "summer savings",
                "summer vacation money",
                "summer spending",
                "summer income",
                "summer side hustle",
                "summer financial planning",
                "summer investment",
            ],
            "autumn": [
                "fall budget",
                "autumn savings",
                "holiday budget",
                "fall financial planning",
                "autumn investment",
                "year-end tax",
                "fall routine",
                "autumn reset",
                "holiday spending",
                "black friday savings",
            ],
            "winter": [
                "winter budget",
                "winter savings",
                "holiday spending",
                "winter heating costs",
                "year-end financial",
                "winter investment",
                "holiday budget",
                "winter financial planning",
                "new year financial goals",
            ],
        }

        queries = seasonal_queries.get(season.lower(), [])

        if not queries:
            logger.warning(f"⚠️ 알 수 없는 계절: {season}")
            return []

        logger.info(f"🍂 {season} 계절 트렌드 키워드 수집 시작...")

        all_keywords = []

        try:
            for query in queries[:3]:  # 최대 3개 쿼리만 사용
                # 검색 쿼리에 계절 키워드 추가
                search_query = f"{query} #shorts"

                request = self.youtube.search().list(
                    part="snippet",
                    q=search_query,
                    type="video",
                    maxResults=min(max_videos // len(queries), 25),
                    order="viewCount",
                    publishedAfter=(datetime.now() - timedelta(days=30)).isoformat()
                    + "Z",  # 최근 30일
                    videoDuration="short",
                )

                response = request.execute()

                if "items" in response:
                    for item in response["items"]:
                        video_id = item["id"]["videoId"]
                        video_details = self._get_video_details(video_id)

                        if video_details and video_details.get("views", 0) >= min_views:
                            title = item["snippet"]["title"]
                            description = item["snippet"].get("description", "")
                            tags = video_details.get("tags", [])

                            # AI를 사용하여 키워드 추출
                            combined_text = f"Title: {title}. Description: {description}. Tags: {', '.join(tags)}"

                            if self.openai_client:
                                try:
                                    ai_response = self.openai_client.chat.completions.create(
                                        model="gpt-4o-mini",
                                        messages=[
                                            {
                                                "role": "system",
                                                "content": f"You are an expert in extracting concise, impactful keywords related to {season} season, finance, productivity, and lifestyle from video titles, descriptions, and tags for YouTube Shorts. Focus on 1-3 core English keywords that capture the main theme and seasonal relevance.",
                                            },
                                            {
                                                "role": "user",
                                                "content": f"Extract 1-3 core English keywords from the following text, separated by commas:\n\n{combined_text}",
                                            },
                                        ],
                                        max_tokens=50,
                                        temperature=0.3,
                                    )
                                    keywords_text = ai_response.choices[
                                        0
                                    ].message.content.strip()
                                    extracted_keywords = [
                                        k.strip()
                                        for k in keywords_text.split(",")
                                        if k.strip()
                                    ]
                                    if extracted_keywords:
                                        all_keywords.extend(extracted_keywords)
                                except Exception as e:
                                    logger.warning(f"⚠️ AI 키워드 추출 실패: {e}")
                                    # AI 실패 시 제목에서 간단한 키워드 추출
                                    words = title.lower().split()
                                    relevant_words = [
                                        w
                                        for w in words
                                        if len(w) > 4
                                        and w not in ["video", "shorts", "youtube"]
                                    ]
                                    if relevant_words:
                                        all_keywords.extend(relevant_words[:2])

            # 키워드 빈도 계산 및 상위 N개 선택
            keyword_counter = Counter(all_keywords)
            top_keywords = [
                keyword for keyword, count in keyword_counter.most_common(top_n)
            ]

            logger.info(
                f"✅ {season} 계절 트렌드 키워드 {len(top_keywords)}개 수집 완료"
            )
            return top_keywords

        except Exception as e:
            logger.warning(f"⚠️ {season} 계절 트렌드 키워드 수집 실패: {e}")
            return []

    def generate_seasonal_topics(
        self,
        season: str,
        keywords: List[str] = None,
        content_type: str = "hook",
        num_topics: int = 10,
        language: str = "en",
    ) -> List[str]:
        """
        계절별 트렌드 키워드를 기반으로 AI가 새로운 계절별 주제 생성

        Args:
            season: 계절 ('spring', 'summer', 'autumn', 'winter')
            keywords: 계절별 트렌드 키워드 리스트 (None이면 자동 수집)
            content_type: 콘텐츠 타입 ('hook', 'quote', 'story', 'fact', 'short_story')
            num_topics: 생성할 주제 수
            language: 언어 ('en' 또는 'ko', 기본값: 'en')

        Returns:
            생성된 계절별 주제 리스트
        """
        if not self.openai_client:
            logger.warning("⚠️ OpenAI API가 없어 계절별 주제 생성이 불가능합니다.")
            return []

        # 키워드가 없으면 자동 수집
        if not keywords:
            logger.info(f"📊 {season} 계절 트렌드 키워드 자동 수집 중...")
            keywords = self.collect_seasonal_trending_keywords(
                season=season, max_videos=30, min_views=5000, top_n=15
            )

        if not keywords:
            logger.warning(f"⚠️ {season} 계절 키워드가 없습니다.")
            return []

        try:
            # 계절별 프롬프트
            seasonal_prompts = {
                "spring": {
                    "en": "Create topics that are highly relevant to spring season (March-May), such as spring cleaning, tax season, spring financial planning, spring reset routines, and seasonal transitions.",
                    "ko": "봄 시즌(3-5월)과 매우 관련된 주제를 생성하세요. 예: 봄 정리, 세금 시즌, 봄 재무 계획, 봄 리셋 루틴, 계절 전환 등. **[중요] 반드시 한국의 문화적 맥락과 정서에 맞는 주제여야 합니다.**",
                },
                "summer": {
                    "en": "Create topics that are highly relevant to summer season (June-August), such as summer budget planning, vacation savings, summer side hustles, summer spending management, and seasonal financial strategies.",
                    "ko": "여름 시즌(6-8월)과 매우 관련된 주제를 생성하세요. 예: 여름 예산 계획, 휴가 저축, 여름 부업, 여름 지출 관리, 계절별 재무 전략 등. **[중요] 반드시 한국의 문화적 맥락과 정서에 맞는 주제여야 합니다.**",
                },
                "autumn": {
                    "en": "Create topics that are highly relevant to autumn/fall season (September-November), such as fall financial planning, holiday budget preparation, year-end tax strategies, autumn reset routines, Black Friday savings, and seasonal transitions.",
                    "ko": "가을 시즌(9-11월)과 매우 관련된 주제를 생성하세요. 예: 가을 재무 계획, 연말 예산 준비, 연말 세금 전략, 가을 리셋 루틴, 블랙프라이데이 저축, 계절 전환 등. **[중요] 반드시 한국의 문화적 맥락과 정서에 맞는 주제여야 합니다.**",
                },
                "winter": {
                    "en": "Create topics that are highly relevant to winter season (December-February), such as winter budget management, holiday spending, year-end financial review, winter heating costs, new year financial goals, and seasonal financial planning.",
                    "ko": "겨울 시즌(12-2월)과 매우 관련된 주제를 생성하세요. 예: 겨울 예산 관리, 연말 지출, 연말 재무 검토, 겨울 난방비, 새해 재무 목표, 계절별 재무 계획 등. **[중요] 반드시 한국의 문화적 맥락과 정서에 맞는 주제여야 합니다.**",
                },
            }

            season_prompt = seasonal_prompts.get(
                season.lower(), seasonal_prompts["spring"]
            )
            system_prompt = season_prompt.get(language, season_prompt["en"])

            # 콘텐츠 타입별 추가 프롬프트
            content_type_prompts = {
                "hook": {
                    "en": "Use the 'Mindset Flip' technique: state a common negative thought about this season and immediately reframe it positively.",
                    "ko": "'마인드셋 플립' 기법을 사용하세요: 이 계절에 대한 흔한 부정적 생각을 제시하고 즉시 긍정적으로 재해석하세요.",
                },
                "quote": {
                    "en": "Deliver powerful insights about finance, productivity, or self-improvement that are relevant to this season.",
                    "ko": "이 계절과 관련된 재태크, 생산성, 자기계발에 대한 강력한 인사이트를 전달하세요.",
                },
                "story": {
                    "en": "Tell stories about seasonal transitions, financial planning, or lifestyle changes that happen during this season.",
                    "ko": "이 계절에 일어나는 계절 전환, 재무 계획, 라이프스타일 변화에 대한 스토리를 전달하세요.",
                },
                "fact": {
                    "en": "Present shocking numbers, statistics, or 'did you know' facts about this season's financial trends, spending patterns, or seasonal habits.",
                    "ko": "이 계절의 재무 트렌드, 지출 패턴, 계절별 습관에 대한 충격적인 숫자, 통계, '알고 계셨나요' 팩트를 제시하세요.",
                },
                "short_story": {
                    "en": "Share personal narratives about seasonal changes, financial lessons learned during this season, or success stories related to seasonal planning.",
                    "ko": "계절 변화, 이 계절 동안 배운 재무 교훈, 계절별 계획과 관련된 성공 스토리에 대한 개인적 서술을 공유하세요.",
                },
            }

            content_prompt = content_type_prompts.get(
                content_type.lower(), content_type_prompts["hook"]
            )
            content_system_prompt = content_prompt.get(language, content_prompt["en"])

            combined_system_prompt = f"{system_prompt} {content_system_prompt}"

            keywords_text = ", ".join(keywords[:20])  # 최대 20개 키워드만 사용

            user_prompt = f"""Based on these {season} season trending keywords from popular YouTube Shorts: {keywords_text}

Generate {num_topics} new topic ideas for YouTube Shorts videos that:
1. Are highly relevant to {season} season (seasonal timing, events, trends)
2. Are related to finance, productivity, self-improvement, or lifestyle
3. Are engaging and click-worthy
4. Can be explained in about 55 seconds
5. Follow the {content_type} content style

**[CRITICAL] For Korean topics, they MUST be specific to Korean culture, trends, and sentiments. Avoid generic or translated topics. For example, instead of a generic topic about \'winter\', create a topic about Korea\'s specific winter culture like \'end-of-year gatherings\' or \'winter kimchi making (gimjang)\'.**

Return only the topics, one per line, without numbering or bullets. Each topic should be a complete sentence or phrase that can be used directly as a video title or topic."""

            if language == "ko":
                user_prompt = f"""다음은 인기 YouTube Shorts에서 수집한 {season} 계절 트렌드 키워드입니다: {keywords_text}

**자기계발 중심** {season} 계절과 관련된 YouTube Shorts 영상 주제 {num_topics}개를 생성하세요:
1. {season} 계절과 매우 관련되어야 함 (계절적 타이밍, 이벤트, 트렌드)
2. **자기계발, 생산성, 습관 형성, 목표 달성, 시간 관리, 동기부여, 성장 마인드셋**과 관련되어야 함
3. 매력적이고 클릭을 유도해야 함
4. 약 55초 분량으로 설명 가능해야 함
5. {content_type} 콘텐츠 스타일을 따름

**[매우 중요 - 절대 규칙] 한국어 주제는 반드시 한국의 문화, 정서, 사회적 맥락에 특화되어야 합니다. 다음을 반드시 포함하거나 참고하세요:**

**자기계발 중심 한국 특화 요소:**
- 한국 직장인의 계절별 자기계발: 새해 목표 설정, 봄 이직 준비, 여름 휴가 중 자기계발, 가을 습관 형성 등
- 한국 사회의 계절별 자기계발 문화: 
  * 겨울(12-2월): 새해 목표, 연말 회고, 겨울 독서 습관, 새벽 기상 루틴 등
  * 봄(3-5월): 봄 정리, 새 학기/새 직장 적응, 봄 운동 습관, 봄 목표 재설정 등
  * 여름(6-8월): 여름 방학 자기계발, 여름 독서, 여름 운동 루틴, 여름 습관 형성 등
  * 가을(9-11월): 가을 독서, 가을 운동, 연말 목표 점검, 가을 습관 개선 등
- 한국인만이 공감할 수 있는 자기계발 상황: 출근길 독서, 퇴근 후 자기계발, 주말 루틴, 새벽 기상 등

**절대 금지:**
- 재태크, 투자, 부동산, 주식, 금융 관련 주제 (완전히 제외)
- 돈 버는 방법, 수익 창출, 자산 관리 등 금융 관련 내용
- 일반적이거나 번역된 느낌의 주제
- 미국/캐나다 문화를 그대로 번역한 주제

번호나 불릿 없이 주제만 한 줄에 하나씩 반환하세요. 각 주제는 영상 제목이나 주제로 직접 사용할 수 있는 완전한 문장이나 구문이어야 합니다."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": combined_system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=500,
                temperature=0.8,
            )

            topics_text = response.choices[0].message.content.strip()

            # 주제 파싱 (줄바꿈으로 분리)
            topics = []
            for line in topics_text.split("\n"):
                line = line.strip()
                # 번호나 불릿 제거
                line = re.sub(r"^[\d\.\-\*\•\s]+", "", line)
                if line and len(line) > 10:  # 최소 10자 이상
                    topics.append(line)

            # 중복 제거
            unique_topics = list(dict.fromkeys(topics))  # 순서 유지하면서 중복 제거

            logger.info(
                f"✅ {season} 계절 AI 생성 주제 {len(unique_topics)}개 (목표: {num_topics}개)"
            )
            return unique_topics[:num_topics]

        except Exception as e:
            logger.warning(f"⚠️ {season} 계절 AI 주제 생성 실패: {e}")
            import traceback

            traceback.print_exc()
            return []

    def analyze_cpm_potential(self, text: str) -> float:
        """
        텍스트(주제 또는 키워드)의 CPM 잠재력 점수 계산

        Args:
            text: 분석할 텍스트

        Returns:
            CPM 점수 (기본값 1.0)
        """
        if not text:
            return 1.0

        text_lower = text.lower()
        score = 1.0

        # 키워드 매칭
        for keyword, weight in self.CPM_KEYWORDS.items():
            if keyword in text_lower:
                # 가장 높은 가중치 적용
                score = max(score, weight)

        return score

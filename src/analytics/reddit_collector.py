"""
Reddit 트렌드 키워드 수집 모듈
Reddit RSS 피드를 사용하여 인기 게시글을 분석하고 주제로 변환

Reddit RSS 피드 사용 (API 승인 불필요):
- 공개 RSS 피드 사용으로 API 승인 없이 접근 가능
- 읽기 전용 접근 (게시글만 읽고, 게시/댓글/투표 등은 하지 않음)
- 적절한 rate limiting (서브레딧당 제한된 수의 게시글만 요청)
- 캐싱을 통한 요청 최소화
"""

import os
import re
import time
import json
import xml.etree.ElementTree as ET
from typing import List, Dict
from datetime import datetime
from src.core.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import praw

    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class RedditCollector:
    """Reddit 트렌드 키워드 수집 클래스"""

    # 재태크/생산성 관련 서브레딧 목록
    FINANCE_SUBREDDITS = [
        "personalfinance",
        "investing",
        "FIREyFemmes",
        "FinancialPlanning",
        "wealth",
        "dividends",
        "stocks",
        "cryptocurrency",
    ]

    PRODUCTIVITY_SUBREDDITS = [
        "productivity",
        "getdisciplined",
        "getmotivated",
        "selfimprovement",
        "time management",
        "organization",
    ]

    LIFESTYLE_SUBREDDITS = [
        "minimalism",
        "declutter",
        "simpleliving",
        "homemaking",
        "organization",
    ]

    def __init__(self):
        """Reddit 수집기 초기화 (RSS 피드 사용, API 승인 불필요)"""
        self.reddit = None  # PRAW 클라이언트 (선택사항)
        self.openai_client = None
        self.last_request_time = {}  # Rate limiting을 위한 마지막 요청 시간 추적
        self.min_request_interval = 2.0  # 서브레딧당 최소 요청 간격 (초)
        self.use_rss = True  # RSS 피드 사용 (기본값)

        # PRAW API 초기화 (선택사항, RSS가 실패할 경우 대비)
        if PRAW_AVAILABLE:
            try:
                client_id = os.getenv("REDDIT_CLIENT_ID")
                client_secret = os.getenv("REDDIT_CLIENT_SECRET")
                user_agent = os.getenv(
                    "REDDIT_USER_AGENT",
                    "youtubeshorts-bot/1.0 (by /u/joohans) - topic collection for YouTube Shorts",
                )

                if client_id and client_secret:
                    self.reddit = praw.Reddit(
                        client_id=client_id,
                        client_secret=client_secret,
                        user_agent=user_agent,
                    )
                    self.use_rss = False  # API가 있으면 API 사용
                    logger.info("✅ Reddit API 클라이언트 초기화 완료 (PRAW 사용)")
                else:
                    logger.info(
                        "ℹ️ Reddit API 인증 정보가 없습니다. RSS 피드를 사용합니다 (승인 불필요)."
                    )
            except Exception as e:
                logger.warning(
                    f"⚠️ Reddit API 클라이언트 초기화 실패, RSS 피드 사용: {e}"
                )

        # OpenAI API 초기화 (주제 변환용)
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            try:
                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception as e:
                logger.warning(f"⚠️ OpenAI 클라이언트 초기화 실패: {e}")

        if self.use_rss:
            logger.info("✅ Reddit RSS 피드 모드 활성화 (API 승인 불필요)")

    def get_trending_posts_from_rss(
        self,
        subreddit_name: str,
        limit: int = 25,
        time_filter: str = "day",  # 'day', 'week', 'month', 'year', 'all'
    ) -> List[Dict]:
        """
        Reddit RSS 피드에서 인기 게시글 가져오기 (API 승인 불필요)

        Args:
            subreddit_name: 서브레딧 이름
            limit: 가져올 게시글 수
            time_filter: 시간 필터 ('day', 'week', 'month', 'year', 'all')

        Returns:
            인기 게시글 리스트 (제목, 점수, 댓글 수 등 포함)
        """
        if not REQUESTS_AVAILABLE:
            logger.warning(
                "⚠️ requests 라이브러리가 없어 RSS 피드를 사용할 수 없습니다."
            )
            return []

        # Rate limiting
        if subreddit_name in self.last_request_time:
            elapsed = time.time() - self.last_request_time[subreddit_name]
            if elapsed < self.min_request_interval:
                sleep_time = self.min_request_interval - elapsed
                time.sleep(sleep_time)

        try:
            # Reddit RSS 피드 URL
            # top 게시글: https://www.reddit.com/r/{subreddit}/top/.rss?t={time_filter}
            rss_url = (
                f"https://www.reddit.com/r/{subreddit_name}/top/.rss?t={time_filter}"
            )

            # User-Agent 설정 (Reddit이 봇을 차단하지 않도록)
            headers = {
                "User-Agent": "youtubeshorts-bot/1.0 (by /u/joohans) - topic collection for YouTube Shorts"
            }

            # RSS 피드 가져오기
            response = requests.get(rss_url, headers=headers, timeout=10)
            response.raise_for_status()

            # XML 파싱 (Reddit은 Atom 형식 사용)
            root = ET.fromstring(response.content)

            # Atom 네임스페이스
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            posts = []
            # Atom 형식에서는 <entry> 태그 사용
            entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")[
                :limit
            ]  # 최대 limit개만

            for entry in entries:
                # Atom 형식: <title>, <link href="...">, <published> 또는 <updated>
                title_elem = entry.find("{http://www.w3.org/2005/Atom}title")
                link_elem = entry.find("{http://www.w3.org/2005/Atom}link")
                published_elem = entry.find("{http://www.w3.org/2005/Atom}published")
                updated_elem = entry.find("{http://www.w3.org/2005/Atom}updated")

                if title_elem is not None:
                    title = title_elem.text or ""

                    # link는 href 속성 사용
                    link = ""
                    if link_elem is not None:
                        link = link_elem.get("href", "")

                    # published 또는 updated 날짜 파싱
                    pub_date = None
                    date_elem = (
                        published_elem if published_elem is not None else updated_elem
                    )
                    if date_elem is not None and date_elem.text:
                        try:
                            # ISO 8601 형식: 2025-11-29T05:24:15+00:00
                            pub_date = datetime.fromisoformat(
                                date_elem.text.replace("Z", "+00:00")
                            )
                        except:
                            try:
                                from email.utils import parsedate_to_datetime

                                pub_date = parsedate_to_datetime(date_elem.text)
                            except:
                                pass

                    # Reddit RSS는 점수와 댓글 수를 직접 제공하지 않으므로 기본값 사용
                    posts.append(
                        {
                            "title": title,
                            "score": 0,  # RSS에서는 점수 정보 없음
                            "num_comments": 0,  # RSS에서는 댓글 수 정보 없음
                            "created_utc": pub_date or datetime.now(),
                            "url": link,
                            "subreddit": subreddit_name,
                        }
                    )

            self.last_request_time[subreddit_name] = time.time()
            logger.info(
                f"✅ Reddit RSS '{subreddit_name}' 서브레딧에서 {len(posts)}개 게시글 수집"
            )
            return posts
        except Exception as e:
            logger.warning(f"⚠️ Reddit RSS 게시글 수집 실패 ({subreddit_name}): {e}")
            import traceback

            traceback.print_exc()
            return []

    def get_trending_posts(
        self,
        subreddit_name: str,
        limit: int = 25,
        time_filter: str = "day",  # 'hour', 'day', 'week', 'month', 'year', 'all'
    ) -> List[Dict]:
        """
        Reddit 인기 게시글 가져오기 (RSS 피드 또는 PRAW API 사용)

        Args:
            subreddit_name: 서브레딧 이름
            limit: 가져올 게시글 수
            time_filter: 시간 필터 ('hour', 'day', 'week', 'month', 'year', 'all')

        Returns:
            인기 게시글 리스트 (제목, 점수, 댓글 수 등 포함)
        """
        # RSS 피드 사용 (기본값, API 승인 불필요)
        if self.use_rss or not self.reddit:
            return self.get_trending_posts_from_rss(
                subreddit_name=subreddit_name, limit=limit, time_filter=time_filter
            )

        # PRAW API 사용 (API 승인 받은 경우)

        # Rate limiting: 같은 서브레딧에 대한 요청 간격 제어
        if subreddit_name in self.last_request_time:
            elapsed = time.time() - self.last_request_time[subreddit_name]
            if elapsed < self.min_request_interval:
                sleep_time = self.min_request_interval - elapsed
                time.sleep(sleep_time)

        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []

            # 인기 게시글 가져오기 (읽기 전용)
            # Reddit API 정책 준수: 적절한 제한 (최대 25개)
            actual_limit = min(limit, 25)  # Reddit API 제한 준수

            for post in subreddit.top(time_filter=time_filter, limit=actual_limit):
                posts.append(
                    {
                        "title": post.title,
                        "score": post.score,
                        "num_comments": post.num_comments,
                        "created_utc": datetime.fromtimestamp(post.created_utc),
                        "url": post.url,
                        "subreddit": subreddit_name,
                    }
                )

            # 마지막 요청 시간 업데이트
            self.last_request_time[subreddit_name] = time.time()

            logger.info(
                f"✅ Reddit '{subreddit_name}' 서브레딧에서 {len(posts)}개 게시글 수집 (읽기 전용)"
            )
            return posts
        except Exception as e:
            logger.warning(f"⚠️ Reddit 게시글 수집 실패 ({subreddit_name}): {e}")
            # Rate limiting 오류인 경우 추가 대기
            if "rate limit" in str(e).lower() or "429" in str(e):
                logger.info("   ⏳ Rate limit 도달, 60초 대기...")
                time.sleep(60)
            return []

    def get_trending_topics_from_multiple_subreddits(
        self,
        categories: List[str] = None,
        limit_per_subreddit: int = 10,
        time_filter: str = "day",
    ) -> List[Dict]:
        """
        여러 서브레딧에서 트렌드 주제 수집

        Args:
            categories: 카테고리 리스트 ('finance', 'productivity', 'lifestyle')
            limit_per_subreddit: 서브레딧당 가져올 게시글 수
            time_filter: 시간 필터

        Returns:
            트렌드 주제 리스트
        """
        if categories is None:
            categories = ["finance", "productivity", "lifestyle"]

        all_posts = []

        # 카테고리별 서브레딧 선택
        subreddits_to_check = []
        if "finance" in categories:
            subreddits_to_check.extend(self.FINANCE_SUBREDDITS[:3])  # 상위 3개만
        if "productivity" in categories:
            subreddits_to_check.extend(self.PRODUCTIVITY_SUBREDDITS[:3])
        if "lifestyle" in categories:
            subreddits_to_check.extend(self.LIFESTYLE_SUBREDDITS[:3])

        # 각 서브레딧에서 게시글 수집
        for subreddit_name in subreddits_to_check:
            posts = self.get_trending_posts(
                subreddit_name=subreddit_name,
                limit=limit_per_subreddit,
                time_filter=time_filter,
            )
            all_posts.extend(posts)

        # 점수와 댓글 수를 기준으로 정렬
        all_posts.sort(key=lambda x: x["score"] + x["num_comments"] * 2, reverse=True)

        logger.info(f"✅ 총 {len(all_posts)}개 Reddit 게시글 수집 완료")
        return all_posts

    def convert_posts_to_topics(
        self,
        posts: List[Dict],
        content_type: str = "hook",
        num_topics: int = 10,
        language: str = "en",
    ) -> List[str]:
        """
        Reddit 게시글 제목을 YouTube Shorts 주제로 변환

        Args:
            posts: Reddit 게시글 리스트
            content_type: 콘텐츠 타입 ('hook', 'quote', 'story', 'fact')
            num_topics: 생성할 주제 수
            language: 언어

        Returns:
            변환된 주제 리스트
        """
        if not self.openai_client:
            logger.warning(
                "⚠️ OpenAI API가 없어 Reddit 게시글을 주제로 변환할 수 없습니다."
            )
            # 간단한 필터링만 수행
            topics = []
            for post in posts[:num_topics]:
                title = post["title"]
                # 질문 형식이나 너무 긴 제목은 제외
                if not title.endswith("?") and len(title) < 100:
                    topics.append(title)
            return topics[:num_topics]

        try:
            # 상위 게시글 제목들을 프롬프트에 포함
            post_titles = [post["title"] for post in posts[:20]]  # 상위 20개만
            titles_text = "\n".join([f"- {title}" for title in post_titles])

            system_prompt = f"""You are an expert at creating engaging YouTube Shorts topics based on Reddit discussions.

Your task is to convert Reddit post titles into YouTube Shorts topics that are:
- Engaging and click-worthy
- Suitable for {content_type} content type
- 55-60 seconds long
- Related to finance, productivity, or lifestyle
- In {language} language

Return only the topics, one per line, without numbering or bullets."""

            user_prompt = f"""Based on these trending Reddit posts, generate {num_topics} YouTube Shorts topics:

{titles_text}

Requirements:
- Convert Reddit post titles into engaging YouTube Shorts topics
- Make them suitable for {content_type} content type
- Keep them relevant to finance, productivity, or lifestyle
- Each topic should be a complete sentence or phrase ready to use as a video title
- Make them compelling and click-worthy
- In {language} language

Return only the topics, one per line."""

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

            # 주제 파싱
            topics = []
            for line in topics_text.split("\n"):
                line = line.strip()
                # 번호나 불릿 제거
                line = re.sub(r"^[\d\.\-\*\•\s]+", "", line)
                if line and len(line) > 10:  # 최소 10자 이상
                    topics.append(line)

            # 중복 제거
            unique_topics = list(dict.fromkeys(topics))

            logger.info(f"✅ Reddit 게시글에서 {len(unique_topics)}개 주제 생성")
            return unique_topics[:num_topics]

        except Exception as e:
            logger.warning(f"⚠️ Reddit 게시글 주제 변환 실패: {e}")
            import traceback

            traceback.print_exc()
            return []

    def get_trending_topics(
        self,
        content_type: str = "hook",
        num_topics: int = 10,
        categories: List[str] = None,
        language: str = "en",
        use_cache: bool = True,
    ) -> List[str]:
        """
        Reddit 트렌드 주제 가져오기 (통합 메서드, 캐싱 지원)

        Args:
            content_type: 콘텐츠 타입
            num_topics: 생성할 주제 수
            categories: 카테고리 리스트
            language: 언어
            use_cache: 캐시 사용 여부 (Reddit API 호출 최소화)

        Returns:
            트렌드 주제 리스트
        """
        # 캐시 확인 (Reddit API 호출 최소화)
        if use_cache:
            cache_file = os.path.join(
                settings.TEMP_DIR, f"reddit_topics_cache_{content_type}_{language}.json"
            )
            cache_duration = 6 * 3600  # 6시간 캐시 (Reddit API 정책 준수)

            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        cache_data = json.load(f)
                        cache_time = cache_data.get("timestamp", 0)
                        if time.time() - cache_time < cache_duration:
                            topics = cache_data.get("topics", [])
                            if topics:
                                logger.info(
                                    f"📊 캐시된 Reddit 주제 {len(topics)}개 사용 (API 호출 생략)"
                                )
                                return topics[:num_topics]
                except Exception as e:
                    logger.warning(f"⚠️ 캐시 읽기 실패: {e}")

        # Reddit 게시글 수집
        posts = self.get_trending_topics_from_multiple_subreddits(
            categories=categories,
            limit_per_subreddit=10,  # 적절한 제한 (Reddit API 정책 준수)
            time_filter="day",
        )

        if not posts:
            return []

        # 주제로 변환
        topics = self.convert_posts_to_topics(
            posts=posts,
            content_type=content_type,
            num_topics=num_topics,
            language=language,
        )

        # 캐시 저장
        if use_cache and topics:
            try:
                os.makedirs(settings.TEMP_DIR, exist_ok=True)
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(
                        {"timestamp": time.time(), "topics": topics},
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )
            except Exception as e:
                logger.warning(f"⚠️ 캐시 저장 실패: {e}")

        return topics

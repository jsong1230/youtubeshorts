from typing import Dict, Any
from datetime import datetime, timedelta
from src.utils.youtube_auth import get_authenticated_service
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AnalyticsManager:
    """YouTube Shorts 성과 분석 관리 클래스"""

    def __init__(self):
        self.youtube = get_authenticated_service()

    def fetch_channel_stats(self):
        """채널 전체 통계 조회"""
        if not self.youtube:
            logger.warning("⚠️ YouTube API 서비스가 초기화되지 않았습니다.")
            return None

        try:
            request = self.youtube.channels().list(part="statistics,snippet", mine=True)
            response = request.execute()

            if response["items"]:
                channel = response["items"][0]
                stats = channel["statistics"]
                snippet = channel["snippet"]

                return {
                    "title": snippet["title"],
                    "view_count": int(stats["viewCount"]),
                    "subscriber_count": int(stats["subscriberCount"]),
                    "video_count": int(stats["videoCount"]),
                }
            return None
        except Exception as e:
            logger.error(f"❌ 채널 통계 조회 실패: {e}")
            return None

    def get_recent_shorts_stats(self, max_results=10):
        """
        최근 업로드된 Shorts 영상 통계 조회
        Search API 대신 videos.db에서 가져오기 (quota 절약)
        """
        if not self.youtube:
            return []

        try:
            # 1. videos.db에서 최근 영상 목록 가져오기 (우선)
            videos = []
            video_ids = []

            try:
                import sqlite3
                from pathlib import Path

                db_path = Path("data/videos.db")
                if db_path.exists():
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()

                    cursor.execute(
                        """
                        SELECT video_id, title, upload_date, topic
                        FROM videos
                        ORDER BY upload_date DESC
                        LIMIT ?
                        """,
                        (max_results,),
                    )

                    rows = cursor.fetchall()
                    for row in rows:
                        video_id, title, upload_date, topic = row
                        if video_id:
                            video_ids.append(video_id)
                            videos.append(
                                {
                                    "id": video_id,
                                    "title": title or "",
                                    "published_at": upload_date or "",
                                    "topic": topic or "",
                                }
                            )

                    conn.close()

                    if video_ids:
                        logger.debug(
                            f"💾 videos.db에서 {len(video_ids)}개 영상 정보 가져옴 (Search API 미사용)"
                        )
            except Exception as e:
                logger.debug(f"⚠️ videos.db 읽기 실패: {e}")

            # 2. Search API는 최후의 수단으로만 사용 (로컬 데이터가 없을 때만)
            if not video_ids:
                logger.warning("⚠️ 로컬 데이터가 없어 Search API 사용 (quota 소모)")
                request = self.youtube.search().list(
                    part="snippet",
                    forMine=True,
                    type="video",
                    maxResults=max_results,
                    order="date",
                )
                response = request.execute()

                for item in response.get("items", []):
                    video_id = item["id"]["videoId"]
                    video_ids.append(video_id)
                    videos.append(
                        {
                            "id": video_id,
                            "title": item["snippet"]["title"],
                            "published_at": item["snippet"]["publishedAt"],
                            "topic": item["snippet"]
                            .get("title", "")
                            .replace(" #Shorts", "")
                            .replace("#Shorts", "")
                            .strip(),
                        }
                    )

            if not video_ids:
                return []

            # 3. 각 영상의 상세 통계 조회 (배치 처리) - 이건 videos().list() 사용 (quota 적음)
            stats_request = self.youtube.videos().list(
                part="statistics,contentDetails", id=",".join(video_ids)
            )
            stats_response = stats_request.execute()

            # 4. 데이터 병합
            stats_map = {item["id"]: item for item in stats_response["items"]}

            results = []
            for video in videos:
                vid = video["id"]
                if vid in stats_map:
                    stats = stats_map[vid]["statistics"]
                    # content_details = stats_map[vid]["contentDetails"]

                    # Shorts 여부 확인 (duration이 60초 이하)
                    # duration_iso = content_details["duration"]
                    # 간단한 체크 (정확한 파싱은 isodate 라이브러리 필요하지만 여기선 생략)
                    # PT1M, PT59S 등으로 표시됨

                    video["stats"] = {
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)),
                        "comments": int(stats.get("commentCount", 0)),
                    }

                    # 참여율 계산 (좋아요/조회수)
                    if video["stats"]["views"] > 0:
                        video["stats"]["engagement_rate"] = (
                            (video["stats"]["likes"] + video["stats"]["comments"])
                            / video["stats"]["views"]
                            * 100
                        )
                    else:
                        video["stats"]["engagement_rate"] = 0.0

                    results.append(video)

            return results

        except Exception as e:
            logger.error(f"❌ 영상 통계 조회 실패: {e}")
            return []

    def _extract_topic(self, title):
        """영상 제목에서 주제 추출"""
        import re

        # 1. 대괄호 [Topic] 형식 확인
        match = re.search(r"\[(.*?)\]", title)
        if match:
            return match.group(1).strip()

        # 2. 주요 키워드 확인
        keywords = {
            "Money": [
                "money",
                "finance",
                "rich",
                "wealth",
                "invest",
                "cash",
                "dollar",
                "돈",
                "부자",
                "투자",
                "금융",
            ],
            "Motivation": [
                "motivation",
                "mindset",
                "dream",
                "passion",
                "courage",
                "동기부여",
                "마인드셋",
                "성공",
                "꿈",
            ],
            "Productivity": [
                "productivity",
                "habit",
                "focus",
                "time",
                "routine",
                "생산성",
                "습관",
                "집중",
                "시간",
                "루틴",
            ],
            "Health": [
                "health",
                "fitness",
                "diet",
                "workout",
                "exercise",
                "건강",
                "운동",
                "다이어트",
            ],
            "Tech": ["tech", "ai", "gpt", "robot", "future", "기술", "인공지능"],
            "Life": [
                "life",
                "love",
                "friend",
                "family",
                "relationship",
                "인생",
                "사랑",
                "친구",
                "가족",
            ],
        }

        title_lower = title.lower()
        for topic, tags in keywords.items():
            if any(tag in title_lower for tag in tags):
                return topic

        return "General"

    def analyze_topic_performance(self, videos):
        """주제별 성과 분석"""
        from collections import defaultdict

        topic_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "views": 0,
                "likes": 0,
                "comments": 0,
                "engagement_sum": 0.0,
            }
        )

        for video in videos:
            topic = self._extract_topic(video["title"])
            stats = video["stats"]

            t_stat = topic_stats[topic]
            t_stat["count"] += 1
            t_stat["views"] += stats["views"]
            t_stat["likes"] += stats["likes"]
            t_stat["comments"] += stats["comments"]
            t_stat["engagement_sum"] += stats["engagement_rate"]

        # 평균 계산
        results = []
        for topic, stats in topic_stats.items():
            count = stats["count"]
            if count > 0:
                results.append(
                    {
                        "topic": topic,
                        "count": count,
                        "avg_views": stats["views"] / count,
                        "avg_likes": stats["likes"] / count,
                        "avg_engagement": stats["engagement_sum"] / count,
                    }
                )

        # 성과(평균 조회수) 순으로 정렬
        results.sort(key=lambda x: x["avg_views"], reverse=True)
        return results

    def analyze_upload_time_performance(self, videos):
        """업로드 시간대별 성과 분석"""
        from collections import defaultdict

        hour_stats: Dict[int, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "views": 0, "likes": 0, "engagement_sum": 0.0}
        )

        for video in videos:
            # published_at: "2025-11-20T14:30:00Z" 형식
            pub_time = datetime.strptime(video["published_at"], "%Y-%m-%dT%H:%M:%SZ")
            # UTC 시간을 한국 시간(KST, UTC+9)으로 변환
            kst_time = pub_time + timedelta(hours=9)
            hour = kst_time.hour

            stats = video["stats"]
            h_stat = hour_stats[hour]
            h_stat["count"] += 1
            h_stat["views"] += stats["views"]
            h_stat["likes"] += stats["likes"]
            h_stat["engagement_sum"] += stats["engagement_rate"]

        # 평균 계산
        results = []
        for hour, stats in hour_stats.items():
            count = stats["count"]
            if count > 0:
                results.append(
                    {
                        "hour": hour,
                        "count": count,
                        "avg_views": stats["views"] / count,
                        "avg_likes": stats["likes"] / count,
                        "avg_engagement": stats["engagement_sum"] / count,
                    }
                )

        # 시간 순으로 정렬
        results.sort(key=lambda x: x["hour"])
        return results

    def generate_performance_report(self):
        """성과 분석 리포트 생성 및 출력"""
        logger.info("\n📊 YouTube Shorts 성과 분석 리포트")
        logger.info("=" * 50)

        # 1. 채널 통계
        channel_stats = self.fetch_channel_stats()
        if channel_stats:
            logger.info(f"📺 채널: {channel_stats['title']}")
            logger.info(f"   구독자: {channel_stats['subscriber_count']:,}명")
            logger.info(f"   총 조회수: {channel_stats['view_count']:,}회")
            logger.info(f"   총 영상 수: {channel_stats['video_count']:,}개")
        logger.info("-" * 50)

        # 2. 최근 영상 성과 (더 많은 데이터 분석을 위해 30개 조회)
        recent_videos = self.get_recent_shorts_stats(max_results=30)

        logger.info(f"📈 최근 업로드 영상 성과 (최근 {len(recent_videos)}개 분석)")

        if not recent_videos:
            logger.info("   최근 업로드된 영상이 없습니다.")
        else:
            # 상위 5개만 출력
            top_videos = sorted(
                recent_videos, key=lambda x: x["stats"]["views"], reverse=True
            )[:5]

            logger.info("\n   🏆 Top 5 인기 영상:")
            for i, video in enumerate(top_videos):
                title = video["title"]
                if len(title) > 40:
                    title = title[:37] + "..."

                stats = video["stats"]
                pub_date = datetime.strptime(
                    video["published_at"], "%Y-%m-%dT%H:%M:%SZ"
                ).strftime("%Y-%m-%d")

                logger.info(f"   {i+1}. [{pub_date}] {title}")
                logger.info(
                    f"      👁️ {stats['views']:,} | ❤️ {stats['likes']:,} | 🔥 {stats['engagement_rate']:.2f}%"
                )

            logger.info("-" * 50)

            # 3. 주제별 성과 분석
            logger.info("🧠 주제별 성과 분석")
            topic_results = self.analyze_topic_performance(recent_videos)

            logger.info(
                f"\n   {'주제':<15} | {'영상수':<5} | {'평균조회수':<10} | {'평균참여율':<10}"
            )
            logger.info(f"   {'-'*15}-+-{'-'*5}-+-{'-'*10}-+-{'-'*10}")

            for res in topic_results:
                logger.info(
                    f"   {res['topic']:<15} | {res['count']:<5} | {res['avg_views']:<10.1f} | {res['avg_engagement']:<9.2f}%"
                )

            logger.info("-" * 50)

            # 4. 인사이트 및 추천
            if topic_results:
                best_topic = topic_results[0]
                logger.info("💡 AI 인사이트:")
                logger.info(
                    f"   - 현재 가장 성과가 좋은 주제는 '{best_topic['topic']}' 입니다."
                )
                logger.info(
                    f"     (평균 조회수 {best_topic['avg_views']:.1f}회, 참여율 {best_topic['avg_engagement']:.2f}%)"
                )

                if len(topic_results) > 1:
                    worst_topic = topic_results[-1]
                    if worst_topic["count"] >= 2:  # 데이터가 좀 쌓인 경우에만 조언
                        logger.info(
                            f"   - '{worst_topic['topic']}' 주제는 성과가 저조합니다. 접근 방식을 바꾸거나 비중을 줄이세요."
                        )

                # 참여율이 높은 주제 찾기 (조회수 1등과 다를 수 있음)
                most_engaging = max(topic_results, key=lambda x: x["avg_engagement"])
                if most_engaging["topic"] != best_topic["topic"]:
                    logger.info(
                        f"   - '{most_engaging['topic']}' 주제는 조회수 대비 참여율이 가장 높습니다 ({most_engaging['avg_engagement']:.2f}%)."
                    )
                    logger.info(
                        "     이 주제는 충성도 높은 시청자를 모으기에 좋습니다."
                    )

            logger.info("-" * 50)

            # 5. 업로드 시간대별 분석
            logger.info("⏰ 업로드 시간대별 성과 분석 (KST 기준)")
            time_results = self.analyze_upload_time_performance(recent_videos)

            if len(time_results) >= 3:  # 최소 3개 이상의 시간대 데이터가 있을 때만 분석
                logger.info(
                    f"\n   {'시간':<10} | {'영상수':<5} | {'평균조회수':<10} | {'평균참여율':<10}"
                )
                logger.info(f"   {'-'*10}-+-{'-'*5}-+-{'-'*10}-+-{'-'*10}")

                for res in time_results:
                    hour_str = f"{res['hour']:02d}:00"
                    logger.info(
                        f"   {hour_str:<10} | {res['count']:<5} | {res['avg_views']:<10.1f} | {res['avg_engagement']:<9.2f}%"
                    )

                logger.info("\n   💡 업로드 시간 인사이트:")

                # 조회수 기준 최고 시간대
                best_time = max(time_results, key=lambda x: x["avg_views"])
                logger.info(
                    f"   - 가장 성과가 좋은 시간대는 {best_time['hour']:02d}:00 입니다."
                )
                logger.info(
                    f"     (평균 조회수 {best_time['avg_views']:.1f}회, 참여율 {best_time['avg_engagement']:.2f}%)"
                )

                # 데이터가 한 시간대에 집중되어 있는지 확인
                total_videos = sum(r["count"] for r in time_results)
                max_concentration = max(r["count"] for r in time_results)
                if (
                    max_concentration / total_videos > 0.7
                ):  # 70% 이상이 한 시간대에 집중
                    logger.info(
                        "   - ⚠️ 대부분의 영상이 같은 시간대에 업로드되었습니다."
                    )
                    logger.info(
                        "     다양한 시간대에 업로드를 시도해보면 더 정확한 분석이 가능합니다."
                    )
            else:
                logger.info(
                    "\n   ⚠️ 업로드 시간대 데이터가 부족합니다. 다양한 시간에 업로드를 시도해보세요."
                )

        logger.info("=" * 50)

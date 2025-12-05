"""
댓글 기반 다음 주제 제안 시스템
YouTube 댓글을 분석하여 다음 영상 주제를 제안
"""

from datetime import datetime
from typing import List, Dict, Optional
from src.uploaders.youtube_uploader import YouTubeUploader
from src.generators.user_request_handler import UserRequestHandler
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CommentAnalyzer:
    """댓글 분석 클래스"""

    def __init__(self):
        self.uploader = YouTubeUploader()
        self.request_handler = UserRequestHandler()

    def analyze_video_comments(self, video_id: str, max_comments: int = 100) -> Dict:
        """
        영상 댓글 분석

        Args:
            video_id: YouTube 영상 ID
            max_comments: 분석할 최대 댓글 수

        Returns:
            분석된 댓글 리스트 (주제 제안 포함)
        """
        try:
            # YouTube API로 댓글 가져오기
            comments = self._fetch_comments(video_id, max_comments)

            # 댓글에서 주제 제안 추출
            topic_suggestions = self._extract_topic_suggestions(comments)

            return {
                "video_id": video_id,
                "total_comments": len(comments),
                "topic_suggestions": topic_suggestions,
                "analyzed_at": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.warning(f"⚠️ 댓글 분석 실패: {e}")
            return {}

    def _fetch_comments(self, video_id: str, max_comments: int) -> List[Dict]:
        """YouTube API로 댓글 가져오기"""
        try:
            youtube = self.uploader.youtube
            if not youtube:
                return []

            comments: List[Dict] = []
            next_page_token = None

            while len(comments) < max_comments:
                request = youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=min(100, max_comments - len(comments)),
                    pageToken=next_page_token,
                    order="relevance",
                )
                response = request.execute()

                for item in response.get("items", []):
                    comment = item["snippet"]["topLevelComment"]["snippet"]
                    comments.append(
                        {
                            "id": item["id"],
                            "author": comment.get("authorDisplayName", ""),
                            "text": comment.get("textDisplay", ""),
                            "like_count": comment.get("likeCount", 0),
                            "published_at": comment.get("publishedAt", ""),
                            "updated_at": comment.get("updatedAt", ""),
                        }
                    )

                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break

            return comments[:max_comments]
        except Exception as e:
            logger.warning(f"⚠️ 댓글 가져오기 실패: {e}")
            return []

    def _extract_topic_suggestions(self, comments: List[Dict]) -> List[Dict]:
        """댓글에서 주제 제안 추출"""
        try:
            # 키워드 패턴 (주제 제안을 나타내는 패턴)
            suggestion_patterns = [
                "can you make",
                "can you do",
                "please make",
                "please do",
                "would love to see",
                "want to see",
                "next video",
                "should make",
                "should do",
                "how about",
                "what about",
                "suggest",
                "recommend",
                "topic",
                "idea",
            ]

            suggestions = []

            for comment in comments:
                text_lower = comment["text"].lower()

                # 제안 패턴이 포함된 댓글 찾기
                for pattern in suggestion_patterns:
                    if pattern in text_lower:
                        # 주제 추출 (간단한 휴리스틱)
                        topic = self._extract_topic_from_comment(comment["text"])
                        if topic:
                            suggestions.append(
                                {
                                    "topic": topic,
                                    "source": "comment",
                                    "source_id": comment["id"],
                                    "author": comment["author"],
                                    "like_count": comment["like_count"],
                                    "comment_text": comment["text"],
                                    "priority": min(
                                        10, 5 + comment["like_count"] // 10
                                    ),  # 좋아요 수에 따라 우선순위 조정
                                }
                            )
                        break

            # 우선순위 순으로 정렬
            suggestions.sort(key=lambda x: x["priority"], reverse=True)

            # 사용자 요청에 추가
            for suggestion in suggestions:
                self.request_handler.add_request(
                    topic=suggestion["topic"],
                    source="comment",
                    source_id=suggestion["source_id"],
                    priority=suggestion["priority"],
                    requested_by=suggestion["author"],
                    notes=f"댓글: {suggestion['comment_text'][:100]}",
                )

            return suggestions
        except Exception as e:
            logger.warning(f"⚠️ 주제 제안 추출 실패: {e}")
            return []

    def _extract_topic_from_comment(self, comment_text: str) -> Optional[str]:
        """댓글 텍스트에서 주제 추출"""
        try:
            # 간단한 휴리스틱으로 주제 추출
            # 실제로는 AI를 사용하여 더 정확하게 추출 가능

            # 제안 패턴 제거
            text = comment_text.lower()
            patterns_to_remove = [
                "can you make a video about",
                "can you do a video about",
                "please make a video about",
                "please do a video about",
                "would love to see a video about",
                "want to see a video about",
                "next video should be about",
                "should make a video about",
                "should do a video about",
                "how about",
                "what about",
                "suggest",
                "recommend",
                "topic",
                "idea",
            ]

            for pattern in patterns_to_remove:
                if pattern in text:
                    # 패턴 이후의 텍스트 추출
                    idx = text.find(pattern)
                    topic = comment_text[idx + len(pattern) :].strip()
                    # 문장 부호 제거
                    topic = topic.rstrip(".,!?")
                    # 첫 100자만
                    topic = topic[:100].strip()
                    if topic and len(topic) > 5:
                        return topic

            return None
        except Exception as e:
            logger.warning(f"⚠️ 주제 추출 실패: {e}")
            return None

    def analyze_recent_videos_comments(
        self, num_videos: int = 10, max_comments_per_video: int = 50
    ) -> Dict:
        """
        최근 영상들의 댓글 분석

        Args:
            num_videos: 분석할 영상 수
            max_comments_per_video: 영상당 최대 댓글 수

        Returns:
            분석 결과
        """
        try:
            # 최근 영상 목록 가져오기
            from src.pipeline.database import VideoDatabase

            video_db = VideoDatabase()
            videos = video_db.get_all_videos(limit=num_videos, order_by="upload_date")

            all_suggestions = []

            for video in videos:
                video_id = video.get("video_id")
                if video_id:
                    result = self.analyze_video_comments(
                        video_id, max_comments_per_video
                    )
                    if result.get("topic_suggestions"):
                        all_suggestions.extend(result["topic_suggestions"])

            return {
                "total_videos_analyzed": len(videos),
                "total_suggestions": len(all_suggestions),
                "suggestions": all_suggestions,
                "analyzed_at": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.warning(f"⚠️ 최근 영상 댓글 분석 실패: {e}")
            return {}

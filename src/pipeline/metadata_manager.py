from datetime import datetime
from typing import Optional, Dict, Any
from src.core.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MetadataManager:
    """Handles generation of video metadata (title, description, tags)."""

    def generate_title(self, topic: str, actual_topic: str = None) -> str:
        """Generates a video title."""
        if actual_topic:
            title = actual_topic
        elif topic:
            title = topic
        else:
            title = datetime.now().strftime("%Y년 %m월 %d일")

        # Add #Shorts if not present
        if "#Shorts" not in title and "#shorts" not in title:
            title = f"{title} #Shorts"

        return title

    def generate_description(
        self,
        language: str,
        original_topic: str,
        actual_topic: str,
        channel_info: Optional[Dict[str, Any]] = None,
        recent_videos: list = None,
    ) -> str:
        """Generates the video description."""
        if language == "en":
            return self._generate_english_description(
                original_topic, channel_info, recent_videos
            )
        else:
            return self._generate_korean_description(
                original_topic, channel_info, recent_videos
            )

    def _generate_english_description(
        self,
        original_topic: str,
        channel_info: Optional[Dict[str, Any]],
        recent_videos: list,
    ) -> str:
        description = f"{settings.DEFAULT_DESCRIPTION}\n\n"
        description += (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        description += "📺 Video Information\n"
        description += (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        description += f"📅 Upload Date: {datetime.now().strftime('%B %d, %Y')}\n"
        if original_topic:
            description += f"📌 Topic: {original_topic}\n"
        description += "⏱️ Duration: ~55 seconds (YouTube Shorts optimized)\n\n"

        description += (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        description += "💡 About This Video\n"
        description += (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        description += (
            "This video was automatically generated using the latest AI technology.\n"
        )
        description += "We provide useful information and practical tips on new topics every day.\n"
        description += "We will continue to upload diverse content that helps improve your daily life.\n\n"

        # Subscribe section
        description += (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        description += "🔔 SUBSCRIBE NOW - Don't Miss Daily Content!\n"
        description += (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        if channel_info and channel_info.get("channel_url"):
            description += f"👉 Subscribe here: {channel_info['channel_url']}\n\n"
        description += "Why subscribe?\n"
        description += "✅ Daily new videos with practical tips\n"
        description += "✅ Finance, productivity, and lifestyle content\n"
        description += "✅ Short, actionable advice (under 1 minute)\n"
        description += "✅ AI-powered insights you can use today\n\n"

        description += (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        description += "🙏 Your Engagement Matters\n"
        description += (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        description += (
            "👍 LIKE: If this video helped you, please hit the like button!\n"
        )
        description += "🔔 SUBSCRIBE: Get notified when we upload new videos daily!\n"
        description += (
            "💬 COMMENT: Share your thoughts or suggest topics you'd like to see!\n"
        )
        description += "📤 SHARE: Help others discover this content by sharing!\n\n"

        # Recent videos
        if recent_videos:
            description += (
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
            description += "📚 More Videos You Might Like\n"
            description += (
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
            for i, video in enumerate(recent_videos[:3], 1):
                description += f"{i}. {video['title']}\n"
                description += f"   👉 {video['url']}\n\n"

        return description

    def _generate_korean_description(
        self,
        original_topic: str,
        channel_info: Optional[Dict[str, Any]],
        recent_videos: list,
    ) -> str:
        description = f"{settings.DEFAULT_DESCRIPTION}\n\n"
        description += (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        description += "📺 영상 정보\n"
        description += (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        description += f"📅 업로드 날짜: {datetime.now().strftime('%Y년 %m월 %d일')}\n"
        if original_topic:
            description += f"📌 영상 주제: {original_topic}\n"
        description += "⏱️ 영상 길이: 약 55초 (YouTube Shorts 최적화)\n\n"

        description += (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        description += "💡 이 영상에 대해\n"
        description += (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        description += "이 영상은 최신 AI 기술을 활용하여 자동으로 생성되었습니다.\n"
        description += "매일 새로운 주제로 유용한 정보와 실용적인 팁을 제공합니다.\n"
        description += (
            "생활에 도움이 되는 다양한 콘텐츠를 지속적으로 업로드할 예정입니다.\n\n"
        )

        # Subscribe section
        description += (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        description += "🔔 지금 구독하세요 - 매일 새로운 콘텐츠를 놓치지 마세요!\n"
        description += (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        if channel_info and channel_info.get("channel_url"):
            description += f"👉 구독하기: {channel_info['channel_url']}\n\n"
        description += "구독하면 좋은 이유:\n"
        description += "✅ 매일 새로운 실용적인 팁 영상\n"
        description += "✅ 재태크, 생산성, 라이프스타일 콘텐츠\n"
        description += "✅ 짧고 실행 가능한 조언 (1분 이내)\n"
        description += "✅ 오늘 바로 써먹을 수 있는 AI 인사이트\n\n"

        description += (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        description += "🙏 여러분의 참여를 기다립니다\n"
        description += (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        description += "👍 좋아요: 영상이 도움이 되셨다면 좋아요를 눌러주세요!\n"
        description += "🔔 구독: 매일 새로운 영상을 받아보시려면 구독해주세요!\n"
        description += (
            "💬 댓글: 궁금한 점이나 원하시는 주제가 있으시면 댓글로 알려주세요!\n"
        )
        description += "📤 공유: 친구들과 함께 보시면 더욱 좋습니다!\n\n"

        # Recent videos
        if recent_videos:
            description += (
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
            description += "📚 함께 보면 좋은 영상\n"
            description += (
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
            for i, video in enumerate(recent_videos[:3], 1):
                description += f"{i}. {video['title']}\n"
                description += f"   👉 {video['url']}\n\n"

        return description

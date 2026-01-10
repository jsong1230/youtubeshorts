"""
Tests for bot pipeline system (ShortsBot)
"""

import pytest
from unittest.mock import Mock, patch

from src.pipeline.bot import ShortsBot


class TestShortsBot:
    """Test ShortsBot class"""

    @pytest.fixture
    def bot(self, tmp_path, monkeypatch):
        """Create a ShortsBot instance with mocked dependencies"""
        from contextlib import ExitStack

        with ExitStack() as stack:
            stack.enter_context(patch("src.pipeline.bot.AIVideoGenerator"))
            stack.enter_context(patch("src.pipeline.bot.YouTubeUploader"))
            stack.enter_context(patch("src.pipeline.bot.MonetizationTracker"))
            stack.enter_context(patch("src.pipeline.bot.VideoDatabase"))
            stack.enter_context(patch("src.pipeline.bot.SyncManager"))
            stack.enter_context(patch("src.pipeline.bot.ABTestDatabase"))
            stack.enter_context(patch("src.pipeline.bot.TopicDatabase"))
            stack.enter_context(patch("src.pipeline.bot.ThumbnailOptimizer"))
            stack.enter_context(patch("src.pipeline.bot.PerformancePredictor"))
            stack.enter_context(patch("src.pipeline.bot.AutoOptimizer"))
            stack.enter_context(patch("src.pipeline.bot.CompetitorAnalyzer"))
            stack.enter_context(patch("src.pipeline.bot.AudienceSegmentAnalyzer"))
            stack.enter_context(patch("src.pipeline.bot.NotificationService"))
            stack.enter_context(patch("src.pipeline.bot.SeriesGenerator"))
            stack.enter_context(patch("src.pipeline.bot.UserRequestHandler"))
            stack.enter_context(patch("src.pipeline.bot.CommentAnalyzer"))
            stack.enter_context(patch("src.pipeline.bot.VideoPipeline"))
            stack.enter_context(patch("config.ENABLE_TIKTOK_UPLOAD", False))
            stack.enter_context(patch("config.ENABLE_INSTAGRAM_UPLOAD", False))
            stack.enter_context(
                patch("config.DATABASE_PATH", str(tmp_path / "videos.db"))
            )
            stack.enter_context(patch("config.UPLOAD_TIMEZONE", "Asia/Seoul"))

            bot_instance = ShortsBot()
            bot_instance.pipeline = Mock()  # Mock the pipeline instance

            yield bot_instance

    def test_init(self, bot):
        """Test bot initialization"""
        assert bot.video_generator is not None
        assert bot.uploader is not None
        assert bot.monetization is not None
        assert bot.database is not None
        assert bot.sync_manager is not None
        assert bot.use_multi_platform is False

    def test_create_video_only(self, bot, tmp_path):
        """Test creating video only (no upload)"""
        video_path = str(tmp_path / "test_video.mp4")
        thumbnail_path = str(tmp_path / "test_thumbnail.jpg")

        bot.video_generator.generate_video = Mock(
            return_value=(video_path, thumbnail_path, "Test Topic", ["Script"])
        )

        # Mock metadata manager in pipeline if used, or just mock pipeline attributes if needed
        # create_video_only uses self.pipeline.metadata_manager
        bot.pipeline.metadata_manager.generate_description = Mock(return_value="Desc")

        # Mock 중복 주제 체크를 건너뛰기 위해 ChannelHistoryCollector 모킹
        # 실제 import 경로는 함수 내부에서 이루어지므로 해당 경로를 모킹
        with patch("config.VIDEO_OUTPUT_DIR", str(tmp_path)), patch(
            "src.analytics.channel_history_collector.ChannelHistoryCollector"
        ) as mock_collector_class:
            # 중복 체크가 항상 통과하도록 설정
            mock_collector = Mock()
            mock_collector.get_existing_topics.return_value = (
                []
            )  # 빈 리스트 반환 (중복 없음)
            mock_collector.check_topic_similarity.return_value = (
                False,
                None,
            )  # 중복 아님
            mock_collector_class.return_value = mock_collector

            result = bot.create_video_only(topic="Test Topic")

        assert result == video_path
        bot.video_generator.generate_video.assert_called_once()

    def test_create_and_upload_delegation(self, bot):
        """Test create_and_upload delegates to pipeline"""
        bot.create_and_upload(topic="Test Topic", auto_upload=True)

        bot.pipeline.run.assert_called_once_with(
            topic="Test Topic",
            content_type=None,
            force=False,
            language=None,
            auto_upload=True,
        )

    def test_update_all_stats(self, bot):
        """Test updating all statistics"""
        bot.monetization.update_all_videos = Mock()
        bot.database.get_all_videos = Mock(
            return_value=[{"video_id": "test_1"}, {"video_id": "test_2"}]
        )
        bot.uploader.get_video_stats = Mock(
            side_effect=[{"views": 1000}, {"views": 2000}]
        )
        bot.database.update_video_stats = Mock()
        bot.ab_test_db.update_test_stats = Mock()

        bot.update_all_stats()

        bot.monetization.update_all_videos.assert_called_once()
        assert bot.database.update_video_stats.call_count == 2
        assert bot.ab_test_db.update_test_stats.call_count == 2

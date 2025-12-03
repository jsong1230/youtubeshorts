import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.pipeline.bot import ShortsBot
from src.generators.content_type import ContentType
from src.pipeline.video_pipeline import VideoPipeline

class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_video_generator = MagicMock()
        self.mock_uploader = MagicMock()
        self.mock_database = MagicMock()
        self.mock_sync_manager = MagicMock()
        self.mock_user_request_handler = MagicMock()
        self.mock_notification_service = MagicMock()
        self.mock_monetization = MagicMock()
        
        # Setup default return values
        self.mock_video_generator.generate_video.return_value = (
            "/path/to/video.mp4", 
            "/path/to/thumb.jpg", 
            "Test Topic", 
            "Test Script"
        )
        self.mock_uploader.upload_video.return_value = "VIDEO_ID_123"
        self.mock_sync_manager.check_today_uploaded.return_value = False
        self.mock_user_request_handler.get_next_request.return_value = None
        self.mock_database.get_top_performing_videos.return_value = []
        self.mock_database.get_top_topics.return_value = []

    def test_pipeline_execution(self):
        """Test the full pipeline execution via ShortsBot."""
        # Initialize ShortsBot with mocks
        with patch('src.pipeline.bot.AIVideoGenerator', return_value=self.mock_video_generator), \
             patch('src.pipeline.bot.YouTubeUploader', return_value=self.mock_uploader), \
             patch('src.pipeline.bot.VideoDatabase', return_value=self.mock_database), \
             patch('src.pipeline.bot.SyncManager', return_value=self.mock_sync_manager), \
             patch('src.pipeline.bot.UserRequestHandler', return_value=self.mock_user_request_handler), \
             patch('src.pipeline.bot.NotificationService', return_value=self.mock_notification_service), \
             patch('src.pipeline.bot.MonetizationTracker', return_value=self.mock_monetization), \
             patch('src.pipeline.bot.MultiPlatformUploader'), \
             patch('src.pipeline.bot.ABTestDatabase'), \
             patch('src.pipeline.bot.TopicDatabase'), \
             patch('src.pipeline.bot.ThumbnailOptimizer'), \
             patch('src.pipeline.bot.PerformancePredictor'), \
             patch('src.pipeline.bot.AutoOptimizer'), \
             patch('src.pipeline.bot.CompetitorAnalyzer'), \
             patch('src.pipeline.bot.AudienceSegmentAnalyzer'), \
             patch('src.pipeline.bot.SeriesGenerator'), \
             patch('src.pipeline.bot.CommentAnalyzer'):
            
            bot = ShortsBot()
            
            # Inject mocks into pipeline manually to ensure they are used
            # (ShortsBot init creates new instances, so we need to mock the classes or replace instances)
            # Since we patched the classes, bot.pipeline should have the mock instances.
            # Let's verify.
            
            # Execute
            video_id = bot.create_and_upload(
                topic="Test Topic",
                content_type=ContentType.FACT,
                force=True,
                auto_upload=True
            )
            
            # Verify
            self.assertEqual(video_id, "VIDEO_ID_123")
            
            # Check calls
            # 1. Video Generation
            bot.pipeline.video_generator.generate_video.assert_called_once()
            args, kwargs = bot.pipeline.video_generator.generate_video.call_args
            self.assertEqual(kwargs['topic'], "Test Topic")
            self.assertEqual(kwargs['content_type'], ContentType.FACT)
            
            # 2. Upload
            bot.pipeline.uploader.upload_video.assert_called_once()
            
            # 3. Database Update
            bot.pipeline.database.add_video.assert_called_once()
            
            # 4. Notification
            bot.pipeline.notification_service.send_upload_notification.assert_called_once()

    def test_pipeline_constraints(self):
        """Test that pipeline respects upload constraints."""
        self.mock_sync_manager.check_today_uploaded.return_value = True
        
        with patch('src.pipeline.bot.AIVideoGenerator', return_value=self.mock_video_generator), \
             patch('src.pipeline.bot.YouTubeUploader', return_value=self.mock_uploader), \
             patch('src.pipeline.bot.VideoDatabase', return_value=self.mock_database), \
             patch('src.pipeline.bot.SyncManager', return_value=self.mock_sync_manager), \
             patch('src.pipeline.bot.UserRequestHandler', return_value=self.mock_user_request_handler), \
             patch('src.pipeline.bot.NotificationService', return_value=self.mock_notification_service), \
             patch('src.pipeline.bot.MonetizationTracker', return_value=self.mock_monetization), \
             patch('src.pipeline.bot.MultiPlatformUploader'), \
             patch('src.pipeline.bot.ABTestDatabase'), \
             patch('src.pipeline.bot.TopicDatabase'), \
             patch('src.pipeline.bot.ThumbnailOptimizer'), \
             patch('src.pipeline.bot.PerformancePredictor'), \
             patch('src.pipeline.bot.AutoOptimizer'), \
             patch('src.pipeline.bot.CompetitorAnalyzer'), \
             patch('src.pipeline.bot.AudienceSegmentAnalyzer'), \
             patch('src.pipeline.bot.SeriesGenerator'), \
             patch('src.pipeline.bot.CommentAnalyzer'):
            
            bot = ShortsBot()
            
            # Execute without force
            video_id = bot.create_and_upload(
                topic="Test Topic",
                force=False,
                auto_upload=True
            )
            
            # Verify
            self.assertIsNone(video_id)
            bot.pipeline.video_generator.generate_video.assert_not_called()

if __name__ == '__main__':
    unittest.main()

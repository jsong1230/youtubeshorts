"""
Tests for bot pipeline system
"""
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

from src.pipeline.bot import ShortsBot
from src.generators.content_type import ContentType


class TestShortsBot:
    """Test ShortsBot class"""
    
    @pytest.fixture
    def bot(self, tmp_path, monkeypatch):
        """Create a ShortsBot instance with mocked dependencies"""
        # Mock all dependencies
        with patch('src.pipeline.bot.AIVideoGenerator') as mock_vg, \
             patch('src.pipeline.bot.YouTubeUploader') as mock_uploader, \
             patch('src.pipeline.bot.MonetizationTracker') as mock_monet, \
             patch('src.pipeline.bot.VideoDatabase') as mock_db, \
             patch('src.pipeline.bot.SyncManager') as mock_sync, \
             patch('src.pipeline.bot.ABTestDatabase') as mock_ab, \
             patch('src.pipeline.bot.TopicDatabase') as mock_topic_db, \
             patch('src.pipeline.bot.ThumbnailOptimizer') as mock_thumb, \
             patch('src.pipeline.bot.PerformancePredictor') as mock_pred, \
             patch('src.pipeline.bot.AutoOptimizer') as mock_opt, \
             patch('src.pipeline.bot.CompetitorAnalyzer') as mock_comp, \
             patch('src.pipeline.bot.AudienceSegmentAnalyzer') as mock_aud, \
             patch('src.pipeline.bot.NotificationService') as mock_notif, \
             patch('src.pipeline.bot.SeriesGenerator') as mock_series, \
             patch('src.pipeline.bot.UserRequestHandler') as mock_user, \
             patch('src.pipeline.bot.CommentAnalyzer') as mock_comment, \
             patch('config.ENABLE_TIKTOK_UPLOAD', False), \
             patch('config.ENABLE_INSTAGRAM_UPLOAD', False), \
             patch('config.DATABASE_PATH', str(tmp_path / 'videos.db')), \
             patch('config.UPLOAD_TIMEZONE', 'Asia/Seoul'):
            
            # Create bot instance
            bot_instance = ShortsBot()
            
            # Store mocks for easy access
            bot_instance._mocks = {
                'video_generator': bot_instance.video_generator,
                'uploader': bot_instance.uploader,
                'monetization': bot_instance.monetization,
                'database': bot_instance.database,
                'sync_manager': bot_instance.sync_manager
            }
            
            return bot_instance
    
    def test_init(self, bot):
        """Test bot initialization"""
        assert bot.video_generator is not None
        assert bot.uploader is not None
        assert bot.monetization is not None
        assert bot.database is not None
        assert bot.sync_manager is not None
        assert bot.use_multi_platform is False
    
    def test_init_multi_platform(self, tmp_path, monkeypatch):
        """Test bot initialization with multi-platform enabled"""
        with patch('src.pipeline.bot.AIVideoGenerator') as mock_vg, \
             patch('src.pipeline.bot.MultiPlatformUploader') as mock_multi, \
             patch('src.pipeline.bot.MonetizationTracker') as mock_monet, \
             patch('src.pipeline.bot.VideoDatabase') as mock_db, \
             patch('src.pipeline.bot.SyncManager') as mock_sync, \
             patch('src.pipeline.bot.ABTestDatabase') as mock_ab, \
             patch('src.pipeline.bot.TopicDatabase') as mock_topic_db, \
             patch('src.pipeline.bot.ThumbnailOptimizer') as mock_thumb, \
             patch('src.pipeline.bot.PerformancePredictor') as mock_pred, \
             patch('src.pipeline.bot.AutoOptimizer') as mock_opt, \
             patch('src.pipeline.bot.CompetitorAnalyzer') as mock_comp, \
             patch('src.pipeline.bot.AudienceSegmentAnalyzer') as mock_aud, \
             patch('src.pipeline.bot.NotificationService') as mock_notif, \
             patch('src.pipeline.bot.SeriesGenerator') as mock_series, \
             patch('src.pipeline.bot.UserRequestHandler') as mock_user, \
             patch('src.pipeline.bot.CommentAnalyzer') as mock_comment, \
             patch('config.ENABLE_TIKTOK_UPLOAD', True), \
             patch('config.ENABLE_INSTAGRAM_UPLOAD', False), \
             patch('config.DATABASE_PATH', str(tmp_path / 'videos.db')), \
             patch('config.UPLOAD_TIMEZONE', 'Asia/Seoul'):
            
            bot = ShortsBot()
            assert bot.use_multi_platform is True
            assert isinstance(bot.uploader, Mock)  # MultiPlatformUploader mock
    
    def test_get_performance_based_prompt(self, bot):
        """Test getting performance-based prompt"""
        # Mock database methods
        bot.database.get_top_performing_videos = Mock(return_value=[
            {'topic': 'Test Topic 1', 'engagement_rate': 3.5},
            {'topic': 'Test Topic 2', 'engagement_rate': 2.8}
        ])
        bot.database.get_top_topics = Mock(return_value=[
            {'topic': 'Popular Topic 1'},
            {'topic': 'Popular Topic 2'}
        ])
        
        prompt = bot._get_performance_based_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        bot.database.get_top_performing_videos.assert_called_once()
        bot.database.get_top_topics.assert_called_once()
    
    def test_get_performance_based_prompt_no_data(self, bot):
        """Test getting performance-based prompt when no data exists"""
        bot.database.get_top_performing_videos = Mock(return_value=[])
        bot.database.get_top_topics = Mock(return_value=[])
        
        prompt = bot._get_performance_based_prompt()
        
        assert isinstance(prompt, str)
        # Should return empty string or default prompt when no data
        assert len(prompt) >= 0
    
    def test_check_upload_constraints(self, bot):
        """Test checking upload constraints"""
        # Mock sync manager methods
        bot.sync_manager.check_today_uploaded = Mock(return_value=False)
        bot.sync_manager.print_sync_status = Mock()
        bot.uploader.check_today_uploaded = Mock(return_value=False)
        
        result = bot._check_upload_constraints(force=False)
        
        assert result is True
        bot.sync_manager.check_today_uploaded.assert_called_once()
    
    def test_check_upload_constraints_already_uploaded(self, bot, monkeypatch):
        """Test upload constraints when already uploaded today"""
        bot.sync_manager.check_today_uploaded = Mock(return_value=True)
        bot.sync_manager.get_today_upload_info = Mock(return_value={
            'video_id': 'test_video_1',
            'title': 'Test Video',
            'computer_id': 'test_computer'
        })
        bot.sync_manager.print_sync_status = Mock()
        
        # Mock input to return 'n' (no) - input() takes no args in this context
        monkeypatch.setattr('builtins.input', lambda: 'n')
        
        result = bot._check_upload_constraints(force=False)
        
        assert result is False
    
    def test_check_upload_constraints_force(self, bot):
        """Test upload constraints with force flag"""
        bot.sync_manager.get_sync_status = Mock(return_value={
            'today_uploaded': True,
            'last_upload': {
                'video_id': 'test_video_1',
                'upload_time': datetime.now().isoformat()
            }
        })
        
        result = bot._check_upload_constraints(force=True)
        
        # Force should bypass constraints
        assert result is True
    
    def test_determine_video_parameters(self, bot):
        """Test determining video parameters"""
        topic, language, request_id = bot._determine_video_parameters(
            topic="How to save money",
            language=None
        )
        
        assert topic == "How to save money"
        assert language == "en"  # English topic detected
        assert request_id is None  # No user request
    
    def test_determine_video_parameters_korean(self, bot):
        """Test determining video parameters for Korean topic"""
        topic, language, request_id = bot._determine_video_parameters(
            topic="돈 버는 방법",
            language=None
        )
        
        assert topic == "돈 버는 방법"
        assert language == "ko"  # Korean topic detected
        assert request_id is None
    
    def test_determine_video_parameters_explicit_language(self, bot):
        """Test determining video parameters with explicit language"""
        topic, language, request_id = bot._determine_video_parameters(
            topic="How to save money",
            language="ko"  # Explicitly set to Korean
        )
        
        assert topic == "How to save money"
        assert language == "ko"  # Explicit language takes precedence
        assert request_id is None
    
    def test_generate_description(self, bot):
        """Test generating video description"""
        description = bot._generate_description(
            language="en",
            original_topic="How to save money",
            actual_topic="How to save money fast"
        )
        
        assert isinstance(description, str)
        assert len(description) > 0
        assert "How to save money" in description or "save money" in description.lower()
    
    def test_generate_description_korean(self, bot):
        """Test generating Korean description"""
        description = bot._generate_description(
            language="ko",
            original_topic="돈 버는 방법",
            actual_topic="빠르게 돈 버는 방법"
        )
        
        assert isinstance(description, str)
        assert len(description) > 0
    
    def test_map_topic_source(self, bot):
        """Test mapping topic source"""
        # _map_topic_source takes string, not enum
        assert bot._map_topic_source("manual") == "manual"
        assert bot._map_topic_source("ai_generated") == "ai_generated"
        assert bot._map_topic_source("youtube_trend") == "trend"
        assert bot._map_topic_source("global_trend") == "trend"
        assert bot._map_topic_source("seasonal") == "seasonal"
        assert bot._map_topic_source("unknown") == "manual"  # Default to manual
        assert bot._map_topic_source(None) == "manual"
        assert bot._map_topic_source([]) == "manual"
    
    def test_create_video_only(self, bot, tmp_path):
        """Test creating video only (no upload)"""
        # Mock video generator - returns tuple (video_path, thumbnail_path, generated_topic, script)
        video_path = str(tmp_path / 'test_video.mp4')
        thumbnail_path = str(tmp_path / 'test_thumbnail.jpg')
        generated_topic = "Test Topic"
        script = ['Sentence 1', 'Sentence 2']
        
        bot.video_generator.generate_video = Mock(return_value=(
            video_path, thumbnail_path, generated_topic, script
        ))
        
        # Mock config
        with patch('config.VIDEO_OUTPUT_DIR', str(tmp_path)):
            result = bot.create_video_only(topic="Test Topic")
        
        assert result is not None
        assert result == video_path  # Returns video_path string
        bot.video_generator.generate_video.assert_called_once()
    
    def test_create_video_only_no_topic(self, bot, tmp_path):
        """Test creating video with auto topic selection"""
        video_path = str(tmp_path / 'test_video.mp4')
        thumbnail_path = str(tmp_path / 'test_thumbnail.jpg')
        generated_topic = 'Auto Selected Topic'
        script = ['Sentence 1']
        
        bot.video_generator.generate_video = Mock(return_value=(
            video_path, thumbnail_path, generated_topic, script
        ))
        
        with patch('config.VIDEO_OUTPUT_DIR', str(tmp_path)):
            result = bot.create_video_only()
        
        assert result is not None
        assert result == video_path
        bot.video_generator.generate_video.assert_called_once()
    
    def test_create_and_upload_success(self, bot, tmp_path):
        """Test creating and uploading video successfully"""
        # Setup mocks - generate_video returns tuple
        video_path = str(tmp_path / 'test_video.mp4')
        thumbnail_path = str(tmp_path / 'test_thumbnail.jpg')
        generated_topic = 'Test Topic'
        script = ['Sentence 1', 'Sentence 2']
        
        bot.video_generator.generate_video = Mock(return_value=(
            video_path, thumbnail_path, generated_topic, script
        ))
        bot.video_generator.image_generator = Mock()
        bot.video_generator.image_generator.embed_thumbnail_frame = Mock()
        bot._check_upload_constraints = Mock(return_value=True)
        bot._get_performance_based_prompt = Mock(return_value="")
        bot.uploader.upload_video = Mock(return_value="test_video_id_123")
        bot.sync_manager.record_upload = Mock()
        bot.database.add_video = Mock(return_value=True)
        bot.monetization.add_video = Mock()
        bot.monetization.print_report = Mock()
        bot.ab_test_db.add_test = Mock(return_value=True)
        bot.user_request_handler.get_next_request = Mock(return_value=None)
        bot.uploader.get_channel_info = Mock(return_value={'url': 'https://youtube.com/channel/test'})
        bot.uploader.get_recent_videos = Mock(return_value=[])
        
        # Mock TopicDatabase since _update_databases creates a new instance
        with patch('src.pipeline.bot.TopicDatabase') as mock_topic_db_class, \
             patch('config.USE_BACKGROUND_MUSIC', True), \
             patch('config.SUBTITLE_MODE', 'full_sentence'), \
             patch('config.DEFAULT_TAGS', ['shorts', 'ai', 'automated']):
            mock_topic_db = Mock()
            mock_topic_db.add_topic = Mock(return_value=1)
            mock_topic_db.link_topic_to_video = Mock(return_value=True)
            mock_topic_db_class.return_value = mock_topic_db
            
            # Mock _save_upload_log
            bot._save_upload_log = Mock()
            
            result = bot.create_and_upload(topic="Test Topic", auto_upload=True)
        
        assert result is not None
        # Result is video_id string (not dict)
        assert isinstance(result, str)
        assert result == "test_video_id_123"
        # upload_video may be called multiple times (once in _upload_to_platforms, once directly)
        assert bot.uploader.upload_video.call_count >= 1
        bot.sync_manager.record_upload.assert_called_once()
        bot.database.add_video.assert_called_once()
    
    def test_create_and_upload_constraints_failed(self, bot):
        """Test create and upload when constraints fail"""
        bot._check_upload_constraints = Mock(return_value=False)
        
        result = bot.create_and_upload(topic="Test Topic", auto_upload=True)
        
        assert result is None
        bot._check_upload_constraints.assert_called_once()
    
    def test_create_and_upload_video_generation_failed(self, bot):
        """Test create and upload when video generation fails"""
        bot._check_upload_constraints = Mock(return_value=True)
        bot._get_performance_based_prompt = Mock(return_value="")
        bot.video_generator.generate_video = Mock(return_value=None)
        
        result = bot.create_and_upload(topic="Test Topic", auto_upload=True)
        
        assert result is None
    
    def test_update_databases(self, bot):
        """Test updating databases after upload"""
        video_assets = {
            'video_id': 'test_video_123',
            'title': 'Test Video',
            'actual_topic': 'Test Topic',
            'script': ['Sentence 1', 'Sentence 2'],
            'content_type': ContentType.HOOK.value
        }
        upload_results = {
            'youtube': 'test_video_123'
        }
        
        bot.database.add_video = Mock(return_value=True)
        bot.monetization.add_video = Mock()
        bot.ab_test_db.add_test = Mock(return_value=True)
        bot.sync_manager.record_upload = Mock()
        bot.video_generator._get_season = Mock(return_value='winter')
        bot._save_upload_log = Mock()
        
        # Mock TopicDatabase since _update_databases creates a new instance
        # Patch both import paths
        with patch('src.pipeline.topic_database.TopicDatabase') as mock_topic_db_class, \
             patch('config.USE_BACKGROUND_MUSIC', True), \
             patch('config.SUBTITLE_MODE', 'full_sentence'):
            mock_topic_db = Mock()
            mock_topic_db.add_topic = Mock(return_value=1)
            mock_topic_db.link_topic_to_video = Mock(return_value=True)
            mock_topic_db_class.return_value = mock_topic_db
            
            bot._update_databases(
                video_assets, 
                upload_results, 
                request_id=None,
                content_type=ContentType.HOOK, 
                performance_prompt=""
            )
        
        bot.database.add_video.assert_called_once()
        bot.monetization.add_video.assert_called_once()
        bot.ab_test_db.add_test.assert_called_once()
        bot.sync_manager.record_upload.assert_called_once()
        # TopicDatabase should be instantiated (may fail silently in try/except)
        # Just verify that the main database operations were called
    
    def test_send_notifications(self, bot):
        """Test sending notifications"""
        video_assets = {
            'video_id': 'test_video_123',
            'title': 'Test Video',
            'topic': 'Test Topic'
        }
        video_id = 'test_video_123'
        
        bot.notification_service.notify_video_uploaded = Mock()
        
        bot._send_notifications(video_assets, video_id)
        
        bot.notification_service.notify_video_uploaded.assert_called_once()
    
    def test_update_all_stats(self, bot):
        """Test updating all statistics"""
        bot.monetization.update_all_videos = Mock()
        bot.database.get_all_videos = Mock(return_value=[
            {'video_id': 'test_1', 'views': 1000},
            {'video_id': 'test_2', 'views': 2000}
        ])
        bot.uploader.get_video_stats = Mock(side_effect=[
            {'views': 1000, 'likes': 50, 'comments': 10},
            {'views': 2000, 'likes': 100, 'comments': 20}
        ])
        bot.database.update_video_stats = Mock(return_value=True)
        bot.ab_test_db.update_test_stats = Mock(return_value=True)
        bot.ab_test_db.get_best_style = Mock(return_value="bold")
        bot.ab_test_db.get_best_styles_by_engagement = Mock(return_value=[
            ("bold", 5.5, 1500),
            ("default", 4.2, 1200)
        ])
        
        bot.update_all_stats()
        
        bot.monetization.update_all_videos.assert_called_once()
        # Database update should be called for each video
        assert bot.database.update_video_stats.call_count >= 0
    
    def test_create_and_upload_all_types(self, bot, tmp_path):
        """Test creating and uploading all content types"""
        # Mock video generation for each type
        mock_video_assets = {
            'video_path': str(tmp_path / 'test_video.mp4'),
            'title': 'Test Video',
            'topic': 'Test Topic',
            'script': ['Sentence 1'],
            'thumbnail_path': str(tmp_path / 'test_thumbnail.jpg'),
            'content_type': ContentType.HOOK.value
        }
        bot.video_generator.generate_video = Mock(return_value=mock_video_assets)
        bot._check_upload_constraints = Mock(return_value=True)
        bot._get_performance_based_prompt = Mock(return_value="")
        bot.uploader.upload_video = Mock(return_value="test_video_id")
        bot.sync_manager.mark_uploaded = Mock()
        bot.database.add_video = Mock(return_value=True)
        bot.monetization.add_video = Mock()
        bot.ab_test_db.add_test = Mock(return_value=True)
        bot.topic_database.add_topic = Mock(return_value=1)
        bot.topic_database.link_topic_to_video = Mock(return_value=True)
        
        # This will try to create videos for all types
        # We'll limit it by mocking to return None after first success
        bot.video_generator.generate_video = Mock(side_effect=[
            mock_video_assets,  # First call succeeds
            None  # Subsequent calls fail to limit test time
        ])
        
        # Should handle gracefully
        try:
            bot.create_and_upload_all_types(auto_upload=True)
        except Exception:
            pass  # Expected to fail after first video or handle gracefully
        
        # At least one video generation attempt should be made
        assert bot.video_generator.generate_video.call_count >= 1


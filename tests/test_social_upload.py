"""
Tests for social media upload functionality
"""
import os
import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from src.uploaders.instagram_uploader import InstagramUploader
from src.uploaders.tiktok_uploader import TikTokUploader
from src.uploaders.social_manager import SocialManager


class TestInstagramUploader:
    """Test InstagramUploader functionality"""
    
    @patch('src.uploaders.instagram_uploader.settings')
    def test_instagram_uploader_init(self, mock_config):
        """Test InstagramUploader initialization"""
        mock_config.INSTAGRAM_ACCESS_TOKEN = 'test_token'
        mock_config.INSTAGRAM_ACCOUNT_ID = 'test_id'
        
        uploader = InstagramUploader()
        assert uploader.is_configured is True
        assert uploader.access_token == 'test_token'
    
    @patch('src.uploaders.instagram_uploader.settings')
    def test_instagram_uploader_not_configured(self, mock_config):
        """Test InstagramUploader when not configured"""
        mock_config.INSTAGRAM_ACCESS_TOKEN = None
        mock_config.INSTAGRAM_ACCOUNT_ID = None
        
        uploader = InstagramUploader()
        assert uploader.is_configured is False


class TestTikTokUploader:
    """Test TikTokUploader functionality"""
    
    @patch('src.uploaders.tiktok_uploader.settings')
    def test_tiktok_uploader_init(self, mock_config):
        """Test TikTokUploader initialization"""
        mock_config.TIKTOK_ACCESS_TOKEN = 'test_token'
        
        uploader = TikTokUploader()
        assert uploader.is_configured is True
        assert uploader.access_token == 'test_token'
    
    @patch('src.uploaders.tiktok_uploader.settings')
    def test_tiktok_uploader_not_configured(self, mock_config):
        """Test TikTokUploader when not configured"""
        mock_config.TIKTOK_ACCESS_TOKEN = None
        
        uploader = TikTokUploader()
        assert uploader.is_configured is False


class TestSocialManager:
    """Test SocialManager functionality"""
    
    @patch('src.uploaders.social_manager.InstagramUploader')
    @patch('src.uploaders.social_manager.TikTokUploader')
    @patch('src.uploaders.social_manager.settings')
    def test_social_manager_upload_all(self, mock_config, MockTikTok, MockInstagram):
        """Test SocialManager upload_all method"""
        # Setup config
        mock_config.ENABLE_INSTAGRAM_UPLOAD = True
        mock_config.ENABLE_TIKTOK_UPLOAD = True
        
        # Setup mock instances
        mock_insta_instance = Mock()
        mock_insta_instance.is_configured = True
        mock_insta_instance.upload_reel.return_value = 'instagram_id_123'
        MockInstagram.return_value = mock_insta_instance
        
        mock_tiktok_instance = Mock()
        mock_tiktok_instance.is_configured = True
        mock_tiktok_instance.upload_video.return_value = 'tiktok_id_456'
        MockTikTok.return_value = mock_tiktok_instance
        
        # Test
        manager = SocialManager()
        results = manager.upload_all("test_video.mp4", "Test Title", "Test Desc")
        
        # Verify
        assert results['instagram'] == 'success'
        assert results['tiktok'] == 'success'
        mock_insta_instance.upload_reel.assert_called_once()
        mock_tiktok_instance.upload_video.assert_called_once()
    
    @patch('src.uploaders.social_manager.InstagramUploader')
    @patch('src.uploaders.social_manager.TikTokUploader')
    @patch('src.uploaders.social_manager.settings')
    def test_social_manager_upload_all_partial_failure(self, mock_config, MockTikTok, MockInstagram):
        """Test SocialManager handles partial failures"""
        mock_config.ENABLE_INSTAGRAM_UPLOAD = True
        mock_config.ENABLE_TIKTOK_UPLOAD = True
        
        # Instagram succeeds, TikTok fails
        mock_insta_instance = Mock()
        mock_insta_instance.is_configured = True
        mock_insta_instance.upload_reel.return_value = 'instagram_id_123'
        MockInstagram.return_value = mock_insta_instance
        
        mock_tiktok_instance = Mock()
        mock_tiktok_instance.is_configured = True
        mock_tiktok_instance.upload_video.side_effect = Exception("TikTok API Error")
        MockTikTok.return_value = mock_tiktok_instance
        
        manager = SocialManager()
        
        # Should raise exception when TikTok fails (no error handling in current implementation)
        with pytest.raises(Exception, match="TikTok API Error"):
            manager.upload_all("test_video.mp4", "Test Title", "Test Desc")
    
    @patch('src.uploaders.social_manager.InstagramUploader')
    @patch('src.uploaders.social_manager.TikTokUploader')
    @patch('src.uploaders.social_manager.settings')
    def test_social_manager_upload_all_not_configured(self, mock_config, MockTikTok, MockInstagram):
        """Test SocialManager when platforms are not configured"""
        mock_config.ENABLE_INSTAGRAM_UPLOAD = True
        mock_config.ENABLE_TIKTOK_UPLOAD = True
        
        # Both not configured
        mock_insta_instance = Mock()
        mock_insta_instance.is_configured = False
        MockInstagram.return_value = mock_insta_instance
        
        mock_tiktok_instance = Mock()
        mock_tiktok_instance.is_configured = False
        MockTikTok.return_value = mock_tiktok_instance
        
        manager = SocialManager()
        results = manager.upload_all("test_video.mp4", "Test Title", "Test Desc")
        
        assert results['instagram'] == 'not_configured'
        assert results['tiktok'] == 'not_configured'

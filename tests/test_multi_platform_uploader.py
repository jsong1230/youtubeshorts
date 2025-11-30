"""
Tests for MultiPlatformUploader functionality
"""
import os
import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from src.uploaders.multi_platform_uploader import MultiPlatformUploader


class TestMultiPlatformUploaderInit:
    """Test MultiPlatformUploader initialization"""
    
    @patch('src.uploaders.multi_platform_uploader.YouTubeUploader')
    @patch('src.uploaders.multi_platform_uploader.config')
    def test_init_with_youtube_only(self, mock_config, mock_youtube):
        """Test initialization with only YouTube enabled"""
        mock_config.ENABLE_TIKTOK_UPLOAD = False
        mock_config.ENABLE_INSTAGRAM_UPLOAD = False
        
        mock_youtube_instance = Mock()
        mock_youtube.return_value = mock_youtube_instance
        
        uploader = MultiPlatformUploader()
        
        assert 'youtube' in uploader.uploaders
        assert 'tiktok' not in uploader.uploaders
        assert 'instagram' not in uploader.uploaders
        mock_youtube.assert_called_once()
    
    @patch('src.uploaders.multi_platform_uploader.InstagramUploader')
    @patch('src.uploaders.multi_platform_uploader.TikTokUploader')
    @patch('src.uploaders.multi_platform_uploader.YouTubeUploader')
    @patch('src.uploaders.multi_platform_uploader.config')
    def test_init_with_all_platforms(self, mock_config, mock_youtube, 
                                     mock_tiktok, mock_instagram):
        """Test initialization with all platforms enabled"""
        mock_config.ENABLE_TIKTOK_UPLOAD = True
        mock_config.ENABLE_INSTAGRAM_UPLOAD = True
        
        mock_youtube_instance = Mock()
        mock_youtube.return_value = mock_youtube_instance
        
        mock_tiktok_instance = Mock()
        mock_tiktok_instance.is_available.return_value = True
        mock_tiktok.return_value = mock_tiktok_instance
        
        mock_instagram_instance = Mock()
        mock_instagram_instance.is_available.return_value = True
        mock_instagram.return_value = mock_instagram_instance
        
        uploader = MultiPlatformUploader()
        
        assert 'youtube' in uploader.uploaders
        assert 'tiktok' in uploader.uploaders
        assert 'instagram' in uploader.uploaders
    
    @patch('src.uploaders.multi_platform_uploader.TikTokUploader')
    @patch('src.uploaders.multi_platform_uploader.YouTubeUploader')
    @patch('src.uploaders.multi_platform_uploader.config')
    def test_init_handles_tiktok_unavailable(self, mock_config, mock_youtube, mock_tiktok):
        """Test initialization handles TikTok when unavailable"""
        mock_config.ENABLE_TIKTOK_UPLOAD = True
        mock_config.ENABLE_INSTAGRAM_UPLOAD = False
        
        mock_youtube_instance = Mock()
        mock_youtube.return_value = mock_youtube_instance
        
        mock_tiktok_instance = Mock()
        mock_tiktok_instance.is_available.return_value = False
        mock_tiktok.return_value = mock_tiktok_instance
        
        uploader = MultiPlatformUploader()
        
        assert 'youtube' in uploader.uploaders
        # TikTok is still added to uploaders, but is_available() returns False
        # This allows the uploader to exist but be marked as unavailable
        assert 'tiktok' in uploader.uploaders
        assert uploader.uploaders['tiktok'].is_available() is False


class TestMultiPlatformUploaderUpload:
    """Test video upload functionality"""
    
    @patch('src.uploaders.multi_platform_uploader.YouTubeUploader')
    @patch('src.uploaders.multi_platform_uploader.config')
    def test_upload_to_all_youtube_only(self, mock_config, mock_youtube, 
                                       temp_video_file, sample_video_metadata):
        """Test upload to all platforms with only YouTube"""
        mock_config.ENABLE_TIKTOK_UPLOAD = False
        mock_config.ENABLE_INSTAGRAM_UPLOAD = False
        
        mock_youtube_instance = Mock()
        mock_youtube_instance.upload_video.return_value = 'youtube_video_id_123'
        mock_youtube.return_value = mock_youtube_instance
        
        uploader = MultiPlatformUploader()
        
        results = uploader.upload_to_all(
            video_path=temp_video_file,
            title=sample_video_metadata['title'],
            description=sample_video_metadata['description'],
            tags=sample_video_metadata['tags']
        )
        
        assert results['youtube'] == 'youtube_video_id_123'
        assert 'tiktok' not in results
        assert 'instagram' not in results
        mock_youtube_instance.upload_video.assert_called_once()
    
    @patch('src.uploaders.multi_platform_uploader.InstagramUploader')
    @patch('src.uploaders.multi_platform_uploader.TikTokUploader')
    @patch('src.uploaders.multi_platform_uploader.YouTubeUploader')
    @patch('src.uploaders.multi_platform_uploader.config')
    def test_upload_to_all_multiple_platforms(self, mock_config, mock_youtube,
                                             mock_tiktok, mock_instagram,
                                             temp_video_file, sample_video_metadata):
        """Test upload to multiple platforms"""
        mock_config.ENABLE_TIKTOK_UPLOAD = True
        mock_config.ENABLE_INSTAGRAM_UPLOAD = True
        
        mock_youtube_instance = Mock()
        mock_youtube_instance.upload_video.return_value = 'youtube_id'
        mock_youtube.return_value = mock_youtube_instance
        
        mock_tiktok_instance = Mock()
        mock_tiktok_instance.is_available.return_value = True
        mock_tiktok_instance.upload_video.return_value = 'tiktok_id'
        mock_tiktok.return_value = mock_tiktok_instance
        
        mock_instagram_instance = Mock()
        mock_instagram_instance.is_available.return_value = True
        mock_instagram_instance.upload_reel.return_value = 'instagram_id'
        mock_instagram.return_value = mock_instagram_instance
        
        uploader = MultiPlatformUploader()
        
        results = uploader.upload_to_all(
            video_path=temp_video_file,
            title=sample_video_metadata['title'],
            description=sample_video_metadata['description']
        )
        
        assert results['youtube'] == 'youtube_id'
        assert results['tiktok'] == 'tiktok_id'
        assert results['instagram'] == 'instagram_id'
    
    @patch('src.uploaders.multi_platform_uploader.YouTubeUploader')
    @patch('src.uploaders.multi_platform_uploader.config')
    def test_upload_to_all_file_not_found(self, mock_config, mock_youtube, sample_video_metadata):
        """Test upload with non-existent file"""
        mock_config.ENABLE_TIKTOK_UPLOAD = False
        mock_config.ENABLE_INSTAGRAM_UPLOAD = False
        
        mock_youtube_instance = Mock()
        mock_youtube.return_value = mock_youtube_instance
        
        uploader = MultiPlatformUploader()
        
        with pytest.raises(FileNotFoundError, match="영상 파일을 찾을 수 없습니다"):
            uploader.upload_to_all(
                video_path='/nonexistent/video.mp4',
                title=sample_video_metadata['title'],
                description=sample_video_metadata['description']
            )
    
    @patch('src.uploaders.multi_platform_uploader.YouTubeUploader')
    @patch('src.uploaders.multi_platform_uploader.config')
    def test_upload_to_specific_platforms(self, mock_config, mock_youtube,
                                        temp_video_file, sample_video_metadata):
        """Test upload to specific platforms only"""
        mock_config.ENABLE_TIKTOK_UPLOAD = False
        mock_config.ENABLE_INSTAGRAM_UPLOAD = False
        
        mock_youtube_instance = Mock()
        mock_youtube_instance.upload_video.return_value = 'youtube_id'
        mock_youtube.return_value = mock_youtube_instance
        
        uploader = MultiPlatformUploader()
        
        results = uploader.upload_to_all(
            video_path=temp_video_file,
            title=sample_video_metadata['title'],
            description=sample_video_metadata['description'],
            platforms=['youtube']
        )
        
        assert results['youtube'] == 'youtube_id'
        mock_youtube_instance.upload_video.assert_called_once()
    
    @patch('src.uploaders.multi_platform_uploader.InstagramUploader')
    @patch('src.uploaders.multi_platform_uploader.TikTokUploader')
    @patch('src.uploaders.multi_platform_uploader.YouTubeUploader')
    @patch('src.uploaders.multi_platform_uploader.config')
    def test_upload_handles_platform_errors(self, mock_config, mock_youtube,
                                          mock_tiktok, mock_instagram,
                                          temp_video_file, sample_video_metadata):
        """Test upload handles errors from individual platforms"""
        mock_config.ENABLE_TIKTOK_UPLOAD = True
        mock_config.ENABLE_INSTAGRAM_UPLOAD = True
        
        mock_youtube_instance = Mock()
        mock_youtube_instance.upload_video.return_value = 'youtube_id'
        mock_youtube.return_value = mock_youtube_instance
        
        mock_tiktok_instance = Mock()
        mock_tiktok_instance.is_available.return_value = True
        mock_tiktok_instance.upload_video.side_effect = Exception("TikTok API Error")
        mock_tiktok.return_value = mock_tiktok_instance
        
        mock_instagram_instance = Mock()
        mock_instagram_instance.is_available.return_value = True
        mock_instagram_instance.upload_reel.return_value = 'instagram_id'
        mock_instagram.return_value = mock_instagram_instance
        
        uploader = MultiPlatformUploader()
        
        results = uploader.upload_to_all(
            video_path=temp_video_file,
            title=sample_video_metadata['title'],
            description=sample_video_metadata['description']
        )
        
        # YouTube and Instagram should succeed
        assert results['youtube'] == 'youtube_id'
        assert results['instagram'] == 'instagram_id'
        # TikTok should be None due to error
        assert results['tiktok'] is None


class TestMultiPlatformUploaderIntegration:
    """Integration tests for MultiPlatformUploader"""
    
    @patch('src.uploaders.multi_platform_uploader.YouTubeUploader')
    @patch('src.uploaders.multi_platform_uploader.config')
    def test_upload_with_thumbnail(self, mock_config, mock_youtube,
                                  temp_video_file, temp_thumbnail_file, sample_video_metadata):
        """Test upload with thumbnail to all platforms"""
        mock_config.ENABLE_TIKTOK_UPLOAD = False
        mock_config.ENABLE_INSTAGRAM_UPLOAD = False
        
        mock_youtube_instance = Mock()
        mock_youtube_instance.upload_video.return_value = 'youtube_id'
        mock_youtube.return_value = mock_youtube_instance
        
        uploader = MultiPlatformUploader()
        
        results = uploader.upload_to_all(
            video_path=temp_video_file,
            title=sample_video_metadata['title'],
            description=sample_video_metadata['description'],
            thumbnail_path=temp_thumbnail_file
        )
        
        assert results['youtube'] == 'youtube_id'
        # Verify thumbnail was passed
        call_args = mock_youtube_instance.upload_video.call_args
        assert 'thumbnail_path' in call_args.kwargs or temp_thumbnail_file in call_args.args


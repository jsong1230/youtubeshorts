"""
Tests for YouTube uploader functionality
"""

import pytest
from unittest.mock import Mock, patch

from src.uploaders.youtube_uploader import YouTubeUploader


class TestYouTubeUploaderInit:
    """Test YouTubeUploader initialization"""

    @patch("src.utils.youtube_auth.get_authenticated_service")
    def test_init_with_valid_credentials(self, mock_auth):
        """Test initialization with valid credentials"""
        mock_service = Mock()
        mock_auth.return_value = mock_service

        uploader = YouTubeUploader()

        assert uploader.youtube is not None
        mock_auth.assert_called_once()

    @patch("src.utils.youtube_auth.get_authenticated_service")
    def test_init_handles_auth_failure(self, mock_auth):
        """Test initialization handles authentication failure gracefully"""
        mock_auth.side_effect = Exception("Auth failed")

        # Should raise exception during initialization
        with pytest.raises(Exception, match="Auth failed"):
            uploader = YouTubeUploader()


class TestYouTubeUploaderUpload:
    """Test video upload functionality"""

    @patch("src.utils.youtube_auth.get_authenticated_service")
    def test_upload_video_success(
        self, mock_auth, temp_video_file, sample_video_metadata
    ):
        """Test successful video upload"""
        # Setup mock YouTube service
        mock_service = Mock()
        mock_auth.return_value = mock_service

        # Mock the resumable upload - next_chunk() returns (status, response) tuple
        mock_request = Mock()
        # First call: status=None means upload complete, response contains video data
        mock_request.next_chunk.return_value = (None, {"id": "test_video_id_123"})
        mock_service.videos().insert.return_value = mock_request

        uploader = YouTubeUploader()

        # Perform upload
        video_id = uploader.upload_video(
            video_path=temp_video_file,
            title=sample_video_metadata["title"],
            description=sample_video_metadata["description"],
            tags=sample_video_metadata["tags"],
        )

        assert video_id == "test_video_id_123"
        mock_service.videos().insert.assert_called_once()
        mock_request.next_chunk.assert_called_once()

    @patch("src.utils.youtube_auth.get_authenticated_service")
    def test_upload_video_with_thumbnail(
        self, mock_auth, temp_video_file, temp_thumbnail_file, sample_video_metadata
    ):
        """Test video upload with thumbnail"""
        mock_service = Mock()
        mock_auth.return_value = mock_service

        # Mock upload responses - next_chunk() returns (status, response) tuple
        mock_video_request = Mock()
        mock_video_request.next_chunk.return_value = (None, {"id": "test_video_id_456"})
        mock_service.videos().insert.return_value = mock_video_request

        # Mock thumbnail upload
        mock_thumbnail_request = Mock()
        mock_thumbnail_request.execute.return_value = {"items": [{"default": {}}]}
        mock_service.thumbnails().set.return_value = mock_thumbnail_request

        uploader = YouTubeUploader()

        video_id = uploader.upload_video(
            video_path=temp_video_file,
            title=sample_video_metadata["title"],
            description=sample_video_metadata["description"],
            thumbnail_path=temp_thumbnail_file,
        )

        assert video_id == "test_video_id_456"
        # Verify thumbnail was uploaded
        mock_service.thumbnails().set.assert_called_once()

    @patch("src.utils.youtube_auth.get_authenticated_service")
    def test_upload_video_file_not_found(self, mock_auth, sample_video_metadata):
        """Test upload with non-existent video file"""
        mock_service = Mock()
        mock_auth.return_value = mock_service

        uploader = YouTubeUploader()

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError, match="영상 파일을 찾을 수 없습니다"):
            uploader.upload_video(
                video_path="/nonexistent/video.mp4",
                title=sample_video_metadata["title"],
                description=sample_video_metadata["description"],
            )

    @patch("src.utils.youtube_auth.get_authenticated_service")
    def test_upload_video_api_error(
        self, mock_auth, temp_video_file, sample_video_metadata
    ):
        """Test upload handles API errors"""
        mock_service = Mock()
        mock_auth.return_value = mock_service

        # Mock API error in next_chunk()
        mock_request = Mock()
        mock_request.next_chunk.side_effect = Exception("API Error")
        mock_service.videos().insert.return_value = mock_request

        uploader = YouTubeUploader()

        # Should raise exception after retries
        with pytest.raises(Exception, match="API Error"):
            uploader.upload_video(
                video_path=temp_video_file,
                title=sample_video_metadata["title"],
                description=sample_video_metadata["description"],
            )


class TestYouTubeUploaderStats:
    """Test video statistics retrieval"""

    @patch("src.utils.youtube_auth.get_authenticated_service")
    def test_get_video_stats_success(self, mock_auth):
        """Test successful stats retrieval"""
        mock_service = Mock()
        mock_auth.return_value = mock_service

        # Mock stats response - needs both statistics and snippet
        mock_request = Mock()
        mock_request.execute.return_value = {
            "items": [
                {
                    "statistics": {
                        "viewCount": "1000",
                        "likeCount": "50",
                        "commentCount": "10",
                    },
                    "snippet": {
                        "title": "Test Video",
                        "publishedAt": "2025-01-01T00:00:00Z",
                    },
                }
            ]
        }
        mock_service.videos().list.return_value = mock_request

        uploader = YouTubeUploader()
        stats = uploader.get_video_stats("test_video_id")

        assert stats is not None
        assert stats["views"] == 1000
        assert stats["likes"] == 50
        assert stats["comments"] == 10
        assert stats["title"] == "Test Video"

    @patch("src.utils.youtube_auth.get_authenticated_service")
    def test_get_video_stats_video_not_found(self, mock_auth):
        """Test stats retrieval for non-existent video"""
        mock_service = Mock()
        mock_auth.return_value = mock_service

        # Mock empty response
        mock_request = Mock()
        mock_request.execute.return_value = {"items": []}
        mock_service.videos().list.return_value = mock_request

        uploader = YouTubeUploader()
        stats = uploader.get_video_stats("nonexistent_video_id")

        # Should return None or empty dict
        assert stats is None or stats == {}

    @patch("src.utils.youtube_auth.get_authenticated_service")
    def test_get_video_stats_api_error(self, mock_auth):
        """Test stats retrieval handles API errors"""
        mock_service = Mock()
        mock_auth.return_value = mock_service

        # Mock API error
        mock_request = Mock()
        mock_request.execute.side_effect = Exception("API Error")
        mock_service.videos().list.return_value = mock_request

        uploader = YouTubeUploader()
        stats = uploader.get_video_stats("test_video_id")

        # Should handle error gracefully
        assert stats is None


class TestYouTubeUploaderTodayCheck:
    """Test today's upload check functionality"""

    @patch("src.utils.youtube_auth.get_authenticated_service")
    def test_check_today_uploaded_true(self, mock_auth):
        """Test check returns True when video uploaded today"""
        mock_service = Mock()
        mock_auth.return_value = mock_service

        from datetime import datetime

        today = datetime.now()
        today_iso = today.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Mock response with today's video
        mock_request = Mock()
        mock_request.execute.return_value = {
            "items": [{"snippet": {"publishedAt": today_iso, "title": "Test Video"}}]
        }
        mock_service.search().list.return_value = mock_request

        uploader = YouTubeUploader()
        result = uploader.check_today_uploaded()

        assert result is True

    @patch("src.utils.youtube_auth.get_authenticated_service")
    def test_check_today_uploaded_false(self, mock_auth):
        """Test check returns False when no video uploaded today"""
        mock_service = Mock()
        mock_auth.return_value = mock_service

        # Mock empty response
        mock_request = Mock()
        mock_request.execute.return_value = {"items": []}
        mock_service.search().list.return_value = mock_request

        uploader = YouTubeUploader()
        result = uploader.check_today_uploaded()

        assert result is False


class TestYouTubeUploaderIntegration:
    """Integration tests for YouTube uploader"""

    @patch("src.utils.youtube_auth.get_authenticated_service")
    def test_upload_and_get_stats_workflow(
        self, mock_auth, temp_video_file, sample_video_metadata
    ):
        """Test complete workflow: upload video and retrieve stats"""
        mock_service = Mock()
        mock_auth.return_value = mock_service

        # Mock upload - next_chunk() returns (status, response) tuple
        mock_upload_request = Mock()
        mock_upload_request.next_chunk.return_value = (None, {"id": "workflow_test_id"})
        mock_service.videos().insert.return_value = mock_upload_request

        # Mock stats - needs both statistics and snippet
        mock_stats_request = Mock()
        mock_stats_request.execute.return_value = {
            "items": [
                {
                    "statistics": {
                        "viewCount": "100",
                        "likeCount": "5",
                        "commentCount": "2",
                    },
                    "snippet": {
                        "title": "Test Video",
                        "publishedAt": "2025-01-01T00:00:00Z",
                    },
                }
            ]
        }
        mock_service.videos().list.return_value = mock_stats_request

        uploader = YouTubeUploader()

        # Upload video
        video_id = uploader.upload_video(
            video_path=temp_video_file,
            title=sample_video_metadata["title"],
            description=sample_video_metadata["description"],
        )

        assert video_id == "workflow_test_id"

        # Get stats
        stats = uploader.get_video_stats(video_id)

        assert stats is not None
        assert stats["views"] == 100
        assert stats["likes"] == 5
        assert stats["comments"] == 2

"""
Tests for VideoPipeline class
"""

import pytest
from unittest.mock import Mock

from src.pipeline.video_pipeline import VideoPipeline


class TestVideoPipeline:
    """Test VideoPipeline class"""

    @pytest.fixture
    def pipeline(self, tmp_path):
        """Create a VideoPipeline instance with mocked dependencies"""
        mock_vg = Mock()
        mock_uploader = Mock()
        mock_db = Mock()
        mock_sync = Mock()
        mock_user = Mock()
        mock_notif = Mock()
        mock_monet = Mock()

        pipeline = VideoPipeline(
            video_generator=mock_vg,
            uploader=mock_uploader,
            database=mock_db,
            sync_manager=mock_sync,
            user_request_handler=mock_user,
            notification_service=mock_notif,
            monetization_tracker=mock_monet,
            use_multi_platform=False,
        )

        # Mock metadata manager
        pipeline.metadata_manager = Mock()
        pipeline.metadata_manager.generate_title = Mock(return_value="Test Title")
        pipeline.metadata_manager.generate_description = Mock(
            return_value="Test Description"
        )

        return pipeline

    def test_determine_parameters(self, pipeline):
        """Test determining video parameters"""
        topic, language, request_id = pipeline._determine_parameters(
            topic="How to save money", language=None
        )

        assert topic == "How to save money"
        assert language == "en"
        assert request_id is None

    def test_determine_parameters_korean(self, pipeline):
        """Test determining video parameters for Korean topic"""
        topic, language, request_id = pipeline._determine_parameters(
            topic="돈 버는 방법", language=None
        )

        assert topic == "돈 버는 방법"
        assert language == "ko"
        assert request_id is None

    def test_check_constraints(self, pipeline):
        """Test checking upload constraints"""
        pipeline.sync_manager.check_today_uploaded = Mock(return_value=False)
        pipeline.uploader.check_today_uploaded = Mock(return_value=False)

        result = pipeline._check_constraints(force=False)

        assert result is True
        pipeline.sync_manager.check_today_uploaded.assert_called_once()

    def test_check_constraints_already_uploaded(self, pipeline):
        """Test upload constraints when already uploaded today"""
        pipeline.sync_manager.check_today_uploaded = Mock(return_value=True)
        pipeline.sync_manager.get_today_upload_info = Mock(
            return_value={"video_id": "123"}
        )

        result = pipeline._check_constraints(force=False)

        assert result is False

    def test_get_performance_prompt(self, pipeline):
        """Test getting performance-based prompt"""
        pipeline.database.get_top_performing_videos = Mock(
            return_value=[{"topic": "Test Topic 1", "engagement_rate": 3.5}]
        )
        pipeline.database.get_top_topics = Mock(
            return_value=[{"topic": "Popular Topic 1"}]
        )

        prompt = pipeline._get_performance_prompt()

        assert isinstance(prompt, str)
        pipeline.database.get_top_performing_videos.assert_called_once()

    def test_generate_content(self, pipeline, tmp_path):
        """Test generating video content"""
        video_path = str(tmp_path / "test_video.mp4")
        thumbnail_path = str(tmp_path / "test_thumbnail.jpg")

        pipeline.video_generator.generate_video = Mock(
            return_value=(video_path, thumbnail_path, "Test Topic", ["Script"])
        )
        pipeline.video_generator.image_generator = Mock()

        result = pipeline._generate_content(
            topic="Test Topic", content_type=None, language="en", performance_prompt=""
        )

        assert result["video_path"] == video_path
        assert result["thumbnail_path"] == thumbnail_path
        assert result["actual_topic"] == "Test Topic"

    def test_run_success(self, pipeline, tmp_path):
        """Test full pipeline run success"""
        video_path = str(tmp_path / "test_video.mp4")

        # Mock methods
        pipeline._check_constraints = Mock(return_value=True)
        pipeline._determine_parameters = Mock(return_value=("Test Topic", "en", None))
        pipeline._get_performance_prompt = Mock(return_value="")
        pipeline._generate_content = Mock(
            return_value={
                "video_path": video_path,
                "title": "Test Title",
                "actual_topic": "Test Topic",
                "description": "Desc",
                "tags": [],
                "thumbnail_path": None,
                "script": [],
                "topic_source": "manual",
            }
        )
        pipeline._confirm_upload = Mock(return_value=True)
        pipeline._upload = Mock(return_value={"youtube": "video_123"})
        pipeline._update_records = Mock()
        pipeline._save_upload_log = Mock()
        pipeline._notify = Mock()

        result = pipeline.run(topic="Test Topic", auto_upload=True)

        assert result == "video_123"
        pipeline._generate_content.assert_called_once()
        pipeline._upload.assert_called_once()
        pipeline._notify.assert_called_once()

    def test_run_constraints_failed(self, pipeline):
        """Test run when constraints fail"""
        pipeline._check_constraints = Mock(return_value=False)

        result = pipeline.run(topic="Test Topic")

        assert result is None
        pipeline._check_constraints.assert_called_once()

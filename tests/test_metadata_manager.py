import pytest
from datetime import datetime
from unittest.mock import patch
from src.pipeline.metadata_manager import MetadataManager
from src.core.config import settings


class TestMetadataManager:
    @pytest.fixture
    def metadata_manager(self):
        return MetadataManager()

    def test_generate_title_with_actual_topic(self, metadata_manager):
        """Test title generation with actual topic provided"""
        title = metadata_manager.generate_title(
            topic="Draft Topic", actual_topic="Actual Video Title"
        )
        assert "Actual Video Title" in title
        assert "#Shorts" in title

    def test_generate_title_without_actual_topic(self, metadata_manager):
        """Test title generation falling back to draft topic"""
        title = metadata_manager.generate_title(topic="Draft Topic", actual_topic=None)
        assert "Draft Topic" in title
        assert "#Shorts" in title

    def test_generate_title_fallback_date(self, metadata_manager):
        """Test title generation falling back to date"""
        title = metadata_manager.generate_title(topic=None, actual_topic=None)
        today = datetime.now().strftime("%Y년 %m월 %d일")
        assert today in title
        assert "#Shorts" in title

    def test_generate_title_no_duplicate_shorts_tag(self, metadata_manager):
        """Test that #Shorts tag isn't duplicated"""
        title = metadata_manager.generate_title(topic="Test #shorts", actual_topic=None)
        # Should not add another #Shorts
        assert title.count("#shorts") + title.count("#Shorts") == 1

    def test_generate_description_english(self, metadata_manager):
        """Test English description generation"""
        with patch.object(settings, "DEFAULT_DESCRIPTION", "Default Desc"):
            desc = metadata_manager.generate_description(
                language="en",
                original_topic="Test Topic",
                actual_topic="Test Title",
                channel_info={"channel_url": "http://channel.url"},
                recent_videos=[
                    {"title": "V1", "url": "u1"},
                    {"title": "V2", "url": "u2"},
                ],
            )

            assert "Default Desc" in desc
            assert "Test Topic" in desc
            assert "Upload Date:" in desc
            assert "http://channel.url" in desc
            assert "More Videos You Might Like" in desc
            assert "V1" in desc
            assert "u1" in desc

    def test_generate_description_korean(self, metadata_manager):
        """Test Korean description generation"""
        with patch.object(settings, "DEFAULT_DESCRIPTION", "기본 설명"):
            desc = metadata_manager.generate_description(
                language="ko",
                original_topic="테스트 주제",
                actual_topic="테스트 제목",
                channel_info={"channel_url": "http://channel.url"},
                recent_videos=[],
            )

            assert "기본 설명" in desc
            assert "테스트 주제" in desc
            assert "업로드 날짜:" in desc
            assert "함께 보면 좋은 영상" not in desc  # recent_videos empty

    def test_generate_description_no_channel_info(self, metadata_manager):
        """Test description generation without channel info"""
        desc = metadata_manager.generate_description(
            language="en",
            original_topic="Topic",
            actual_topic="Title",
            channel_info=None,
        )
        assert "Subscribe here:" not in desc

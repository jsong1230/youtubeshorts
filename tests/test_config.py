"""
Unit tests for src.core.config.Settings class
"""

import os
from unittest.mock import patch

from src.core.config import Settings


class TestSettings:
    """Test Settings class"""

    def test_settings_initialization(self, monkeypatch):
        """Test Settings class initializes correctly with env vars"""
        monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
        monkeypatch.setenv("CLAUDE_API_KEY", "test_claude_key")
        monkeypatch.setenv("PEXELS_API_KEY", "test_pexels_key")

        settings = Settings()
        assert settings.OPENAI_API_KEY == "test_openai_key"
        assert settings.CLAUDE_API_KEY == "test_claude_key"
        assert settings.PEXELS_API_KEY == "test_pexels_key"

    def test_validate_volume_range(self, monkeypatch, capsys):
        """Test _validate corrects out-of-range volume"""
        monkeypatch.setenv("BACKGROUND_MUSIC_VOLUME", "2.0")
        settings = Settings()
        assert settings.BACKGROUND_MUSIC_VOLUME == 0.25
        captured = capsys.readouterr()
        assert "BACKGROUND_MUSIC_VOLUME" in captured.out

    def test_validate_subtitle_mode(self, monkeypatch, capsys):
        """Test _validate corrects invalid subtitle mode"""
        monkeypatch.setenv("SUBTITLE_MODE", "invalid_mode")
        settings = Settings()
        assert settings.SUBTITLE_MODE == "full_sentence"
        captured = capsys.readouterr()
        assert "SUBTITLE_MODE" in captured.out

    def test_create_directories(self, tmp_path, monkeypatch):
        """Test directory creation"""
        video_dir = tmp_path / "videos"
        thumb_dir = tmp_path / "thumbnails"
        temp_dir = tmp_path / "temp"

        monkeypatch.setenv("VIDEO_OUTPUT_DIR", str(video_dir))
        monkeypatch.setenv("THUMBNAIL_OUTPUT_DIR", str(thumb_dir))
        monkeypatch.setenv("TEMP_DIR", str(temp_dir))

        _ = Settings()

        assert video_dir.exists()
        assert thumb_dir.exists()
        assert temp_dir.exists()

    def test_default_values(self):
        """Test default values are set correctly"""
        # Unset env vars to test defaults
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.AI_API_PROVIDER == "openai"
            assert settings.OPENAI_RPM_LIMIT == 500
            assert settings.USE_BACKGROUND_VIDEO is True
            assert settings.SHORTS_MIN_DURATION == 15

    def test_list_parsing(self, monkeypatch):
        """Test parsing of comma-separated lists"""
        monkeypatch.setenv("DEFAULT_TAGS", "tag1, tag2, tag3")
        settings = Settings()
        assert settings.DEFAULT_TAGS == ["tag1", "tag2", "tag3"]

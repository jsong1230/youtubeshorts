"""
Pytest fixtures and configuration for tests
"""
import os
import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    client = Mock()
    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.create = Mock()
    return client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client"""
    client = Mock()
    client.messages = Mock()
    client.messages.create = Mock()
    return client


@pytest.fixture
def mock_tts_engine():
    """Mock TTS engine"""
    engine = Mock()
    engine.generate_audio = Mock(return_value="mock_audio.mp3")
    return engine


@pytest.fixture
def temp_dir(tmp_path):
    """Temporary directory for test files"""
    return tmp_path


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables"""
    env_vars = {
        'OPENAI_API_KEY': 'test_openai_key',
        'CLAUDE_API_KEY': 'test_claude_key',
        'PEXELS_API_KEY': 'test_pexels_key',
        'VIDEO_OUTPUT_DIR': 'test_output/videos',
        'THUMBNAIL_OUTPUT_DIR': 'test_output/thumbnails',
        'TEMP_DIR': 'test_output/temp',
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def mock_youtube_service():
    """Mock YouTube API service"""
    service = Mock()
    service.videos = Mock(return_value=Mock())
    service.videos().insert = Mock(return_value=Mock())
    service.videos().list = Mock(return_value=Mock())
    service.thumbnails = Mock(return_value=Mock())
    service.thumbnails().set = Mock(return_value=Mock())
    return service


@pytest.fixture
def sample_video_metadata():
    """Sample video metadata for testing"""
    return {
        'title': 'Test Video Title',
        'description': 'Test video description',
        'tags': ['test', 'video', 'shorts'],
        'privacy_status': 'private',
        'category_id': '22'
    }


@pytest.fixture
def temp_video_file(tmp_path):
    """Create a temporary video file for testing"""
    video_file = tmp_path / 'test_video.mp4'
    # Create a minimal file (not a real video, just for testing file operations)
    video_file.write_bytes(b'fake video content')
    return str(video_file)


@pytest.fixture
def temp_thumbnail_file(tmp_path):
    """Create a temporary thumbnail file for testing"""
    thumbnail_file = tmp_path / 'test_thumbnail.jpg'
    # Create a minimal file
    thumbnail_file.write_bytes(b'fake image content')
    return str(thumbnail_file)

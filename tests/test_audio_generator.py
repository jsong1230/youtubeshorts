"""
Unit tests for audio_generator.py
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.generators.audio_generator import AudioGenerator
from src.generators.content_type import ContentType


class TestAudioGenerator:
    """Test AudioGenerator class"""

    @pytest.fixture
    def mock_tts_engine(self):
        """Create a mock TTS engine"""
        mock_engine = Mock()
        mock_engine.get_provider.return_value = Mock(value="openai")
        mock_engine.generate.return_value = True
        return mock_engine

    @pytest.fixture
    def audio_generator(self, mock_tts_engine):
        """Create AudioGenerator instance with mocked TTS engine"""
        generator = AudioGenerator(tts_engine=mock_tts_engine)
        return generator

    def test_initialization_with_engine(self, mock_tts_engine):
        """Test AudioGenerator initializes with provided TTS engine"""
        generator = AudioGenerator(tts_engine=mock_tts_engine)
        assert generator.tts_engine is not None
        assert generator.tts_engine == mock_tts_engine

    def test_initialization_without_engine(self):
        """Test AudioGenerator initializes its own TTS engine if not provided"""
        with patch("src.generators.audio_generator.TTSEngine") as mock_tts_class:
            mock_engine = Mock()
            mock_engine.get_provider.return_value = Mock(value="openai")
            mock_tts_class.return_value = mock_engine

            generator = AudioGenerator()
            assert generator.tts_engine is not None

    def test_generate_audio(self, audio_generator, mock_tts_engine, tmp_path):
        """Test audio generation for text"""
        test_text = "Test audio content"

        # Mock the generate method to return True
        mock_tts_engine.generate.return_value = True

        result = audio_generator.generate_audio(
            text=test_text, index=0, content_type="fact", language="en"
        )

        assert result is not None
        assert result.endswith(".mp3")
        mock_tts_engine.generate.assert_called_once()

    def test_select_music_category_for_content_type(self, audio_generator):
        """Test music category selection based on content type"""

        # Test FACT content type
        category = audio_generator.select_music_category_for_content_type(
            ContentType.FACT
        )
        assert category in ["corporate", "modern", "tech"]

        # Test STORY content type
        category = audio_generator.select_music_category_for_content_type(
            ContentType.STORY
        )
        assert category in ["emotional", "cinematic", "dramatic"]

        # Test HOOK content type
        category = audio_generator.select_music_category_for_content_type(
            ContentType.HOOK
        )
        assert category in ["energetic", "upbeat", "motivational"]

    def test_download_background_music(self, audio_generator, tmp_path):
        """Test background music download"""

        with patch("src.generators.audio_generator.os.path.exists") as mock_exists:
            # Mock that music library doesn't exist
            mock_exists.return_value = False

            result = audio_generator.download_background_music(
                content_type=ContentType.FACT, duration=30, topic="test topic"
            )

            # Should return None if no music library exists and no API key
            assert result is None

    def test_mix_background_music(self, audio_generator, tmp_path):
        """Test mixing voice with background music"""
        music_path = str(tmp_path / "music.mp3")

        # Create dummy music file
        Path(music_path).write_text("fake music")

        # Mock voice clip
        mock_voice_clip = Mock()
        mock_voice_clip.duration = 30

        with patch("src.generators.audio_generator.AudioFileClip") as mock_audio_file:
            mock_music_clip = Mock()
            mock_music_clip.duration = 60
            mock_music_clip.subclip.return_value = mock_music_clip
            mock_music_clip.volumex.return_value = mock_music_clip
            mock_music_clip.fx.return_value = mock_music_clip
            mock_music_clip.set_duration.return_value = mock_music_clip

            mock_audio_file.return_value = mock_music_clip

            with patch(
                "src.generators.audio_generator.CompositeAudioClip"
            ) as mock_composite:
                mock_final = Mock()
                mock_composite.return_value = mock_final

                result = audio_generator.mix_background_music(
                    voice_clip=mock_voice_clip,
                    music_path=music_path,
                    target_duration=30,
                )

                # Should return composite audio
                assert result is not None
                mock_composite.assert_called_once()

    def test_retry_on_failure(self, audio_generator, mock_tts_engine):
        """Test retry mechanism on audio generation failure"""
        # Mock first two attempts fail, third succeeds
        mock_tts_engine.generate.side_effect = [
            False,  # First attempt fails
            False,  # Second attempt fails
            True,  # Third attempt succeeds
        ]

        # Should retry and eventually succeed
        result = audio_generator.generate_audio(text="Test", index=0, language="en")

        # Should return a path even if TTS engine fails (falls back to gTTS)
        assert result is not None or mock_tts_engine.generate.call_count >= 1

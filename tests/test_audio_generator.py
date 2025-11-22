"""
Unit tests for audio_generator.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.generators.audio_generator import AudioGenerator


class TestAudioGenerator:
    """Test AudioGenerator class"""
    
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
        with patch('src.generators.audio_generator.TTSEngine') as mock_tts_class:
            mock_engine = Mock()
            mock_tts_class.return_value = mock_engine
            
            generator = AudioGenerator()
            assert generator.tts_engine is not None
    
    def test_generate_audio(self, audio_generator, mock_tts_engine, tmp_path):
        """Test audio generation for text"""
        test_text = "Test audio content"
        output_path = str(tmp_path / "test_audio.mp3")
        
        mock_tts_engine.generate_audio.return_value = output_path
        
        result = audio_generator.generate_audio(
            text=test_text,
            output_path=output_path,
            language='en'
        )
        
        assert result == output_path
        mock_tts_engine.generate_audio.assert_called_once()
    
    def test_select_music_category_for_content_type(self, audio_generator):
        """Test music category selection based on content type"""
        from src.generators.content_type import ContentType
        
        # Test different content types
        category = audio_generator.select_music_category_for_content_type(ContentType.FACT)
        assert category in ['ambient', 'corporate', 'upbeat']
        
        category = audio_generator.select_music_category_for_content_type(ContentType.STORY)
        assert category in ['ambient', 'cinematic', 'emotional']
        
        category = audio_generator.select_music_category_for_content_type(ContentType.HOOK)
        assert category in ['upbeat', 'energetic']
    
    def test_download_background_music(self, audio_generator, tmp_path):
        """Test background music download"""
        output_path = str(tmp_path / "bg_music.mp3")
        
        with patch('src.generators.audio_generator.requests.get') as mock_get:
            # Mock successful download
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"fake music data"
            mock_get.return_value = mock_response
            
            result = audio_generator.download_background_music(
                category='ambient',
                duration=30,
                output_path=output_path
            )
            
            # Should return a path (either downloaded or fallback)
            assert result is not None
    
    def test_mix_background_music(self, audio_generator, tmp_path):
        """Test mixing voice with background music"""
        voice_path = str(tmp_path / "voice.mp3")
        music_path = str(tmp_path / "music.mp3")
        output_path = str(tmp_path / "mixed.mp3")
        
        # Create dummy files
        Path(voice_path).write_text("fake voice")
        Path(music_path).write_text("fake music")
        
        with patch('src.generators.audio_generator.AudioSegment') as mock_audio:
            mock_voice = Mock()
            mock_music = Mock()
            mock_mixed = Mock()
            
            mock_audio.from_mp3.side_effect = [mock_voice, mock_music]
            mock_voice.__add__ = Mock(return_value=mock_mixed)
            mock_music.__sub__ = Mock(return_value=mock_music)
            
            result = audio_generator.mix_background_music(
                voice_path=voice_path,
                music_path=music_path,
                output_path=output_path,
                music_volume=0.3
            )
            
            # Should attempt to mix audio
            assert mock_audio.from_mp3.called
    
    def test_retry_on_failure(self, audio_generator, mock_tts_engine):
        """Test retry mechanism on audio generation failure"""
        mock_tts_engine.generate_audio.side_effect = [
            Exception("First attempt failed"),
            Exception("Second attempt failed"),
            "success_path.mp3"  # Third attempt succeeds
        ]
        
        # Should retry and eventually succeed
        result = audio_generator.generate_audio(
            text="Test",
            output_path="test.mp3"
        )
        
        assert result == "success_path.mp3"
        assert mock_tts_engine.generate_audio.call_count == 3

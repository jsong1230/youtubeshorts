"""
Unit tests for config.py Settings class
"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import config


class TestSettings:
    """Test Settings class"""
    
    def test_settings_initialization(self, mock_env_vars):
        """Test Settings class initializes correctly"""
        # Import after setting env vars
        from src.core.config import settings
        
        settings = config.Settings()
        assert settings.openai_api_key == 'test_openai_key'
        assert settings.claude_api_key == 'test_claude_key'
        assert settings.pexels_api_key == 'test_pexels_key'
    
    def test_get_bool_true_values(self):
        """Test _get_bool with various true values"""
        from src.core.config import settings
        settings = config.Settings()
        
        with patch.dict(os.environ, {'TEST_BOOL': 'true'}):
            assert settings._get_bool('TEST_BOOL', False) is True
        
        with patch.dict(os.environ, {'TEST_BOOL': '1'}):
            assert settings._get_bool('TEST_BOOL', False) is True
        
        with patch.dict(os.environ, {'TEST_BOOL': 'yes'}):
            assert settings._get_bool('TEST_BOOL', False) is True
    
    def test_get_bool_false_values(self):
        """Test _get_bool with various false values"""
        from src.core.config import settings
        settings = config.Settings()
        
        with patch.dict(os.environ, {'TEST_BOOL': 'false'}):
            assert settings._get_bool('TEST_BOOL', True) is False
        
        with patch.dict(os.environ, {'TEST_BOOL': '0'}):
            assert settings._get_bool('TEST_BOOL', True) is False
        
        with patch.dict(os.environ, {'TEST_BOOL': 'no'}):
            assert settings._get_bool('TEST_BOOL', True) is False
    
    def test_get_bool_default(self):
        """Test _get_bool returns default when env var not set"""
        from src.core.config import settings
        settings = config.Settings()
        
        assert settings._get_bool('NONEXISTENT_VAR', True) is True
        assert settings._get_bool('NONEXISTENT_VAR', False) is False
    
    def test_get_int_valid(self):
        """Test _get_int with valid integer"""
        from src.core.config import settings
        settings = config.Settings()
        
        with patch.dict(os.environ, {'TEST_INT': '42'}):
            assert settings._get_int('TEST_INT', 0) == 42
    
    def test_get_int_invalid(self, capsys):
        """Test _get_int with invalid value returns default"""
        from src.core.config import settings
        settings = config.Settings()
        
        with patch.dict(os.environ, {'TEST_INT': 'not_a_number'}):
            result = settings._get_int('TEST_INT', 10)
            assert result == 10
            captured = capsys.readouterr()
            assert 'TEST_INT' in captured.out
    
    def test_get_float_valid(self):
        """Test _get_float with valid float"""
        from src.core.config import settings
        settings = config.Settings()
        
        with patch.dict(os.environ, {'TEST_FLOAT': '0.5'}):
            assert settings._get_float('TEST_FLOAT', 0.0) == 0.5
    
    def test_get_float_clamping(self):
        """Test _get_float clamps values to 0.0-1.0"""
        from src.core.config import settings
        settings = config.Settings()
        
        with patch.dict(os.environ, {'TEST_FLOAT': '1.5'}):
            assert settings._get_float('TEST_FLOAT', 0.5) == 1.0
        
        with patch.dict(os.environ, {'TEST_FLOAT': '-0.5'}):
            assert settings._get_float('TEST_FLOAT', 0.5) == 0.0
    
    def test_get_list_valid(self):
        """Test _get_list with comma-separated values"""
        from src.core.config import settings
        settings = config.Settings()
        
        with patch.dict(os.environ, {'TEST_LIST': 'a,b,c'}):
            result = settings._get_list('TEST_LIST', 'default')
            assert result == ['a', 'b', 'c']
    
    def test_get_list_with_spaces(self):
        """Test _get_list strips whitespace"""
        from src.core.config import settings
        settings = config.Settings()
        
        with patch.dict(os.environ, {'TEST_LIST': 'a , b , c '}):
            result = settings._get_list('TEST_LIST', 'default')
            assert result == ['a', 'b', 'c']
    
    def test_validate_creates_directories(self, tmp_path, monkeypatch):
        """Test _validate creates required directories"""
        from src.core.config import settings
        
        # Set temp directories
        video_dir = tmp_path / "videos"
        thumb_dir = tmp_path / "thumbnails"
        temp_dir = tmp_path / "temp"
        
        monkeypatch.setenv('VIDEO_OUTPUT_DIR', str(video_dir))
        monkeypatch.setenv('THUMBNAIL_OUTPUT_DIR', str(thumb_dir))
        monkeypatch.setenv('TEMP_DIR', str(temp_dir))
        
        # Create new settings instance
        settings = config.Settings()
        
        # Directories should be created
        assert video_dir.exists()
        assert thumb_dir.exists()
        assert temp_dir.exists()
    
    def test_validate_volume_range(self, capsys):
        """Test _validate corrects out-of-range volume"""
        from src.core.config import settings
        
        with patch.dict(os.environ, {'BACKGROUND_MUSIC_VOLUME': '2.0'}):
            settings = config.Settings()
            assert settings.background_music_volume == 0.25
            captured = capsys.readouterr()
            assert 'BACKGROUND_MUSIC_VOLUME' in captured.out
    
    def test_validate_subtitle_mode(self, capsys):
        """Test _validate corrects invalid subtitle mode"""
        from src.core.config import settings
        
        with patch.dict(os.environ, {'SUBTITLE_MODE': 'invalid_mode'}):
            settings = config.Settings()
            assert settings.subtitle_mode == 'full_sentence'
            captured = capsys.readouterr()
            assert 'SUBTITLE_MODE' in captured.out
    
    def test_backward_compatibility(self, mock_env_vars):
        """Test module-level variables are exposed"""
        # Reimport to get fresh instance
        import importlib
        import src.core.config
        importlib.reload(src.core.config)
        from src.core.config import settings
        importlib.reload(config)
        
        # Module-level variables should exist
        assert hasattr(config, 'OPENAI_API_KEY')
        assert hasattr(config, 'VIDEO_OUTPUT_DIR')
        assert hasattr(config, 'SHORTS_MAX_DURATION')
        
        # Values should match settings
        assert config.OPENAI_API_KEY == config._settings.openai_api_key
        assert config.VIDEO_OUTPUT_DIR == config._settings.video_output_dir
        assert config.SHORTS_MAX_DURATION == config._settings.shorts_max_duration

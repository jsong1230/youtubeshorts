"""
Unit tests for script_generator.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.generators.script_generator import ScriptGenerator
from src.generators.content_type import ContentType


class TestScriptGenerator:
    """Test ScriptGenerator class"""
    
    @pytest.fixture
    def script_generator(self, mock_openai_client, mock_anthropic_client):
        """Create ScriptGenerator instance with mocked clients"""
        generator = ScriptGenerator(
            openai_client=mock_openai_client,
            anthropic_client=mock_anthropic_client
        )
        return generator
    
    def test_initialization(self, script_generator):
        """Test ScriptGenerator initializes correctly"""
        assert script_generator.openai_client is not None
        assert script_generator.anthropic_client is not None
    
    def test_generate_script_with_topic(self, script_generator, mock_openai_client):
        """Test script generation with provided topic"""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Test script content"
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        script = script_generator.generate_script(
            topic="Test Topic",
            duration=55,
            content_type=ContentType.FACT,
            language='en'
        )
        
        assert script is not None
        assert isinstance(script, list)
        assert len(script) > 0
    
    def test_generate_script_with_claude(self, script_generator, mock_anthropic_client):
        """Test script generation using Claude API"""
        # Mock Claude response
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Test script from Claude"
        mock_anthropic_client.messages.create.return_value = mock_response
        
        with patch('config.AI_API_PROVIDER', 'claude'):
            script = script_generator.generate_script(
                topic="Test Topic",
                duration=55,
                content_type=ContentType.STORY,
                language='ko'
            )
            
            assert script is not None
            assert isinstance(script, list)
    
    def test_parse_script_text(self, script_generator):
        """Test script text parsing"""
        script_text = """
        1. First sentence
        2. Second sentence
        3. Third sentence
        """
        
        parsed = script_generator._parse_script_text(script_text)
        
        assert isinstance(parsed, list)
        assert len(parsed) == 3
        assert "First sentence" in parsed[0]
        assert "Second sentence" in parsed[1]
        assert "Third sentence" in parsed[2]
    
    def test_remove_repetitive_phrases(self, script_generator):
        """Test repetitive phrase removal"""
        script = [
            "This is a test sentence.",
            "This is a test sentence.",  # Duplicate
            "Another unique sentence.",
            "This is a test sentence."   # Duplicate again
        ]
        
        cleaned = script_generator._remove_repetitive_phrases(script)
        
        # Should remove exact duplicates
        assert len(cleaned) < len(script)
        assert "This is a test sentence." in cleaned
        assert "Another unique sentence." in cleaned
    
    def test_is_script_unique_new_script(self, script_generator):
        """Test script uniqueness check for new script"""
        script = ["Unique sentence one", "Unique sentence two"]
        
        with patch('src.generators.script_generator.VideoDatabase') as mock_db:
            mock_db_instance = Mock()
            mock_db_instance.get_all_scripts.return_value = []
            mock_db.return_value = mock_db_instance
            
            is_unique = script_generator._is_script_unique(script)
            assert is_unique is True
    
    def test_is_script_unique_duplicate_script(self, script_generator):
        """Test script uniqueness check for duplicate script"""
        script = ["Same sentence", "Another sentence"]
        
        with patch('src.generators.script_generator.VideoDatabase') as mock_db:
            mock_db_instance = Mock()
            # Return existing scripts that match
            mock_db_instance.get_all_scripts.return_value = [
                {"script": "Same sentence\nAnother sentence"}
            ]
            mock_db.return_value = mock_db_instance
            
            is_unique = script_generator._is_script_unique(script)
            assert is_unique is False
    
    def test_build_default_script(self, script_generator):
        """Test default script building"""
        script = script_generator._build_default_script(
            topic="Test Topic",
            language='en'
        )
        
        assert isinstance(script, list)
        assert len(script) > 0
        assert any("Test Topic" in sentence for sentence in script)
    
    def test_get_season(self, script_generator):
        """Test season detection"""
        import datetime
        
        with patch('datetime.datetime') as mock_datetime:
            # Test spring (March)
            mock_datetime.now.return_value = datetime.datetime(2024, 3, 15)
            assert script_generator._get_season() == "spring"
            
            # Test summer (July)
            mock_datetime.now.return_value = datetime.datetime(2024, 7, 15)
            assert script_generator._get_season() == "summer"
            
            # Test fall (October)
            mock_datetime.now.return_value = datetime.datetime(2024, 10, 15)
            assert script_generator._get_season() == "fall"
            
            # Test winter (January)
            mock_datetime.now.return_value = datetime.datetime(2024, 1, 15)
            assert script_generator._get_season() == "winter"
    
    def test_generate_topic_with_strategy(self, script_generator, mock_openai_client):
        """Test topic generation with different strategies"""
        # Mock OpenAI response for AI-generated topics
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "AI Generated Topic"
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        topic, source = script_generator.generate_topic(
            content_type=ContentType.FACT,
            language='en'
        )
        
        assert topic is not None
        assert isinstance(topic, str)
        assert len(topic) > 0
        assert source in ['seasonal', 'performance', 'exploration', 'ai_generated', 
                         'ai_seasonal', 'youtube_trend', 'global_trend']

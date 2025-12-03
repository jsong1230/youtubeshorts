"""
Unit tests for image_generator.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
from PIL import Image

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.generators.image_generator import ImageGenerator


class TestImageGenerator:
    """Test ImageGenerator class"""
    
    @pytest.fixture
    def image_generator(self, mock_openai_client):
        """Create ImageGenerator instance with mocked OpenAI client"""
        generator = ImageGenerator(openai_client=mock_openai_client)
        return generator
    
    def test_initialization(self, image_generator):
        """Test ImageGenerator initializes correctly"""
        assert image_generator.openai_client is not None
    
    def test_prepare_thumbnail_canvas(self, image_generator):
        """Test thumbnail canvas preparation"""
        with patch('os.path.exists', return_value=True):
            with patch('PIL.Image.open') as mock_open:
                mock_img = Mock(spec=Image.Image)
                mock_img.width = 1080
                mock_img.height = 1920
                mock_open.return_value = mock_img
                
                canvas_path = image_generator.prepare_thumbnail_canvas(
                    thumbnail_path="dummy_path.jpg",
                    target_size=(1080, 1920)
                )
        
                assert canvas_path is not None
                assert isinstance(canvas_path, str)
    
    def test_generate_thumbnail_with_dalle(self, image_generator, mock_openai_client, tmp_path):
        """Test thumbnail generation using DALL-E"""
        video_path = str(tmp_path / "test_video.mp4")
        title = "Test Video Title"
        output_path = str(tmp_path / "thumbnail.jpg")
        
        # Mock DALL-E response
        mock_response = Mock()
        mock_response.data = [Mock()]
        mock_response.data[0].url = "https://example.com/image.png"
        mock_openai_client.images.generate.return_value = mock_response
        
        # Mock image download
        with patch('src.generators.image_generator.requests.get') as mock_get:
            mock_get.return_value.content = b"fake image data"
            
            with patch('src.generators.image_generator.Image.open') as mock_open:
                mock_img = Mock(spec=Image.Image)
                mock_img.size = (1024, 1024)
                mock_img.resize.return_value = mock_img
                mock_img.crop.return_value = mock_img
                mock_open.return_value = mock_img
                
                result = image_generator.generate_thumbnail(
                    video_path=video_path,
                    title=title
                )
                
                # Should attempt DALL-E generation
                assert mock_openai_client.images.generate.called
    
    def test_generate_thumbnail_fallback_to_frame(self, image_generator, tmp_path):
        """Test thumbnail generation falls back to video frame extraction"""
        video_path = str(tmp_path / "test_video.mp4")
        title = "Test Video"
        output_path = str(tmp_path / "thumbnail.jpg")
        
        # Mock DALL-E failure
        image_generator.openai_client = None
        
        with patch('src.generators.image_generator.VideoFileClip') as mock_video:
            mock_clip = Mock()
            mock_frame = Mock()
            mock_clip.get_frame.return_value = mock_frame
            mock_clip.duration = 10.0
            mock_video.return_value = mock_clip
            
            with patch('src.generators.image_generator.Image.fromarray') as mock_fromarray:
                mock_img = Mock(spec=Image.Image)
                mock_img.size = (1920, 1080)
                mock_img.resize.return_value = mock_img
                mock_img.crop.return_value = mock_img
                mock_fromarray.return_value = mock_img
                
                result = image_generator.generate_thumbnail(
                    video_path=video_path,
                    title=title
                )
                
                # Should extract frame from video
                assert mock_video.called
    
    def test_embed_thumbnail_frame(self, image_generator, tmp_path):
        """Test embedding thumbnail into video first frame"""
        video_path = str(tmp_path / "test_video.mp4")
        thumbnail_path = str(tmp_path / "thumbnail.jpg")
        
        # Create dummy thumbnail
        dummy_img = Image.new('RGB', (1080, 1920), color='red')
        dummy_img.save(thumbnail_path)
        
        with patch('src.generators.image_generator.VideoFileClip') as mock_video:
            with patch('src.generators.image_generator.ImageClip') as mock_image_clip:
                with patch('src.generators.image_generator.concatenate_videoclips') as mock_concatenate:
                    mock_clip = Mock()
                    mock_clip.duration = 10.0
                    mock_clip.fps = 30
                    mock_video.return_value = mock_clip
                    
                    mock_thumb_clip = Mock()
                    mock_thumb_clip.set_duration.return_value = mock_thumb_clip
                    mock_image_clip.return_value = mock_thumb_clip
                    
                    mock_final = Mock()
                    mock_concatenate.return_value = mock_final
                    
                    image_generator.embed_thumbnail_frame(
                        video_path=video_path,
                        thumbnail_path=thumbnail_path
                    )
                    
                    # Should create composite video
                    assert mock_concatenate.called
    
    # Removed test_dalle_prompt_generation as the method is now internal and inline

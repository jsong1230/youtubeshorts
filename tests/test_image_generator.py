"""
Unit tests for image_generator.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

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
        with patch("os.path.exists", return_value=True):
            with patch("PIL.Image.open") as mock_open:
                # Use MagicMock to handle operations better
                mock_img = MagicMock(spec=Image.Image)
                mock_img.width = 1080
                mock_img.height = 1920
                mock_img.convert.return_value = mock_img
                mock_img.resize.return_value = mock_img
                mock_open.return_value = mock_img

                # We also need to patch Image.new because canvas.dict calls happen later
                with patch("PIL.Image.new") as mock_new:
                    mock_canvas = MagicMock()
                    mock_new.return_value = mock_canvas

                    canvas_path = image_generator.prepare_thumbnail_canvas(
                        thumbnail_path="dummy_path.jpg", target_size=(1080, 1920)
                    )

                    assert canvas_path is not None
                    assert isinstance(canvas_path, str)

    def test_generate_thumbnail_from_video_frame(self, image_generator, tmp_path):
        """Test thumbnail generation from video frame (DALL-E not used)"""
        video_path = str(tmp_path / "test_video.mp4")
        title = "Test Video Title"

        with patch("src.generators.image_generator.VideoFileClip") as mock_video:
            mock_clip = Mock()
            mock_frame = Mock()
            mock_clip.get_frame.return_value = mock_frame
            mock_clip.duration = 10.0
            mock_video.return_value = mock_clip

            with patch(
                "src.generators.image_generator.Image.fromarray"
            ) as mock_fromarray:
                mock_img = Mock(spec=Image.Image)
                mock_img.size = (1920, 1080)
                mock_fromarray.return_value = mock_img

                result = image_generator.generate_thumbnail(
                    video_path=video_path, title=title
                )

                # Should extract frame from video (not use DALL-E)
                assert mock_video.called
                # Result should be a path string or None
                assert result is None or isinstance(result, str)

    def test_embed_thumbnail_frame(self, image_generator, tmp_path):
        """Test embedding thumbnail into video first frame"""
        video_path = str(tmp_path / "test_video.mp4")
        thumbnail_path = str(tmp_path / "thumbnail.jpg")

        # Create dummy files
        with open(video_path, "w") as f:
            f.write("dummy video content")
        with open(thumbnail_path, "w") as f:
            f.write("dummy thumbnail content")

        with patch("src.generators.image_generator.VideoFileClip") as mock_video:
            with patch("src.generators.image_generator.ImageClip") as mock_image_clip:
                with patch(
                    "src.generators.image_generator.concatenate_videoclips"
                ) as mock_concatenate:
                    mock_clip = Mock()
                    mock_clip.duration = 10.0
                    mock_clip.fps = 30
                    mock_video.return_value = mock_clip

                    mock_thumb_clip = Mock()
                    mock_thumb_clip.set_duration.return_value = mock_thumb_clip
                    mock_image_clip.return_value = mock_thumb_clip

                    mock_final = Mock()
                    mock_concatenate.return_value = mock_final

                    # Flatten the prepare_thumbnail_canvas call to return a path
                    with patch.object(
                        image_generator,
                        "prepare_thumbnail_canvas",
                        return_value="dummy_canvas.jpg",
                    ):
                        image_generator.embed_thumbnail_frame(
                            video_path=video_path, thumbnail_path=thumbnail_path
                        )

                    # Should create composite video
                    assert mock_concatenate.called

    # Removed test_dalle_prompt_generation as the method is now internal and inline

import sys
import os
from unittest.mock import MagicMock, patch

# 프로젝트 루트를 sys.path에 추가
sys.path.append(os.getcwd())

from src.generators.media_downloader import MediaDownloader
from src.generators.video.background_video_manager import BackgroundVideoManager
from src.generators.image_generator import ImageGenerator


def test_media_downloader_korean_prompt():
    print("\n--- Testing MediaDownloader Korean Prompt ---")
    mock_openai = MagicMock()
    downloader = MediaDownloader(openai_client=mock_openai)

    # Mock behavior
    mock_openai.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="seoul, hanok, city"))]
    )

    # Test with language='ko'
    downloader.extract_keywords("부자가 되는 법", language="ko")

    # Get the system message from the call
    args, kwargs = mock_openai.chat.completions.create.call_args
    system_msg = kwargs["messages"][0]["content"]

    print(f"System Message for 'ko': {system_msg[:100]}...")
    assert "Korean-specific visual keywords" in system_msg
    print("✅ MediaDownloader correctly includes Korean instructions for language='ko'")


def test_background_video_manager_keywords():
    print("\n--- Testing BackgroundVideoManager Korean Keywords ---")
    mock_downloader = MagicMock()
    # Mock extract_keywords to return a specific list
    mock_downloader.extract_keywords.return_value = ["seoul", "korean"]
    mock_downloader.translate_keyword_to_english.side_effect = lambda x: x

    manager = BackgroundVideoManager(media_downloader=mock_downloader)

    # Test _get_category_keywords for ko
    keywords = manager._get_category_keywords("money", language="ko")
    print(f"Category keywords for 'ko': {keywords}")
    assert "seoul" in keywords
    assert "hanok" in keywords
    print(
        "✅ BackgroundVideoManager includes Korean category keywords for language='ko'"
    )


def test_image_generator_korean_prompt():
    print("\n--- Testing ImageGenerator Korean Thumbnail Prompt ---")
    mock_openai = MagicMock()
    generator = ImageGenerator(openai_client=mock_openai)

    # Mock DALL-E response
    mock_openai.images.generate.return_value = MagicMock(
        data=[MagicMock(url="http://example.com/image.jpg")]
    )

    # Mock http_get_with_retry to avoid downloading
    with patch.object(
        generator,
        "_http_get_with_retry",
        return_value=MagicMock(status_code=200, content=b"fake_image_content"),
    ):
        # Test thumbnail generation with language='ko'
        # Use a try-except because it will fail at PIL Image.open or resize,
        # but we only care about the prompt sent to API.
        try:
            generator._generate_dalle3_thumbnail("부자가 되는 법", language="ko")
        except Exception:
            # Ignore PIL related errors
            pass

    # Get the prompt from the call
    args, kwargs = mock_openai.images.generate.call_args
    prompt = kwargs["prompt"]

    print(f"DALL-E Prompt for 'ko': {prompt[:150]}...")
    assert "modern Korean minimalist design" in prompt
    assert "K-style" in prompt
    print("✅ ImageGenerator includes Korean aesthetic instructions for language='ko'")


if __name__ == "__main__":
    try:
        test_media_downloader_korean_prompt()
        test_background_video_manager_keywords()
        test_image_generator_korean_prompt()
        print("\n✨ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

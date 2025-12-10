import pytest
from unittest.mock import Mock, MagicMock, patch
from src.generators.video.video_editor import VideoEditor


class TestVideoEditor:
    @pytest.fixture
    def mock_dependencies(self):
        audio_generator = Mock()
        subtitle_renderer = Mock()
        background_manager = Mock()
        return audio_generator, subtitle_renderer, background_manager

    @pytest.fixture
    def video_editor(self, mock_dependencies):
        return VideoEditor(*mock_dependencies)

    def test_init(self, video_editor, mock_dependencies):
        """Test initialization"""
        audio_gen, sub_renderer, bg_manager = mock_dependencies
        assert video_editor.audio_generator == audio_gen
        assert video_editor.subtitle_renderer == sub_renderer
        assert video_editor.background_manager == bg_manager

    @patch("src.generators.video.video_editor.concatenate_videoclips")
    @patch("src.generators.video.video_editor.CompositeVideoClip")
    def test_compose_final_video_basic(self, mock_composite, mock_concat, video_editor):
        """Test basic video composition flow"""

        # Create a Fake Clip class to handle property access robustly
        class FakeClip:
            def __init__(self, duration=10.0):
                self.duration = duration
                self.size = (1920, 1080)
                self.audio = None

            def set_duration(self, d):
                self.duration = d
                return self

            def set_fps(self, fps):
                return self

            def resize(self, size):
                return self

            def fx(self, *args):
                return self

            def set_audio(self, audio):
                return self

        # Setup mocks
        fake_bg = FakeClip(10.0)
        mock_concat.return_value = fake_bg

        # The editor creates a wrapper/composite, so let's make that return a fake too
        fake_final = FakeClip(10.0)
        mock_composite.return_value = fake_final

        # Execute
        # Pass fake_bg directly so it is used as base_video_clip when len==1
        result = video_editor.compose_final_video(
            background_clips=[fake_bg],
            subtitle_clips=[],
            audio_clips=[],
            total_duration=10.0,
        )

        # Verify
        assert isinstance(result, FakeClip)
        assert result.duration == 10.0
        # CompositeVideoClip is NOT called if no subtitles are present
        mock_composite.assert_not_called()
        # Since we use a FakeClip, we can't assert_called_with on methods unless we implement call tracking.
        # But we verified the flow completes and returns the expected object with correct duration.

    def test_apply_fade_effects(self, video_editor):
        """Test fade effect application"""
        mock_video = MagicMock()
        duration = 10.0

        # Setup method chaining mocks
        mock_video.fx.return_value = mock_video
        mock_video.set_duration.return_value = mock_video

        result = video_editor.apply_fade_effects(mock_video, duration)

        assert result == mock_video
        # fx should be called twice (fadein, fadeout)
        assert mock_video.fx.call_count == 2
        mock_video.set_duration.assert_called_with(duration)

    @patch("src.generators.video.video_editor.concatenate_audioclips")
    def test_sync_audio_video_match(self, mock_concat_audio, video_editor):
        """Test sync when audio and video durations overlap"""
        mock_video = MagicMock()
        mock_video.duration = 10.0

        mock_audio = MagicMock()
        mock_audio.duration = 10.0
        mock_concat_audio.return_value = mock_audio

        # Setup set_audio return
        mock_video.set_audio.return_value = mock_video
        mock_video.set_duration.return_value = mock_video

        result = video_editor.sync_audio_video(mock_video, [MagicMock()])

        assert result == mock_video
        mock_video.set_audio.assert_called_with(mock_audio)

    def test_prepare_background_clips(self, video_editor):
        """Test background clip preparation"""
        background_groups = [(0, 1, "test.mp4", None)]
        durations = [5.0]

        with patch("os.path.exists", return_value=True):
            video_editor.background_manager.create_background_video_clip.return_value = (
                "clip"
            )

            clips = video_editor.prepare_background_clips(background_groups, durations)

            assert clips == ["clip"]
            video_editor.background_manager.create_background_video_clip.assert_called_with(
                "test.mp4", 5.0, 0, 1
            )

    def test_prepare_background_clips_no_file(self, video_editor):
        """Test fallback to solid color background when background file is missing"""
        background_groups = [(0, 1, "missing.mp4", None)]
        durations = [5.0]

        with patch("os.path.exists", return_value=False):
            # 배경 영상이 없으면 단색 배경으로 폴백 (에러 발생하지 않음)
            clips = video_editor.prepare_background_clips(background_groups, durations)
            # 단색 배경이 생성되었는지 확인
            assert len(clips) == 1
            # ColorClip이 생성되었는지 확인 (타입 체크)
            from moviepy.editor import ColorClip

            assert isinstance(clips[0], ColorClip)

    def test_prepare_subtitle_clips(self, video_editor):
        """Test subtitle clip preparation"""
        script = ["Hello"]
        durations = [2.0]

        mock_sub_clip = MagicMock()
        # Mock set_duration, set_position, set_start chaining
        mock_sub_clip.set_duration.return_value = mock_sub_clip
        mock_sub_clip.set_position.return_value = mock_sub_clip
        mock_sub_clip.set_start.return_value = mock_sub_clip

        # Simulate 'pos' attribute being None initially to test default position logic
        # We use a PropertyMock or just rely on 'pos' not being in dir(mock_sub_clip) or explicitly set to None
        # MagicMock by default creates attributes on access, so let's check the code:
        # if getattr(subtitle_clip, "pos", None) is None:
        # We can just ensure our mock doesn't define 'pos' or it is None.
        del mock_sub_clip.pos

        video_editor.subtitle_renderer.create_subtitle_clip.return_value = mock_sub_clip

        clips = video_editor.prepare_subtitle_clips(script, durations)

        assert len(clips) == 1
        assert clips[0] == mock_sub_clip
        video_editor.subtitle_renderer.create_subtitle_clip.assert_called_with(
            "Hello", 2.0, language="ko"
        )
        mock_sub_clip.set_position.assert_called_with(("center", "bottom"))

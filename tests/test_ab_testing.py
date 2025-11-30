"""
Tests for A/B testing system
"""
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.analytics.ab_testing import ABTestDatabase, VideoStyle


class TestABTestDatabase:
    """Test ABTestDatabase class"""
    
    @pytest.fixture
    def ab_test_db(self, tmp_path):
        """Create a temporary AB test database"""
        db_path = str(tmp_path / "ab_tests.db")
        return ABTestDatabase(db_path=db_path)
    
    def test_init_database(self, ab_test_db):
        """Test database initialization"""
        assert os.path.exists(ab_test_db.db_path)
        # Check if tables are created
        import sqlite3
        conn = sqlite3.connect(ab_test_db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ab_tests'")
        assert cursor.fetchone() is not None
        conn.close()
    
    def test_add_test(self, ab_test_db):
        """Test adding a test entry"""
        result = ab_test_db.add_test(
            video_id="test_video_1",
            topic="Test Topic",
            content_type="HOOK",
            style=VideoStyle.DEFAULT.value,
            style_config={"font_size": 24}
        )
        assert result is True
        
        # Verify the entry was added
        import sqlite3
        conn = sqlite3.connect(ab_test_db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ab_tests WHERE video_id = ?", ("test_video_1",))
        row = cursor.fetchone()
        assert row is not None
        assert row['video_id'] == "test_video_1"
        assert row['topic'] == "Test Topic"
        assert row['content_type'] == "HOOK"
        assert row['style'] == VideoStyle.DEFAULT.value
        conn.close()
    
    def test_add_test_duplicate(self, ab_test_db):
        """Test adding duplicate test entry (should replace)"""
        ab_test_db.add_test(
            video_id="test_video_1",
            topic="Original Topic",
            content_type="HOOK",
            style=VideoStyle.DEFAULT.value
        )
        
        # Add same video_id with different data
        ab_test_db.add_test(
            video_id="test_video_1",
            topic="Updated Topic",
            content_type="QUOTE",
            style=VideoStyle.BOLD.value
        )
        
        # Verify it was updated
        import sqlite3
        conn = sqlite3.connect(ab_test_db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ab_tests WHERE video_id = ?", ("test_video_1",))
        row = cursor.fetchone()
        assert row['topic'] == "Updated Topic"
        assert row['content_type'] == "QUOTE"
        assert row['style'] == VideoStyle.BOLD.value
        conn.close()
    
    def test_update_test_stats(self, ab_test_db):
        """Test updating test statistics"""
        ab_test_db.add_test(
            video_id="test_video_1",
            topic="Test Topic",
            content_type="HOOK",
            style=VideoStyle.DEFAULT.value
        )
        
        result = ab_test_db.update_test_stats(
            video_id="test_video_1",
            views=1000,
            likes=50,
            comments=10,
            watch_time=45.5
        )
        assert result is True
        
        # Verify stats were updated
        import sqlite3
        conn = sqlite3.connect(ab_test_db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ab_tests WHERE video_id = ?", ("test_video_1",))
        row = cursor.fetchone()
        assert row['views'] == 1000
        assert row['likes'] == 50
        assert row['comments'] == 10
        assert row['watch_time'] == 45.5
        # Engagement rate should be calculated: (50 + 10) / 1000 * 100 = 6.0
        assert abs(row['engagement_rate'] - 6.0) < 0.01
        conn.close()
    
    def test_update_test_stats_nonexistent(self, ab_test_db):
        """Test updating stats for non-existent video"""
        result = ab_test_db.update_test_stats(
            video_id="nonexistent_video",
            views=1000
        )
        assert result is False
    
    def test_get_best_style(self, ab_test_db):
        """Test getting best style"""
        # Add multiple tests with different styles (need at least 2 per style)
        styles = [VideoStyle.DEFAULT, VideoStyle.BOLD, VideoStyle.MUSIC]
        for style_idx, style in enumerate(styles):
            # Add 2 tests per style (minimum required)
            for test_idx in range(2):
                i = style_idx * 2 + test_idx
                ab_test_db.add_test(
                    video_id=f"test_video_{i}",
                    topic=f"Test Topic {i}",
                    content_type="HOOK",
                    style=style.value
                )
                # Update stats: BOLD has highest engagement
                # DEFAULT: 5% engagement, MUSIC: 6.67% engagement, BOLD: 15% engagement
                engagement_views = [100, 120, 200, 250, 150, 180][i]
                engagement_likes = [5, 6, 30, 37, 10, 12][i]
                ab_test_db.update_test_stats(
                    video_id=f"test_video_{i}",
                    views=engagement_views,
                    likes=engagement_likes,
                    comments=0
                )
        
        # Get best style (should be BOLD with highest engagement)
        best_style = ab_test_db.get_best_style(
            content_type="HOOK",
            days=30,
            min_views=50
        )
        assert best_style == VideoStyle.BOLD.value
    
    def test_get_best_style_no_data(self, ab_test_db):
        """Test getting best style when no data exists"""
        best_style = ab_test_db.get_best_style()
        assert best_style is None
    
    def test_get_style_performance(self, ab_test_db):
        """Test getting style performance statistics"""
        # Add tests with different styles
        for i, style in enumerate([VideoStyle.DEFAULT, VideoStyle.BOLD]):
            ab_test_db.add_test(
                video_id=f"test_video_{i}",
                topic=f"Test Topic {i}",
                content_type="HOOK",
                style=style.value
            )
            ab_test_db.update_test_stats(
                video_id=f"test_video_{i}",
                views=100 * (i + 1),
                likes=10 * (i + 1),
                comments=2 * (i + 1)
            )
        
        performance = ab_test_db.get_style_performance(
            content_type="HOOK",
            days=30
        )
        
        assert len(performance) == 2
        # Check that performance data includes expected fields
        for perf in performance:
            assert 'style' in perf
            assert 'test_count' in perf
            assert 'avg_engagement_rate' in perf
            assert 'avg_views' in perf
    
    def test_get_best_styles_by_engagement(self, ab_test_db):
        """Test getting best styles by engagement rate"""
        # Add multiple tests per style (need at least min_tests=3)
        styles = [VideoStyle.DEFAULT, VideoStyle.BOLD, VideoStyle.MUSIC]
        for style_idx, style in enumerate(styles):
            # Add 3 tests per style
            for test_idx in range(3):
                i = style_idx * 3 + test_idx
                ab_test_db.add_test(
                    video_id=f"test_video_{i}",
                    topic=f"Test Topic {i}",
                    content_type="HOOK",
                    style=style.value
                )
                # BOLD has highest engagement
                views = [100, 110, 120, 200, 210, 220, 150, 160, 170][i]
                likes = [5, 6, 7, 30, 32, 34, 10, 11, 12][i]
                ab_test_db.update_test_stats(
                    video_id=f"test_video_{i}",
                    views=views,
                    likes=likes,
                    comments=0
                )
        
        best_styles = ab_test_db.get_best_styles_by_engagement(
            days=30,
            min_tests=3,
            min_views=50
        )
        
        assert len(best_styles) > 0
        # First style should be BOLD (highest engagement)
        assert best_styles[0][0] == VideoStyle.BOLD.value
    
    def test_get_test_by_video_id(self, ab_test_db):
        """Test getting test by video ID"""
        # Add a test
        ab_test_db.add_test(
            video_id="test_video_1",
            topic="Test Topic",
            content_type="HOOK",
            style=VideoStyle.DEFAULT.value
        )
        
        test = ab_test_db.get_test_by_video_id("test_video_1")
        assert test is not None
        assert test['video_id'] == "test_video_1"
        assert test['topic'] == "Test Topic"
        
        # Test non-existent video
        test = ab_test_db.get_test_by_video_id("nonexistent")
        assert test is None


class TestVideoStyle:
    """Test VideoStyle enum"""
    
    def test_video_style_values(self):
        """Test VideoStyle enum values"""
        assert VideoStyle.DEFAULT.value == "default"
        assert VideoStyle.MINIMAL.value == "minimal"
        assert VideoStyle.BOLD.value == "bold"
        assert VideoStyle.MUSIC.value == "music"
        assert VideoStyle.NO_MUSIC.value == "no_music"
        assert VideoStyle.GRADIENT.value == "gradient"
        assert VideoStyle.VIDEO_BG.value == "video_bg"

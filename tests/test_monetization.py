"""
Tests for monetization tracking system
"""

import os
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.analytics.monetization import MonetizationTracker


class TestMonetizationTracker:
    """Test MonetizationTracker class"""

    @pytest.fixture
    def monetization_tracker(self, tmp_path):
        """Create a temporary monetization tracker"""
        # Mock YouTubeUploader to avoid actual API calls
        with patch("src.analytics.monetization.YouTubeUploader") as mock_uploader_class:
            mock_uploader = Mock()
            mock_uploader.get_video_stats = Mock(
                return_value={"views": 1000, "likes": 50, "comments": 10}
            )
            mock_uploader_class.return_value = mock_uploader

            # Set data file path to temp directory
            data_file = str(tmp_path / "monetization_data.json")

            # Create tracker with custom data file
            tracker = MonetizationTracker()
            tracker.data_file = data_file

            # Initialize with empty data
            tracker.data = {
                "videos": [],
                "stats": {
                    "total_views": 0,
                    "total_likes": 0,
                    "total_comments": 0,
                    "total_revenue": 0,
                    "total_videos": 0,
                },
                "monthly_revenue": {},
                "start_date": datetime.now().isoformat(),
            }
            tracker._save_data()

            yield tracker

    def test_init_creates_data_file(self, monetization_tracker):
        """Test that initialization creates data file"""
        assert os.path.exists(monetization_tracker.data_file)
        assert "videos" in monetization_tracker.data
        assert "stats" in monetization_tracker.data

    def test_add_video(self, monetization_tracker):
        """Test adding a video"""
        monetization_tracker.add_video(
            video_id="test_video_1",
            title="Test Video",
            upload_date=datetime.now().isoformat(),
        )

        assert len(monetization_tracker.data["videos"]) == 1
        video = monetization_tracker.data["videos"][0]
        assert video["video_id"] == "test_video_1"
        assert video["title"] == "Test Video"
        assert video["views"] == 0
        assert video["revenue"] == 0

    def test_add_video_auto_date(self, monetization_tracker):
        """Test adding video with auto-generated date"""
        monetization_tracker.add_video(video_id="test_video_1", title="Test Video")

        video = monetization_tracker.data["videos"][0]
        assert video["upload_date"] is not None
        # Verify it's a valid ISO format date
        datetime.fromisoformat(video["upload_date"])

    def test_update_video_stats(self, monetization_tracker):
        """Test updating video statistics"""
        monetization_tracker.add_video(video_id="test_video_1", title="Test Video")

        # Set CPM before updating stats
        monetization_tracker.data["videos"][0]["cpm"] = 1.0

        monetization_tracker.update_video_stats("test_video_1")

        video = monetization_tracker.data["videos"][0]
        assert video["views"] == 1000
        assert video["likes"] == 50
        assert video["comments"] == 10
        # Revenue is calculated based on views and CPM
        # With 1000 views and CPM of 1.0, revenue should be 1.0
        assert video["revenue"] == 1.0

    def test_update_video_stats_nonexistent(self, monetization_tracker):
        """Test updating stats for non-existent video"""
        # Should not raise error, just return
        monetization_tracker.update_video_stats("nonexistent_video")

    def test_calculate_revenue(self, monetization_tracker):
        """Test revenue calculation"""
        # Test with default CPM
        revenue = monetization_tracker._calculate_revenue(views=1000)
        assert revenue == 1.0  # 1000 views * $1.00 CPM / 1000 = $1.00

        # Test with custom CPM
        revenue = monetization_tracker._calculate_revenue(views=1000, cpm=2.5)
        assert revenue == 2.5  # 1000 views * $2.50 CPM / 1000 = $2.50

        # Test with larger view count
        revenue = monetization_tracker._calculate_revenue(views=100000, cpm=1.5)
        assert revenue == 150.0  # 100000 views * $1.50 CPM / 1000 = $150.00

    def test_update_total_stats(self, monetization_tracker):
        """Test updating total statistics"""
        # Clear any existing videos
        monetization_tracker.data["videos"] = []

        # Add multiple videos with stats
        for i in range(3):
            monetization_tracker.add_video(
                video_id=f"test_video_{i}", title=f"Test Video {i}"
            )
            monetization_tracker.data["videos"][i]["views"] = 1000 * (i + 1)
            monetization_tracker.data["videos"][i]["likes"] = 50 * (i + 1)
            monetization_tracker.data["videos"][i]["comments"] = 10 * (i + 1)
            monetization_tracker.data["videos"][i]["revenue"] = 1.0 * (i + 1)

        monetization_tracker._update_total_stats()

        stats = monetization_tracker.data["stats"]
        assert stats["total_views"] == 6000  # 1000 + 2000 + 3000
        assert stats["total_likes"] == 300  # 50 + 100 + 150
        assert stats["total_comments"] == 60  # 10 + 20 + 30
        assert stats["total_revenue"] == 6.0  # 1.0 + 2.0 + 3.0

    def test_calculate_monthly_revenue(self, monetization_tracker):
        """Test monthly revenue calculation"""
        # Add videos from different months
        now = datetime.now()
        for i in range(3):
            video_date = now - timedelta(days=i * 35)  # Spread across months
            monetization_tracker.add_video(
                video_id=f"test_video_{i}",
                title=f"Test Video {i}",
                upload_date=video_date.isoformat(),
            )
            monetization_tracker.data["videos"][i]["revenue"] = 10.0 * (i + 1)

        monetization_tracker._calculate_monthly_revenue()

        monthly = monetization_tracker.data["monthly_revenue"]
        assert len(monthly) > 0
        # Check that revenue is grouped by month
        total_monthly = sum(monthly.values())
        assert total_monthly > 0

    def test_get_progress_report(self, monetization_tracker):
        """Test getting progress report"""
        # Add a video
        monetization_tracker.add_video(
            video_id="test_video_1",
            title="Test Video",
            upload_date=(datetime.now() - timedelta(days=30)).isoformat(),
        )
        monetization_tracker.data["videos"][0]["views"] = 1000
        monetization_tracker.data["videos"][0]["revenue"] = 1.0
        monetization_tracker._update_total_stats()

        report = monetization_tracker.get_progress_report()

        assert "total_videos" in report
        assert "days_since_start" in report
        assert "days_until_monetization" in report
        assert "total_views" in report
        assert "total_revenue" in report
        assert "monthly_revenue" in report
        assert "avg_views_per_video" in report
        assert "estimated_monthly_revenue" in report
        assert "target_revenue_range" in report
        assert "on_track" in report

        assert report["total_videos"] == 1
        assert report["total_views"] == 1000
        assert report["total_revenue"] == 1.0

    def test_get_progress_report_no_videos(self, monetization_tracker):
        """Test progress report with no videos"""
        report = monetization_tracker.get_progress_report()

        assert report["total_videos"] == 0
        assert report["days_since_start"] == 0
        assert report["total_views"] == 0
        assert report["total_revenue"] == 0

    def test_update_all_videos(self, monetization_tracker):
        """Test updating all videos"""
        # Add multiple videos
        for i in range(3):
            monetization_tracker.add_video(
                video_id=f"test_video_{i}", title=f"Test Video {i}"
            )

        monetization_tracker.update_all_videos()

        # Verify all videos were updated
        for video in monetization_tracker.data["videos"]:
            assert video["views"] == 1000  # From mock
            assert video["likes"] == 50
            assert video["comments"] == 10

    def test_save_and_load_data(self, monetization_tracker):
        """Test saving and loading data"""
        # Add a video
        monetization_tracker.add_video(video_id="test_video_1", title="Test Video")

        # Save data
        monetization_tracker._save_data()

        # Verify file exists and contains data
        assert os.path.exists(monetization_tracker.data_file)
        with open(monetization_tracker.data_file, "r") as f:
            saved_data = json.load(f)
            assert len(saved_data["videos"]) == 1
            assert saved_data["videos"][0]["video_id"] == "test_video_1"

        # Create new tracker instance and verify it loads the data
        new_tracker = MonetizationTracker()
        new_tracker.data_file = monetization_tracker.data_file
        new_tracker._load_data()
        assert len(new_tracker.data["videos"]) == 1
        assert new_tracker.data["videos"][0]["video_id"] == "test_video_1"

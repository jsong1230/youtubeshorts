"""
Performance metrics tracking for YouTube Shorts automation.
Tracks video generation time, API calls, and system performance.
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PerformanceTracker:
    """Track and analyze performance metrics."""

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize PerformanceTracker.

        Args:
            storage_path: Path to store metrics (default: logs/performance_metrics.json)
        """
        if storage_path is None:
            storage_path = os.path.join(os.getcwd(), "logs", "performance_metrics.json")

        self.storage_path = storage_path
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)

        # Load existing metrics
        self.metrics = self._load_metrics()

    def _load_metrics(self) -> Dict:
        """Load metrics from storage."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass

        return {"video_generations": [], "api_calls": [], "errors": []}

    def _save_metrics(self):
        """Save metrics to storage."""
        try:
            with open(self.storage_path, "w") as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save metrics: {e}")

    def track_video_generation(
        self,
        duration: float,
        success: bool,
        video_length: float,
        api_calls: int,
        file_size: int,
        topic: str = None,
        error: str = None,
    ):
        """
        Track video generation metrics.

        Args:
            duration: Generation time in seconds
            success: Whether generation succeeded
            video_length: Video duration in seconds
            api_calls: Number of API calls made
            file_size: Output file size in bytes
            topic: Video topic
            error: Error message if failed
        """
        metric = {
            "timestamp": datetime.now().isoformat(),
            "duration": duration,
            "success": success,
            "video_length": video_length,
            "api_calls": api_calls,
            "file_size": file_size,
            "topic": topic,
            "error": error,
        }

        self.metrics["video_generations"].append(metric)
        self._save_metrics()

    def track_api_call(
        self,
        service: str,
        endpoint: str,
        duration: float,
        success: bool,
        error: str = None,
    ):
        """
        Track API call metrics.

        Args:
            service: API service name (openai, pexels, youtube)
            endpoint: API endpoint called
            duration: Call duration in seconds
            success: Whether call succeeded
            error: Error message if failed
        """
        metric = {
            "timestamp": datetime.now().isoformat(),
            "service": service,
            "endpoint": endpoint,
            "duration": duration,
            "success": success,
            "error": error,
        }

        self.metrics["api_calls"].append(metric)
        self._save_metrics()

    def track_error(self, error_type: str, message: str, context: Dict = None):
        """
        Track error occurrence.

        Args:
            error_type: Type of error
            message: Error message
            context: Additional context
        """
        metric = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "message": message,
            "context": context or {},
        }

        self.metrics["errors"].append(metric)
        self._save_metrics()

    def get_summary(self, last_n_days: int = 7) -> Dict:
        """
        Get performance summary.

        Args:
            last_n_days: Number of days to include in summary

        Returns:
            Summary statistics
        """
        from datetime import timedelta

        cutoff_time = datetime.now() - timedelta(days=last_n_days)

        # Filter recent metrics
        recent_videos = [
            v
            for v in self.metrics["video_generations"]
            if datetime.fromisoformat(v["timestamp"]) > cutoff_time
        ]

        recent_api_calls = [
            a
            for a in self.metrics["api_calls"]
            if datetime.fromisoformat(a["timestamp"]) > cutoff_time
        ]

        recent_errors = [
            e
            for e in self.metrics["errors"]
            if datetime.fromisoformat(e["timestamp"]) > cutoff_time
        ]

        # Calculate statistics
        total_videos = len(recent_videos)
        successful_videos = len([v for v in recent_videos if v["success"]])

        avg_generation_time = (
            sum(v["duration"] for v in recent_videos) / total_videos
            if total_videos > 0
            else 0
        )

        avg_api_calls = (
            sum(v["api_calls"] for v in recent_videos) / total_videos
            if total_videos > 0
            else 0
        )

        total_api_calls = len(recent_api_calls)
        successful_api_calls = len([a for a in recent_api_calls if a["success"]])

        return {
            "period_days": last_n_days,
            "video_generation": {
                "total": total_videos,
                "successful": successful_videos,
                "success_rate": (
                    successful_videos / total_videos if total_videos > 0 else 0
                ),
                "avg_duration": avg_generation_time,
                "avg_api_calls": avg_api_calls,
            },
            "api_calls": {
                "total": total_api_calls,
                "successful": successful_api_calls,
                "success_rate": (
                    successful_api_calls / total_api_calls if total_api_calls > 0 else 0
                ),
            },
            "errors": {"total": len(recent_errors)},
        }

    def print_summary(self, last_n_days: int = 7):
        """Print performance summary to console."""
        summary = self.get_summary(last_n_days)

        logger.info(f"\n📊 Performance Summary (Last {last_n_days} Days)")
        logger.info("=" * 60)

        # Video generation stats
        vg = summary["video_generation"]
        logger.info("\n🎬 Video Generation:")
        logger.info(f"  Total: {vg['total']}")
        logger.info(f"  Successful: {vg['successful']} ({vg['success_rate']*100:.1f}%)")
        logger.info(f"  Avg Duration: {vg['avg_duration']:.1f}s")
        logger.info(f"  Avg API Calls: {vg['avg_api_calls']:.1f}")

        # API call stats
        api = summary["api_calls"]
        logger.info("\n🔌 API Calls:")
        logger.info(f"  Total: {api['total']}")
        logger.info(
            f"  Successful: {api['successful']} ({api['success_rate']*100:.1f}%)"
        )

        # Error stats
        err = summary["errors"]
        logger.info("\n❌ Errors:")
        logger.info(f"  Total: {err['total']}")

        logger.info("\n" + "=" * 60)


# Global performance tracker instance
_performance_tracker = None


def get_performance_tracker() -> PerformanceTracker:
    """Get or create the global PerformanceTracker instance."""
    global _performance_tracker
    if _performance_tracker is None:
        _performance_tracker = PerformanceTracker()
    return _performance_tracker

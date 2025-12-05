"""
고급 분석 및 최적화 시스템
머신러닝 기반 성과 예측, 자동 최적화, 경쟁사 분석, 시청자 세그먼트 분석
"""

import sqlite3
import os
import json
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict

from src.utils.logger import get_logger

logger = get_logger(__name__)
from src.pipeline.database import VideoDatabase
from src.analytics.ab_testing import ABTestDatabase
from src.analytics.thumbnail_optimizer import ThumbnailOptimizer
from src.pipeline.topic_database import TopicDatabase


class PerformancePredictor:
    """머신러닝 기반 성과 예측 클래스"""

    def __init__(self, db_path: str = "data/advanced_analytics.db"):
        """
        성과 예측 시스템 초기화

        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = db_path
        data_dir = os.path.dirname(db_path)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """데이터베이스 테이블 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # predictions 테이블 생성
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT,
                topic TEXT,
                content_type TEXT,
                predicted_views INTEGER,
                predicted_engagement_rate REAL,
                predicted_likes INTEGER,
                confidence REAL,
                features TEXT,  -- JSON 형식의 특징 벡터
                created_at TEXT NOT NULL
            )
        """
        )

        # prediction_accuracy 테이블 생성 (예측 정확도 추적)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS prediction_accuracy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT,
                predicted_views INTEGER,
                actual_views INTEGER,
                error_rate REAL,
                created_at TEXT NOT NULL
            )
        """
        )

        conn.commit()
        conn.close()

    def extract_features(self, video_data: Dict) -> Dict:
        """
        영상 데이터에서 특징 추출

        Args:
            video_data: 영상 데이터 (topic, content_type, upload_time, style 등)

        Returns:
            특징 벡터 딕셔너리
        """
        features = {
            "topic_length": len(video_data.get("topic", "")),
            "content_type": video_data.get("content_type", "auto"),
            "upload_hour": video_data.get("upload_hour", 12),
            "upload_day_of_week": video_data.get("upload_day_of_week", 0),  # 0=월요일
            "has_background_music": video_data.get("has_background_music", True),
            "thumbnail_style": video_data.get("thumbnail_style", "dalle3"),
            "video_style": video_data.get("video_style", "default"),
            "title_length": len(video_data.get("title", "")),
            "description_length": len(video_data.get("description", "")),
        }

        # 주제 카테고리 인코딩
        topic = video_data.get("topic", "").lower()
        features["is_finance"] = (
            1
            if any(
                k in topic
                for k in [
                    "money",
                    "finance",
                    "invest",
                    "budget",
                    "save",
                    "돈",
                    "재태크",
                    "투자",
                ]
            )
            else 0
        )
        features["is_productivity"] = (
            1
            if any(
                k in topic
                for k in ["productivity", "habit", "routine", "time", "생산성", "습관"]
            )
            else 0
        )
        features["is_lifestyle"] = (
            1
            if any(
                k in topic
                for k in ["life", "lifestyle", "health", "wellness", "라이프", "건강"]
            )
            else 0
        )

        return features

    def predict_performance(
        self, video_data: Dict, historical_data: List[Dict] = None
    ) -> Dict:
        """
        영상 성과 예측 (간단한 선형 회귀 기반)

        Args:
            video_data: 예측할 영상 데이터
            historical_data: 과거 영상 데이터 (없으면 데이터베이스에서 가져옴)

        Returns:
            예측 결과 딕셔너리 (predicted_views, predicted_engagement_rate, predicted_likes, confidence)
        """
        try:
            # 특징 추출
            features = self.extract_features(video_data)

            # 과거 데이터가 없으면 데이터베이스에서 가져오기
            if historical_data is None:
                historical_data = self._get_historical_data()

            if len(historical_data) < 10:
                # 데이터가 부족하면 기본값 반환
                return {
                    "predicted_views": 100,
                    "predicted_engagement_rate": 2.0,
                    "predicted_likes": 5,
                    "confidence": 0.3,
                }

            # 간단한 선형 회귀 기반 예측
            # 1. 주제별 평균 성과 계산
            topic = video_data.get("topic", "")
            topic_avg = self._calculate_topic_average(topic, historical_data)

            # 2. 콘텐츠 타입별 평균 성과 계산
            content_type = video_data.get("content_type", "auto")
            content_type_avg = self._calculate_content_type_average(
                content_type, historical_data
            )

            # 3. 업로드 시간별 평균 성과 계산
            upload_hour = video_data.get("upload_hour", 12)
            time_avg = self._calculate_time_average(upload_hour, historical_data)

            # 4. 스타일별 평균 성과 계산
            video_style = video_data.get("video_style", "default")
            style_avg = self._calculate_style_average(video_style, historical_data)

            # 5. 가중 평균으로 예측 (주제 40%, 콘텐츠 타입 30%, 시간 20%, 스타일 10%)
            predicted_views = int(
                topic_avg["views"] * 0.4
                + content_type_avg["views"] * 0.3
                + time_avg["views"] * 0.2
                + style_avg["views"] * 0.1
            )

            predicted_engagement_rate = (
                topic_avg["engagement_rate"] * 0.4
                + content_type_avg["engagement_rate"] * 0.3
                + time_avg["engagement_rate"] * 0.2
                + style_avg["engagement_rate"] * 0.1
            )

            predicted_likes = int(predicted_views * predicted_engagement_rate / 100)

            # 신뢰도 계산 (데이터 양 기반)
            confidence = min(0.9, 0.3 + (len(historical_data) / 100) * 0.6)

            # 예측 결과 저장
            self._save_prediction(
                video_data.get("video_id"),
                features,
                {
                    "predicted_views": predicted_views,
                    "predicted_engagement_rate": predicted_engagement_rate,
                    "predicted_likes": predicted_likes,
                    "confidence": confidence,
                },
            )

            return {
                "predicted_views": predicted_views,
                "predicted_engagement_rate": predicted_engagement_rate,
                "predicted_likes": predicted_likes,
                "confidence": confidence,
            }
        except Exception as e:
            logger.warning(f"⚠️ 성과 예측 실패: {e}")
            return {
                "predicted_views": 100,
                "predicted_engagement_rate": 2.0,
                "predicted_likes": 5,
                "confidence": 0.3,
            }

    def _get_historical_data(self) -> List[Dict]:
        """과거 영상 데이터 가져오기"""
        try:
            video_db = VideoDatabase()
            ab_test_db = ABTestDatabase()

            # 최근 90일 데이터 가져오기
            cutoff_date = (datetime.now() - timedelta(days=90)).isoformat()

            conn = sqlite3.connect(video_db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM videos
                WHERE upload_date >= ?
                ORDER BY upload_date DESC
            """,
                (cutoff_date,),
            )

            videos = []
            for row in cursor.fetchall():
                video = dict(row)

                # A/B 테스트 데이터 추가
                ab_test = ab_test_db.get_test_by_video_id(video["video_id"])
                if ab_test:
                    video["video_style"] = ab_test.get("style", "default")
                    video["style_config"] = ab_test.get("style_config")

                videos.append(video)

            conn.close()
            return videos
        except Exception as e:
            logger.warning(f"⚠️ 과거 데이터 가져오기 실패: {e}")
            return []

    def _calculate_topic_average(self, topic: str, historical_data: List[Dict]) -> Dict:
        """주제별 평균 성과 계산"""
        topic_videos = [
            v for v in historical_data if topic.lower() in v.get("topic", "").lower()
        ]

        if not topic_videos:
            # 주제가 없으면 전체 평균
            return self._calculate_overall_average(historical_data)

        views = [v.get("views", 0) for v in topic_videos]
        engagement_rates = [v.get("engagement_rate", 0) for v in topic_videos]

        return {
            "views": np.mean(views) if views else 0,
            "engagement_rate": np.mean(engagement_rates) if engagement_rates else 0,
        }

    def _calculate_content_type_average(
        self, content_type: str, historical_data: List[Dict]
    ) -> Dict:
        """콘텐츠 타입별 평균 성과 계산"""
        # topic_database에서 content_type 정보 가져오기
        topic_db = TopicDatabase()

        # 간단하게 전체 평균 반환 (실제로는 content_type별로 필터링 필요)
        return self._calculate_overall_average(historical_data)

    def _calculate_time_average(
        self, upload_hour: int, historical_data: List[Dict]
    ) -> Dict:
        """업로드 시간별 평균 성과 계산"""
        # 업로드 시간 추출 (upload_date에서)
        time_videos = []
        for v in historical_data:
            try:
                upload_date = datetime.fromisoformat(v.get("upload_date", ""))
                if upload_date.hour == upload_hour:
                    time_videos.append(v)
            except:
                continue

        if not time_videos:
            return self._calculate_overall_average(historical_data)

        views = [v.get("views", 0) for v in time_videos]
        engagement_rates = [v.get("engagement_rate", 0) for v in time_videos]

        return {
            "views": np.mean(views) if views else 0,
            "engagement_rate": np.mean(engagement_rates) if engagement_rates else 0,
        }

    def _calculate_style_average(
        self, video_style: str, historical_data: List[Dict]
    ) -> Dict:
        """스타일별 평균 성과 계산"""
        style_videos = [
            v for v in historical_data if v.get("video_style") == video_style
        ]

        if not style_videos:
            return self._calculate_overall_average(historical_data)

        views = [v.get("views", 0) for v in style_videos]
        engagement_rates = [v.get("engagement_rate", 0) for v in style_videos]

        return {
            "views": np.mean(views) if views else 0,
            "engagement_rate": np.mean(engagement_rates) if engagement_rates else 0,
        }

    def _calculate_overall_average(self, historical_data: List[Dict]) -> Dict:
        """전체 평균 성과 계산"""
        if not historical_data:
            return {"views": 100, "engagement_rate": 2.0}

        views = [v.get("views", 0) for v in historical_data]
        engagement_rates = [v.get("engagement_rate", 0) for v in historical_data]

        return {
            "views": np.mean(views) if views else 0,
            "engagement_rate": np.mean(engagement_rates) if engagement_rates else 0,
        }

    def _save_prediction(self, video_id: str, features: Dict, prediction: Dict):
        """예측 결과 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now().isoformat()

            cursor.execute(
                """
                INSERT INTO predictions
                (video_id, predicted_views, predicted_engagement_rate, predicted_likes, confidence, features, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    video_id,
                    prediction["predicted_views"],
                    prediction["predicted_engagement_rate"],
                    prediction["predicted_likes"],
                    prediction["confidence"],
                    json.dumps(features),
                    now,
                ),
            )

            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"⚠️ 예측 결과 저장 실패: {e}")

    def update_prediction_accuracy(self, video_id: str, actual_views: int):
        """예측 정확도 업데이트"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 예측 결과 가져오기
            cursor.execute(
                """
                SELECT predicted_views FROM predictions
                WHERE video_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (video_id,),
            )

            row = cursor.fetchone()
            if row:
                predicted_views = row[0]
                error_rate = (
                    abs(predicted_views - actual_views) / max(actual_views, 1) * 100
                )

                now = datetime.now().isoformat()
                cursor.execute(
                    """
                    INSERT INTO prediction_accuracy
                    (video_id, predicted_views, actual_views, error_rate, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (video_id, predicted_views, actual_views, error_rate, now),
                )

                conn.commit()

            conn.close()
        except Exception as e:
            logger.warning(f"⚠️ 예측 정확도 업데이트 실패: {e}")


class AutoOptimizer:
    """자동 최적화 시스템 (주제, 시간, 스타일 등)"""

    def __init__(self):
        self.predictor = PerformancePredictor()
        self.video_db = VideoDatabase()
        self.ab_test_db = ABTestDatabase()
        self.topic_db = TopicDatabase()
        self.thumbnail_optimizer = ThumbnailOptimizer()

    def optimize_topic_selection(self, content_type: str = None) -> Optional[str]:
        """
        주제 선택 최적화

        Args:
            content_type: 콘텐츠 타입

        Returns:
            최적 주제 또는 None
        """
        try:
            # 1. 성과가 좋은 주제 가져오기
            high_performing_topics = self.topic_db.get_high_performing_topics(
                content_type=content_type, days=30, min_engagement_rate=1.0, limit=10
            )

            if high_performing_topics:
                # 가장 성과가 좋은 주제 선택 (리스트이므로 첫 번째 요소)
                if isinstance(high_performing_topics[0], str):
                    return high_performing_topics[0]
                elif isinstance(high_performing_topics[0], dict):
                    return high_performing_topics[0].get("topic")

            # 2. 성과가 좋은 주제가 없으면 트렌드 주제 선택
            from src.analytics.trend_collector import TrendCollector

            trend_collector = TrendCollector()
            trending_keywords = trend_collector.collect_trending_keywords(max_videos=30)

            if trending_keywords:
                return trending_keywords[0]

            return None
        except Exception as e:
            logger.warning(f"⚠️ 주제 선택 최적화 실패: {e}")
            return None

    def optimize_upload_time(self) -> int:
        """
        업로드 시간 최적화

        Returns:
            최적 업로드 시간 (0-23)
        """
        try:
            historical_data = self.predictor._get_historical_data()

            # 시간별 평균 성과 계산
            hour_performance: Dict[int, Dict[str, List[float]]] = defaultdict(
                lambda: {"views": [], "engagement_rate": []}
            )

            for video in historical_data:
                try:
                    upload_date = datetime.fromisoformat(video.get("upload_date", ""))
                    hour = upload_date.hour

                    hour_performance[hour]["views"].append(video.get("views", 0))
                    hour_performance[hour]["engagement_rate"].append(
                        video.get("engagement_rate", 0)
                    )
                except:
                    continue

            # 시간별 평균 계산
            hour_avg = {}
            for hour, data in hour_performance.items():
                if data["views"]:
                    hour_avg[hour] = {
                        "avg_views": np.mean(data["views"]),
                        "avg_engagement": np.mean(data["engagement_rate"]),
                    }

            if hour_avg:
                # 평균 조회수가 가장 높은 시간 선택
                best_hour = max(hour_avg.keys(), key=lambda h: hour_avg[h]["avg_views"])
                return best_hour

            # 기본값: 오전 9시
            return 9
        except Exception as e:
            logger.warning(f"⚠️ 업로드 시간 최적화 실패: {e}")
            return 9

    def optimize_video_style(self, content_type: str) -> str:
        """
        영상 스타일 최적화

        Args:
            content_type: 콘텐츠 타입

        Returns:
            최적 영상 스타일
        """
        try:
            best_style = self.ab_test_db.get_best_style(
                content_type=content_type, days=30, min_views=50
            )

            if best_style:
                return best_style

            # 기본값
            return "default"
        except Exception as e:
            logger.warning(f"⚠️ 영상 스타일 최적화 실패: {e}")
            return "default"

    def optimize_thumbnail_style(self) -> str:
        """
        썸네일 스타일 최적화

        Returns:
            최적 썸네일 스타일
        """
        try:
            best_style = self.thumbnail_optimizer.get_best_thumbnail_style(
                days=30, min_impressions=100
            )

            if best_style:
                return best_style

            # 기본값: DALL-E 3
            return "dalle3"
        except Exception as e:
            logger.warning(f"⚠️ 썸네일 스타일 최적화 실패: {e}")
            return "dalle3"

    def get_optimization_recommendations(self) -> Dict:
        """
        종합 최적화 권장사항 가져오기

        Returns:
            최적화 권장사항 딕셔너리
        """
        return {
            "best_upload_time": self.optimize_upload_time(),
            "best_thumbnail_style": self.optimize_thumbnail_style(),
            "recommended_topics": self.optimize_topic_selection(),
            "recommended_styles": {
                "hook": self.optimize_video_style("hook"),
                "quote": self.optimize_video_style("quote"),
                "story": self.optimize_video_style("story"),
                "fact": self.optimize_video_style("fact"),
            },
        }


class CompetitorAnalyzer:
    """경쟁사 분석 및 벤치마킹 클래스"""

    def __init__(self):
        self.video_db = VideoDatabase()

    def analyze_competitor_channel(self, channel_id: str, days: int = 30) -> Dict:
        """
        경쟁사 채널 분석

        Args:
            channel_id: YouTube 채널 ID
            days: 분석 기간 (일)

        Returns:
            경쟁사 채널 분석 결과
        """
        try:
            from src.uploaders.youtube_uploader import YouTubeUploader

            uploader = YouTubeUploader()

            # 채널 정보 가져오기 (YouTube API 사용)
            # 실제 구현 시 YouTube Data API v3 사용 필요

            return {
                "channel_id": channel_id,
                "subscriber_count": 0,
                "total_views": 0,
                "avg_views_per_video": 0,
                "avg_engagement_rate": 0,
                "upload_frequency": 0,
                "top_topics": [],
                "analysis_date": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.warning(f"⚠️ 경쟁사 채널 분석 실패: {e}")
            return {}

    def benchmark_against_competitors(self, competitor_data: List[Dict]) -> Dict:
        """
        경쟁사 대비 벤치마킹

        Args:
            competitor_data: 경쟁사 채널 데이터 리스트

        Returns:
            벤치마킹 결과
        """
        try:
            # 자체 채널 데이터 가져오기
            own_data = self._get_own_channel_data()

            # 경쟁사 평균 계산
            competitor_avg = {
                "avg_views": np.mean(
                    [c.get("avg_views_per_video", 0) for c in competitor_data]
                ),
                "avg_engagement_rate": np.mean(
                    [c.get("avg_engagement_rate", 0) for c in competitor_data]
                ),
                "upload_frequency": np.mean(
                    [c.get("upload_frequency", 0) for c in competitor_data]
                ),
            }

            # 비교 분석
            comparison = {
                "views_performance": (
                    "above"
                    if own_data["avg_views"] > competitor_avg["avg_views"]
                    else "below"
                ),
                "engagement_performance": (
                    "above"
                    if own_data["avg_engagement_rate"]
                    > competitor_avg["avg_engagement_rate"]
                    else "below"
                ),
                "upload_frequency_performance": (
                    "above"
                    if own_data["upload_frequency"] > competitor_avg["upload_frequency"]
                    else "below"
                ),
                "gap_analysis": {
                    "views_gap": own_data["avg_views"] - competitor_avg["avg_views"],
                    "engagement_gap": own_data["avg_engagement_rate"]
                    - competitor_avg["avg_engagement_rate"],
                    "frequency_gap": own_data["upload_frequency"]
                    - competitor_avg["upload_frequency"],
                },
            }

            return {
                "own_data": own_data,
                "competitor_avg": competitor_avg,
                "comparison": comparison,
                "recommendations": self._generate_benchmark_recommendations(comparison),
            }
        except Exception as e:
            logger.warning(f"⚠️ 벤치마킹 실패: {e}")
            return {}

    def _get_own_channel_data(self) -> Dict:
        """자체 채널 데이터 가져오기"""
        try:
            historical_data = self.video_db.get_top_performing_videos(
                limit=100, days=30
            )

            if not historical_data:
                return {"avg_views": 0, "avg_engagement_rate": 0, "upload_frequency": 0}

            views = [v.get("views", 0) for v in historical_data]
            engagement_rates = [v.get("engagement_rate", 0) for v in historical_data]

            return {
                "avg_views": np.mean(views) if views else 0,
                "avg_engagement_rate": (
                    np.mean(engagement_rates) if engagement_rates else 0
                ),
                "upload_frequency": len(historical_data) / 30,  # 일일 업로드 빈도
            }
        except Exception as e:
            logger.warning(f"⚠️ 자체 채널 데이터 가져오기 실패: {e}")
            return {"avg_views": 0, "avg_engagement_rate": 0, "upload_frequency": 0}

    def _generate_benchmark_recommendations(self, comparison: Dict) -> List[str]:
        """벤치마킹 결과 기반 권장사항 생성"""
        recommendations = []

        if comparison["views_performance"] == "below":
            recommendations.append("조회수 향상을 위해 주제 선택 및 썸네일 최적화 필요")

        if comparison["engagement_performance"] == "below":
            recommendations.append(
                "참여율 향상을 위해 콘텐츠 품질 개선 및 CTA 강화 필요"
            )

        if comparison["upload_frequency_performance"] == "below":
            recommendations.append("업로드 빈도 증가로 채널 성장 가속화 필요")

        return recommendations


class AudienceSegmentAnalyzer:
    """시청자 세그먼트 분석 클래스"""

    def __init__(self):
        self.video_db = VideoDatabase()
        self.topic_db = TopicDatabase()

    def analyze_audience_segments(self, days: int = 30) -> Dict:
        """
        시청자 세그먼트 분석

        Args:
            days: 분석 기간 (일)

        Returns:
            시청자 세그먼트 분석 결과
        """
        try:
            # 주제별 시청자 분석
            topic_segments = self._analyze_topic_segments(days)

            # 콘텐츠 타입별 시청자 분석
            content_type_segments = self._analyze_content_type_segments(days)

            # 시간대별 시청자 분석
            time_segments = self._analyze_time_segments(days)

            return {
                "topic_segments": topic_segments,
                "content_type_segments": content_type_segments,
                "time_segments": time_segments,
                "analysis_date": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.warning(f"⚠️ 시청자 세그먼트 분석 실패: {e}")
            return {}

    def _analyze_topic_segments(self, days: int) -> List[Dict]:
        """주제별 시청자 세그먼트 분석"""
        try:
            # 주제별 성과 데이터 가져오기
            topics = self.topic_db.get_all_topics()

            segments = []
            for topic in topics:
                topic_videos = self.topic_db.get_videos_by_topic(topic["topic"])

                if topic_videos:
                    views = [v.get("views", 0) for v in topic_videos]
                    engagement_rates = [
                        v.get("engagement_rate", 0) for v in topic_videos
                    ]

                    segments.append(
                        {
                            "segment_name": topic["topic"],
                            "segment_type": "topic",
                            "video_count": len(topic_videos),
                            "avg_views": np.mean(views) if views else 0,
                            "avg_engagement_rate": (
                                np.mean(engagement_rates) if engagement_rates else 0
                            ),
                            "total_views": sum(views),
                        }
                    )

            # 평균 조회수 순으로 정렬
            segments.sort(key=lambda x: x["avg_views"], reverse=True)
            return segments
        except Exception as e:
            logger.warning(f"⚠️ 주제별 세그먼트 분석 실패: {e}")
            return []

    def _analyze_content_type_segments(self, days: int) -> List[Dict]:
        """콘텐츠 타입별 시청자 세그먼트 분석"""
        try:
            # 콘텐츠 타입별 데이터 가져오기
            content_types = [
                "hook",
                "quote",
                "story",
                "fact",
                "short_story",
                "meditation",
                "breathing",
            ]

            segments = []
            for content_type in content_types:
                topics = self.topic_db.get_topics_by_content_type(content_type)

                if topics:
                    all_views = []
                    all_engagement_rates = []

                    for topic in topics:
                        topic_videos = self.topic_db.get_videos_by_topic(topic["topic"])
                        for video in topic_videos:
                            all_views.append(video.get("views", 0))
                            all_engagement_rates.append(video.get("engagement_rate", 0))

                    if all_views:
                        segments.append(
                            {
                                "segment_name": content_type,
                                "segment_type": "content_type",
                                "video_count": len(all_views),
                                "avg_views": np.mean(all_views),
                                "avg_engagement_rate": np.mean(all_engagement_rates),
                                "total_views": sum(all_views),
                            }
                        )

            segments.sort(key=lambda x: x["avg_views"], reverse=True)
            return segments
        except Exception as e:
            logger.warning(f"⚠️ 콘텐츠 타입별 세그먼트 분석 실패: {e}")
            return []

    def _analyze_time_segments(self, days: int) -> List[Dict]:
        """시간대별 시청자 세그먼트 분석"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            conn = sqlite3.connect(self.video_db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM videos
                WHERE upload_date >= ?
            """,
                (cutoff_date,),
            )

            videos = [dict(row) for row in cursor.fetchall()]
            conn.close()

            # 시간대별 그룹화 (오전, 오후, 저녁, 밤)
            time_groups = {
                "morning": (6, 12),  # 오전 6시-12시
                "afternoon": (12, 18),  # 오후 12시-18시
                "evening": (18, 22),  # 저녁 18시-22시
                "night": (22, 6),  # 밤 22시-6시
            }

            segments = []
            for group_name, (start_hour, end_hour) in time_groups.items():
                group_videos = []
                for video in videos:
                    try:
                        upload_date = datetime.fromisoformat(
                            video.get("upload_date", "")
                        )
                        hour = upload_date.hour

                        if start_hour < end_hour:
                            if start_hour <= hour < end_hour:
                                group_videos.append(video)
                        else:  # 밤 시간대 (22시-6시)
                            if hour >= start_hour or hour < end_hour:
                                group_videos.append(video)
                    except:
                        continue

                if group_videos:
                    views = [v.get("views", 0) for v in group_videos]
                    engagement_rates = [
                        v.get("engagement_rate", 0) for v in group_videos
                    ]

                    segments.append(
                        {
                            "segment_name": group_name,
                            "segment_type": "time",
                            "video_count": len(group_videos),
                            "avg_views": np.mean(views) if views else 0,
                            "avg_engagement_rate": (
                                np.mean(engagement_rates) if engagement_rates else 0
                            ),
                            "total_views": sum(views),
                        }
                    )

            segments.sort(key=lambda x: x["avg_views"], reverse=True)
            return segments
        except Exception as e:
            logger.warning(f"⚠️ 시간대별 세그먼트 분석 실패: {e}")
            return []

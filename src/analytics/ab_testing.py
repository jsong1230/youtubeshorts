"""
A/B 테스트 시스템
다양한 스타일의 영상 생성, 성과 데이터 수집 및 분석, 최적 스타일 자동 선택
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from enum import Enum
import json

from src.utils.logger import get_logger

logger = get_logger(__name__)


class VideoStyle(Enum):
    """영상 스타일 변형"""

    DEFAULT = "default"  # 기본 스타일
    MINIMAL = "minimal"  # 미니멀 스타일 (자막 최소화)
    BOLD = "bold"  # 볼드 스타일 (큰 자막, 강한 대비)
    MUSIC = "music"  # 배경 음악 포함
    NO_MUSIC = "no_music"  # 배경 음악 없음
    GRADIENT = "gradient"  # 그라데이션 배경 강조
    VIDEO_BG = "video_bg"  # 배경 영상 강조


class ABTestDatabase:
    """A/B 테스트 데이터베이스 관리 클래스"""

    def __init__(self, db_path: str = "data/ab_tests.db"):
        """
        A/B 테스트 데이터베이스 초기화

        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = db_path
        # data 폴더가 없으면 생성
        data_dir = os.path.dirname(db_path)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """데이터베이스 테이블 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # ab_tests 테이블 생성
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ab_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT UNIQUE NOT NULL,
                topic TEXT,
                content_type TEXT,
                style TEXT NOT NULL,
                style_config TEXT,  -- JSON 형식의 스타일 설정
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0.0,
                watch_time REAL DEFAULT 0.0,
                upload_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """
        )

        # 인덱스 생성
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_id ON ab_tests(video_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_style ON ab_tests(style)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_content_type ON ab_tests(content_type)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_engagement_rate ON ab_tests(engagement_rate)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_upload_date ON ab_tests(upload_date)"
        )

        conn.commit()
        conn.close()

    def add_test(
        self,
        video_id: str,
        topic: str,
        content_type: str,
        style: str,
        style_config: Dict = None,
    ) -> bool:
        """
        A/B 테스트 항목 추가

        Args:
            video_id: YouTube 영상 ID
            topic: 영상 주제
            content_type: 콘텐츠 타입
            style: 영상 스타일
            style_config: 스타일 설정 (딕셔너리)

        Returns:
            성공 여부
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now().isoformat()
            style_config_json = json.dumps(style_config) if style_config else None

            cursor.execute(
                """
                INSERT OR REPLACE INTO ab_tests 
                (video_id, topic, content_type, style, style_config, upload_date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    video_id,
                    topic,
                    content_type,
                    style,
                    style_config_json,
                    now,
                    now,
                    now,
                ),
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"⚠️ A/B 테스트 항목 추가 실패: {e}", exc_info=True)
            return False

    def update_test_stats(
        self,
        video_id: str,
        views: int = None,
        likes: int = None,
        comments: int = None,
        watch_time: float = None,
    ) -> bool:
        """
        A/B 테스트 통계 업데이트

        Args:
            video_id: YouTube 영상 ID
            views: 조회수
            likes: 좋아요 수
            comments: 댓글 수
            watch_time: 평균 시청 시간 (초)

        Returns:
            성공 여부
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 기존 데이터 가져오기
            cursor.execute(
                "SELECT views, likes, comments, watch_time FROM ab_tests WHERE video_id = ?",
                (video_id,),
            )
            row = cursor.fetchone()

            if row:
                old_views, old_likes, old_comments, old_watch_time = row
                views = views if views is not None else old_views
                likes = likes if likes is not None else old_likes
                comments = comments if comments is not None else old_comments
                watch_time = watch_time if watch_time is not None else old_watch_time

                # 참여율 계산
                engagement_rate = 0.0
                if views > 0:
                    engagement_rate = ((likes + comments) / views) * 100

                cursor.execute(
                    """
                    UPDATE ab_tests 
                    SET views = ?, likes = ?, comments = ?, watch_time = ?, 
                        engagement_rate = ?, updated_at = ?
                    WHERE video_id = ?
                """,
                    (
                        views,
                        likes,
                        comments,
                        watch_time,
                        engagement_rate,
                        datetime.now().isoformat(),
                        video_id,
                    ),
                )

                conn.commit()
                conn.close()
                return True
            else:
                conn.close()
                return False
        except Exception as e:
            logger.error(f"⚠️ A/B 테스트 통계 업데이트 실패: {e}", exc_info=True)
            return False

    def get_best_style(
        self, content_type: str = None, days: int = 30, min_views: int = 50
    ) -> Optional[str]:
        """
        최적 스타일 자동 선택

        Args:
            content_type: 콘텐츠 타입 (None이면 전체)
            days: 최근 며칠간의 데이터만 사용
            min_views: 최소 조회수

        Returns:
            최적 스타일 또는 None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            # 콘텐츠 타입별로 그룹화하여 평균 성과 계산
            if content_type:
                cursor.execute(
                    """
                    SELECT 
                        style,
                        COUNT(*) as test_count,
                        AVG(engagement_rate) as avg_engagement_rate,
                        AVG(views) as avg_views,
                        AVG(watch_time) as avg_watch_time,
                        SUM(views) as total_views
                    FROM ab_tests
                    WHERE upload_date >= ? 
                        AND content_type = ?
                        AND views >= ?
                    GROUP BY style
                    HAVING COUNT(*) >= 2  -- 최소 2개 이상의 테스트 필요
                    ORDER BY avg_engagement_rate DESC, avg_watch_time DESC, total_views DESC
                    LIMIT 1
                """,
                    (cutoff_date, content_type, min_views),
                )
            else:
                cursor.execute(
                    """
                    SELECT 
                        style,
                        COUNT(*) as test_count,
                        AVG(engagement_rate) as avg_engagement_rate,
                        AVG(views) as avg_views,
                        AVG(watch_time) as avg_watch_time,
                        SUM(views) as total_views
                    FROM ab_tests
                    WHERE upload_date >= ? 
                        AND views >= ?
                    GROUP BY style
                    HAVING COUNT(*) >= 2
                    ORDER BY avg_engagement_rate DESC, avg_watch_time DESC, total_views DESC
                    LIMIT 1
                """,
                    (cutoff_date, min_views),
                )

            row = cursor.fetchone()
            conn.close()

            if row:
                return row["style"]
            return None
        except Exception as e:
            logger.error(f"⚠️ 최적 스타일 조회 실패: {e}", exc_info=True)
            return None

    def get_style_performance(
        self, content_type: str = None, days: int = 30, min_views: int = 50
    ) -> List[Dict]:
        """
        스타일별 성과 데이터 조회

        Args:
            content_type: 콘텐츠 타입 (None이면 전체)
            days: 최근 며칠간의 데이터만 사용
            min_views: 최소 조회수

        Returns:
            스타일별 성과 리스트
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            if content_type:
                cursor.execute(
                    """
                    SELECT 
                        style,
                        content_type,
                        COUNT(*) as test_count,
                        AVG(engagement_rate) as avg_engagement_rate,
                        AVG(views) as avg_views,
                        AVG(likes) as avg_likes,
                        AVG(comments) as avg_comments,
                        AVG(watch_time) as avg_watch_time,
                        SUM(views) as total_views
                    FROM ab_tests
                    WHERE upload_date >= ? 
                        AND content_type = ?
                        AND views >= ?
                    GROUP BY style, content_type
                    ORDER BY avg_engagement_rate DESC
                """,
                    (cutoff_date, content_type, min_views),
                )
            else:
                cursor.execute(
                    """
                    SELECT 
                        style,
                        content_type,
                        COUNT(*) as test_count,
                        AVG(engagement_rate) as avg_engagement_rate,
                        AVG(views) as avg_views,
                        AVG(likes) as avg_likes,
                        AVG(comments) as avg_comments,
                        AVG(watch_time) as avg_watch_time,
                        SUM(views) as total_views
                    FROM ab_tests
                    WHERE upload_date >= ? 
                        AND views >= ?
                    GROUP BY style, content_type
                    ORDER BY avg_engagement_rate DESC
                """,
                    (cutoff_date, min_views),
                )

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"⚠️ 스타일별 성과 조회 실패: {e}", exc_info=True)
            return []

    def get_best_styles_by_engagement(
        self, days: int = 30, min_tests: int = 3, min_views: int = 50
    ) -> List[Tuple[str, float, float]]:
        """
        참여율 기준 최고 성과 스타일 조회

        Args:
            days: 최근 며칠간의 데이터만 사용
            min_tests: 최소 테스트 수
            min_views: 최소 조회수

        Returns:
            (스타일, 평균 참여율, 평균 조회수) 튜플 리스트
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            cursor.execute(
                """
                SELECT 
                    style,
                    AVG(engagement_rate) as avg_engagement_rate,
                    AVG(views) as avg_views,
                    COUNT(*) as test_count
                FROM ab_tests
                WHERE upload_date >= ? 
                    AND views >= ?
                GROUP BY style
                HAVING COUNT(*) >= ?
                ORDER BY avg_engagement_rate DESC, avg_views DESC
            """,
                (cutoff_date, min_views, min_tests),
            )

            rows = cursor.fetchall()
            conn.close()

            return [(row[0], row[1], row[2]) for row in rows]
        except Exception as e:
            logger.error(f"⚠️ 최고 성과 스타일 조회 실패: {e}", exc_info=True)
            return []

    def get_test_by_video_id(self, video_id: str) -> Optional[Dict]:
        """
        비디오 ID로 A/B 테스트 데이터 가져오기

        Args:
            video_id: YouTube 영상 ID

        Returns:
            A/B 테스트 데이터 또는 None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM ab_tests
                WHERE video_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (video_id,),
            )

            row = cursor.fetchone()
            conn.close()

            if row:
                result = dict(row)
                # style_config JSON 파싱
                if result.get("style_config"):
                    try:
                        result["style_config"] = json.loads(result["style_config"])
                    except Exception:
                        pass
                return result
            return None
        except Exception as e:
            logger.error(f"⚠️ A/B 테스트 데이터 가져오기 실패: {e}", exc_info=True)
            return None

    def should_test_new_style(
        self, content_type: str, min_tests_per_style: int = 3
    ) -> bool:
        """
        새로운 스타일 테스트 여부 결정

        Args:
            content_type: 콘텐츠 타입
            min_tests_per_style: 스타일당 최소 테스트 수

        Returns:
            새로운 스타일 테스트 여부
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 현재 콘텐츠 타입의 스타일별 테스트 수 확인
            cursor.execute(
                """
                SELECT style, COUNT(*) as test_count
                FROM ab_tests
                WHERE content_type = ?
                GROUP BY style
            """,
                (content_type,),
            )

            rows = cursor.fetchall()
            conn.close()

            # 모든 스타일이 최소 테스트 수를 충족했는지 확인
            if not rows:
                return True  # 아직 테스트가 없으면 새 스타일 테스트

            for style, test_count in rows:
                if test_count < min_tests_per_style:
                    return False  # 아직 충분한 테스트가 없음

            return True  # 모든 스타일이 충분히 테스트됨, 새 스타일 테스트 가능
        except Exception as e:
            logger.error(f"⚠️ 새 스타일 테스트 여부 확인 실패: {e}", exc_info=True)
            return False

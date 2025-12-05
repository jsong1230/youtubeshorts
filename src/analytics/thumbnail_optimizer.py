"""
썸네일 최적화 시스템
클릭률 최적화 썸네일 선택, 플랫폼별 썸네일 최적화
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ThumbnailOptimizer:
    """썸네일 최적화 클래스"""

    def __init__(self, db_path: str = "data/thumbnails.db"):
        """
        썸네일 최적화 데이터베이스 초기화

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

        # thumbnails 테이블 생성
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS thumbnails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                thumbnail_path TEXT NOT NULL,
                thumbnail_variant TEXT,  -- 썸네일 변형 (default, bold, minimal, etc.)
                thumbnail_style TEXT,  -- 썸네일 스타일 (dalle3, frame_extract, etc.)
                views INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,  -- 썸네일 클릭 수 (조회수로 추정)
                ctr REAL DEFAULT 0.0,  -- 클릭률 (Click-Through Rate)
                impressions INTEGER DEFAULT 0,  -- 노출 수
                upload_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """
        )

        # 인덱스 생성
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_video_id ON thumbnails(video_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_variant ON thumbnails(thumbnail_variant)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ctr ON thumbnails(ctr)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_upload_date ON thumbnails(upload_date)"
        )

        conn.commit()
        conn.close()

    def add_thumbnail(
        self,
        video_id: str,
        thumbnail_path: str,
        thumbnail_variant: str = "default",
        thumbnail_style: str = "dalle3",
    ) -> bool:
        """
        썸네일 정보 추가

        Args:
            video_id: YouTube 영상 ID
            thumbnail_path: 썸네일 파일 경로
            thumbnail_variant: 썸네일 변형
            thumbnail_style: 썸네일 스타일

        Returns:
            성공 여부
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now().isoformat()

            cursor.execute(
                """
                INSERT INTO thumbnails 
                (video_id, thumbnail_path, thumbnail_variant, thumbnail_style, upload_date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    video_id,
                    thumbnail_path,
                    thumbnail_variant,
                    thumbnail_style,
                    now,
                    now,
                    now,
                ),
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.warning(f"⚠️ 썸네일 정보 추가 실패: {e}")
            return False

    def update_thumbnail_stats(
        self, video_id: str, views: int = None, impressions: int = None
    ) -> bool:
        """
        썸네일 통계 업데이트

        Args:
            video_id: YouTube 영상 ID
            views: 조회수 (클릭 수로 추정)
            impressions: 노출 수

        Returns:
            성공 여부
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 기존 데이터 가져오기
            cursor.execute(
                "SELECT views, impressions FROM thumbnails WHERE video_id = ?",
                (video_id,),
            )
            row = cursor.fetchone()

            if row:
                old_views = row[0] or 0
                old_impressions = row[1] or 0

                # 새 값이 제공되면 업데이트, 아니면 기존 값 유지
                new_views = views if views is not None else old_views
                new_impressions = (
                    impressions if impressions is not None else old_impressions
                )

                # 클릭률 계산 (CTR = views / impressions * 100)
                ctr = 0.0
                if new_impressions > 0:
                    ctr = (new_views / new_impressions) * 100

                now = datetime.now().isoformat()

                cursor.execute(
                    """
                    UPDATE thumbnails
                    SET views = ?, impressions = ?, ctr = ?, clicks = ?, updated_at = ?
                    WHERE video_id = ?
                """,
                    (new_views, new_impressions, ctr, new_views, now, video_id),
                )
            else:
                # 데이터가 없으면 새로 추가
                ctr = 0.0
                if impressions and impressions > 0:
                    ctr = (views / impressions) * 100 if views else 0.0

                now = datetime.now().isoformat()

                cursor.execute(
                    """
                    INSERT INTO thumbnails 
                    (video_id, views, impressions, ctr, clicks, upload_date, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        video_id,
                        views or 0,
                        impressions or 0,
                        ctr,
                        views or 0,
                        now,
                        now,
                        now,
                    ),
                )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.warning(f"⚠️ 썸네일 통계 업데이트 실패: {e}")
            return False

    def get_best_thumbnail_variant(
        self, days: int = 30, min_impressions: int = 100
    ) -> Optional[str]:
        """
        최고 성과 썸네일 변형 조회

        Args:
            days: 최근 며칠간의 데이터만 사용
            min_impressions: 최소 노출 수

        Returns:
            최고 성과 썸네일 변형 또는 None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            cursor.execute(
                """
                SELECT 
                    thumbnail_variant,
                    AVG(ctr) as avg_ctr,
                    AVG(views) as avg_views,
                    COUNT(*) as test_count
                FROM thumbnails
                WHERE upload_date >= ? 
                    AND impressions >= ?
                GROUP BY thumbnail_variant
                HAVING COUNT(*) >= 3  -- 최소 3개 이상의 테스트 필요
                ORDER BY avg_ctr DESC, avg_views DESC
                LIMIT 1
            """,
                (cutoff_date, min_impressions),
            )

            row = cursor.fetchone()
            conn.close()

            if row:
                return row[0]
            return None
        except Exception as e:
            logger.warning(f"⚠️ 최고 성과 썸네일 변형 조회 실패: {e}")
            return None

    def get_best_thumbnail_style(
        self, days: int = 30, min_impressions: int = 100
    ) -> Optional[str]:
        """
        최고 성과 썸네일 스타일 조회

        Args:
            days: 최근 며칠간의 데이터만 사용
            min_impressions: 최소 노출 수

        Returns:
            최고 성과 썸네일 스타일 또는 None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            cursor.execute(
                """
                SELECT 
                    thumbnail_style,
                    AVG(ctr) as avg_ctr,
                    AVG(views) as avg_views,
                    COUNT(*) as test_count
                FROM thumbnails
                WHERE upload_date >= ? 
                    AND impressions >= ?
                GROUP BY thumbnail_style
                HAVING COUNT(*) >= 3
                ORDER BY avg_ctr DESC, avg_views DESC
                LIMIT 1
            """,
                (cutoff_date, min_impressions),
            )

            row = cursor.fetchone()
            conn.close()

            if row:
                return row[0]
            return None
        except Exception as e:
            logger.warning(f"⚠️ 최고 성과 썸네일 스타일 조회 실패: {e}")
            return None

    def get_thumbnail_performance(
        self, days: int = 30, min_impressions: int = 100
    ) -> List[Dict]:
        """
        썸네일 성과 데이터 조회

        Args:
            days: 최근 며칠간의 데이터만 사용
            min_impressions: 최소 노출 수

        Returns:
            썸네일 성과 리스트
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            cursor.execute(
                """
                SELECT 
                    thumbnail_variant,
                    thumbnail_style,
                    AVG(ctr) as avg_ctr,
                    AVG(views) as avg_views,
                    AVG(impressions) as avg_impressions,
                    COUNT(*) as test_count
                FROM thumbnails
                WHERE upload_date >= ? 
                    AND impressions >= ?
                GROUP BY thumbnail_variant, thumbnail_style
                ORDER BY avg_ctr DESC
            """,
                (cutoff_date, min_impressions),
            )

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"⚠️ 썸네일 성과 조회 실패: {e}")
            return []

    def optimize_for_platform(self, platform: str = "youtube_shorts") -> Dict:
        """
        플랫폼별 썸네일 최적화 설정 조회

        Args:
            platform: 플랫폼 이름 (youtube_shorts, youtube, tiktok, instagram 등)

        Returns:
            플랫폼별 최적화 설정
        """
        # YouTube Shorts 최적화 설정
        if platform == "youtube_shorts":
            return {
                "size": (1080, 1920),  # 9:16 비율
                "format": "jpg",
                "quality": 95,
                "text_position": "bottom",  # 텍스트 위치
                "badge_position": "top",  # 배지 위치
                "contrast": "high",  # 높은 대비
                "brightness": "medium",  # 중간 밝기
                "saturation": "high",  # 높은 채도
            }
        # 일반 YouTube 최적화 설정
        elif platform == "youtube":
            return {
                "size": (1280, 720),  # 16:9 비율
                "format": "jpg",
                "quality": 95,
                "text_position": "center",
                "badge_position": "top",
                "contrast": "high",
                "brightness": "medium",
                "saturation": "high",
            }
        # TikTok 최적화 설정
        elif platform == "tiktok":
            return {
                "size": (1080, 1920),  # 9:16 비율
                "format": "jpg",
                "quality": 90,
                "text_position": "bottom",
                "badge_position": "top",
                "contrast": "very_high",
                "brightness": "high",
                "saturation": "very_high",
            }
        # Instagram 최적화 설정
        elif platform == "instagram":
            return {
                "size": (1080, 1080),  # 1:1 비율
                "format": "jpg",
                "quality": 95,
                "text_position": "center",
                "badge_position": "top",
                "contrast": "high",
                "brightness": "medium",
                "saturation": "high",
            }
        # 기본 설정
        else:
            return {
                "size": (1080, 1920),
                "format": "jpg",
                "quality": 95,
                "text_position": "bottom",
                "badge_position": "top",
                "contrast": "high",
                "brightness": "medium",
                "saturation": "high",
            }

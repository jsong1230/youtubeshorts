"""
사용자 요청 주제 반영 시스템
사용자가 요청한 주제를 관리하고 우선순위를 부여하는 시스템
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RequestStatus(Enum):
    """요청 상태"""

    PENDING = "pending"  # 대기 중
    APPROVED = "approved"  # 승인됨
    IN_PROGRESS = "in_progress"  # 진행 중
    COMPLETED = "completed"  # 완료됨
    REJECTED = "rejected"  # 거부됨


class UserRequestHandler:
    """사용자 요청 주제 관리 클래스"""

    def __init__(self, db_path: str = "data/user_requests.db"):
        """
        사용자 요청 데이터베이스 초기화

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

        # user_requests 테이블 생성
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                source TEXT,  -- 요청 출처 (comment, email, dashboard, etc.)
                source_id TEXT,  -- 출처 ID (댓글 ID, 이메일 ID 등)
                priority INTEGER DEFAULT 5,  -- 우선순위 (1-10, 높을수록 우선)
                status TEXT NOT NULL DEFAULT 'pending',
                requested_by TEXT,  -- 요청자 (댓글 작성자, 이메일 발신자 등)
                requested_at TEXT NOT NULL,
                approved_at TEXT,
                completed_at TEXT,
                video_id TEXT,  -- 생성된 영상 ID
                notes TEXT,  -- 메모
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """
        )

        # 인덱스 생성
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON user_requests(status)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_priority ON user_requests(priority)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_requested_at ON user_requests(requested_at)"
        )

        conn.commit()
        conn.close()

    def add_request(
        self,
        topic: str,
        source: str = "manual",
        source_id: str = None,
        priority: int = 5,
        requested_by: str = None,
        notes: str = None,
    ) -> int:
        """
        사용자 요청 추가

        Args:
            topic: 요청 주제
            source: 요청 출처 (comment, email, dashboard, manual 등)
            source_id: 출처 ID
            priority: 우선순위 (1-10, 기본값: 5)
            requested_by: 요청자
            notes: 메모

        Returns:
            요청 ID
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now().isoformat()

            cursor.execute(
                """
                INSERT INTO user_requests
                (topic, source, source_id, priority, status, requested_by, requested_at, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    topic,
                    source,
                    source_id,
                    priority,
                    RequestStatus.PENDING.value,
                    requested_by,
                    now,
                    notes,
                    now,
                    now,
                ),
            )

            request_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"✅ 사용자 요청 추가: {topic} (우선순위: {priority})")
            return request_id
        except Exception as e:
            logger.warning(f"⚠️ 사용자 요청 추가 실패: {e}")
            return None

    def get_pending_requests(
        self, limit: int = 10, min_priority: int = 1
    ) -> List[Dict]:
        """
        대기 중인 요청 조회 (우선순위 순)

        Args:
            limit: 반환할 요청 수
            min_priority: 최소 우선순위

        Returns:
            요청 리스트
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM user_requests
                WHERE status = ? AND priority >= ?
                ORDER BY priority DESC, requested_at ASC
                LIMIT ?
            """,
                (RequestStatus.PENDING.value, min_priority, limit),
            )

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"⚠️ 대기 중인 요청 조회 실패: {e}")
            return []

    def approve_request(self, request_id: int) -> bool:
        """
        요청 승인

        Args:
            request_id: 요청 ID

        Returns:
            성공 여부
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now().isoformat()

            cursor.execute(
                """
                UPDATE user_requests
                SET status = ?, approved_at = ?, updated_at = ?
                WHERE id = ?
            """,
                (RequestStatus.APPROVED.value, now, now, request_id),
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.warning(f"⚠️ 요청 승인 실패: {e}")
            return False

    def mark_in_progress(self, request_id: int) -> bool:
        """
        요청을 진행 중으로 표시

        Args:
            request_id: 요청 ID

        Returns:
            성공 여부
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now().isoformat()

            cursor.execute(
                """
                UPDATE user_requests
                SET status = ?, updated_at = ?
                WHERE id = ?
            """,
                (RequestStatus.IN_PROGRESS.value, now, request_id),
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.warning(f"⚠️ 요청 상태 업데이트 실패: {e}")
            return False

    def mark_completed(self, request_id: int, video_id: str = None) -> bool:
        """
        요청 완료 표시

        Args:
            request_id: 요청 ID
            video_id: 생성된 영상 ID

        Returns:
            성공 여부
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now().isoformat()

            cursor.execute(
                """
                UPDATE user_requests
                SET status = ?, completed_at = ?, video_id = ?, updated_at = ?
                WHERE id = ?
            """,
                (RequestStatus.COMPLETED.value, now, video_id, now, request_id),
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.warning(f"⚠️ 요청 완료 표시 실패: {e}")
            return False

    def get_next_request(self) -> Optional[Dict]:
        """
        다음 처리할 요청 가져오기 (우선순위가 가장 높은 대기 중인 요청)

        Returns:
            요청 딕셔너리 또는 None
        """
        requests = self.get_pending_requests(limit=1, min_priority=1)
        if requests:
            return requests[0]
        return None

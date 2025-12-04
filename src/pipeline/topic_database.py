"""
주제 데이터베이스 관리 모듈
주제 추가/삭제/업데이트, 성과 추적, 자동 필터링
"""
import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from enum import Enum
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TopicSource(Enum):
    """주제 출처"""
    MANUAL = "manual"  # 수동 추가
    AI_GENERATED = "ai_generated"  # AI 생성
    SEASONAL_AI = "seasonal_ai"  # 계절별 AI 생성
    TREND = "trend"  # 트렌드에서 수집
    SEASONAL = "seasonal"  # 계절별 하드코딩
    PERFORMANCE = "performance"  # 성과 기반


class TopicStatus(Enum):
    """주제 상태"""
    ACTIVE = "active"  # 활성 (사용 가능)
    INACTIVE = "inactive"  # 비활성 (사용 안 함)
    FILTERED = "filtered"  # 필터링됨 (성과 낮음)
    ARCHIVED = "archived"  # 아카이브됨


class TopicDatabase:
    """주제 데이터베이스 관리 클래스"""
    
    def __init__(self, db_path: str = "data/videos.db"):
        """
        데이터베이스 초기화
        
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
        
        # topics 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT UNIQUE NOT NULL,
                content_type TEXT NOT NULL,
                source TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                season TEXT,
                language TEXT DEFAULT 'en',
                use_count INTEGER DEFAULT 0,
                total_views INTEGER DEFAULT 0,
                total_likes INTEGER DEFAULT 0,
                total_comments INTEGER DEFAULT 0,
                avg_engagement_rate REAL DEFAULT 0.0,
                cpm_score REAL DEFAULT 1.0,
                last_used_date TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # topic_videos 테이블 생성 (주제-영상 연결)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS topic_videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                video_id TEXT NOT NULL,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE,
                UNIQUE(topic_id, video_id)
            )
        ''')
        
        # 인덱스 생성 (성능 향상)
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_topic_content_type ON topics(content_type)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_topic_status ON topics(status)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_topic_source ON topics(source)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_topic_engagement ON topics(avg_engagement_rate)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_topic_videos_topic_id ON topic_videos(topic_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_topic_videos_video_id ON topic_videos(video_id)
        ''')
        
        conn.commit()
        conn.close()
    
    def add_topic(
        self,
        topic: str,
        content_type: str,
        source: str = TopicSource.MANUAL.value,
        season: str = None,
        language: str = 'en',
        status: str = TopicStatus.ACTIVE.value,
        cpm_score: float = 1.0
    ) -> Optional[int]:
        """
        주제 추가
        
        Args:
            topic: 주제 텍스트
            content_type: 콘텐츠 타입 ('hook', 'quote', 'story', 'fact', 'short_story' 등)
            source: 주제 출처 (TopicSource enum 값)
            season: 계절 ('spring', 'summer', 'autumn', 'winter')
            language: 언어 ('en' 또는 'ko')
            status: 주제 상태 (TopicStatus enum 값)
            cpm_score: CPM 잠재력 점수
        
        Returns:
            주제 ID 또는 None (실패 시)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT OR IGNORE INTO topics 
                (topic, content_type, source, status, season, language, cpm_score, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (topic, content_type, source, status, season, language, cpm_score, now, now))
            
            # 주제 ID 가져오기
            cursor.execute('SELECT id FROM topics WHERE topic = ?', (topic,))
            row = cursor.fetchone()
            
            conn.commit()
            conn.close()
            
            if row:
                return row[0]
            else:
                # 이미 존재하는 경우 기존 ID 반환
                return self.get_topic_id(topic)
        except Exception as e:
            logger.warning(f"⚠️ 주제 추가 실패: {e}")
            return None
    
    def get_topic_id(self, topic: str) -> Optional[int]:
        """주제 텍스트로 ID 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM topics WHERE topic = ?', (topic,))
            row = cursor.fetchone()
            conn.close()
            
            return row[0] if row else None
        except Exception as e:
            logger.warning(f"⚠️ 주제 ID 조회 실패: {e}")
            return None
    
    def update_topic(
        self,
        topic_id: int,
        topic: str = None,
        content_type: str = None,
        status: str = None,
        season: str = None,
        cpm_score: float = None
    ) -> bool:
        """
        주제 업데이트
        
        Args:
            topic_id: 주제 ID
            topic: 새로운 주제 텍스트
            content_type: 새로운 콘텐츠 타입
            status: 새로운 상태
            season: 새로운 계절
            cpm_score: 새로운 CPM 점수
        
        Returns:
            성공 여부
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            updates = []
            params: List[Any] = []
            
            if topic is not None:
                updates.append("topic = ?")
                params.append(topic)
            if content_type is not None:
                updates.append("content_type = ?")
                params.append(content_type)
            if status is not None:
                updates.append("status = ?")
                params.append(status)
            if season is not None:
                updates.append("season = ?")
                params.append(season)
            if cpm_score is not None:
                updates.append("cpm_score = ?")
                params.append(cpm_score)
            
            if not updates:
                conn.close()
                return False
            
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(topic_id)
            
            query = f"UPDATE topics SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.warning(f"⚠️ 주제 업데이트 실패: {e}")
            return False
    
    def delete_topic(self, topic_id: int) -> bool:
        """
        주제 삭제 (연결된 영상 정보도 함께 삭제)
        
        Args:
            topic_id: 주제 ID
        
        Returns:
            성공 여부
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM topics WHERE id = ?', (topic_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.warning(f"⚠️ 주제 삭제 실패: {e}")
            return False
    
    def link_topic_to_video(
        self,
        topic: str,
        video_id: str,
        views: int = 0,
        likes: int = 0,
        comments: int = 0
    ) -> bool:
        """
        주제와 영상 연결 및 성과 업데이트
        
        Args:
            topic: 주제 텍스트
            video_id: YouTube 영상 ID
            views: 조회수
            likes: 좋아요 수
            comments: 댓글 수
        
        Returns:
            성공 여부
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 주제 ID 가져오기 (없으면 생성)
            topic_id = self.get_topic_id(topic)
            if not topic_id:
                # 주제가 없으면 기본값으로 추가
                topic_id = self.add_topic(
                    topic=topic,
                    content_type='auto',  # 기본값
                    source=TopicSource.MANUAL.value
                )
            
            if not topic_id:
                conn.close()
                return False
            
            # 참여율 계산
            engagement_rate = 0.0
            if views > 0:
                engagement_rate = ((likes + comments) / views) * 100
            
            # topic_videos 테이블에 연결 정보 추가/업데이트
            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT OR REPLACE INTO topic_videos
                (topic_id, video_id, views, likes, comments, engagement_rate, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (topic_id, video_id, views, likes, comments, engagement_rate, now))
            
            # topics 테이블의 통계 업데이트
            self._update_topic_stats(topic_id, conn, cursor)
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.warning(f"⚠️ 주제-영상 연결 실패: {e}")
            return False
    
    def _update_topic_stats(self, topic_id: int, conn, cursor):
        """주제 통계 업데이트 (내부 메서드)"""
        # topic_videos에서 통계 집계
        cursor.execute('''
            SELECT 
                COUNT(*) as use_count,
                SUM(views) as total_views,
                SUM(likes) as total_likes,
                SUM(comments) as total_comments,
                AVG(engagement_rate) as avg_engagement_rate,
                MAX(created_at) as last_used_date
            FROM topic_videos
            WHERE topic_id = ?
        ''', (topic_id,))
        
        row = cursor.fetchone()
        if row:
            use_count, total_views, total_likes, total_comments, avg_engagement_rate, last_used_date = row
            
            cursor.execute('''
                UPDATE topics
                SET use_count = ?,
                    total_views = ?,
                    total_likes = ?,
                    total_comments = ?,
                    avg_engagement_rate = ?,
                    last_used_date = ?,
                    updated_at = ?
                WHERE id = ?
            ''', (
                use_count or 0,
                total_views or 0,
                total_likes or 0,
                total_comments or 0,
                avg_engagement_rate or 0.0,
                last_used_date,
                datetime.now().isoformat(),
                topic_id
            ))
    
    def get_topics(
        self,
        content_type: str = None,
        status: str = TopicStatus.ACTIVE.value,
        source: str = None,
        season: str = None,
        min_engagement_rate: float = None,
        limit: int = None
    ) -> List[Dict]:
        """
        주제 조회
        
        Args:
            content_type: 콘텐츠 타입 필터
            status: 주제 상태 필터
            source: 주제 출처 필터
            season: 계절 필터
            min_engagement_rate: 최소 평균 참여율 필터
            limit: 반환할 주제 수 제한
        
        Returns:
            주제 리스트
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            conditions = []
            params: List[Any] = []
            
            if content_type:
                conditions.append("content_type = ?")
                params.append(content_type)
            if status:
                conditions.append("status = ?")
                params.append(status)
            if source:
                conditions.append("source = ?")
                params.append(source)
            if season:
                conditions.append("season = ?")
                params.append(season)
            if min_engagement_rate is not None:
                conditions.append("avg_engagement_rate >= ?")
                params.append(min_engagement_rate)
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            limit_clause = f"LIMIT {limit}" if limit else ""
            
            query = f'''
                SELECT * FROM topics
                {where_clause}
                ORDER BY avg_engagement_rate DESC, use_count DESC
                {limit_clause}
            '''
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"⚠️ 주제 조회 실패: {e}")
            return []
    
    def get_topics_by_cpm(
        self,
        content_type: str = None,
        status: str = TopicStatus.ACTIVE.value,
        min_cpm_score: float = 1.0,
        limit: int = 10
    ) -> List[Dict]:
        """
        CPM 점수 기준으로 주제 조회
        
        Args:
            content_type: 콘텐츠 타입 필터
            status: 주제 상태 필터
            min_cpm_score: 최소 CPM 점수
            limit: 반환할 주제 수 제한
        
        Returns:
            주제 리스트 (CPM 점수 내림차순)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            conditions = ["cpm_score >= ?"]
            params: List[Any] = [min_cpm_score]
            
            if content_type:
                conditions.append("content_type = ?")
                params.append(content_type)
            if status:
                conditions.append("status = ?")
                params.append(status)
            
            where_clause = "WHERE " + " AND ".join(conditions)
            limit_clause = f"LIMIT {limit}" if limit else ""
            
            query = f'''
                SELECT * FROM topics
                {where_clause}
                ORDER BY cpm_score DESC, avg_engagement_rate DESC
                {limit_clause}
            '''
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"⚠️ CPM 기준 주제 조회 실패: {e}")
            return []
    
    def get_high_performing_topics(
        self,
        content_type: str = None,
        days: int = 30,
        min_views: int = 100,
        min_engagement_rate: float = 1.0,
        limit: int = 10
    ) -> List[str]:
        """
        성과가 좋은 주제 조회
        
        Args:
            content_type: 콘텐츠 타입 필터
            days: 최근 며칠간의 데이터만 조회
            min_views: 최소 조회수
            min_engagement_rate: 최소 평균 참여율 (%)
            limit: 반환할 주제 수
        
        Returns:
            성과가 좋은 주제 텍스트 리스트
        """
        topics = self.get_topics(
            content_type=content_type,
            status=TopicStatus.ACTIVE.value,
            min_engagement_rate=min_engagement_rate,
            limit=limit
        )
        
        # 추가 필터링 (조회수, 최근 사용 등)
        filtered_topics = []
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        for topic in topics:
            if topic['total_views'] >= min_views:
                # 최근 사용된 주제 우선
                last_used = topic.get('last_used_date')
                if last_used and last_used >= cutoff_date:
                    filtered_topics.append(topic['topic'])
                elif topic['use_count'] >= 2:  # 최소 2번 이상 사용된 주제
                    filtered_topics.append(topic['topic'])
        
        return filtered_topics[:limit]
    
    def get_all_topics(self, status: str = None) -> List[Dict]:
        """
        모든 주제 조회
        
        Args:
            status: 주제 상태 필터 (None이면 모든 상태)
        
        Returns:
            주제 리스트
        """
        return self.get_topics(status=status)
    
    def get_topics_by_content_type(self, content_type: str) -> List[Dict]:
        """
        콘텐츠 타입별 주제 조회
        
        Args:
            content_type: 콘텐츠 타입
        
        Returns:
            주제 리스트
        """
        return self.get_topics(content_type=content_type, status=TopicStatus.ACTIVE.value)
    
    def get_videos_by_topic(self, topic: str) -> List[Dict]:
        """
        주제별 영상 조회
        
        Args:
            topic: 주제 텍스트
        
        Returns:
            영상 리스트 (video_id, views, likes, comments, engagement_rate)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 주제 ID 가져오기
            topic_id = self.get_topic_id(topic)
            if not topic_id:
                conn.close()
                return []
            
            # 주제에 연결된 영상 가져오기
            cursor.execute('''
                SELECT video_id, views, likes, comments, engagement_rate
                FROM topic_videos
                WHERE topic_id = ?
            ''', (topic_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"⚠️ 주제별 영상 조회 실패: {e}")
            return []
    
    def get_low_performing_topics(
        self,
        content_type: str = None,
        days: int = 30,
        max_engagement_rate: float = 0.5,
        min_use_count: int = 1
    ) -> List[Dict]:
        """
        성과가 낮은 주제 조회 (자동 필터링 대상)
        
        Args:
            content_type: 콘텐츠 타입 필터
            days: 최근 며칠간의 데이터만 조회
            max_engagement_rate: 최대 평균 참여율 (%)
            min_use_count: 최소 사용 횟수 (이 이상 사용되었어야 필터링 대상)
        
        Returns:
            성과가 낮은 주제 리스트
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            conditions = ["status = ?", "use_count >= ?", "avg_engagement_rate <= ?"]
            params = [TopicStatus.ACTIVE.value, min_use_count, max_engagement_rate]
            
            if content_type:
                conditions.append("content_type = ?")
                params.append(content_type)
            
            # 최근 사용된 주제만 필터링
            conditions.append("last_used_date >= ?")
            params.append(cutoff_date)
            
            where_clause = "WHERE " + " AND ".join(conditions)
            
            query = f'''
                SELECT * FROM topics
                {where_clause}
                ORDER BY avg_engagement_rate ASC, use_count DESC
            '''
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"⚠️ 성과 낮은 주제 조회 실패: {e}")
            return []
    
    def filter_low_performing_topics(
        self,
        content_type: str = None,
        days: int = 30,
        max_engagement_rate: float = 0.5,
        min_use_count: int = 1
    ) -> int:
        """
        성과가 낮은 주제 자동 필터링 (상태를 'filtered'로 변경)
        
        Args:
            content_type: 콘텐츠 타입 필터
            days: 최근 며칠간의 데이터만 조회
            max_engagement_rate: 최대 평균 참여율 (%)
            min_use_count: 최소 사용 횟수
        
        Returns:
            필터링된 주제 수
        """
        low_performing = self.get_low_performing_topics(
            content_type=content_type,
            days=days,
            max_engagement_rate=max_engagement_rate,
            min_use_count=min_use_count
        )
        
        filtered_count = 0
        for topic in low_performing:
            if self.update_topic(topic['id'], status=TopicStatus.FILTERED.value):
                filtered_count += 1
                logger.debug(f"   🔽 주제 필터링: {topic['topic'][:50]}... (참여율: {topic['avg_engagement_rate']:.2f}%)")
        
        if filtered_count > 0:
            logger.info(f"✅ 성과 낮은 주제 {filtered_count}개 필터링 완료")
        
        return filtered_count
    
    def get_topic_stats(self, topic_id: int) -> Optional[Dict]:
        """
        주제 통계 조회
        
        Args:
            topic_id: 주제 ID
        
        Returns:
            주제 통계 딕셔너리 또는 None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM topics WHERE id = ?', (topic_id,))
            row = cursor.fetchone()
            conn.close()
            
            return dict(row) if row else None
        except Exception as e:
            logger.warning(f"⚠️ 주제 통계 조회 실패: {e}")
            return None


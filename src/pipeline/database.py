"""
SQLite 데이터베이스 모듈
영상 정보 및 성과 데이터 저장
"""
import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path


class VideoDatabase:
    """영상 데이터베이스 관리 클래스"""
    
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
        
        # videos 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                topic TEXT,
                prompt TEXT,
                script TEXT,
                upload_date TEXT NOT NULL,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # 인덱스 생성 (성능 향상)
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_video_id ON videos(video_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_upload_date ON videos(upload_date)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_engagement_rate ON videos(engagement_rate)
        ''')
        
        conn.commit()
        conn.close()
    
    def add_video(
        self,
        video_id: str,
        title: str,
        topic: str = None,
        prompt: str = None,
        script: str = None
    ) -> bool:
        """
        영상 추가
        
        Args:
            video_id: YouTube 영상 ID
            title: 영상 제목
            topic: 영상 주제
            prompt: 사용된 프롬프트
            script: 생성된 스크립트
        
        Returns:
            성공 여부
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT OR REPLACE INTO videos 
                (video_id, title, topic, prompt, script, upload_date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (video_id, title, topic, prompt, script, now, now, now))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"⚠️ 영상 추가 실패: {e}")
            return False
    
    def update_video_stats(
        self,
        video_id: str,
        views: int = None,
        likes: int = None,
        comments: int = None
    ) -> bool:
        """
        영상 통계 업데이트
        
        Args:
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
            
            # 기존 데이터 가져오기
            cursor.execute('SELECT views, likes, comments FROM videos WHERE video_id = ?', (video_id,))
            row = cursor.fetchone()
            
            if row:
                old_views, old_likes, old_comments = row
                views = views if views is not None else old_views
                likes = likes if likes is not None else old_likes
                comments = comments if comments is not None else old_comments
                
                # 참여율 계산 (좋아요 + 댓글) / 조회수 * 100
                engagement_rate = 0.0
                if views > 0:
                    engagement_rate = ((likes + comments) / views) * 100
                
                cursor.execute('''
                    UPDATE videos 
                    SET views = ?, likes = ?, comments = ?, engagement_rate = ?, updated_at = ?
                    WHERE video_id = ?
                ''', (views, likes, comments, engagement_rate, datetime.now().isoformat(), video_id))
                
                conn.commit()
                conn.close()
                return True
            else:
                conn.close()
                return False
        except Exception as e:
            print(f"⚠️ 통계 업데이트 실패: {e}")
            return False
    
    def get_top_performing_videos(
        self,
        limit: int = 5,
        days: int = 30,
        min_views: int = 100
    ) -> List[Dict]:
        """
        성과가 좋은 영상 조회
        
        Args:
            limit: 반환할 영상 수
            days: 최근 며칠간의 데이터만 조회
            min_views: 최소 조회수
        
        Returns:
            성과가 좋은 영상 리스트
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute('''
                SELECT video_id, title, topic, prompt, views, likes, comments, engagement_rate
                FROM videos
                WHERE upload_date >= ? AND views >= ?
                ORDER BY engagement_rate DESC, views DESC
                LIMIT ?
            ''', (cutoff_date, min_views, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"⚠️ 성과 좋은 영상 조회 실패: {e}")
            return []
    
    def get_all_videos(
        self,
        limit: int = None,
        days: int = None,
        order_by: str = 'upload_date'
    ) -> List[Dict]:
        """
        모든 영상 조회 (필터 없이)
        
        Args:
            limit: 반환할 영상 수 (None이면 제한 없음)
            days: 최근 며칠간의 데이터만 조회 (None이면 전체)
            order_by: 정렬 기준 ('upload_date', 'views', 'engagement_rate' 등)
        
        Returns:
            영상 리스트
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT video_id, title, topic, prompt, upload_date, views, likes, comments, engagement_rate FROM videos'
            params = []
            
            if days:
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                query += ' WHERE upload_date >= ?'
                params.append(cutoff_date)
            
            # 정렬
            if order_by == 'upload_date':
                query += ' ORDER BY upload_date DESC'
            elif order_by == 'views':
                query += ' ORDER BY views DESC'
            elif order_by == 'engagement_rate':
                query += ' ORDER BY engagement_rate DESC'
            else:
                query += ' ORDER BY upload_date DESC'
            
            if limit:
                query += ' LIMIT ?'
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"⚠️ 모든 영상 조회 실패: {e}")
            return []
    
    def get_top_topics(
        self,
        limit: int = 5,
        days: int = 30
    ) -> List[Dict]:
        """
        인기 주제 조회 (참여율 기준)
        
        Args:
            limit: 반환할 주제 수
            days: 최근 며칠간의 데이터만 조회
        
        Returns:
            인기 주제 리스트 (주제별 평균 참여율)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute('''
                SELECT 
                    topic,
                    COUNT(*) as video_count,
                    AVG(engagement_rate) as avg_engagement_rate,
                    AVG(views) as avg_views,
                    AVG(likes) as avg_likes
                FROM videos
                WHERE upload_date >= ? AND topic IS NOT NULL AND topic != ''
                GROUP BY topic
                HAVING COUNT(*) >= 1
                ORDER BY avg_engagement_rate DESC, avg_views DESC
                LIMIT ?
            ''', (cutoff_date, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"⚠️ 인기 주제 조회 실패: {e}")
            return []
    
    def get_top_prompts(
        self,
        limit: int = 3,
        days: int = 30
    ) -> List[str]:
        """
        성과가 좋은 프롬프트 조회
        
        Args:
            limit: 반환할 프롬프트 수
            days: 최근 며칠간의 데이터만 조회
        
        Returns:
            성과가 좋은 프롬프트 리스트
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute('''
                SELECT prompt
                FROM videos
                WHERE upload_date >= ? 
                    AND prompt IS NOT NULL 
                    AND prompt != ''
                    AND engagement_rate > 0
                ORDER BY engagement_rate DESC, views DESC
                LIMIT ?
            ''', (cutoff_date, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [row[0] for row in rows if row[0]]
        except Exception as e:
            print(f"⚠️ 성과 좋은 프롬프트 조회 실패: {e}")
            return []
    
    def get_video_by_id(self, video_id: str) -> Optional[Dict]:
        """
        영상 ID로 조회
        
        Args:
            video_id: YouTube 영상 ID
        
        Returns:
            영상 정보 딕셔너리 또는 None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM videos WHERE video_id = ?', (video_id,))
            row = cursor.fetchone()
            conn.close()
            
            return dict(row) if row else None
        except Exception as e:
            print(f"⚠️ 영상 조회 실패: {e}")
            return None


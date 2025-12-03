"""
임시 파일 자동 정리 모듈
temp 폴더의 오래된 임시 파일을 자동으로 삭제
"""
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from src.core.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TempCleaner:
    """임시 파일 자동 정리 클래스"""
    
    def __init__(self, max_age_hours: int = 24):
        """
        임시 파일 정리기 초기화
        
        Args:
            max_age_hours: 최대 보관 시간 (시간 단위, 기본값: 24시간)
        """
        self.max_age_hours = max_age_hours
        self.temp_dir = settings.TEMP_DIR
    
    def clean_old_files(self, dry_run: bool = False) -> dict[str, int]:
        """
        오래된 임시 파일 삭제
        
        Args:
            dry_run: True면 실제 삭제하지 않고 확인만 (기본값: False)
        
        Returns:
            삭제 통계 딕셔너리
        """
        if not os.path.exists(self.temp_dir):
            return {'deleted': 0, 'size_freed': 0, 'errors': 0}
        
        stats = {
            'deleted': 0,
            'size_freed': 0,  # 바이트 단위
            'errors': 0
        }
        
        cutoff_time = time.time() - (self.max_age_hours * 3600)
        
        try:
            for root, dirs, files in os.walk(self.temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    try:
                        # 파일 수정 시간 확인
                        mtime = os.path.getmtime(file_path)
                        
                        if mtime < cutoff_time:
                            file_size = os.path.getsize(file_path)
                            
                            if not dry_run:
                                os.remove(file_path)
                            
                            stats['deleted'] += 1
                            stats['size_freed'] += file_size
                            
                            if dry_run:
                                logger.debug(f"   [DRY RUN] 삭제 예정: {file_path} ({file_size / 1024 / 1024:.2f} MB)")
                    except Exception as e:
                        stats['errors'] += 1
                        if not dry_run:
                            logger.warning(f"   ⚠️ 파일 삭제 실패 ({file_path}): {e}")
            
            # 빈 디렉토리 삭제
            if not dry_run:
                for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        try:
                            if not os.listdir(dir_path):  # 디렉토리가 비어있으면
                                os.rmdir(dir_path)
                        except:
                            pass
        
        except Exception as e:
            logger.warning(f"⚠️ 임시 파일 정리 중 오류: {e}")
            stats['errors'] += 1
        
        return stats
    
    def clean_after_video_generation(self) -> None:
        """
        영상 생성 후 즉시 임시 파일 정리 (최근 생성된 파일 제외)
        """
        if not os.path.exists(self.temp_dir):
            return
        
        # 최근 1시간 이내 파일은 보존
        cutoff_time = time.time() - 3600
        
        try:
            for root, dirs, files in os.walk(self.temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    try:
                        mtime = os.path.getmtime(file_path)
                        
                        # 오래된 파일만 삭제 (1시간 이상)
                        if mtime < cutoff_time:
                            os.remove(file_path)
                    except Exception as e:
                        pass  # 조용히 실패 처리
        except Exception as e:
            pass  # 조용히 실패 처리


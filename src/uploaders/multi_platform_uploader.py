"""
멀티 플랫폼 동시 업로드 모듈
"""
import os
from typing import Dict, Optional, List, Union, Any
from src.uploaders.youtube_uploader import YouTubeUploader
from src.uploaders.tiktok_uploader import TikTokUploader
from src.uploaders.instagram_uploader import InstagramUploader
from src.core.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MultiPlatformUploader:
    """여러 플랫폼에 동시에 영상을 업로드하는 클래스"""
    
    def __init__(self):
        """각 플랫폼 업로더 초기화"""
        self.uploaders: Dict[str, Any] = {}
        self.results: Dict[str, Optional[str]] = {}
        
        # YouTube 업로더 (항상 활성화)
        try:
            self.uploaders['youtube'] = YouTubeUploader()
            logger.info("✅ YouTube 업로더 초기화 완료")
        except Exception as e:
            logger.warning(f"⚠️ YouTube 업로더 초기화 실패: {e}")
        
        # TikTok 업로더 (선택사항)
        if settings.ENABLE_TIKTOK_UPLOAD:
            try:
                self.uploaders['tiktok'] = TikTokUploader()
                if self.uploaders['tiktok'].is_available():
                    logger.info("✅ TikTok 업로더 초기화 완료")
                else:
                    logger.warning("⚠️ TikTok 업로더 사용 불가 (API 키 미설정)")
            except Exception as e:
                logger.warning(f"⚠️ TikTok 업로더 초기화 실패: {e}")
        
        # Instagram 업로더 (선택사항)
        if settings.ENABLE_INSTAGRAM_UPLOAD:
            try:
                self.uploaders['instagram'] = InstagramUploader()
                if self.uploaders['instagram'].is_available():
                    logger.info("✅ Instagram 업로더 초기화 완료")
                else:
                    logger.warning("⚠️ Instagram 업로더 사용 불가 (API 키 미설정)")
            except Exception as e:
                logger.warning(f"⚠️ Instagram 업로더 초기화 실패: {e}")
    
    def upload_to_all(
        self,
        video_path: str,
        title: str,
        description: str = None,
        tags: List[str] = None,
        platforms: List[str] = None,
        thumbnail_path: str = None
    ) -> Dict[str, Optional[str]]:
        """
        여러 플랫폼에 동시에 영상 업로드
        
        Args:
            video_path: 업로드할 영상 파일 경로
            title: 영상 제목
            description: 영상 설명 (선택사항)
            tags: 태그 리스트 (선택사항)
            platforms: 업로드할 플랫폼 리스트 (None이면 모든 활성화된 플랫폼)
        
        Returns:
            플랫폼별 영상 ID 딕셔너리
            예: {'youtube': 'abc123', 'tiktok': 'xyz789', 'instagram': None}
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"영상 파일을 찾을 수 없습니다: {video_path}")
        
        if platforms is None:
            platforms = list(self.uploaders.keys())
        
        results = {}
        
        logger.info(f"📤 멀티 플랫폼 업로드 시작: {', '.join(platforms)}")
        
        # YouTube 업로드
        if 'youtube' in platforms and 'youtube' in self.uploaders:
            try:
                logger.info("📺 YouTube 업로드 중...")
                if thumbnail_path:
                    logger.info(f"   🖼️ 썸네일 경로 전달됨: {thumbnail_path}")
                else:
                    logger.warning("   ⚠️ 썸네일 경로가 전달되지 않았습니다.")
                youtube_id = self.uploaders['youtube'].upload_video(
                    video_path=video_path,
                    title=title,
                    description=description or settings.DEFAULT_DESCRIPTION,
                    tags=tags or settings.DEFAULT_TAGS if isinstance(settings.DEFAULT_TAGS, list) else [],  # type: ignore[arg-type]
                    privacy_status='public',
                    thumbnail_path=thumbnail_path,
                    schedule_delay_hours=settings.UPLOAD_DELAY_HOURS  # 예약 업로드 지연 시간
                )
                results['youtube'] = youtube_id
                if youtube_id:
                    logger.info(f"✅ YouTube 업로드 완료: {youtube_id}")
                else:
                    logger.error("⚠️ YouTube 업로드 실패")
            except Exception as e:
                logger.error(f"⚠️ YouTube 업로드 오류: {e}", exc_info=True)
                results['youtube'] = None
        
        # TikTok 업로드
        if 'tiktok' in platforms and 'tiktok' in self.uploaders:
            try:
                if self.uploaders['tiktok'].is_available():
                    logger.info("🎵 TikTok 업로드 중...")
                    tiktok_id = self.uploaders['tiktok'].upload_video(
                        video_path=video_path,
                        title=title,
                        description=description
                    )
                    results['tiktok'] = tiktok_id
                    if tiktok_id:
                        logger.info(f"✅ TikTok 업로드 완료: {tiktok_id}")
                    else:
                        logger.error("⚠️ TikTok 업로드 실패")
                else:
                    logger.warning("⚠️ TikTok 업로더 사용 불가 (API 키 미설정)")
                    results['tiktok'] = None
            except Exception as e:
                logger.error(f"⚠️ TikTok 업로드 오류: {e}", exc_info=True)
                results['tiktok'] = None
        
        # Instagram 업로드
        if 'instagram' in platforms and 'instagram' in self.uploaders:
            try:
                if self.uploaders['instagram'].is_available():
                    logger.info("📷 Instagram Reels 업로드 중...")
                    # Instagram은 caption에 해시태그 포함
                    caption = title
                    if description:
                        caption += f"\n\n{description}"
                    if tags:
                        hashtags = ' '.join([f"#{tag.replace(' ', '')}" for tag in tags[:10]])
                        caption += f"\n\n{hashtags}"
                    
                    instagram_id = self.uploaders['instagram'].upload_reel(
                        video_path=video_path,
                        caption=caption
                    )
                    results['instagram'] = instagram_id
                    if instagram_id:
                        logger.info(f"✅ Instagram 업로드 완료: {instagram_id}")
                    else:
                        logger.error("⚠️ Instagram 업로드 실패")
                else:
                    logger.warning("⚠️ Instagram 업로더 사용 불가 (API 키 미설정)")
                    results['instagram'] = None
            except Exception as e:
                logger.error(f"⚠️ Instagram 업로드 오류: {e}", exc_info=True)
                results['instagram'] = None
        
        self.results = results
        return results
    
    def get_results(self) -> Dict[str, Optional[str]]:
        """마지막 업로드 결과 반환"""
        return self.results
    
    def get_video_stats(self, video_id: str):
        """
        영상 통계 정보 가져오기 (YouTube만 지원)
        
        Args:
            video_id: YouTube 영상 ID
        
        Returns:
            통계 정보 딕셔너리 또는 None
        """
        if 'youtube' in self.uploaders:
            try:
                return self.uploaders['youtube'].get_video_stats(video_id)
            except Exception as e:
                logger.warning(f"⚠️ YouTube 통계 정보 가져오기 실패: {e}")
                return None
        return None
    
    def check_today_uploaded(self) -> bool:
        """
        오늘 업로드한 영상이 있는지 확인 (YouTube만 지원)
        
        Returns:
            오늘 업로드한 영상이 있으면 True, 없으면 False
        """
        if 'youtube' in self.uploaders:
            try:
                return self.uploaders['youtube'].check_today_uploaded()
            except Exception as e:
                logger.warning(f"⚠️ 오늘 업로드 확인 실패: {e}")
                return False
        return False


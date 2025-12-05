"""
소셜 미디어 업로드 매니저
"""

from src.core.config import settings
from .instagram_uploader import InstagramUploader
from .tiktok_uploader import TikTokUploader
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SocialManager:
    """여러 소셜 플랫폼에 동시 업로드를 관리하는 클래스"""

    def __init__(self):
        self.instagram = InstagramUploader()
        self.tiktok = TikTokUploader()

        self.enable_instagram = settings.ENABLE_INSTAGRAM_UPLOAD
        self.enable_tiktok = settings.ENABLE_TIKTOK_UPLOAD

    def upload_all(self, video_path: str, title: str, description: str = "") -> dict:
        """
        활성화된 모든 플랫폼에 영상 업로드

        Args:
            video_path: 로컬 비디오 파일 경로
            title: 영상 제목 (TikTok 등에서 사용)
            description: 영상 설명/캡션 (Instagram 등에서 사용)

        Returns:
            플랫폼별 업로드 결과 딕셔너리
        """
        results = {"instagram": "skipped", "tiktok": "skipped"}

        # 로컬 파일 업로드 지원 여부 확인
        # 현재 구현체들은 URL 기반 업로드만 지원하므로,
        # 실제로는 여기서 S3 업로드 등의 로직이 선행되어야 함.
        # 임시로 경고 메시지 출력 후 스킵 처리 가능성 있음.

        if self.enable_instagram:
            logger.info("📸 Instagram 업로드 시도...")
            if self.instagram.is_configured:
                success = self.instagram.upload_reel(video_path, caption=description)
                results["instagram"] = "success" if success else "failed"
            else:
                logger.warning("   ⚠️ Instagram 설정이 미완료되어 건너뜁니다.")
                results["instagram"] = "not_configured"

        if self.enable_tiktok:
            logger.info("🎵 TikTok 업로드 시도...")
            if self.tiktok.is_configured:
                success = self.tiktok.upload_video(video_path, title=title)
                results["tiktok"] = "success" if success else "failed"
            else:
                logger.warning("   ⚠️ TikTok 설정이 미완료되어 건너뜁니다.")
                results["tiktok"] = "not_configured"

        return results

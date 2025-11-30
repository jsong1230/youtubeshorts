"""
Instagram Reels 업로더 (Graph API 사용)
"""
import os
import time
import requests
import config
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger(__name__)

class InstagramUploader:
    """Instagram Graph API를 사용하여 Reels 업로드"""
    
    def __init__(self):
        self.access_token = config.INSTAGRAM_ACCESS_TOKEN
        self.account_id = config.INSTAGRAM_ACCOUNT_ID
        self.api_version = "v19.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        if not self.access_token or not self.account_id:
            logger.warning("⚠️ Instagram 설정이 누락되었습니다. (ACCESS_TOKEN 또는 ACCOUNT_ID)")
            self.is_configured = False
        else:
            self.is_configured = True

    def upload_reel(self, video_path: str, caption: str = "") -> bool:
        """
        Reels 업로드 프로세스:
        1. 미디어 컨테이너 생성 (업로드)
        2. 컨테이너 상태 확인 (처리 완료 대기)
        3. 미디어 게시 (Publish)
        """
        if not self.is_configured:
            logger.error("❌ Instagram 업로더가 설정되지 않았습니다.")
            return False
            
        if not os.path.exists(video_path):
            logger.error(f"❌ 영상 파일을 찾을 수 없습니다: {video_path}")
            return False

        # 주의: Graph API는 로컬 파일 업로드를 직접 지원하지 않고, 
        # 공개된 URL에서 다운로드하는 방식을 주로 사용합니다.
        # 하지만 로컬 테스트를 위해 임시로 ngrok 등을 사용하거나,
        # 실제 운영 환경에서는 S3 등에 업로드 후 URL을 전달해야 합니다.
        # 
        # 여기서는 사용자가 비디오 호스팅 URL을 제공하거나, 
        # 추후 확장을 위해 'video_url' 파라미터를 받는 구조로 작성합니다.
        # *현재 구현은 로컬 파일을 직접 올릴 수 없으므로, 
        #  이 부분은 실제 호스팅 로직이 필요함을 알립니다.*
        
        logger.warning("⚠️ Instagram Graph API는 공개된 비디오 URL이 필요합니다.")
        logger.warning("   현재 로컬 파일 직접 업로드는 지원하지 않으므로,")
        logger.warning("   실제 사용 시에는 AWS S3나 호스팅 서버에 먼저 업로드해야 합니다.")
        
        # TODO: 실제 호스팅 로직 구현 필요 (S3, Google Cloud Storage 등)
        # 임시로 로컬 경로를 반환하며 실패 처리
        logger.error(f"❌ [미구현] 비디오 호스팅 URL 생성 필요: {video_path}")
        return False

    def upload_reel_from_url(self, video_url: str, caption: str = "") -> bool:
        """공개된 URL에서 비디오를 가져와 Reels로 게시"""
        if not self.is_configured:
            return False

        logger.info(f"🚀 Instagram Reels 업로드 시작: {video_url}")
        
        # 1. 컨테이너 생성
        container_id = self._create_media_container(video_url, caption)
        if not container_id:
            return False
            
        # 2. 처리 대기
        if not self._wait_for_processing(container_id):
            return False
            
        # 3. 게시
        media_id = self._publish_media(container_id)
        if media_id:
            logger.info(f"✅ Instagram Reels 게시 성공! Media ID: {media_id}")
            return True
        
        return False

    def _create_media_container(self, video_url: str, caption: str) -> str:
        """미디어 컨테이너 생성 요청"""
        url = f"{self.base_url}/{self.account_id}/media"
        payload = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": self.access_token
        }
        
        try:
            response = requests.post(url, data=payload)
            result = response.json()
            
            if "id" in result:
                logger.info(f"   📦 컨테이너 생성 완료: {result['id']}")
                return result["id"]
            else:
                logger.error(f"❌ 컨테이너 생성 실패: {result}")
                return None
        except Exception as e:
            logger.error(f"❌ API 요청 오류: {e}", exc_info=True)
            return None

    def _wait_for_processing(self, container_id: str, timeout: int = 300) -> bool:
        """컨테이너 처리 상태 확인"""
        url = f"{self.base_url}/{container_id}"
        params = {
            "fields": "status_code,status",
            "access_token": self.access_token
        }
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, params=params)
                result = response.json()
                
                status = result.get("status_code")
                if status == "FINISHED":
                    logger.info("   ✅ 미디어 처리 완료")
                    return True
                elif status == "ERROR":
                    logger.error(f"❌ 미디어 처리 중 오류 발생: {result}")
                    return False
                elif status == "IN_PROGRESS":
                    logger.info("   ⏳ 처리 중... (대기)")
                    time.sleep(5)
                else:
                    logger.warning(f"   ❓ 알 수 없는 상태: {status}")
                    time.sleep(5)
            except Exception as e:
                logger.error(f"❌ 상태 확인 오류: {e}", exc_info=True)
                return False
                
        logger.error("❌ 처리 시간 초과")
        return False

    def _publish_media(self, container_id: str) -> str:
        """컨테이너 게시 요청"""
        url = f"{self.base_url}/{self.account_id}/media_publish"
        payload = {
            "creation_id": container_id,
            "access_token": self.access_token
        }
        
        try:
            response = requests.post(url, data=payload)
            result = response.json()
            
            if "id" in result:
                return result["id"]
            else:
                logger.error(f"❌ 게시 실패: {result}")
                return None
        except Exception as e:
            logger.error(f"❌ 게시 요청 오류: {e}", exc_info=True)
            return None

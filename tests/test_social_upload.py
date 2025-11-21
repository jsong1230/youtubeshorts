"""
소셜 미디어 업로드 모의 테스트 (Mock Test)
실제 API 호출 없이 로직을 검증합니다.
"""
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.uploaders.instagram_uploader import InstagramUploader
from src.uploaders.tiktok_uploader import TikTokUploader
from src.uploaders.social_manager import SocialManager

class TestSocialUpload(unittest.TestCase):

    @patch('src.uploaders.instagram_uploader.config')
    def test_instagram_uploader_init(self, mock_config):
        """InstagramUploader 초기화 테스트"""
        mock_config.INSTAGRAM_ACCESS_TOKEN = 'test_token'
        mock_config.INSTAGRAM_ACCOUNT_ID = 'test_id'
        
        uploader = InstagramUploader()
        self.assertTrue(uploader.is_configured)
        self.assertEqual(uploader.access_token, 'test_token')

    @patch('src.uploaders.tiktok_uploader.config')
    def test_tiktok_uploader_init(self, mock_config):
        """TikTokUploader 초기화 테스트"""
        mock_config.TIKTOK_ACCESS_TOKEN = 'test_token'
        
        uploader = TikTokUploader()
        self.assertTrue(uploader.is_configured)
        self.assertEqual(uploader.access_token, 'test_token')

    @patch('src.uploaders.social_manager.InstagramUploader')
    @patch('src.uploaders.social_manager.TikTokUploader')
    @patch('src.uploaders.social_manager.config')
    def test_social_manager_upload_all(self, mock_config, MockTikTok, MockInstagram):
        """SocialManager 통합 업로드 테스트"""
        # 설정 모의 (둘 다 활성화)
        mock_config.ENABLE_INSTAGRAM_UPLOAD = True
        mock_config.ENABLE_TIKTOK_UPLOAD = True
        
        # 업로더 모의 객체 설정
        mock_insta_instance = MockInstagram.return_value
        mock_insta_instance.is_configured = True
        mock_insta_instance.upload_reel.return_value = True
        
        mock_tiktok_instance = MockTikTok.return_value
        mock_tiktok_instance.is_configured = True
        mock_tiktok_instance.upload_video.return_value = True
        
        # 테스트 실행
        manager = SocialManager()
        results = manager.upload_all("test_video.mp4", "Test Title", "Test Desc")
        
        # 검증
        self.assertEqual(results['instagram'], 'success')
        self.assertEqual(results['tiktok'], 'success')
        
        mock_insta_instance.upload_reel.assert_called_once()
        mock_tiktok_instance.upload_video.assert_called_once()

if __name__ == '__main__':
    unittest.main()

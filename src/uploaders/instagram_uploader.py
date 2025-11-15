"""
Instagram Reels 자동 업로드 모듈
"""
import os
import requests
import json
import config


class InstagramUploader:
    """Instagram Graph API를 사용한 Reels 업로드 클래스"""
    
    def __init__(self):
        self.app_id = config.INSTAGRAM_APP_ID
        self.app_secret = config.INSTAGRAM_APP_SECRET
        self.access_token = config.INSTAGRAM_ACCESS_TOKEN
        self.instagram_account_id = config.INSTAGRAM_ACCOUNT_ID
        self.authenticated = False
        
        if self.app_id and self.app_secret and self.access_token:
            self._authenticate()
    
    def _authenticate(self):
        """Instagram Graph API 인증"""
        if not all([self.app_id, self.app_secret, self.access_token, self.instagram_account_id]):
            print("⚠️ Instagram API 키가 설정되지 않았습니다.")
            print("   Facebook for Developers에서 앱을 만들고 API 키를 발급받아 .env 파일에 설정하세요.")
            return False
        
        try:
            # Instagram Graph API 인증 확인
            # 실제 구현은 Instagram Graph API 문서를 참고하세요
            # https://developers.facebook.com/docs/instagram-api/
            
            print("⚠️ Instagram API 인증은 Facebook for Developers에서 설정이 필요합니다.")
            print("   자세한 내용은 docs/INSTAGRAM_SETUP.md를 참고하세요.")
            self.authenticated = False
            return False
        except Exception as e:
            print(f"⚠️ Instagram 인증 실패: {e}")
            self.authenticated = False
            return False
    
    def upload_reel(
        self,
        video_path: str,
        caption: str,
        thumbnail_url: str = None,
        share_to_feed: bool = True
    ):
        """
        Instagram Reels에 영상 업로드
        
        Args:
            video_path: 업로드할 영상 파일 경로
            caption: 영상 캡션 (해시태그 포함 가능)
            thumbnail_url: 썸네일 URL (선택사항)
            share_to_feed: 피드에도 공유할지 여부
        
        Returns:
            업로드된 Reels의 ID 또는 None
        """
        if not self.authenticated:
            print("⚠️ Instagram 인증이 필요합니다. 업로드를 건너뜁니다.")
            return None
        
        if not os.path.exists(video_path):
            print(f"⚠️ 영상 파일을 찾을 수 없습니다: {video_path}")
            return None
        
        try:
            # Instagram Graph API를 통한 Reels 업로드
            # 실제 구현은 Instagram Graph API 문서를 참고하세요
            
            # 1단계: 영상 업로드 URL 요청
            # 2단계: 영상 파일 업로드
            # 3단계: Reels 게시
            
            print("⚠️ Instagram Reels 업로드 기능은 Instagram Graph API 설정이 필요합니다.")
            print("   자세한 내용은 docs/INSTAGRAM_SETUP.md를 참고하세요.")
            return None
            
        except Exception as e:
            print(f"⚠️ Instagram 업로드 실패: {e}")
            return None
    
    def is_available(self) -> bool:
        """Instagram 업로더 사용 가능 여부"""
        return self.authenticated

